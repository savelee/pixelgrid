# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.12-slim

ARG TARGETARCH=arm64
ENV SUPERCRONIC_VERSION=v0.2.33

# Install BlueZ / D-Bus, rfkill, and curl for Supercronic
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    dbus \
    libglib2.0-0 \
    curl \
    rfkill \
    && rm -rf /var/lib/apt/lists/*

# Install Supercronic (container-safe cron daemon that preserves env vars and forwards stdout/stderr)
RUN curl -fsSL "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}" -o /usr/local/bin/supercronic \
    && chmod +x /usr/local/bin/supercronic

COPY --from=ghcr.io/astral-sh/uv:0.4 /uv /bin/uv

WORKDIR /app
COPY pyproject.toml .
RUN uv pip install --system .

COPY src/ src/
COPY crontab /etc/crontab

RUN mkdir -p /app/downloads
VOLUME ["/app/downloads"]

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV DOWNLOAD_DIR=/app/downloads
ENV PORT=8080
ENV LOOP_INTERVAL_MINUTES=15

EXPOSE 8080

ENTRYPOINT ["python", "src/server.py"]
