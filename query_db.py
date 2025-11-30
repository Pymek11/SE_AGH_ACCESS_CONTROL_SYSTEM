from sqlalchemy import text
from app.core import database


def main():
    engine = database.engine
    with engine.connect() as conn:
        tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"))
        tables = tables.fetchall()
        if not tables:
            print("No tables found in the database.")
            return
        print("Tables:")
        for t in tables:
            print(" -", t[0])

        # Preview the first table
        first_table = tables[0][0]
        print(f"\nPreviewing first table: {first_table}\n")
        rows = conn.execute(text(f"SELECT * FROM {first_table} LIMIT 10;"))
        rows = rows.fetchall()
        if not rows:
            print("(no rows)")
            return
        for r in rows:
            print(r)


if __name__ == '__main__':
    main()
