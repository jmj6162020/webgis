-- ============================================================================
-- ROCK SAMPLE INDEX SYSTEM - DATABASE SCHEMA
-- MySQL/MariaDB Database Creation Script
-- Target: XAMPP (MySQL/MariaDB)
-- Normalization: 3NF (Third Normal Form)
-- ============================================================================
-- Description: Geological specimen collection management system
-- Features: Direct image storage in database (BLOB)
-- ============================================================================

-- Drop database if exists (CAUTION: This will delete all data)
-- Uncomment the line below if you want to recreate the database from scratch
-- DROP DATABASE IF EXISTS rock_sample_index;

-- Create database
CREATE DATABASE IF NOT EXISTS webgisDB
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Use the database
USE webgisDB;

-- ============================================================================
-- TABLE 1: USERS
-- Description: Stores all user information (Admin, Personnel, Students)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY  ,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    role ENUM('admin', 'personnel', 'student') NOT NULL DEFAULT 'student',
    school_id VARCHAR(50) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 2: ROCK_SAMPLES
-- Description: Stores rock specimen information with location data
-- ============================================================================
CREATE TABLE IF NOT EXISTS rock_samples (
    sample_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    verified_by INT NULL,
    rock_index VARCHAR(50) NOT NULL,
    rock_id VARCHAR(50) NOT NULL UNIQUE,
    rock_type VARCHAR(100) NOT NULL,
    description TEXT NULL,
    formation VARCHAR(100) NULL,
    outcrop_id VARCHAR(50) NULL,
    location_name VARCHAR(100) NOT NULL,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    status ENUM('pending', 'verified', 'rejected') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (verified_by) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_verified_by (verified_by),
    INDEX idx_rock_id (rock_id),
    INDEX idx_rock_type (rock_type),
    INDEX idx_status (status),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 3: IMAGES
-- Description: Stores rock and outcrop images as binary data (BLOB)
-- ============================================================================
CREATE TABLE IF NOT EXISTS images (
    image_id INT AUTO_INCREMENT PRIMARY KEY,
    sample_id INT NOT NULL,
    image_type ENUM('rock_specimen', 'outcrop') NOT NULL,
    image_data LONGBLOB NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size INT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sample_id) REFERENCES rock_samples(sample_id) ON DELETE CASCADE,
    INDEX idx_sample_id (sample_id),
    INDEX idx_image_type (image_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 4: ACTIVITY_LOGS
-- Description: Tracks all user activities in the system
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_logs (
    activity_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    sample_id INT NULL,
    activity_type ENUM('approved', 'rejected', 'edited', 'submitted', 'archived', 'deleted') NOT NULL,
    description TEXT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (sample_id) REFERENCES rock_samples(sample_id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_sample_id (sample_id),
    INDEX idx_activity_type (activity_type),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 5: APPROVAL_LOGS
-- Description: Records approval/rejection actions by personnel
-- ============================================================================
CREATE TABLE IF NOT EXISTS approval_logs (
    approval_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    sample_id INT NOT NULL,
    action ENUM('approved', 'rejected') NOT NULL,
    remarks TEXT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (sample_id) REFERENCES rock_samples(sample_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_sample_id (sample_id),
    INDEX idx_action (action),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- TABLE 6: ARCHIVES
-- Description: Stores archived rock samples with archive information
-- ============================================================================
CREATE TABLE IF NOT EXISTS archives (
    archive_id INT AUTO_INCREMENT PRIMARY KEY,
    sample_id INT NOT NULL,
    archived_by INT NOT NULL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archive_reason TEXT NULL,
    status VARCHAR(50) NULL,
    FOREIGN KEY (sample_id) REFERENCES rock_samples(sample_id) ON DELETE CASCADE,
    FOREIGN KEY (archived_by) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_sample_id (sample_id),
    INDEX idx_archived_by (archived_by),
    INDEX idx_archived_at (archived_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SAMPLE DATA INSERTION (Optional)
-- Only users are inserted here. No rock sample data is inserted.
-- ============================================================================

-- Insert sample users (password hashes are placeholders; change for production)
INSERT INTO users (username, email, password_hash, first_name, last_name, role, is_active) 
VALUES 
    ('admin', 'admin@gmail.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyJb8K7JpqeG', 'System', 'Administrator', 'admin', TRUE),
    ('personnel1', 'personnel@gmail.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyJb8K7JpqeG', 'John', 'Smith', 'personnel', TRUE),
    ('student1', 'student@gmail.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyJb8K7JpqeG', 'Jane', 'Doe', 'student', TRUE);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: All verified rock samples with student and verifier information
CREATE OR REPLACE VIEW verified_rocks_view AS
SELECT 
    rs.sample_id,
    rs.rock_id,
    rs.rock_type,
    rs.description,
    rs.formation,
    rs.location_name,
    rs.latitude,
    rs.longitude,
    rs.status,
    rs.created_at,
    CONCAT(u.first_name, ' ', u.last_name) AS student_name,
    u.school_id,
    CONCAT(v.first_name, ' ', v.last_name) AS verified_by_name,
    rs.updated_at AS verified_at
FROM rock_samples rs
INNER JOIN users u ON rs.user_id = u.user_id
LEFT JOIN users v ON rs.verified_by = v.user_id
WHERE rs.status = 'verified';

-- View: Pending verifications
CREATE OR REPLACE VIEW pending_verifications_view AS
SELECT 
    rs.sample_id,
    rs.rock_id,
    rs.rock_type,
    rs.location_name,
    CONCAT(u.first_name, ' ', u.last_name) AS student_name,
    u.email AS student_email,
    rs.created_at AS submitted_at
FROM rock_samples rs
INNER JOIN users u ON rs.user_id = u.user_id
WHERE rs.status = 'pending'
ORDER BY rs.created_at ASC;

-- View: Recent activity logs with user and rock information
CREATE OR REPLACE VIEW recent_activity_view AS
SELECT 
    al.activity_id,
    al.activity_type,
    al.description,
    al.timestamp,
    CONCAT(u.first_name, ' ', u.last_name) AS user_name,
    u.role AS user_role,
    rs.rock_id,
    rs.rock_type
FROM activity_logs al
INNER JOIN users u ON al.user_id = u.user_id
LEFT JOIN rock_samples rs ON al.sample_id = rs.sample_id
ORDER BY al.timestamp DESC;

-- ============================================================================
-- STORED PROCEDURES
-- ============================================================================

-- Procedure: Approve a rock sample
DELIMITER //
CREATE PROCEDURE approve_rock_sample(
    IN p_sample_id INT,
    IN p_verifier_id INT,
    IN p_remarks TEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error approving rock sample';
    END;
    
    START TRANSACTION;
    
    -- Update rock sample status
    UPDATE rock_samples 
    SET status = 'verified', 
        verified_by = p_verifier_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE sample_id = p_sample_id;
    
    -- Log the approval
    INSERT INTO approval_logs (user_id, sample_id, action, remarks)
    VALUES (p_verifier_id, p_sample_id, 'approved', p_remarks);
    
    -- Log the activity
    INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
    VALUES (p_verifier_id, p_sample_id, 'approved', 'Rock sample approved');
    
    COMMIT;
END //
DELIMITER ;

-- Procedure: Reject a rock sample
DELIMITER //
CREATE PROCEDURE reject_rock_sample(
    IN p_sample_id INT,
    IN p_verifier_id INT,
    IN p_remarks TEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error rejecting rock sample';
    END;
    
    START TRANSACTION;
    
    -- Update rock sample status
    UPDATE rock_samples 
    SET status = 'rejected', 
        verified_by = p_verifier_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE sample_id = p_sample_id;
    
    -- Log the rejection
    INSERT INTO approval_logs (user_id, sample_id, action, remarks)
    VALUES (p_verifier_id, p_sample_id, 'rejected', p_remarks);
    
    -- Log the activity
    INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
    VALUES (p_verifier_id, p_sample_id, 'rejected', 'Rock sample rejected');
    
    COMMIT;
END //
DELIMITER ;

-- Procedure: Archive a rock sample
DELIMITER //
CREATE PROCEDURE archive_rock_sample(
    IN p_sample_id INT,
    IN p_user_id INT,
    IN p_reason TEXT
)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error archiving rock sample';
    END;
    
    START TRANSACTION;
    
    -- Create archive record
    INSERT INTO archives (sample_id, archived_by, archive_reason, status)
    VALUES (p_sample_id, p_user_id, p_reason, 'archived');
    
    -- Log the activity
    INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
    VALUES (p_user_id, p_sample_id, 'archived', CONCAT('Rock sample archived: ', p_reason));
    
    COMMIT;
END //
DELIMITER ;

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger: Log rock sample submission
DELIMITER //
CREATE TRIGGER after_rock_sample_insert
AFTER INSERT ON rock_samples
FOR EACH ROW
BEGIN
    INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
    VALUES (NEW.user_id, NEW.sample_id, 'submitted', 'New rock sample submitted');
END //
DELIMITER ;

-- Trigger: Log rock sample updates
DELIMITER //
CREATE TRIGGER after_rock_sample_update
AFTER UPDATE ON rock_samples
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO activity_logs (user_id, sample_id, activity_type, description)
        VALUES (NEW.verified_by, NEW.sample_id, 'edited', 
                CONCAT('Status changed from ', OLD.status, ' to ', NEW.status));
    END IF;
END //
DELIMITER ;

-- ============================================================================
-- INDEXES FOR PERFORMANCE OPTIMIZATION
-- ============================================================================

-- Additional composite indexes for common queries
CREATE INDEX idx_rocks_user_status ON rock_samples(user_id, status);
CREATE INDEX idx_rocks_verified_status ON rock_samples(verified_by, status);
CREATE INDEX idx_activity_user_timestamp ON activity_logs(user_id, timestamp);
CREATE INDEX idx_images_sample_type ON images(sample_id, image_type);

-- ============================================================================
-- GRANT PERMISSIONS (Adjust according to your XAMPP setup)
-- ============================================================================

-- Create application user (optional)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON rock_sample_index.* TO 'rock_app'@'localhost' IDENTIFIED BY 'your_secure_password';
-- FLUSH PRIVILEGES;

-- ============================================================================
-- DATABASE SCHEMA INFORMATION
-- ============================================================================

SELECT 'Database schema created successfully!' AS Status;
SELECT DATABASE() AS Current_Database;
SHOW TABLES;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================

