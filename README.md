# Photo History Archive Analysis System

A system for analyzing and interrogating large collections of documentary photographs, specifically designed for studying urban deindustrialization and social history.

## Overview

This system implements the workflow described for analyzing 21,000+ documentary photographs spanning 50+ years of urban change in American cities. It combines:

- **Automated inventory**: File metadata and EXIF extraction
- **Vision analysis**: Claude AI analyzes each photo for temporal, spatial, and social indicators
- **Structured storage**: SQLite database with queryable fields
- **Research interface**: Query system for longitudinal and thematic analysis

## Features

### Phase 1: Inventory (Implemented)
- Extracts file metadata (size, dates, dimensions)
- Reads EXIF data (camera, GPS if available, timestamps)
- Stores in SQLite database with unique file paths

### Phase 2: Vision-Based Analysis (Implemented)
For each image, Claude analyzes:
- **Temporal estimation**: Decade, confidence level, dating clues
- **Location cues**: Signage, street names, architectural style
- **Subject matter**: Buildings, people, vehicles, infrastructure
- **Condition indicators**: Building state, fire/vacancy evidence, murals
- **Historical context**: References to events, movements, social themes
- **Detailed description**: Prose capturing the scene's significance

### Phase 3: Query Interface (Implemented)
Search and analyze the corpus:
- Find photos by decade
- Identify photos with murals or graffiti
- Track evidence of fire damage
- Find vacant/abandoned buildings
- Search descriptions for keywords
- Get complete analysis for any photo

## Installation

### Requirements
```bash
pip install pillow anthropic
```

### API Key
For vision analysis, you need an Anthropic API key:
```bash
export ANTHROPIC_API_KEY='your-key-here'
```

## Usage

### 1. Basic Inventory (No Vision Analysis)
```bash
python photo_analyzer.py Photos/
```

This creates `photo_archive.db` with file metadata.

### 2. Full Analysis with Vision AI
```bash
python photo_analyzer.py Photos/ --analyze
```

This performs Claude vision analysis on each image (requires API key).

### 3. Query the Archive

**Interactive mode:**
```bash
python query_archive.py --interactive
```

**Command-line queries:**
```bash
# List all photos
python query_archive.py --list

# Find photos from the 1980s
python query_archive.py --decade 1980s

# Find photos with murals
python query_archive.py --murals

# Find fire damage evidence
python query_archive.py --fire

# Search descriptions
python query_archive.py --search "civil rights"
```

### 4. Get Summary Statistics
```bash
python photo_analyzer.py --summary
```

## Database Schema

### `photos` table
- File path, filename, size, dimensions
- Creation and modification dates
- EXIF metadata (camera, GPS, date taken)
- Original captions (when available)
- Analysis status

### `vision_analysis` table
- Temporal estimation (decade, confidence, year range)
- Location cues (signage, street names, architectural style)
- Subject categorization (buildings, people, vehicles)
- Condition indicators (fire, vacancy, boarding, murals)
- Infrastructure state
- Detailed prose description
- Historical and social context markers

## Research Workflow

### Typical Usage Pattern

1. **Ingest a collection:**
   ```bash
   python photo_analyzer.py path/to/photos/ --analyze
   ```

2. **Explore the corpus:**
   ```bash
   python photo_analyzer.py --summary
   python query_archive.py --interactive
   ```

3. **Thematic queries:**
   - "Show me all images depicting public housing"
   - "Find evidence of community murals in the 1980s"
   - "Track the same location across decades"

4. **Export for further analysis:**
   Query the SQLite database directly for custom analysis:
   ```python
   import sqlite3
   conn = sqlite3.connect('photo_archive.db')
   # Your custom queries...
   ```

## Ethical Considerations

Following Opus's recommendations:

1. **Original captions are sacred**: Human-authored metadata never overwritten
2. **Observational descriptions**: Avoids evaluative terms like "decay" or "blight"
3. **Specific features**: Describes what IS present, not presumed absence
4. **Community respect**: Mindful that subjects are vulnerable populations

## Cost Estimation

- **Haiku (fast, cheap)**: ~$0.50 per 1000 images
- **Sonnet (balanced)**: ~$5 per 1000 images
- **Opus (highest quality)**: ~$25 per 1000 images

Current implementation uses Sonnet. For 21,000 images: ~$105

## Future Enhancements

- [ ] CLIP embeddings for visual similarity clustering
- [ ] Geographic clustering for "same place, different time" sets
- [ ] OCR integration for degraded signage
- [ ] Web interface for browsing results
- [ ] Export to timeline visualizations
- [ ] Batch API integration (50% cost reduction)

## Related Research

- Distant Viewing Lab (Taylor Arnold & Lauren Tilton, U. Richmond)
- Computational approaches to documentary photography
- Digital humanities methodologies for visual archives

## License

MIT License - feel free to adapt for your own photo history projects.
