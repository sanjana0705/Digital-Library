import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE books ADD COLUMN image TEXT")
    print("✅ Column 'image' added successfully.")
except sqlite3.OperationalError as e:
    print("⚠️ Already exists or error:", e)

conn.commit()
conn.close()
