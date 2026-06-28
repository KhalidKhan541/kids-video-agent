import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute('SELECT id, name, active FROM workflow_entity')
rows = c.fetchall()
if rows:
    for row in rows:
        print(f'Workflow: id={row[0]}, name={row[1]}, active={row[2]}')
else:
    print('No workflows imported yet')

c.execute('SELECT id, name, type FROM credentials_entity')
creds = c.fetchall()
if creds:
    print('\nExisting credentials:')
    for c in creds:
        print(f'  Credential: id={c[0]}, name={c[1]}, type={c[2]}')
else:
    print('\nNo credentials set up yet')

c.execute("SELECT id, name, value FROM settings WHERE name LIKE '%n8n%'")
for s in c.fetchall():
    print(f'Setting: {s[1]} = {s[2]}')

c.execute("SELECT id, email, firstName, lastName FROM user")
for u in c.fetchall():
    print(f'User: {u[0]}, {u[1]}, {u[2]} {u[3]}')

conn.close()
