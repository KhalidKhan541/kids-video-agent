import sqlite3
conn = sqlite3.connect(r'C:\Users\khali\.n8n\database.sqlite')
c = conn.cursor()

# Get installed packages
c.execute("SELECT packageName FROM installed_packages")
packages = [r[0] for r in c.fetchall()]
print("Installed packages:", packages)

# Get installed nodes
c.execute("SELECT name, type, package FROM installed_nodes")
nodes = c.fetchall()
if nodes:
    print(f"\nInstalled nodes ({len(nodes)}):")
    for row in nodes:
        print(f"  {row[0]} ({row[1]}) from {row[2]}")
else:
    print("\nNo custom nodes installed")

# Check if executeCommand exists
c.execute("SELECT * FROM installed_nodes WHERE name LIKE '%execute%' OR name LIKE '%command%' OR name LIKE '%exec%'")
found = c.fetchall()
print("\nExecute-related nodes:", found if found else "None found")

conn.close()
