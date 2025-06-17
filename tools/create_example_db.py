#!/usr/bin/env python3
"""Create example SQLite database for tests and CI."""
from __future__ import annotations

from pathlib import Path
import sqlite3

DB = Path("database/example.db")
SCHEMA = Path("database/schema.sql")


def main() -> None:
    if DB.exists():
        DB.unlink()
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA.read_text())
    conn.execute(
        "INSERT INTO clusters (name, control_plane, workers, ssh_user, private_key_path) VALUES (?,?,?,?,?)",
        ("demo", "192.0.2.10", "192.0.2.11", "root", "/tmp/id_rsa"),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
