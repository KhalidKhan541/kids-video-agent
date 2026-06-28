import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute("UPDATE workflow_entity SET active=1 WHERE name='Kids Video Pipeline'")
c.execute("SELECT id, name, active FROM workflow_entity WHERE name='Kids Video Pipeline'")
print(c.fetchone())
conn.commit()
conn.close()
