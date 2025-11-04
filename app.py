from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
import io
import os
from db_utils import get_db_connection, execute_query, fetch_one, fetch_all, close_connection
from auth_utils import login_required, role_required

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Note: Bootstrap is loaded via CDN in templates, no need for Flask-Bootstrap extension

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def log_activity(conn, user_id, activity_type, description, sample_id=None):
    """
    Log user activity to the database
    
    Args:
        conn: Database connection
        user_id: ID of the user performing the action
        activity_type: Type of activity performed
        description: Detailed description of the activity
        sample_id: Optional sample ID related to the activity
    """
    try:
        execute_query(conn,
            """INSERT INTO activity_logs (user_id, sample_id, activity_type, description, timestamp)
               VALUES (%s, %s, %s, %s, NOW())""",
            (user_id, sample_id, activity_type, description))
    except Exception as e:
        print(f"Error logging activity: {e}")

# ============================================================================
# CONTEXT PROCESSORS
# ============================================================================

@app.context_processor
def inject_user_data():
    """Inject user session data into all templates"""
    from auth_utils import get_session_context
    return get_session_context()

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.route('/')
def index():
    """Redirect to appropriate dashboard based on user role or login page"""
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'personnel':
            return redirect(url_for('personnel_dashboard'))
        elif role == 'student':
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        # Email-only login
        email = request.form.get('email')
        password = request.form.get('password')
        selected_role = request.form.get('organization', 'student')  # Get selected organization/role
        
        conn = get_db_connection()
        # Lookup by email only
        user = fetch_one(conn, 
            "SELECT * FROM users WHERE email = %s AND is_active = TRUE",
            (email,))
        
        if user and check_password_hash(user['password_hash'], password):
            # Check if user's actual role matches the selected role
            if user['role'] != selected_role:
                close_connection(conn)
                flash(f'Invalid role selection. Please select "{user["role"].title()}" for this account.', 'danger')
                return render_template('login.html')
            
            # Update last login
            execute_query(conn,
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s",
                (user['user_id'],))
            
            # Set session variables
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = f"{user['first_name']} {user['last_name']}"
            
            close_connection(conn)
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            close_connection(conn)
            flash('Invalid credentials or inactive account', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle new user registration"""
    if request.method == 'POST':
        # Get form data - support both fullname split or separate first/last names
        fullname = request.form.get('fullname', '')
        email = request.form.get('email')
        password = request.form.get('password')
        student_id = request.form.get('student_id')
        
        # Split fullname into first and last name
        name_parts = fullname.strip().split(' ', 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Create username from email (before @)
        username = email.split('@')[0] if email else ''
        
        # Hash password
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            # Enforce uniqueness: prevent duplicate email or school_id
            existing_user = fetch_one(
                conn,
                """
                SELECT user_id, email, school_id
                FROM users
                WHERE email = %s OR school_id = %s
                """,
                (email, student_id),
            )

            if existing_user:
                # Build specific error message(s)
                duplicate_fields = []
                if existing_user.get('email') == email:
                    duplicate_fields.append('email')
                if existing_user.get('school_id') == student_id:
                    duplicate_fields.append('school ID')
                msg = ' and '.join(duplicate_fields).title() + ' already exists'
                close_connection(conn)
                flash(msg, 'danger')
                return render_template('signup.html')

            execute_query(conn,
                """INSERT INTO users (username, email, password_hash, first_name, last_name, 
                   role, school_id, is_active) 
                   VALUES (%s, %s, %s, %s, %s, 'student', %s, TRUE)""",
                (username, email, password_hash, first_name, last_name, student_id))
            close_connection(conn)
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            close_connection(conn)
            flash(f'Registration failed: Username or email already exists', 'danger')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# ============================================================================
# STUDENT ROUTES
# ============================================================================

@app.route('/student/dashboard')
@login_required
@role_required('student')
def student_dashboard():
    """Student dashboard with statistics and recent submissions"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # Get student information
    student = fetch_one(conn,
        """SELECT first_name, last_name FROM users WHERE user_id = %s""",
        (user_id,))
    
    # Get basic statistics
    stats = fetch_one(conn,
        """SELECT 
            COUNT(*) as total_submissions,
            SUM(CASE WHEN status = 'verified' THEN 1 ELSE 0 END) as verified_count,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
            SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count
        FROM rock_samples WHERE user_id = %s""",
        (user_id,))
    
    # Get additional statistics
    additional_stats = fetch_one(conn,
        """SELECT 
            COUNT(DISTINCT rock_type) as unique_rock_types,
            COUNT(DISTINCT location_name) as unique_locations
        FROM rock_samples WHERE user_id = %s""",
        (user_id,))
    
    # Merge statistics
    if stats:
        stats.update(additional_stats or {})
    
    # Get recent submissions
    recent_rocks = fetch_all(conn,
        """SELECT * FROM rock_samples 
           WHERE user_id = %s 
           ORDER BY created_at DESC LIMIT 10""",
        (user_id,))
    
    close_connection(conn)
    return render_template('students/dashboard.html', stats=stats, recent_rocks=recent_rocks, student=student)

@app.route('/student/add-rock', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_add_rock():
    """Add new rock sample submission"""
    if request.method == 'POST':
        user_id = session['user_id']
        rock_index = request.form.get('rock_index')
        rock_id = request.form.get('rock_id')
        rock_type = request.form.get('rock_type')
        description = request.form.get('description', '')
        formation = request.form.get('formation', '')
        outcrop_id = request.form.get('outcrop_id', '')
        location_name = request.form.get('location_name')
        
        # Handle optional latitude/longitude
        latitude_str = request.form.get('latitude', '')
        longitude_str = request.form.get('longitude', '')
        latitude = float(latitude_str) if latitude_str else None
        longitude = float(longitude_str) if longitude_str else None
        
        rock_specimen = request.files.get('rock_specimen')
        outcrop_image = request.files.get('outcrop_image')
        
        conn = get_db_connection()
        try:
            # Insert rock sample
            sample_id = execute_query(conn,
                """INSERT INTO rock_samples (user_id, rock_index, rock_id, rock_type, 
                   description, formation, outcrop_id, location_name, latitude, longitude, 
                   status, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', NOW())""",
                (user_id, rock_index, rock_id, rock_type, description, formation, 
                 outcrop_id, location_name, latitude, longitude))
            
            # Insert rock specimen image
            if rock_specimen:
                rock_specimen_data = rock_specimen.read()
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'rock_specimen', %s, %s, %s, %s, NOW())""",
                    (sample_id, rock_specimen_data, rock_specimen.filename,
                     len(rock_specimen_data), rock_specimen.content_type))
            
            # Insert outcrop image
            if outcrop_image:
                outcrop_image_data = outcrop_image.read()
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'outcrop', %s, %s, %s, %s, NOW())""",
                    (sample_id, outcrop_image_data, outcrop_image.filename,
                     len(outcrop_image_data), outcrop_image.content_type))
            
            # Log activity
            log_activity(conn, user_id, 'submitted', 
                        f'Submitted rock sample: {rock_id} - {rock_type}', sample_id)
            
            close_connection(conn)
            flash('Rock sample submitted successfully and is pending verification!', 'success')
            return redirect(url_for('student_view_rocks'))
        except Exception as e:
            close_connection(conn)
            flash(f'Error submitting rock sample: {str(e)}', 'danger')
    
    return render_template('students/add_rock.html')

@app.route('/student/edit-rock/<int:sample_id>', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_edit_rock(sample_id):
    """Edit rock sample (students can only edit their own pending samples)"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # First, verify the rock belongs to this student and is pending
    rock = fetch_one(conn,
        """SELECT * FROM rock_samples 
           WHERE sample_id = %s AND user_id = %s AND status = 'pending'""",
        (sample_id, user_id))
    
    if not rock:
        close_connection(conn)
        flash('Rock sample not found or cannot be edited.', 'danger')
        return redirect(url_for('student_pending_verifications'))
    
    if request.method == 'POST':
        rock_index = request.form.get('rock_index')
        rock_id = request.form.get('rock_id')
        rock_type = request.form.get('rock_type')
        description = request.form.get('description', '')
        formation = request.form.get('formation', '')
        outcrop_id = request.form.get('outcrop_id', '')
        location_name = request.form.get('location_name')
        
        # Handle optional latitude/longitude
        latitude_str = request.form.get('latitude', '')
        longitude_str = request.form.get('longitude', '')
        latitude = float(latitude_str) if latitude_str else None
        longitude = float(longitude_str) if longitude_str else None
        
        rock_specimen = request.files.get('rock_specimen')
        outcrop_image = request.files.get('outcrop_image')
        
        try:
            # Update rock sample
            execute_query(conn,
                """UPDATE rock_samples 
                   SET rock_index = %s, rock_id = %s, rock_type = %s, 
                       description = %s, formation = %s, outcrop_id = %s, 
                       location_name = %s, latitude = %s, longitude = %s,
                       updated_at = NOW()
                   WHERE sample_id = %s""",
                (rock_index, rock_id, rock_type, description, formation, 
                 outcrop_id, location_name, latitude, longitude, sample_id))
            
            # Update rock specimen image if provided
            if rock_specimen and rock_specimen.filename:
                rock_specimen_data = rock_specimen.read()
                # Delete existing rock specimen image
                execute_query(conn,
                    """DELETE FROM images 
                       WHERE sample_id = %s AND image_type = 'rock_specimen'""",
                    (sample_id,))
                # Insert new rock specimen image
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'rock_specimen', %s, %s, %s, %s, NOW())""",
                    (sample_id, rock_specimen_data, rock_specimen.filename,
                     len(rock_specimen_data), rock_specimen.content_type))
            
            # Update outcrop image if provided
            if outcrop_image and outcrop_image.filename:
                outcrop_image_data = outcrop_image.read()
                # Delete existing outcrop image
                execute_query(conn,
                    """DELETE FROM images 
                       WHERE sample_id = %s AND image_type = 'outcrop'""",
                    (sample_id,))
                # Insert new outcrop image
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'outcrop', %s, %s, %s, %s, NOW())""",
                    (sample_id, outcrop_image_data, outcrop_image.filename,
                     len(outcrop_image_data), outcrop_image.content_type))
            
            # Log activity
            log_activity(conn, user_id, 'updated', 
                        f'Updated rock sample: {rock_id} - {rock_type}', sample_id)
            
            close_connection(conn)
            flash('Rock sample updated successfully!', 'success')
            return redirect(url_for('student_pending_verifications'))
        except Exception as e:
            close_connection(conn)
            flash(f'Error updating rock sample: {str(e)}', 'danger')
    
    # Get existing images for display
    images = fetch_all(conn,
        """SELECT image_id, image_type, file_name, file_size, mime_type, created_at
           FROM images WHERE sample_id = %s""",
        (sample_id,))
    
    close_connection(conn)
    return render_template('students/edit_rock.html', rock=rock, images=images)

@app.route('/student/delete-rock/<int:sample_id>', methods=['POST'])
@login_required
@role_required('student')
def student_delete_rock(sample_id):
    """Delete rock sample (students can only delete their own pending samples)"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # First, verify the rock belongs to this student and is pending
    rock = fetch_one(conn,
        """SELECT * FROM rock_samples 
           WHERE sample_id = %s AND user_id = %s AND status = 'pending'""",
        (sample_id, user_id))
    
    if not rock:
        close_connection(conn)
        flash('Rock sample not found or cannot be deleted.', 'danger')
        return redirect(url_for('student_pending_verifications'))
    
    try:
        # Log the deletion activity before deleting other records
        execute_query(conn,
            """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
               VALUES (%s, %s, 'deleted', %s)""",
            (user_id, sample_id, f'Rock sample deleted: {rock["rock_id"]} - {rock["rock_type"]}'))
        
        # Delete associated images
        execute_query(conn,
            """DELETE FROM images WHERE sample_id = %s""",
            (sample_id,))
        
        # Delete the rock sample (activity logs will remain for history)
        execute_query(conn,
            """DELETE FROM rock_samples WHERE sample_id = %s""",
            (sample_id,))
        
        close_connection(conn)
        flash('Rock sample deleted successfully!', 'success')
        return redirect(url_for('student_pending_verifications'))
        
    except Exception as e:
        close_connection(conn)
        flash(f'Error deleting rock sample: {str(e)}', 'danger')
        return redirect(url_for('student_pending_verifications'))

@app.route('/student/view-rocks')
@login_required
@role_required('student')
def student_view_rocks():
    """View all verified rock samples from all students with search and filtering"""
    conn = get_db_connection()
    
    # Get filter parameters from request
    search_query = request.args.get('search', '').strip()
    rock_type_filter = request.args.get('rock_type', '')
    location_filter = request.args.get('location', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build the base query - only verified rocks from all students
    base_query = """SELECT rs.*, 
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name,
           CONCAT(s.first_name, ' ', s.last_name) as submitted_by_name
           FROM rock_samples rs
           LEFT JOIN users v ON rs.verified_by = v.user_id
           LEFT JOIN users s ON rs.user_id = s.user_id
           WHERE rs.status = 'verified'"""
    
    # Add WHERE conditions for filtering
    where_conditions = []
    params = []
    
    if search_query:
        where_conditions.append("(rs.rock_id LIKE %s OR rs.rock_type LIKE %s OR rs.location_name LIKE %s OR rs.description LIKE %s)")
        search_param = f"%{search_query}%"
        params.extend([search_param, search_param, search_param, search_param])
    
    if rock_type_filter:
        where_conditions.append("rs.rock_type = %s")
        params.append(rock_type_filter)
    
    if location_filter:
        where_conditions.append("rs.location_name LIKE %s")
        params.append(f"%{location_filter}%")
    
    if date_from:
        where_conditions.append("DATE(rs.created_at) >= %s")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("DATE(rs.created_at) <= %s")
        params.append(date_to)
    
    # Combine query with conditions
    if where_conditions:
        query = base_query + " AND " + " AND ".join(where_conditions) + " ORDER BY rs.created_at DESC"
    else:
        query = base_query + " ORDER BY rs.created_at DESC"
    
    rocks = fetch_all(conn, query, params)
    
    # Get unique rock types and locations for filter dropdowns
    rock_types = fetch_all(conn, 
        "SELECT DISTINCT rock_type FROM rock_samples WHERE status = 'verified' AND rock_type IS NOT NULL ORDER BY rock_type")
    
    locations = fetch_all(conn, 
        "SELECT DISTINCT location_name FROM rock_samples WHERE status = 'verified' AND location_name IS NOT NULL ORDER BY location_name")
    
    close_connection(conn)
    return render_template('students/view_rocks.html', rocks=rocks, 
                         search_query=search_query, rock_type_filter=rock_type_filter,
                         location_filter=location_filter, date_from=date_from, date_to=date_to,
                         rock_types=rock_types, locations=locations)

@app.route('/student/rock-detail/<int:rock_id>')
@login_required
@role_required('student')
def student_rock_detail(rock_id):
    """View details of any verified rock sample"""
    conn = get_db_connection()
    
    # Get rock details - allow viewing any verified rock
    rock = fetch_one(conn,
        """SELECT rs.*, 
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name,
           CONCAT(s.first_name, ' ', s.last_name) as submitted_by_name
           FROM rock_samples rs
           LEFT JOIN users v ON rs.verified_by = v.user_id
           LEFT JOIN users s ON rs.user_id = s.user_id
           WHERE rs.sample_id = %s AND rs.status = 'verified'""",
        (rock_id,))
    
    if not rock:
        flash('Rock sample not found or not verified', 'error')
        close_connection(conn)
        return redirect(url_for('student_view_rocks'))
    
    # Get images for this rock sample
    images = fetch_all(conn,
        """SELECT image_id, image_type, file_name, file_size, mime_type, created_at
           FROM images WHERE sample_id = %s""",
        (rock_id,))
    
    close_connection(conn)
    return render_template('students/rock_detail.html', rock=rock, images=images)

@app.route('/student/pending-verifications')
@login_required
@role_required('student')
def student_pending_verifications():
    """View pending verifications for student"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    pending = fetch_all(conn,
        """SELECT *, DATEDIFF(NOW(), created_at) as days_pending 
           FROM rock_samples 
           WHERE user_id = %s AND status = 'pending'
           ORDER BY created_at DESC""",
        (user_id,))
    
    close_connection(conn)
    return render_template('students/pending_verifications.html', pending=pending)

@app.route('/student/archives')
@login_required
@role_required('student')
def student_archives():
    """View archived rock samples for student"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    archives = fetch_all(conn,
        """SELECT a.*, rs.rock_id, rs.rock_type, rs.location_name,
           CONCAT(u.first_name, ' ', u.last_name) as archived_by_name
           FROM archives a
           JOIN rock_samples rs ON a.sample_id = rs.sample_id
           JOIN users u ON a.archived_by = u.user_id
           WHERE rs.user_id = %s
           ORDER BY a.archived_at DESC""",
        (user_id,))
    
    close_connection(conn)
    return render_template('students/archives.html', archives=archives)

@app.route('/student/map')
@login_required
@role_required('student')
def student_map():
    """Interactive map showing verified rock sample locations from all students"""
    conn = get_db_connection()
    
    # Get all verified rock samples with coordinates from all students
    rocks = fetch_all(conn,
        """SELECT rs.sample_id, rs.rock_id, rs.rock_type, rs.location_name, 
           rs.latitude, rs.longitude, rs.status, rs.created_at,
           CONCAT(u.first_name, ' ', u.last_name) as student_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           WHERE rs.status = 'verified' AND rs.latitude IS NOT NULL AND rs.longitude IS NOT NULL
           ORDER BY rs.created_at DESC""")
    
    # Get city-level statistics for verified rocks only
    cities = fetch_all(conn,
        """SELECT location_name, COUNT(*) as specimen_count,
           AVG(latitude) as avg_lat, AVG(longitude) as avg_lng
           FROM rock_samples 
           WHERE status = 'verified' AND latitude IS NOT NULL AND longitude IS NOT NULL
           GROUP BY location_name""")
    
    close_connection(conn)
    return render_template('students/map.html', rocks=rocks, cities=cities)

@app.route('/student/logs')
@login_required
@role_required('student')
def student_logs():
    """View activity logs for student with filtering"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # Get filter parameters from request
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build the base query
    base_query = """SELECT al.*, rs.rock_id, rs.rock_type, rs.status as sample_status
           FROM activity_logs al
           LEFT JOIN rock_samples rs ON al.sample_id = rs.sample_id
           WHERE al.user_id = %s"""
    
    # Add WHERE conditions for filtering
    where_conditions = [user_id]
    params = [user_id]
    
    if date_from:
        where_conditions.append("DATE(al.timestamp) >= %s")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("DATE(al.timestamp) <= %s")
        params.append(date_to)
    
    # Combine query with conditions
    if len(where_conditions) > 1:
        query = base_query + " AND " + " AND ".join(where_conditions[1:]) + " ORDER BY al.timestamp DESC LIMIT 50"
    else:
        query = base_query + " ORDER BY al.timestamp DESC LIMIT 50"
    
    logs = fetch_all(conn, query, params)
    
    close_connection(conn)
    return render_template('students/logs.html', logs=logs, 
                         date_from=date_from, date_to=date_to)

@app.route('/student/settings', methods=['GET', 'POST'])
@login_required
@role_required('student')
def student_settings():
    """Student settings page"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        school_id = request.form.get('school_id')
        new_password = request.form.get('new_password')
        
        if new_password:
            password_hash = generate_password_hash(new_password)
            execute_query(conn,
                """UPDATE users SET first_name = %s, last_name = %s, email = %s, 
                   school_id = %s, password_hash = %s WHERE user_id = %s""",
                (first_name, last_name, email, school_id, password_hash, user_id))
        else:
            execute_query(conn,
                """UPDATE users SET first_name = %s, last_name = %s, email = %s, 
                   school_id = %s WHERE user_id = %s""",
                (first_name, last_name, email, school_id, user_id))
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('student_settings'))
    
    user = fetch_one(conn, "SELECT * FROM users WHERE user_id = %s", (user_id,))
    close_connection(conn)
    return render_template('students/settings.html', user=user)

@app.route('/student/update-profile', methods=['POST'])
@login_required
@role_required('student')
def student_update_profile():
    """Update student profile"""
    try:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        school_id = request.form.get('school_id')
        
        conn = get_db_connection()
        
        # Check if email is already taken by another user
        existing_user = fetch_one(conn,
            "SELECT user_id FROM users WHERE email = %s AND user_id != %s",
            (email, session['user_id']))
        
        if existing_user:
            flash('Email already taken by another user', 'error')
            close_connection(conn)
            return redirect(url_for('student_settings'))
        
        # Update user profile
        execute_query(conn,
            "UPDATE users SET first_name = %s, last_name = %s, email = %s, school_id = %s, updated_at = NOW() WHERE user_id = %s",
            (first_name, last_name, email, school_id, session['user_id']))
        
        # Update session
        session['full_name'] = f"{first_name} {last_name}"
        
        log_activity(conn, session['user_id'], 'profile_updated', 'Updated profile information')
        
        close_connection(conn)
        flash('Profile updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('student_settings'))

@app.route('/student/change-password', methods=['POST'])
@login_required
@role_required('student')
def student_change_password():
    """Change student password"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('student_settings'))
        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('student_settings'))
        
        conn = get_db_connection()
        
        # Verify current password
        user = fetch_one(conn, "SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            flash('Current password is incorrect', 'error')
            close_connection(conn)
            return redirect(url_for('student_settings'))
        
        # Update password
        new_hash = generate_password_hash(new_password)
        execute_query(conn,
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s",
            (new_hash, session['user_id']))
        
        log_activity(conn, session['user_id'], 'password_changed', 'Changed password')
        
        close_connection(conn)
        flash('Password changed successfully', 'success')
        
    except Exception as e:
        flash(f'Error changing password: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('student_settings'))

@app.route('/student/update-notifications', methods=['POST'])
@login_required
@role_required('student')
def student_update_notifications():
    """Update student notification preferences"""
    try:
        # This is a placeholder for future notification functionality
        conn = get_db_connection()
        log_activity(conn, session['user_id'], 'notifications_updated', 'Updated notification preferences')
        close_connection(conn)
        
        flash('Notification preferences updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating notifications: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('student_settings'))

# ============================================================================
# PERSONNEL ROUTES
# ============================================================================

@app.route('/personnel/settings')
@login_required
@role_required('personnel')
def personnel_settings():
    """Personnel settings page - view info and change password"""
    conn = get_db_connection()
    user = fetch_one(conn, "SELECT * FROM users WHERE user_id = %s", (session['user_id'],))
    close_connection(conn)
    return render_template('personnel/settings.html', user=user)

@app.route('/personnel/change-password', methods=['POST'])
@login_required
@role_required('personnel')
def personnel_change_password():
    """Change personnel password"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('personnel_settings'))
        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('personnel_settings'))
        
        conn = get_db_connection()
        user = fetch_one(conn, "SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        if not user or not check_password_hash(user['password_hash'], current_password):
            flash('Current password is incorrect', 'error')
            close_connection(conn)
            return redirect(url_for('personnel_settings'))
        
        new_hash = generate_password_hash(new_password)
        execute_query(conn,
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s",
            (new_hash, session['user_id']))
        
        log_activity(conn, session['user_id'], 'password_changed', 'Changed password')
        close_connection(conn)
        flash('Password changed successfully', 'success')
    except Exception as e:
        flash(f'Error changing password: {str(e)}', 'error')
        try:
            close_connection(conn)
        except Exception:
            pass
    return redirect(url_for('personnel_settings'))

@app.route('/personnel/dashboard')
@login_required
@role_required('personnel')
def personnel_dashboard():
    """Personnel dashboard with verification statistics"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # Get comprehensive statistics
    stats = fetch_one(conn,
        """SELECT 
            (SELECT COUNT(*) FROM rock_samples) as total_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'pending') as pending_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'verified') as approved_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'rejected') as rejected_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE verified_by = %s) as verified_by_me
        """,
        (user_id,))
    
    # Get recent pending submissions for display
    recent_pending = fetch_all(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name, u.school_id
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           WHERE rs.status = 'pending'
           ORDER BY rs.created_at ASC LIMIT 10""")
    
    close_connection(conn)
    return render_template('personnel/dashboard.html', 
                         total_rocks=stats['total_rocks'] or 0,
                         pending_rocks=stats['pending_rocks'] or 0,
                         approved_rocks=stats['approved_rocks'] or 0,
                         rejected_rocks=stats['rejected_rocks'] or 0,
                         recent_pending=recent_pending)

@app.route('/personnel/verification-panel')
@login_required
@role_required('personnel')
def personnel_verification_panel():
    """Verification panel for personnel to review rock samples"""
    conn = get_db_connection()
    
    pending_rocks = fetch_all(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
           u.email as student_email, u.school_id
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           WHERE rs.status = 'pending'
           ORDER BY rs.created_at ASC""")
    
    close_connection(conn)
    return render_template('personnel/verification_panel.html', pending_rocks=pending_rocks)

@app.route('/personnel/verify-rock/<int:sample_id>', methods=['POST'])
@login_required
@role_required('personnel')
def personnel_verify_rock(sample_id):
    """Approve or reject a rock sample"""
    action = request.form.get('action')  # 'approve' or 'reject'
    remarks = request.form.get('remarks', '')
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    if action == 'approve':
        execute_query(conn,
            """UPDATE rock_samples 
               SET status = 'verified', verified_by = %s, updated_at = CURRENT_TIMESTAMP
               WHERE sample_id = %s""",
            (user_id, sample_id))
        
        execute_query(conn,
            """INSERT INTO approval_logs (user_id, sample_id, action, remarks)
               VALUES (%s, %s, 'approved', %s)""",
            (user_id, sample_id, remarks))
        
        execute_query(conn,
            """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
               VALUES (%s, %s, 'approved', 'Rock sample approved')""",
            (user_id, sample_id))
        
        flash('Rock sample approved successfully!', 'success')
    
    elif action == 'reject':
        execute_query(conn,
            """UPDATE rock_samples 
               SET status = 'rejected', verified_by = %s, updated_at = CURRENT_TIMESTAMP
               WHERE sample_id = %s""",
            (user_id, sample_id))
        
        execute_query(conn,
            """INSERT INTO approval_logs (user_id, sample_id, action, remarks)
               VALUES (%s, %s, 'rejected', %s)""",
            (user_id, sample_id, remarks))
        
        execute_query(conn,
            """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
               VALUES (%s, %s, 'rejected', %s)""",
            (user_id, sample_id, f'Rock sample rejected: {remarks}'))
        
        flash('Rock sample rejected', 'warning')
    
    close_connection(conn)
    return redirect(url_for('personnel_verification_panel'))

@app.route('/personnel/rock-list')
@login_required
@role_required('personnel')
def personnel_rock_list():
    """View verified rock samples only"""
    conn = get_db_connection()
    
    rocks = fetch_all(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           LEFT JOIN users v ON rs.verified_by = v.user_id
           WHERE rs.status = 'verified'
           ORDER BY rs.created_at DESC""")
    
    close_connection(conn)
    return render_template('personnel/rock_list_view.html', rocks=rocks)

@app.route('/personnel/rock-detail/<int:sample_id>')
@login_required
@role_required('personnel')
def personnel_rock_detail(sample_id):
    """View detailed information about a rock sample"""
    conn = get_db_connection()
    
    rock = fetch_one(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
           u.email as student_email, u.school_id,
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           LEFT JOIN users v ON rs.verified_by = v.user_id
           WHERE rs.sample_id = %s""",
        (sample_id,))
    
    images = fetch_all(conn,
        """SELECT image_id, image_type, file_name, file_size, mime_type, created_at
           FROM images WHERE sample_id = %s""",
        (sample_id,))
    
    approval_history = fetch_all(conn,
        """SELECT al.*, CONCAT(u.first_name, ' ', u.last_name) as user_name
           FROM approval_logs al
           JOIN users u ON al.user_id = u.user_id
           WHERE al.sample_id = %s
           ORDER BY al.timestamp DESC""",
        (sample_id,))
    
    close_connection(conn)
    return render_template('personnel/rock_detail_view.html', rock=rock, 
                         images=images, approval_history=approval_history)

@app.route('/personnel/archive-rock/<int:sample_id>', methods=['POST'])
@login_required
@role_required('personnel')
def personnel_archive_rock(sample_id):
    """Archive a rock sample"""
    reason = request.form.get('reason', '')
    user_id = session['user_id']
    
    conn = get_db_connection()
    
    execute_query(conn,
        """INSERT INTO archives (sample_id, archived_by, archive_reason, status)
           VALUES (%s, %s, %s, 'archived')""",
        (sample_id, user_id, reason))
    
    execute_query(conn,
        """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
           VALUES (%s, %s, 'archived', %s)""",
        (user_id, sample_id, f'Rock sample archived: {reason}'))
    
    close_connection(conn)
    flash('Rock sample archived successfully!', 'success')
    return redirect(url_for('personnel_verification_panel'))

@app.route('/personnel/archives')
@login_required
@role_required('personnel')
def personnel_archives():
    """View archived rock samples - only show archives created by logged-in personnel"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    archives = fetch_all(conn,
        """SELECT a.*, rs.rock_id, rs.rock_type, rs.location_name,
           CONCAT(u.first_name, ' ', u.last_name) as archived_by_name,
           CONCAT(s.first_name, ' ', s.last_name) as student_name
           FROM archives a
           JOIN rock_samples rs ON a.sample_id = rs.sample_id
           JOIN users u ON a.archived_by = u.user_id
           JOIN users s ON rs.user_id = s.user_id
           WHERE a.archived_by = %s
           ORDER BY a.archived_at DESC""", (user_id,))
    
    close_connection(conn)
    return render_template('personnel/archives.html', archived_rocks=archives)

@app.route('/personnel/map')
@login_required
@role_required('personnel')
def personnel_map():
    """Interactive map showing all rock sample locations"""
    conn = get_db_connection()
    
    # Get all rock samples with coordinates
    rocks = fetch_all(conn,
        """SELECT rs.sample_id, rs.rock_id, rs.rock_type, rs.location_name, 
           rs.latitude, rs.longitude, rs.status, rs.created_at,
           CONCAT(u.first_name, ' ', u.last_name) as student_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           WHERE rs.latitude IS NOT NULL AND rs.longitude IS NOT NULL
           ORDER BY rs.created_at DESC""")
    
    # Get city-level statistics
    cities = fetch_all(conn,
        """SELECT location_name, COUNT(*) as specimen_count,
           AVG(latitude) as avg_lat, AVG(longitude) as avg_lng
           FROM rock_samples 
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
           GROUP BY location_name""")
    
    close_connection(conn)
    return render_template('personnel/map.html', rocks=rocks, cities=cities)

@app.route('/personnel/activity-logs')
@login_required
@role_required('personnel')
def personnel_activity_logs():
    """View activity logs with filtering - only show activities performed by logged-in personnel"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    # Get filter parameters from request
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build the base query - filter by logged-in personnel user
    base_query = """SELECT al.*, CONCAT(u.first_name, ' ', u.last_name) as user_name,
           u.username, u.role as user_role, rs.rock_id, rs.rock_type
           FROM activity_logs al
           JOIN users u ON al.user_id = u.user_id
           LEFT JOIN rock_samples rs ON al.sample_id = rs.sample_id
           WHERE al.user_id = %s"""
    
    # Add WHERE conditions for filtering
    where_conditions = ["al.user_id = %s"]
    params = [user_id]
    
    if date_from:
        where_conditions.append("DATE(al.timestamp) >= %s")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("DATE(al.timestamp) <= %s")
        params.append(date_to)
    
    # Combine query with conditions
    query = base_query + " AND " + " AND ".join(where_conditions[1:]) + " ORDER BY al.timestamp DESC LIMIT 100" if len(where_conditions) > 1 else base_query + " ORDER BY al.timestamp DESC LIMIT 100"
    
    logs = fetch_all(conn, query, params)
    
    close_connection(conn)
    return render_template('personnel/activity_logs.html', logs=logs, 
                         date_from=date_from, date_to=date_to)

# Removed export-to-CSV endpoint for personnel

# ============================================================================
# ADMIN ROUTES
# ============================================================================

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    """Admin dashboard with system statistics"""
    conn = get_db_connection()
    
    # Get comprehensive statistics
    stats = fetch_one(conn,
        """SELECT 
            (SELECT COUNT(*) FROM users WHERE is_active = TRUE) as total_users,
            (SELECT COUNT(*) FROM users WHERE role = 'student' AND is_active = TRUE) as total_students,
            (SELECT COUNT(*) FROM users WHERE role = 'personnel' AND is_active = TRUE) as total_personnel,
            (SELECT COUNT(*) FROM rock_samples) as total_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'verified') as verified_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'pending') as pending_rocks,
            (SELECT COUNT(*) FROM rock_samples WHERE status = 'rejected') as rejected_rocks,
            (SELECT COUNT(*) FROM archives) as archived_rocks""")
    
    # Get recent activity
    recent_activity = fetch_all(conn,
        """SELECT al.*, CONCAT(u.first_name, ' ', u.last_name) as user_name,
           u.role, rs.rock_id
           FROM activity_logs al
           JOIN users u ON al.user_id = u.user_id
           LEFT JOIN rock_samples rs ON al.sample_id = rs.sample_id
           ORDER BY al.timestamp DESC LIMIT 10""")
    
    # Get all rock samples for the dashboard table
    all_rocks = fetch_all(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as submitted_by_name,
           u.school_id as student_id
           FROM rock_samples rs
           LEFT JOIN users u ON rs.user_id = u.user_id
           ORDER BY rs.created_at DESC LIMIT 20""")
    
    close_connection(conn)
    return render_template('admin/dashboard.html', stats=stats, recent_activity=recent_activity, all_rocks=all_rocks)

@app.route('/admin/manage-users')
@login_required
@role_required('admin')
def admin_manage_users():
    """Manage all users in the system"""
    conn = get_db_connection()
    role_filter = request.args.get('role', '').strip()
    
    if role_filter in ('admin', 'personnel', 'student'):
        users = fetch_all(conn,
            """SELECT user_id, username, email, first_name, last_name, role, 
               school_id, is_active, created_at, last_login
               FROM users
               WHERE role = %s
               ORDER BY created_at DESC""",
            (role_filter,))
    else:
        users = fetch_all(conn,
            """SELECT user_id, username, email, first_name, last_name, role, 
               school_id, is_active, created_at, last_login
               FROM users
               ORDER BY created_at DESC""")
    
    close_connection(conn)
    return render_template('admin/manage_users.html', users=users, role_filter=role_filter)

@app.route('/admin/toggle-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_toggle_user(user_id):
    """Activate or deactivate a user"""
    conn = get_db_connection()
    
    user = fetch_one(conn, "SELECT is_active FROM users WHERE user_id = %s", (user_id,))
    new_status = not user['is_active']
    
    execute_query(conn,
        "UPDATE users SET is_active = %s WHERE user_id = %s",
        (new_status, user_id))
    
    close_connection(conn)
    flash(f'User {"activated" if new_status else "deactivated"} successfully!', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    """Delete a user from the system"""
    from flask import jsonify
    if user_id == session['user_id']:
        # Never allow self-delete
        return jsonify({ 'success': False, 'message': 'Cannot delete your own account.' }), 400
    
    try:
        conn = get_db_connection()
        # Optionally ensure user exists
        existing = fetch_one(conn, "SELECT user_id FROM users WHERE user_id = %s", (user_id,))
        if not existing:
            close_connection(conn)
            return jsonify({ 'success': False, 'message': 'User not found.' }), 404
        
        # To preserve rock samples, do NOT hard-delete users. Soft-disable instead.
        execute_query(conn,
            "UPDATE users SET is_active = 0, updated_at = NOW() WHERE user_id = %s",
            (user_id,))
        close_connection(conn)
        return jsonify({ 'success': True, 'message': 'User deactivated to preserve submitted rock records.' })
    except Exception as e:
        try:
            close_connection(conn)
        except Exception:
            pass
        return jsonify({ 'success': False, 'message': f'Error deleting user: {str(e)}' }), 500

@app.route('/admin/rock-list')
@login_required
@role_required('admin')
def admin_rock_list():
    """View all rock samples with search and filtering"""
    conn = get_db_connection()
    
    # Get search and filter parameters
    search_query = request.args.get('search', '').strip()
    rock_type_filter = request.args.get('rock_type', '').strip()
    
    # Debug logging (remove in production)
    print(f"Search query: '{search_query}', Rock type filter: '{rock_type_filter}'")
    
    # Build the base query
    base_query = """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
           u.school_id as student_id,
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           LEFT JOIN users v ON rs.verified_by = v.user_id
           LEFT JOIN archives a ON rs.sample_id = a.sample_id
           WHERE a.sample_id IS NULL"""
    
    # Build WHERE conditions
    where_conditions = []
    params = []
    
    # Add search functionality
    if search_query:
        where_conditions.append("""(rs.rock_id LIKE %s OR rs.rock_type LIKE %s 
                                   OR rs.location_name LIKE %s OR rs.description LIKE %s
                                   OR CONCAT(u.first_name, ' ', u.last_name) LIKE %s
                                   OR u.school_id LIKE %s)""")
        search_param = f"%{search_query}%"
        params.extend([search_param] * 6)  # 6 placeholders for the search
    
    # Add rock type filter
    if rock_type_filter and rock_type_filter != '':
        where_conditions.append("rs.rock_type = %s")
        params.append(rock_type_filter)
    
    # Combine query
    if where_conditions:
        query = base_query + " AND " + " AND ".join(where_conditions)
    else:
        query = base_query
    
    query += " ORDER BY rs.created_at DESC"
    
    # Debug logging (remove in production)
    print(f"Final query: {query}")
    print(f"Parameters: {params}")
    
    # Execute query
    rocks = fetch_all(conn, query, params)
    
    close_connection(conn)
    return render_template('admin/rock_list_view.html', rocks=rocks, 
                          search_query=search_query, rock_type_filter=rock_type_filter)

@app.route('/admin/add-rock', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_rock():
    """Add new rock sample (admin adds their own rock)"""
    if request.method == 'POST':
        user_id = session['user_id']  # Admin's ID
        rock_index = request.form.get('rock_index')
        rock_id = request.form.get('rock_id')
        rock_type = request.form.get('rock_type')
        description = request.form.get('description', '')
        formation = request.form.get('formation', '')
        outcrop_id = request.form.get('outcrop_id', '')
        location_name = request.form.get('location_name')
        
        # Handle optional latitude/longitude
        latitude_str = request.form.get('latitude', '')
        longitude_str = request.form.get('longitude', '')
        latitude = float(latitude_str) if latitude_str else None
        longitude = float(longitude_str) if longitude_str else None
        
        rock_specimen = request.files.get('rock_specimen')
        outcrop_image = request.files.get('outcrop_image')
        
        conn = get_db_connection()
        try:
            # Insert rock sample - admin rocks are auto-verified
            sample_id = execute_query(conn,
                """INSERT INTO rock_samples (user_id, rock_index, rock_id, rock_type, 
                   description, formation, outcrop_id, location_name, latitude, longitude, 
                   status, verified_by, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'verified', %s, NOW())""",
                (user_id, rock_index, rock_id, rock_type, description, formation, 
                 outcrop_id, location_name, latitude, longitude, user_id))
            
            # Insert rock specimen image
            if rock_specimen:
                rock_specimen_data = rock_specimen.read()
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'rock_specimen', %s, %s, %s, %s, NOW())""",
                    (sample_id, rock_specimen_data, rock_specimen.filename,
                     len(rock_specimen_data), rock_specimen.content_type))
            
            # Insert outcrop image
            if outcrop_image:
                outcrop_image_data = outcrop_image.read()
                execute_query(conn,
                    """INSERT INTO images (sample_id, image_type, image_data, file_name, 
                       file_size, mime_type, created_at)
                       VALUES (%s, 'outcrop', %s, %s, %s, %s, NOW())""",
                    (sample_id, outcrop_image_data, outcrop_image.filename,
                     len(outcrop_image_data), outcrop_image.content_type))
            
            # Log activity
            log_activity(conn, session['user_id'], 'submitted', 
                        f'Admin added rock sample: {rock_id} - {rock_type}', sample_id)
            
            close_connection(conn)
            flash('Rock sample added successfully and automatically verified!', 'success')
            return redirect(url_for('admin_rock_list'))
        except Exception as e:
            close_connection(conn)
            flash(f'Error adding rock sample: {str(e)}', 'danger')
    
    return render_template('admin/add_rock.html')

@app.route('/admin/rock-detail/<int:sample_id>')
@login_required
@role_required('admin')
def admin_rock_detail(sample_id):
    """View detailed information about a rock sample"""
    conn = get_db_connection()
    
    rock = fetch_one(conn,
        """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
           u.email as student_email, u.school_id,
           CONCAT(v.first_name, ' ', v.last_name) as verified_by_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           LEFT JOIN users v ON rs.verified_by = v.user_id
           WHERE rs.sample_id = %s""",
        (sample_id,))
    
    images = fetch_all(conn,
        """SELECT image_id, image_type, file_name, file_size, mime_type, created_at
           FROM images WHERE sample_id = %s""",
        (sample_id,))
    
    approval_history = fetch_all(conn,
        """SELECT al.*, CONCAT(u.first_name, ' ', u.last_name) as user_name
           FROM approval_logs al
           JOIN users u ON al.user_id = u.user_id
           WHERE al.sample_id = %s
           ORDER BY al.timestamp DESC""",
        (sample_id,))
    
    close_connection(conn)
    return render_template('admin/rock_detail_view.html', rock=rock, 
                         images=images, approval_history=approval_history)

@app.route('/admin/edit-rock/<int:sample_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_rock(sample_id):
    """Edit a rock sample"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            # Get form data
            rock_id = request.form.get('rock_id', '').strip()
            rock_type = request.form.get('rock_type', '').strip()
            description = request.form.get('description', '').strip()
            location_name = request.form.get('location_name', '').strip()
            latitude = request.form.get('latitude', '').strip()
            longitude = request.form.get('longitude', '').strip()
            outcrop_id = request.form.get('outcrop_id', '').strip()
            formation = request.form.get('formation', '').strip()
            rock_index = request.form.get('rock_index', '').strip()
            
            # Validate required fields
            if not rock_id or not rock_type or not location_name:
                flash('Rock ID, Rock Type, and Location are required!', 'error')
                return redirect(url_for('admin_edit_rock', sample_id=sample_id))
            
            # Update the rock sample
            execute_query(conn,
                """UPDATE rock_samples SET 
                   rock_id = %s, rock_type = %s, description = %s,
                   location_name = %s, latitude = %s, longitude = %s,
                   outcrop_id = %s, formation = %s, rock_index = %s,
                   updated_at = NOW()
                   WHERE sample_id = %s""",
                (rock_id, rock_type, description, location_name, latitude, longitude,
                 outcrop_id, formation, rock_index, sample_id))
            
            # Log the edit activity
            user_id = session['user_id']
            execute_query(conn,
                """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
                   VALUES (%s, %s, 'edited', %s)""",
                (user_id, sample_id, f'Rock sample edited by admin: {rock_id}'))
            
            close_connection(conn)
            flash('Rock sample updated successfully!', 'success')
            return redirect(url_for('admin_rock_detail', sample_id=sample_id))
            
        except Exception as e:
            print(f"Error updating rock sample {sample_id}: {str(e)}")
            flash('Error updating rock sample!', 'error')
            close_connection(conn)
            return redirect(url_for('admin_edit_rock', sample_id=sample_id))
    
    else:
        # GET request - show edit form
        rock = fetch_one(conn,
            """SELECT rs.*, CONCAT(u.first_name, ' ', u.last_name) as student_name,
               u.email as student_email, u.school_id
               FROM rock_samples rs
               JOIN users u ON rs.user_id = u.user_id
               WHERE rs.sample_id = %s""",
            (sample_id,))
        
        if not rock:
            close_connection(conn)
            flash('Rock sample not found!', 'error')
            return redirect(url_for('admin_rock_list'))
        
        close_connection(conn)
        return render_template('admin/edit_rock.html', rock=rock)

@app.route('/admin/archive-rock/<int:sample_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_archive_rock(sample_id):
    """Archive a rock sample"""
    conn = None
    try:
        reason = request.form.get('reason', 'Archived by admin')
        user_id = session['user_id']
        
        conn = get_db_connection()
        
        # Check if rock sample exists
        rock = fetch_one(conn, "SELECT * FROM rock_samples WHERE sample_id = %s", (sample_id,))
        if not rock:
            close_connection(conn)
            flash('Rock sample not found!', 'error')
            return redirect(url_for('admin_rock_list'))
        
        # Check if already archived
        existing_archive = fetch_one(conn, "SELECT * FROM archives WHERE sample_id = %s", (sample_id,))
        if existing_archive:
            close_connection(conn)
            flash('Rock sample is already archived!', 'warning')
            return redirect(url_for('admin_rock_list'))
        
        # Archive the rock sample
        archive_id = execute_query(conn,
            """INSERT INTO archives (sample_id, archived_by, archive_reason, status)
               VALUES (%s, %s, %s, 'archived')""",
            (sample_id, user_id, reason))
        
        # Log the activity
        activity_id = execute_query(conn,
            """INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
               VALUES (%s, %s, 'archived', %s)""",
            (user_id, sample_id, f'Rock sample archived by admin: {reason}'))
        
        close_connection(conn)
        flash('Rock sample archived successfully!', 'success')
        
    except Exception as e:
        print(f"Error archiving rock sample {sample_id}: {str(e)}")
        flash('Error archiving rock sample!', 'error')
        # Ensure connection is closed even on error
        if conn:
            try:
                close_connection(conn)
            except:
                pass
    
    return redirect(url_for('admin_rock_list'))

@app.route('/admin/archives')
@login_required
@role_required('admin')
def admin_archives():
    """View all archived rock samples"""
    conn = get_db_connection()
    
    archives = fetch_all(conn,
        """SELECT a.*, rs.rock_id, rs.rock_type, rs.location_name,
           CONCAT(u.first_name, ' ', u.last_name) as archived_by_name,
           CONCAT(s.first_name, ' ', s.last_name) as student_name
           FROM archives a
           JOIN rock_samples rs ON a.sample_id = rs.sample_id
           JOIN users u ON a.archived_by = u.user_id
           JOIN users s ON rs.user_id = s.user_id
           ORDER BY a.archived_at DESC""")
    
    close_connection(conn)
    return render_template('admin/archives.html', archives=archives)

@app.route('/admin/map')
@login_required
@role_required('admin')
def admin_map():
    """Interactive map showing all rock sample locations"""
    conn = get_db_connection()
    
    # Get all rock samples with coordinates
    rocks = fetch_all(conn,
        """SELECT rs.sample_id, rs.rock_id, rs.rock_type, rs.location_name, 
           rs.latitude, rs.longitude, rs.status, rs.created_at,
           CONCAT(u.first_name, ' ', u.last_name) as student_name
           FROM rock_samples rs
           JOIN users u ON rs.user_id = u.user_id
           WHERE rs.latitude IS NOT NULL AND rs.longitude IS NOT NULL
           ORDER BY rs.created_at DESC""")
    
    # Get city-level statistics
    cities = fetch_all(conn,
        """SELECT location_name, COUNT(*) as specimen_count,
           AVG(latitude) as avg_lat, AVG(longitude) as avg_lng
           FROM rock_samples 
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
           GROUP BY location_name""")
    
    close_connection(conn)
    return render_template('admin/map.html', rocks=rocks, cities=cities)

@app.route('/admin/activity-logs')
@login_required
@role_required('admin')
def admin_activity_logs():
    """View all activity logs with filtering"""
    conn = get_db_connection()
    
    # Get filter parameters
    user_filter = request.args.get('user', '').strip()
    action_filter = request.args.get('action', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    
    # Build the base query
    base_query = """SELECT al.*, CONCAT(u.first_name, ' ', u.last_name) as user_name,
           u.username, u.role as user_role, rs.rock_id, rs.rock_type
           FROM activity_logs al
           JOIN users u ON al.user_id = u.user_id
           LEFT JOIN rock_samples rs ON al.sample_id = rs.sample_id"""
    
    # Build WHERE conditions
    where_conditions = []
    params = []
    
    # Add user filter
    if user_filter:
        where_conditions.append("al.user_id = %s")
        params.append(user_filter)
    
    # Add action filter
    if action_filter:
        where_conditions.append("al.activity_type = %s")
        params.append(action_filter)
    
    # Add date filters
    if date_from:
        where_conditions.append("DATE(al.timestamp) >= %s")
        params.append(date_from)
    
    if date_to:
        where_conditions.append("DATE(al.timestamp) <= %s")
        params.append(date_to)
    
    # Combine query
    if where_conditions:
        query = base_query + " WHERE " + " AND ".join(where_conditions)
    else:
        query = base_query
    
    query += " ORDER BY al.timestamp DESC LIMIT 200"
    
    logs = fetch_all(conn, query, params)
    
    # Get users for filter dropdown
    users = fetch_all(conn, "SELECT user_id, username FROM users WHERE is_active = TRUE ORDER BY username")
    
    close_connection(conn)
    return render_template('admin/activity_logs.html', logs=logs, users=users,
                          user_filter=user_filter, action_filter=action_filter,
                          date_from=date_from, date_to=date_to)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_settings():
    """Admin settings page"""
    conn = get_db_connection()
    user_id = session['user_id']
    
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        new_password = request.form.get('new_password')
        
        if new_password:
            password_hash = generate_password_hash(new_password)
            execute_query(conn,
                """UPDATE users SET first_name = %s, last_name = %s, email = %s, 
                   password_hash = %s WHERE user_id = %s""",
                (first_name, last_name, email, password_hash, user_id))
        else:
            execute_query(conn,
                """UPDATE users SET first_name = %s, last_name = %s, email = %s 
                   WHERE user_id = %s""",
                (first_name, last_name, email, user_id))
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('admin_settings'))
    
    user = fetch_one(conn, "SELECT * FROM users WHERE user_id = %s", (user_id,))
    close_connection(conn)
    return render_template('admin/settings.html', user=user)

# ============================================================================
# IMAGE ROUTES
# ============================================================================

@app.route('/image/<int:image_id>')
@login_required
def serve_image(image_id):
    """Serve an image from the database"""
    conn = get_db_connection()
    
    image = fetch_one(conn,
        "SELECT image_data, mime_type, file_name FROM images WHERE image_id = %s",
        (image_id,))
    
    close_connection(conn)
    
    if image:
        return send_file(
            io.BytesIO(image['image_data']),
            mimetype=image['mime_type'],
            as_attachment=False,
            download_name=image['file_name']
        )
    else:
        flash('Image not found', 'danger')
        return redirect(url_for('index'))

@app.route('/image/sample/<int:sample_id>/<image_type>')
@login_required
def serve_sample_image(sample_id, image_type):
    """Serve a specific type of image for a rock sample"""
    conn = get_db_connection()
    
    image = fetch_one(conn,
        """SELECT image_data, mime_type, file_name 
           FROM images 
           WHERE sample_id = %s AND image_type = %s
           ORDER BY created_at DESC LIMIT 1""",
        (sample_id, image_type))
    
    close_connection(conn)
    
    if image:
        return send_file(
            io.BytesIO(image['image_data']),
            mimetype=image['mime_type'],
            as_attachment=False,
            download_name=image['file_name']
        )
    else:
        # Return placeholder image
        return redirect(url_for('static', filename='images/no-image.png'))

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    flash('You do not have permission to access this page', 'danger')
    return redirect(url_for('index'))

# ============================================================================
# ADDITIONAL ADMIN ROUTES
# ============================================================================

@app.route('/admin/add-user', methods=['POST'])
@login_required
@role_required('admin')
def admin_add_user():
    """Add a new user"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        role = request.form.get('role', 'student')
        school_id = request.form.get('school_id')
        password = request.form.get('password')
        
        if not all([username, email, first_name, last_name, password]):
            flash('All fields are required', 'error')
            return redirect(url_for('admin_manage_users'))
        
        conn = get_db_connection()
        
        # Check if username or email already exists
        existing_user = fetch_one(conn,
            "SELECT user_id FROM users WHERE username = %s OR email = %s",
            (username, email))
        
        if existing_user:
            flash('Username or email already exists', 'error')
            close_connection(conn)
            return redirect(url_for('admin_manage_users'))
        
        # Hash password and insert user
        password_hash = generate_password_hash(password)
        user_id = execute_query(conn,
            """INSERT INTO users (username, email, password_hash, first_name, last_name, 
               role, school_id, is_active, created_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE, NOW())""",
            (username, email, password_hash, first_name, last_name, role, school_id))
        
        log_activity(conn, session['user_id'], 'user_created', 
                    f'Created user: {username} ({role})')
        
        close_connection(conn)
        flash(f'User {username} created successfully', 'success')
        
    except Exception as e:
        flash(f'Error creating user: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/edit-user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_user(user_id):
    """Edit user information"""
    conn = get_db_connection()
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            email = request.form.get('email')
            full_name = request.form.get('full_name', '')
            # Derive first_name and last_name from full_name for backward compatibility
            full_name = (full_name or '').strip()
            if ' ' in full_name:
                first_name, last_name = full_name.split(' ', 1)
            else:
                first_name, last_name = full_name, ''
            role = request.form.get('role')
            school_id = request.form.get('school_id')
            is_active = request.form.get('is_active') == 'on'
            
            if not all([username, email, first_name, role]):
                flash('All required fields must be filled', 'error')
                close_connection(conn)
                return redirect(url_for('admin_edit_user', user_id=user_id))
            
            # Check if username or email already exists for other users
            existing_user = fetch_one(conn,
                "SELECT user_id FROM users WHERE (username = %s OR email = %s) AND user_id != %s",
                (username, email, user_id))
            
            if existing_user:
                flash('Username or email already exists for another user', 'error')
                close_connection(conn)
                return redirect(url_for('admin_edit_user', user_id=user_id))
            
            # Update user information
            execute_query(conn,
                """UPDATE users SET username = %s, email = %s, first_name = %s, 
                   last_name = %s, role = %s, school_id = %s, is_active = %s, updated_at = NOW()
                   WHERE user_id = %s""",
                (username, email, first_name, last_name, role, school_id, is_active, user_id))
            
            # Update password if provided
            new_password = request.form.get('new_password')
            if new_password and new_password.strip():
                password_hash = generate_password_hash(new_password)
                execute_query(conn,
                    "UPDATE users SET password_hash = %s WHERE user_id = %s",
                    (password_hash, user_id))
            
            log_activity(conn, session['user_id'], 'user_updated', 
                        f'Updated user: {username} ({role})')
            
            close_connection(conn)
            flash(f'User {username} updated successfully', 'success')
            return redirect(url_for('admin_manage_users'))
            
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
            if 'conn' in locals():
                close_connection(conn)
            return redirect(url_for('admin_edit_user', user_id=user_id))
    
    else:  # GET request
        try:
            # Get user information
            user = fetch_one(conn,
                "SELECT * FROM users WHERE user_id = %s",
                (user_id,))
            
            if not user:
                flash('User not found', 'error')
                close_connection(conn)
                return redirect(url_for('admin_manage_users'))
            
            close_connection(conn)
            return render_template('admin/edit_user.html', user=user)
            
        except Exception as e:
            flash(f'Error loading user: {str(e)}', 'error')
            if 'conn' in locals():
                close_connection(conn)
            return redirect(url_for('admin_manage_users'))

# Removed export-to-CSV endpoint for admin

@app.route('/admin/update-profile', methods=['POST'])
@login_required
@role_required('admin')
def admin_update_profile():
    """Update admin profile"""
    try:
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        
        conn = get_db_connection()
        
        # Check if email is already taken by another user
        existing_user = fetch_one(conn,
            "SELECT user_id FROM users WHERE email = %s AND user_id != %s",
            (email, session['user_id']))
        
        if existing_user:
            flash('Email already taken by another user', 'error')
            close_connection(conn)
            return redirect(url_for('admin_settings'))
        
        # Update user profile
        execute_query(conn,
            "UPDATE users SET first_name = %s, last_name = %s, email = %s, updated_at = NOW() WHERE user_id = %s",
            (first_name, last_name, email, session['user_id']))
        
        # Update session
        session['full_name'] = f"{first_name} {last_name}"
        
        log_activity(conn, session['user_id'], 'profile_updated', 'Updated profile information')
        
        close_connection(conn)
        flash('Profile updated successfully', 'success')
        
    except Exception as e:
        flash(f'Error updating profile: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/change-password', methods=['POST'])
@login_required
@role_required('admin')
def admin_change_password():
    """Change admin password"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return redirect(url_for('admin_settings'))
        
        conn = get_db_connection()
        
        # Verify current password
        user = fetch_one(conn, "SELECT password_hash FROM users WHERE user_id = %s", (session['user_id'],))
        
        if not user or not check_password_hash(user['password_hash'], current_password):
            flash('Current password is incorrect', 'error')
            close_connection(conn)
            return redirect(url_for('admin_settings'))
        
        # Update password
        new_hash = generate_password_hash(new_password)
        execute_query(conn,
            "UPDATE users SET password_hash = %s, updated_at = NOW() WHERE user_id = %s",
            (new_hash, session['user_id']))
        
        log_activity(conn, session['user_id'], 'password_changed', 'Changed password')
        
        close_connection(conn)
        flash('Password changed successfully', 'success')
        
    except Exception as e:
        flash(f'Error changing password: {str(e)}', 'error')
        if 'conn' in locals():
            close_connection(conn)
    
    return redirect(url_for('admin_settings'))


# ============================================================================
# ERROR HANDLERS
# ============================================================================

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5817)

