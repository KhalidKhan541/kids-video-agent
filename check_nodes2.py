import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Check schema
c.execute("PRAGMA table_info(installed_packages)")
for col in c.fetchall():
    print("installed_packages column:", col)

c.execute("PRAGMA table_info(installed_nodes)")
for col in c.fetchall():
    print("installed_nodes column:", col)

c.execute("SELECT * FROM installed_nodes")
rows = c.fetchall()
if rows:
    for row in rows[:5]:  # Show first 5
        print("Node:", row)

conn.close()
