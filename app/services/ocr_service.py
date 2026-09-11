"""
OCR Service — Past paper PDFs se text extract karta hai.

Usage:
    python ocr_service.py data/past_papers/physics_2023.pdf

Note: Ye Tesseract OCR use karta hai jo free hai lekin scanned/handwritten
papers pe accuracy kam ho sakti hai. Clean scanned PDFs pe best results milte hain.
"""

import sys
import os
import json
from pdf2image import convert_from_path
import pytesseract


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Har page ko image mein convert karke OCR se text nikalta hai.
    Returns: list of {"page": page_number, "text": extracted_text}
    """
    print(f"Processing: {pdf_path}")
    pages = convert_from_path(pdf_path, dpi=300)  # 300 dpi = better OCR accuracy

    results = []
    for i, page_image in enumerate(pages, start=1):
        text = pytesseract.image_to_string(page_image, lang="eng")
        results.append({"page": i, "text": text.strip()})
        print(f"  Page {i}: {len(text)} characters extracted")

    return results


def save_extracted_text(pdf_path: str, output_dir: str = "data/processed"):
    """Extract karke JSON file mein save karta hai for next step (chunking)."""
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{filename}.json")

    extracted = extract_text_from_pdf(pdf_path)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ocr_service.py <path_to_pdf>")
        sys.exit(1)

    save_extracted_text(sys.argv[1])
