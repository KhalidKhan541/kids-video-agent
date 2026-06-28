import sqlite3, json

db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()

c.execute("SELECT id, name, nodes, connections, active FROM workflow_entity WHERE name='Kids Video Pipeline'")
row = c.fetchone()
if row:
    wid, name, nodes_str, conns_str, active = row
    nodes = json.loads(nodes_str)
    conns = json.loads(conns_str)
    
    print(f"Workflow: {name}")
    print(f"Active: {active}")
    print(f"ID: {wid}")
    print()
    
    for n in nodes:
        print(f"  [{n['id']}] {n['name']} ({n['type']})")
    
    print("\nConnections:")
    for src, targets in conns.items():
        for t_list in targets.get('main', []):
            for t in t_list:
                print(f"  {src} -> {t['node']}")

db.close()
