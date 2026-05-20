# Photo Ingestion Workflow

## How to Add New Photos

### Simple Process:

1. **Add photos to `Photos/` directory**
   ```bash
   cp /path/to/new/photos/*.jpg Photos/
   ```

2. **Commit and push to GitHub**
   ```bash
   git add Photos/
   git commit -m "Add new photos from [date/location]"
   git push
   ```

3. **GitHub Action automatically processes them**
   - Extracts EXIF metadata
   - Parses captions for year, location, address
   - Geocodes locations to GPS coordinates
   - Updates database
   - Commits database back to repo

4. **Streamlit Cloud auto-deploys**
   - New photos appear in the app within 2-3 minutes

---

## What Happens Automatically:

The GitHub Action (`.github/workflows/process-photos.yml`) runs when you push photos:

1. ✅ Detects which photos are **not** in database yet
2. ✅ Extracts EXIF data (dimensions, camera, date, caption)
3. ✅ Parses Vergara-style captions:
   - Year (e.g., "1982")
   - City (e.g., "Camden")
   - Location/intersection (e.g., "Broadway at Walnut")
   - Street address (e.g., "810 Broadway")
4. ✅ Geocodes locations using OpenStreetMap
5. ✅ Updates `photo_archive.db`
6. ✅ Commits updated database
7. ✅ Triggers Streamlit redeploy

---

## Manual Processing (Local Testing):

You can test the processing locally before pushing:

```bash
# Add photos to Photos/ directory
cp new_photo.jpg Photos/

# Run processing script locally
python process_new_photos.py

# Review changes
git status

# Push when ready
git add .
git commit -m "Add new photos"
git push
```

---

## Photo Requirements:

### File Format:
- ✅ JPEG files (`.jpg` or `.jpeg`)
- ✅ Should have EXIF data (especially ImageDescription for caption)

### Caption Format (in EXIF ImageDescription):
The script expects Vergara-style captions:
```
"Description or quote", Location, City, Year
```

Examples:
- `"We built the USA," Bicentennial celebration, Broadway at Mt. Vernon, Camden, 1979`
- `Revolutionary war scenes painted by school children on abandoned buildings, 810 Broadway, Camden, 1982`

### Components Extracted:
- **Year**: 4-digit year at end
- **City**: City name before year
- **Location**: Text after "at/from" or in quotes
- **Address**: Street number + street name (e.g., "810 Broadway")

---

## Monitoring:

### Check GitHub Action Status:
1. Go to: https://github.com/georgehagstrom/camilo-photo-archive-test/actions
2. See processing logs
3. Check for errors

### View Logs:
Click on any workflow run to see:
- Which photos were processed
- Any geocoding errors
- Database update status

---

## Troubleshooting:

### "No API key available" error:
Add `ANTHROPIC_API_KEY` to GitHub repository secrets:
1. Go to: https://github.com/georgehagstrom/camilo-photo-archive-test/settings/secrets/actions
2. Click "New repository secret"
3. Name: `ANTHROPIC_API_KEY`
4. Value: Your API key

### Photo not geocoded:
- Check caption format matches expected pattern
- Location might not be found by OpenStreetMap
- Script falls back to city center if specific address not found

### Database conflicts:
- Action automatically handles merge conflicts
- If issues persist, manually pull and push

---

## Scaling to 21,000 Photos:

When ready for full archive:

### Option A: Batch Upload (Recommended)
```bash
# Copy photos in batches
cp batch1/*.jpg Photos/
git add Photos/
git commit -m "Add batch 1: 1979-1980 photos"
git push

# Wait for processing (5-10 minutes per 100 photos)
# Then repeat for next batch
```

### Option B: One-Time Migration
```bash
# Copy all photos
cp archive/*.jpg Photos/

# Run locally first (takes a while)
python process_new_photos.py

# Push everything
git add .
git commit -m "Migrate full archive"
git push
```

**Note:** At 21k photos, you'll need to migrate to cloud storage (S3/GCS) as GitHub has 1GB repo limits. See DEPLOYMENT.md for cloud storage setup.

---

## Future Enhancements:

- [ ] Add vision AI analysis during ingestion (auto-tag photo content)
- [ ] Batch processing API endpoint
- [ ] Web upload interface (drag & drop in app)
- [ ] Duplicate detection
- [ ] Quality checks (resolution, corruption)
