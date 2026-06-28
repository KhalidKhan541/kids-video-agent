import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Get column info for user_api_keys
c.execute("PRAGMA table_info(user_api_keys)")
for col in c.fetchall():
    print('user_api_keys column:', col)

# Get column info for workflow_entity
c.execute("PRAGMA table_info(workflow_entity)")
for col in c.fetchall():
    print('workflow_entity column:', col)

conn.close()
