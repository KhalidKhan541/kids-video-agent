import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute("PRAGMA table_info(shared_workflow)")
for col in c.fetchall():
    print('shared_workflow column:', col)
c.execute("PRAGMA table_info(project)")
for col in c.fetchall():
    print('project column:', col)
conn.close()
