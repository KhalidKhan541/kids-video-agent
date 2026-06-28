import sqlite3, json, uuid
from datetime import datetime

db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()
c.execute("DELETE FROM workflow_entity WHERE name LIKE '%Kids Video%'")
c.execute("DELETE FROM shared_workflow WHERE workflowId NOT IN (SELECT id FROM workflow_entity)")

wid = str(uuid.uuid4())
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

nodes = [
    {"id":"1","name":"Start","type":"n8n-nodes-base.manualTrigger","typeVersion":1,"position":[250,300],"parameters":{}},
    {"id":"2","name":"Generate Images","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[470,300],
     "parameters":{"method":"GET","url":"http://127.0.0.1:8787/generate-images","authentication":"none",
     "options":{"timeout":120000}}},
    {"id":"3","name":"Build Video","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[690,300],
     "parameters":{"method":"GET","url":"http://127.0.0.1:8787/run-pipeline","authentication":"none",
     "options":{"timeout":300000}}},
    {"id":"4","name":"Done","type":"n8n-nodes-base.noOp","typeVersion":1,"position":[910,300],"parameters":{}}
]

connections = {
    "Start":{"main":[[{"node":"Generate Images","type":"main","index":0}]]},
    "Generate Images":{"main":[[{"node":"Build Video","type":"main","index":0}]]},
    "Build Video":{"main":[[{"node":"Done","type":"main","index":0}]]}
}

c.execute("""INSERT INTO workflow_entity (id,name,active,nodes,connections,settings,versionId,createdAt,updatedAt,isArchived,versionCounter,nodeGroups,description) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (wid,"Kids Video Pipeline",0,json.dumps(nodes),json.dumps(connections),json.dumps({}),
     str(uuid.uuid4()),now,now,False,1,"[]","Auto generate images + build video"))
c.execute("INSERT INTO shared_workflow (workflowId,projectId,role,createdAt,updatedAt) VALUES (?,?,?,?,?)",
    (wid,"cP5PdWQRV8iFpxYm","workflow:owner",now,now))
c.execute("UPDATE workflow_entity SET active=1 WHERE id=?", (wid,))
db.commit()
db.close()

print(f"NEW AUTO WORKFLOW: http://localhost:5678/workflow/{wid}")
print("No manual steps needed! Generates images + builds video automatically.")
