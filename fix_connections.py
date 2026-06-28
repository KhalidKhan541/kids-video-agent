import sqlite3, json

db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()

c.execute("SELECT id, nodes, connections FROM workflow_entity WHERE name='Kids Video Pipeline'")
row = c.fetchone()
if row:
    wid, nodes_str, conns_str = row
    nodes = json.loads(nodes_str)
    conns = json.loads(conns_str)
    
    # Build name lookup
    id_to_name = {n['id']: n['name'] for n in nodes}
    print("ID -> Name mapping:", id_to_name)
    
    # Fix connections - replace node IDs with names
    for source_key, conn_data in conns.items():
        for main_list in conn_data.get('main', []):
            for item in main_list:
                if 'node' in item and item['node'] in id_to_name:
                    old = item['node']
                    item['node'] = id_to_name[old]
                    print(f"  Fixed: {source_key} -> {old} -> {id_to_name[old]}")
    
    # Update in DB
    c.execute("UPDATE workflow_entity SET connections=? WHERE id=?", (json.dumps(conns), wid))
    db.commit()

db.close()
