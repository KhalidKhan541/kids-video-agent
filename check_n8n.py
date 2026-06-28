import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in c.fetchall()]
print('Tables:', tables)
if 'workflow' in tables:
    c.execute('SELECT id, name, active FROM workflow')
    rows = c.fetchall()
    if rows:
        for row in rows:
            print(f'  Workflow: id={row[0]}, name={row[1]}, active={row[2]}')
    else:
        print('No workflows found - import the workflow JSON!')
if 'user' in tables:
    c.execute('SELECT id, email FROM user')
    for row in c.fetchall():
        print(f'  User: id={row[0]}, email={row[1]}')
conn.close()
