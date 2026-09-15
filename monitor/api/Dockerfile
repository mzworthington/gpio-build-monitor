FROM python:3.12-slim-bookworm

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY monitor/api/requirements.lock ./requirements.lock
COPY monitor/api/monitor ./monitor
RUN pip install --no-cache-dir --require-hashes --only-binary :all: -r requirements.lock \
    && pip wheel --no-cache-dir --no-deps --no-build-isolation -w /tmp/app-wheel . \
    && pip install --no-cache-dir --no-deps --only-binary :all: /tmp/app-wheel/* \
    && rm -rf /tmp/app-wheel \
    && useradd --create-home --uid 1000 app \
    && chown -R app:app /app

EXPOSE 8080
USER app
CMD ["python", "-m", "monitor", "run", "--conf", "/etc/gpio-build-monitor/integrations.yaml"]

EXPOSE 8080
USER app
CMD ["python", "-m", "monitor", "run", "--conf", "/etc/gpio-build-monitor/integrations.yaml"]
