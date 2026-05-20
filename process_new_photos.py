#!/usr/bin/env python3
"""
Process new photos in the Photos/ directory that aren't in the database yet
"""

import sqlite3
import os
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.geocoders import Nominatim
import time
import re

def get_processed_photos():
    """Get list of filenames already in database"""
    conn = sqlite3.connect('photo_archive.db')
    cursor = conn.cursor()

    cursor.execute("SELECT filename FROM photos")
    processed = {row[0] for row in cursor.fetchall()}

    conn.close()
    return processed

def get_photo_files():
    """Get all photo files in Photos/ directory"""
    photos_dir = Path('Photos')
    if not photos_dir.exists():
        return set()

    photo_files = set()
    for ext in ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']:
        photo_files.update(photos_dir.glob(ext))

    return {p.name for p in photo_files}

def extract_exif(image_path):
    """Extract EXIF metadata from image"""
    try:
        image = Image.open(image_path)

        # Get EXIF data
        exif_data = {}
        if hasattr(image, '_getexif') and image._getexif() is not None:
            exif = image._getexif()
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value

        # Extract caption from various possible fields
        caption = None
        for field in ['ImageDescription', 'UserComment', 'XPComment', 'Caption', 'Description']:
            if field in exif_data and exif_data[field]:
                caption = exif_data[field]
                if isinstance(caption, bytes):
                    caption = caption.decode('utf-8', errors='ignore')
                caption = str(caption).strip()
                if caption:
                    break

        return {
            'width': image.width,
            'height': image.height,
            'camera_make': exif_data.get('Make'),
            'camera_model': exif_data.get('Model'),
            'date_taken': exif_data.get('DateTimeOriginal'),
            'caption': caption,
        }
    except Exception as e:
        print(f"Error extracting EXIF from {image_path}: {e}")
        return {
            'width': None,
            'height': None,
            'camera_make': None,
            'camera_model': None,
            'date_taken': None,
            'caption': None,
        }

def parse_caption(caption):
    """Parse Vergara-style caption to extract structured data"""
    if not caption:
        return {}

    # Extract year (4 digits, usually at end)
    year_match = re.search(r',\s*(\d{4})\s*$', caption)
    year = int(year_match.group(1)) if year_match else None

    # Remove year for further parsing
    caption_without_year = re.sub(r',\s*\d{4}\s*$', '', caption)

    # Extract city (Camden, Newark, etc.)
    city_match = re.search(r',\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*,', caption_without_year)
    city = city_match.group(1) if city_match else None

    # Extract street address (e.g., "810 Broadway")
    address_match = re.search(r'(\d{3,4})\s+([A-Z][a-z]+)', caption)
    street_address = None
    if address_match:
        street_address = f"{address_match.group(1)} {address_match.group(2)}"

    # Extract intersection/location (text between quotes or "at/from" patterns)
    location = None
    # Try quoted text first
    quote_match = re.search(r'"([^"]+)"', caption)
    if quote_match:
        location = quote_match.group(1)
    else:
        # Try "at/from" pattern
        at_match = re.search(r'(?:at|from)\s+([^,]+)', caption_without_year)
        if at_match:
            location = at_match.group(1).strip()

    return {
        'year': year,
        'city': city,
        'location': location,
        'street_address': street_address
    }

def geocode_location(street_address=None, location=None, city="Camden, NJ"):
    """Geocode a location to get latitude/longitude"""
    if not (street_address or location):
        return None, None

    geolocator = Nominatim(user_agent="camilo_photo_archive")

    # Try full address first
    if street_address:
        query = f"{street_address}, {city}, USA"
        try:
            result = geolocator.geocode(query, timeout=10)
            if result:
                return result.latitude, result.longitude
            time.sleep(1)  # Rate limiting
        except:
            pass

    # Try location/intersection
    if location:
        query = f"{location}, {city}, USA"
        try:
            result = geolocator.geocode(query, timeout=10)
            if result:
                return result.latitude, result.longitude
            time.sleep(1)
        except:
            pass

    # Fallback to city center
    try:
        result = geolocator.geocode(f"{city}, USA", timeout=10)
        if result:
            return result.latitude, result.longitude
    except:
        pass

    return None, None

def process_photo(filename):
    """Process a single photo: extract metadata, parse caption, geocode"""
    filepath = Path('Photos') / filename

    print(f"Processing: {filename}")

    # Extract EXIF
    exif_data = extract_exif(filepath)

    # Parse caption
    parsed = parse_caption(exif_data['caption'])

    # Geocode
    lat, lon = geocode_location(
        street_address=parsed.get('street_address'),
        location=parsed.get('location'),
        city=parsed.get('city', 'Camden, NJ')
    )

    return {
        'filename': filename,
        'file_path': f"Photos/{filename}",
        'width': exif_data['width'],
        'height': exif_data['height'],
        'camera_make': exif_data['camera_make'],
        'camera_model': exif_data['camera_model'],
        'date_taken': exif_data['date_taken'],
        'original_caption': exif_data['caption'],
        'caption_year': parsed.get('year'),
        'caption_city': parsed.get('city'),
        'caption_location': parsed.get('location'),
        'caption_street_address': parsed.get('street_address'),
        'latitude': lat,
        'longitude': lon,
    }

def insert_photo(conn, photo_data):
    """Insert photo metadata into database"""
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO photos (
            filename, file_path, width, height, camera_make, camera_model,
            date_taken, original_caption, caption_year, caption_city,
            caption_location, caption_street_address, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        photo_data['filename'],
        photo_data['file_path'],
        photo_data['width'],
        photo_data['height'],
        photo_data['camera_make'],
        photo_data['camera_model'],
        photo_data['date_taken'],
        photo_data['original_caption'],
        photo_data['caption_year'],
        photo_data['caption_city'],
        photo_data['caption_location'],
        photo_data['caption_street_address'],
        photo_data['latitude'],
        photo_data['longitude']
    ))

    conn.commit()
    print(f"✓ Added to database: {photo_data['filename']}")

def main():
    """Main processing function"""
    print("Checking for new photos...")

    # Get photos already processed
    processed = get_processed_photos()
    print(f"Database has {len(processed)} photos")

    # Get all photo files
    all_photos = get_photo_files()
    print(f"Photos/ directory has {len(all_photos)} files")

    # Find new photos
    new_photos = all_photos - processed

    if not new_photos:
        print("No new photos to process!")
        return

    print(f"\nFound {len(new_photos)} new photos to process:")
    for p in sorted(new_photos):
        print(f"  - {p}")

    # Connect to database
    conn = sqlite3.connect('photo_archive.db')

    # Process each new photo
    for filename in sorted(new_photos):
        try:
            photo_data = process_photo(filename)
            insert_photo(conn, photo_data)
            time.sleep(1)  # Rate limiting for geocoding
        except Exception as e:
            print(f"✗ Error processing {filename}: {e}")

    conn.close()
    print("\n✓ Processing complete!")

if __name__ == '__main__':
    main()
