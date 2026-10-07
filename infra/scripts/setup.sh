#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
python3 infra/scripts/setup_env.py
