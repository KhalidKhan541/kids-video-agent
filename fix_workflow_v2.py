import sqlite3
import json
import uuid
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Delete old workflows
c.execute("DELETE FROM workflow_entity WHERE name LIKE '%Kids Video%'")
c.execute("DELETE FROM shared_workflow WHERE workflowId NOT IN (SELECT id FROM workflow_entity)")

# Generate IDs
workflow_id = str(uuid.uuid4())
version_id = str(uuid.uuid4())
project_id = "cP5PdWQRV8iFpxYm"
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

# New workflow without Ollama - prompts are already generated
nodes = [
    {
        "parameters": {},
        "id": "1",
        "name": "Start",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [250, 300]
    },
    {
        "parameters": {
            "jsCode": "// Load pre-generated prompts\nconst fs = require('fs');\nconst promptsFile = 'C:\\\\Users\\\\khali\\\\kids-video-agent\\\\output\\\\prompts\\\\animal_dance_party.txt';\nconst prompts = fs.readFileSync(promptsFile, 'utf8');\n\n// Open Bing Image Creator\nconst { exec } = require('child_process');\nexec('start https://www.bing.com/create');\n\nreturn [{ json: { prompts: prompts, message: 'Prompts loaded. Create 5 images in Bing.' } }];"
        },
        "id": "2",
        "name": "Load Prompts",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [470, 300]
    },
    {
        "parameters": {
            "resume": "webhook",
            "options": {
                "message": "1. Open Bing Image Creator (tab opened)\n2. Create 5 images from prompts:\n\nScene 1: Cute pink cow dancing in meadow\nScene 2: Penguin with top hat on ice\nScene 3: Fluffy bunny in magical garden\nScene 4: Friendly lion cub dancing\nScene 5: All animals together\n\n3. Download to: C:\\Users\\khali\\kids-video-agent\\input_images\\\n4. Name: scene_01.jpg through scene_05.jpg\n5. Click Resume when done"
            }
        },
        "id": "3",
        "name": "Wait for Images",
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1,
        "position": [690, 300]
    },
    {
        "parameters": {
            "jsCode": "// Run video pipeline\nconst { execSync } = require('child_process');\n\ntry {\n    const result = execSync(\n        'python C:\\\\Users\\\\khali\\\\kids-video-agent\\\\make_video.py --topic \"animal dance party\" --assemble',\n        { cwd: 'C:\\\\Users\\\\khali\\\\kids-video-agent', encoding: 'utf8', timeout: 300000 }\n    );\n    return [{ json: { success: true, output: result, topic: 'animal dance party' } }];\n} catch (e) {\n    return [{ json: { success: false, error: e.message, topic: 'animal dance party' } }];\n}"
        },
        "id": "4",
        "name": "Run Pipeline",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [910, 300]
    },
    {
        "parameters": {
            "jsCode": "// Show completion message\nconst fs = require('fs');\nconst videoPath = 'C:\\\\Users\\\\khali\\\\Downloads\\\\animal_dance_party.mp4';\n\nlet message = 'Video pipeline completed!';\nif (fs.existsSync(videoPath)) {\n    const stats = fs.statSync(videoPath);\n    message = `Video created: ${(stats.size / 1024 / 1024).toFixed(1)}MB\\nLocation: ${videoPath}`;\n}\n\nreturn [{ json: { success: true, message: message } }];"
        },
        "id": "5",
        "name": "Complete",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1130, 300]
    }
]

connections = {
    "Start": {
        "main": [[{"node": "Load Prompts", "type": "main", "index": 0}]]
    },
    "Load Prompts": {
        "main": [[{"node": "Wait for Images", "type": "main", "index": 0}]]
    },
    "Wait for Images": {
        "main": [[{"node": "Run Pipeline", "type": "main", "index": 0}]]
    },
    "Run Pipeline": {
        "main": [[{"node": "Complete", "type": "main", "index": 0}]]
    }
}

# Insert workflow
c.execute(
    """INSERT INTO workflow_entity 
       (id, name, active, nodes, connections, settings, versionId, createdAt, updatedAt, isArchived, versionCounter, nodeGroups, description)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
        workflow_id,
        "Kids Video Pipeline",
        0,
        json.dumps(nodes),
        json.dumps(connections),
        json.dumps({"executionOrder": "v1"}),
        version_id,
        now,
        now,
        False,
        1,
        "[]",
        "Kids video pipeline without Ollama"
    )
)

# Link to project
c.execute(
    """INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt)
       VALUES (?, ?, ?, ?, ?)""",
    (workflow_id, project_id, "workflow:owner", now, now)
)

conn.commit()
conn.close()

print(f"Workflow created!")
print(f"URL: http://localhost:5678/workflow/{workflow_id}")
