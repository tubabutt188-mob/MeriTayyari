r"""
PDF export — student ke saved notes se e-book style PDF banata hai.

Notes content AI se markdown-ish text ki shakal mein aata hai
(**bold**, "- " bullets, \[ ... \] LaTeX formula blocks). Ye file
usay parse kar ke properly formatted PDF banati hai.
"""
import re
from fpdf import FPDF
from datetime import datetime


# ---------- Unicode sanitization (pehle wala fix, laazmi rakha hai) ----------

_UNICODE_REPLACEMENTS = {
    "\u2018": "'",   # left single quote  '
    "\u2019": "'",   # right single quote ' (Newton's wala apostrophe)
    "\u201c": '"',   # left double quote  "
    "\u201d": '"',   # right double quote "
    "\u2013": "-",   # en dash  –
    "\u2014": "-",   # em dash  —
    "\u2026": "...", # ellipsis …
    "\u00d7": "x",   # multiplication sign ×
    "\u2192": "->",  # right arrow →
    "\u2212": "-",   # minus sign −
}


def sanitize_text(text: str) -> str:
    """Unicode characters ko safe ASCII/Latin-1 equivalents mein convert karta hai."""
    if not text:
        return text
    for unicode_char, replacement in _UNICODE_REPLACEMENTS.items():
        text = text.replace(unicode_char, replacement)
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ---------- LaTeX formula cleanup ----------

def clean_latex(expr: str) -> str:
    """
    Simple LaTeX expression ko readable plain text mein convert karta hai.
    Poora LaTeX render nahi karte (font support nahi hai), bas
    \\mathbf{}, \\text{}, \\frac{}{}, subscripts/superscripts, aur
    common symbols ko clean, readable form mein convert karte hain.
    """
    expr = re.sub(r"\\mathbf\{([^}]*)\}", r"\1", expr)
    expr = re.sub(r"\\text\{([^}]*)\}", r"\1", expr)
    expr = re.sub(r"\\frac\{([^}]*)\}\{([^}]*)\}", r"(\1)/(\2)", expr)
    expr = expr.replace("\\,", " ")
    expr = expr.replace("\\times", " x ")
    expr = expr.replace("\\cdot", " * ")
    expr = re.sub(r"_\{([^}]*)\}", r"_\1", expr)
    expr = re.sub(r"\^\{([^}]*)\}", r"^\1", expr)
    expr = expr.replace("\\", "")
    return re.sub(r"\s+", " ", expr).strip()


# ---------- Content parsing + rendering ----------

_BULLET_RE = re.compile(r"^(\s*)[-*]\s+(.*)$")
_FORMULA_BLOCK_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
_FORMULA_TOKEN = "\x00FORMULA\x00"


def _extract_formulas(content: str) -> str:
    """
    \\[ ... \\] LaTeX blocks ko dhoondta hai (chahe kisi bullet line ke
    andar hi kyun na hon, ya kai lines mein phaile hon) aur unhe ek
    single-line placeholder token se replace karta hai, taake baad mein
    line-by-line rendering step unhe aasani se pakad sake.
    """
    def repl(match: "re.Match") -> str:
        cleaned = clean_latex(match.group(1))
        return f"\n{_FORMULA_TOKEN}{cleaned}{_FORMULA_TOKEN}\n"

    return _FORMULA_BLOCK_RE.sub(repl, content)


def render_note_content(pdf: FPDF, content: str) -> None:
    """
    Note ka content line-by-line parse kar ke PDF mein likhta hai:
    - **bold** text ko actually bold render karta hai
    - "- " bullets ko indent + bullet symbol ke saath render karta hai
    - \\[ ... \\] LaTeX blocks ko clean, centered formula line mein render karta hai
    """
    content = _extract_formulas(content)
    lines = content.split("\n")

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped:
            pdf.ln(3)
            continue

        if stripped.startswith(_FORMULA_TOKEN) and stripped.endswith(_FORMULA_TOKEN):
            formula = stripped[len(_FORMULA_TOKEN):-len(_FORMULA_TOKEN)]
            pdf.ln(2)
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "I", 11)
            pdf.multi_cell(0, 7, sanitize_text(formula), align="C")
            pdf.ln(2)
            continue

        bullet_match = _BULLET_RE.match(raw_line)
        if bullet_match:
            indent_spaces, bullet_text = bullet_match.groups()
            if not bullet_text.strip():
                # Bullet line jiska content sirf formula block tha (ab placeholder
                # alag line pe hai) - khud ye khali bullet skip kar dete hain.
                continue
            # Zyada se zyada 4 nesting levels tak hi indent karte hain, taake
            # available width kabhi itni chhoti na ho ke word-wrap fail ho jaye.
            level = min(len(indent_spaces) // 2, 4)
            indent = 5 * level
            pdf.set_font("Helvetica", "", 11)
            pdf.set_left_margin(pdf.l_margin + indent)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0,
                6,
                sanitize_text("- " + bullet_text),
                markdown=True,
                new_x="LMARGIN",
                new_y="NEXT",
            )
            pdf.set_left_margin(pdf.l_margin - indent)
        else:
            pdf.set_font("Helvetica", "", 11)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, sanitize_text(stripped), markdown=True)


# ---------- PDF structure ----------

class NotesPDF(FPDF):
    def header(self):
        pass  # cover page alag se banate hain

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def generate_pdf(student_name: str, notes: list) -> bytes:
    """
    notes: list of dicts with keys: title, content, subject, grade
    Returns PDF bytes.
    """
    student_name = sanitize_text(student_name)

    pdf = NotesPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Cover page
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.ln(60)
    pdf.cell(0, 15, "MeriTayyari", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, f"Notes - {student_name}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, datetime.now().strftime("%B %Y"), align="C")

    # Table of contents
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 12, "Table of Contents", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    for i, note in enumerate(notes, start=1):
        pdf.cell(0, 8, sanitize_text(f"{i}. {note['title']}"), new_x="LMARGIN", new_y="NEXT")

    # Notes content
    for note in notes:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.multi_cell(0, 10, sanitize_text(note["title"]), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "I", 10)
        subject_line = f"{note.get('subject', '')} - Grade {note.get('grade', '')}"
        pdf.cell(0, 8, sanitize_text(subject_line), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        render_note_content(pdf, note["content"])

    return bytes(pdf.output())