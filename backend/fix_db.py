import sqlite3
import os

db_path = r"c:\Users\LAPTOP\OneDrive - ECOLE SUPÉRIEURE DES INDUSTRIES DU TEXTILE ET DE L'HABILLEMENT\Bureau\Smart Esith v2\backend\hall_esith_v3.db"

if not os.path.exists(db_path):
    print("DB not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

tables = ['Cours', 'Event', 'Formation', 'Absence', 'Retard']

for table in tables:
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall() if row[2] in ('TEXT', 'VARCHAR')]
        
        for col in columns:
            cursor.execute(f"UPDATE {table} SET {col} = REPLACE({col}, '', 'é') WHERE {col} LIKE '%%'")
            cursor.execute(f"UPDATE {table} SET {col} = REPLACE({col}, 'Ã©', 'é') WHERE {col} LIKE '%Ã©%'")
            cursor.execute(f"UPDATE {table} SET {col} = REPLACE({col}, 'Ã¨', 'è') WHERE {col} LIKE '%Ã¨%'")
            cursor.execute(f"UPDATE {table} SET {col} = REPLACE({col}, 'Ã', 'à') WHERE {col} LIKE '%Ã %'") # usually a followed by space
    except Exception as e:
        print(f"Error on {table}: {e}")

conn.commit()
conn.close()
print("Fixed encoding issues in database")
