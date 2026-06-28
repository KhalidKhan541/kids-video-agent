import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Check auth providers
c.execute("SELECT * FROM auth_identity")
for row in c.fetchall():
    print('Auth identity:', row)

# Check for API keys
c.execute("SELECT * FROM user_api_keys")
for row in c.fetchall():
    print('API key:', row)

# Check user table
c.execute("SELECT * FROM user")
for row in c.fetchall():
    print('User:', row)

conn.close()
