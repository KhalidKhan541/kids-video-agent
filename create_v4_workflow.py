import sqlite3, json, uuid
from datetime import datetime

db = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = db.cursor()
c.execute("DELETE FROM workflow_entity WHERE name LIKE '%Kids Video%'")
c.execute("DELETE FROM shared_workflow WHERE workflowId NOT IN (SELECT id FROM workflow_entity)")

wid = str(uuid.uuid4())
ver = str(uuid.uuid4())
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
proj = "cP5PdWQRV8iFpxYm"

nodes = [
    {"id":"1","name":"Start","type":"n8n-nodes-base.manualTrigger","typeVersion":1,"position":[250,300],"parameters":{}},
    {"id":"2","name":"Save Prompts","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[470,300],
     "parameters":{"method":"GET","url":"http://127.0.0.1:8787/save-prompts","authentication":"none","options":{"timeout":10000}}},
    {"id":"3","name":"Open Bing","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[690,300],
     "parameters":{"method":"GET","url":"http://127.0.0.1:8787/open-bing","authentication":"none","options":{"timeout":5000}}},
    {"id":"4","name":"Wait Images","type":"n8n-nodes-base.wait","typeVersion":1,"position":[910,300],
     "parameters":{"resume":"webhook","options":{"message":"Create 5 images in Bing, save to input_images/, then click Resume"}}},
    {"id":"5","name":"Build Video","type":"n8n-nodes-base.httpRequest","typeVersion":4.2,"position":[1130,300],
     "parameters":{"method":"GET","url":"http://127.0.0.1:8787/run-pipeline","authentication":"none","options":{"timeout":300000}}},
    {"id":"6","name":"Done","type":"n8n-nodes-base.noOp","typeVersion":1,"position":[1350,300],"parameters":{}}
]

connections = {
    "Start":{"main":[[{"node":"Save Prompts","type":"main","index":0}]]},
    "Save Prompts":{"main":[[{"node":"Open Bing","type":"main","index":0}]]},
    "Open Bing":{"main":[[{"node":"Wait Images","type":"main","index":0}]]},
    "Wait Images":{"main":[[{"node":"Build Video","type":"main","index":0}]]},
    "Build Video":{"main":[[{"node":"Done","type":"main","index":0}]]}
}

c.execute("""INSERT INTO workflow_entity (id,name,active,nodes,connections,settings,versionId,createdAt,updatedAt,isArchived,versionCounter,nodeGroups,description)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (wid,"Kids Video Pipeline",0,json.dumps(nodes),json.dumps(connections),
     json.dumps({"executionOrder":"v1"}),ver,now,now,False,1,"[]","Pipeline"))
c.execute("INSERT INTO shared_workflow (workflowId,projectId,role,createdAt,updatedAt) VALUES (?,?,?,?,?)",
    (wid,proj,"workflow:owner",now,now))
c.execute("UPDATE workflow_entity SET active=1 WHERE id=?", (wid,))
db.commit()
db.close()
print(f"Workflow: http://localhost:5678/workflow/{wid}")
