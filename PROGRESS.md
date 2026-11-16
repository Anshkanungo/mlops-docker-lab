# Progress

**Current status:** Lab built, verified and committed locally; remote `origin` set. Next: Ansh pushes `main` to https://github.com/Anshkanungo/mlops-docker-lab and submits (due date Nov 15 has passed).

## Todo
- [ ] Ansh pushes `main` (`git push -u origin main`) to https://github.com/Anshkanungo/mlops-docker-lab (public, empty, created by Ansh)
- [ ] Submit the repo link on Canvas (Lab Assignment 4)
- [ ] Pantry Path: port the v2 name rule (`meat_in_name`) into the team's `diet_rules` (separate change, needs approval)
- [ ] Optional: GitHub Actions job that runs `docker build` on each push

## Done
- 2026-11-16: `git init` (branch `main`, repo-only identity Ansh Kanungo <anshkanungo17@gmail.com>), first commit (13 files; `.venv/`, `output/`, `*.tar`, caches ignored; secret scan clean), remote `origin` = https://github.com/Anshkanungo/mlops-docker-lab.git. Not pushed
- 2026-11-16: README (what changed vs the original lab, run steps, verification table, lessons, limitations)
- 2026-11-16: Verified: 43/43 tests locally (Python 3.12, pytest 9.2.0) and inside `docker build`; `docker run -v $PWD/output:/app/output` → 3 files, 7 non-veg / 5 vegan / 5 veg, agreement 1.0; runs as uid 1000; runtime image has no tests/pytest; broken-rule copy fails the build with no image; bad input → exit 1; image 203 MB vs `python:3.10` base 1.61 GB; `docker save` (42 MB tar) → `docker rmi` → `docker load` → same results
- 2026-11-16: `Dockerfile` (multi-stage base → test → runtime, `python:3.12-slim`, non-root, ENTRYPOINT + CMD, VOLUME), `.dockerignore`, `.gitignore`, `requirements-dev.txt`
- 2026-11-16: `src/classify.py` entry point (validate → classify → write `validation.json`, `products_classified.json`, `diet_metrics.json`; exit 1 on bad records/duplicates) and tests (`tests/test_diet_rules.py`, `tests/test_classify.py`)
- 2026-11-16: Diet rules v2: product name is evidence (fixes Oscar Mayer Original Bacon → non-vegetarian), plant-based name markers, ingredients still win; `classify(evidence, name=None)` keeps v1 behaviour without a name
- 2026-11-16: Created `docker_lab1/`, copied the DVC lab's v2 data (17 products) and rules

## Decisions
- Lab choice: Docker_Labs/Lab1, the fastest remaining lab with a real repo as output (Ansh's call, after the due date had passed).
- Model: Pantry Path diet classifier instead of Iris RandomForest (Ansh's call), so all four labs tell one story.
- Fixed the DVC lab's known bacon bug as the "model change" (agreement 94.1% → 100%).
- Tests run inside `docker build`; a marker file copied from the test stage stops BuildKit from skipping it.
- Data baked into the image for reproducibility; a mounted `--input` can override it.
- No runtime dependencies (stdlib only), so the runtime stage has no `pip install`.
- The original lab image wasn't built for comparison: the permission check blocked running the downloaded Dockerfile, so its base image `python:3.10` stands in (a lower bound).

## Open questions
- Is a late submission accepted for Lab Assignment 4?
