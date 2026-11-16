# Docker Lab 1: Pantry Path diet classifier in a container

MLOps (IE7374) Lab Assignment 4, based on [`Labs/Docker_Labs/Lab1`](https://github.com/raminmohammadi/MLOps/tree/main/Labs/Docker_Labs/Lab1).

The original lab packs a script that trains a RandomForest on Iris into a Docker image.
This version packs **Pantry Path's diet classifier** instead. Pantry Path is my team project: a meal planner
that checks real grocery products against a user's diet. The container reads a snapshot of real
Open Food Facts products, labels each one vegan / vegetarian / non-vegetarian with a reason,
and writes the results and metrics to a folder on your machine.

It continues my earlier labs: the same rules and data from
[GitHub Lab 1](https://github.com/Anshkanungo/mlops-github-lab1) and the
[DVC lab](https://github.com/Anshkanungo/mlops-dvc-lab), now shipped as an image anyone can run.

## What I changed from the original lab

| | Original lab | This repo |
|---|---|---|
| Data | Iris (built into scikit-learn) | 17 real grocery products from Open Food Facts, each hand-labelled with its diet (`data/products.json`, v2 from the DVC lab) |
| Model | RandomForest, trained in the container | Diet rules **v2**: ingredients + allergen tags, and now the **product name** (see below). Agreement with the labels: **94.1% → 100%** |
| Output | `iris_model.pkl` saved *inside* the container, so it is lost when the container exits | 3 JSON files written to `/app/output`, a **volume** you mount from your machine |
| Base image | `python:3.10` (full Debian, 1.61 GB before scikit-learn) | `python:3.12-slim`: the final image is **203 MB** (≈8× smaller) |
| Dependencies | `scikit-learn`, `joblib`, unpinned | None at runtime (standard library only); `pytest==9.2.0` pinned, test stage only |
| Tests | None | 43 pytest tests that **run during `docker build`**; a failing test fails the build, so no image is produced |
| Build | One stage | Multi-stage: `test` stage → small `runtime` stage without tests or pytest |
| Security | Runs as root | Runs as non-root user `pantry` (uid 1000) |
| Bad input | — | Validates every record first; a bad record or duplicate barcode stops the run with exit code 1 |
| Arguments | Fixed `CMD` | `ENTRYPOINT` + default `CMD`, so you can point it at your own snapshot |
| Build context | Everything | `.dockerignore` keeps `.git`, `.venv`, caches and outputs out |

### The rules change (v1 → v2)
The DVC lab's metrics found one wrong answer: **Oscar Mayer Original Bacon** was labelled *vegan*,
because its ingredients list shows only the cure (`Water, salt, sugar, sodium phosphates, sodium
ascorbate, sodium nitrite`), with no meat word. v2 also reads the product name: a meat word there
makes the product non-vegetarian, unless the name says it is plant-based (`Veggie`, `Plant-Based`,
`Meatless`, `Vegan`, `Imitation`, …). Ingredients still win: "Veggie Egg Bites" with egg whites stays vegetarian.

```
Original Bacon    non-vegetarian  Name says bacon (not in the ingredients list)
```

## Project structure

```
Dockerfile              multi-stage: base → test (runs pytest) → runtime
.dockerignore
requirements-dev.txt    pytest, used only in the test stage
data/products.json      17 Open Food Facts products with hand-checked expected_diet
src/diet_rules.py       classify(evidence, name) and fits_diet(diet, evidence, name)
src/classify.py         container entry point: validate → classify → write 3 JSON files
tests/                  43 tests: every real product, name rule, traps, entry point, bad data
```

## Run it

Needs Docker Desktop (or any Docker engine).

```bash
# 1. Build (the tests run as part of this; it fails if any test fails)
docker build -t pantry-diet:v2 .

# 2. Run; results land in ./output on your machine
docker run --rm -v "$PWD/output:/app/output" pantry-diet:v2

# 3. Optional: save the image to a file (like the original lab) and load it elsewhere
docker save pantry-diet:v2 -o pantry-diet_v2.tar
docker load -i pantry-diet_v2.tar
```

Run it on your own snapshot (same JSON shape as `data/products.json`):

```bash
docker run --rm -v "$PWD/my_data:/in:ro" -v "$PWD/output:/app/output" \
  pantry-diet:v2 --input /in/my_products.json --output output
```

Output files:

| File | Contents |
|---|---|
| `validation.json` | products, invalid records, duplicate barcodes, products with complete evidence |
| `products_classified.json` | each product: barcode, name, brand, diet, reason, expected_diet |
| `diet_metrics.json` | rules version, count per diet, agreement with labels, list of mismatches |

Run the tests without Docker:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

On Linux, if the mounted `output/` folder isn't writable by uid 1000, add `--user "$(id -u)"` to `docker run`.

## Verification (2026-11-16, Docker 29.8.2 on macOS)

| Check | Result |
|---|---|
| Tests locally (Python 3.12) | 43 passed |
| `docker build` | tests ran inside the build: 43 passed; image `pantry-diet:v2`, Python 3.12.16 |
| `docker run` with the volume | 3 files in `./output`; 7 non-vegetarian / 5 vegan / 5 vegetarian; agreement **1.0**, 0 mismatches |
| Runs as non-root | `uid=1000(pantry)` |
| Runtime image is clean | contains only `src/`, `data/`, `output/`; pytest not installed |
| Broken rule (removed `bacon` from the meat words, in a copy) | `docker build` failed at the test step; no image created |
| Bad input (non-digit barcode + duplicate, mounted read-only) | exit code 1, `validation.json` says 1 invalid / 1 duplicate, nothing classified |
| Size | `pantry-diet:v2` 203 MB vs the original's base `python:3.10` 1.61 GB |
| `docker save` → delete image → `docker load` → run | 42 MB `.tar`; same results after loading |

## What I learned
- Anything a container writes is gone when it exits unless it goes to a mounted volume. The original lab's saved model has nowhere to go.
- With BuildKit, a stage that the final image doesn't use is **skipped**. Copying a marker file from the test stage (`COPY --from=test /tests-passed`) forces the tests to run on every build.
- Layer order matters: copying `requirements-dev.txt` and installing before copying `tests/` means editing a test doesn't reinstall pytest.
- A slim base image and no unneeded libraries cut the image size by ~8×.

## Limitations
- The name rule is keyword-based: a product named "Chicken-Flavoured Ramen" with a vegan ingredients list would be marked non-vegetarian. This errs on the safe side for vegetarians, but it is still a false alarm.
- 17 labelled products is a small evaluation set; 100% agreement here doesn't mean 100% in general.
- The snapshot is baked into the image as a fixed copy (retrieved 2026-10-18). The container doesn't fetch fresh Open Food Facts data, so runs are reproducible.
- `python:3.12-slim` is pinned by tag, not by digest, so a rebuild later may pick up a newer 3.12 patch release.
