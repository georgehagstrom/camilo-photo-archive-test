#!/usr/bin/env python3
"""
Visual Photo Archive App - Click to view, fully interactive
"""

import streamlit as st
import sqlite3
import folium
from streamlit_folium import st_folium
from pathlib import Path
from collections import defaultdict
import base64
import os
import anthropic
import subprocess
import json
import httpx
import pandas as pd
import time
from datetime import datetime
from github import Github, GithubException

# ===== CHAT SESSION MANAGEMENT =====

def get_all_chat_sessions():
    """Get all saved chat sessions"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cs.id, cs.title, cs.created_at, cs.updated_at,
               COUNT(DISTINCT csp.photo_id) as photo_count
        FROM chat_sessions cs
        LEFT JOIN chat_session_photos csp ON cs.id = csp.session_id
        GROUP BY cs.id
        ORDER BY cs.updated_at DESC
    """)
    sessions = cursor.fetchall()
    conn.close()
    return sessions

def save_chat_session(title, messages, photo_ids):
    """Save current chat session to database"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    now = datetime.now()

    # Create session
    cursor.execute("""
        INSERT INTO chat_sessions (title, created_at, updated_at)
        VALUES (?, ?, ?)
    """, (title, now, now))

    session_id = cursor.lastrowid

    # Save messages
    for msg in messages:
        # Try to extract photo_id from message if it mentions analyze_image
        photo_id = None
        if msg['role'] == 'assistant' and 'photo' in msg.get('content', '').lower():
            # This is a simple heuristic - will be improved by tracking during tool use
            pass

        cursor.execute("""
            INSERT INTO chat_messages (session_id, role, content, photo_id, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, msg['role'], msg['content'], photo_id, now))

    # Link photos to session
    for photo_id in set(photo_ids):
        if photo_id:
            cursor.execute("""
                INSERT OR IGNORE INTO chat_session_photos (session_id, photo_id)
                VALUES (?, ?)
            """, (session_id, photo_id))

    conn.commit()
    conn.close()

    return session_id

def load_chat_session(session_id):
    """Load a saved chat session"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    # Get messages
    cursor.execute("""
        SELECT role, content, photo_id, timestamp
        FROM chat_messages
        WHERE session_id = ?
        ORDER BY timestamp ASC
    """, (session_id,))

    messages = []
    photo_ids = []
    for row in cursor.fetchall():
        messages.append({
            'role': row[0],
            'content': row[1]
        })
        if row[2]:
            photo_ids.append(row[2])

    # Get session info
    cursor.execute("""
        SELECT title, created_at
        FROM chat_sessions
        WHERE id = ?
    """, (session_id,))

    session_info = cursor.fetchone()
    conn.close()

    return {
        'messages': messages,
        'photo_ids': photo_ids,
        'title': session_info[0] if session_info else "Untitled",
        'created_at': session_info[1] if session_info else None
    }

def delete_chat_session(session_id):
    """Delete a chat session"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def get_chats_for_photo(photo_id):
    """Get all chat sessions that discussed a specific photo"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cs.id, cs.title, cs.updated_at
        FROM chat_sessions cs
        JOIN chat_session_photos csp ON cs.id = csp.session_id
        WHERE csp.photo_id = ?
        ORDER BY cs.updated_at DESC
    """, (photo_id,))
    chats = cursor.fetchall()
    conn.close()
    return chats

def check_vision_cache(photo_id):
    """Check if we have cached vision analysis for a photo"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT analysis, timestamp
        FROM vision_cache
        WHERE photo_id = ?
    """, (photo_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def save_vision_cache(photo_id, question, analysis):
    """Save vision analysis to cache"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO vision_cache (photo_id, last_question, analysis, timestamp)
        VALUES (?, ?, ?, ?)
    """, (photo_id, question, analysis, datetime.now()))
    conn.commit()
    conn.close()

# ===== END CHAT SESSION MANAGEMENT =====

st.set_page_config(
    page_title="Camilo Vergara Photo Archive",
    page_icon="📷",
    layout="wide"
)

# Authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Camilo Vergara Photo Archive")
    st.markdown("### Please log in to access the archive")

    password = st.text_input("Password", type="password", key="login_password")

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("Login", type="primary"):
            # Check against environment variable (set in Streamlit Cloud secrets)
            correct_password = os.environ.get('APP_PASSWORD', 'changeme')
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password")

    st.stop()  # Stop execution until authenticated

# Custom CSS for clickable thumbnails
st.markdown("""
<style>
    .photo-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 15px;
        margin: 20px 0;
    }
    .photo-card {
        border: 2px solid #ddd;
        border-radius: 8px;
        padding: 10px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .photo-card:hover {
        border-color: #ff4b4b;
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .photo-card.selected {
        border-color: #ff4b4b;
        background-color: #ffe6e6;
    }
    .photo-card img {
        width: 100%;
        height: 150px;
        object-fit: cover;
        border-radius: 4px;
    }
    .photo-card .caption {
        font-size: 12px;
        margin-top: 5px;
        font-weight: bold;
    }
    .photo-card .year {
        font-size: 11px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_photos():
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.id, p.filename, p.file_path, p.original_caption,
               p.latitude, p.longitude, p.caption_year, p.caption_city,
               p.caption_location, p.notes
        FROM photos p
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        ORDER BY p.caption_year, p.filename
    """)

    columns = ['id', 'filename', 'file_path', 'original_caption', 'latitude',
               'longitude', 'caption_year', 'caption_city', 'caption_location', 'notes']

    photos = []
    for row in cursor.fetchall():
        photo_dict = dict(zip(columns, row))
        # Fix file paths - convert absolute paths to relative
        # Extract just the filename and construct relative path
        filename = Path(photo_dict['file_path']).name
        photo_dict['file_path'] = f"Photos/{filename}"
        photos.append(photo_dict)

    conn.close()
    return photos

def get_image_base64(image_path):
    """Convert image to base64 for embedding in HTML"""
    try:
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

# Initialize session state
if 'selected_photo_id' not in st.session_state:
    st.session_state.selected_photo_id = None
if 'selected_location' not in st.session_state:
    st.session_state.selected_location = None

# Load photos
photos = load_photos()

# Group by location
location_groups = defaultdict(list)
for photo in photos:
    loc_key = f"{photo['latitude']:.6f},{photo['longitude']:.6f}"
    location_groups[loc_key].append(photo)

# Header
st.title("📷 Camilo Vergara Photo Archive")
st.markdown(f"**{len(photos)} photos** at **{len(location_groups)} locations** • Click map markers to view photos")

# Map
st.subheader("🗺️ Interactive Map")

center_lat = sum(p['latitude'] for p in photos) / len(photos)
center_lon = sum(p['longitude'] for p in photos) / len(photos)

m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=15,
    tiles='OpenStreetMap'
)

# Add markers
for loc_key, group in location_groups.items():
    photo = group[0]

    # Check if this location or any photo in it is selected
    selected_here = (st.session_state.selected_location == loc_key or
                    any(p['id'] == st.session_state.selected_photo_id for p in group))
    color = 'red' if selected_here else 'blue'

    # Popup with photo list
    popup_text = f"<b>{len(group)} photo(s) at this location</b><br><br>"
    for p in group:
        popup_text += f"📷 {p['filename']} ({p['caption_year']})<br>"
    popup_text += "<br><i>Click to view photos below ⬇️</i>"

    folium.Marker(
        location=[photo['latitude'], photo['longitude']],
        popup=folium.Popup(popup_text, max_width=300),
        tooltip=f"📍 {len(group)} photos here",
        icon=folium.Icon(color=color, icon='camera', prefix='fa')
    ).add_to(m)

# Display map and capture clicks
map_result = st_folium(m, width=None, height=500, returned_objects=["last_object_clicked"])

# Check if marker was clicked
if map_result and map_result.get("last_object_clicked"):
    clicked_lat = map_result["last_object_clicked"]["lat"]
    clicked_lon = map_result["last_object_clicked"]["lng"]
    clicked_loc = f"{clicked_lat:.6f},{clicked_lon:.6f}"

    if clicked_loc != st.session_state.selected_location:
        st.session_state.selected_location = clicked_loc
        # Select first photo at this location
        if clicked_loc in location_groups:
            st.session_state.selected_photo_id = location_groups[clicked_loc][0]['id']
        st.rerun()

# Show photos from selected location
if st.session_state.selected_location and st.session_state.selected_location in location_groups:
    st.markdown("---")
    selected_group = location_groups[st.session_state.selected_location]

    st.subheader(f"📸 Photos at this location ({len(selected_group)} photos)")

    # Create clickable photo grid
    cols = st.columns(min(len(selected_group), 4))

    for idx, photo in enumerate(selected_group):
        with cols[idx % len(cols)]:
            # Check if this photo is selected
            is_selected = photo['id'] == st.session_state.selected_photo_id

            # Create clickable photo container
            if Path(photo['file_path']).exists():
                st.image(photo['file_path'], use_container_width=True)
            else:
                st.error("Image not found")

            st.markdown(f"**{photo['filename']}** ({photo['caption_year']})")

            # Click button to select
            if st.button(f"View Details", key=f"btn_{photo['id']}",
                        type="primary" if is_selected else "secondary"):
                st.session_state.selected_photo_id = photo['id']
                st.rerun()

    st.markdown("---")

# Display selected photo details
selected_photo = None
for p in photos:
    if p['id'] == st.session_state.selected_photo_id:
        selected_photo = p
        break

if selected_photo:
    st.subheader("🔍 Photo Details")

    col1, col2 = st.columns([2, 1])

    with col1:
        if Path(selected_photo['file_path']).exists():
            st.image(selected_photo['file_path'], use_container_width=True)
        else:
            st.error(f"Image not found: {selected_photo['file_path']}")

    with col2:
        st.markdown(f"### {selected_photo['filename']}")
        st.markdown(f"**Year:** {selected_photo['caption_year']}")
        st.markdown(f"**City:** {selected_photo['caption_city']}")
        st.markdown(f"**Location:** {selected_photo['caption_location']}")

        st.markdown("---")

        st.markdown("**Caption:**")
        st.markdown(f"*{selected_photo['original_caption']}*")

        # Display research notes if they exist
        if selected_photo.get('notes'):
            st.markdown("---")
            st.markdown("**📝 Research Notes:**")
            st.markdown(selected_photo['notes'])

        st.markdown("---")

        st.markdown(f"**GPS:** {selected_photo['latitude']:.6f}, {selected_photo['longitude']:.6f}")

        maps_url = f"https://www.google.com/maps?q={selected_photo['latitude']},{selected_photo['longitude']}"
        st.markdown(f"[🗺️ View on Google Maps]({maps_url})")

        # Google Street View
        street_view_url = f"https://www.google.com/maps/@{selected_photo['latitude']},{selected_photo['longitude']},3a,75y,90t/data=!3m4!1e1!3m2!1s0!2e0"
        st.markdown(f"[📍 Google Street View]({street_view_url})")

        # Show related chat sessions
        related_chats = get_chats_for_photo(selected_photo['id'])
        if related_chats:
            st.markdown("---")
            st.markdown("**💬 Previous Discussions:**")
            for chat_id, chat_title, updated_at in related_chats:
                st.markdown(f"- [{chat_title}](#) (Last updated: {updated_at[:16]})")
                st.caption(f"Chat ID: {chat_id}")

else:
    # No photo selected yet
    st.info("👆 Click a marker on the map to view photos at that location")

# Sidebar with location list
with st.sidebar:
    st.header("📍 All Locations")

    for loc_key, group in sorted(location_groups.items()):
        is_selected = loc_key == st.session_state.selected_location

        if st.button(
            f"📌 {len(group)} photos at {group[0]['caption_location'] or 'this location'}",
            key=f"loc_{loc_key}",
            type="primary" if is_selected else "secondary"
        ):
            st.session_state.selected_location = loc_key
            st.session_state.selected_photo_id = group[0]['id']
            st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Statistics")
    st.markdown(f"**Total photos:** {len(photos)}")
    st.markdown(f"**Locations:** {len(location_groups)}")

    years = [p['caption_year'] for p in photos if p['caption_year']]
    if years:
        st.markdown(f"**Years:** {min(years)} - {max(years)}")

# Tool implementations for MCP
def execute_sql_query(query):
    """Execute a read-only SQL query on the photo database"""
    try:
        # Only allow SELECT queries for safety
        if not query.strip().upper().startswith('SELECT'):
            return {"error": "Only SELECT queries are allowed for safety"}

        conn = sqlite3.connect('photo_archive.db')
        df = pd.read_sql_query(query, conn)
        conn.close()

        return {"success": True, "data": df.to_dict('records'), "row_count": len(df)}
    except Exception as e:
        return {"error": str(e)}

def fetch_web_content(url, max_chars=10000):
    """Fetch content from a URL"""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=15)
        response.raise_for_status()

        # Get HTML content
        html = response.text

        # Try to extract main text content (strip HTML tags)
        from html.parser import HTMLParser

        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.skip = False

            def handle_starttag(self, tag, attrs):
                # Skip script, style, nav, footer
                if tag.lower() in ['script', 'style', 'nav', 'footer', 'header']:
                    self.skip = True

            def handle_endtag(self, tag):
                if tag.lower() in ['script', 'style', 'nav', 'footer', 'header']:
                    self.skip = False

            def handle_data(self, data):
                if not self.skip:
                    text = data.strip()
                    if text:
                        self.text.append(text)

        parser = TextExtractor()
        parser.feed(html)
        extracted_text = ' '.join(parser.text)

        # Return extracted text, limited to max_chars
        content = extracted_text[:max_chars] if len(extracted_text) > max_chars else extracted_text

        return {
            "success": True,
            "url": url,
            "content": content,
            "content_length": len(extracted_text),
            "truncated": len(extracted_text) > max_chars,
            "status": response.status_code
        }
    except Exception as e:
        return {"error": str(e)}

def execute_python_code(code):
    """Execute Python code in a restricted environment"""
    try:
        # Create a restricted namespace with pandas, no file I/O
        namespace = {
            'pd': pd,
            'json': json,
            '__builtins__': {
                'len': len,
                'str': str,
                'int': int,
                'float': float,
                'list': list,
                'dict': dict,
                'sum': sum,
                'min': min,
                'max': max,
                'sorted': sorted,
                'range': range,
            }
        }

        # Execute code and capture output
        exec(code, namespace)

        # Get any variables created (exclude builtins and imports)
        results = {k: v for k, v in namespace.items()
                  if not k.startswith('_') and k not in ['pd', 'json']}

        return {"success": True, "results": str(results)}
    except Exception as e:
        return {"error": str(e)}

def analyze_image_vision(photo_id, question=None):
    """Use Claude Vision to analyze a photo from the archive"""
    try:
        # Get photo info from database
        conn = sqlite3.connect('photo_archive.db')
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filename, file_path, original_caption, caption_year, caption_location
            FROM photos WHERE id = ?
        """, (photo_id,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return {"error": f"Photo ID {photo_id} not found"}

        filename, file_path, caption, year, location = result

        # Convert absolute path to relative
        relative_path = f"Photos/{Path(file_path).name}"

        # Check if file exists
        if not Path(relative_path).exists():
            return {"error": f"Image file not found: {relative_path}"}

        # Read and encode image
        with open(relative_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determine image type
        ext = Path(relative_path).suffix.lower()
        media_type = "image/jpeg" if ext in ['.jpg', '.jpeg'] else "image/png"

        # Get API key
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return {"error": "No API key available"}

        # Build prompt
        if question:
            prompt = f"This photo is from Camilo Vergara's archive: {filename} ({year}), {location}. Caption: {caption}\n\nQuestion: {question}"
        else:
            prompt = f"Analyze this photo from Camilo Vergara's documentary archive: {filename} ({year}), {location}. Caption: {caption}\n\nDescribe what you see in detail, including: buildings, architecture, signs, text visible, condition of structures, people, vehicles, and any evidence of urban decline or change."

        # Call Claude Vision
        client = anthropic.Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }],
        )

        analysis = response.content[0].text

        return {
            "success": True,
            "photo_id": photo_id,
            "filename": filename,
            "analysis": analysis
        }

    except Exception as e:
        return {"error": str(e)}

# MCP Tool Definitions
TOOLS = [
    {
        "name": "query_database",
        "description": "Execute SQL queries on the photo archive database. The database has a 'photos' table with columns: id, filename, file_path, original_caption, latitude, longitude, caption_year, caption_city, caption_location, caption_intersection, caption_street_address. Use this to find photos matching specific criteria.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL SELECT query to execute. Only SELECT statements are allowed."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "analyze_image",
        "description": "Use Claude's vision capabilities to analyze a photo from the archive. Can describe visual content, read text/signs, assess building conditions, identify architectural features, and answer specific questions about what's visible in the image. Use this when you need to 'see' what's actually in a photo beyond the metadata.",
        "input_schema": {
            "type": "object",
            "properties": {
                "photo_id": {
                    "type": "integer",
                    "description": "The ID of the photo to analyze (from the photos table)"
                },
                "question": {
                    "type": "string",
                    "description": "Optional: A specific question to answer about the image. If omitted, provides a general detailed description."
                }
            },
            "required": ["photo_id"]
        }
    },
    {
        "name": "fetch_url",
        "description": "Fetch content from a web URL. Useful for researching historical context, locations, or other information related to the photos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "run_python",
        "description": "Execute Python code for data analysis. Has access to pandas (as pd) and json modules. No file I/O allowed. Good for calculations, data transformations, and analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute"
                }
            },
            "required": ["code"]
        }
    }
]

def process_tool_call(tool_name, tool_input):
    """Process a tool call and return results"""
    if tool_name == "query_database":
        result = execute_sql_query(tool_input["query"])
        # Track photo IDs from query results
        if isinstance(result, dict) and 'rows' in result:
            for row in result['rows']:
                if isinstance(row, (list, tuple)) and len(row) > 0:
                    # Check if first column looks like a photo ID
                    if isinstance(row[0], int) and row[0] > 0 and row[0] < 10000:
                        if row[0] not in st.session_state.tracked_photo_ids:
                            st.session_state.tracked_photo_ids.append(row[0])
        return result

    elif tool_name == "analyze_image":
        photo_id = tool_input["photo_id"]
        question = tool_input.get("question")

        # Track this photo
        if photo_id not in st.session_state.tracked_photo_ids:
            st.session_state.tracked_photo_ids.append(photo_id)

        # Check cache first
        cached = check_vision_cache(photo_id)
        if cached and not question:
            # Use cached analysis if no specific question
            return {"cached": True, "analysis": cached[0], "timestamp": cached[1]}

        # Get fresh analysis
        result = analyze_image_vision(photo_id, question)

        # Cache the result
        if isinstance(result, dict) and 'analysis' in result:
            save_vision_cache(photo_id, question or "general", result['analysis'])

        return result

    elif tool_name == "fetch_url":
        return fetch_web_content(tool_input["url"])
    elif tool_name == "run_python":
        return execute_python_code(tool_input["code"])
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# Chat Interface
st.markdown("---")
st.subheader("💬 Chat with the Archive")

# Check for API key
api_key = os.environ.get('ANTHROPIC_API_KEY')

if not api_key:
    st.warning("""
    ⚠️ **Chat requires an Anthropic API key**

    To enable chat:
    1. Get your API key from: https://console.anthropic.com/settings/keys
    2. Run: `./update_api_key.sh` (and paste your key when prompted)
    3. Restart the app

    Or set it directly:
    ```bash
    export ANTHROPIC_API_KEY='your-key-here'
    ```
    """)
else:
    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Initialize chat session tracking
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "tracked_photo_ids" not in st.session_state:
        st.session_state.tracked_photo_ids = []
    if "session_title" not in st.session_state:
        st.session_state.session_title = None

    # Display chat messages
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about the archive..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build system context
        system_context = f"""You are analyzing Camilo Vergara's documentary photography archive of urban deindustrialization.

Archive contains {len(photos)} photos from {min(years)} to {max(years)} across {len(location_groups)} locations in Camden, NJ.

You have access to tools:
- query_database: Run SQL queries on the photo database to find photos
- analyze_image: Use vision AI to actually SEE and analyze the content of photos (read signs, describe buildings, assess conditions, identify visual details)
- fetch_url: Fetch web content for research (extracts text from HTML, handles large pages)
- run_python: Execute Python code for analysis

RESEARCH APPROACH:
- Be thorough and persistent - use as many tool calls as needed to answer completely
- Try multiple search strategies if initial approaches don't work
- When you find good sources, extract all relevant information
- If the user provides a URL, fully parse and extract information from it
- Continue researching until you have a complete answer

The photos table has: id, filename, file_path, original_caption, latitude, longitude, caption_year, caption_city, caption_location, caption_intersection, caption_street_address."""

        # Get AI response with tool use
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            current_tool_status = st.empty()  # Single line for current tool

            try:
                client = anthropic.Anthropic(api_key=api_key)

                # Build full conversation history from session state
                messages = []
                for msg in st.session_state.chat_messages:
                    # Only include user and assistant text messages (not tool results)
                    if isinstance(msg.get("content"), str):
                        messages.append({"role": msg["role"], "content": msg["content"]})

                # Tool use loop (generous limit like Opus - 25 iterations)
                for iteration in range(25):
                    # Clean spinner without step numbers
                    with st.spinner("Thinking..."):
                        response = client.messages.create(
                            model="claude-sonnet-4-5-20250929",
                            max_tokens=8192,  # Match Opus's generous token limit
                            system=system_context,
                            tools=TOOLS,
                            messages=messages
                        )

                    # Check if Claude wants to use tools
                    if response.stop_reason == "tool_use":
                        # Process tool calls
                        tool_results = []

                        # Show any thinking text before tool use (like Opus does)
                        thinking_text = ""
                        for content_block in response.content:
                            if hasattr(content_block, "text") and content_block.text:
                                thinking_text += content_block.text

                        if thinking_text:
                            message_placeholder.markdown(f"*{thinking_text}*")

                        # Process tools quietly - just show current tool
                        for content_block in response.content:
                            if content_block.type == "tool_use":
                                tool_name = content_block.name
                                tool_input = content_block.input

                                # Show brief status - just the tool name, no clutter
                                current_tool_status.caption(f"🔧 Using {tool_name}...")

                                # Execute tool (silently)
                                tool_result = process_tool_call(tool_name, tool_input)

                                # Add tool result to conversation
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": json.dumps(tool_result)
                                })

                        # Clear tool status
                        current_tool_status.empty()

                        # Add assistant's response and tool results to messages
                        messages.append({"role": "assistant", "content": response.content})
                        messages.append({"role": "user", "content": tool_results})

                    else:
                        # No more tools to use, get final text response
                        final_text = ""
                        for content_block in response.content:
                            if hasattr(content_block, "text"):
                                final_text += content_block.text

                        if final_text:
                            message_placeholder.markdown(final_text)
                            # Save to chat history
                            st.session_state.chat_messages.append({"role": "assistant", "content": final_text})
                        else:
                            message_placeholder.info("Response completed (see tool results above)")
                            st.session_state.chat_messages.append({"role": "assistant", "content": "(Tool execution completed)"})
                        break
                else:
                    # Hit iteration limit - try one more time without tools (like Opus does gracefully)
                    current_tool_status.empty()

                    # Ask Claude to synthesize without more tools
                    final_response = client.messages.create(
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=4096,
                        system=system_context,
                        messages=messages + [{
                            "role": "user",
                            "content": "Please provide a comprehensive final answer based on all the information you've gathered."
                        }]
                    )

                    final_text = ""
                    for content_block in final_response.content:
                        if hasattr(content_block, "text"):
                            final_text += content_block.text

                    if final_text:
                        message_placeholder.markdown(final_text)
                        st.session_state.chat_messages.append({"role": "assistant", "content": final_text})
                    else:
                        message_placeholder.error("Could not generate a final response.")
                        st.session_state.chat_messages.append({"role": "assistant", "content": "(Error: No final response)"})

            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.error(error_msg)

                # If model not found, suggest update
                if "404" in str(e) or "not_found_error" in str(e):
                    st.info("""
                    This API key doesn't have access to the required model.

                    Please:
                    1. Get a new key from: https://console.anthropic.com/settings/keys
                    2. Run: `./update_api_key.sh`
                    3. Restart the app
                    """)

    # Example questions
    with st.expander("💡 Example questions (with vision AI!)"):
        example_questions = [
            "Analyze photo 7 - what do you see in the image?",
            "What text is visible on the buildings in the photos from 810 Broadway?",
            "Compare the visual condition of buildings across different years",
            "Search the web for historical context about Camden NJ in 1979",
            "Find all photos from the 1970s and describe what they show",
            "What architectural features are visible in photo 5?",
            "Analyze the graffiti and murals visible in the archive photos"
        ]

        for q in example_questions:
            if st.button(q, key=f"example_{q[:20]}"):
                st.session_state.chat_messages.append({"role": "user", "content": q})
                st.rerun()

    # Save/Load Chat Session
    st.markdown("---")
    st.markdown("### 💾 Save & Load Chats")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Save Current Chat**")
        if len(st.session_state.chat_messages) > 0:
            save_title = st.text_input(
                "Chat Title:",
                value=st.session_state.session_title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                key="save_title_input"
            )

            photo_count = len(st.session_state.tracked_photo_ids)
            st.caption(f"📸 {photo_count} photos discussed")

            if st.button("💾 Save This Chat", type="primary"):
                session_id = save_chat_session(
                    save_title,
                    st.session_state.chat_messages,
                    st.session_state.tracked_photo_ids
                )
                st.session_state.current_session_id = session_id
                st.session_state.session_title = save_title
                st.success(f"✓ Chat saved! (ID: {session_id})")
                st.rerun()
        else:
            st.info("Start a conversation to save it")

    with col2:
        st.markdown("**Load Saved Chat**")
        saved_sessions = get_all_chat_sessions()

        if saved_sessions:
            for session_id, title, created_at, updated_at, photo_count in saved_sessions:
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    if st.button(f"📁 {title}", key=f"load_{session_id}"):
                        # Load session
                        session_data = load_chat_session(session_id)
                        st.session_state.chat_messages = session_data['messages']
                        st.session_state.tracked_photo_ids = session_data['photo_ids']
                        st.session_state.current_session_id = session_id
                        st.session_state.session_title = session_data['title']
                        st.success(f"✓ Loaded: {session_data['title']}")
                        st.rerun()
                with col_b:
                    if st.button("🗑️", key=f"delete_{session_id}"):
                        delete_chat_session(session_id)
                        st.success("Deleted")
                        st.rerun()

                st.caption(f"📸 {photo_count} photos | Updated: {updated_at[:16]}")
        else:
            st.info("No saved chats yet")

    # New Chat button
    if len(st.session_state.chat_messages) > 0:
        if st.button("🆕 Start New Chat"):
            st.session_state.chat_messages = []
            st.session_state.tracked_photo_ids = []
            st.session_state.current_session_id = None
            st.session_state.session_title = None
            st.rerun()

# Admin Section - Edit Photo Metadata
st.markdown("---")
st.subheader("🔧 Admin: Edit Photo Metadata")

# Admin password check
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    admin_password = st.text_input("Admin Password", type="password", key="admin_password")

    if st.button("Access Admin Panel", type="primary"):
        # Use same APP_PASSWORD or a separate ADMIN_PASSWORD
        correct_password = os.environ.get('ADMIN_PASSWORD', os.environ.get('APP_PASSWORD', 'admin'))
        if admin_password == correct_password:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect admin password")
else:
    st.success("✓ Admin access granted")

    # Select photo to edit
    photo_options = {f"{p['id']}: {p['filename']} ({p['caption_year']})": p['id'] for p in photos}
    selected_display = st.selectbox("Select photo to edit:", options=list(photo_options.keys()))
    selected_id = photo_options[selected_display]

    # Get photo data
    photo = next((p for p in photos if p['id'] == selected_id), None)

    if photo:
        st.markdown(f"### Editing: {photo['filename']}")

        # Show current photo
        col1, col2 = st.columns([1, 2])

        with col1:
            if Path(photo['file_path']).exists():
                st.image(photo['file_path'], use_container_width=True)

        with col2:
            st.markdown("**Current Caption:**")
            st.info(photo['original_caption'] or "No caption")

        # Edit form
        with st.form(key=f"edit_form_{selected_id}"):
            st.markdown("#### Edit Metadata")

            # Editable fields
            new_year = st.number_input("Year", value=photo['caption_year'] if photo['caption_year'] else 1900, min_value=1900, max_value=2100)
            new_city = st.text_input("City", value=photo['caption_city'] or "")
            new_location = st.text_input("Location/Intersection", value=photo['caption_location'] or "")
            new_address = st.text_input("Street Address", value=photo.get('caption_street_address') or "")

            col_lat, col_lon = st.columns(2)
            with col_lat:
                new_lat = st.number_input("Latitude", value=float(photo['latitude']) if photo['latitude'] else 0.0, format="%.6f")
            with col_lon:
                new_lon = st.number_input("Longitude", value=float(photo['longitude']) if photo['longitude'] else 0.0, format="%.6f")

            # Notes field
            st.markdown("#### Research Notes")
            conn = sqlite3.connect('photo_archive.db')
            cursor = conn.cursor()
            cursor.execute("SELECT notes FROM photos WHERE id = ?", (selected_id,))
            current_notes = cursor.fetchone()
            conn.close()

            notes_value = current_notes[0] if current_notes and current_notes[0] else ""
            new_notes = st.text_area("Notes", value=notes_value, height=150,
                                     help="Add research notes, historical context, corrections, etc.")

            # Submit button
            col1, col2 = st.columns([1, 3])
            with col1:
                submitted = st.form_submit_button("💾 Save Changes", type="primary")

            if submitted:
                # Update database
                try:
                    conn = sqlite3.connect('photo_archive.db')
                    cursor = conn.cursor()

                    cursor.execute("""
                        UPDATE photos
                        SET caption_year = ?,
                            caption_city = ?,
                            caption_location = ?,
                            caption_street_address = ?,
                            latitude = ?,
                            longitude = ?,
                            notes = ?
                        WHERE id = ?
                    """, (
                        new_year if new_year != 1900 else None,
                        new_city if new_city else None,
                        new_location if new_location else None,
                        new_address if new_address else None,
                        new_lat if new_lat != 0.0 else None,
                        new_lon if new_lon != 0.0 else None,
                        new_notes if new_notes else None,
                        selected_id
                    ))

                    conn.commit()
                    conn.close()

                    st.success("✓ Changes saved to database!")

                    # Auto-commit to GitHub
                    github_token = os.environ.get('GITHUB_TOKEN')

                    if github_token:
                        with st.spinner("📤 Committing to GitHub..."):
                            try:
                                # Initialize GitHub client
                                g = Github(github_token)
                                repo = g.get_repo("georgehagstrom/camilo-photo-archive-test")

                                # Read current database file
                                with open('photo_archive.db', 'rb') as f:
                                    content = f.read()

                                # Get current file from repo to get its SHA
                                try:
                                    file = repo.get_contents("photo_archive.db", ref="main")
                                    sha = file.sha
                                except:
                                    sha = None  # File doesn't exist yet

                                # Commit message
                                commit_msg = f"Auto-update metadata: {photo['filename']} (photo ID {selected_id})"

                                # Update file in GitHub
                                if sha:
                                    repo.update_file(
                                        path="photo_archive.db",
                                        message=commit_msg,
                                        content=content,
                                        sha=sha,
                                        branch="main"
                                    )
                                else:
                                    repo.create_file(
                                        path="photo_archive.db",
                                        message=commit_msg,
                                        content=content,
                                        branch="main"
                                    )

                                st.success("✓ Committed to GitHub! App will redeploy in ~30 seconds.")
                                st.info("💡 The app will automatically restart with your changes.")

                            except GithubException as e:
                                st.warning(f"⚠️ Could not auto-commit to GitHub: {e.data.get('message', str(e))}")
                                st.info("💡 Changes saved locally but not persisted. See instructions below to commit manually.")

                            except Exception as e:
                                st.warning(f"⚠️ Could not auto-commit: {e}")
                                st.info("💡 Changes saved locally but not persisted. See instructions below to commit manually.")
                    else:
                        st.warning("⚠️ No GITHUB_TOKEN found - changes saved locally only")
                        st.info("💡 Add GITHUB_TOKEN to secrets to enable auto-commit")

                    # Clear cache to reload data
                    st.cache_data.clear()

                    time.sleep(2)
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error saving changes: {e}")

        # Instructions for setting up auto-commit
        github_token = os.environ.get('GITHUB_TOKEN')
        if not github_token:
            with st.expander("⚙️ Setup: Enable Auto-Commit to GitHub"):
                st.markdown("""
                **To enable automatic persistence of changes:**

                1. **Create a GitHub Personal Access Token:**
                   - Go to: https://github.com/settings/tokens
                   - Click "Generate new token (classic)"
                   - Give it a name: "Camilo Archive App"
                   - Select scopes: **`repo`** (full control of private repositories)
                   - Click "Generate token"
                   - **Copy the token** (you won't see it again!)

                2. **Add token to Streamlit Secrets:**
                   - Go to your app settings: https://share.streamlit.io/
                   - Click on your app → Settings (⚙️) → Secrets
                   - Add this line:
                   ```toml
                   GITHUB_TOKEN = "ghp_your_token_here"
                   ```
                   - Click "Save"

                3. **That's it!** Changes will auto-commit to GitHub.

                **Security Note:** The token has write access to your repo. Keep it secret!
                """)
        else:
            with st.expander("✅ Auto-Commit Enabled"):
                st.markdown("""
                **Auto-commit to GitHub is enabled!**

                When you save changes:
                1. ✓ Database updates locally
                2. ✓ Commits to GitHub automatically
                3. ✓ Streamlit Cloud redeploys (~30 seconds)
                4. ✓ Changes persist permanently

                Changes are tracked in git history:
                https://github.com/georgehagstrom/camilo-photo-archive-test/commits/main
                """)

    # Logout button
    if st.button("🚪 Logout Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()
