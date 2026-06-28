import sqlite3

db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()

# Check what node types are actually in the workflow nodes
c.execute("SELECT nodes FROM workflow_entity WHERE name='Kids Video Pipeline'")
row = c.fetchone()
if row:
    import json
    nodes = json.loads(row[0])
    for n in nodes:
        print(f"  {n['name']}: type={n['type']}")

# Check if python node type exists in any installed/available nodes
c.execute("SELECT name, type FROM installed_nodes WHERE type LIKE '%python%'")
for row in c.fetchall():
    print(f"Python node: {row}")

db.close()
