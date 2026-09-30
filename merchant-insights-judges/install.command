#!/usr/bin/env bash
# One-time setup for a judge. Creates .venv in this folder and installs the
# pinned packages. .venv is not committed.
set -euo pipefail
cd "$(dirname "$0")"
echo "Installing Merchant Insights. This takes about a minute, once."
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import streamlit, duckdb, pandas, pyarrow, plotly; print('pinned-ok')"
echo
echo "Done."
if [[ -f final.py ]]; then
  echo "Start the demo with: .venv/bin/python final.py"
else
  echo "Start the app with: .venv/bin/python -m streamlit run app/Home.py --server.address 127.0.0.1"
fi
