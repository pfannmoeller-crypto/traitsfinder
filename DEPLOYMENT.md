# Deployment Guide for Streamlit App

This guide will help you deploy your Streamlit app publicly. The easiest and recommended method is **Streamlit Community Cloud** (free).

## 🚀 Option 1: Streamlit Community Cloud (Recommended - Free)

### Prerequisites
1. A GitHub account
2. Your code pushed to a GitHub repository

### Steps

#### 1. Push Your Code to GitHub

If you haven't already:

```bash
# Initialize git (if not already done)
git init

# Add all files (secrets.toml will be ignored by .gitignore)
git add .

# Commit
git commit -m "Initial commit"

# Create a repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

**⚠️ Important:** Make sure `.streamlit/secrets.toml` is NOT committed to GitHub (it's in `.gitignore`).

#### 2. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Click **"New app"**
4. Select your repository and branch
5. Set the **Main file path** to: `app.py`
6. Click **"Deploy!"**

#### 3. Configure Secrets

After deployment:

1. In your Streamlit Cloud dashboard, click on your app
2. Go to **"Settings"** → **"Secrets"**
3. Add your secrets in TOML format:

```toml
GOOGLE_API_KEY = "your-api-key-here"
```

4. Click **"Save"** - your app will automatically redeploy

#### 4. Access Your App

Your app will be available at: `https://YOUR_APP_NAME.streamlit.app`

---

## 🌐 Option 2: Other Deployment Platforms

### Railway

1. Sign up at [railway.app](https://railway.app)
2. Create a new project from GitHub
3. Add environment variable: `GOOGLE_API_KEY`
4. Railway will auto-detect Streamlit and deploy

### Heroku

1. Install Heroku CLI
2. Create `Procfile`:
   ```
   web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
   ```
3. Deploy:
   ```bash
   heroku create your-app-name
   heroku config:set GOOGLE_API_KEY=your-key
   git push heroku main
   ```

### Render

1. Sign up at [render.com](https://render.com)
2. Create a new Web Service
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`
5. Add environment variable: `GOOGLE_API_KEY`

---

## ✅ Pre-Deployment Checklist

- [x] Fixed hardcoded Windows path in `debug_log()` function
- [ ] `.gitignore` created to protect secrets
- [ ] Code pushed to GitHub
- [ ] Secrets configured in deployment platform
- [ ] Tested locally with `streamlit run app.py`

## 🔒 Security Notes

- **Never commit** `.streamlit/secrets.toml` to GitHub
- Use environment variables or platform secrets management
- Keep your API keys secure and rotate them if exposed

## 📝 Troubleshooting

### App won't start
- Check that `app.py` is the correct main file
- Verify all dependencies in `requirements.txt` are correct
- Check logs in your deployment platform

### API Key errors
- Ensure `GOOGLE_API_KEY` is set in your platform's secrets/environment variables
- Verify the key is valid and has proper permissions

### Import errors
- Make sure all packages in `requirements.txt` are listed
- Check Python version compatibility (Streamlit Cloud uses Python 3.11)

---

## 🎉 You're Done!

Once deployed, share your app URL with the world!

