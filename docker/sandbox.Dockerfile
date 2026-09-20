FROM python:3.12-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN python -m pip install --no-cache-dir --upgrade pip && python -m pip install --no-cache-dir pytest ruff mypy
WORKDIR /workspace
ENTRYPOINT []
