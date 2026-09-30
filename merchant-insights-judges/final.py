#!/usr/bin/env python3
"""Open the Kraków-metro prototype. Does not rebuild the marts.

    python final.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ["INSIGHTS_DATASET"] = "Final"
os.chdir(ROOT)
raise SystemExit(
    subprocess.call(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "app/Home.py",
            "--server.port",
            "8502",
            "--server.headless",
            "true",
            "--server.address",
            "127.0.0.1",
        ],
        cwd=ROOT,
    )
)
