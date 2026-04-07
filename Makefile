.PHONY: install test lint generate deploy clean

install:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

generate:
	python -m src.data_generator.generate_fhir_bundles --count 10 --output-dir output/fhir_bundles

deploy:
	cd infrastructure && terraform init && terraform apply

clean:
	rm -rf output/ .pytest_cache __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} +
