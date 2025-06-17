"""Generate Ansible files from the SQLite configuration."""
from __future__ import annotations

import argparse
import configparser
import sqlite3
from pathlib import Path
import yaml


def fetch_cluster(db_path: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute("SELECT * FROM clusters LIMIT 1")
    row = cur.fetchone()
    if not row:
        raise SystemExit("No clusters defined in database")
    return dict(row)


def write_config(data: dict, config_path: Path) -> None:
    config = {
        'cluster_name': data['name'],
        'ssh_user': data['ssh_user'],
        'private_key_path': data['private_key_path'],
        'control_plane': data['control_plane'].split(','),
        'workers': data['workers'].split(','),
    }
    config_path.write_text(yaml.safe_dump(config))


def write_inventory(data: dict, inv_path: Path) -> None:
    config = configparser.ConfigParser(allow_no_value=True)
    config.add_section('control-plane')
    for host in data['control_plane'].split(','):
        config.set('control-plane', host)
    config.add_section('workers')
    for host in data['workers'].split(','):
        config.set('workers', host)
    config.add_section('all:vars')
    config.set('all:vars', 'ansible_user', data['ssh_user'])
    config.set('all:vars', 'ansible_ssh_private_key_file', data['private_key_path'])
    with inv_path.open('w') as f:
        config.write(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate files")
    parser.add_argument('--db', type=Path, required=True)
    args = parser.parse_args()

    cluster = fetch_cluster(args.db)
    write_config(cluster, Path('ansible/config.yml'))
    write_inventory(cluster, Path('ansible/inventory.ini'))


if __name__ == '__main__':
    main()
