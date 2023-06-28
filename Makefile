# this target runs checks on all files
quality:
	isort . -c
	flake8
	black --check .

# this target runs checks on all files and potentially modifies some of them
style:
	isort .
	black .

# Run app
run:
	docker build -t pyro_labeller:latest .
	docker compose up -d
