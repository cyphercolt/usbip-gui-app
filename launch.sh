#!/bin/bash

# Change to the directory where the script is located
# dirname "$0" gets the directory of the script file itself
cd "$(dirname "$0")"

# Activate the virtual environment
source venv/bin/activate

# Launch the Python script
python src/main.py
