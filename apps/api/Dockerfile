FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /srv

# El entorno virtual vive FUERA de /srv. docker-compose monta ./apps/api sobre
# /srv para tener recarga en caliente, y ese bind mount es bidireccional: con
# el .venv por defecto en /srv/.venv, el `uv sync` del contenedor pisa el .venv
# del host con archivos de root y ningún comando local vuelve a correr.
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Las dependencias se instalan antes de copiar el código para que un cambio en
# app/ no invalide la capa de dependencias.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

EXPOSE 8000
# alembic upgrade head antes de arrancar: Railway (y la mayoria de PaaS) no
# tiene una release phase separada como Heroku, asi que el propio arranque
# del contenedor es el unico lugar garantizado de correr antes de servir
# trafico. Es idempotente (no-op si ya esta en head), seguro en cada boot
# y en local (docker-compose ya espera a que el db este healthy).
#
# Railway inyecta PORT dinamico y espera que el proceso escuche ahi;
# docker-compose local no lo setea, por eso el fallback a 8000 (el mismo
# puerto que docker-compose ya mapea). Forma shell, no exec, para que
# ${PORT:-8000} se expanda.
#
# Despues de migrar se corre el seed, que es idempotente (upsert por clave
# natural; el perfil y el peso objetivo solo se crean si no existen). Sin el,
# una migracion que agrega catalogos o parametros deja la API respondiendo 404
# hasta que alguien lo corra a mano. Si el seed falla (p. ej. faltan las
# credenciales SEED_USUARIO_*) se avisa y se arranca igual: no debe tumbar el
# deploy.
CMD ["sh", "-c", "uv run alembic upgrade head && (uv run python -m app.seeds || echo 'AVISO: el seed fallo, se arranca igual') && uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
