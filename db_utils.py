"""
Database Utilities Module
Provides native MySQL database connection and query execution functions
Uses mysql.connector for MariaDB/MySQL connectivity
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load .env file (for local development)
load_dotenv()

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'srv2046.hostinger.com'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'u178238182_webgiscaps'),
    'password': os.environ.get('DB_PASSWORD', 'Webgis123456'),
    'database': os.environ.get('DB_NAME', 'u178238182_webgis'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

print("🔍 DATABASE CONFIGURATION (startup check):")
for k, v in DB_CONFIG.items():
    if k != 'password':
        print(f"  {k}: {v}")

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

def get_db_connection():
    """Create and return a new database connection."""
    try:
        print(f"Connecting to MySQL at {DB_CONFIG['host']}:{DB_CONFIG['port']} as {DB_CONFIG['user']}")
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("✅ Connected to MySQL successfully!")
            return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL database: {e}")
        raise

def close_connection(connection):
    """Close database connection."""
    if connection and connection.is_connected():
        connection.close()

# ============================================================================
# QUERY EXECUTION FUNCTIONS
# ============================================================================

def execute_query(connection, query, params=None):
    """Execute INSERT, UPDATE, or DELETE query."""
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        connection.commit()
        return cursor.lastrowid or cursor.rowcount
    except Error as e:
        connection.rollback()
        print(f"❌ Error executing query: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def fetch_one(connection, query, params=None):
    """Fetch a single row."""
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchone()
    except Error as e:
        print(f"❌ Error fetching data: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def fetch_all(connection, query, params=None):
    """Fetch all rows."""
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Error as e:
        print(f"❌ Error fetching data: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def execute_many(connection, query, params_list):
    """Execute a query multiple times (batch insert/update)."""
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.executemany(query, params_list)
        connection.commit()
        return cursor.rowcount
    except Error as e:
        connection.rollback()
        print(f"❌ Error executing batch query: {e}")
        print(f"Query: {query}")
        raise
    finally:
        if cursor:
            cursor.close()

def call_procedure(connection, procedure_name, params=None):
    """Call a stored procedure."""
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.callproc(procedure_name, params or ())
        results = []
        for result in cursor.stored_results():
            results.extend(result.fetchall())
        connection.commit()
        return results
    except Error as e:
        connection.rollback()
        print(f"❌ Error calling procedure: {e}")
        print(f"Procedure: {procedure_name}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

# ============================================================================
# TRANSACTION MANAGEMENT
# ============================================================================

def begin_transaction(connection):
    """Begin a transaction."""
    connection.autocommit = False

def commit_transaction(connection):
    """Commit current transaction."""
    connection.commit()
    connection.autocommit = True

def rollback_transaction(connection):
    """Rollback current transaction."""
    connection.rollback()
    connection.autocommit = True

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def test_connection():
    """Test database connection."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        close_connection(conn)
        print(f"✅ Connected to MySQL Server version: {version[0]}")
        return True
    except Error as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def get_table_info(table_name):
    """Get information about a table's structure."""
    conn = get_db_connection()
    result = fetch_all(conn, f"DESCRIBE {table_name}")
    close_connection(conn)
    return result

def execute_raw_sql(connection, sql_file_path):
    """Execute raw SQL from a file (schema import)."""
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        cursor = connection.cursor()
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        connection.commit()
        cursor.close()
        return True
    except Error as e:
        connection.rollback()
        print(f"❌ Error executing SQL file: {e}")
        return False
