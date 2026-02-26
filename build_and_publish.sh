#!/bin/bash
# Build and Publish Script for tfnsw-trip-planner
# Usage: ./build_and_publish.sh [test|prod]

set -e  # Exit on error

MODE="${1:-test}"  # Default to testpypi

echo "=========================================="
echo "TfNSW Trip Planner - Build & Publish"
echo "=========================================="
echo ""

# Run unit tests
echo "🧪 Running unit tests..."
python -m pytest tests/ -v
echo "✓ All tests passed"
echo ""

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info
echo "✓ Clean complete"
echo ""

# Build the package
echo "🔨 Building package..."
python -m build
echo "✓ Build complete"
echo ""

# Check the package
echo "🔍 Validating package..."
twine check dist/*
echo "✓ Validation passed"
echo ""

# Ask for confirmation
echo "📦 Packages to upload:"
ls -lh dist/
echo ""

if [ "$MODE" == "test" ]; then
    echo "🚀 Uploading to TestPyPI..."
    twine upload --repository testpypi dist/*
    echo ""
    echo "✓ Uploaded to TestPyPI!"
    echo ""
    echo "To test install:"
    echo "  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ tfnsw-trip-planner"
else
    echo "⚠️  WARNING: You are about to upload to PRODUCTION PyPI!"
    echo ""
    read -p "Are you sure? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        echo "🚀 Uploading to PyPI..."
        twine upload dist/*
        echo ""
        echo "✓ Uploaded to PyPI!"
        echo ""
        echo "Package URL: https://pypi.org/project/tfnsw-trip-planner/"
    else
        echo "❌ Upload cancelled"
        exit 0
    fi
fi

echo ""
echo "=========================================="
echo "✓ All done!"
echo "=========================================="