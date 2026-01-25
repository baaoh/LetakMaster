import sqlite3
import os

DB_PATH = "letak_master.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(project_states)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "last_build_plans_path" not in columns:
            print("Adding last_build_plans_path to project_states...")
            cursor.execute("ALTER TABLE project_states ADD COLUMN last_build_plans_path VARCHAR(1024)")
            conn.commit()
            print("Migration successful.")
        else:
            print("Column last_build_plans_path already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
