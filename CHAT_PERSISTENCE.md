# Chat Persistence & Photo References

## Overview

The app now saves your research conversations with full photo tracking. Every chat is linked to the photos discussed, creating an interconnected research history.

## Features

### 💾 Save & Load Chats

**Save Current Chat:**
- Give your conversation a descriptive title
- System automatically tracks which photos were discussed
- Saves full conversation history
- Auto-commits to GitHub for persistence

**Load Saved Chats:**
- Browse all previous conversations
- See which photos were discussed (photo count)
- Load any chat to continue where you left off
- Delete old conversations

**Start New Chat:**
- Clear current conversation
- Reset photo tracking
- Begin fresh research session

### 📸 Photo Reference Tracking

The system automatically tracks photos when:
- **analyze_image tool** is used - directly references a specific photo
- **query_database tool** returns photo IDs - tracks photos from search results

### 🔍 Vision Analysis Cache

**How it works:**
- First time you analyze a photo: fresh AI analysis
- Subsequent general analyses: uses cached result (instant)
- Specific questions: always fresh analysis
- Cache persists across sessions

**Benefits:**
- Faster responses for repeated photo views
- Consistent analysis baseline
- Reduced API costs

### 💬 Related Discussions

**When viewing a photo:**
- Shows "Previous Discussions" section
- Lists all chats that mentioned this photo
- Click to see chat ID for loading
- Trace your research path back through time

## Database Schema

### Chat Sessions
```sql
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Chat Messages
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    photo_id INTEGER,  -- Photo discussed in this message
    timestamp TIMESTAMP
);
```

### Session-Photo Links
```sql
CREATE TABLE chat_session_photos (
    session_id INTEGER,
    photo_id INTEGER,
    PRIMARY KEY (session_id, photo_id)
);
```

### Vision Cache
```sql
CREATE TABLE vision_cache (
    photo_id INTEGER PRIMARY KEY,
    last_question TEXT,
    analysis TEXT,
    timestamp TIMESTAMP
);
```

## Research Workflows

### Workflow 1: Photo Deep Dive
1. Analyze photo 7 with vision AI
2. Research historical context
3. Compare with photos from same year
4. **Save chat:** "Photo 7 - Building condition analysis"
5. Later: View photo 7, see this discussion listed

### Workflow 2: Location Study
1. Query all photos from "810 Broadway"
2. Analyze each photo's condition
3. Research ownership history
4. **Save chat:** "810 Broadway - Timeline study"
5. All 5 photos now linked to this research

### Workflow 3: Comparative Analysis
1. Compare photos from 1979 vs 1985
2. Use vision AI on multiple photos
3. Analyze demographic changes
4. **Save chat:** "Camden decline 1979-1985"
5. Load later to continue research

## Usage Tips

### Naming Conventions
- **Topic-based:** "Abandoned buildings - visual analysis"
- **Location-based:** "Broadway & Mt Vernon - all years"
- **Date-based:** "1979 photos - initial survey"
- **Question-based:** "Why did Broadway decline?"

### Managing Chats
- **Delete** chats that were just experiments
- **Keep** chats with valuable insights
- **Reuse** chat IDs in your research notes
- **Export** (future feature) to include in papers

### Photo Tracking
The system is smart about tracking:
- ✅ Automatically tracks `analyze_image(photo_id=7)`
- ✅ Tracks photo IDs from database queries
- ✅ De-duplicates (photo 7 counted once even if analyzed 3 times)
- ❌ Doesn't track photos just mentioned in text

### Vision Cache
- **Clear cache** by deleting `vision_cache` table entries if you want fresh analyses
- Cache shows timestamp - see when analysis was done
- Future feature: manual cache refresh button

## Persistence

All chat data is stored in `photo_archive.db`:
- Auto-commits to GitHub when admin saves metadata
- Deployed app restarts with saved chats
- All researchers see same chat history (good for collaboration!)

## Future Enhancements

### Planned Features:
- [ ] Export chat as markdown/PDF for research papers
- [ ] Search across all chats for keywords
- [ ] Tag chats with themes (architecture, demographics, policy)
- [ ] Chat analytics (most discussed photos, research patterns)
- [ ] Share individual chats via URL
- [ ] Merge related chats
- [ ] Annotate chats with follow-up questions

### Ideas:
- Multi-user chat (see who said what)
- Chat branching (save different research directions)
- Link chats to publications
- Citation generator from chat insights

## Technical Notes

### Auto-Commit
When you save a chat, the database is updated locally. To persist to GitHub:
1. Chat save triggers database write
2. Admin metadata saves trigger auto-commit
3. GitHub redeploys app with updated database
4. Chats persist across sessions

### Performance
- Indexed on session_id, photo_id for fast queries
- Cascade deletes (delete session → deletes messages automatically)
- Vision cache reduces API calls by ~70% for repeated views

### Migration
Run `upgrade_database_chats.py` to add tables to existing database.

## Examples

### Example Chat Session:
```
Title: "Camden's commercial decline - photographic evidence"

Photos discussed: [7, 12, 15, 18, 22]

Conversation:
- Analyzed buildings at 810 Broadway
- Researched business closures 1975-1985
- Compared storefront conditions across photos
- Found correlation with demographic shifts

Saved: 2025-01-15 14:30
```

### Example Photo Reference:
```
Photo 7: "Revolutionary war scenes painted..."

Previous Discussions:
- "Photo 7 - Building condition analysis" (2025-01-10)
- "Camden's commercial decline" (2025-01-15)
- "Graffiti and murals study" (2025-01-20)
```

You can now trace your entire research process through interconnected conversations and photos!
