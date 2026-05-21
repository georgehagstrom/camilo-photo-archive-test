# Context-Aware Chat with Reorganized UI

## Changes Made

### 1. UI Reorganization

**New Section Order:**
1. **Photo Display & Map** (top)
2. **📸 Selected Location Photos Grid**
3. **🔍 Photo Details**
4. **📍 Sidebar** (locations list, statistics)
5. **💬 Chat Interface** ← Moved here!
6. **💾 Save/Load Chats**
7. **💡 Example Questions**
8. **🆕 Start New Chat**
9. **🔧 Admin Panel** (bottom)

**What Changed:**
- Chat interface now appears **immediately after the photo display**
- More intuitive workflow: View photo → Ask questions about it
- Save/load management and admin features moved to bottom
- Tool function definitions moved after UI sections

### 2. Context-Aware Chat

The chat now **automatically knows** which photo you're currently viewing!

**How it works:**
When you click on a photo marker or select a photo from the grid, the chat system prompt is updated to include:

```
CURRENTLY VIEWING:
- Photo ID: 7
- Filename: 7.jpeg
- Year: 1979
- Location: Broadway at Mt. Vernon
- City: Camden
- Caption: "We built the USA," Bicentennial celebration...

When the user refers to "this photo", "the current image", "this image", or "the photo",
they mean Photo ID 7.
```

**User Experience:**

*Before (required explicit reference):*
```
You: "Analyze photo 7"
Chat: [Uses analyze_image tool with photo_id=7]
```

*After (natural language):*
```
[User clicks on photo 7]
You: "What do you see in this image?"
Chat: [Automatically knows you mean photo 7]

You: "Analyze the current photo"
Chat: [Uses analyze_image tool with photo_id=7]

You: "Tell me about this building"
Chat: [Understands context, analyzes photo 7]
```

## Example Workflows

### Workflow 1: Photo Exploration
1. **Click** on map marker showing "810 Broadway"
2. **View** 3 photos at that location
3. **Click** on one photo to see details
4. **Scroll down** to chat (right below!)
5. **Type:** "What condition is this building in?"
6. **Chat knows** you're asking about the currently selected photo

### Workflow 2: Comparative Analysis
1. **Select** photo from 1979
2. **Ask:** "Describe this image"
3. **Click** photo from 1985 at same location
4. **Ask:** "Compare this to the previous image"
5. Chat uses vision AI on both photos with full context

### Workflow 3: Location Research
1. **Click** location with multiple photos
2. **Scroll through** photos in grid
3. **Click** one photo
4. **Ask:** "What's the historical context for this location?"
5. Chat knows which photo/location you're researching
6. **Save chat** for later reference

## Technical Implementation

### System Prompt Enhancement

The `system_context` is dynamically built to include:
```python
current_context = ""
if st.session_state.selected_photo_id:
    current_photo = next((p for p in photos if p['id'] == st.session_state.selected_photo_id), None)
    if current_photo:
        current_context = f"""
CURRENTLY VIEWING:
- Photo ID: {current_photo['id']}
- Filename: {current_photo['filename']}
- Year: {current_photo['caption_year']}
- Location: {current_photo['caption_location']}
- City: {current_photo['caption_city']}
- Caption: {current_photo['original_caption']}
"""
```

This context is included in every chat message, so Claude always knows what photo is being viewed.

### Reorganization Details

**Original Structure:**
```
1. Photo display (lines 1-437)
2. Sidebar (lines 439-462)
3. Tool functions (lines 464-753)
4. Chat interface (lines 754-1030)
5. Admin (lines 1031+)
```

**New Structure:**
```
1. Photo display (lines 1-437)
2. Sidebar (lines 439-462)
3. Chat interface (lines 463-1046)
4. Tool functions (lines 1047-1336)
5. Admin (lines 1337+)
```

Python's function parsing allows tool functions to be defined after they're referenced in the chat code, as long as they're defined before actual execution.

## Benefits

### User Experience
- **More intuitive flow**: View → Ask → Research
- **Natural language**: No need to specify photo IDs
- **Faster workflow**: Chat is right where you need it
- **Context preserved**: Chat knows your research focus

### Research Efficiency
- **Seamless exploration**: Click, view, ask - all in one flow
- **Contextual questions**: "Tell me more about this" just works
- **Photo-to-chat integration**: Visual and textual research unified
- **Chat persistence**: Full context saved for later

### Code Quality
- **Logical organization**: UI flow matches user workflow
- **Maintainability**: Related functionality grouped together
- **Flexibility**: Easy to add more context-aware features

## Future Enhancements

### Potential Improvements:
- [ ] Show currently viewed photo thumbnail in chat
- [ ] Quick action buttons: "Analyze this photo" button
- [ ] Location context: Chat knows about all photos at current location
- [ ] Temporal context: Chat knows photo's position in timeline
- [ ] Visual indicator: Highlight which photo chat is focused on
- [ ] Multi-photo context: "Compare all photos at this location"
- [ ] Smart suggestions: "Ask about this photo's architecture"

### Ideas:
- Auto-analyze on photo select (optional)
- Photo comparison mode in chat
- Timeline-aware questions ("What changed since last photo?")
- Location-aware research ("What else is nearby?")

## Testing Tips

### Verify Context Awareness:
1. Click different photos
2. Ask "What do you see?" for each
3. Confirm chat analyzes correct photo
4. Try phrases like "this image", "current photo", "the photo"

### Verify UI Order:
1. Load app
2. Confirm chat appears after photo details
3. Confirm save/load appears after chat
4. Confirm admin is at bottom

### Verify Integration:
1. Click photo
2. Scroll to chat (should be close!)
3. Ask contextual question
4. Save chat
5. Load chat - context should persist

## Deployment

Push to GitHub to deploy:
```bash
git push
```

Streamlit Cloud will redeploy with:
- Chat moved to optimal position
- Context awareness fully functional
- All photo references tracked correctly

The reorganization and context awareness work together to create a seamless research experience!
