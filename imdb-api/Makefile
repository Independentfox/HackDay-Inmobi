.PHONY: all deploy clean local-up local-down local-restart migrate seed test test-watch status health logs

# === LOCAL DEVELOPMENT (Docker Compose) ===
local-up:
	docker compose up --build -d
	@echo "⏳ Waiting for API to be ready..."
	@sleep 10
	@echo "✅ CineDB API at http://localhost:8000"
	@echo "📚 Docs at http://localhost:8000/docs"
	@echo "🎬 UI  at http://localhost:8000/"

local-down:
	docker compose down -v

local-restart:
	docker compose restart api

logs:
	docker compose logs -f api

migrate:
	PYTHONPATH=. DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb alembic revision --autogenerate -m "$(msg)"
	PYTHONPATH=. DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb alembic upgrade head

seed:
	PYTHONPATH=. DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb python seed.py

# === TESTING ===
test:
	@echo "🧪 Running test suite..."
	PYTHONPATH=. TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb_test pytest tests/ -v --tb=short -W ignore::DeprecationWarning

test-watch:
	PYTHONPATH=. TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/imdb_test pytest tests/ -v --tb=short -x

# === KUBERNETES DEPLOYMENT ===
deploy:
	@echo "🚀 Starting Minikube..."
	minikube start --driver=docker
	@echo "🔧 Building Docker image inside Minikube..."
	@eval $$(minikube docker-env) && \
	docker build -t imdb-api:latest . && \
	echo "📦 Applying Kubernetes manifests..." && \
	kubectl apply -f k8s/namespace.yaml && \
	kubectl apply -f k8s/secret.yaml && \
	kubectl apply -f k8s/ai-secret.yaml && \
	kubectl apply -f k8s/configmap.yaml && \
	kubectl apply -f k8s/postgres-statefulset.yaml && \
	echo "⏳ Waiting for PostgreSQL..." && \
	kubectl wait --for=condition=ready pod/postgres-0 -n imdb --timeout=180s && \
	echo "🗄️  Running migrations + seed (one-shot Job)..." && \
	kubectl delete job/db-init -n imdb --ignore-not-found && \
	kubectl apply -f k8s/db-init-job.yaml && \
	kubectl wait --for=condition=complete job/db-init -n imdb --timeout=300s && \
	echo "📦 Applying API resources..." && \
	kubectl apply -f k8s/api-deployment.yaml && \
	kubectl apply -f k8s/api-service.yaml && \
	kubectl apply -f k8s/api-pdb.yaml && \
	echo "⏳ Waiting for API pods..." && \
	kubectl wait --for=condition=ready pod -l app=imdb-api -n imdb --timeout=180s && \
	echo "" && \
	echo "✅ DEPLOYMENT COMPLETE!" && \
	echo "📡 API URL:" && \
	minikube service imdb-api-service -n imdb --url

clean:
	kubectl delete namespace imdb --ignore-not-found
	minikube stop

status:
	kubectl get all -n imdb
	@echo ""
	@echo "📡 API URL:"
	@minikube service imdb-api-service -n imdb --url 2>/dev/null || echo "Service not ready yet"

# === QUICK HEALTH CHECK ===
health:
	@curl -s http://localhost:8000/health | python3 -m json.tool || echo "API not running"
