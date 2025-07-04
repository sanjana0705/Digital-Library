import sqlite3

conn = sqlite3.connect('books.db')  # This will create books.db file

# Create table
conn.execute('''
    CREATE TABLE books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT NOT NULL,
        image TEXT
    );
''')

print("✅ Database and books table created successfully.")

conn.close()
