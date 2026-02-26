#!/usr/bin/env python3
"""Build Lambda deployment packages. Run from terraform/ directory."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TERRAFORM_DIR = SCRIPT_DIR.parent
LAMBDAS = ["create_order", "generate_careplan", "get_order"]
BUILD_DIR = TERRAFORM_DIR / "build"


def main():
    BUILD_DIR.mkdir(exist_ok=True)
    for name in LAMBDAS:
        print(f"Building {name}...")
        src = TERRAFORM_DIR / "lambdas" / name
        tmp = BUILD_DIR / f"{name}_tmp"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir()
        shutil.copy(src / "index.py", tmp)
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(src / "requirements.txt"), "-t", str(tmp)],
            check=True,
        )
        zip_path = BUILD_DIR / f"{name}.zip"
        if zip_path.exists():
            zip_path.unlink()
        shutil.make_archive(str(BUILD_DIR / name), "zip", tmp)
        shutil.rmtree(tmp)
    print(f"Done. Zips in {BUILD_DIR}")


if __name__ == "__main__":
    main()
