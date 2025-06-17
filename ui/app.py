"""Flask UI for Kubernetes deployment."""
from __future__ import annotations

import os
import queue
import threading
from functools import wraps
from pathlib import Path
from typing import Generator, List

try:
    import ansible_runner
except ImportError:  # pragma: no cover - fallback for test env
    class _DummyRunner:
        """Minimal ansible_runner replacement for tests."""

        @staticmethod
        def run(**_: object) -> None:
            return None

    ansible_runner = _DummyRunner()
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from pydantic import BaseModel, ValidationError, validator
import sqlite3
import yaml
import configparser

AUTH_USERNAME = os.getenv("AUTH_USERNAME", "admin")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "secret")

APP = Flask(__name__)
APP.secret_key = os.getenv("SECRET_KEY", "change-me")


def get_db_path() -> Path:
    """Return database path from environment or default."""
    return Path(os.getenv("DB_PATH", "database/clusters.db"))


def init_db() -> None:
    """Create SQLite database if it does not exist."""
    db_path = get_db_path()
    if db_path.exists():
        return
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(Path("database/schema.sql").read_text())
    conn.commit()
    conn.close()


def get_db() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def requires_auth(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username != AUTH_USERNAME or auth.password != AUTH_PASSWORD:
            return Response(status=401, headers={"WWW-Authenticate": 'Basic realm="Login"'})
        return func(*args, **kwargs)

    return wrapped


class ClusterModel(BaseModel):
    """Validate cluster configuration."""

    name: str
    ssh_user: str
    private_key_path: str
    control_plane: List[str]
    workers: List[str]
    k8s_version: str = "1.29.0"
    cni_plugin: str = "calico"

    @validator("control_plane", "workers", pre=True)
    def split_hosts(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, str):
            return [h.strip() for h in value.split(",") if h.strip()]
        return value

    @validator("control_plane", "workers")
    def validate_ips(cls, value: List[str]) -> List[str]:
        for ip in value:
            parts = ip.split(".")
            if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                raise ValueError(f"Invalid IP {ip}")
        if len(set(value)) != len(value):
            raise ValueError("Duplicate IP detected")
        return value

    @validator("private_key_path")
    def key_readable(cls, value: str) -> str:
        path = Path(value).expanduser()
        if not path.exists():
            raise ValueError("Private key path not found")
        return str(path)


def write_config_and_inventory(cluster: ClusterModel) -> None:
    config = {
        "cluster_name": cluster.name,
        "ssh_user": cluster.ssh_user,
        "private_key_path": cluster.private_key_path,
        "control_plane": cluster.control_plane,
        "workers": cluster.workers,
    }
    Path("ansible").mkdir(exist_ok=True)
    Path("ansible/config.yml").write_text(yaml.safe_dump(config))
    cfg = configparser.ConfigParser(allow_no_value=True)
    cfg.add_section("control-plane")
    for host in cluster.control_plane:
        cfg.set("control-plane", host)
    cfg.add_section("workers")
    for host in cluster.workers:
        cfg.set("workers", host)
    cfg.add_section("all:vars")
    cfg.set("all:vars", "ansible_user", cluster.ssh_user)
    cfg.set("all:vars", "ansible_ssh_private_key_file", cluster.private_key_path)
    with open("ansible/inventory.ini", "w") as f:
        cfg.write(f)


def run_playbook(playbook: str) -> Generator[str, None, None]:
    q: "queue.Queue[str]" = queue.Queue()

    def handler(event: dict) -> None:
        if event.get("stdout"):
            q.put(event["stdout"])

    def runner() -> None:
        ansible_runner.run(
            private_data_dir=".",
            playbook=playbook,
            inventory="ansible/inventory.ini",
            event_handler=handler,
        )
        q.put("RUN_COMPLETE")

    threading.Thread(target=runner, daemon=True).start()

    while True:
        line = q.get()
        if line == "RUN_COMPLETE":
            break
        yield f"data: {line}\n\n"


@APP.route("/")
@requires_auth
def index() -> str:
    conn = get_db()
    clusters = conn.execute("SELECT * FROM clusters").fetchall()
    return render_template("index.html", clusters=clusters)


@APP.route("/cluster/new", methods=["GET", "POST"])
@requires_auth
def create_cluster() -> str | Response:
    if request.method == "POST":
        data = request.form.to_dict()
        try:
            model = ClusterModel(**data)
        except ValidationError as exc:
            flash(str(exc), "danger")
            return render_template("form.html", data=data)
        conn = get_db()
        conn.execute(
            "INSERT INTO clusters (name, control_plane, workers, ssh_user, private_key_path, k8s_version, cni_plugin) VALUES (?,?,?,?,?,?,?)",
            (
                model.name,
                ",".join(model.control_plane),
                ",".join(model.workers),
                model.ssh_user,
                model.private_key_path,
                model.k8s_version,
                model.cni_plugin,
            ),
        )
        conn.commit()
        flash("Cluster saved", "success")
        return redirect(url_for("index"))
    return render_template("form.html", data={"k8s_version": "1.29.0", "cni_plugin": "calico"})


@APP.route("/deploy/<int:cid>")
@requires_auth
def deploy(cid: int) -> Response:
    conn = get_db()
    row = conn.execute("SELECT * FROM clusters WHERE id=?", (cid,)).fetchone()
    if not row:
        return Response("Not found", status=404)
    cluster = ClusterModel(**dict(row))
    write_config_and_inventory(cluster)
    return Response(run_playbook("ansible/site.yml"), mimetype="text/event-stream")


@APP.route("/destroy/<int:cid>")
@requires_auth
def destroy(cid: int) -> Response:
    conn = get_db()
    row = conn.execute("SELECT * FROM clusters WHERE id=?", (cid,)).fetchone()
    if not row:
        return Response("Not found", status=404)
    cluster = ClusterModel(**dict(row))
    write_config_and_inventory(cluster)
    return Response(run_playbook("ansible/cleanup.yml"), mimetype="text/event-stream")


if __name__ == "__main__":
    init_db()
    APP.run(debug=True)
