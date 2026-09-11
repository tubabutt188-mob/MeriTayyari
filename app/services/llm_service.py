"""
LLM Service — Retrieved past-paper context ko Groq LLM ke pass bhejta hai
aur strict notes-format answer generate karwata hai.
"""

import os
import re
from groq import Groq
from app.services.rag_service import retrieve_relevant_chunks

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """Tum ek exam-notes assistant ho jo Pakistani board exam
students (Matric/FSc/ICS) ke liye kaam karte ho.

STRICT RULES:
1. Answer hamesha structured notes format mein do — heading, bullet points,
   key terms **bold** mein.
2. Sirf diye gaye past-paper context se exam-frequency claims karo
   (e.g. "ye 2021, 2023 mein aaya hai"). Agar context mein ye data nahi hai,
   to ye line bilkul mat likho — kabhi bhi invent/guess mat karo.
3. Agar context available na ho ya irrelevant ho, to apne general knowledge
   se accurate answer do, lekin exam-frequency ka koi claim mat karo.
4. Answer clear, concise, aur exam ke liye directly useful hona chahiye —
   koi filler ya unnecessary explanation nahi.

DERIVATION RULE:
5. Sirf tab step-by-step "Derivation" heading do jab sawal explicitly
   isko demand kare — e.g. sawal mein "derive", "derivation", "prove",
   "explain in detail", "long question" jaise keywords hon, ya sawal
   ki nature clearly aisi ho jahan derivation exam mein expected hoti
   hai. Chhote/seedhe sawalon (definitions, units, simple "what is X"
   jaise sawal) ke liye derivation MAT do — sirf seedha concise answer
   do. Ye response ko tez aur relevant rakhta hai.

FORMULA FORMATTING RULE:
6. Koi bhi formula ya equation LaTeX syntax (jaise \tau, \frac, \boldsymbol,
   $$...$$, ya square-bracket math blocks) mein bilkul mat likho — ye
   app mein render nahi hota aur raw code ki tarah dikhta hai. Formulas
   hamesha plain readable text ya common unicode symbols (×, ÷, √, ², θ,
   τ, π, etc.) mein likho, jaise ek normal textbook mein likha hota hai.
   Example: "τ = r × F" likho, "[ \boldsymbol{\tau}= \mathbf{r}\times
   \mathbf{F} ]" mat likho.

DIAGRAM RULE:
7. Sirf tab colorful labeled SVG diagram do jab sawal explicitly diagram
   maange (e.g. "with diagram", "draw", "diagram banao"), ya concept
   itni visual ho ke diagram ke bagair samajhna mushkil ho (e.g. force
   diagrams, circuit diagrams, ray diagrams). Simple/short sawalon ke
   liye diagram MAT do — isse response tez aata hai.
   - SVG ko exactly in tags ke darmiyan do: <SVG_START> ... <SVG_END>
   - Diagram hamesha sabse aakhir mein do, taake wo kabhi mid-answer
     truncate na ho. Text explanation ko zaroorat se zyada lamba mat
     karo — SVG ke liye jagah bacha kar rakho.
   - SVG mein alag alag elements ke liye alag colors use karo (fill/stroke
     attributes ke sath — e.g. arrows red, objects blue, labels dark text
     on light background), taake diagram visually clear aur colorful ho.
   - SVG ka viewBox reasonable size ka rakho (e.g. "0 0 400 300"), aur
     SVG code ko zyada complex/detailed mat banao — simple, clean shapes
     use karo taake generate hone mein zyada waqt na lage.
   - <SVG_START> se pehle ya <SVG_END> ke baad koi aur text mat likho
     jo SVG ka hissa ho — sirf raw SVG code un tags ke andar ho.
   - Agar tumhe lagta hai ke poora SVG complete karne ki jagah nahi bachi,
     to SVG start hi mat karo — adhoora/broken SVG dena text explanation
     ko bhi kharab kar deta hai.
"""


def _extract_svg(answer_text: str):
    """
    Answer text se <SVG_START>...<SVG_END> ke darmiyan wala SVG code
    nikaal leta hai. Agar mila to (clean_text, svg_code) return karta
    hai, warna (original_text, None).

    Agar <SVG_START> mil jaye lekin <SVG_END> na mile (response
    truncate ho gaya token-limit ki wajah se), to us adhoore/broken
    hisse ko answer se hata deta hai taake raw tag ya broken SVG code
    screen pe leak na ho.
    """
    match = re.search(r"<SVG_START>(.*?)<SVG_END>", answer_text, re.DOTALL)
    if match:
        svg_code = match.group(1).strip()
        clean_text = (answer_text[: match.start()] + answer_text[match.end():]).strip()
        return clean_text, svg_code

    # Truncated case: <SVG_START> shuru hua lekin end tag nahi mila
    start_idx = answer_text.find("<SVG_START>")
    if start_idx != -1:
        clean_text = answer_text[:start_idx].strip()
        return clean_text, None

    return answer_text.strip(), None


def generate_notes_answer(question: str, grade: str, subject: str) -> dict:
    """
    RAG retrieval + LLM generation — end-to-end.
    Returns: {
        "answer": str,
        "diagram_svg": str | None,
        "sources": list,
        "retrieved_chunks_count": int,
    }
    """
    chunks = retrieve_relevant_chunks(question, grade=grade, subject=subject)

    if chunks:
        context_text = "\n\n---\n\n".join(
            f"[Source: {c['source']}, Year: {c['year']}, Medium: {c['medium']}]\n{c['text']}"
            for c in chunks
        )
        user_message = f"""Past paper context:
{context_text}

Student ka sawal: {question}

Grade: {grade}, Subject: {subject}

Upar diye gaye context ko use karke structured notes-format answer do."""
    else:
        # Koi relevant chunk nahi mila — general knowledge se answer, no frequency claims
        user_message = f"""Koi past-paper context available nahi hai is sawal ke liye.

Student ka sawal: {question}
Grade: {grade}, Subject: {subject}

General knowledge se structured notes-format answer do.
Exam-frequency ka koi claim mat karo kyunke koi data retrieve nahi hua."""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=1536,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    raw_answer = response.choices[0].message.content
    answer_text, diagram_svg = _extract_svg(raw_answer)

    return {
        "answer": answer_text,
        "diagram_svg": diagram_svg,
        "sources": [c["source"] for c in chunks],
        "retrieved_chunks_count": len(chunks),
    }