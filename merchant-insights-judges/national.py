#!/usr/bin/env python3
"""Build the national marts.

This is the long run: about an hour and a half on the sample file. The app the
judges open does not load this set. It uses the Kraków metro build from final.py.

    python national.py --file /path/to/data.parquet
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if "--file" not in sys.argv:
    print("Usage: python national.py --file /path/to/data.parquet", file=sys.stderr)
    raise SystemExit(2)
raise SystemExit(
    subprocess.call(
        [sys.executable, str(ROOT / "pipeline" / "build_marts.py"), *sys.argv[1:]],
        cwd=ROOT,
    )
)
