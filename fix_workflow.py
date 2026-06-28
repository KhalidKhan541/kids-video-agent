import sqlite3
import json
import uuid
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Delete old workflow
c.execute("DELETE FROM workflow_entity WHERE name LIKE '%Kids Video%'")
c.execute("DELETE FROM shared_workflow WHERE workflowId NOT IN (SELECT id FROM workflow_entity)")

# Generate IDs
workflow_id = str(uuid.uuid4())
version_id = str(uuid.uuid4())
user_id = "7e86ac7d-065c-4bed-9a7a-828da2035caf"
project_id = "cP5PdWQRV8iFpxYm"
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

# Correct n8n node types - Code node instead of executeCommand
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
            "values": {
                "string": [
                    {
                        "name": "topic",
                        "value": "animal dance party"
                    }
                ]
            },
            "options": {}
        },
        "id": "2",
        "name": "Enter Topic",
        "type": "n8n-nodes-base.set",
        "typeVersion": 3,
        "position": [470, 300]
    },
    {
        "parameters": {
            "method": "POST",
            "url": "http://localhost:11434/api/generate",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {
                        "name": "model",
                        "value": "qwen2.5:1.5b"
                    },
                    {
                        "name": "prompt",
                        "value": "Generate a kids video script about animal dance party with 5 scenes. Return ONLY a numbered list."
                    },
                    {
                        "name": "stream",
                        "value": False
                    }
                ]
            },
            "options": {
                "timeout": 120000
            }
        },
        "id": "3",
        "name": "Generate Prompts",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [690, 300]
    },
    {
        "parameters": {
            "jsCode": "// Save prompts to file\nconst fs = require('fs');\nconst path = require('path');\n\nconst prompts = $input.first().json.response || 'No prompts generated';\nconst filePath = 'C:\\\\Users\\\\khali\\\\kids-video-agent\\\\output\\\\prompts\\\\latest_prompts.txt';\n\ntry {\n    fs.writeFileSync(filePath, prompts, 'utf8');\n    return [{ json: { success: true, message: 'Prompts saved', path: filePath } }];\n} catch (e) {\n    return [{ json: { success: false, error: e.message } }];\n}"
        },
        "id": "4",
        "name": "Save to File",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [910, 300]
    },
    {
        "parameters": {
            "jsCode": "// Open Bing Image Creator\nconst { exec } = require('child_process');\nexec('start https://www.bing.com/create');\nreturn [{ json: { success: true, message: 'Bing opened' } }];"
        },
        "id": "5",
        "name": "Open Bing",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1130, 300]
    },
    {
        "parameters": {
            "resume": "webhook",
            "options": {
                "message": "1. Create 5 images in Bing Image Creator\n2. Download to C:\\Users\\khali\\kids-video-agent\\input_images\\\n3. Name: scene_01.jpg through scene_05.jpg\n4. Click Resume below when done"
            }
        },
        "id": "6",
        "name": "Wait for Images",
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1,
        "position": [1350, 300]
    },
    {
        "parameters": {
            "jsCode": "// Run video pipeline\nconst { execSync } = require('child_process');\nconst topic = $('Enter Topic').first().json.topic;\n\ntry {\n    const result = execSync(\n        `python C:\\\\Users\\\\khali\\\\kids-video-agent\\\\make_video.py --topic \"${topic}\" --assemble`,\n        { cwd: 'C:\\\\Users\\\\khali\\\\kids-video-agent', encoding: 'utf8', timeout: 300000 }\n    );\n    return [{ json: { success: true, output: result, topic: topic } }];\n} catch (e) {\n    return [{ json: { success: false, error: e.message, topic: topic } }];\n}"
        },
        "id": "7",
        "name": "Run Pipeline",
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [1570, 300]
    },
    {
        "parameters": {
            "fromEmail": "khalid.khan46571@gmail.com",
            "toEmail": "khalid.khan46571@gmail.com",
            "subject": "Kids Video Ready!",
            "message": "Your video about {{ $json.topic }} is ready in Downloads folder."
        },
        "id": "8",
        "name": "Email",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 2.1,
        "position": [1790, 300],
        "credentials": {
            "smtp": {
                "id": "1",
                "name": "SMTP"
            }
        }
    }
]

connections = {
    "Start": {
        "main": [[{"node": "Enter Topic", "type": "main", "index": 0}]]
    },
    "Enter Topic": {
        "main": [[{"node": "Generate Prompts", "type": "main", "index": 0}]]
    },
    "Generate Prompts": {
        "main": [[{"node": "Save to File", "type": "main", "index": 0}]]
    },
    "Save to File": {
        "main": [[{"node": "Open Bing", "type": "main", "index": 0}]]
    },
    "Open Bing": {
        "main": [[{"node": "Wait for Images", "type": "main", "index": 0}]]
    },
    "Wait for Images": {
        "main": [[{"node": "Run Pipeline", "type": "main", "index": 0}]]
    },
    "Run Pipeline": {
        "main": [[{"node": "Email", "type": "main", "index": 0}]]
    }
}

# Insert workflow
c.execute(
    """INSERT INTO workflow_entity 
       (id, name, active, nodes, connections, settings, versionId, createdAt, updatedAt, isArchived, versionCounter, nodeGroups, description)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (
        workflow_id,
        "Kids Video Pipeline v2",
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
        "Automated kids video creation pipeline using Code nodes"
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

print(f"Workflow v2 created successfully!")
print(f"ID: {workflow_id}")
print(f"URL: http://localhost:5678/workflow/{workflow_id}")
