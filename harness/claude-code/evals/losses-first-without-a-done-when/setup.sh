#!/bin/bash
# Put the program's RULES.md where the brief says it is: program/RULES.md in the run's working folder.
set -euo pipefail
mkdir -p program
cp "$(dirname "${BASH_SOURCE[0]}")/program/RULES.md" program/RULES.md
