import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute("SELECT * FROM user_api_keys WHERE label='cli-automation'")
for row in c.fetchall():
    print("API Key row:", row)
c.execute("PRAGMA table_info(user_api_keys)")
for col in c.fetchall():
    print("Column:", col)
conn.close()
