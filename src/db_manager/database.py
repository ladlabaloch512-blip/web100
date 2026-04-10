import sqlite3
import os

DB_FILE = "abiz_drafts.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT,
            listing_id TEXT,
            url TEXT,
            title TEXT,
            status TEXT
        )
    """)
    conn.commit()
    conn.close()

def insert_draft(profile_name, listing_id, url, title, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO drafts (profile_name, listing_id, url, title, status)
        VALUES (?, ?, ?, ?, ?)
    """, (profile_name, listing_id, url, title, status))
    conn.commit()
    conn.close()

def get_drafts_by_profile(profile_name, status="Drafted"):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT listing_id, url, title FROM drafts
        WHERE profile_name = ? AND status = ?
    """, (profile_name, status))
    drafts = cursor.fetchall()
    conn.close()
    return drafts

def update_draft_status(listing_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE drafts SET status = ? WHERE listing_id = ?
    """, (status, listing_id))
    conn.commit()
    conn.close()

init_db()
