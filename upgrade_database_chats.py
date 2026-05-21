#!/usr/bin/env python3
"""
Upgrade database to add chat persistence and photo references
"""

import sqlite3
from datetime import datetime

def upgrade_database():
    """Add tables for chat persistence with photo references"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    # Check if tables already exist
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='chat_sessions'
    """)

    if cursor.fetchone():
        print("✓ Chat tables already exist")
        conn.close()
        return

    print("Creating chat persistence tables...")

    # Chat sessions table
    cursor.execute("""
        CREATE TABLE chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL
        )
    """)
    print("✓ Created chat_sessions table")

    # Chat messages table with photo references
    cursor.execute("""
        CREATE TABLE chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            photo_id INTEGER,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE SET NULL
        )
    """)
    print("✓ Created chat_messages table")

    # Many-to-many relationship: sessions to photos
    cursor.execute("""
        CREATE TABLE chat_session_photos (
            session_id INTEGER NOT NULL,
            photo_id INTEGER NOT NULL,
            PRIMARY KEY (session_id, photo_id),
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
        )
    """)
    print("✓ Created chat_session_photos table")

    # Vision analysis cache
    cursor.execute("""
        CREATE TABLE vision_cache (
            photo_id INTEGER PRIMARY KEY,
            last_question TEXT,
            analysis TEXT,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE
        )
    """)
    print("✓ Created vision_cache table")

    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX idx_chat_messages_session
        ON chat_messages(session_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_chat_messages_photo
        ON chat_messages(photo_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_chat_session_photos_photo
        ON chat_session_photos(photo_id)
    """)

    print("✓ Created indexes")

    conn.commit()
    conn.close()

    print("\n✓ Database upgrade complete!")
    print("\nNew features enabled:")
    print("  - Save and load chat sessions")
    print("  - Automatic photo reference tracking")
    print("  - Search chats by photo")
    print("  - Vision analysis caching")

if __name__ == '__main__':
    upgrade_database()
