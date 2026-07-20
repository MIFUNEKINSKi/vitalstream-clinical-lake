.PHONY: install test lint generate samples dbt-build dbt-docs deploy clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/ scripts/ airflow/

format:
	ruff format src/ tests/ scripts/ airflow/

generate:
	python -m src.data_generator.generate_fhir_bundles --count 10 --output-dir output/fhir_bundles

samples:
	python scripts/regenerate_sample_outputs.py

dbt-build:
	python scripts/generate_dbt_seed.py
	cd dbt && dbt build

dbt-docs:
	cd dbt && dbt docs generate

deploy:
	cd infrastructure && terraform init && terraform apply

clean:
	rm -rf output/ .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
