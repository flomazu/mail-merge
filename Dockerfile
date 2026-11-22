# Optional container wrapper around the same CLI as a local pip install.
# Config, input and output are mounted to /data at runtime; nothing
# customer-specific and no secrets are baked into the image.

# Small official Python image (Debian without extras).
FROM python:3.14-slim

# No .pyc files in the image, log output appears immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install the package exactly like a local `pip install .`.
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 1000 app

# Run as a normal user instead of root.
USER app

# Mount point for config, recipient list, template and output.
WORKDIR /data

# `docker run mail-merge --config config.yaml` runs `mail-merge --config config.yaml`.
ENTRYPOINT ["mail-merge"]
CMD ["--help"]
