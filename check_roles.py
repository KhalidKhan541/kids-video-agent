import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute("SELECT * FROM role")
for row in c.fetchall():
    print('Role:', row)
c.execute("SELECT * FROM project_relation")
for row in c.fetchall():
    print('Project relation:', row)
conn.close()
