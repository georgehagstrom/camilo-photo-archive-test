# Streamlit Cloud Deployment Instructions

## What's Included in This Repo

- ✅ `app_visual.py` - Main application with authentication
- ✅ `photo_archive.db` - Database with 6 demo photos
- ✅ `Photos/` - 6 demo JPEG images
- ✅ `requirements.txt` - All Python dependencies
- ✅ `.streamlit/config.toml` - Streamlit configuration

## Steps to Deploy on Streamlit Cloud

### 1. Go to Streamlit Cloud
Visit: https://share.streamlit.io/

### 2. Sign In
Click "Sign in with GitHub"

### 3. Deploy New App
1. Click "New app" button
2. Select repository: `georgehagstrom/camilo-photo-archive-test`
3. Branch: `main` (or `master`)
4. Main file path: `app_visual.py`
5. Click "Deploy!"

### 4. Add Secrets (Required!)
Once the app deploys, click on the app settings (⚙️ icon):

1. Go to "Secrets" section
2. Paste this (with your actual values):

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-YOUR-ACTUAL-KEY-HERE"
APP_PASSWORD = "your-secure-password-here"
```

3. Click "Save"
4. App will automatically restart

### 5. Test It!
Your app will be live at: `https://[your-app-name].streamlit.app`

1. Visit the URL
2. Enter your APP_PASSWORD
3. Browse photos and chat!

## Security Notes

- ✅ Secrets are encrypted and never exposed in logs
- ✅ Password protects the entire app
- ✅ HTTPS by default
- ⚠️ Change the default password immediately!

## Local Development

To run locally:
```bash
source photo_archive_env/bin/activate
export ANTHROPIC_API_KEY="your-key"
export APP_PASSWORD="your-password"
streamlit run app_visual.py
```

## Updating the Deployed App

Just push to GitHub - Streamlit Cloud auto-deploys:
```bash
git add .
git commit -m "Update app"
git push
```

## Troubleshooting

**App won't start:**
- Check that secrets are set correctly
- View logs in Streamlit Cloud dashboard

**Photos don't load:**
- Check that `Photos/` directory is in the repo
- Check `photo_archive.db` has correct file paths

**Chat doesn't work:**
- Verify ANTHROPIC_API_KEY is set in secrets
- Check API key is valid at console.anthropic.com
