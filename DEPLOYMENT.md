# Deployment Guide - TfNSW Trip Planner

Releases go to [PyPI](https://pypi.org/project/tfnsw-trip-planner/) automatically
when a pull request is merged into `main`.

## How a release happens

1. Bump the version in **both** places (a test fails if they disagree):
   - `pyproject.toml` → `[project] version`
   - `tfnsw_trip_planner/__init__.py` → `__version__`
2. Open a PR. The **Tests** workflow runs pytest on Python 3.10–3.15, ruff, mypy
   and a build check (`twine check --strict`, `py.typed` present in the wheel).
3. Merge it. The **Publish to PyPI** workflow (`.github/workflows/publish.yml`)
   builds the sdist and wheel and uploads them using
   [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC),
   so no API token is stored in the repository.

A merged PR that does not bump the version publishes nothing: the upload runs
with `skip-existing`, so an already-published version is a no-op, not a failure.

### One-time setup (already done for this repo)

- On PyPI, the project has a trusted publisher for repository
  `maxim75/tfnsw_trip_planner`, workflow `publish.yml`, environment `pypi`.
- On GitHub, an environment named `pypi` exists (Settings → Environments). Add
  required reviewers there if you want a manual approval step before upload.

## Building locally

```bash
pip install --upgrade build twine
rm -rf build/ dist/ *.egg-info
python -m build
twine check --strict dist/*
```

This creates `dist/tfnsw_trip_planner-<version>.tar.gz` and
`dist/tfnsw_trip_planner-<version>-py3-none-any.whl`.

## Manual upload (fallback)

`./build_and_publish.sh test` runs the tests, builds, and uploads to TestPyPI;
`./build_and_publish.sh prod` uploads to PyPI after a confirmation prompt. Both
use `twine`, which needs a PyPI API token in `~/.pypirc` or a keyring:

```ini
[pypi]
username = __token__
password = pypi-...
```

Install from TestPyPI to check a build:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ tfnsw-trip-planner
python -c "import tfnsw_trip_planner; print(tfnsw_trip_planner.__version__)"
```

## Common issues

- **`400 File already exists`** — that version is already on PyPI. Versions
  cannot be reused; bump it.
- **`403 Forbidden` / `invalid-publisher`** from the workflow — the trusted
  publisher settings on PyPI don't match the repository, workflow file name or
  environment name above.
- **`twine check` fails** — usually README Markdown that PyPI can't render.
