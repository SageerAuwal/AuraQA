import sqlite3
import os

db_paths = [
    r"c:\Users\HP ProBook\Desktop\ChatBot\backend\chatbot.db",
    r"c:\Users\HP ProBook\Desktop\ChatBot\chatbot.db"
]

for path in db_paths:
    if not os.path.exists(path):
        print(f"Database not found at {path}, skipping.")
        continue
        
    print(f"Migrating database at: {path}")
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    try:
        # Check if chat_id already exists in documents
        cursor.execute("PRAGMA table_info(documents)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "chat_id" not in columns:
            cursor.execute("ALTER TABLE documents ADD COLUMN chat_id INTEGER REFERENCES chats(id) ON DELETE CASCADE")
            conn.commit()
            print("Successfully added chat_id column to documents table.")
        else:
            print("chat_id column already exists in documents table.")
            
    except Exception as e:
        print(f"Error migrating {path}: {str(e)}")
    finally:
        conn.close()

print("Migration run complete.")
