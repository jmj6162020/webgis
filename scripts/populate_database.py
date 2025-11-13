#!/usr/bin/env python3
"""
Populate the web-gis database with starter data.

This script connects to the MySQL database configured in `db_utils.DB_CONFIG`,
clears all application tables (unless `--skip-truncate` is provided) and
inserts a curated dataset that exercises the main relationships of the system.

User accounts are sourced from a CSV file (default: scripts/user_accounts.csv),
so you can easily customise which accounts are created. The script inspects
the live database schema instead of relying on a static SQL dump, keeping the
population logic in sync with the columns that actually exist in XAMPP.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Dict, Iterable, List, Optional, Tuple

from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db_utils import get_db_connection, close_connection  # noqa: E402


# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------

def get_table_columns(conn, table_name: str) -> List[str]:
    cursor = conn.cursor()
    cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
    columns = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return columns


def truncate_tables(conn, tables: Iterable[str]) -> None:
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    for table in tables:
        cursor.execute(f"TRUNCATE TABLE `{table}`;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    conn.commit()
    cursor.close()


def insert_row(conn, table: str, columns: List[str], row: Dict) -> int:
    available_columns = [col for col in columns if col in row]
    if not available_columns:
        raise ValueError(f"No matching columns found for table `{table}` in row: {row}")

    col_clause = ", ".join(f"`{col}`" for col in available_columns)
    placeholders = ", ".join(["%s"] * len(available_columns))
    values = [row[col] for col in available_columns]

    cursor = conn.cursor()
    cursor.execute(
        f"INSERT INTO `{table}` ({col_clause}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    cursor.close()
    return inserted_id


def insert_or_get_user(conn, table_columns: List[str], record: Dict) -> Tuple[int, bool]:
    """
    Insert a user if they don't exist, or return existing user_id if they do.
    Checks by username or email.
    
    Returns:
        Tuple of (user_id, was_new) where was_new is True if user was just inserted
    """
    cursor = conn.cursor()
    
    # Check if user exists by username or email
    username = record.get("username")
    email = record.get("email")
    
    cursor.execute(
        "SELECT user_id FROM users WHERE username = %s OR email = %s",
        (username, email)
    )
    existing_user = cursor.fetchone()
    
    if existing_user:
        # User already exists, return their ID and False (not new)
        user_id = existing_user[0]
        cursor.close()
        return (user_id, False)
    
    # User doesn't exist, insert them
    available_columns = [col for col in table_columns if col in record]
    if not available_columns:
        cursor.close()
        raise ValueError(f"No matching columns found for table `users` in record: {record}")

    col_clause = ", ".join(f"`{col}`" for col in available_columns)
    placeholders = ", ".join(["%s"] * len(available_columns))
    values = [record[col] for col in available_columns]

    cursor.execute(
        f"INSERT INTO `users` ({col_clause}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    cursor.close()
    return (inserted_id, True)


def insert_or_skip_rock_sample(conn, table_columns: List[str], record: Dict) -> Optional[Tuple[int, bool]]:
    """
    Insert a rock sample if it doesn't exist (by rock_id), or skip if it does.
    
    Returns:
        Tuple of (sample_id, was_new) if inserted, or None if skipped
    """
    cursor = conn.cursor()
    
    # Check if rock sample exists by rock_id
    rock_id = record.get("rock_id")
    if not rock_id:
        cursor.close()
        raise ValueError("rock_id is required for rock sample")
    
    cursor.execute(
        "SELECT sample_id FROM rock_samples WHERE rock_id = %s",
        (rock_id,)
    )
    existing_sample = cursor.fetchone()
    
    if existing_sample:
        # Rock sample already exists, skip it
        cursor.close()
        return None
    
    # Rock sample doesn't exist, insert it
    available_columns = [col for col in table_columns if col in record]
    if not available_columns:
        cursor.close()
        raise ValueError(f"No matching columns found for table `rock_samples` in record: {record}")

    col_clause = ", ".join(f"`{col}`" for col in available_columns)
    placeholders = ", ".join(["%s"] * len(available_columns))
    values = [record[col] for col in available_columns]

    cursor.execute(
        f"INSERT INTO `rock_samples` ({col_clause}) VALUES ({placeholders})",
        values,
    )
    conn.commit()
    inserted_id = cursor.lastrowid
    cursor.close()
    return (inserted_id, True)


# -----------------------------------------------------------------------------
# Data builders
# -----------------------------------------------------------------------------

def read_accounts(csv_path: Path) -> List[Tuple[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        if reader.fieldnames:
            reader.fieldnames = [name.strip() if name else "" for name in reader.fieldnames]
        accounts: List[Tuple[str, str]] = []
        for raw_row in reader:
            row = {(key or "").strip(): (value or "") for key, value in raw_row.items()}
            email = row.get("Email", "").strip()
            password = row.get("Password", "").strip()
            if email and password:
                accounts.append((email, password))
    return accounts


def derive_role(email: str) -> str:
    lower = email.lower()
    if "admin" in lower:
        return "admin"
    if "personnel" in lower or "staff" in lower:
        return "personnel"
    return "student"


def split_name_from_email(email: str) -> Tuple[str, str]:
    local = email.split("@")[0]
    cleaned = local.replace("_", " ").replace(".", " ")
    parts = [part for part in cleaned.split() if part]
    if not parts:
        return ("User", "Sample")
    if len(parts) == 1:
        return (parts[0].title(), "User")
    return (parts[0].title(), parts[1].title())


def build_user_records(accounts: List[Tuple[str, str]]) -> List[Dict]:
    now = datetime.now(timezone.utc)
    records: List[Dict] = []
    student_counter = 1
    for email, password in accounts:
        username = email.split("@")[0]
        role = derive_role(email)
        first_name, last_name = split_name_from_email(email)
        record = {
            "username": username,
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "is_active": 1,
            "created_at": now,
            "updated_at": now,
            "last_login": now,
        }
        if role == "student":
            record["school_id"] = f"STU-{now.year}-{student_counter:04d}"
            student_counter += 1
        records.append(record)
    return records


def choose_user(role_map: Dict[str, List[int]], role: str, fallback: Optional[str] = None) -> Optional[int]:
    users = role_map.get(role, [])
    if users:
        return users[0]
    if fallback:
        return choose_user(role_map, fallback)
    return None


def build_sample_records(role_map: Dict[str, List[int]]) -> List[Dict]:
    now = datetime.now(timezone.utc)
    students = role_map.get("student", [])
    if not students:
        raise RuntimeError("At least one student account is required to populate rock samples.")
    personnel_list = role_map.get("personnel", [])
    if not personnel_list:
        raise RuntimeError("At least one personnel account is required to populate rock samples.")

    # Use multiple personnel for verification diversity
    personnel_primary = personnel_list[0]
    personnel_secondary = personnel_list[1] if len(personnel_list) > 1 else personnel_list[0]
    personnel_tertiary = personnel_list[2] if len(personnel_list) > 2 else personnel_list[0]

    # Expand student list - cycle through all students
    num_students = len(students)

    # Comprehensive list of rock specimens with diverse types and locations
    specimens = [
        # Igneous Rocks - Verified
        {"rock_index": "RS-2025-001", "rock_id": "IG-Alpha-01", "rock_type": "Igneous Rock", "formation": "Basaltic Flow", "description": "Fine-grained igneous rock with visible vesicles.", "location_name": "Butuan", "barangay": "Ampayon", "province": "Agusan del Norte", "latitude": 8.95123, "longitude": 125.544321},
        {"rock_index": "RS-2025-002", "rock_id": "IG-Beta-02", "rock_type": "Igneous Rock", "formation": "Granite Intrusion", "description": "Coarse-grained granite with large feldspar crystals.", "location_name": "Cagayan de Oro", "barangay": "Camaman-an", "province": "Misamis Oriental", "latitude": 8.4779, "longitude": 124.6452},
        {"rock_index": "RS-2025-003", "rock_id": "IG-Gamma-03", "rock_type": "Igneous Rock", "formation": "Andesitic Lava", "description": "Medium-grained andesite with plagioclase phenocrysts.", "location_name": "Iligan", "barangay": "Poblacion", "province": "Lanao del Norte", "latitude": 8.2289, "longitude": 124.2432},
        {"rock_index": "RS-2025-004", "rock_id": "IG-Delta-04", "rock_type": "Igneous Rock", "formation": "Dacite Flow", "description": "Light-colored dacite with quartz and feldspar.", "location_name": "Surigao City", "barangay": "Mat-i", "province": "Surigao del Norte", "latitude": 9.789012, "longitude": 125.495732},
        {"rock_index": "RS-2025-005", "rock_id": "IG-Epsilon-05", "rock_type": "Igneous Rock", "formation": "Rhyolite Dome", "description": "Fine-grained rhyolite with flow banding.", "location_name": "Davao City", "barangay": "Buhangin", "province": "Davao del Sur", "latitude": 7.0735, "longitude": 125.6128},
        {"rock_index": "RS-2025-006", "rock_id": "IG-Zeta-06", "rock_type": "Igneous Rock", "formation": "Obsidian Flow", "description": "Black volcanic glass with conchoidal fracture.", "location_name": "Tagum", "barangay": "Visayan Village", "province": "Davao del Norte", "latitude": 7.4478, "longitude": 125.8078},
        {"rock_index": "RS-2025-007", "rock_id": "IG-Eta-07", "rock_type": "Igneous Rock", "formation": "Pumice Deposit", "description": "Lightweight pumice with numerous vesicles.", "location_name": "General Santos", "barangay": "Calumpang", "province": "South Cotabato", "latitude": 6.1164, "longitude": 125.1716},
        
        # Sedimentary Rocks - Verified
        {"rock_index": "RS-2025-008", "rock_id": "SED-Alpha-08", "rock_type": "Sedimentary Rock", "formation": "Layered Sandstone", "description": "Well-sorted sandstone with ripple marks.", "location_name": "Cabadbaran", "barangay": "Comagascas", "province": "Agusan del Norte", "latitude": 9.125678, "longitude": 125.640987},
        {"rock_index": "RS-2025-009", "rock_id": "SED-Beta-09", "rock_type": "Sedimentary Rock", "formation": "Limestone Bed", "description": "Fossiliferous limestone with marine fossils.", "location_name": "Cebu City", "barangay": "Lahug", "province": "Cebu", "latitude": 10.3157, "longitude": 123.8854},
        {"rock_index": "RS-2025-010", "rock_id": "SED-Gamma-10", "rock_type": "Sedimentary Rock", "formation": "Shale Formation", "description": "Fine-grained shale with laminations.", "location_name": "Bacolod", "barangay": "Villamonte", "province": "Negros Occidental", "latitude": 10.6667, "longitude": 122.9500},
        {"rock_index": "RS-2025-011", "rock_id": "SED-Delta-11", "rock_type": "Sedimentary Rock", "formation": "Conglomerate Layer", "description": "Poorly sorted conglomerate with rounded pebbles.", "location_name": "Iloilo City", "barangay": "Mandurriao", "province": "Iloilo", "latitude": 10.7202, "longitude": 122.5621},
        {"rock_index": "RS-2025-012", "rock_id": "SED-Epsilon-12", "rock_type": "Sedimentary Rock", "formation": "Mudstone Bed", "description": "Very fine-grained mudstone with smooth texture.", "location_name": "Zamboanga City", "barangay": "Tetuan", "province": "Zamboanga del Sur", "latitude": 6.9214, "longitude": 122.0790},
        {"rock_index": "RS-2025-013", "rock_id": "SED-Zeta-13", "rock_type": "Sedimentary Rock", "formation": "Siltstone Layer", "description": "Medium-grained siltstone with cross-bedding.", "location_name": "Cotabato City", "barangay": "Rosary Heights", "province": "Maguindanao", "latitude": 7.2167, "longitude": 124.2500},
        {"rock_index": "RS-2025-014", "rock_id": "SED-Eta-14", "rock_type": "Sedimentary Rock", "formation": "Coal Seam", "description": "Bituminous coal with visible plant fossils.", "location_name": "Dipolog", "barangay": "Miputak", "province": "Zamboanga del Norte", "latitude": 8.5883, "longitude": 123.3419},
        {"rock_index": "RS-2025-015", "rock_id": "SED-Theta-15", "rock_type": "Sedimentary Rock", "formation": "Chert Layer", "description": "Hard, dense chert with conchoidal fracture.", "location_name": "Pagadian", "barangay": "Baliwasan", "province": "Zamboanga del Sur", "latitude": 7.8257, "longitude": 123.4370},
        
        # Metamorphic Rocks - Verified
        {"rock_index": "RS-2025-016", "rock_id": "MET-Alpha-16", "rock_type": "Metamorphic Rock", "formation": "Schist Facies", "description": "Shiny schist with prominent mica alignment.", "location_name": "Baguio", "barangay": "Session Road", "province": "Benguet", "latitude": 16.4023, "longitude": 120.5960},
        {"rock_index": "RS-2025-017", "rock_id": "MET-Beta-17", "rock_type": "Metamorphic Rock", "formation": "Gneiss Band", "description": "Banded gneiss with alternating light and dark layers.", "location_name": "Bontoc", "barangay": "Poblacion", "province": "Mountain Province", "latitude": 17.0875, "longitude": 120.9756},
        {"rock_index": "RS-2025-018", "rock_id": "MET-Gamma-18", "rock_type": "Metamorphic Rock", "formation": "Marble Quarry", "description": "White marble with calcite crystals.", "location_name": "Romblon", "barangay": "Cajidiocan", "province": "Romblon", "latitude": 12.5753, "longitude": 122.2708},
        {"rock_index": "RS-2025-019", "rock_id": "MET-Delta-19", "rock_type": "Metamorphic Rock", "formation": "Quartzite Outcrop", "description": "Hard quartzite with interlocking quartz grains.", "location_name": "Palawan", "barangay": "Puerto Princesa", "province": "Palawan", "latitude": 9.8349, "longitude": 118.7384},
        {"rock_index": "RS-2025-020", "rock_id": "MET-Epsilon-20", "rock_type": "Metamorphic Rock", "formation": "Slate Formation", "description": "Fine-grained slate with excellent cleavage.", "location_name": "Marikina", "barangay": "San Roque", "province": "Metro Manila", "latitude": 14.6507, "longitude": 121.1029},
        {"rock_index": "RS-2025-021", "rock_id": "MET-Zeta-21", "rock_type": "Metamorphic Rock", "formation": "Amphibolite Layer", "description": "Dark amphibolite with hornblende and plagioclase.", "location_name": "Quezon City", "barangay": "Diliman", "province": "Metro Manila", "latitude": 14.6515, "longitude": 121.0500},
        
        # More Igneous Rocks - Verified
        {"rock_index": "RS-2025-022", "rock_id": "IG-Theta-22", "rock_type": "Igneous Rock", "formation": "Basalt Column", "description": "Columnar jointed basalt from lava flow.", "location_name": "Legazpi", "barangay": "Rawis", "province": "Albay", "latitude": 13.1390, "longitude": 123.7440},
        {"rock_index": "RS-2025-023", "rock_id": "IG-Iota-23", "rock_type": "Igneous Rock", "formation": "Gabbro Intrusion", "description": "Coarse-grained gabbro with pyroxene and plagioclase.", "location_name": "Naga", "barangay": "Pacol", "province": "Camarines Sur", "latitude": 13.6192, "longitude": 123.1814},
        {"rock_index": "RS-2025-024", "rock_id": "IG-Kappa-24", "rock_type": "Igneous Rock", "formation": "Diorite Pluton", "description": "Medium-grained diorite with equal feldspar and mafic minerals.", "location_name": "Calapan", "barangay": "Sta. Isabel", "province": "Oriental Mindoro", "latitude": 13.4125, "longitude": 121.1794},
        
        # More Sedimentary - Pending (for testing)
        {"rock_index": "RS-2025-025", "rock_id": "SED-Iota-25", "rock_type": "Sedimentary Rock", "formation": "Breccia Deposit", "description": "Angular fragments in a fine-grained matrix.", "location_name": "Tacloban", "barangay": "Downtown", "province": "Leyte", "latitude": 11.2444, "longitude": 125.0039},
        {"rock_index": "RS-2025-026", "rock_id": "SED-Kappa-26", "rock_type": "Sedimentary Rock", "formation": "Chalk Bed", "description": "Soft white chalk composed of microscopic shells.", "location_name": "Ormoc", "barangay": "Linao", "province": "Leyte", "latitude": 11.0067, "longitude": 124.6078},
        
        # More Metamorphic - Pending
        {"rock_index": "RS-2025-027", "rock_id": "MET-Eta-27", "rock_type": "Metamorphic Rock", "formation": "Phyllite Layer", "description": "Fine-grained phyllite with silky sheen.", "location_name": "Bacolod", "barangay": "Bata", "province": "Negros Occidental", "latitude": 10.6311, "longitude": 122.9508},
        
        # Rejected samples
        {"rock_index": "RS-2025-028", "rock_id": "IG-Lambda-28", "rock_type": "Igneous Rock", "formation": "Unknown", "description": "Poor quality sample with unclear identification.", "location_name": "Butuan", "barangay": "Libertad", "province": "Agusan del Norte", "latitude": 8.9475, "longitude": 125.5406},
    ]

    # Distribute samples across students and assign statuses
    # Most samples should be verified so students can see them
    # Total: 28 specimens (24 verified, 3 pending, 1 rejected)
    statuses = (
        ["verified"] * 24 +  # 24 verified samples
        ["pending"] * 3 +    # 3 pending samples
        ["rejected"] * 1     # 1 rejected sample
    )
    
    # Distribute personnel verifiers (for 24 verified + 1 rejected = 25 verifications)
    verifiers = (
        [personnel_primary] * 9 +
        [personnel_secondary] * 9 +
        [personnel_tertiary] * 7
    )
    
    # Cycle through students to distribute samples
    records: List[Dict] = []
    verifier_counter = 0  # Counter for assigning verifiers
    
    for idx, (specimen, status) in enumerate(zip(specimens, statuses)):
        # Cycle through students
        student_idx = idx % num_students
        submitter = students[student_idx]
        
        record = {
            "user_id": submitter,
            "status": status,
            "created_at": now,
            "updated_at": now,
        }
        
        if status in ("verified", "rejected"):
            # Use appropriate verifier (only increment counter for verified/rejected)
            if verifier_counter < len(verifiers):
                record["verified_by"] = verifiers[verifier_counter]
                verifier_counter += 1
            else:
                # Fallback if we run out of verifiers
                record["verified_by"] = personnel_primary
        
        record.update(specimen)
        records.append(record)

    return records


def build_approval_logs(sample_map: Dict[int, Dict]) -> List[Dict]:
    """Build approval logs using the verified_by field from each sample."""
    now = datetime.now(timezone.utc)
    approvals: List[Dict] = []
    for sample_id, sample in sample_map.items():
        verifier_id = sample.get("verified_by")
        if not verifier_id:
            continue
            
        if sample["status"] == "verified":
            approvals.append(
                {
                    "user_id": verifier_id,
                    "sample_id": sample_id,
                    "action": "approved",
                    "remarks": "Approved during data population.",
                    "timestamp": now,
                }
            )
        elif sample["status"] == "rejected":
            approvals.append(
                {
                    "user_id": verifier_id,
                    "sample_id": sample_id,
                    "action": "rejected",
                    "remarks": "Rejected during data population.",
                    "timestamp": now,
                }
            )
    return approvals


def build_archive_records(sample_ids: List[int], admin_id: Optional[int]) -> List[Dict]:
    if not sample_ids or not admin_id:
        return []
    now = datetime.now(timezone.utc)
    return [
        {
            "sample_id": sample_ids[0],
            "archived_by": admin_id,
            "archived_at": now,
            "archive_reason": "Archived during data population.",
            "status": "archived",
        }
    ]


def build_activity_logs(sample_map: Dict[int, Dict], role_map: Dict[str, List[int]]) -> List[Dict]:
    now = datetime.now(timezone.utc)
    admin_id = choose_user(role_map, "admin", fallback="personnel")
    logs: List[Dict] = []
    for sample_id, sample in sample_map.items():
        submitter = sample["user_id"]
        logs.append(
            {
                "user_id": submitter,
                "sample_id": sample_id,
                "activity_type": "submitted",
                "description": f"Submitted sample {sample['rock_id']}.",
                "timestamp": now,
            }
        )
        if sample["status"] == "verified":
            logs.append(
                {
                    "user_id": sample.get("verified_by"),
                    "sample_id": sample_id,
                    "activity_type": "approved",
                    "description": f"Approved sample {sample['rock_id']}.",
                    "timestamp": now,
                }
            )
        elif sample["status"] == "rejected":
            logs.append(
                {
                    "user_id": sample.get("verified_by"),
                    "sample_id": sample_id,
                    "activity_type": "rejected",
                    "description": f"Rejected sample {sample['rock_id']}.",
                    "timestamp": now,
                }
            )
    if admin_id and sample_map:
        any_sample_id = next(iter(sample_map))
        logs.append(
            {
                "user_id": admin_id,
                "sample_id": any_sample_id,
                "activity_type": "archived",
                "description": f"Archived sample {sample_map[any_sample_id]['rock_id']}.",
                "timestamp": now,
            }
        )
    return logs


# -----------------------------------------------------------------------------
# Main population logic
# -----------------------------------------------------------------------------

def populate_database(csv_path: Path, skip_truncate: bool = False) -> None:
    conn = get_db_connection()
    try:
        tables = [
            "activity_logs",
            "approval_logs",
            "archives",
            "images",
            "rock_samples",
            "users",
        ]

        if not skip_truncate:
            print("Truncating tables…")
            truncate_tables(conn, tables)

        table_columns = {table: get_table_columns(conn, table) for table in tables}

        # Insert users --------------------------------------------------------
        accounts = read_accounts(csv_path)
        if not accounts:
            raise RuntimeError("No accounts found in CSV. Aborting population.")
        user_records = build_user_records(accounts)
        role_map: Dict[str, List[int]] = {"admin": [], "personnel": [], "student": []}

        print("Inserting users…")
        new_users = 0
        existing_users = 0
        
        for record in user_records:
            password_plain = record.pop("password")
            record["password_hash"] = generate_password_hash(password_plain)
            
            # Check if user exists and get their ID, or insert if new
            user_id, was_new = insert_or_get_user(conn, table_columns["users"], record)
            
            # Track new vs existing users
            if was_new:
                new_users += 1
            else:
                existing_users += 1
            
            # Always add to role map (avoid duplicates)
            if user_id not in role_map.get(record["role"], []):
                role_map.setdefault(record["role"], []).append(user_id)
        
        total_users = sum(len(ids) for ids in role_map.values())
        if skip_truncate:
            print(f"  → Processed {len(user_records)} users ({new_users} new, {existing_users} existing).")
        else:
            print(f"  → Inserted {total_users} users.")

        # Insert rock samples -------------------------------------------------
        print("Inserting rock samples…")
        sample_records = build_sample_records(role_map)
        sample_ids: List[int] = []
        sample_map: Dict[int, Dict] = {}
        new_samples = 0
        skipped_samples = 0
        
        for record in sample_records:
            if skip_truncate:
                # Check if rock sample already exists and skip if it does
                result = insert_or_skip_rock_sample(conn, table_columns["rock_samples"], record)
                if result is None:
                    # Sample already exists, skip it
                    skipped_samples += 1
                    continue
                inserted_id, _ = result
                new_samples += 1
            else:
                # Normal insert (will fail if duplicate, but that's expected in truncate mode)
                inserted_id = insert_row(conn, "rock_samples", table_columns["rock_samples"], record)
                new_samples += 1
            
            sample_ids.append(inserted_id)
            sample_map[inserted_id] = record
        
        if skip_truncate:
            print(f"  → Processed {len(sample_records)} rock samples ({new_samples} new, {skipped_samples} skipped).")
        else:
            print(f"  → Inserted {len(sample_ids)} rock samples.")

        # Insert approval logs -----------------------------------------------
        if sample_map:
            print("Recording approvals…")
            approval_columns = table_columns["approval_logs"]
            approval_records = build_approval_logs(sample_map)
            
            if skip_truncate:
                # Check for existing approval logs to avoid duplicates
                new_approvals = 0
                skipped_approvals = 0
                cursor = conn.cursor()
                for record in approval_records:
                    # Check if approval log already exists
                    cursor.execute(
                        "SELECT approval_id FROM approval_logs WHERE user_id = %s AND sample_id = %s AND action = %s",
                        (record["user_id"], record["sample_id"], record["action"])
                    )
                    if cursor.fetchone():
                        skipped_approvals += 1
                        continue
                    
                    # Insert new approval log
                    insert_row(conn, "approval_logs", approval_columns, record)
                    new_approvals += 1
                cursor.close()
                print(f"  → Logged {new_approvals} new approvals ({skipped_approvals} skipped).")
            else:
                for record in approval_records:
                    insert_row(conn, "approval_logs", approval_columns, record)
                    print(f"  → Logged {len(approval_records)} approvals.")
                else:
                    print("  → No new samples to create approval logs for.")

        # Insert archives -----------------------------------------------------
        archive_columns = table_columns["archives"]
        archive_records = build_archive_records(sample_ids, choose_user(role_map, "admin", fallback="personnel"))
        for record in archive_records:
            insert_row(conn, "archives", archive_columns, record)
        if archive_records:
            print(f"  → Archived {len(archive_records)} sample(s).")
        else:
            print("  → No archives created (missing admin/personnel account).")

        # Insert placeholder images ------------------------------------------
        if sample_ids:
            image_columns = table_columns["images"]
            print("Inserting placeholder images…")
            placeholder_bytes = b""
            new_images = 0
            skipped_images = 0
            
            cursor = conn.cursor()
        for sample_id in sample_ids:
            for image_type in ("rock_specimen", "outcrop"):
                    if skip_truncate:
                        # Check if image already exists
                        cursor.execute(
                            "SELECT image_id FROM images WHERE sample_id = %s AND image_type = %s",
                            (sample_id, image_type)
                        )
                        if cursor.fetchone():
                            skipped_images += 1
                            continue
                    
                            record = {
                                "sample_id": sample_id,
                                "image_type": image_type,
                                "image_data": placeholder_bytes,
                                "file_name": f"{image_type}_{sample_id}.png",
                                "file_size": 0,
                                "mime_type": "image/png",
                                    "created_at": datetime.now(timezone.utc),
                            }
                            insert_row(conn, "images", image_columns, record)
                            new_images += 1
            cursor.close()
            
            if skip_truncate:
                print(f"  → Added {new_images} new images ({skipped_images} skipped).")
            else:
                print(f"  → Added {len(sample_ids) * 2} placeholder images.")
        else:
            print("  → No new samples to create images for.")

        # Insert activity logs ------------------------------------------------
        if sample_map:
            print("Creating activity logs…")
            activity_columns = table_columns["activity_logs"]
            activity_records = build_activity_logs(sample_map, role_map)
            
            if skip_truncate:
                # Check for existing activity logs to avoid duplicates
                new_logs = 0
                skipped_logs = 0
                cursor = conn.cursor()
                for record in activity_records:
                    # Check if activity log already exists (by sample_id, activity_type, and description)
                    cursor.execute(
                        "SELECT activity_id FROM activity_logs WHERE user_id = %s AND sample_id = %s AND activity_type = %s AND description = %s",
                        (record["user_id"], record["sample_id"], record["activity_type"], record["description"])
                    )
                    if cursor.fetchone():
                        skipped_logs += 1
                        continue
                    
                    # Insert new activity log
                    insert_row(conn, "activity_logs", activity_columns, record)
                    new_logs += 1
                cursor.close()
                print(f"  → Stored {new_logs} new activity log entries ({skipped_logs} skipped).")
            else:
                for record in activity_records:
                    insert_row(conn, "activity_logs", activity_columns, record)
                print(f"  → Stored {len(activity_records)} activity log entries.")
        else:
            print("  → No new samples to create activity logs for.")

        print("\nDatabase population complete.")

    finally:
        close_connection(conn)


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate the web-gis database with sample data.")
    parser.add_argument(
        "--accounts-csv",
        type=Path,
        default=Path(__file__).resolve().parent / "user_accounts.csv",
        help="CSV file with Email and Password columns (default: scripts/user_accounts.csv)",
    )
    parser.add_argument(
        "--skip-truncate",
        action="store_true",
        help="Skip truncating tables before inserting data (adds on top of existing rows).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    populate_database(args.accounts_csv, skip_truncate=args.skip_truncate)

