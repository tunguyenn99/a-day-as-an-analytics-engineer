"""Create and verify a source/documentation ZIP using an explicit file allowlist."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "a-day-as-an-analytics-engineer"
FILES = (
    "README.md",
    "LICENSE",
    "Makefile",
    "Dockerfile",
    "compose.yml",
    "compose.local.yml",
    ".dockerignore",
    ".gitignore",
    ".sqlfluff",
    ".env.example",
    ".env.supabase.example",
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
)
DIRECTORIES = (
    ".github",
    "dags",
    "dbt",
    "docs",
    "ingestion",
    "observability",
    "sample_data",
    "scripts",
    "tests",
    "tools",
)
EXCLUDED = {
    "target",
    "logs",
    "dbt_packages",
    "__pycache__",
    "node_modules",
    ".venv",
    ".git",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def secret_values():
    path = ROOT / ".env"
    values = []
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, value = line.partition("=")
            if sep and any(
                word in key.upper()
                for word in ("PASSWORD", "SECRET", "TOKEN", "JWT", "ACCESS_KEY")
            ):
                if len(value) >= 8 and value not in (
                    "local-only",
                    "local-only-change-me",
                ):
                    values.append(value.encode())
    return values


def source_files():
    paths = [ROOT / name for name in FILES]
    for directory in DIRECTORIES:
        paths.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file() and not EXCLUDED.intersection(p.relative_to(ROOT).parts)
        )
    for path in sorted(set(paths)):
        if path.is_symlink() or not path.is_file():
            raise ValueError("Missing or unsupported package source")
        yield path


def verify(path):
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive paths")
        for name in names:
            parts = PurePosixPath(name).parts
            if ".." in parts or PurePosixPath(name).is_absolute() or parts[0] != NAME:
                raise ValueError("Invalid package path")
        manifest_name = NAME + "/PACKAGE_MANIFEST.json"
        manifest = json.loads(archive.read(manifest_name))
        expected = {NAME + "/" + item["path"] for item in manifest["files"]} | {
            manifest_name
        }
        if set(names) != expected:
            raise ValueError("Package inventory mismatch")
        for item in manifest["files"]:
            data = archive.read(NAME + "/" + item["path"])
            if digest(data) != item["sha256"] or len(data) != item["bytes"]:
                raise ValueError("Package checksum mismatch")
            if any(value in data for value in secret_values()):
                raise ValueError("Local secret found in package; refusing release")
    return len(manifest["files"])


def build():
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    path = output / (NAME + ".zip")
    entries = []
    secrets = secret_values()
    for source in source_files():
        relative = source.relative_to(ROOT).as_posix()
        data = source.read_bytes()
        if any(value in data for value in secrets):
            raise ValueError("Local secret found in source; refusing release")
        entries.append((relative, data))
    manifest = {
        "format": 1,
        "name": NAME,
        "contents": "Source, configuration templates, synthetic fixture, documentation and screenshots. No databases, credentials, venvs or raw source exports.",
        "files": [
            {"path": name, "bytes": len(data), "sha256": digest(data)}
            for name, data in entries
        ],
    }
    entries.append(
        ("PACKAGE_MANIFEST.json", (json.dumps(manifest, indent=2) + "\n").encode())
    )
    temporary = path.with_suffix(".zip.tmp")
    try:
        with zipfile.ZipFile(
            temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as archive:
            for name, data in entries:
                info = zipfile.ZipInfo(
                    NAME + "/" + name, date_time=(2020, 1, 1, 0, 0, 0)
                )
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
        verify(temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    checksum = digest(path.read_bytes())
    path.with_suffix(".zip.sha256").write_text(checksum + "  " + path.name + "\n")
    print(
        f"Created {path.relative_to(ROOT)} ({len(entries) - 1} files, {path.stat().st_size:,} bytes)"
    )
    print("Verified file inventory, SHA-256, ZIP integrity and local-secret exclusion.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(f"Verified {verify(args.verify)} packaged files")
    else:
        build()
