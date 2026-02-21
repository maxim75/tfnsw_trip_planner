# Deployment Guide - TfNSW Trip Planner

This guide explains how to build and deploy the `tfnsw-trip-planner` package to PyPI.

## Prerequisites

1. **PyPI Account**
   - Create an account at [PyPI](https://pypi.org/account/register/)
   - Verify your email address
   - Enable 2FA (required for uploads)

2. **API Token**
   - Generate an API token at [PyPI Account Settings](https://pypi.org/manage/account/token/)
   - Save the token - you'll only see it once!
   - Name it something like "tfnsw-trip-planner-publish"

3. **Install Build Tools**
   ```bash
   pip install --upgrade build twine
   ```

## Setup Authentication

### Option 1: Using an API Token (Recommended)

Configure `~/.pypirc` with your token:

```ini
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Replace `pypi-xxxxxxxxx...` with your actual PyPI API token.

### Option 2: Using keyring (More Secure)

```bash
pip install keyring
keyring set https://upload.pypi.org/legacy/ your-username
# Enter your API token when prompted
```

## Building the Package

### 1. Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ *.egg-info
```

### 2. Build Source Distribution and Wheels

```bash
python -m build
```

This creates:
- `dist/tfnsw_trip_planner-1.0.0.tar.gz` (source distribution)
- `dist/tfnsw_trip_planner-1.0.0-py3-none-any.whl` (wheel)

### 3. Verify the Build

```bash
twine check dist/*
```

This validates the package structure and metadata.

## Testing Before Upload

### 1. Upload to TestPyPI

TestPyPI is a separate instance of PyPI for testing:

```bash
twine upload --repository testpypi dist/*
```

### 2. Install from TestPyPI

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ tfnsw-trip-planner
```

### 3. Verify Installation

```bash
python -c "import tfnsw_trip_planner; print(tfnsw_trip_planner.__version__)"
```

## Deploying to PyPI

Once you've verified everything works on TestPyPI:

### 1. Upload to Production PyPI

```bash
twine upload dist/*
```

### 2. Verify on PyPI

Visit https://pypi.org/project/tfnsw-trip-planner/ to see your package.

### 3. Install from PyPI

```bash
pip install tfnsw-trip-planner
```

## Version Management

When you need to release a new version:

### 1. Update Version Numbers

Edit `tfnsw_trip_planner/__init__.py`:
```python
__version__ = "1.0.1"  # Increment this
```

Edit `pyproject.toml`:
```toml
[project]
version = "1.0.1"  # Keep in sync with __init__.py
```

### 2. Update CHANGELOG (Optional but Recommended)

Document what changed in the new version.

### 3. Clean, Build, and Upload

```bash
rm -rf build/ dist/ *.egg-info
python -m build
twine upload dist/*
```

## Common Issues

### "HTTPError: 400 Bad Request"

- Check your `pyproject.toml` for valid metadata
- Ensure version numbers are in sync
- Verify README.md has proper formatting

### "403 Forbidden"

- Check your API token has write permissions
- Verify the package name isn't already taken
- Ensure you're authenticated correctly

### "Upload failed"

- Run `twine check dist/*` to validate the package
- Check the PyPI server status at https://status.python.org/
- Try uploading to TestPyPI first to debug

## Automated Deployment (Optional)

### GitHub Actions

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  pypi-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

Configure PyPI trusted publishers in your PyPI account settings to allow automated uploads from GitHub.

## Post-Release Checklist

- [ ] Verify package appears on PyPI
- [ ] Test installation in a clean virtual environment
- [ ] Check documentation renders correctly on PyPI
- [ ] Update GitHub releases page
- [ ] Announce the release (if applicable)

## Additional Resources

- [PyPI Packaging Tutorial](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Python Packaging User Guide](https://packaging.python.org/)