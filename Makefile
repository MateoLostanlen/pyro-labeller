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
	docker build -t task_manager:latest -f task_manager/Dockerfile task_manager/
	docker compose up -d

stop:
	docker compose down

log:
	docker logs --tail 50 pyro-labeller-task_manager-1 -f
	

logapp:
	docker logs --tail 50 pyro-labeller-pyro_labeller-1 -f

