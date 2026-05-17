#!/bin/bash
cd "$(dirname "$0")"
if [ -x "./venv/bin/python" ]; then
    ./venv/bin/python src/main.py
else
    ./venv/Scripts/python.exe src/main.py
fi
