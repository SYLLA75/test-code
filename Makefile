.PHONY: up down ui lint test example-db

up:
	docker compose up -d

down:
	docker compose down

ui:
	FLASK_APP=ui.app flask run --reload

lint:
	ansible-lint ansible/site.yml ansible/cleanup.yml ansible/upgrade.yml ansible/roles
	yamllint ansible

example-db:
	python tools/create_example_db.py

test:
	pytest
