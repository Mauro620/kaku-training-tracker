API := apps/api
UV  := uv run --directory $(API)

# La configuración local se lee de .env.local y se exporta al entorno de los
# comandos. El guion la hace opcional: sin el archivo, valen los defaults.
-include .env.local
export

.PHONY: up down migrate revision seed test lint format shell

up:  ## Levanta postgres y el api
	docker compose up -d --build

down:  ## Baja los contenedores (los datos sobreviven en el volumen)
	docker compose down

migrate:  ## Aplica las migraciones pendientes
	$(UV) alembic upgrade head

revision:  ## Genera una migración. Uso: make revision m="mensaje"
	$(UV) alembic revision --autogenerate -m "$(m)"
	@echo
	@echo ">> Revisala a mano antes de aplicarla. Autogenerate no detecta"
	@echo ">> renombres ni columnas generadas."

seed:  ## Siembra catálogos y parámetros (idempotente)
	$(UV) python -m app.seeds

test:  ## Corre los tests del backend
	$(UV) pytest

lint:  ## ruff + mypy
	$(UV) ruff check .
	$(UV) ruff format --check .
	$(UV) mypy

format:  ## Aplica el formato
	$(UV) ruff check --fix .
	$(UV) ruff format .

shell:  ## psql contra la base local
	docker compose exec db psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)
