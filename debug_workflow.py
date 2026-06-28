import sqlite3, json

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

c.execute("SELECT id, name, nodes, connections FROM workflow_entity WHERE name='Kids Video Pipeline'")
row = c.fetchone()
if row:
    wid, name, nodes_str, conns_str = row
    nodes = json.loads(nodes_str)
    conns = json.loads(conns_str)
    
    print("Nodes:")
    for n in nodes:
        print(f"  id={n['id']}, name='{n['name']}', type={n['type']}")
    
    print("\nConnections:")
    print(json.dumps(conns, indent=2))

conn.close()
