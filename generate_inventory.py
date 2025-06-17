"""Generate Ansible inventory from config.yml.

Usage:
    python generate_inventory.py
"""
from __future__ import annotations

import configparser
import yaml
from pathlib import Path

CONFIG_PATH = Path('ansible/config.yml')
INVENTORY_PATH = Path('ansible/inventory.ini')


def main() -> None:
    """Create inventory.ini based on config.yml."""
    data = yaml.safe_load(CONFIG_PATH.read_text())

    config = configparser.ConfigParser(allow_no_value=True)
    config.add_section('control-plane')
    for host in data.get('control_plane', []):
        config.set('control-plane', host)

    config.add_section('workers')
    for host in data.get('workers', []):
        config.set('workers', host)

    ssh_user = data.get('ssh_user', 'ubuntu')
    private_key = Path(data.get('private_key_path', '~/.ssh/id_rsa')).expanduser()

    config.add_section('all:vars')
    config.set('all:vars', 'ansible_user', ssh_user)
    config.set('all:vars', 'ansible_ssh_private_key_file', str(private_key))

    with INVENTORY_PATH.open('w') as f:
        config.write(f)
    print(f"Inventory written to {INVENTORY_PATH}")


if __name__ == '__main__':
    main()
