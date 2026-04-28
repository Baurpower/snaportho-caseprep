"""
setup_db.py
===========
Run once to build cpt_codes.db from the SQL file.

Usage:
    python setup_db.py

Optional env vars:
    CPT_SQL_PATH   — path to the .sql file  (default: ./cpt_codes.sql)
    CPT_DB_PATH    — where to write the .db  (default: ./cpt_codes.db)
"""

import os
import sqlite3
from pathlib import Path

SQL_PATH = Path(os.getenv("CPT_SQL_PATH", "cpt_codes.sql"))
DB_PATH  = Path(os.getenv("CPT_DB_PATH",  "cpt_codes.db"))

def main():
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"SQL file not found: {SQL_PATH}")

    if DB_PATH.exists():
        print(f"Database already exists at {DB_PATH} — skipping rebuild.")
        print("To force a rebuild, delete the .db file and re-run.")
        return

    print(f"Building {DB_PATH} from {SQL_PATH} ...")
    conn = sqlite3.connect(DB_PATH)
    try:
        with open(SQL_PATH) as f:
            conn.executescript(f.read())
        conn.commit()
    except Exception as e:
        conn.close()
        DB_PATH.unlink(missing_ok=True)  # clean up partial file
        raise RuntimeError(f"Failed to build database: {e}") from e

    conn.close()

    # Quick sanity check
    conn = sqlite3.connect(DB_PATH)
    codes     = conn.execute("SELECT COUNT(*) FROM cpt_codes").fetchone()[0]
    fellowships = conn.execute("SELECT COUNT(*) FROM fellowships").fetchone()[0]
    fts_rows  = conn.execute("SELECT COUNT(*) FROM cpt_fts").fetchone()[0]
    conn.close()

    print(f"Done.")
    print(f"  CPT codes:   {codes}")
    print(f"  Fellowships: {fellowships}")
    print(f"  FTS rows:    {fts_rows}")

if __name__ == "__main__":
    main()