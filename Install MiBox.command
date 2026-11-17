#!/bin/bash
cd "$(dirname "$0")" || exit 1
python3 setup_mibox.py
echo
read -r -p "Press Enter to close this window. "
