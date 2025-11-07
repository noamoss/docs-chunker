#!/bin/bash
# Script to remove accidentally committed files from git tracking
# This removes files from git index but keeps them on disk

set -e

echo "🧹 Cleaning up accidentally committed files..."

# Remove .venv/ from git tracking
if git ls-files --error-unmatch .venv/ >/dev/null 2>&1; then
    echo "Removing .venv/ from git tracking..."
    git rm -r --cached .venv/
    echo "✅ Removed .venv/"
else
    echo "ℹ️  .venv/ not tracked in git"
fi

# Remove build artifacts
if git ls-files --error-unmatch src/docs_chunker.egg-info/ >/dev/null 2>&1; then
    echo "Removing build artifacts (src/docs_chunker.egg-info/) from git tracking..."
    git rm -r --cached src/docs_chunker.egg-info/
    echo "✅ Removed build artifacts"
else
    echo "ℹ️  Build artifacts not tracked in git"
fi

# Remove output files (but keep the directory structure)
if git ls-files --error-unmatch output/ >/dev/null 2>&1; then
    echo "Removing output/ files from git tracking..."
    git rm -r --cached output/
    echo "✅ Removed output/ files"
else
    echo "ℹ️  output/ files not tracked in git"
fi

# Remove test documents (optional - uncomment if needed)
# if git ls-files --error-unmatch documents/*.docx >/dev/null 2>&1; then
#     echo "Removing test documents from git tracking..."
#     git rm --cached documents/*.docx
#     echo "✅ Removed test documents"
# fi

echo ""
echo "✨ Cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Review the changes: git status"
echo "2. Commit the cleanup: git commit -m 'chore: remove accidentally committed files from version control'"
echo "3. Verify .gitignore is working: git status --ignored"
