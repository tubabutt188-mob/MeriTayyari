"""
Phase 1 — Chunk OCR Text Into Question-Level Pieces
=======================================================
Ye script data/extracted_papers.jsonl (extract_all.py ka output) padhti hai,
jisme har line EK POORE PAPER ka OCR text hota hai. Ye bohot bara chunk hai —
RAG ke liye behtar retrieval ke liye humein har SAWAL (question) ko alag
chunk banana hai.

Kya karti hai:
1. Har paper ke OCR text ko halka sa clean karti hai (extra whitespace,
   repeated blank lines waghera hatati hai)
2. Question numbers (Q1, Q.1, 1., (i), (ii) waghera) ke pattern pe text ko
   split karti hai
3. Har chunk ke saath wahi metadata (grade, subject, year, group, medium,
   type) attach karti hai jo poore paper ka tha
4. Bohot chhote chunks (jaise sirf "Q5" akela, koi text nahi) ko skip kar
   deti hai — wo useless hain
5. Result save karti hai: data/chunks.jsonl

IMPORTANT: Ye script data/extracted_papers.jsonl ke MUKAMMAL hone ke baad
chalani hai — agar OCR abhi chal rahi hai, to pehle usay khatam hone dein.

Usage:
    python chunk_papers.py
"""

import json
import re
from pathlib import Path

INPUT_FILE = Path("data/extracted_papers.jsonl")
OUTPUT_FILE = Path("data/chunks.jsonl")

# Minimum characters a chunk must have to be kept (filters out junk like a
# lone question number with no real text after OCR errors).
MIN_CHUNK_CHARS = 15

# Matches common question-number patterns seen in board exam papers:
#   "Q1", "Q.1", "Question 1", "(i)", "(ii)", "1.", "1)"
# NOTE: single-letter markers like "(a)", "(b)" are deliberately NOT matched
# here — those are usually MCQ answer options, not separate questions, and
# splitting on them would tear a multiple-choice question away from its
# options (leaving orphaned, meaningless fragments like "(a) Velocity").
QUESTION_SPLIT_RE = re.compile(
    r"""
    (?:^|\n)\s*
    (?:
        Q(?:uestion)?[\s.]*\d+          |   # Q1, Q.1, Question 1
        \(\s*[ivxIVX]+\s*\)             |   # (i), (ii), (iii)...
        \d+[\.\)]\s                          # 1.  or 1)
    )
    """,
    re.VERBOSE,
)


def clean_text(text: str) -> str:
    """Light cleanup of raw OCR text before chunking."""
    # Collapse 3+ blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse repeated spaces/tabs
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Strip trailing whitespace on each line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def split_into_questions(text: str) -> list:
    """Split cleaned OCR text into question-level chunks using QUESTION_SPLIT_RE."""
    matches = list(QUESTION_SPLIT_RE.finditer(text))

    if not matches:
        # No recognizable question markers — keep the whole thing as one chunk
        # (better than losing the content entirely).
        return [text] if len(text) >= MIN_CHUNK_CHARS else []

    chunks = []

    # Anything before the first match (e.g. paper header/instructions) —
    # usually not useful for Q&A retrieval, so we skip it rather than keep
    # it as a chunk on its own.
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()
        if len(chunk) >= MIN_CHUNK_CHARS:
            chunks.append(chunk)

    return chunks


def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE.resolve()}")
        print("Run extract_all.py first and let it finish completely.")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    total_papers = 0
    total_chunks = 0
    skipped_empty = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as infile, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

        for line in infile:
            line = line.strip()
            if not line:
                continue

            try:
                paper = json.loads(line)
            except json.JSONDecodeError:
                continue

            total_papers += 1
            raw_text = paper.get("text", "")

            if not raw_text or len(raw_text.strip()) < MIN_CHUNK_CHARS:
                skipped_empty += 1
                continue

            cleaned = clean_text(raw_text)
            question_chunks = split_into_questions(cleaned)

            for idx, chunk_text in enumerate(question_chunks):
                chunk_record = {
                    "grade": paper.get("grade", "unknown"),
                    "subject": paper.get("subject", "unknown"),
                    "year": paper.get("year", "unknown"),
                    "group": paper.get("group", "unknown"),
                    "medium": paper.get("medium", "unknown"),
                    "type": paper.get("type", "unknown"),
                    "source_filename": paper.get("filename", "unknown"),
                    "chunk_id": f"{Path(paper.get('filename', 'unknown')).stem}_{idx}",
                    "text": chunk_text,
                }
                outfile.write(json.dumps(chunk_record, ensure_ascii=False) + "\n")
                total_chunks += 1

            if total_papers % 50 == 0:
                print(f"Processed {total_papers} papers so far... ({total_chunks} chunks)")

    print("\n" + "=" * 60)
    print(f"DONE. Chunks saved to: {OUTPUT_FILE.resolve()}")
    print(f"Papers processed      : {total_papers}")
    print(f"Papers skipped (empty): {skipped_empty}")
    print(f"Total chunks created  : {total_chunks}")
    if total_papers:
        print(f"Avg chunks per paper  : {total_chunks / max(total_papers - skipped_empty, 1):.1f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
