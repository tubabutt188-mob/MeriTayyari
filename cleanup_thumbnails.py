"""
Cleanup Script — Remove small/thumbnail images
================================================
Deletes any .jpg/.jpeg/.png files smaller than 20 KB inside
data/past_papers/ (recursively). These are the old manually-saved
thumbnails that never had real content — the real full-size papers
downloaded by bulk_download.py are all 200 KB+.

Usage:
    python cleanup_thumbnails.py
    (it will list what it WOULD delete first, then ask for confirmation)
"""

import os
from pathlib import Path

ROOT = Path("data/past_papers")
SIZE_THRESHOLD = 20_000  # bytes (20 KB)
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def find_small_images():
    small_files = []
    for path in ROOT.rglob("*"):
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
            if path.stat().st_size < SIZE_THRESHOLD:
                small_files.append(path)
    return small_files


def main():
    if not ROOT.exists():
        print(f"Folder not found: {ROOT.resolve()}")
        return

    small_files = find_small_images()

    if not small_files:
        print("No small/thumbnail images found. Nothing to clean up.")
        return

    print(f"Found {len(small_files)} small images (under {SIZE_THRESHOLD // 1000} KB):\n")
    for f in small_files:
        size = f.stat().st_size
        print(f"  {size:>6} bytes  -  {f}")

    answer = input(f"\nDelete all {len(small_files)} files above? (yes/no): ").strip().lower()

    if answer == "yes":
        for f in small_files:
            f.unlink()
        print(f"\nDeleted {len(small_files)} files.")
    else:
        print("\nCancelled. No files were deleted.")


if __name__ == "__main__":
    main()
