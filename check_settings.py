import sqlite3, json
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

c.execute("SELECT * FROM settings")
for row in c.fetchall():
    print("Setting:", row)

c.execute("PRAGMA table_info(settings)")
for col in c.fetchall():
    print("Column:", col)

conn.close()
