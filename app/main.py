"""
MeriTaiyari Backend — Main FastAPI App

Run karne ke liye:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.database import Base, engine, get_db
from app.models import User, Note
from app.schemas import UserCreate, UserLogin, Token, NoteCreate, NoteUpdate, NoteOut
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services.llm_service import generate_notes_answer
from app.services.pdf_service import generate_pdf

# Database tables bana dein (agar pehle se nahi hain)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MeriTaiyari API")


# ---------- /ask (pehle se maujood) ----------

class AskRequest(BaseModel):
    question: str
    grade: str      # e.g. "9", "10", "fsc1", "ics2"
    subject: str    # e.g. "physics", "chemistry"


@app.post("/ask")
def ask(request: AskRequest):
    """
    Student ka sawal leta hai, RAG + LLM se notes-format answer generate
    karke return karta hai.
    """
    result = generate_notes_answer(
        question=request.question,
        grade=request.grade,
        subject=request.subject,
    )
    return result


# ---------- Auth ----------

@app.post("/signup", response_model=Token)
def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="This email is already registered")

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        name=user_data.name,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": new_user.email})
    return {"access_token": token}


@app.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    token = create_access_token({"sub": user.email})
    return {"access_token": token}


# ---------- Notes CRUD ----------

@app.post("/notes", response_model=NoteOut)
def create_note(
    note_data: NoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = Note(
        title=note_data.title,
        content=note_data.content,
        grade=note_data.grade,
        subject=note_data.subject,
        diagram_svg=note_data.diagram_svg,
        owner_id=current_user.id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@app.get("/notes", response_model=List[NoteOut])
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Note).filter(Note.owner_id == current_user.id).all()


@app.put("/notes/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.owner_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.grade is not None:
        note.grade = note_data.grade
    if note_data.subject is not None:
        note.subject = note_data.subject
    if note_data.diagram_svg is not None:
        note.diagram_svg = note_data.diagram_svg

    db.commit()
    db.refresh(note)
    return note


@app.delete("/notes/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = (
        db.query(Note)
        .filter(Note.id == note_id, Note.owner_id == current_user.id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return {"detail": "Note deleted successfully"}


# ---------- PDF Export ----------

@app.post("/export-pdf")
def export_pdf(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes = db.query(Note).filter(Note.owner_id == current_user.id).all()
    if not notes:
        raise HTTPException(status_code=400, detail="No notes found to export")

    notes_data = [
        {"title": n.title, "content": n.content, "subject": n.subject, "grade": n.grade}
        for n in notes
    ]
    pdf_bytes = generate_pdf(
        student_name=current_user.name or current_user.email, notes=notes_data
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=meritayyari_notes.pdf"},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}