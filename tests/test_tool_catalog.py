"""The README tool catalog must match the live tool registry."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def test_readme_tool_catalog_is_in_sync() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_tool_catalog.py", "--check"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
