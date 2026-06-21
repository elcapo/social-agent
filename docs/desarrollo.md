# Desarrollo

## Tests y linter

```bash
# Ejecutar tests
uv run pytest tests/ -v

# Linter
uv run ruff check backend/src/ tests/

# Tests del frontend (Astro + Vitest)
cd frontend && pnpm test

# (Opcional) Activar el entorno virtual para comandos más rápidos
source .venv/bin/activate
```

## Migraciones de base de datos (Alembic)

El backend SQLite usa [Alembic](https://alembic.sqlalchemy.org/) para el control
de versiones del esquema. Las migraciones viven en `backend/alembic/versions/`.

```bash
# Aplicar todas las migraciones pendientes
cd backend && alembic upgrade head

# Revertir la última migración
cd backend && alembic downgrade -1

# Generar una migración a partir de cambios en los modelos ORM (db.py)
cd backend && alembic revision --autogenerate -m "descripción del cambio"
```

> [!NOTE]
> La ruta de la base de datos `settings.data_dir` es relativa al
> CWD, por lo que `alembic` ejecutado desde `backend/` resuelve la DB a
> `backend/data/social_agent.db` en vez de `data/social_agent.db` (raíz del
> proyecto). Si tu DB con datos está en la raíz, apunta a ella explícitamente:

```bash
cd backend && SOCIAL_AGENT_SQLITE_PATH=$(pwd)/../data/social_agent.db alembic upgrade head
```
