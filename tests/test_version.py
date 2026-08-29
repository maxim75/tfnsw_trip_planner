"""The package version is written in two files; they must agree.

A release is cut by bumping the version and merging: publish.yml runs on every
merged PR and uploads with ``skip-existing``, so a merge that forgets the bump
publishes nothing at all. That makes the version string load-bearing, and it
lives in both pyproject.toml and __init__.py.
"""
import re
from pathlib import Path

import tfnsw_trip_planner

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def pyproject_version() -> str:
    # Parsed by regex rather than tomllib, which is 3.11+; this package
    # supports 3.9. Matches the first `version = "..."` under [project].
    text = PYPROJECT.read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert match, "no version found in pyproject.toml"
    return match.group(1)


def test_package_version_matches_pyproject():
    assert tfnsw_trip_planner.__version__ == pyproject_version()


def test_version_looks_like_a_release():
    assert re.fullmatch(r"\d+\.\d+\.\d+", pyproject_version())
