from sqlalchemy import inspect
from database import engine

# Inspect database tables
print(f"Database URL: {engine.url}")

print("Inspecting database...")
inspector = inspect(engine)
tables = inspector.get_table_names()

print("Tables in the database:")
if not tables:
    print("No tables found.")
else:
    for table in tables:
        print(table)
