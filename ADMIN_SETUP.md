# Admin Panel Setup

## Enable Auto-Commit to GitHub

To make metadata edits persist automatically, you need to add a GitHub token to Streamlit secrets.

### Step 1: Create GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token (classic)"**
3. Give it a name: `Camilo Archive App`
4. Set expiration: **No expiration** (or custom)
5. Select scopes:
   - ✅ **`repo`** (Full control of private repositories)
   - That's the only scope needed
6. Click **"Generate token"**
7. **COPY THE TOKEN** - you won't see it again!
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Step 2: Add Token to Streamlit Secrets

1. Go to: https://share.streamlit.io/
2. Find your app: `camilo-photo-archive-test`
3. Click **⚙️ Settings**
4. Go to **Secrets** tab
5. Add this line to your existing secrets:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
APP_PASSWORD = "your-password"
GITHUB_TOKEN = "ghp_your_github_token_here"
```

6. Click **"Save"**
7. App will restart automatically

### Step 3: Test It!

1. Go to your deployed app
2. Scroll to **"🔧 Admin: Edit Photo Metadata"**
3. Enter admin password
4. Edit a photo's metadata or notes
5. Click **"💾 Save Changes"**

You should see:
- ✓ Changes saved to database!
- ✓ Committed to GitHub! App will redeploy in ~30 seconds.

### How It Works

When you save changes:

1. **Database updates** locally
2. **Auto-commits** `photo_archive.db` to GitHub via API
3. **GitHub triggers** Streamlit Cloud redeploy
4. **App restarts** with updated database (~30 seconds)
5. **Changes persist** permanently

### Commit History

All edits are tracked in git:
https://github.com/georgehagstrom/camilo-photo-archive-test/commits/main

Each commit message shows:
- `Auto-update metadata: [filename] (photo ID X)`

### Security

**The GitHub token has write access to your repository.**

- ✅ Store only in Streamlit secrets (encrypted)
- ✅ Never commit token to git
- ✅ Token is used only for committing database updates
- ⚠️ Anyone with admin password can trigger commits

### Troubleshooting

**"Could not auto-commit to GitHub"**
- Check token is valid: https://github.com/settings/tokens
- Check token has `repo` scope
- Check token is added to Streamlit secrets correctly

**"No GITHUB_TOKEN found"**
- Token not in Streamlit secrets
- Add it following Step 2 above

**Changes don't persist**
- Wait 30-60 seconds for redeploy
- Check GitHub commits: https://github.com/georgehagstrom/camilo-photo-archive-test/commits/main
- If no commit, check Streamlit logs for errors

### Alternative: Manual Commits

If you prefer not to use auto-commit:

1. Don't add `GITHUB_TOKEN` to secrets
2. Make edits in the app
3. Manually commit from your local machine:

```bash
cd /home/georgehagstrom/work/CamiloPhotos
git add photo_archive.db
git commit -m "Update metadata: [description]"
git push
```

### For Production (21k Photos)

When scaling to the full archive, consider:
- **Cloud database** (PostgreSQL) for instant persistence
- No redeploys needed for edits
- Multiple users can edit simultaneously
- See DEPLOYMENT.md for cloud database setup
