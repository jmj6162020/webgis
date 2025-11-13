"""
Authentication Utilities Module
Provides authentication and authorization decorators for Flask routes
Implements role-based access control
"""

from functools import wraps
from flask import session, redirect, url_for, flash, abort

# ============================================================================
# AUTHENTICATION DECORATORS
# ============================================================================

def login_required(f):
    """
    Decorator to require user authentication for a route
    Redirects to login page if user is not authenticated
    
    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "This is protected"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    """
    Decorator to require specific user role(s) for a route
    Returns 403 error if user doesn't have required role
    
    Args:
        *roles: Variable number of role strings (e.g., 'admin', 'personnel', 'student')
        
    Usage:
        @app.route('/admin-only')
        @login_required
        @role_required('admin')
        def admin_route():
            return "Admin only"
            
        @app.route('/staff')
        @login_required
        @role_required('admin', 'personnel')
        def staff_route():
            return "Admin or Personnel only"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'role' not in session:
                flash('Please login to access this page', 'warning')
                return redirect(url_for('login'))
            
            if session['role'] not in roles:
                flash('You do not have permission to access this page', 'danger')
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============================================================================
# AUTHORIZATION HELPER FUNCTIONS
# ============================================================================

def is_authenticated():
    """
    Check if current user is authenticated
    
    Returns:
        bool: True if user is logged in, False otherwise
    """
    return 'user_id' in session

def get_current_user_id():
    """
    Get current user's ID from session
    
    Returns:
        int: User ID if authenticated, None otherwise
    """
    return session.get('user_id')

def get_current_username():
    """
    Get current user's username from session
    
    Returns:
        str: Username if authenticated, None otherwise
    """
    return session.get('username')

def get_current_user_role():
    """
    Get current user's role from session
    
    Returns:
        str: User role ('admin', 'personnel', or 'student') if authenticated, None otherwise
    """
    return session.get('role')

def get_current_user_full_name():
    """
    Get current user's full name from session
    
    Returns:
        str: Full name if authenticated, None otherwise
    """
    return session.get('full_name')

def is_admin():
    """
    Check if current user is an admin
    
    Returns:
        bool: True if user is admin, False otherwise
    """
    return session.get('role') == 'admin'

def is_personnel():
    """
    Check if current user is personnel
    
    Returns:
        bool: True if user is personnel, False otherwise
    """
    return session.get('role') == 'personnel'

def is_student():
    """
    Check if current user is a student
    
    Returns:
        bool: True if user is student, False otherwise
    """
    return session.get('role') == 'student'

def has_role(*roles):
    """
    Check if current user has one of the specified roles
    
    Args:
        *roles: Variable number of role strings
        
    Returns:
        bool: True if user has one of the roles, False otherwise
    """
    current_role = session.get('role')
    return current_role in roles

def can_access_resource(resource_user_id):
    """
    Check if current user can access a resource owned by another user
    Admins and personnel can access any resource
    Students can only access their own resources
    
    Args:
        resource_user_id: The user_id of the resource owner
        
    Returns:
        bool: True if user can access the resource, False otherwise
    """
    if not is_authenticated():
        return False
    
    # Admins and personnel can access any resource
    if is_admin() or is_personnel():
        return True
    
    # Students can only access their own resources
    return get_current_user_id() == resource_user_id

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

def create_user_session(user_data):
    """
    Create a user session with user data
    
    Args:
        user_data: Dictionary containing user information from database
    """
    session['user_id'] = user_data['user_id']
    session['username'] = user_data['username']
    session['role'] = user_data['role']
    session['full_name'] = f"{user_data['first_name']} {user_data['last_name']}"

def clear_user_session():
    """
    Clear the user session (logout)
    """
    session.clear()

def update_session_data(key, value):
    """
    Update a specific key in the session
    
    Args:
        key: Session key to update
        value: New value for the key
    """
    session[key] = value

# ============================================================================
# PERMISSION CHECKS
# ============================================================================

def can_verify_samples():
    """
    Check if current user can verify rock samples
    Only personnel and admin can verify
    
    Returns:
        bool: True if user can verify, False otherwise
    """
    return has_role('admin', 'personnel')

def can_manage_users():
    """
    Check if current user can manage users
    Only admin can manage users
    
    Returns:
        bool: True if user can manage users, False otherwise
    """
    return is_admin()

def can_archive_samples():
    """
    Check if current user can archive rock samples
    Only admin can archive
    
    Returns:
        bool: True if user can archive, False otherwise
    """
    return is_admin()

def can_delete_users():
    """
    Check if current user can delete users
    Only admin can delete users
    
    Returns:
        bool: True if user can delete users, False otherwise
    """
    return is_admin()

def can_view_all_logs():
    """
    Check if current user can view all activity logs
    Admin and personnel can view all logs
    Students can only view their own
    
    Returns:
        bool: True if user can view all logs, False otherwise
    """
    return has_role('admin', 'personnel')

def can_submit_samples():
    """
    Check if current user can submit rock samples
    Only students can submit samples
    
    Returns:
        bool: True if user can submit samples, False otherwise
    """
    return is_student()

# ============================================================================
# CONTEXT PROCESSOR HELPERS
# ============================================================================

def get_current_user():
    """
    Get the full current user data from database
    
    Returns:
        dict: User data or None if not authenticated or on database error
    """
    if not is_authenticated():
        return None
    
    try:
        from db_utils import get_db_connection, fetch_one, close_connection
        
        user_id = session.get('user_id')
        if not user_id:
            return None
            
        conn = get_db_connection()
        user = fetch_one(conn, "SELECT * FROM users WHERE user_id = %s", (user_id,))
        close_connection(conn)
        return user
    except Exception as e:
        # Database connection failed - log and return None to prevent crashes
        print(f"Database error getting current user: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_session_context():
    """
    Get session data as a context dictionary for templates
    
    Returns:
        dict: Dictionary with session information
    """
    return {
        'is_authenticated': is_authenticated(),
        'current_user_id': get_current_user_id(),
        'current_username': get_current_username(),
        'current_user_role': get_current_user_role(),
        'current_user_full_name': get_current_user_full_name(),
        'is_admin': is_admin(),
        'is_personnel': is_personnel(),
        'is_student': is_student(),
        'current_user': get_current_user()
    }

