import sqlite3, json

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Change schedule trigger to manual trigger
c.execute("SELECT id, nodes FROM workflow_entity WHERE name='Kids Video Pipeline'")
row = c.fetchone()
if row:
    wid, nodes_json = row
    nodes = json.loads(nodes_json)
    for n in nodes:
        if n['type'] == 'n8n-nodes-base.scheduleTrigger':
            n['type'] = 'n8n-nodes-base.manualTrigger'
            n.pop('parameters', None)
    c.execute("UPDATE workflow_entity SET nodes=? WHERE id=?", (json.dumps(nodes), wid))
    conn.commit()
    print(f"Updated workflow {wid} with manual trigger")
else:
    print("Workflow not found")

conn.close()
