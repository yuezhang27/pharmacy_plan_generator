#!/bin/bash
# Build Lambda deployment packages with dependencies
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$TERRAFORM_DIR/build"
LAMBDAS_DIR="$TERRAFORM_DIR/lambdas"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

for name in create_order generate_careplan get_order; do
  echo "Building $name..."
  dir="$LAMBDAS_DIR/$name"
  tmp="$BUILD_DIR/${name}_tmp"
  rm -rf "$tmp"
  mkdir -p "$tmp"
  cp "$dir/index.py" "$tmp/"
  pip install -q -r "$dir/requirements.txt" -t "$tmp/"
  cd "$tmp"
  zip -rq "$BUILD_DIR/${name}.zip" .
  cd - > /dev/null
  rm -rf "$tmp"
done

echo "Done. Zips in $BUILD_DIR"
