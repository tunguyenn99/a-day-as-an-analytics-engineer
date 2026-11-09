"""Load literal KEY=value entries without shell evaluation or secret output."""

import os
from pathlib import Path
import re
import sys


def read_env(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError("Expected literal KEY=value environment entry")
        values[key] = value
    return values


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m scripts.with_env command [arguments]")
    os.execvpe(sys.argv[1], sys.argv[1:], os.environ | read_env(".env"))
