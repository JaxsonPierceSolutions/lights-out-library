#!/bin/sh
set -e
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed on this computer. Install it (for example: sudo apt install python3, or brew install python), then run this again." >&2
  exit 1
fi
here=$(cd "$(dirname "$0")" && pwd)
PYTHONPATH="$here/src${PYTHONPATH:+:$PYTHONPATH}" exec python3 -m lightsout "$@"
