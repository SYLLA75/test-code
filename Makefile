.PHONY: lint test deploy ui inventory

lint:
	ansible-lint ansible/*.yml ansible/roles
	yamllint ansible

inventory:
	python generate_inventory.py

test:
	molecule test

deploy: inventory
	ansible-playbook -i ansible/inventory.ini ansible/site.yml

ui:
	python ui/app.py
