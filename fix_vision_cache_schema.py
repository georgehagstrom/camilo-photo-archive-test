#!/usr/bin/env python3
"""
Fix vision_cache to preserve multiple analyses per photo
"""

import sqlite3
import hashlib
from datetime import datetime

def fix_vision_cache_schema():
    """Migrate vision_cache to support multiple Q&As per photo"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    print("Backing up existing vision_cache data...")

    # Get existing data
    cursor.execute("SELECT photo_id, last_question, analysis, timestamp FROM vision_cache")
    existing_data = cursor.fetchall()
    print(f"Found {len(existing_data)} existing analyses")

    # Drop old table
    print("Dropping old vision_cache table...")
    cursor.execute("DROP TABLE IF EXISTS vision_cache")

    # Create new table with composite key
    print("Creating new vision_cache table...")
    cursor.execute("""
        CREATE TABLE vision_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            question_hash TEXT NOT NULL,
            analysis TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE,
            UNIQUE(photo_id, question_hash)
        )
    """)

    # Create indexes for fast lookups
    cursor.execute("""
        CREATE INDEX idx_vision_cache_photo
        ON vision_cache(photo_id)
    """)

    cursor.execute("""
        CREATE INDEX idx_vision_cache_hash
        ON vision_cache(photo_id, question_hash)
    """)

    print("✓ New schema created")

    # Restore existing data
    if existing_data:
        print(f"Restoring {len(existing_data)} existing analyses...")
        for photo_id, question, analysis, timestamp in existing_data:
            # Create hash of question for deduplication
            question = question or "general"
            question_hash = hashlib.md5(question.lower().strip().encode()).hexdigest()[:16]

            cursor.execute("""
                INSERT OR IGNORE INTO vision_cache
                (photo_id, question, question_hash, analysis, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (photo_id, question, question_hash, analysis, timestamp))
        print("✓ Data restored")

    conn.commit()
    conn.close()

    print("\n✓ Vision cache schema fixed!")
    print("\nNew features:")
    print("  - Multiple analyses per photo preserved")
    print("  - Each unique question gets its own cache entry")
    print("  - Same question reuses cached answer")
    print("  - Full analysis history maintained")

if __name__ == '__main__':
    fix_vision_cache_schema()
