# Database Population Guide

This guide explains how to populate the web-gis database with sample accounts and rock sample data.

## Prerequisites

1. Ensure XAMPP MySQL is running
2. Make sure the database `webgisDB` exists
3. Ensure all required tables are created (run the database schema SQL if needed)

## Running the Population Script

### Option 1: Replace All Data (Recommended for fresh start)

This will **delete all existing data** and populate with new data:

```bash
cd /Users/stephen/Documents/[00]\ School\ Works/SYSTEM\ PROJECTS/web-gis
python3 scripts/populate_database.py
```

### Option 2: Add Data Without Deleting (Append mode)

This will add new data on top of existing data:

```bash
cd /Users/stephen/Documents/[00]\ School\ Works/SYSTEM\ PROJECTS/web-gis
python3 scripts/populate_database.py --skip-truncate
```

## What Gets Created

### User Accounts (18 accounts)
- **2 Admin accounts**: admin@gmail.com, admin2@gmail.com (password: admin123)
- **3 Personnel accounts**: personnel@gmail.com, personnel2@gmail.com, personnel3@gmail.com (password: personnel123)
- **13 Student accounts**: student@gmail.com, student2@gmail.com, etc. (password: student123)

### Rock Samples (28 samples)
- **24 Verified samples** - distributed across all students
- **3 Pending samples** - awaiting verification
- **1 Rejected sample** - rejected sample

### Rock Types
- **Igneous Rocks**: 10 samples (Basalt, Granite, Andesite, Dacite, Rhyolite, Obsidian, Pumice, Gabbro, Diorite)
- **Sedimentary Rocks**: 9 samples (Sandstone, Limestone, Shale, Conglomerate, Mudstone, Siltstone, Coal, Chert, Breccia, Chalk)
- **Metamorphic Rocks**: 9 samples (Schist, Gneiss, Marble, Quartzite, Slate, Amphibolite, Phyllite)

### Locations
Samples are distributed across various Philippine locations including:
- Butuan, Cagayan de Oro, Surigao City, Davao City
- Cebu City, Bacolod, Iloilo City
- Baguio, Bontoc, Marikina, Quezon City
- And many more locations across the Philippines

## Testing the Data

After running the script:

1. **Login as a student** (e.g., student@gmail.com / student123)
2. **View Verified Rocks** - You should see verified rocks in the "My Verified Samples" section
3. **Check the map** - Verified rocks should appear on the map
4. **View all rocks** - The "All Rock Sample List" should show all verified rocks from all students

## Troubleshooting

### Error: "No accounts found in CSV"
- Make sure `scripts/user_accounts.csv` exists and has the correct format
- Check that the CSV has "Email" and "Password" columns

### Error: "At least one student account is required"
- Make sure the CSV contains at least one student account
- Student accounts are identified by email (not containing "admin" or "personnel")

### Error: Database connection failed
- Ensure XAMPP MySQL is running
- Check database credentials in `db_utils.py`
- Verify database name is `webgisDB`

## Customizing the Data

### Adding More Accounts
Edit `scripts/user_accounts.csv` and add more rows:
```csv
Email,Password
newstudent@gmail.com,password123
```

### Modifying Rock Samples
Edit the `build_sample_records()` function in `scripts/populate_database.py` to add or modify rock samples.

## Notes

- All passwords are hashed using Werkzeug's password hashing
- Rock samples are distributed evenly across all students
- Verified samples are assigned to different personnel for diversity
- The script automatically creates approval logs and activity logs for verified/rejected samples

