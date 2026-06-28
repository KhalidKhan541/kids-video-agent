import sqlite3
db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()
c.execute("UPDATE workflow_entity SET active=1 WHERE name='Kids Video Pipeline'")
c.execute("SELECT id, name, active FROM workflow_entity WHERE name='Kids Video Pipeline'")
print(c.fetchone())
db.commit()
db.close()
