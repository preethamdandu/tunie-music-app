# 🚀 TuneGenie Quick Start Guide

Get TuneGenie up and running in minutes! This guide will walk you through the setup process step by step.

## 📋 Prerequisites

Before you begin, make sure you have:

- **Python 3.8+** installed
- **Spotify Developer Account** with API credentials
- **OpenAI API Key** for GPT-4 integration
- **Git** (optional, for cloning the repository)

## 🔑 Step 1: Get API Credentials

### Spotify API Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Log in with your Spotify account
3. Click "Create App"
4. Fill in the app details:
   - **App name**: TuneGenie
   - **App description**: AI-powered music recommender
   - **Website**: `http://localhost:8501`
   - **Redirect URI**: `http://localhost:8501/callback`
5. Click "Save"
6. Copy your **Client ID** and **Client Secret**

### OpenAI API Setup
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Navigate to "API Keys"
4. Click "Create new secret key"
5. Copy your **API Key**

## 📥 Step 2: Set Up the Project

### Option A: Clone Repository
```bash
git clone <repository-url>
cd tunie-music-app
```

### Option B: Use Existing Files
If you already have the project files, navigate to the project directory.

## 🔧 Step 3: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## ⚙️ Step 4: Configure Environment

1. Copy the example environment file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` with your API credentials:
   ```env
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   SPOTIFY_REDIRECT_URI=http://localhost:8501/callback
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## 🧪 Step 5: Test the Setup

Run the test script to verify everything is working:

```bash
python test_setup.py
```

You should see all tests passing! ✅

## 🚀 Step 6: Launch TuneGenie

### Option A: Run Locally
```bash
streamlit run app.py
```

### Option B: Use Docker
```bash
# Build and run with Docker Compose
docker-compose up --build
```

## 🌐 Step 7: Access the Application

Open your browser and go to:
- **Local**: http://localhost:8501
- **Docker**: http://localhost:8501

## 🎯 Step 8: First Use

1. **Connect Spotify**: Click the authentication button to connect your Spotify account
2. **Generate Playlist**: Use the "Generate Playlist" tab to create your first AI-powered playlist
3. **Explore Features**: Try the user analysis, AI insights, and other features

## 🔍 Troubleshooting

### Common Issues

#### Import Errors
```bash
# Make sure you're in the project directory
pwd
# Should show: /path/to/tunie-music-app

# Check Python path
python -c "import sys; print(sys.path)"
```

#### API Authentication Issues
- Verify your API credentials in `.env`
- Check that redirect URIs match exactly
- Ensure your Spotify app is not in development mode (if you want others to use it)

#### Port Already in Use
```bash
# Find what's using port 8501
lsof -i :8501

# Kill the process or use a different port
streamlit run app.py --server.port 8502
```

### Getting Help

1. **Check the logs**: Look for error messages in the terminal
2. **Verify API keys**: Ensure all environment variables are set
3. **Test components**: Run `python test_setup.py` to isolate issues
4. **Check dependencies**: Verify all packages are installed correctly

## 📚 Next Steps

Once TuneGenie is running:

1. **Customize Prompts**: Edit files in the `prompts/` directory
2. **Train Models**: Use the settings tab to retrain recommendation models
3. **Deploy to Cloud**: Use the AWS deployment script for production
4. **Monitor Performance**: Check the performance tab for insights

## 🎉 You're All Set!

Congratulations! You now have a fully functional AI-powered music recommendation system. 

**Happy listening with TuneGenie! 🎵**

---

## 📞 Support

If you encounter issues:
1. Check this guide first
2. Review the error logs
3. Verify your API credentials
4. Test with the setup script

For additional help, refer to the main README.md file or create an issue in the repository.
