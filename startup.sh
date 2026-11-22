#!/bin/sh
# App Service startup command. One worker because concurrency is limited inside the app;
# raise -w only together with AGENT_MAX_CONCURRENT and a larger plan.
exec gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 1 \
  --bind 0.0.0.0:${PORT:-8000} \
  --timeout 180 \
  --access-logfile - --error-logfile -
