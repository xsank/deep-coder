#!/bin/bash
# One-click release: bump version → commit → tag → push → PyPI + GitHub Release.
#
# Usage:
#   ./scripts/release.sh 0.1.0
#
# What happens:
#   1. Updates version in pyproject.toml and deep_coder/__init__.py (if changed)
#   2. Commits: "Release v0.1.0" (skipped if version unchanged)
#   3. Tags: v0.1.0
#   4. Pushes commit + tag to origin
#   5. Builds wheel and uploads to PyPI
#   6. Tag push triggers release.yml → GitHub Release + binaries

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <version>"
    echo "  e.g. $0 0.1.0"
    exit 1
fi

VERSION="$1"

if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version must be in X.Y.Z format (got: $VERSION)"
    exit 1
fi

cd "$(git rev-parse --show-toplevel)"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree is not clean. Commit or stash changes first."
    exit 1
fi

if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: tag v$VERSION already exists."
    exit 1
fi

CURRENT=$(python -c "from deep_coder import __version__; print(__version__)")
echo "Releasing: v$CURRENT -> v$VERSION"

sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" pyproject.toml
sed -i '' "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" deep_coder/__init__.py

NEW_TOML=$(grep '^version' pyproject.toml | head -1)
NEW_INIT=$(grep '__version__' deep_coder/__init__.py)
echo "  pyproject.toml: $NEW_TOML"
echo "  __init__.py:    $NEW_INIT"

if [[ -n "$(git diff pyproject.toml deep_coder/__init__.py)" ]]; then
    git add pyproject.toml deep_coder/__init__.py
    git commit -m "Release v$VERSION"
fi

git tag "v$VERSION"

echo ""
echo "Pushing to origin..."
git push origin main
git push origin "v$VERSION"

echo ""
echo "==> Building wheel + sdist..."
rm -rf dist/ build/ *.egg-info
python -m build

echo ""
echo "==> Uploading to PyPI..."
twine upload dist/*

echo ""
echo "Done! v$VERSION published."
echo "  PyPI: https://pypi.org/project/deep-coder/$VERSION/"
echo "  GitHub Actions: https://github.com/xsank/deep-coder/actions"
