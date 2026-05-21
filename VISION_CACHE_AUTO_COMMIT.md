# Vision Cache Auto-Commit

## Overview

Every vision AI analysis now automatically commits to GitHub, ensuring analyses persist across redeploys.

## How It Works

### Separate Entry Per Photo

Vision cache stores **one row per photo**:

```sql
CREATE TABLE vision_cache (
    photo_id INTEGER PRIMARY KEY,
    last_question TEXT,
    analysis TEXT,
    timestamp TIMESTAMP
);
```

**Example:**
- Analyze photo 1 → 1 row in vision_cache
- Analyze photos 1, 2, and 7 → 3 separate rows
- Re-analyze photo 1 → Updates existing row (INSERT OR REPLACE)

### Auto-Commit Flow

```
1. Chat analyzes photo 7 with vision AI
   ↓
2. save_vision_cache(7, "general", "Buildings show...")
   ↓
3. INSERT OR REPLACE INTO vision_cache...
   ↓
4. auto_commit_database("Auto-cache vision analysis: photo 7")
   ↓
5. Commits photo_archive.db to GitHub
   ↓
6. Streamlit Cloud detects commit
   ↓
7. Auto-redeploys app (~30 seconds)
   ↓
8. Analysis persists permanently!
```

## What Gets Auto-Committed

### 1. Vision Analyses
```python
# Every time chat uses vision AI:
result = analyze_image_vision(photo_id, question)
save_vision_cache(photo_id, question, result['analysis'])
auto_commit_database(f"Auto-cache vision analysis: photo {photo_id}")
```

**Commit message:** `Auto-cache vision analysis: photo 7`

### 2. Saved Chats
```python
# When you save a chat in sidebar:
save_chat_session(title, messages, photo_ids)
auto_commit_database(f"Auto-save chat: {title}")
```

**Commit message:** `Auto-save chat: My research session`

### 3. Metadata Edits
```python
# When admin edits photo metadata:
# (Uses existing inline auto-commit code)
```

**Commit message:** `Auto-update metadata: 7.jpeg (photo ID 7)`

## Targeted Searches

Each photo has its own cache entry, enabling efficient queries:

### Query 1: Find all photos with people
```sql
SELECT p.id, p.filename, v.analysis
FROM photos p
JOIN vision_cache v ON p.id = v.photo_id
WHERE v.analysis LIKE '%people%'
```

### Query 2: Check specific photo's analysis
```sql
SELECT analysis
FROM vision_cache
WHERE photo_id = 7
```

### Query 3: Get all cached analyses
```sql
SELECT p.*, v.analysis, v.timestamp
FROM photos p
LEFT JOIN vision_cache v ON p.id = v.photo_id
```

## Benefits

### ✅ Persistence
- Analyses survive redeploys
- No need to re-analyze photos
- Database grows with research

### ✅ Efficiency
- **First query:** Analyzes 6 photos, commits 6 times
- **Future queries:** Uses cached analyses, 0 API calls
- Chat checks cache first before new analyses

### ✅ Research Continuity
- Build knowledge over time
- Share analyses with collaborators
- Track what's been analyzed

### ✅ Targeted Access
- Each photo = separate row
- Fast lookups by photo_id
- Support complex JOINs

## Git Commit History

All auto-commits appear in git history:
https://github.com/georgehagstrom/camilo-photo-archive-test/commits/main

**Example commits:**
```
Auto-cache vision analysis: photo 7
Auto-cache vision analysis: photo 1
Auto-save chat: Finding photos with people
Auto-update metadata: 7.jpeg (photo ID 7)
```

## Performance

### Commit Frequency
- **Vision cache:** One commit per photo analyzed
- **Chat save:** One commit per chat saved
- **Metadata:** One commit per photo edited

### Redeploy Impact
- Each commit triggers redeploy (~30 seconds)
- During redeploy, app remains available (no downtime)
- Users may see "updating..." banner briefly

### For 6 Photos
- First-time analysis: 6 commits in quick succession
- Streamlit Cloud batches rapid commits
- Typically results in 1-2 actual redeploys

### For 21k Photos (Future)
- Analyze 100 photos = 100 commits
- Will need batching strategy
- Consider cloud database (PostgreSQL) to avoid redeploys

## Scaling Considerations

### Current (6 Photos)
✅ Auto-commit works perfectly
- Fast cache population
- Minimal redeploy overhead
- Git history stays clean

### Future (21k Photos)
⚠️ Need optimization:

**Option 1: Batch Commits**
```python
# Accumulate analyses, commit every N photos
if len(pending_analyses) >= 10:
    auto_commit_database("Auto-cache: 10 vision analyses")
```

**Option 2: Cloud Database**
```python
# PostgreSQL on Render/Supabase
# No redeploys needed
# Instant persistence
```

**Option 3: Hybrid**
```python
# Vision cache in cloud DB (fast, no redeploys)
# Metadata in SQLite (rare changes, auto-commit fine)
```

## Troubleshooting

### "Changes not persisting"
1. Check if GITHUB_TOKEN is set in Streamlit secrets
2. Look for commit at: https://github.com/georgehagstrom/camilo-photo-archive-test/commits/main
3. Wait 30-60 seconds for redeploy

### "Too many redeploys"
- Each commit triggers redeploy
- For batch analyses, commits happen in quick succession
- Streamlit Cloud handles this gracefully

### "Cache still empty after analysis"
1. Check if analysis succeeded (look for errors)
2. Check if commit happened (git history)
3. Verify GITHUB_TOKEN has repo write access

## Code Reference

### Helper Function
```python
def auto_commit_database(commit_message):
    """Auto-commit database to GitHub"""
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        return False

    g = Github(github_token)
    repo = g.get_repo("georgehagstrom/camilo-photo-archive-test")

    with open('photo_archive.db', 'rb') as f:
        content = f.read()

    file = repo.get_contents("photo_archive.db", ref="main")
    repo.update_file(
        path="photo_archive.db",
        message=commit_message,
        content=content,
        sha=file.sha,
        branch="main"
    )
    return True
```

### Vision Cache Save
```python
def save_vision_cache(photo_id, question, analysis):
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO vision_cache (photo_id, last_question, analysis, timestamp)
        VALUES (?, ?, ?, ?)
    """, (photo_id, question, analysis, datetime.now()))
    conn.commit()
    conn.close()

# In process_tool_call:
save_vision_cache(photo_id, question, result['analysis'])
auto_commit_database(f"Auto-cache vision analysis: photo {photo_id}")
```

## Result

**Complete persistence for all research data:**
- ✅ Vision analyses
- ✅ Saved chats
- ✅ Metadata edits
- ✅ Research notes

All automatically committed to GitHub, surviving redeploys and available to all collaborators!
