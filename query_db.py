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

        # Show unauthorized access logs (if table exists)
        if any(t[0] == "unauthorized_access" for t in tables):
            count = conn.execute(text("SELECT COUNT(*) FROM unauthorized_access;")).scalar_one()
            print(f"\nunauthorized_access rows: {count}\n")
            rows = conn.execute(
                text(
                    """
                    SELECT id, qr_text, created_at,
                           CASE WHEN photo IS NULL THEN 0 ELSE length(photo) END AS photo_bytes
                    FROM unauthorized_access
                    ORDER BY id DESC
                    LIMIT 10;
                    """
                )
            ).fetchall()
            if rows:
                print("Latest unauthorized_access rows:")
                for r in rows:
                    print(r)
            else:
                print("(no unauthorized_access rows yet)")

        # Preview the employees table (if present)
        if any(t[0] == "employees" for t in tables):
            print("\nPreviewing employees (up to 10 rows)\n")
            rows = conn.execute(
                text("SELECT emp_id, emp_name, created_at FROM employees ORDER BY emp_id DESC LIMIT 10;")
            ).fetchall()
            if not rows:
                print("(no employees rows)")
            else:
                for r in rows:
                    print(r)


if __name__ == '__main__':
    main()
