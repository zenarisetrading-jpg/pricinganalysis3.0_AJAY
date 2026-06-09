import argparse
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def apply_sql_migration(path: str, env_name: str = "SUPABASE_DB_URL") -> None:
    db_url = os.getenv(env_name)
    if not db_url:
        raise RuntimeError(f"{env_name} is not set")

    migration_path = Path(path)
    if not migration_path.exists():
        raise RuntimeError(f"Migration file not found: {migration_path}")

    sql = migration_path.read_text(encoding="utf-8")
    with psycopg2.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()

    print(f"Applied migration: {migration_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply a SQL migration using a database URL from .env.")
    parser.add_argument("path", help="Path to the SQL migration file.")
    parser.add_argument("--env", default="SUPABASE_DB_URL", help="Environment variable containing the database URL.")
    args = parser.parse_args()
    apply_sql_migration(args.path, args.env)


if __name__ == "__main__":
    main()
