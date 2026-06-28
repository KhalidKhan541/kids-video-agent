import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Get all installed node types
c.execute("SELECT name FROM installed_packages")
packages = [r[0] for r in c.fetchall()]
print("Installed packages:", packages)

c.execute("SELECT nodeType FROM installed_nodes")
nodes = [r[0] for r in c.fetchall()]
print("\nInstalled custom nodes:", nodes)

conn.close()
