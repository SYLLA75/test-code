# CLI Usage

While the UI is the primary interface, you can still manage the cluster manually.

```bash
python tools/generate_files.py --db database/example.db
ansible-playbook -i ansible/inventory.ini ansible/site.yml
```
