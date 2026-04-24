FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management (as root, before user switch)
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip install --system --no-cache .

COPY . .

# Create an unprivileged user and make the app tree writable for it.
# /app/boards and /app/data are volume mount points — chown them too so the
# container can write board/state files as the non-root user.
RUN useradd --no-create-home --shell /usr/sbin/nologin --uid 10001 orbvis \
    && mkdir -p /app/maps /app/boards /app/data /app/icons \
    && chown -R orbvis:orbvis /app

USER orbvis

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
