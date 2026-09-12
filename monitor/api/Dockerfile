FROM python:3.12-slim-bookworm

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY monitor/api/monitor ./monitor
RUN pip install --no-cache-dir .

EXPOSE 8080
CMD ["python", "-m", "monitor", "run", "--conf", "/etc/gpio-build-monitor/integrations.yaml"]
