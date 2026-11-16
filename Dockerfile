# Pantry Path diet classifier in a container.
# Two stages: "test" runs the test suite during the build (a failing test fails the build),
# "runtime" is the small image you actually run: no pytest, no tests, non-root user.

# ---------- shared base ----------
FROM python:3.12-slim AS base
# Don't write .pyc files; print logs straight away instead of buffering them
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
# The classifier uses only the Python standard library, so there is nothing to pip install here
COPY src/ src/
COPY data/ data/

# ---------- test stage ----------
FROM base AS test
# Install the test tool first: this layer is cached and only re-runs when requirements-dev.txt changes
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY tests/ tests/
RUN python -m pytest -q && touch /tests-passed

# ---------- runtime stage ----------
FROM base AS runtime
# Copying this marker makes the runtime stage depend on the test stage,
# so BuildKit can't skip the tests when you build the default target
COPY --from=test /tests-passed /tests-passed
RUN useradd --create-home --uid 1000 pantry \
    && mkdir -p /app/output && chown pantry:pantry /app/output
USER pantry
# Results go here; mount a folder from your machine to keep them: -v "$PWD/output:/app/output"
VOLUME ["/app/output"]
ENTRYPOINT ["python", "-m", "src.classify"]
# Default arguments; anything after the image name in `docker run` replaces these
CMD ["--input", "data/products.json", "--output", "output"]
