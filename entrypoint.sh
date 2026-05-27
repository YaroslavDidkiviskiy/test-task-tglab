#!/bin/sh
set -e

if [ -z "$(ls -A alembic/versions)" ]; then
  echo "No migrations found, generating..."
  alembic revision --autogenerate -m "init"
fi

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload