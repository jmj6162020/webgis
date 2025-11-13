# Web-GIS Geological Specimen Collection

A role-based Flask web application to collect, verify, and visualize rock specimen locations on an interactive map. The system supports Students, Personnel, and Admin users with tailored workflows and permissions.

## Tech Stack

### Backend
- **Language/Runtime**: Python 3.x (tested with Python 3.13)
- **Framework**: Flask (3.x)
- **Database**: MySQL/MariaDB
- **Database Connector**: mysql-connector-python
- **Auth & Security**: Werkzeug password hashing (bcrypt/scrypt), role-based authorization
- **Sessions**: Flask sessions (HTTP-only cookies; secure in production)
- **File/Image Handling**: Pillow (image processing)
- **Excel I/O**: openpyxl (for .xlsx export/import)

### Frontend
- **Templating Engine**: Jinja2 (server-side rendering)
- **CSS Framework**: Bootstrap 5 (responsive UI components)
- **Maps**: Leaflet.js (interactive map visualization)
  - Leaflet core: `L.map`, `L.tileLayer`, `L.circleMarker`, `L.layerGroup`, `L.featureGroup`, `bindPopup`, `fitBounds`
  - Multi-filter system: Rock ID search, Rock Type dropdown, City/Municipality dropdown with debounced input handling
  - Role-aware popup links and inline image thumbnails
  - Dark mode styling for Leaflet controls and popups
- **Map Tiles**: OpenStreetMap Standard tiles (with attribution)
- **JavaScript**: Vanilla JS for map interactions and form handling

### Development Tools
- **Environment Management**: python-dotenv (.env configuration)
- **Version Control**: Git
- **Database Management**: phpMyAdmin (via XAMPP) or MySQL CLI

### Infrastructure
- **Server**: Flask development server (for production, use Gunicorn/uWSGI)
- **Database Server**: MySQL/MariaDB (default XAMPP installation)
- **Web Server**: Flask built-in (development) or Apache/Nginx (production)

## Key Features (All Users)
- Email-based login (email + password, role confirmation required)
- Role-aware dashboards and navigation with personalized statistics
- Consistent filters across list/map views (search, rock type, city/municipality, date range)
- Rock details with images and metadata (role-scoped visibility and edit permissions)
- Export filtered rock lists to CSV/Excel (role-scoped, includes image indicators)
- Profile management: update profile info, change password, and upload profile photo
- Activity logs (per-role scope with date filtering)
- Interactive maps with color-coded markers by rock type
- Image galleries with thumbnail previews in rock detail views




## Role Capabilities

### Student
- Submit new rock samples
  - Rock Type via dropdown (Igneous, Sedimentary, Metamorphic)
  - Required latitude/longitude coordinates
  - Optional formation, barangay, province
  - Upload specimen/outcrop images
- Pending Verifications
  - Edit and update pending samples
  - Delete only if status is pending (cannot delete verified samples)
- View Verified Rocks
  - View all verified rock samples from all students
  - Filter by search query, rock type, location, and date range
  - See own verified samples highlighted separately
- Edit Rock Samples
  - Edit own pending samples
  - Edit own verified samples (status and verified_by preserved)
  - Update all fields including images
- Archives
  - View own archived samples (read-only)
- Logs
  - View personal activity logs with date filtering
- Interactive Map
  - View verified rock sample locations from all students
  - City selector and click-to-filter cities
  - See specimen count per city and navigate to details
  - Color-coded markers by rock type
- Rock Details
  - View details for own samples (any status: pending, verified, rejected)
  - View verified samples from other students
  - See images, metadata, and approval history
- Export
  - Export verified rock list to CSV or Excel based on current filters
  - Includes image indicators and all metadata
- Settings
  - Update profile (Full Name, Email, Student ID)
  - Change password with validation and success/error banners
  - Upload/replace profile photo

### Personnel
- Verification Panel
  - Review submitted samples and verify/reject
  - Add remarks when approving or rejecting
  - View student information and submission details
- Rock Samples
  - Add new rock samples (auto-verified upon creation)
  - Edit any rock sample (all fields including images)
  - View verified rock samples (excluding archived)
  - Archive verified samples (cannot delete verified samples)
  - View own archived samples only
- Rock List
  - Search and filter verified rocks by rock ID, type, location, or student name
  - Filter by rock type (igneous, sedimentary, metamorphic)
- Rock Details
  - View detailed information for any accessible sample
  - See approval history and activity logs
  - View images and metadata
- Logs
  - View own activity logs with date filtering
- Interactive Map
  - View all rock sample locations (all statuses)
  - City selector and click-to-filter
  - Popups with rock metadata and deep links to sample details
  - Color-coded markers by rock type
- Export
  - Export verified rock list to CSV or Excel based on current filters
  - Includes image indicators and all metadata
- Settings
  - Read-only profile (Full Name, Email, Role)
  - Change password
  - Upload/replace profile photo

### Admin
- Manage Users
  - View users with role and status badges
  - Add User (School ID required only for Students)
  - Edit User (Username, Email, Full Name, Role, School ID, Active Status)
  - Update user passwords
  - Block/Unblock User (toggle active status)
  - Soft-delete users (deactivates to preserve rock associations)
  - Filter by Role (Admin, Personnel, Student)
- Rock Samples
  - Add Rock (auto-verified upon creation, with Rock Type dropdown)
  - Edit any rock sample (all fields including images)
  - List, search, and inspect all rock samples (excluding archived)
  - Filter by search query, rock type, and status (verified, pending, rejected, or all)
  - Archive verified samples (cannot delete verified samples)
  - View all archived samples (from all users)
  - Unarchive samples when required
- Rock Details
  - View detailed information for any rock sample
  - See approval history and activity logs
  - View images and metadata
- Activity Logs
  - View all activity logs across the system
  - Filter by user, action type, and date range
  - Filter UI consistent with Manage Users (styled filters)
- Interactive Map
  - View all rock sample locations (all statuses)
  - City selector and click-to-filter
  - Popups with rock metadata and deep links to sample details
  - Color-coded markers by rock type
- Export
  - Export rock list to CSV or Excel based on current filters and status
  - Includes image indicators and all metadata
  - Status filter affects export (verified, pending, rejected, or all)
- Settings
  - Update profile (Full Name, Email)
  - Change password
  - Upload/replace profile photo

## Data Integrity Rules
- Verified rocks cannot be deleted by any user.
- Students may only delete their own samples in PENDING status.
- Admins can deactivate (and reactivate) users to preserve historical rock associations; deletion is restricted and should be used cautiously.
- Admin and Personnel can archive rock samples (Personnel can view only their own archives; Admin can view all archives). Admins can also unarchive.

## Map UX Details
- Specimen Markers: color-coded by rock type (purple for igneous, red for sedimentary, green for metamorphic)
- Filters: Rock ID (text search), Rock Type (dropdown), City/Municipality (dropdown) with "Clear Filters" button
- City dropdown: compact control above the map; selecting updates markers and auto-zooms to filtered specimens
- Specimen count badge: displays the number of filtered specimens
- Popups: concise rock information with deep links to detail pages appropriate to the user's role
- Consistent navigation: map and list views share filter semantics for seamless user experience

## Map Features
- Base map:
  - OpenStreetMap standard tiles via Leaflet `L.tileLayer(...)` with proper attribution
  - Initial view centered near Caraga Region (approx. 8.9475, 125.5406), zoom 6
- Specimen visualization:
  - Each rock specimen is rendered as a `L.circleMarker` with color-styling by Rock Type:
    - Igneous Rock: Purple (#9933cc)
    - Sedimentary Rock: Red (#dc2626)
    - Metamorphic Rock: Green (#16a34a)
  - Dynamic re-render of markers on filter changes
  - Automatic viewport: when markers are present, `fitBounds` pads to show all; if none, resets to default view
- Popups:
  - Show Rock ID, Rock Type, Formation, Location (City/Municipality), Coordinates, and Created Date (when available)
  - Thumbnail previews for specimen and outcrop images displayed inline (64x64px)
  - Role-aware deep links to the appropriate detail page (student/personnel/admin)
- Controls and filters:
  - Rock ID filter: text input with debounced search (300ms) for case-insensitive partial matching
  - Rock Type filter: dropdown selector (All Types, Igneous Rock, Sedimentary Rock, Metamorphic Rock)
  - City/Municipality filter: dropdown (`#city-select`) populated with cities sorted alphabetically, showing specimen count per city
  - Clear Filters button: resets all filters and refreshes the map view
  - Specimen count badge: displays the current number of filtered specimens
  - Shared filter semantics with list pages for consistency
- Legend and theming:
  - Compact legend and control container styled for readability
  - Dark mode tweaks for Leaflet UI and popups for better contrast
- Per-role behavior:
  - Students: view verified markers from all users; popups link to `/student/rock-detail/:id`
  - Personnel: view all relevant markers; popups link to `/personnel/rock-detail/:id`
  - Admin: view all markers across the system; popups link to `/admin/rock-detail/:id`
- Performance notes:
  - Markers are rendered as lightweight circle markers; clustering is not enabled
  - For very large datasets, consider server-side filtering and marker clustering in future versions

## Installation & Setup
1. Create and activate a Python virtual environment.
   - `python -m venv venv && source venv/bin/activate`
2. Install dependencies from `requirements.txt`.
   - `pip install -r requirements.txt`
3. Configure environment variables (or a `.env` file) for database access (see `config.py`):
   - `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - `SECRET_KEY`, `FLASK_ENV` (or `FLASK_DEBUG`)
   - Optional: `MAX_FILE_SIZE` (default: 16MB)
4. Initialize the database schema (import `webgisDB.sql` via phpMyAdmin or MySQL CLI).
5. Run the Flask app:
   - Using Flask CLI: `export FLASK_APP=app.py && flask run`
   - Direct execution: `python app.py` (runs on port 5817 by default, host 0.0.0.0)

### Configuration (.env example)
Create a `.env` file in the project root for local development:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=webgisDB

SECRET_KEY=change_me_in_production
FLASK_ENV=development
FLASK_DEBUG=True
MAX_FILE_SIZE=16777216
```

**Note**: The default database name is `webgisDB` (case-sensitive). Ensure your MySQL/MariaDB database matches this name or update `DB_NAME` in your `.env` file.

## Project Structure
The following tree shows the key folders and files in this repository. It excludes the `MISC/` directory.

```text
web-gis/
├─ app.py
├─ auth_utils.py
├─ config.py
├─ db_utils.py
├─ README.md
├─ requirements.txt
├─ webgisDB.sql
├─ user_accounts.csv
├─ scripts/
│  ├─ README_POPULATE.md
│  ├─ populate_database.py
│  ├─ update_accounts_from_csv.py
│  └─ user_accounts.csv
├─ static/
│  └─ photos/
│     └─ logo.png
├─ templates/
│  ├─ admin/
│  │  ├─ activity_logs.html
│  │  ├─ add_rock.html
│  │  ├─ archives.html
│  │  ├─ dashboard.html
│  │  ├─ edit_rock.html
│  │  ├─ edit_user.html
│  │  ├─ manage_users.html
│  │  ├─ map.html
│  │  ├─ rock_detail_view.html
│  │  ├─ rock_list_view.html
│  │  └─ settings.html
│  ├─ admin_base.html
│  ├─ base.html
│  ├─ login.html
│  ├─ personnel/
│  │  ├─ activity_logs.html
│  │  ├─ add_rock.html
│  │  ├─ archives.html
│  │  ├─ dashboard.html
│  │  ├─ edit_rock.html
│  │  ├─ map.html
│  │  ├─ rock_detail_view.html
│  │  ├─ rock_list_view.html
│  │  ├─ settings.html
│  │  └─ verification_panel.html
│  ├─ personnel_base.html
│  ├─ signup.html
│  ├─ students/
│  │  ├─ add_rock.html
│  │  ├─ archives.html
│  │  ├─ dashboard.html
│  │  ├─ edit_rock.html
│  │  ├─ logs.html
│  │  ├─ map.html
│  │  ├─ pending_verifications.html
│  │  ├─ rock_detail.html
│  │  ├─ settings.html
│  │  └─ view_rocks.html
│  └─ students_base.html
└─ venv/  (virtual environment; not required in production repos)
```

- `app.py`: Main Flask application with routes and views (runs on port 5817 by default)
- `auth_utils.py`: Authentication helpers (login required, role checks, session helpers)
- `db_utils.py`: Database connection factory and query utilities (MySQL/MariaDB via mysql-connector-python)
- `config.py`: Environment-driven configuration (loads from .env via python-dotenv)
- `templates/`: Role-based pages and layout bases (Jinja2 templates)
- `static/`: Static assets (CSS, images, etc.)
- `scripts/`: Data seeding and maintenance utilities
- `webgisDB.sql`: Canonical schema/data dump for initializing the database (default database name: webgisDB)

## Security Notes
- Email-only login; username is not accepted at login (role confirmation required)
- Sessions are HTTP-only by default; set `SESSION_COOKIE_SECURE=True` for production (requires HTTPS)
- Passwords are hashed using Werkzeug (bcrypt/scrypt)
- Role checks applied to all protected routes (`@login_required`, `@role_required` decorators)
- File upload validation: 16MB max file size, image processing via Pillow
- SQL injection protection: parameterized queries throughout
- Avoid committing secrets; prefer environment variables or a local `.env` excluded from version control
- User deactivation: soft-delete preserves historical rock associations (no hard deletes)

## Recent Enhancements
- Email-only login with role confirmation and consistent auth feedback
- Compact headers and consistent filter UI across all views
- Rock Type dropdown on Add/Edit Rock for all roles (Students, Personnel, Admin)
- Student ability to edit verified rocks (status preserved)
- Profile management: update profile info, change password, upload profile photo (all roles)
- Personnel Settings page with password change and profile photo upload
- Manage Users: role filter, block/unblock, soft-deactivate instead of delete
- Admin can edit all user fields (username, email, role, school_id, active status)
- Verified rock protection and archiving (Admin and Personnel)
- Admin can unarchive archived samples
- CSV/Excel export for rock lists (role-scoped with image indicators)
- Rock detail pages with image galleries and approval history
- Enhanced filtering: search by rock ID, type, location, student name, date range
- Location fields: barangay and province support added
- Activity logging for all user actions with per-role filtering
- Image handling: automatic resizing for Excel exports (150px max), supports JPEG/PNG

## Maintenance & Housekeeping
- Safe to remove locally:
  - `__pycache__/` (Python bytecode cache)
  - `venv/` (recreate as needed)
  - Duplicate SQL dumps (keep `webgisDB.sql` in project root as canonical)
- Repository hygiene:
  - Keep one authoritative SQL dump (`webgisDB.sql` in project root)
  - Store one-off tools in `scripts/` (prune when obsolete)
  - Avoid committing local CSV/XLSX import artifacts unless required by the app
  - Keep `.env` and similar local config out of version control (.gitignore)

## Operational Notes
- Database backup/restore:
  - Backup: export via phpMyAdmin or `mysqldump webgisDB > webgisDB_backup.sql`
  - Restore: import `webgisDB.sql` via phpMyAdmin or `mysql webgisDB < webgisDB.sql`
  - Default database name: `webgisDB` (case-sensitive)
- Application runtime:
  - Default port: 5817 (when running `python app.py`)
  - Default host: 0.0.0.0 (accessible from all network interfaces)
  - Debug mode: enabled by default (set `FLASK_DEBUG=False` in production)
- File uploads and images:
  - Images are validated and processed with Pillow; prefer JPEG/PNG
  - Maximum file size: 16 MB per file (configurable via `MAX_FILE_SIZE` env var)
  - Images stored as BLOB in database (rock specimens and outcrop images)
  - Profile photos stored in users table (LONGBLOB)
  - Excel exports automatically resize images to 150px max while maintaining aspect ratio
  - Original images preserved; thumbnails generated on-the-fly for Excel exports
- Performance and security:
  - Use strong `SECRET_KEY` and set `SESSION_COOKIE_SECURE=True` in production
  - Restrict admin endpoints at the network layer (e.g., VPN or IP allowlist) for added safety
  - Rate-limit login if deploying to the public internet (e.g., proxy-based)

## Browser Support
- Modern Chromium-based browsers, Firefox, and Safari (latest two versions) are recommended
- Mobile UI is responsive; long tables provide horizontal scrolling

## Maps Attribution
- Map tiles by OpenStreetMap; app should include proper attribution in the map UI
- Built with Leaflet.js; follow Leaflet attribution guidelines