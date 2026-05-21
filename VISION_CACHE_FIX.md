# Vision Cache Fix: Preserving Multiple Analyses

## The Bug

**Original Schema:**
```sql
CREATE TABLE vision_cache (
    photo_id INTEGER PRIMARY KEY,  -- ⚠️ ONLY ONE ROW PER PHOTO
    last_question TEXT,
    analysis TEXT,
    timestamp TIMESTAMP
)
```

**Problem:**
Every new analysis of the same photo **replaced** the previous one:

```
1. User: "What buildings are in photo 7?"
   → Analysis A saved

2. User: "What's the building condition in photo 7?"
   → Analysis A DELETED, Analysis B saved

3. User: "Any people visible in photo 7?"
   → Analysis B DELETED, Analysis C saved
```

All previous research was lost!

## The Fix

**New Schema:**
```sql
CREATE TABLE vision_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    question_hash TEXT NOT NULL,  -- MD5 hash for deduplication
    analysis TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    UNIQUE(photo_id, question_hash)  -- One entry per photo+question combo
)
```

**Now:**
- Each unique question gets its own cache entry
- All previous analyses are preserved
- Asking the same question reuses cached answer
- Different questions create new entries

## How It Works

### Question Hashing
Questions are normalized and hashed to detect duplicates:

```python
# These are treated as the same question:
"What buildings are visible?"
"what buildings are visible?"
"What buildings are visible?    "

# MD5 hash: "3f2a1b4c..."
```

### Cache Lookup
```python
cached = check_vision_cache(photo_id=7, question="What's the condition?")
if cached:
    # Use cached answer
else:
    # Call vision AI, save new entry
```

### Storage
```sql
-- Photo 7 with 3 different questions:
id | photo_id | question              | question_hash | analysis           | timestamp
1  | 7        | general               | abc123...     | "Buildings show..." | 2025-01-15 10:00
2  | 7        | building condition?   | def456...     | "Moderate decay..." | 2025-01-15 10:05
3  | 7        | any people visible?   | ghi789...     | "No people seen..." | 2025-01-15 10:10
```

All 3 analyses are preserved!

## Query Examples

### Get all analyses for a photo:
```sql
SELECT question, analysis, timestamp
FROM vision_cache
WHERE photo_id = 7
ORDER BY timestamp DESC
```

### Get specific analysis:
```sql
SELECT analysis
FROM vision_cache
WHERE photo_id = 7 AND question LIKE '%condition%'
```

### Find all photos analyzed for people:
```sql
SELECT DISTINCT photo_id
FROM vision_cache
WHERE question LIKE '%people%' OR analysis LIKE '%people%'
```

### Join with photo metadata:
```sql
SELECT p.filename, p.caption_year, v.question, v.analysis
FROM photos p
JOIN vision_cache v ON p.id = v.photo_id
WHERE p.caption_location = 'Broadway'
ORDER BY p.caption_year, v.timestamp
```

## Benefits

### ✅ Research Continuity
- Build knowledge over time
- Never lose previous insights
- Track evolution of understanding

### ✅ Multi-Perspective Analysis
- Ask multiple questions about same photo
- Compare different aspects (architecture vs. people vs. condition)
- Comprehensive documentation

### ✅ Efficient Caching
- Same question = instant cached response
- Different question = new analysis
- Best of both worlds

### ✅ Full History
- See all questions ever asked about a photo
- Track research progression
- Audit trail for collaboration

## Migration

The migration script (`fix_vision_cache_schema.py`) automatically:
1. Backs up existing vision_cache data
2. Drops old table
3. Creates new schema
4. Restores data with question hashes

Run it with:
```bash
python3 fix_vision_cache_schema.py
```

## Auto-Commit Behavior

Each unique analysis still auto-commits to GitHub:
```
Auto-cache vision analysis: photo 7
Auto-cache vision analysis: photo 7
Auto-cache vision analysis: photo 7
```

These are now **3 different analyses** for photo 7, not replacements!

## Future Enhancements

### Planned:
- [ ] View all cached analyses for a photo in UI
- [ ] "Re-analyze" button to refresh stale cache entries
- [ ] Export all Q&As for a photo as research notes
- [ ] Smart suggestions: "You haven't asked about X yet"

### Ideas:
- Versioned analyses (track how answers change over time)
- Confidence scores for cached answers
- Related questions ("Others also asked...")
- Analysis comparison ("How did answer change?")

## Testing

After deploying the fix:

1. **Analyze photo 7 with different questions:**
   ```
   "What do you see?"
   "What's the building condition?"
   "Any signs or text visible?"
   ```

2. **Check database:**
   ```sql
   SELECT * FROM vision_cache WHERE photo_id = 7;
   ```
   Should see 3 rows!

3. **Re-ask same question:**
   ```
   "What do you see?"
   ```
   Should get instant cached response.

4. **View in UI:**
   All previous analyses should be accessible.

## Result

Your research is now **cumulative**, not **destructive**. Every insight is preserved!
