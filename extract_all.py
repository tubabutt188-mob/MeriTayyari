"""
OCR Extraction — All Subjects (Day 1, RAG pipeline step 1)
============================================================
Runs Tesseract OCR on every past-paper image under data/past_papers/,
extracts metadata (grade, subject, year, group, medium) from the
filename, and saves everything into one structured JSONL file:

    data/extracted_papers.jsonl

Each line is one JSON object:
    {
        "grade": "9th", "subject": "physics", "year": "2024",
        "group": "I", "medium": "English", "type": "Objective",
        "filename": "...", "text": "<ocr extracted text>"
    }

Requirements:
    pip install pytesseract pillow

Usage:
    python extract_all.py
"""

import os
import re
import json
from pathlib import Path

import pytesseract
from PIL import Image

# ---- Set this to your actual Tesseract install path ----
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\tubab\AppData\Local\Tesseract-OCR\tesseract.exe"

ROOT = Path("data/past_papers")
OUTPUT_FILE = Path("data/extracted_papers.jsonl")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def parse_metadata(filepath: Path) -> dict:
    """Extract grade, subject, year, group, medium, type from folder structure + filename."""
    # folder structure: data/past_papers/class_9/physics/filename.jpg
    parts = filepath.parts
    grade_folder = next((p for p in parts if p.startswith("class_")), "unknown")
    grade = grade_folder.replace("class_", "") + "th" if grade_folder != "unknown" else "unknown"
    subject = filepath.parent.name

    name = filepath.stem  # filename without extension

    year_match = re.search(r"(20\d{2}|19\d{2})", name)
    year = year_match.group(1) if year_match else "unknown"

    group_match = re.search(r"Group[- ]?(I{1,2}|1|2)", name, re.IGNORECASE)
    group = group_match.group(1) if group_match else "unknown"

    medium = "Urdu" if "urdu" in name.lower() else ("English" if "english" in name.lower() else "unknown")

    paper_type = "Objective" if "objective" in name.lower() else (
        "Subjective" if "subjective" in name.lower() else "unknown"
    )

    return {
        "grade": grade,
        "subject": subject,
        "year": year,
        "group": group,
        "medium": medium,
        "type": paper_type,
    }


def ocr_image(image_path: Path, lang: str = "eng+urd") -> str:
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang=lang)


def main():
    if not ROOT.exists():
        print(f"Folder not found: {ROOT.resolve()}")
        return

    images = [p for p in ROOT.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Found {len(images)} images to process.\n")

    # Resume support: skip filenames already in the output file
    already_done = set()
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    already_done.add(json.loads(line)["filename"])
                except Exception:
                    pass

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        for i, img_path in enumerate(images, 1):
            filename = str(img_path)
            if filename in already_done:
                print(f"[{i}/{len(images)}] SKIP (already processed): {img_path.name}")
                continue

            try:
                text = ocr_image(img_path)
                meta = parse_metadata(img_path)
                meta["filename"] = filename
                meta["text"] = text.strip()

                out.write(json.dumps(meta, ensure_ascii=False) + "\n")
                out.flush()

                char_count = len(text.strip())
                status = "OK" if char_count > 50 else "LOW TEXT"
                print(f"[{i}/{len(images)}] {status} ({char_count} chars): {img_path.name}")

            except Exception as e:
                print(f"[{i}/{len(images)}] ERROR on {img_path.name}: {e}")

    print(f"\nDone. Extracted data saved to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
