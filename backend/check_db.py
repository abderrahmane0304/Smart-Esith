import sqlite3

db_path = r"hall_esith_v3.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]

for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [r[1] for r in cursor.fetchall() if r[2] in ('TEXT', 'VARCHAR', '')]
    for col in cols:
        try:
            cursor.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} LIKE '%\ufffd%'")
            rows = cursor.fetchall()
            if rows:
                print(f"[UFFFD] Table {table}, Col {col}:", [ascii(r[0]) for r in rows[:10]])
            
            cursor.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} LIKE '%?%'")
            rows = cursor.fetchall()
            if rows:
                print(f"[QUESTION_MARK] Table {table}, Col {col}:", [ascii(r[0]) for r in rows[:10]])

            cursor.execute(f"SELECT DISTINCT {col} FROM {table} WHERE {col} LIKE '%Ã%'")
            rows = cursor.fetchall()
            if rows:
                print(f"[MOJIBAKE] Table {table}, Col {col}:", [ascii(r[0]) for r in rows[:10]])
        except Exception as e:
            pass

conn.close()

