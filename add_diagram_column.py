"""
Migration script — 'notes' table mein 'diagram_svg' column add karta hai
bina existing data delete kiye.

Run karne ke liye (project root se, jahan aapki .db file hai):
    python add_diagram_column.py

Agar aapki database file ka naam ya path alag hai to neeche DB_PATH
variable update kar dein.
"""

import sqlite3

DB_PATH = "meritayyari.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check karo ke column pehle se to nahi hai
cursor.execute("PRAGMA table_info(notes)")
columns = [row[1] for row in cursor.fetchall()]

if "diagram_svg" in columns:
    print("'diagram_svg' column pehle se maujood hai — kuch karne ki zaroorat nahi.")
else:
    cursor.execute("ALTER TABLE notes ADD COLUMN diagram_svg TEXT")
    conn.commit()
    print("'diagram_svg' column successfully add ho gaya!")

conn.close()
