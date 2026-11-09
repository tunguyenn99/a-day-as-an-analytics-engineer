.PHONY: install demo validate format platform platform-local docs package
install:
	uv venv --python 3.11
	uv pip install -r requirements-dev.txt
format:
	.venv/bin/black ingestion scripts dags tests
validate:
	.venv/bin/black --check ingestion scripts dags tests
	.venv/bin/sqlfluff lint dbt/models dbt/tests
	.venv/bin/python -m unittest discover -s tests
	.venv/bin/dbt parse --project-dir dbt --profiles-dir dbt
demo:
	docker compose --env-file .env.example up -d --wait warehouse
	PGHOST=localhost PGPORT=5432 PGDATABASE=postgres PGUSER=postgres PGPASSWORD=local-only PGSSLMODE=disable .venv/bin/python -m ingestion.web_analytics --fixture --no-archive
	.venv/bin/dbt build --project-dir dbt --profiles-dir dbt
platform:
	docker compose --profile platform up -d --build

platform-local:
	docker compose --env-file .env.example -f compose.yml -f compose.local.yml --profile platform up -d --build

docs:
	.venv/bin/dbt docs generate --project-dir dbt --profiles-dir dbt
	.venv/bin/dbt docs serve --project-dir dbt --profiles-dir dbt --port 8081 --host 127.0.0.1

package:
	python3 -m scripts.package
