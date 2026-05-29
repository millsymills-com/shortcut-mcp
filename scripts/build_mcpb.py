"""Build the MCPB bundle (.mcpb) and its MCP-registry server.json.

The bundle is a UV-runtime MCPB: it ships the source plus pyproject.toml/uv.lock,
and the host installs dependencies with uv at runtime. server.json points the MCP
registry at the .mcpb attached to a GitHub release and pins its SHA-256.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_SRC = REPO_ROOT / "mcpb" / "manifest.json"
BUNDLE_PAYLOAD = ("pyproject.toml", "uv.lock", "README.md", "LICENSE", "src")
SERVER_NAME = "io.github.millsymills-com/shortcut-mcp"
RELEASE_URL = "https://github.com/millsymills-com/shortcut-mcp/releases/download/v{version}/shortcut-mcp.mcpb"
SERVER_SCHEMA = "https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json"


def project_version() -> str:
    """Read the single-sourced version from pyproject.toml."""
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    return data["project"]["version"]


def stage_bundle(stage_dir: Path, version: str) -> None:
    """Copy the manifest (version-synced) and payload into a clean staging dir."""
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    stage_dir.mkdir(parents=True)

    manifest = json.loads(MANIFEST_SRC.read_text())
    manifest["version"] = version
    (stage_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    for name in BUNDLE_PAYLOAD:
        source = REPO_ROOT / name
        target = stage_dir / name
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, target)


def pack(stage_dir: Path, output: Path) -> None:
    """Invoke the mcpb CLI to validate the manifest and produce the .mcpb."""
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["npx", "--yes", "@anthropic-ai/mcpb", "pack", str(stage_dir), str(output)],
        check=True,
        cwd=REPO_ROOT,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_server_json(version: str, digest: str) -> dict[str, object]:
    return {
        "$schema": SERVER_SCHEMA,
        "name": SERVER_NAME,
        "title": "Shortcut",
        "description": "FastMCP server for the Shortcut REST API (read, write, and destructive tiers).",
        "version": version,
        "packages": [
            {
                "registryType": "mcpb",
                "identifier": RELEASE_URL.format(version=version),
                "fileSha256": digest,
                "transport": {"type": "stdio"},
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the MCPB bundle and server.json.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist", help="output directory")
    args = parser.parse_args()

    version = project_version()
    out_dir: Path = args.output
    stage_dir = out_dir / "mcpb-stage"
    bundle = out_dir / "shortcut-mcp.mcpb"

    stage_bundle(stage_dir, version)
    pack(stage_dir, bundle)
    shutil.rmtree(stage_dir)

    digest = sha256(bundle)
    server_json = out_dir / "server.json"
    server_json.write_text(json.dumps(render_server_json(version, digest), indent=2) + "\n")

    print(f"bundle:  {bundle}")
    print(f"sha256:  {digest}")
    print(f"server:  {server_json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
