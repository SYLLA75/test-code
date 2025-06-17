# FAQ

## Why is my node not joining?
Check network connectivity and ensure that the token is valid.

## How do I rollback?
Run `ansible-playbook -i ansible/inventory.ini ansible/cleanup.yml` and redeploy.

## How do I edit an advanced parameter?
Open the cluster form in the UI and expand the **Advanced** section. Modify the desired field and save.
