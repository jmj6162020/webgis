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
  - Leaflet core: `L.map`, `L.tileLayer`, `L.circleMarker`, `bindPopup`, `fitBounds`
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
- Email-based login (email + password, role confirmation)
- Role-aware dashboards and navigation
- Interactive map with city dots (blue) and specimen markers (purple)
 - Consistent filters across list/map views (city, rock type, search)
 - Rock details with images and metadata (role-scoped visibility)
 - Export filtered rock lists to CSV/Excel (role-scoped)
 - Profile management: change password and upload profile photo
 - Activity logs (per-role scope)




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
- Archives
  - View own archived samples (read-only)
- Logs
  - View personal activity logs
- Interactive Map
  - City selector and click-to-filter cities
  - See specimen count per city and navigate to details
- Rock Details
  - View details for own samples (any status) and verified samples from others
- Export
  - Export verified rock list to CSV or Excel based on current filters
- Settings
  - Read-only profile info (Full Name, Email, Student ID)
  - Change password with validation and success/error banners
  - Upload/replace profile photo

### Personnel
 - Verification Panel
  - Review submitted samples and verify/reject
- Rock Samples
   - Add and edit own samples
  - Archive verified samples (cannot delete verified samples)
  - View own archived samples
- Logs
  - View activity logs
- Interactive Map
  - Same capabilities as admin map, with personnel-specific details
- Activity Logs (view)
- Rock Details
  - View detailed information for any accessible sample with history
- Export
  - Export verified rock list to CSV or Excel based on current filters
- Settings
  - Read-only profile (Full Name, Email, Role)
   - Change password
   - Upload/replace profile photo

### Admin
- Manage Users
  - View users with role and status badges
  - Add User (School ID required only for Students)
  - Edit User (Full Name only; Username/Email/Role are disabled)
  - Block/Unblock User (toggle active status)
  - Activate/Deactivate users; delete user when necessary per policy
  - Filter by Role (Admin, Personnel, Student)
- Rock Samples
  - Add Rock (with the same dropdown for Rock Type)
  - List, search, and inspect rock samples
  - Archive verified samples (cannot delete verified samples)
  - View all archived samples (from all users)
   - Unarchive samples when required
- Activity Logs
  - Filter UI consistent with Manage Users (styled filters)
- Interactive Map
  - City selector and click-to-filter
  - Popups with rock metadata and deep links to sample details
- Export
  - Export rock list to CSV or Excel based on current filters and status
- Settings
  - Update profile (Full Name); Email is disabled
   - Change password
   - Upload/replace profile photo

## Data Integrity Rules
- Verified rocks cannot be deleted by any user.
- Students may only delete their own samples in PENDING status.
- Admins can deactivate (and reactivate) users to preserve historical rock associations; deletion is restricted and should be used cautiously.
- Admin and Personnel can archive rock samples (Personnel can view only their own archives; Admin can view all archives). Admins can also unarchive.

## Map UX Details
- City Markers (blue): represent cities/municipalities by average coordinates
- Specimen Markers (purple): appear after selecting a city
- City dropdown: compact control above the map; selecting updates markers and auto-zooms
- Popups: concise rock information with deep links to detail pages appropriate to the user’s role
- Filters: map and list views share filters (city, rock type, search) for consistent navigation

## Map Features
- Base map:
  - OpenStreetMap standard tiles via Leaflet `L.tileLayer(...)` with proper attribution
  - Initial view centered near Caraga Region (approx. 8.9475, 125.5406), zoom 6
- Specimen visualization:
  - Each rock specimen is rendered as a `L.circleMarker` with color-styling by Rock Type
  - Dynamic re-render of markers on filter changes
  - Automatic viewport: when markers are present, `fitBounds` pads to show all; if none, resets to default view
- Popups:
  - Show Rock ID, Rock Type, Formation, City, and Created Date (when available)
  - Thumbnail previews for specimen and outcrop images displayed inline
  - Role-aware deep links to the appropriate detail page (student/personnel/admin)
- Controls and filters:
  - City dropdown (`#city-select`) to filter by municipality/city and re-zoom
  - Rock Type selector and free-text search for quick narrowing
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
   - `SECRET_KEY`, `FLASK_ENV`
4. Initialize the database schema (import `db/webgisDB.sql` via phpMyAdmin or MySQL CLI).
5. Run the Flask app:
   - `export FLASK_APP=app.py`
   - `flask run` (or `python app.py`)

### Configuration (.env example)
Create a `.env` file in the project root for local development:

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=webgisdb

SECRET_KEY=change_me_in_production
FLASK_ENV=development
```

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

- `app.py`: Main Flask application with routes and views
- `auth_utils.py`: Authentication helpers (login required, role checks, session helpers)
- `db_utils.py`: Database connection factory and query utilities
- `config.py`: Environment-driven configuration
- `templates/`: Role-based pages and layout bases
- `static/`: Static assets
- `scripts/`: Data seeding and maintenance utilities
- `webgisDB.sql`: Canonical schema/data dump for initializing the database

## Security Notes
- Email-only login; username is not accepted at login
- Sessions are HTTP-only; consider `SESSION_COOKIE_SECURE=True` for production
- Passwords are hashed (Werkzeug)
- Role checks applied to all protected routes (`@login_required`, `@role_required`)
- Avoid committing secrets; prefer environment variables or a local `.env` excluded from version control

## Recent Enhancements
- Email-only login and consistent auth feedback
- Compact headers and consistent filter UI
- Rock Type dropdown on Add/Edit Rock for Students and Admin
- Personnel Settings page with password change
- Manage Users: role filter, block/unblock, soft-deactivate instead of delete
- Verified rock protection and archiving (Admin and Personnel)
- CSV/Excel export for rock lists (role-scoped)
- Rock detail pages with image galleries and approval history
- Profile photo upload in Settings (all roles)
- Admin unarchive for archived samples

## Maintenance & Housekeeping
- Safe to remove locally:
  - `__pycache__/` (Python bytecode cache)
  - `venv/` (recreate as needed)
  - Duplicate SQL dumps outside `db/` (keep `db/webgisDB.sql` canonical)
- Repository hygiene:
  - Keep one authoritative SQL dump in `db/`
  - Store one-off tools in `scripts/` (prune when obsolete)
  - Avoid committing local CSV/XLSX import artifacts unless required by the app
  - Keep `.env` and similar local config out of version control (.gitignore)

## Operational Notes
- Database backup/restore:
  - Backup: export via phpMyAdmin or `mysqldump webgisdb > db/webgisDB.sql`
  - Restore: import `db/webgisDB.sql` via phpMyAdmin or `mysql webgisdb < db/webgisDB.sql`
- File uploads and images:
  - Images are validated and processed with Pillow; prefer JPEG/PNG
  - Recommended max image size: ≤5 MB per file for smoother uploads
  - Store original images securely; thumbnails can be generated on demand if needed
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