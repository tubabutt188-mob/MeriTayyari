"""
Organize / Verify / Rename Past Papers
=======================================
Ye script data/past_papers/ ke andar sab classes aur subjects check karti hai:

1. VERIFY   — har image file ko khol kar check karti hai ke woh corrupt/incomplete
              to nahi (Pillow se). Corrupt files ko delete NAHI karti — sirf
              "corrupt" folder mein move kar deti hai taake aap khud dekh kar
              faisla karein (dobara download karna hai ya nahi).

2. DEDUPE   — content ke hisab se (MD5 hash), na ke sirf naam ke hisab se,
              exact duplicate images dhoondti hai. Pehli copy rakhti hai,
              baaki duplicates ko "duplicates" folder mein move kar deti hai
              (delete nahi karti — safe rehta hai).

3. RENAME   — sab filenames ko ek consistent format mein normalize karti hai:
              spaces -> hyphens, multiple hyphens -> single, trailing/leading
              hyphens hata deti hai, extension lowercase kar deti hai.
              Asal descriptive naam (Year, Subject, Group, Medium waghera)
              barqarar rehta hai — sirf formatting consistent hoti hai.

4. REPORT   — end mein ek CSV report (papers_report.csv) banati hai jisme
              har class/subject ke liye: total files, total size, kitne
              corrupt mile, kitne duplicate mile — sab kuch.

Requirements:
    pip install Pillow

Usage:
    python organize_papers.py
    (BASE_DIR neeche configure karein agar folder structure alag hai)
"""

import os
import re
import csv
import hashlib
import shutil
import sys

try:
    from PIL import Image
except ImportError:
    print("Missing package. Run: pip install Pillow")
    sys.exit(1)

# -----------------------------------------------------------------------
# Root folder jahan sab class_9/10/11/12 subfolders hain.
# -----------------------------------------------------------------------
BASE_DIR = "data/past_papers"

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")


def normalize_filename(filename: str) -> str:
    """Spaces/underscores -> single hyphens, collapse repeats, lowercase extension."""
    name, ext = os.path.splitext(filename)
    ext = ext.lower()
    # Replace spaces and underscores with hyphens
    name = re.sub(r"[\s_]+", "-", name)
    # Collapse multiple hyphens into one
    name = re.sub(r"-{2,}", "-", name)
    # Trim leading/trailing hyphens
    name = name.strip("-")
    return f"{name}{ext}"


def file_md5(filepath: str, chunk_size: int = 65536) -> str:
    """Compute MD5 hash of a file's contents (for exact-duplicate detection)."""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_image(filepath: str) -> bool:
    """Return True if the file opens and verifies correctly as an image."""
    try:
        with Image.open(filepath) as img:
            img.verify()
        return True
    except Exception:
        return False


def process_subject_folder(folder_path: str, rel_label: str, report_rows: list):
    """Verify, dedupe, and rename all images inside one subject folder."""
    if not os.path.isdir(folder_path):
        return

    corrupt_dir = os.path.join(folder_path, "_corrupt")
    dup_dir = os.path.join(folder_path, "_duplicates")

    files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(IMAGE_EXTENSIONS) and os.path.isfile(os.path.join(folder_path, f))
    ]

    total_size = 0
    corrupt_count = 0
    duplicate_count = 0
    seen_hashes = {}  # hash -> filename (first copy seen)

    for filename in files:
        filepath = os.path.join(folder_path, filename)

        # 1. Verify
        if not is_valid_image(filepath):
            os.makedirs(corrupt_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(corrupt_dir, filename))
            corrupt_count += 1
            print(f"  [CORRUPT] {rel_label}/{filename} -> moved to _corrupt/")
            continue

        # 2. Dedupe (by content hash)
        file_hash = file_md5(filepath)
        if file_hash in seen_hashes:
            os.makedirs(dup_dir, exist_ok=True)
            shutil.move(filepath, os.path.join(dup_dir, filename))
            duplicate_count += 1
            print(f"  [DUPLICATE] {rel_label}/{filename} -> moved to _duplicates/ "
                  f"(same as {seen_hashes[file_hash]})")
            continue
        seen_hashes[file_hash] = filename

        # 3. Rename to normalized form (only if it changes)
        new_filename = normalize_filename(filename)
        if new_filename != filename:
            new_filepath = os.path.join(folder_path, new_filename)
            if os.path.exists(new_filepath):
                # Extremely rare collision after normalization — keep original name
                new_filename = filename
            else:
                os.rename(filepath, new_filepath)
                filepath = new_filepath

        total_size += os.path.getsize(filepath)

    kept_count = len(seen_hashes)
    report_rows.append({
        "folder": rel_label,
        "kept_files": kept_count,
        "corrupt_moved": corrupt_count,
        "duplicates_moved": duplicate_count,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    })


def main():
    if not os.path.isdir(BASE_DIR):
        print(f"BASE_DIR not found: {BASE_DIR}")
        print("Edit BASE_DIR at the top of this script to match your folder.")
        sys.exit(1)

    report_rows = []

    for class_folder in sorted(os.listdir(BASE_DIR)):
        class_path = os.path.join(BASE_DIR, class_folder)
        # Skip helper folders like _excluded_subjects (created by other scripts)
        # and anything else starting with "_" — these aren't actual class folders.
        if not os.path.isdir(class_path) or class_folder.startswith("_"):
            continue

        for subject_folder in sorted(os.listdir(class_path)):
            subject_path = os.path.join(class_path, subject_folder)
            if not os.path.isdir(subject_path):
                continue

            rel_label = f"{class_folder}/{subject_folder}"
            print(f"\n=== {rel_label} ===")
            process_subject_folder(subject_path, rel_label, report_rows)

    # Write CSV summary report
    report_path = os.path.join(BASE_DIR, "papers_report.csv")
    with open(report_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["folder", "kept_files", "corrupt_moved", "duplicates_moved", "total_size_mb"]
        )
        writer.writeheader()
        writer.writerows(report_rows)

    total_kept = sum(r["kept_files"] for r in report_rows)
    total_corrupt = sum(r["corrupt_moved"] for r in report_rows)
    total_dupes = sum(r["duplicates_moved"] for r in report_rows)

    print("\n" + "=" * 60)
    print(f"DONE. Report saved to: {report_path}")
    print(f"Total good files kept   : {total_kept}")
    print(f"Total corrupt (moved)   : {total_corrupt}")
    print(f"Total duplicates (moved): {total_dupes}")
    print("=" * 60)


if __name__ == "__main__":
    main()