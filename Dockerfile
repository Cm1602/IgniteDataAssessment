# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv/app

# Installs the runtime dependencies only, not the [dev] extra, so pytest, mypy
# and ruff never end up in a production image.
#
# The dependency list lives in pyproject.toml alongside the package itself, so
# app/ has to be present before pip can install, which means a code change
# reinstalls the dependencies too. Fine at this size. A lock file, or a
# generated requirements.txt, would let the dependency layer cache separately.
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

COPY alembic.ini ./
COPY migrations ./migrations
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Nothing here needs root, and a container that cannot write to its own code is
# one less thing to worry about.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /srv/app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
