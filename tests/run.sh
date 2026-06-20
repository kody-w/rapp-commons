#!/bin/bash
# Run the full RAPP Commons acceptance suite. The browser tests need the commons served
# (default http://localhost:8777). Exit 0 iff ALL green.
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/.brainstem/venv/bin/python}"
fail=0
echo "== data / engine tests =="
"$PY" tests/test_data.py || fail=1
echo; echo "== commons.html acceptance (headless browser) =="
"$PY" tests/test_commons.py || fail=1
echo
if [ $fail -eq 0 ]; then echo "ALL GREEN -- ready to publish"; else echo "RED -- keep building until green"; fi
exit $fail
