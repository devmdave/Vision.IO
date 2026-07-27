import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vision_io.db")

def get_connection():
    """Returns a connection to the SQLite database. Enables foreign keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds default data if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create Cameras Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cameras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        type TEXT NOT NULL
    );
    """)

    # Create Rules Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camera_id INTEGER NOT NULL,
        rule_text TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE
    );
    """)

    # Create Incidents Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        camera_id INTEGER NOT NULL,
        camera_name TEXT NOT NULL,
        snapshot_path TEXT NOT NULL,
        explanation TEXT,
        alert INTEGER DEFAULT 1,
        false_positive INTEGER DEFAULT 0,
        FOREIGN KEY (camera_id) REFERENCES cameras (id) ON DELETE CASCADE
    );
    """)

    # Check if empty and seed mock data
    cursor.execute("SELECT COUNT(*) FROM cameras;")
    if cursor.fetchone()[0] == 0:
        # Seed default USB camera and mock RTSP camera
        cursor.execute("INSERT INTO cameras (name, url, status, type) VALUES (?, ?, ?, ?);",
                       ("USB Webcam 0", "0", "active", "USB"))
        cursor.execute("INSERT INTO cameras (name, url, status, type) VALUES (?, ?, ?, ?);",
                       ("Front Porch Camera", "rtsp://localhost:8554/porch", "active", "RTSP"))
        camera_id = cursor.lastrowid
        
        # Seed default VLM rules
        cursor.execute("INSERT INTO rules (camera_id, rule_text, active) VALUES (?, ?, ?);",
                       (1, "Alert if a person is standing by the window after 10 PM.", 1))
        cursor.execute("INSERT INTO rules (camera_id, rule_text, active) VALUES (?, ?, ?);",
                       (2, "Alert if a delivery vehicle or truck parks in the driveway.", 1))
        
        # Seed an initial mock incident
        cursor.execute("""
        INSERT INTO incidents (timestamp, camera_id, camera_name, snapshot_path, explanation, alert, false_positive)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            1,
            "USB Webcam 0",
            "mock_snapshot.jpg",
            "A person carrying a package was detected approaching the main entry door.",
            1,
            0
        ))

    conn.commit()
    conn.close()

# --- Cameras API ---

def get_all_cameras():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cameras;")
    cameras = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return cameras

def add_camera(name, url, cam_type):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cameras (name, url, type) VALUES (?, ?, ?);", (name, url, cam_type))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def delete_camera(camera_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cameras WHERE id = ?;", (camera_id,))
    conn.commit()
    conn.close()

# --- Rules API ---

def get_rules_by_camera(camera_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules WHERE camera_id = ?;", (camera_id,))
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

def get_all_active_rules():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rules.*, cameras.name as camera_name FROM rules JOIN cameras ON rules.camera_id = cameras.id WHERE rules.active = 1;")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

def get_all_rules():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT rules.*, cameras.name as camera_name FROM rules JOIN cameras ON rules.camera_id = cameras.id;")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

def add_rule(camera_id, rule_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO rules (camera_id, rule_text) VALUES (?, ?);", (camera_id, rule_text))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def toggle_rule(rule_id, active):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE rules SET active = ? WHERE id = ?;", (1 if active else 0, rule_id))
    conn.commit()
    conn.close()

def delete_rule(rule_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM rules WHERE id = ?;", (rule_id,))
    conn.commit()
    conn.close()

# --- Incidents API ---

def log_incident(camera_id, camera_name, snapshot_path, explanation, alert=1):
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO incidents (timestamp, camera_id, camera_name, snapshot_path, explanation, alert)
    VALUES (?, ?, ?, ?, ?, ?);
    """, (timestamp, camera_id, camera_name, snapshot_path, explanation, alert))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_all_incidents():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM incidents ORDER BY id DESC;")
    incidents = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return incidents

def toggle_false_positive(incident_id, is_false_positive):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE incidents SET false_positive = ? WHERE id = ?;", (1 if is_false_positive else 0, incident_id))
    conn.commit()
    conn.close()

def delete_incident(incident_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM incidents WHERE id = ?;", (incident_id,))
    conn.commit()
    conn.close()
