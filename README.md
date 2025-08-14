# 🎵 TuneGenie - AI-Powered Music Recommender

**TuneGenie** is an intelligent music recommendation system that combines collaborative filtering with AI-powered contextual insights to create personalized playlists based on your mood, activity, and language preferences.

## ✨ Features

### 🎯 **Smart Playlist Generation**
- **Mood-Based Recommendations**: Generate playlists based on your current emotional state
- **Activity Context**: Tailored music for working, exercising, studying, commuting, and more
- **Language Preferences**: Support for 20+ languages including English, Tamil, Telugu, Hindi, and more
- **Custom Track Count**: Generate playlists with 1-250 tracks based on your needs

### 🤖 **AI-Powered Intelligence**
- **Collaborative Filtering**: Uses SVD algorithm for personalized recommendations
- **LLM Enhancement**: GPT-4 and Hugging Face models for contextual insights
- **Multi-Agent Workflow**: Orchestrated AI agents for optimal playlist creation
- **Intelligent Fallbacks**: Graceful degradation when external APIs are unavailable

### 🎨 **Beautiful User Interface**
- **Modern Streamlit Dashboard**: Clean, responsive web interface
- **Real-time Analysis**: User profile insights and listening patterns
- **Interactive Visualizations**: Charts and metrics for music preferences
- **Professional Design**: Dark theme with Spotify-inspired color scheme

### 🔌 **Spotify Integration**
- **OAuth Authentication**: Secure Spotify account connection
- **Playlist Management**: Create, modify, and save playlists directly to Spotify
- **Track Discovery**: Search and include songs from Spotify's vast catalog
- **Artist Filtering**: Find music by specific artists and genres

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Spotify Premium Account
- OpenAI API Key (optional, for enhanced AI features)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/tunie-music-app.git
cd tunie-music-app
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp env.example .env
# Edit .env with your API keys
```

5. **Run the application:**
```bash
streamlit run app.py
```

## ⚙️ Configuration

### Environment Variables (.env)
```env
# Spotify API Credentials
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8501/callback

# OpenAI API (Optional)
OPENAI_API_KEY=your_openai_api_key

# Hugging Face Token (Free AI Model)
HUGGINGFACE_TOKEN=your_huggingface_token
```

### Spotify API Setup
1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new application
3. Add `http://127.0.0.1:8501/callback` to Redirect URIs
4. Copy Client ID and Client Secret to your `.env` file

## 🎵 Usage

### Generate Playlist
1. **Select Your Mood**: Choose from Happy, Sad, Energetic, Calm, etc.
2. **Describe Your Activity**: Tell us what you're doing (working, exercising, etc.)
3. **Choose Language**: Select your preferred language for music
4. **Set Track Count**: Pick any number from 1 to 250 tracks
5. **Generate**: Let TuneGenie create your perfect playlist!

### User Analysis
- **Profile Insights**: View your music preferences and listening patterns
- **Genre Analysis**: Discover your favorite music genres
- **Performance Metrics**: Track workflow execution and AI model usage

## 🏗️ Architecture

### Core Components
- **`src/spotify_client.py`**: Spotify API integration and authentication
- **`src/recommender.py`**: Collaborative filtering engine using scikit-surprise
- **`src/llm_agent.py`**: AI model integration and contextual insights
- **`src/workflow.py`**: Multi-agent orchestration and workflow management
- **`app.py`**: Streamlit web interface and user experience

### Technology Stack
- **Backend**: Python 3.8+, scikit-learn, scikit-surprise
- **AI/ML**: OpenAI GPT-4, Hugging Face models, LangChain
- **Web Framework**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, Matplotlib
- **Authentication**: Spotify OAuth, API key management

## 🔧 Development

### Project Structure
```
tunie-music-app/
├── src/                    # Core application code
│   ├── spotify_client.py  # Spotify API client
│   ├── recommender.py     # ML recommendation engine
│   ├── llm_agent.py      # AI model integration
│   └── workflow.py        # Workflow orchestration
├── models/                 # Trained ML models
├── data/                   # Data storage and cache
├── app.py                  # Streamlit web interface
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── .gitignore             # Git ignore rules
└── README.md              # Project documentation
```

### Running Tests
```bash
# Test imports
python -c "import app; print('✅ App imports successfully!')"

# Run specific modules
python -c "from src.workflow import MultiAgentWorkflow; print('✅ Workflow imports successfully!')"
```

## 🌟 Features in Detail

### Language Support
- **Indian Languages**: Tamil, Telugu, Hindi, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Urdu
- **International**: English, Spanish, French, German, Italian, Portuguese, Korean, Japanese, Chinese, Arabic, Russian
- **Smart Filtering**: Language-specific genre mapping and track prioritization

### AI Models
- **Primary**: OpenAI GPT-4 (when API key available)
- **Fallback**: Hugging Face free models (DialoGPT, OPT, GPT-2)
- **Intelligent Responses**: Context-aware music insights and recommendations

### Collaborative Filtering
- **Algorithm**: SVD (Singular Value Decomposition)
- **Training**: User-item interaction matrix from Spotify data
- **Personalization**: User-specific track recommendations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Spotify API** for music data and playlist management
- **OpenAI** for advanced AI capabilities
- **Hugging Face** for free AI model access
- **Streamlit** for the beautiful web interface
- **scikit-learn** for machine learning algorithms

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/tunie-music-app/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/tunie-music-app/discussions)
- **Email**: your.email@example.com

---

**Made with ❤️ by [Your Name]**

*Transform your mood into music with TuneGenie!* 🎵✨
