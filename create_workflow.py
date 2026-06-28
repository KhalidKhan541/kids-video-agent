import sqlite3
import json
import uuid
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Check if workflow already exists
c.execute("SELECT id, name FROM workflow_entity WHERE name LIKE '%Kids Video%'")
existing = c.fetchall()
if existing:
    print(f"Workflow already exists: {existing}")
    conn.close()
    exit()

# Generate IDs
workflow_id = str(uuid.uuid4())
version_id = str(uuid.uuid4())
user_id = "7e86ac7d-065c-4bed-9a7a-828da2035caf"
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

# Workflow settings
settings = {
    "executionOrder": "v1"
}

# Nodes JSON
nodes = [
    {
        "id": "manual-trigger",
        "name": "Start",
        "type": "n8n-nodes-base.manualTrigger",
        "typeVersion": 1,
        "position": [250, 300],
        "parameters": {}
    },
    {
        "id": "generate-prompts",
        "name": "Generate Script (Ollama)",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [480, 300],
        "parameters": {
            "method": "POST",
            "url": "http://localhost:11434/api/generate",
            "authentication": "none",
            "sendBody": True,
            "bodyParameters": {
                "parameters": [
                    {
                        "name": "model",
                        "value": "qwen2.5:1.5b"
                    },
                    {
                        "name": "prompt",
                        "value": "Generate a kids video script about animal dance party with 5 scenes. Return ONLY a numbered list of scene descriptions, one per line."
                    },
                    {
                        "name": "stream",
                        "value": False
                    }
                ]
            },
            "options": {
                "timeout": 120000,
                "response": {
                    "responseFormat": "json"
                }
            }
        }
    },
    {
        "id": "save-prompts",
        "name": "Save to File",
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": [710, 300],
        "parameters": {
            "command": "powershell",
            "arguments": [
                "-Command",
                "Set-Content -Path 'C:\\Users\\khali\\kids-video-agent\\output\\prompts\\latest_prompts.txt' -Value $env:PROMPTS"
            ],
            "executeInCommand": True,
            "cwd": "C:\\Users\\khali\\kids-video-agent"
        }
    },
    {
        "id": "open-bing",
        "name": "Open Bing",
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": [940, 300],
        "parameters": {
            "command": "powershell",
            "arguments": [
                "-Command",
                "Start-Process 'https://www.bing.com/create'"
            ],
            "executeInCommand": True
        }
    },
    {
        "id": "wait-node",
        "name": "Create Images Then Resume",
        "type": "n8n-nodes-base.wait",
        "typeVersion": 1,
        "position": [1170, 300],
        "parameters": {
            "resume": "webhook",
            "options": {
                "message": "1. Create 5 images in Bing Image Creator\n2. Download to C:\\Users\\khali\\kids-video-agent\\input_images\\\n3. Name: scene_01.jpg through scene_05.jpg\n4. Click Resume below when done"
            }
        }
    },
    {
        "id": "run-video",
        "name": "Run Video Pipeline",
        "type": "n8n-nodes-base.executeCommand",
        "typeVersion": 1,
        "position": [1400, 300],
        "parameters": {
            "command": "python",
            "arguments": [
                "C:\\Users\\khali\\kids-video-agent\\make_video.py",
                "--topic",
                "animal dance party",
                "--assemble"
            ],
            "executeInCommand": True,
            "cwd": "C:\\Users\\khali\\kids-video-agent"
        }
    },
    {
        "id": "notify-user",
        "name": "Send Notification",
        "type": "n8n-nodes-base.noOp",
        "typeVersion": 1,
        "position": [1630, 300],
        "parameters": {}
    }
]

connections = {
    "manual-trigger": {
        "main": [[{"node": "generate-prompts", "type": "main", "index": 0}]]
    },
    "generate-prompts": {
        "main": [[{"node": "save-prompts", "type": "main", "index": 0}]]
    },
    "save-prompts": {
        "main": [[{"node": "open-bing", "type": "main", "index": 0}]]
    },
    "open-bing": {
        "main": [[{"node": "wait-node", "type": "main", "index": 0}]]
    },
    "wait-node": {
        "main": [[{"node": "run-video", "type": "main", "index": 0}]]
    },
    "run-video": {
        "main": [[{"node": "notify-user", "type": "main", "index": 0}]]
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
        0,  # not active initially
        json.dumps(nodes),
        json.dumps(connections),
        json.dumps(settings),
        version_id,
        now,
        now,
        False,
        1,
        "[]",
        "Automated kids video creation pipeline"
    )
)

# Set up sharing - link to personal project
project_id = "cP5PdWQRV8iFpxYm"
c.execute(
    """INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt)
       VALUES (?, ?, ?, ?, ?)""",
    (workflow_id, project_id, "workflow:owner", now, now)
)

# Clean up temp files
c.execute("DELETE FROM processed_data WHERE workflowId = ?", (workflow_id,))

conn.commit()
conn.close()

print(f"Workflow created successfully!")
print(f"ID: {workflow_id}")
print(f"Name: Kids Video Pipeline")
print(f"Open http://localhost:5678/workflow/{workflow_id} to view")
