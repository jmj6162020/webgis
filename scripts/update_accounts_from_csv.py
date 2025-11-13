#!/usr/bin/env python3
"""
Update user account passwords based on a CSV file.

The CSV is expected to contain two columns named `Email` and `Password`.
Rows with missing values are ignored. Existing passwords are overwritten
with the new values using Werkzeug's `generate_password_hash`.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db_utils import get_db_connection, close_connection  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update user accounts based on a CSV file.")
    parser.add_argument(
        "csv_path",
        type=Path,
        help="Path to the CSV file containing `Email` and `Password` columns.",
    )
    return parser.parse_args()


def update_accounts(csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    updates = []
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames:
            reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
        for raw_row in reader:
            row = { (key or "").strip(): (value or "") for key, value in raw_row.items() }
            email = row.get("Email", "").strip()
            password = row.get("Password", "").strip()
            if email and password:
                updates.append((email, password))

    if not updates:
        print("No valid entries found in CSV. Nothing to update.")
        return

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE email = %s"

        updated_count = 0
        for email, plain_password in updates:
            password_hash = generate_password_hash(plain_password)
            cursor.execute(query, (password_hash, email))
            if cursor.rowcount:
                updated_count += 1
            else:
                print(f"Warning: no user found with email {email}")

        conn.commit()
        cursor.close()
        print(f"Password update complete. {updated_count}/{len(updates)} accounts updated.")
    finally:
        close_connection(conn)


if __name__ == "__main__":
    args = parse_args()
    update_accounts(args.csv_path)


