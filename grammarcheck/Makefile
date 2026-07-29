.PHONY: dev install test lint clean eval docker-up docker-down

dev:
	cd backend && uvicorn main:app --reload --port 8000

install:
	cd backend && pip install -r requirements.txt

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && ruff check . && ruff format --check .

eval:
	cd backend && python -m evals.eval_runner

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.db" -delete

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
