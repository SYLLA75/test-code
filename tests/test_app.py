from pathlib import Path
import sqlite3
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ui.app as app


def setup_test_db(tmp_path):
    db = tmp_path / "test.db"
    schema = Path("database/schema.sql").read_text()
    conn = sqlite3.connect(db)
    conn.executescript(schema)
    conn.execute(
        "INSERT INTO clusters (name, control_plane, workers, ssh_user, private_key_path) VALUES (?,?,?,?,?)",
        ("demo", "10.0.0.1", "10.0.0.2", "root", "/tmp/key"),
    )
    conn.commit()
    conn.close()
    return db


def test_index(tmp_path, monkeypatch):
    db = setup_test_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    app.init_db()
    client = app.APP.test_client()
    response = client.get("/", headers={"Authorization": "Basic YWRtaW46c2VjcmV0"})
    assert response.status_code == 200


def test_invalid_ip(tmp_path, monkeypatch):
    db = setup_test_db(tmp_path)
    monkeypatch.setenv("DB_PATH", str(db))
    client = app.APP.test_client()
    data = {
        "name": "bad",
        "control_plane": "invalid",
        "workers": "",
        "ssh_user": "root",
        "private_key_path": "/tmp/key",
    }
    resp = client.post("/cluster/new", data=data, headers={"Authorization": "Basic YWRtaW46c2VjcmV0"})
    assert resp.status_code == 200
    assert b"Invalid IP" in resp.data
