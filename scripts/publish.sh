#!/bin/bash
# Publish deep-coder to PyPI.
#
# Prerequisites:
#   pip install build twine
#
# Usage:
#   ./scripts/publish.sh          # publish to PyPI
#   ./scripts/publish.sh test     # publish to TestPyPI first
#
# Authentication (pick one):
#   export TWINE_USERNAME=__token__
#   export TWINE_PASSWORD=pypi-xxx...
#   — or —
#   Create ~/.pypirc with credentials
#   — or —
#   Use keyring (pip install keyring)

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "==> Cleaning old builds..."
rm -rf dist/ build/ *.egg-info

echo "==> Building wheel + sdist..."
python -m build

echo "==> Built artifacts:"
ls -lh dist/

if [[ "${1:-}" == "test" ]]; then
    echo "==> Uploading to TestPyPI..."
    twine upload --repository testpypi dist/*
    echo ""
    echo "Install from TestPyPI:"
    echo "  pip install --index-url https://test.pypi.org/simple/ deep-coder"
else
    echo "==> Uploading to PyPI..."
    twine upload dist/*
    echo ""
    echo "Install:"
    echo "  pip install deep-coder"
fi

echo "==> Done!"
