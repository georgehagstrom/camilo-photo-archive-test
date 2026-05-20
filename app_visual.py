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
               p.caption_location
        FROM photos p
        WHERE p.latitude IS NOT NULL AND p.longitude IS NOT NULL
        ORDER BY p.caption_year, p.filename
    """)

    columns = ['id', 'filename', 'file_path', 'original_caption', 'latitude',
               'longitude', 'caption_year', 'caption_city', 'caption_location']

    photos = []
    for row in cursor.fetchall():
        photos.append(dict(zip(columns, row)))

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

        st.markdown("---")

        st.markdown(f"**GPS:** {selected_photo['latitude']:.6f}, {selected_photo['longitude']:.6f}")

        maps_url = f"https://www.google.com/maps?q={selected_photo['latitude']},{selected_photo['longitude']}"
        st.markdown(f"[🗺️ View on Google Maps]({maps_url})")

        # Google Street View
        street_view_url = f"https://www.google.com/maps/@{selected_photo['latitude']},{selected_photo['longitude']},3a,75y,90t/data=!3m4!1e1!3m2!1s0!2e0"
        st.markdown(f"[📍 Google Street View]({street_view_url})")

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
        return execute_sql_query(tool_input["query"])
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
- query_database: Run SQL queries on the photo database
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
    with st.expander("💡 Example questions (now with MCP tools!)"):
        example_questions = [
            "Run a SQL query to find all photos from the 1970s",
            "What years are documented in this archive?",
            "Search the web for historical context about Camden NJ in 1979",
            "Calculate the average year of photos by location",
            "Tell me about the Broadway location",
            "Find all photos that mention 'Broadway' in the caption",
            "Use Python to analyze the distribution of photos by decade"
        ]

        for q in example_questions:
            if st.button(q, key=f"example_{q[:20]}"):
                st.session_state.chat_messages.append({"role": "user", "content": q})
                st.rerun()
