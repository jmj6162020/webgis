# Web-GIS Geological Specimen Collection

A role-based Flask web application to collect, verify, and visualize rock specimen locations on an interactive map. The system supports Students, Personnel, and Admin users with tailored workflows and permissions.

## Tech Stack

### Backend
- **Framework**: Flask 3.0+ (Python web framework)
- **Language**: Python 3.x
- **Database**: MySQL/MariaDB (via XAMPP)
- **Database Connector**: mysql-connector-python 8.2+
- **Authentication**: Werkzeug password hashing (bcrypt/scrypt)
- **Session Management**: Flask sessions with role-based access control
- **Image Processing**: Pillow 10.1+ for image handling

### Frontend
- **Templating Engine**: Jinja2 (server-side rendering)
- **CSS Framework**: Bootstrap 5 (responsive UI components)
- **Maps**: Leaflet.js (interactive map visualization)
- **Map Tiles**: OpenStreetMap (free, open-source map tiles)
- **JavaScript**: Vanilla JS for map interactions and form handling

### Development Tools
- **Environment Management**: python-dotenv (configuration via .env files)
- **Version Control**: Git
- **Database Management**: phpMyAdmin (via XAMPP) or MySQL CLI

### Infrastructure
- **Server**: Flask development server (for production, use Gunicorn/uWSGI)
- **Database Server**: MySQL/MariaDB (default XAMPP installation)
- **Web Server**: Flask built-in (development) or Apache/Nginx (production)

## Key Features (All Users)
- Email-based login (email + password, role confirmation)
- Role-aware dashboards and navigation
- Interactive map with city dots (blue) and specimen markers (purple)






## Role Capabilities

### Student
- Submit new rock samples
  - Rock Type via dropdown (Igneous, Sedimentary, Metamorphic)
  - Optional formation, outcrop ID, and coordinates
  - Upload specimen/outcrop images
- Pending Verifications
  - Edit and update pending samples
  - Delete only if status is pending (cannot delete verified samples)
- View Verified Rocks (all users' verified samples)
- Interactive Map
  - City selector and click-to-filter cities
  - See specimen count per city and navigate to details
- Settings
  - Read-only profile info (Full Name, Email, Student ID)
  - Change password with validation and success/error banners

### Personnel
- Verification Panel
  - Review submitted samples and verify/reject
- Interactive Map
  - Same capabilities as admin map, with personnel-specific details
- Activity Logs (view)
- Settings
  - Read-only profile (Full Name, Email, Role)
  - Change password

### Admin
- Manage Users
  - View users with role and status badges
  - Add User (School ID required only for Students)
  - Edit User (Full Name only; Username/Email/Role are disabled)
  - Block/Unblock User (toggle active status)
  - Deactivate (instead of delete) to preserve rock record integrity
  - Filter by Role (Admin, Personnel, Student)
- Rock Samples
  - Add Rock (with the same dropdown for Rock Type)
  - List, search, and inspect rock samples
  - Archive verified samples (cannot delete verified samples)
- Activity Logs
  - Filter UI consistent with Manage Users (styled filters)
- Interactive Map
  - City selector and click-to-filter
  - Popups with rock metadata and deep links to sample details
- Settings
  - Update profile (Full Name); Email is disabled
  - Change password

## Data Integrity Rules
- Verified rocks cannot be deleted by any user.
- Students may only delete their own samples in PENDING status.
- Admin “delete user” is implemented as a soft-deactivation to ensure rocks remain linked historically.
- Only Admin can archive rock samples.

## Map UX Details
- City Markers (blue): represent cities/municipalities by average coordinates
- Specimen Markers (purple): appear after selecting a city
- City dropdown: compact control above the map; selecting updates markers and auto-zooms
- Popups: concise rock information and deep links to detail pages based on role

## Installation & Setup
1. Create and configure a Python virtual environment.
2. Install dependencies from `requirements.txt`.
3. Set environment variables (or `.env`) for database access (see `config.py`):
   - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - `SECRET_KEY`, `FLASK_ENV`
4. Initialize the database schema (see `webgisDB.sql`).
5. Run the Flask app:
   - `export FLASK_APP=app.py`
   - `flask run` (or `python app.py` if applicable in your environment)

## Project Structure (Selected)
- `app.py` – Main Flask routes and views
- `auth_utils.py` – Login/role decorators and session helpers
- `db_utils.py` – Database connection and query helpers
- `config.py` – Environment-driven configuration
- `templates/` – Role-based pages and UI components
- `static/` – Static assets (e.g., logo)

## Security Notes
- Email-only login; username is not accepted at login
- Sessions are HTTP-only; consider `SESSION_COOKIE_SECURE=True` for production
- Passwords are hashed (Werkzeug)
- Role checks applied to all protected routes (`@login_required`, `@role_required`)

## Recent Enhancements
- Email-only login and consistent auth feedback
- Compact headers and consistent filter UI
- Rock Type dropdown on Add/Edit Rock for Students and Admin
- Personnel Settings page with password change
- Manage Users: role filter, block/unblock, soft-deactivate instead of delete
- Verified rock protection and admin-only archiving


