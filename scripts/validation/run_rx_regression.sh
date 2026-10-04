#!/usr/bin/env bash
# Author: Miguel Simoes
# SPDX-FileCopyrightText: 2026 Miguel Simoes
# SPDX-License-Identifier: Apache-2.0
# Every attempted test has an explicit verdict; only a complete clean matrix passes.
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
PY=${PY:-$HOME/venvs/btle/bin/python}
exec "$PY" "$repo/scripts/validation/rx_regression.py" "$@"
