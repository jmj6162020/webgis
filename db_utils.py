"""
Database Utilities Module
Provides native MySQL database connection and query execution functions
Uses mysql.connector for MariaDB/MySQL connectivity
"""

import mysql.connector
from mysql.connector import Error
import os

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 3306)),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'webgisDB'),
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'autocommit': True
}

# ============================================================================
# CONNECTION MANAGEMENT
# ============================================================================

def get_db_connection():
    """
    Create and return a new database connection
    
    Returns:
        connection: MySQL database connection object
        
    Raises:
        Error: If connection fails
    """
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        raise

def close_connection(connection):
    """
    Close database connection
    
    Args:
        connection: MySQL database connection object
    """
    if connection and connection.is_connected():
        connection.close()

# ============================================================================
# QUERY EXECUTION FUNCTIONS
# ============================================================================

def execute_query(connection, query, params=None):
    """
    Execute a query that modifies data (INSERT, UPDATE, DELETE)
    
    Args:
        connection: MySQL database connection object
        query: SQL query string
        params: Tuple of parameters for parameterized query
        
    Returns:
        int: Last inserted ID for INSERT queries, or affected rows count
        
    Raises:
        Error: If query execution fails
    """
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        connection.commit()
        
        # Return last inserted ID for INSERT queries
        if cursor.lastrowid:
            return cursor.lastrowid
        else:
            return cursor.rowcount
            
    except Error as e:
        connection.rollback()
        print(f"Error executing query: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def fetch_one(connection, query, params=None):
    """
    Fetch a single row from the database
    
    Args:
        connection: MySQL database connection object
        query: SQL query string
        params: Tuple of parameters for parameterized query
        
    Returns:
        dict: Dictionary with column names as keys, or None if no results
        
    Raises:
        Error: If query execution fails
    """
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        result = cursor.fetchone()
        return result
        
    except Error as e:
        print(f"Error fetching data: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def fetch_all(connection, query, params=None):
    """
    Fetch all rows from the database
    
    Args:
        connection: MySQL database connection object
        query: SQL query string
        params: Tuple of parameters for parameterized query
        
    Returns:
        list: List of dictionaries with column names as keys
        
    Raises:
        Error: If query execution fails
    """
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        return results
        
    except Error as e:
        print(f"Error fetching data: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        raise
    finally:
        if cursor:
            cursor.close()

def execute_many(connection, query, params_list):
    """
    Execute a query multiple times with different parameters (batch insert/update)
    
    Args:
        connection: MySQL database connection object
        query: SQL query string
        params_list: List of tuples containing parameters for each execution
        
    Returns:
        int: Number of affected rows
        
    Raises:
        Error: If query execution fails
    """
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.executemany(query, params_list)
        connection.commit()
        return cursor.rowcount
        
    except Error as e:
        connection.rollback()
        print(f"Error executing batch query: {e}")
        print(f"Query: {query}")
        raise
    finally:
        if cursor:
            cursor.close()

def call_procedure(connection, procedure_name, params=None):
    """
    Call a stored procedure
    
    Args:
        connection: MySQL database connection object
        procedure_name: Name of the stored procedure
        params: Tuple of parameters for the procedure
        
    Returns:
        list: Results from the stored procedure
        
    Raises:
        Error: If procedure call fails
    """
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        if params:
            cursor.callproc(procedure_name, params)
        else:
            cursor.callproc(procedure_name)
        
        # Fetch all result sets
        results = []
        for result in cursor.stored_results():
            results.extend(result.fetchall())
        
        connection.commit()
        return results
        
    except Error as e:
        connection.rollback()
        print(f"Error calling procedure: {e}")
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
    """
    Begin a transaction (disable autocommit)
    
    Args:
        connection: MySQL database connection object
    """
    connection.autocommit = False

def commit_transaction(connection):
    """
    Commit current transaction
    
    Args:
        connection: MySQL database connection object
    """
    connection.commit()
    connection.autocommit = True

def rollback_transaction(connection):
    """
    Rollback current transaction
    
    Args:
        connection: MySQL database connection object
    """
    connection.rollback()
    connection.autocommit = True

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def test_connection():
    """
    Test database connection and print server information
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        cursor.close()
        close_connection(conn)
        print(f"Successfully connected to MySQL Server version: {version[0]}")
        return True
    except Error as e:
        print(f"Database connection test failed: {e}")
        return False

def get_table_info(table_name):
    """
    Get information about a table's structure
    
    Args:
        table_name: Name of the table
        
    Returns:
        list: List of column information dictionaries
    """
    conn = get_db_connection()
    result = fetch_all(conn, f"DESCRIBE {table_name}")
    close_connection(conn)
    return result

def execute_raw_sql(connection, sql_file_path):
    """
    Execute raw SQL from a file (useful for running schema files)
    
    Args:
        connection: MySQL database connection object
        sql_file_path: Path to SQL file
        
    Returns:
        bool: True if successful
    """
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_script = file.read()
        
        cursor = connection.cursor()
        # Split by semicolon and execute each statement
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        connection.commit()
        cursor.close()
        return True
        
    except Error as e:
        connection.rollback()
        print(f"Error executing SQL file: {e}")
        return False

