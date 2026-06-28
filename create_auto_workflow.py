import sqlite3, json, uuid
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Clean old workflows
c.execute("DELETE FROM workflow_entity WHERE name LIKE '%Kids Video%'")
c.execute("DELETE FROM shared_workflow WHERE workflowId NOT IN (SELECT id FROM workflow_entity)")
c.execute("DELETE FROM execution_entity")
c.execute("DELETE FROM execution_data")
c.execute("DELETE FROM execution_metadata")

workflow_id = str(uuid.uuid4())
version_id = str(uuid.uuid4())
project_id = "cP5PdWQRV8iFpxYm"
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

nodes = [
    {
        "id": "1",
        "name": "Schedule",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1.1,
        "position": [250, 300],
        "parameters": {
            "rule": {
                "interval": [
                    { "field": "days", "hoursInterval": 24 }
                ]
            }
        }
    },
    {
        "id": "2",
        "name": "Generate & Open",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [470, 300],
        "parameters": {
            "jsCode": "const prompts = [\n  'Cute pink cow dancing in meadow, 3D cartoon, Pixar style, 8K',\n  'Penguin with top hat dancing on ice, 3D cartoon, 8K',\n  'Fluffy bunny hopping in garden, 3D cartoon, 8K',\n  'Lion cub dancing on savanna, 3D cartoon, 8K',\n  'All animals dancing together, party scene, 3D cartoon, 8K'\n];\n\nconst fs = require('fs');\nconst filePath = 'C:\\\\Users\\\\khali\\\\kids-video-agent\\\\output\\\\prompts\\\\latest_prompts.txt';\nlet content = 'ANIMAL DANCE PARTY - Bing Prompts\\n\\n';\nprompts.forEach((p, i) => { content += `Scene ${i+1}: ${p}\\n\\n`; });\nfs.writeFileSync(filePath, content);\n\nconst { exec } = require('child_process');\nexec('start https://www.bing.com/create');\n\nreturn [{ json: {\n  success: true,\n  promptsFile: filePath,\n  message: 'Bing opened! Create 5 images, then click Resume'\n}}];"
        }
    },
    {
        "id": "3",
        "name": "Wait Images",
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1,
        "position": [690, 300],
        "parameters": {
            "resume": "webhook",
            "options": {
                "message": "Create 5 images in Bing, save to input_images/ as scene_01.jpg through scene_05.jpg, then click Resume"
            }
        }
    },
    {
        "id": "4",
        "name": "Build Video",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [910, 300],
        "parameters": {
            "jsCode": "const { execSync } = require('child_process');\nconst result = execSync(\n  'python C:\\\\Users\\\\khali\\\\kids-video-agent\\\\make_video.py --topic \"animal dance party\" --assemble',\n  { cwd: 'C:\\\\Users\\\\khali\\\\kids-video-agent', encoding: 'utf8', timeout: 300000 }\n);\nreturn [{ json: { success: true, output: result, topic: 'animal dance party' } }];"
        }
    },
    {
        "id": "5",
        "name": "Done",
        "type": "n8n-nodes-base.noOp",
        "typeVersion": 1,
        "position": [1130, 300],
        "parameters": {}
    }
]

connections = {
    "1": { "main": [[{"node": "2", "type": "main", "index": 0}]] },
    "2": { "main": [[{"node": "3", "type": "main", "index": 0}]] },
    "3": { "main": [[{"node": "4", "type": "main", "index": 0}]] },
    "4": { "main": [[{"node": "5", "type": "main", "index": 0}]] }
}

# Use node names as keys
conns = {}
for from_id, to_info in connections.items():
    for n in nodes:
        if n["id"] == from_id:
            conns[n["name"]] = to_info
            break

c.execute(
    """INSERT INTO workflow_entity 
       (id, name, active, nodes, connections, settings, versionId, createdAt, updatedAt, isArchived, versionCounter, nodeGroups, description)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (workflow_id, "Kids Video Pipeline", 0,
     json.dumps(nodes), json.dumps(conns),
     json.dumps({"executionOrder": "v1"}),
     version_id, now, now, False, 1, "[]",
     "Full auto kids video pipeline")
)

c.execute("INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?)",
          (workflow_id, project_id, "workflow:owner", now, now))

conn.commit()
conn.close()

print(f"Workflow created: http://localhost:5678/workflow/{workflow_id}")
print(f"To activate: curl -X PATCH http://localhost:5678/rest/workflows/{workflow_id}/activate")
print(f"API Key: n8n_api_iKER8RH36XtTFBR9aQxzOn5EsTPjUrVZKBuHIvHJhlXTZte3")
