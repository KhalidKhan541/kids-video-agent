import sqlite3, uuid, secrets, string, json
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

api_key_id = str(uuid.uuid4())
user_id = "7e86ac7d-065c-4bed-9a7a-828da2035caf"
random_part = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(48))
api_key = f"n8n_api_{random_part}"
now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
scopes = json.dumps(["workflow:create", "workflow:read", "workflow:update", "workflow:delete", "workflow:execute", "workflow:list", "credential:create", "credential:read", "credential:update", "credential:delete", "user:read"])

c.execute("DELETE FROM user_api_keys WHERE label='cli-automation'")
c.execute("INSERT INTO user_api_keys (id, userId, label, apiKey, createdAt, updatedAt, scopes, audience) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
          (api_key_id, user_id, "cli-automation", api_key, now, now, scopes, "public-api"))

conn.commit()
conn.close()

print(f"API_KEY={api_key}")
