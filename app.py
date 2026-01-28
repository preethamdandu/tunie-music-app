"""
TuneGenie - AI-Powered Music Recommender
Main Streamlit Application
"""

import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import logging
from dotenv import load_dotenv

# Load environment variables and configure logging once at entrypoint
load_dotenv()

def validate_environment():
    """
    Validate presence of required secrets and configuration.
    - Accepts either SPOTIFY_* or SPOTIPY_* variable names for Spotify creds
    - Requires redirect URI
    - Requires at least one LLM credential: OPENAI_API_KEY or HUGGINGFACE_TOKEN
    Raises SystemExit with a clear message if anything critical is missing.
    """
    import os
    missing = []

    spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID') or os.getenv('SPOTIPY_CLIENT_ID')
    spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET') or os.getenv('SPOTIPY_CLIENT_SECRET')
    spotify_redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI') or os.getenv('SPOTIPY_REDIRECT_URI')

    if not spotify_client_id:
        missing.append('SPOTIFY_CLIENT_ID (or SPOTIPY_CLIENT_ID)')
    if not spotify_client_secret:
        missing.append('SPOTIFY_CLIENT_SECRET (or SPOTIPY_CLIENT_SECRET)')
    if not spotify_redirect_uri:
        missing.append('SPOTIFY_REDIRECT_URI (or SPOTIPY_REDIRECT_URI)')

    # LLM credentials: require at least one
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    has_hf = bool(os.getenv('HUGGINGFACE_TOKEN'))
    if not (has_openai or has_hf):
        missing.append('OPENAI_API_KEY (or provide HUGGINGFACE_TOKEN for fallback)')

    if missing:
        details = '\n - ' + '\n - '.join(missing)
        raise SystemExit(
            f"Missing required environment variables. Please set the following in your .env file:{details}"
        )

# Validate secrets on startup
validate_environment()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

from src.workflow import MultiAgentWorkflow
from src.intent_classifier import IntentClassifier
from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator
from src.security import initialize_security

# ============================================
# UI CONFIGURATION CONSTANTS
# ============================================
UI_DEFAULTS = {
    # Track Count Settings
    'TRACK_COUNT_DEFAULT': 20,
    'TRACK_COUNT_MIN_QUICK': 5,
    'TRACK_COUNT_MAX_QUICK': 50,
    'TRACK_COUNT_STEP_QUICK': 5,
    'TRACK_COUNT_MIN_CUSTOM': 1,
    'TRACK_COUNT_MAX_CUSTOM': 250,
}

# Page configuration
st.set_page_config(
    page_title="TuneGenie - AI Music Recommender",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for ultra-modern styling
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* ============================================
       CRITICAL DARK THEME FIXES
       These override Streamlit's default light theme
       ============================================ */
    
    /* NUCLEAR OPTION - Force all backgrounds dark */
    html, body, 
    html body .stApp,
    html body [data-testid="stAppViewContainer"],
    html body section.main,
    html body .main,
    html body .block-container,
    #root, #root > div {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%) !important;
        background-color: #0a0a0a !important;
    }
    
    /* Remove any border/glow effects */
    .stApp::before, .stApp::after,
    [data-testid="stAppViewContainer"]::before, 
    [data-testid="stAppViewContainer"]::after {
        display: none !important;
        content: none !important;
    }
    
    /* Main app container - DARK background */
    .stApp {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%) !important;
    }

    
    /* Main content area - ALL containers */
    .main, 
    .main > div,
    .block-container,
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"],
    .stMain,
    section.main,
    section.main > div,
    .stApp > section {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Force main app view dark */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%) !important;
    }
    

    /* Header bar - HIDE the glow/white bar at top */
    header[data-testid="stHeader"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Decoration element (the gradient bar at top) - HIDE */
    [data-testid="stDecoration"] {
        display: none !important;
        background: none !important;
    }
    
    /* Toolbar */
    [data-testid="stToolbar"] {
        background: transparent !important;
    }
    
    /* Sidebar - DARK */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div,
    [data-testid="stSidebar"] > div:first-child {
        background: linear-gradient(180deg, rgba(15, 15, 25, 0.98) 0%, rgba(10, 10, 20, 1) 100%) !important;
    }
    
    /* OPTION MENU - Navigation box fix */
    .menu-title, .menu-icon,
    nav.nav, .nav-link,
    [data-testid="stSidebar"] .stRadio,
    [data-testid="stSidebar"] [data-baseweb] {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Global Styles */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: #1a1a1a;
    }
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #1DB954, #1ed760);
        border-radius: 4px;
    }
    

    /* Main Header with Gradient */
    .main-header {
        font-size: 64px;
        font-weight: 800;
        text-align: center;
        background: linear-gradient(135deg, #1DB954, #1ed760, #00ff88, #00d4ff);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 3s ease-in-out infinite;
        margin-bottom: 48px;
        text-shadow: 0 0 30px rgba(29, 185, 84, 0.3);
    }
    
    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* Sub Header with Glow */
    .sub-header {
        font-size: 32px;
        font-weight: 600;
        background: linear-gradient(45deg, #1DB954, #1ed760);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 32px;
        text-shadow: 0 0 20px rgba(29, 185, 84, 0.2);
    }
    
    /* Ultra-Modern Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #2d3748, #4a5568);
        color: #ffffff;
        padding: 32px;
        border-radius: 20px;
        border: 1px solid rgba(29, 185, 84, 0.2);
        box-shadow: 
            0 20px 40px rgba(0, 0, 0, 0.3),
            0 0 0 1px rgba(29, 185, 84, 0.1),
            inset 0 1px 0 rgba(255, 255, 255, 0.1);
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        backdrop-filter: blur(10px);
    }
    
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(29, 185, 84, 0.1), transparent);
        transition: left 0.5s;
    }
    
    .metric-card:hover {
        transform: translateY(-10px) scale(1.02);
        box-shadow: 
            0 30px 60px rgba(0, 0, 0, 0.4),
            0 0 0 1px rgba(29, 185, 84, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
        border-color: rgba(29, 185, 84, 0.4);
    }
    
    .metric-card:hover::before {
        left: 100%;
    }
    
    .metric-card h3 {
        color: #1DB954;
        margin-bottom: 24px;
        font-size: 22px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        position: relative;
    }
    
    .metric-card h3::after {
        content: '';
        position: absolute;
        bottom: -5px;
        left: 0;
        width: 30px;
        height: 3px;
        background: linear-gradient(45deg, #1DB954, #1ed760);
        border-radius: 2px;
    }
    
    .metric-card p {
        color: #e2e8f0;
        margin-bottom: 13px;
        font-size: 16px;
        font-weight: 400;
        transition: color 0.3s ease;
    }
    
    .metric-card:hover p {
        color: #ffffff;
    }
    
    .metric-card strong {
        color: #ffffff;
        font-weight: 600;
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }
    
    /* Animated Success/Error Messages */
    .success-message {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        color: #155724;
        padding: 24px;
        border-radius: 15px;
        border: 1px solid #c3e6cb;
        box-shadow: 0 10px 30px rgba(21, 87, 36, 0.2);
        animation: slideInUp 0.5s ease-out;
    }
    
    .error-message {
        background: linear-gradient(135deg, #f8d7da, #f5c6cb);
        color: #721c24;
        padding: 24px;
        border-radius: 15px;
        border: 1px solid #f5c6cb;
        box-shadow: 0 10px 30px rgba(114, 28, 36, 0.2);
        animation: slideInUp 0.5s ease-out;
    }
    
    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Ultra-Modern Quick Action Buttons */
    .quick-action-btn {
        background: linear-gradient(135deg, #1DB954, #1ed760);
        color: white;
        border: none;
        padding: 16px 32px;
        border-radius: 15px;
        font-weight: 600;
        font-size: 18px;
        cursor: pointer;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        margin: 13px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(29, 185, 84, 0.3);
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .quick-action-btn::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
        transition: left 0.5s;
    }
    
    .quick-action-btn:hover {
        background: linear-gradient(135deg, #1ed760, #00ff88);
        transform: translateY(-5px) scale(1.05);
        box-shadow: 0 20px 40px rgba(29, 185, 84, 0.4);
    }
    
    .quick-action-btn:hover::before {
        left: 100%;
    }
    
    .quick-action-btn:active {
        transform: translateY(-2px) scale(1.02);
    }
    
    /* Enhanced Streamlit Button Styling */
    .stButton > button {
        background: linear-gradient(135deg, #1DB954, #1ed760) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        padding: 16px 32px !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        box-shadow: 0 10px 30px rgba(29, 185, 84, 0.3) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        position: relative !important;
        overflow: hidden !important;
    }
    
    .stButton > button::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: -100% !important;
        width: 100% !important;
        height: 100% !important;
        background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent) !important;
        transition: left 0.5s !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #1ed760, #00ff88) !important;
        transform: translateY(-5px) scale(1.05) !important;
        box-shadow: 0 20px 40px rgba(29, 185, 84, 0.4) !important;
    }
    
    .stButton > button:hover::before {
        left: 100% !important;
    }
    
    .stButton > button:active {
        transform: translateY(-2px) scale(1.02) !important;
    }
    
    /* Modern Form Styling - Container only */
    .stSelectbox, .stTextInput, .stNumberInput {
        background: transparent !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    /* TextInput inner element styling */
    .stTextInput > div > div > input {
        background: #2d3748 !important;
        border: 1px solid rgba(100, 100, 100, 0.4) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        padding: 12px 16px !important;
        font-size: 15px !important;
        box-shadow: none !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: rgba(255, 255, 255, 0.5) !important;
    }
    
    .stTextInput > div > div > input:hover {
        border-color: #1DB954 !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #1DB954 !important;
        outline: none !important;
    }
    
    /* Remove TextInput container borders */
    .stTextInput > div,
    .stTextInput > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Custom Track Count Styling */
    .stRadio > div {
        background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8)) !important;
        border-radius: 15px !important;
        padding: 16px !important;
        border: 1px solid rgba(29, 185, 84, 0.2) !important;
    }
    
    .stRadio > div > label {
        color: white !important;
        font-weight: 600 !important;
    }
    
    .stRadio > div > label:hover {
        color: #1DB954 !important;
    }
    
    .stNumberInput > div > input {
        background: #2d3748 !important;
        border: 1px solid rgba(100, 100, 100, 0.4) !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        text-align: center !important;
        box-shadow: none !important;
    }
    
    .stNumberInput > div > input:focus {
        border-color: #1DB954 !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Remove ghosting from NumberInput containers */
    .stNumberInput,
    .stNumberInput > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* ===== SELECTBOX STYLING - SINGLE SOURCE OF TRUTH ===== */
    /* Only style the actual clickable element, not parent containers */
    .stSelectbox > div > div > div[data-baseweb="select"] > div:first-child,
    .stSelectbox > div > div > div {
        background: #2d3748 !important;
        border: 1px solid rgba(100, 100, 100, 0.4) !important;
        border-radius: 12px !important;
        color: #ffffff !important;
        transition: border-color 0.2s ease !important;
        padding: 12px 16px !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
        line-height: 1.4 !important;
        font-size: 15px !important;
        box-shadow: none !important;
    }
    
    /* Ensure dropdown selected text is always visible */
    .stSelectbox > div > div > div > div,
    .stSelectbox > div > div > div > div > div,
    .stSelectbox > div > div > div > div > div > div,
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div,
    .stSelectbox [data-testid="stMarkdownContainer"],
    .stSelectbox div[data-baseweb="select"] div[aria-selected] {
        color: #ffffff !important;
    }
    
    /* Force visibility on the value placeholder */
    .stSelectbox [data-baseweb="select"] > div:first-child {
        color: #ffffff !important;
    }
    .stSelectbox [data-baseweb="select"] > div:first-child > div {
        color: #ffffff !important;
    }
    .stSelectbox [data-baseweb="select"] > div:first-child > div > div {
        color: #ffffff !important;
    }
    
    .stSelectbox > div > div > div:hover {
        border-color: #1DB954 !important;
    }
    
    .stSelectbox > div > div > div:focus-within {
        border-color: #1DB954 !important;
        outline: none !important;
    }
    
    /* Remove any inherited borders from parent elements */
    .stSelectbox,
    .stSelectbox > div,
    .stSelectbox > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Fix dropdown text visibility - ensure text is fully shown */
    .stSelectbox > div > div > div > div {
        padding: 8px 0 !important;
        line-height: 1.4 !important;
        min-height: 40px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* Ensure dropdown options are fully visible */
    .stSelectbox > div > div > div > div > div {
        padding: 10px 0 !important;
        line-height: 1.4 !important;
        min-height: 45px !important;
    }
    
    /* Enhanced dropdown options styling for better visibility */
    .stSelectbox > div > div > div > div > div > div {
        padding: 10px 0 !important;
        line-height: 1.4 !important;
        min-height: 45px !important;
    }
    
    /* Enhanced Form Spacing */
    .stForm > div {
        padding: 0 !important;
    }
    
    /* Better Column Spacing */
    .row-widget.stHorizontal > div {
        gap: 48px !important;
        padding: 0 16px !important;
    }
    
    /* Enhanced form element spacing */
    .stForm > div > div {
        margin-bottom: 32px !important;
    }
    
    /* Better input field spacing - compact for single viewport */
    .stSelectbox, .stTextArea, .stRadio, .stSlider, .stNumberInput {
        margin-bottom: 24px !important;
    }
    
    /* Compact form layout */
    .stForm > div > div {
        margin-bottom: 16px !important;
    }
    
    /* Enhanced Text Area - Clean single-layer styling */
    .stTextArea > div > div > textarea {
        background: #2d3748 !important;
        border: 1px solid rgba(100, 100, 100, 0.4) !important;
        border-radius: 12px !important;
        color: white !important;
        padding: 16px !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        transition: border-color 0.2s ease !important;
        box-shadow: none !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #1DB954 !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    .stTextArea > div > div > textarea:hover {
        border-color: #1DB954 !important;
    }
    
    /* Remove inherited styles from TextArea containers */
    .stTextArea,
    .stTextArea > div,
    .stTextArea > div > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* ===== DROPDOWN Z-INDEX & OVERFLOW FIX ===== */
    /* Fix 1: Z-Index for dropdown menus to appear above all elements */
    [data-baseweb="popover"] {
        z-index: 999999 !important;
    }
    
    [data-baseweb="menu"],
    [data-baseweb="select"] > div:last-child {
        z-index: 999999 !important;
    }
    
    /* The dropdown list container */
    .stSelectbox [data-baseweb="popover"],
    .stSelectbox ul,
    .stSelectbox [role="listbox"] {
        z-index: 999999 !important;
        position: relative !important;
    }
    
    /* Fix 2: Overflow visible on all parent containers */
    .stSelectbox {
        margin-bottom: 16px !important;
        overflow: visible !important;
        position: relative !important;
    }
    
    .stSelectbox > div,
    .stSelectbox > div > div,
    .stSelectbox > div > div > div {
        overflow: visible !important;
    }
    
    /* Fix 3: Form containers must not clip dropdowns */
    .stForm,
    .stForm > div,
    .stForm > div > div,
    [data-testid="stForm"],
    [data-testid="column"],
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"] {
        overflow: visible !important;
    }
    
    /* Main content area overflow fix */
    .main .block-container,
    .main .block-container > div,
    section[data-testid="stSidebar"] ~ div {
        overflow: visible !important;
    }
    

    

    

    
    /* Consolidated dropdown text visibility */
    
    /* Fix dropdown arrow positioning */
    .stSelectbox > div > div > div > div:last-child {
        margin-left: auto !important;
        padding-left: 8px !important;
    }
    
    /* Ensure dropdown text has enough space */
    .stSelectbox > div > div > div > div:first-child {
        flex: 1 !important;
        padding-right: 8px !important;
        min-height: 56px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        overflow: visible !important;
        word-wrap: break-word !important;
        white-space: normal !important;
        padding-top: 5px !important;
        padding-bottom: 5px !important;
    }
    
    /* Ensure dropdown text content is fully visible */
    .stSelectbox > div > div > div > div:first-child > div {
        width: 100% !important;
        text-align: left !important;
        padding: 3px 0 !important;
        line-height: 1.4 !important;
        overflow: visible !important;
    }
    
    /* Force override Streamlit's internal text clipping */
    .stSelectbox > div > div > div > div:first-child > div > div {
        padding: 5px 0 !important;
        line-height: 1.6 !important;
        min-height: 45px !important;
        display: flex !important;
        align-items: center !important;
        overflow: visible !important;
        text-overflow: unset !important;
        white-space: normal !important;
        word-break: normal !important;
    }
    
    /* Hover effects only on the actual input elements, not containers */
    
    /* Animated Background */
    .main {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
        background-size: 400% 400% !important;
        animation: backgroundShift 15s ease-in-out infinite !important;
    }
    
    @keyframes backgroundShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* Sidebar Styling - Removed unstable selectors */
    /* Navigation Menu Styling - Removed unstable selectors */
    
    /* Page Container Improvements */
    .main .block-container {
        padding-top: 48px !important;
        padding-bottom: 48px !important;
        max-width: 1400px !important;
    }
    
    /* Dashboard Section Spacing */
    .dashboard-section {
        margin-bottom: 48px !important;
        animation: fadeInUp 0.8s ease-out !important;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header {
            font-size: 40px;
        }
        .sub-header {
            font-size: 24px;
        }
        .metric-card {
            padding: 24px;
            margin-bottom: 16px;
        }
    }
    
    /* Loading Animation */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid rgba(29, 185, 84, 0.3);
        border-radius: 50%;
        border-top-color: #1DB954;
        animation: spin 1s ease-in-out infinite;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
    
    /* Floating Action Button */
    .fab {
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #1DB954, #1ed760);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 24px;
        box-shadow: 0 10px 30px rgba(29, 185, 84, 0.4);
        cursor: pointer;
        transition: all 0.3s ease;
        z-index: 1000;
    }
    
    .fab:hover {
        transform: scale(1.1);
        box-shadow: 0 15px 40px rgba(29, 185, 84, 0.6);
    }
    
    /* Interactive Card Effects */
    .interactive-card {
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
    }
    
    .interactive-card:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
    }
    
    /* Pulse Animation for Important Elements */
    .pulse {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Glow Effect for Active Elements */
    .glow {
        box-shadow: 0 0 20px rgba(29, 185, 84, 0.5);
        animation: glow 2s ease-in-out infinite alternate;
    }
    
    @keyframes glow {
        from { box-shadow: 0 0 20px rgba(29, 185, 84, 0.5); }
        to { box-shadow: 0 0 30px rgba(29, 185, 84, 0.8); }
    }
    
    /* Smooth Page Transitions */
    .page-transition {
        animation: fadeIn 0.8s ease-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* Modern Input Focus Effects */
    .stSelectbox > div > div:focus,
    .stTextInput > div > div:focus,
    .stNumberInput > div > div:focus {
        border-color: #1DB954 !important;
        box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    
    /* Enhanced Button States */
    .stButton > button:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.3) !important;
    }
    
    /* Loading States */
    .loading-state {
        opacity: 0.7;
        pointer-events: none;
        transition: all 0.3s ease;
    }
    
    /* Success States */
    .success-state {
        animation: successPulse 0.6s ease-out;
    }
    
    @keyframes successPulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    /* FRESH NEW DESIGN - Modern Card Styling */
    .stMarkdown > div {
        transition: all 0.3s ease !important;
    }
    
    .stMarkdown > div:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4) !important;
    }
    
    /* Enhanced Form Elements for Fresh Design */
    .stSelectbox > div > div > div {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05)) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 15px !important;
        padding: 19px 24px !important;
        font-size: 16px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stSelectbox > div > div > div:hover {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.1)) !important;
        border-color: rgba(29, 185, 84, 0.6) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(29, 185, 84, 0.3) !important;
    }
    
    /* TextArea styling consolidated above */
    
    .stRadio > div > label {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05)) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 12px !important;
        padding: 13px 19px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stRadio > div > label:hover {
        background: linear-gradient(145deg, rgba(29, 185, 84, 0.2), rgba(46, 204, 113, 0.1)) !important;
        border-color: rgba(29, 185, 84, 0.6) !important;
        transform: translateY(-2px) !important;
    }
    
    .stSlider > div > div > div > div {
        background: linear-gradient(90deg, #1DB954, #46CD73) !important;
    }
    
    /* NumberInput styling consolidated above */
    
    /* Submit Button Enhancement for Fresh Design */
    .stButton > button {
        background: linear-gradient(135deg, #1DB954, #46CD73, #2ECC71) !important;
        border: none !important;
        border-radius: 25px !important;
        padding: 16px 32px !important;
        font-size: 19px !important;
        font-weight: 700 !important;
        color: white !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 8px 25px rgba(29, 185, 84, 0.3) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 15px 35px rgba(29, 185, 84, 0.5) !important;
        background: linear-gradient(135deg, #46CD73, #2ECC71, #27AE60) !important;
    }
    
    /* CSS Animations for Fresh Design */
    @keyframes float {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-20px) rotate(180deg); }
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 0.6; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.1); }
    }
</style>

<script>
// Interactive JavaScript for enhanced user experience
document.addEventListener('DOMContentLoaded', function() {
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Add hover effects to metric cards
    document.querySelectorAll('.metric-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Add click effects to buttons
    document.querySelectorAll('.stButton button').forEach(button => {
        button.addEventListener('click', function() {
            this.classList.add('success-state');
            setTimeout(() => {
                this.classList.remove('success-state');
            }, 600);
        });
    });
    
    // Add loading states
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.classList.add('loading-state');
                submitBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
            }
        });
    });
    
    // Add floating action button functionality
    const fab = document.querySelector('.fab');
    if (fab) {
        fab.addEventListener('click', function() {
            // Trigger playlist generation
            const playlistBtn = document.querySelector('button[data-testid="baseButton-secondary"]');
            if (playlistBtn) {
                playlistBtn.click();
            }
        });
    }
    
    // Add smooth animations for page elements
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('page-transition');
            }
        });
    }, observerOptions);
    
    // Observe all major sections
    document.querySelectorAll('h1, h2, h3, .metric-card, .stButton').forEach(el => {
        observer.observe(el);
    });
});
</script>
""", unsafe_allow_html=True)

def load_premium_css():
    """Load premium CSS from external file for world-class UI"""
    import os
    css_path = os.path.join(os.path.dirname(__file__), 'styles', 'premium.css')
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            premium_css = f.read()
            st.markdown(f'<style>{premium_css}</style>', unsafe_allow_html=True)

def check_workflow_ready():
    """Check if the workflow is ready to execute"""
    try:
        workflow = MultiAgentWorkflow()
        return workflow.is_ready(), workflow
    except Exception as e:
        st.error(f"Failed to initialize workflow: {str(e)}")
        return False, None

def show_credentials_warning():
    """Show a warning about missing credentials"""
    st.warning("⚠️ **API Credentials Required**")
    st.markdown("""
    To use TuneGenie, you need to set up your API credentials:
    
    1. **Create a `.env` file** in the project directory
    2. **Add your API keys:**
       ```env
       SPOTIFY_CLIENT_ID=your_spotify_client_id
       SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
       SPOTIFY_REDIRECT_URI=http://127.0.0.1:8501/callback
       OPENAI_API_KEY=your_openai_api_key
       ```
    3. **Restart the application**
    
    See `QUICKSTART.md` for detailed setup instructions.
    """)
    
    if st.button("📖 View Quick Start Guide"):
        with open('QUICKSTART.md', 'r') as f:
            st.markdown(f.read())

def main():
    """Main application function"""
    
    # Load environment variables
    load_dotenv()
    
    # Load premium CSS for world-class UI
    load_premium_css()
    
    # Initialize security (telemetry + optional license enforcement)
    ok, message = initialize_security()
    if not ok:
        st.error(f"🚫 License check failed: {message}")
        st.stop()
    
    # Main header with gradient
    st.markdown('<h1 class="main-header">🎵 TuneGenie</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #e2e8f0; font-size: 19px; margin-bottom: 32px;">AI-Powered Music Recommendation System</p>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        # If some action wants to programmatically change the navigation,
        # handle it via default_index for option_menu
        nav_target = st.session_state.pop("nav_target", None)
        nav_options = ["Dashboard", "Generate Playlist", "User Analysis", "AI Insights", "Settings", "Performance"]
        
        # Calculate default index based on nav_target or session state
        default_idx = 0
        if nav_target:
            target_map = {
                "🏠 Dashboard": 0, "🎯 Generate Playlist": 1, "📊 User Analysis": 2,
                "🤖 AI Insights": 3, "⚙️ Settings": 4, "📈 Performance": 5
            }
            default_idx = target_map.get(nav_target, 0)
        
        # Clean option_menu navigation (no radio buttons)
        selected = option_menu(
            menu_title="Navigation",
            options=nav_options,
            icons=["house-fill", "music-note-list", "bar-chart-line-fill", "robot", "gear-fill", "graph-up-arrow"],
            menu_icon="compass",
            default_index=default_idx,
            styles={
                "container": {
                    "padding": "8px !important", 
                    "background-color": "transparent !important",
                    "border": "none !important"
                },
                "icon": {"color": "#1DB954", "font-size": "18px"},
                "nav-link": {
                    "font-size": "15px",
                    "text-align": "left",
                    "margin": "4px 0",
                    "padding": "12px 16px",
                    "border-radius": "10px",
                    "color": "#e2e8f0",
                    "background-color": "rgba(30, 35, 50, 0.6)",
                    "--hover-color": "rgba(29, 185, 84, 0.2)",
                },
                "nav-link-selected": {
                    "background-color": "rgba(29, 185, 84, 0.3)",
                    "color": "#1DB954",
                    "font-weight": "600",
                },
                "menu-title": {
                    "color": "#1DB954",
                    "font-size": "18px",
                    "font-weight": "700",
                    "margin-bottom": "16px",
                    "background-color": "transparent !important",
                    "padding": "8px 16px",
                }
            }
        )

        
        # Map back to full names with emojis for content routing
        selected_map = {
            "Dashboard": "🏠 Dashboard",
            "Generate Playlist": "🎯 Generate Playlist", 
            "User Analysis": "📊 User Analysis",
            "AI Insights": "🤖 AI Insights",
            "Settings": "⚙️ Settings",
            "Performance": "📈 Performance"
        }
        selected = selected_map.get(selected, "🏠 Dashboard")
        
        st.markdown("---")
        st.markdown("### 🔗 Quick Actions")
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
        
        if st.button("📥 Export Data"):
            export_user_data()
    
    # NOTE: Navigation is driven solely by `st.radio(key="main_nav")`.
    # Avoid additional override flags here; they can cause confusing "snap back"
    # behavior across Streamlit reruns if they linger in session_state.
    
    # Main content based on selection
    if selected == "🏠 Dashboard":
        show_dashboard()
    elif selected == "🎯 Generate Playlist":
        show_playlist_generation()
    elif selected == "📊 User Analysis":
        show_user_analysis()
    elif selected == "🤖 AI Insights":
        show_ai_insights()
    elif selected == "⚙️ Settings":
        show_settings()
    elif selected == "📈 Performance":
        show_performance()

def show_dashboard():
    """Display the main dashboard"""
    st.markdown('<h2 class="sub-header">Dashboard</h2>', unsafe_allow_html=True)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Get workflow status
        status = workflow.get_workflow_status()
        
        # Display status cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <h3>🎵 Spotify Status</h3>
                <p><strong>Status:</strong> {}</p>
                <p><strong>Authenticated:</strong> {}</p>
            </div>
            """.format(
                status['spotify_client']['status'],
                "✅ Yes" if status['spotify_client']['authenticated'] else "❌ No"
            ), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <h3>🤖 AI Model</h3>
                <p><strong>Algorithm:</strong> {}</p>
                <p><strong>Trained:</strong> {}</p>
                <p><strong>Model Files:</strong> {}</p>
                <p><strong>Training Data:</strong> {} interactions</p>
            </div>
            """.format(
                status['recommender'].get('algorithm', 'N/A'),
                "✅ Yes" if status['recommender'].get('is_trained', False) else "❌ No",
                status['recommender'].get('model_files_count', 0),
                status['recommender'].get('training_data_size', 0)
            ), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <h3>💬 LLM Agent</h3>
                <p><strong>Model:</strong> {}</p>
                <p><strong>Status:</strong> ✅ Active</p>
            </div>
            """.format(
                status['llm_agent'].get('model_name', 'N/A')
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <h3>⚡ Workflows</h3>
                <p><strong>Total:</strong> {}</p>
                <p><strong>Recent:</strong> {}</p>
            </div>
            """.format(
                status['workflow_history']['total_executions'],
                len(status['workflow_history']['recent_executions'])
            ), unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("## 🚀 Quick Actions")
        
        # Add floating action button
        st.markdown("""
        <div class="fab" onclick="document.querySelector('.stButton button').click()">
            🎵
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🎵 Generate Mood Playlist", key="quick_playlist"):
                st.session_state["nav_target"] = "🎯 Generate Playlist"
                st.rerun()
        
        with col2:
            if st.button("📊 Analyze Profile", key="quick_analyze"):
                st.session_state["nav_target"] = "📊 User Analysis"
                st.rerun()
        
        with col3:
            if st.button("🤖 Ask AI", key="quick_ai"):
                st.session_state["nav_target"] = "🤖 AI Insights"
                st.rerun()
        
        # Recent activity
        if status['workflow_history']['recent_executions']:
            st.markdown("## 📋 Recent Activity")
            
            # Workflow type icons mapping
            workflow_icons = {
                'playlist_generation': '🎵',
                'user_analysis': '👤',
                'ai_insights': '💬',
                'recommendation': '🎯',
                'default': '⚡'
            }
            
            for execution in status['workflow_history']['recent_executions'][-5:]:
                wf_type = execution['workflow_type']
                icon = workflow_icons.get(wf_type, workflow_icons['default'])
                # Format timestamp nicely
                timestamp = execution['start_time'][:19].replace('T', ' ')
                with st.expander(f"{icon} {wf_type} - {timestamp}"):
                    st.json(execution)
        
    except Exception as e:
        st.error(f"Failed to load dashboard: {str(e)}")
        st.info("Please check your API credentials and try again.")

def show_playlist_generation():
    """Display playlist generation interface"""
    # Show which strategy is active (feature flag)
    llm_driven_flag = os.getenv('FEATURE_FLAG_LLM_DRIVEN', 'False').strip().lower() in ('1','true','yes','on')
    strategy_banner = "🤖 LLM-Driven mode is ENABLED" if llm_driven_flag else "🧮 Collaborative Filtering (CF-First) mode"
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # CSS for form alignment and clean styling
        st.markdown("""
        <style>
        /* ===== TRACK COUNT TOGGLE STYLING ===== */
        /* Hide radio button circles */
        .stRadio > div[role="radiogroup"] > label > div:first-child {
            display: none !important;
        }
        /* Make radio containers transparent */
        .stRadio, .stRadio > div {
            background: transparent !important;
        }
        /* Radio button group layout */
        .stRadio > div[role="radiogroup"] {
            background: transparent !important;
            display: flex !important;
            flex-direction: row !important;
            gap: 8px !important;
        }
        /* Individual toggle buttons - default state */
        .stRadio > div[role="radiogroup"] > label {
            background: rgba(45, 55, 72, 0.5) !important;
            border: 1px solid rgba(100, 100, 100, 0.4) !important;
            border-radius: 10px !important;
            padding: 10px 16px !important;
            margin: 0 !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            flex: 1 !important;
            text-align: center !important;
        }
        /* Hover state */
        .stRadio > div[role="radiogroup"] > label:hover {
            border-color: #1DB954 !important;
            background: rgba(29, 185, 84, 0.15) !important;
        }
        /* Active/Selected state - multiple selector approaches for compatibility */
        .stRadio > div[role="radiogroup"] > label:has(input:checked),
        .stRadio > div[role="radiogroup"] > label[data-baseweb="radio"][aria-checked="true"],
        .stRadio > div[role="radiogroup"] label[aria-checked="true"] {
            background: rgba(29, 185, 84, 0.3) !important;
            border-color: #1DB954 !important;
            box-shadow: 0 0 0 1px rgba(29, 185, 84, 0.2) !important;
        }
        /* Form section headers */
        .section-title {
            color: #1DB954;
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(29, 185, 84, 0.3);
        }
        /* Consistent input heights */
        .stSelectbox, .stTextInput {
            margin-bottom: 12px !important;
        }
        /* Consistent column backgrounds */
        [data-testid="column"], [data-testid="stVerticalBlock"] {
            background: transparent !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Page Header
        st.markdown('<h2 class="sub-header">🎯 Generate Your Perfect Playlist</h2>', unsafe_allow_html=True)
        st.caption(strategy_banner)
        st.markdown('<p style="color: #a0aec0; margin-bottom: 24px;">Let TuneGenie create the perfect soundtrack for your mood, activity, and preferences</p>', unsafe_allow_html=True)
        
        # Initialize session state for track count method if not exists
        if 'track_count_method' not in st.session_state:
            st.session_state.track_count_method = "Quick Select"
        
        # Main Form Container
        with st.form("playlist_generation_form"):
            # Three-Column Layout with equal widths
            col1, col2, col3 = st.columns([1, 1, 1])
            
            # ===== COLUMN 1: MOOD & CONTEXT =====
            with col1:
                st.markdown('<p class="section-title">😊 Mood & Context</p>', unsafe_allow_html=True)
                
                mood = st.selectbox(
                    "Mood",
                    ["Happy", "Sad", "Energetic", "Calm", "Focused", "Relaxed", "Motivated", "Melancholic", "Excited", "Peaceful"],
                    key="mood_select",
                    label_visibility="collapsed"
                )
                
                user_context = st.text_input(
                    "Context",
                    placeholder="What are you doing? (optional)",
                    key="context_input",
                    label_visibility="collapsed"
                )
                
                keywords_input = st.text_input(
                    "Keywords",
                    placeholder="artist: name, genre: pop (optional)",
                    value="",
                    key="keywords_input",
                    label_visibility="collapsed"
                )
            
            # ===== COLUMN 2: ACTIVITY & LANGUAGE =====
            with col2:
                st.markdown('<p class="section-title">🏃 Activity & Language</p>', unsafe_allow_html=True)
                
                activity = st.selectbox(
                    "Activity",
                    ["Working", "Exercising", "Studying", "Commuting", "Cooking", "Cleaning", "Socializing", "Meditating", "Creative Work", "Relaxing"],
                    key="activity_select",
                    label_visibility="collapsed"
                )
                
                language_preference = st.selectbox(
                    "Language",
                    ["Any Language", "English", "Tamil", "Telugu", "Hindi", "Kannada", "Malayalam", "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Spanish", "French", "German", "Italian", "Portuguese", "Korean", "Japanese", "Chinese", "Arabic", "Russian"],
                    key="language_select",
                    label_visibility="collapsed"
                )
                
                # Language info (only show if specific language selected)
                if language_preference != "Any Language":
                    st.caption(f"🌍 {language_preference} tracks prioritized")
            
            # ===== COLUMN 3: TRACK COUNT =====
            with col3:
                st.markdown('<p class="section-title">🎯 Track Count</p>', unsafe_allow_html=True)
                
                # Use hidden number input to capture value since radio can't trigger form rerenders
                # We'll use buttons styled as toggles outside the form idea, but simpler:
                # Just show both options with proper styling based on session state
                # Note: Radio inside form won't rerender until submit, so we use a workaround
                
                # Display current mode selection info
                current_method = st.session_state.track_count_method
                st.caption(f"Mode: {current_method} (switch below form)")
                
                # Show appropriate input based on session state
                if st.session_state.track_count_method == "Quick Select":
                    n_recommendations = st.slider(
                        "Tracks", 
                        min_value=UI_DEFAULTS['TRACK_COUNT_MIN_QUICK'], 
                        max_value=UI_DEFAULTS['TRACK_COUNT_MAX_QUICK'], 
                        value=UI_DEFAULTS['TRACK_COUNT_DEFAULT'], 
                        step=UI_DEFAULTS['TRACK_COUNT_STEP_QUICK'], 
                        key="tracks_slider",
                        label_visibility="collapsed"
                    )
                else:
                    n_recommendations = st.number_input(
                        "Custom Tracks", 
                        min_value=UI_DEFAULTS['TRACK_COUNT_MIN_CUSTOM'], 
                        max_value=UI_DEFAULTS['TRACK_COUNT_MAX_CUSTOM'], 
                        value=UI_DEFAULTS['TRACK_COUNT_DEFAULT'], 
                        step=1, 
                        key="tracks_custom_input",
                        label_visibility="collapsed",
                        help=f"Enter any number from {UI_DEFAULTS['TRACK_COUNT_MIN_CUSTOM']} to {UI_DEFAULTS['TRACK_COUNT_MAX_CUSTOM']}"
                    )
            
            # Summary row
            st.markdown("---")
            st.markdown("**Your Selection:**")
            sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
            with sum_col1:
                st.metric("Mood", mood)
            with sum_col2:
                st.metric("Activity", activity)
            with sum_col3:
                st.metric("Language", language_preference if language_preference != "Any Language" else "Any")
            with sum_col4:
                st.metric("Tracks", n_recommendations)
            
            if keywords_input.strip():
                st.caption(f"🔍 Keywords: {keywords_input}")
            
            # Advanced Settings Expander
            with st.expander("Advanced Settings"):
                must_be_instrumental = st.checkbox("Must be instrumental", value=False)
                search_strictness = st.slider(
                    "Search Strictness (0 = broad, 2 = strict)", min_value=0, max_value=2, value=1,
                    help="Maps to Progressive Relaxation stages: 2=strict, 1=relaxed, 0=broad"
                )

            # Submit button
            submit_button = st.form_submit_button(
                "🚀 Generate My Perfect Playlist",
                type="primary"
            )
        
        # Track count mode toggle (outside form for dynamic switching)
        st.markdown("---")
        st.markdown("**🎯 Switch Track Count Mode:**")
        
        # CSS for consistent toggle button sizing
        st.markdown("""
        <style>
        /* ===== TOGGLE BUTTON SIZING FIX ===== */
        /* Target the toggle button columns specifically */
        [data-testid="column"]:has(button[kind="secondary"]) button,
        [data-testid="column"]:has(button[kind="primary"]) button {
            min-height: 48px !important;
            height: 48px !important;
            max-height: 48px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 16px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        toggle_col1, toggle_col2, toggle_col3 = st.columns([1, 1, 2])
        with toggle_col1:
            if st.button(
                f"🎚️ Slider ({UI_DEFAULTS['TRACK_COUNT_MIN_QUICK']}-{UI_DEFAULTS['TRACK_COUNT_MAX_QUICK']})",
                key="quick_select_btn",
                type="secondary" if st.session_state.track_count_method == "Custom" else "primary",
                use_container_width=True
            ):
                st.session_state.track_count_method = "Quick Select"
                st.rerun()
        with toggle_col2:
            if st.button(
                f"✏️ Custom ({UI_DEFAULTS['TRACK_COUNT_MIN_CUSTOM']}-{UI_DEFAULTS['TRACK_COUNT_MAX_CUSTOM']})",
                key="custom_btn", 
                type="secondary" if st.session_state.track_count_method == "Quick Select" else "primary",
                use_container_width=True
            ):
                st.session_state.track_count_method = "Custom"
                st.rerun()
        with toggle_col3:
            st.caption(f"Current mode: **{st.session_state.track_count_method}**")
        
        # Results and feedback section (outside the form)
        if submit_button:
            # Modern loading animation
            with st.spinner("🎵 TuneGenie is crafting your perfect playlist..."):
                try:
                    # Execute playlist generation workflow
                    # Use IntentClassifier for strategy selection
                    # Frontend Capture: log all user inputs for this request
                    try:
                        logger.info("FrontendCapture | inputs=%s", json.dumps({
                            'mood': mood,
                            'activity': activity,
                            'keywords': keywords_input,
                            'language_preference': language_preference,
                            'must_be_instrumental': must_be_instrumental,
                            'search_strictness': search_strictness,
                            'num_tracks': n_recommendations
                        }, ensure_ascii=False))
                    except Exception:
                        pass
                    intent = IntentClassifier()
                    # Intent Classification: log inputs and decision
                    try:
                        logger.info("IntentClassification | keywords=%s", (keywords_input or ''))
                    except Exception:
                        pass
                    strategy = intent.classify(keywords_input or '')
                    try:
                        logger.info("IntentClassification | strategy=%s", strategy)
                    except Exception:
                        pass
                    result = workflow.execute_workflow(
                        'playlist_generation',
                        mood=mood,
                        activity=activity,
                        user_context=user_context,
                        num_tracks=n_recommendations,
                        language_preference=language_preference,
                        keywords=keywords_input,
                        must_be_instrumental=must_be_instrumental,
                        search_strictness=search_strictness,
                        strategy=strategy
                    )
                    
                    if 'error' not in result:
                        # Success message with tracks added vs generated
                        generated = len(result.get('final_playlist', {}).get('tracks', []) or [])
                        added = int(result.get('spotify_playlist', {}).get('tracks_added', 0) or 0)
                        if added == generated and generated > 0:
                            st.success(f"🎉 Playlist Generated Successfully! Added {added}/{generated} tracks to Spotify.")
                        else:
                            st.warning(f"✅ Playlist generated. Added {added}/{generated} tracks to Spotify.")

                        # Display any warnings from backend
                        warnings_list = result.get('warnings', []) or []
                        for w in warnings_list:
                            st.warning(f"⚠️ {w}")
                        
                        # Display results
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            # Indicate active strategy in UI
                            strategy_label = ("Niche" if strategy == 'niche_query' else ("LLM-Driven" if (os.getenv('FEATURE_FLAG_LLM_DRIVEN', 'False').strip().lower() in ('1','true','yes','on')) else "CF-First"))
                            st.markdown(f'<h3 style="color: #1DB954; margin-bottom: 16px;">📋 Generated Playlist ({strategy_label})</h3>', unsafe_allow_html=True)
                            
                            if 'spotify_playlist' in result and 'spotify_url' in result['spotify_playlist']:
                                playlist_name = result['final_playlist'].get('playlist_name', 'TuneGenie Playlist')
                                
                                # Display playlist info
                                st.info(f"🎵 **{playlist_name}**")
                                st.info(f"🌍 **Language:** {language_preference if language_preference != 'Any Language' else 'Mixed Languages'}")
                                st.info(f"🎵 **Tracks:** {len(result['final_playlist'].get('tracks', []))} / {n_recommendations} requested")
                                st.info(f"😊 **Mood:** {mood} | 🏃‍♂️ **Activity:** {activity}")
                                
                                # Spotify link
                                st.markdown(f"[🎵 Open in Spotify]({result['spotify_playlist']['spotify_url']})")
                                
                                # Display tracks
                                if 'tracks' in result['final_playlist']:
                                    st.markdown('<h4 style="color: #1DB954; margin: 16px 0;">📝 Track List</h4>', unsafe_allow_html=True)
                                    
                                    tracks = result['final_playlist']['tracks']
                                    for i, track in enumerate(tracks[:10], 1):  # Show first 10 tracks
                                        st.write(f"{i}. **{track.get('name', 'Unknown Track')}** by {', '.join(track.get('artists', ['Unknown Artist']))}")
                                    
                                    if len(tracks) > 10:
                                        st.info(f"📋 Showing first 10 of {len(tracks)} tracks. View all tracks in Spotify!")
                            else:
                                st.warning("⚠️ Playlist was generated but couldn't be saved to Spotify. Check your credentials.")
                        
                        with col2:
                            st.markdown('<h3 style="color: #1DB954; margin-bottom: 16px;">📊 Generation Stats</h3>', unsafe_allow_html=True)
                            
                            # Display workflow stats
                            if 'workflow_stats' in result:
                                stats = result['workflow_stats']
                                st.metric("Collaborative Tracks", stats.get('collaborative_tracks', 0))
                                st.metric("AI-Enhanced Tracks", stats.get('ai_enhanced_tracks', 0))
                                st.metric("Total Processing Time", f"{stats.get('total_time', 0):.2f}s")

                            # Keyword validation summary
                            kv = result.get('keyword_validation', {}) or {}
                            if kv.get('enabled'):
                                st.markdown('<h4 style="color: #1DB954; margin-top: 16px;">🔎 Keyword Match</h4>', unsafe_allow_html=True)
                                st.metric("Coverage", f"{int((kv.get('coverage_score', 0)*100))}%")
                                st.caption(f"Matched {kv.get('matched_terms', 0)} of {kv.get('total_terms', 0)} terms")
                                unmet = kv.get('unmet_keywords', [])
                                if unmet:
                                    st.warning("Unmet keywords: " + ", ".join(unmet[:5]))
                                examples = kv.get('examples', [])
                                if examples:
                                    st.caption("Examples:")
                                    for ex in examples[:3]:
                                        st.caption(f"- {ex.get('keyword')}: {ex.get('track')} by {', '.join(ex.get('artists', []) or [])}")
                        
                        # Feedback section
                        st.markdown("---")
                        st.markdown('<h3 style="color: #1DB954; text-align: center; margin: 32px 0;">💬 How was your playlist?</h3>', unsafe_allow_html=True)
                        
                        feedback_col1, feedback_col2, feedback_col3 = st.columns(3)
                        
                        with feedback_col1:
                            if st.button("👍 Loved it!", key="feedback_love"):
                                save_feedback(result, "positive")
                                st.success("Thanks for the feedback! We'll use this to improve your recommendations.")
                        
                        with feedback_col2:
                            if st.button("😐 It's okay", key="feedback_ok"):
                                save_feedback(result, "neutral")
                                st.info("Thanks for the feedback! We'll work on making it better.")
                        
                        with feedback_col3:
                            if st.button("👎 Not great", key="feedback_dislike"):
                                save_feedback(result, "negative")
                                st.warning("Thanks for the feedback! We'll learn from this to improve.")
                    
                    else:
                        st.error(f"❌ Failed to generate playlist: {result['error']}")
                
                except Exception as e:
                    st.error(f"❌ An error occurred: {str(e)}")
        
    except Exception as e:
        st.error(f"Failed to initialize playlist generation: {str(e)}")

def show_user_analysis():
    """Display user analysis interface"""
    st.markdown('<h2 class="sub-header">📊 User Profile Analysis</h2>', unsafe_allow_html=True)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Analysis options
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### 🎵 Analyze your music profile")
            st.markdown("Get insights into your listening habits, favorite genres, and music preferences.")
        
        with col2:
            run_analysis = st.button("🔍 Run Analysis")
        
        # Check if analysis has been run before (show empty state if not)
        if 'user_analysis_results' not in st.session_state and not run_analysis:
            # Empty state placeholder
            st.markdown("---")
            empty_col1, empty_col2, empty_col3 = st.columns([1, 2, 1])
            with empty_col2:
                st.markdown("""
                <div style="text-align: center; padding: 60px 20px; background: rgba(29, 185, 84, 0.05); border-radius: 16px; border: 1px dashed rgba(29, 185, 84, 0.3);">
                    <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
                    <h3 style="color: #1DB954; margin-bottom: 12px;">No Analysis Data Yet</h3>
                    <p style="color: #888; margin-bottom: 20px;">Click <strong>"Run Analysis"</strong> above to generate insights from your listening history.</p>
                    <p style="color: #666; font-size: 0.9rem;">We'll analyze your:</p>
                    <ul style="color: #888; text-align: left; display: inline-block; margin-top: 8px;">
                        <li>🎭 Top genres and artists</li>
                        <li>📈 Listening patterns</li>
                        <li>🎵 Audio feature preferences</li>
                        <li>⏱️ Activity by time of day</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            return
        
        if run_analysis:
                with st.spinner("📊 Analyzing your music profile..."):
                    try:
                        # Execute user analysis workflow
                        result = workflow.execute_workflow('user_analysis', export_data=True)
                        
                        if 'error' not in result:
                            st.success("✅ Profile analysis completed!")
                            
                            # Display analysis results
                            if 'analysis' in result:
                                analysis = result['analysis']
                                
                                # Metrics cards
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Total Tracks", analysis.get('total_tracks_analyzed', 0))
                                
                                with col2:
                                    st.metric("Top Genres", len(analysis.get('top_genres', [])))
                                
                                with col3:
                                    st.metric("Listening Patterns", analysis.get('preferences_summary', {}).get('listening_consistency', 0))
                                
                                with col4:
                                    st.metric("Playlists", analysis.get('preferences_summary', {}).get('playlist_count', 0))
                                
                                # Top genres
                                if 'top_genres' in analysis:
                                    st.markdown("### 🎭 Top Genres")
                                    genres_df = pd.DataFrame({
                                        'Genre': analysis['top_genres'][:10],
                                        'Rank': range(1, min(11, len(analysis['top_genres']) + 1))
                                    })
                                    st.dataframe(genres_df)
                                
                                # Listening patterns
                                if 'listening_patterns' in analysis:
                                    st.markdown("### 📈 Listening Patterns")
                                    patterns_df = pd.DataFrame([
                                        {
                                            'Time Range': time_range.replace('_', ' ').title(),
                                            'Track Count': data.get('track_count', 0),
                                            'Avg Popularity': f"{data.get('avg_popularity', 0):.1f}"
                                        }
                                        for time_range, data in analysis['listening_patterns'].items()
                                    ])
                                    st.dataframe(patterns_df)
                                
                                # Create visualization
                                st.markdown("### 📊 Profile Visualization")
                                try:
                                    # Create user profile chart
                                    fig = create_user_profile_chart(analysis)
                                    st.plotly_chart(fig)
                                except Exception as e:
                                    st.warning(f"Could not create visualization: {str(e)}")
                                    
                                # Create additional visualizations
                                try:
                                    # Top Genres Chart
                                    if 'top_genres' in analysis and analysis['top_genres']:
                                        st.markdown("### 🎭 Top Genres Distribution")
                                        genres_fig = create_genres_chart(analysis['top_genres'])
                                        st.plotly_chart(genres_fig)
                                    
                                    # Listening Patterns Chart
                                    if 'listening_patterns' in analysis and analysis['listening_patterns']:
                                        st.markdown("### 📈 Listening Patterns Over Time")
                                        patterns_fig = create_listening_patterns_chart(analysis['listening_patterns'])
                                        st.plotly_chart(patterns_fig)
                                        
                                except Exception as e:
                                    st.warning(f"Could not create additional visualizations: {str(e)}")
                            
                        else:
                            st.error(f"❌ Analysis failed: {result['error']}")
                    
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
        
    except Exception as e:
        st.error(f"Failed to initialize user analysis: {str(e)}")

def show_ai_insights():
    """Display AI insights interface"""
    st.markdown('<h2 class="sub-header">🤖 AI Music Insights</h2>', unsafe_allow_html=True)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Enhanced AI chat interface
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8));
            border: 1px solid rgba(29, 185, 84, 0.3);
            border-radius: 20px;
            padding: 32px;
            margin: 32px 0;
            backdrop-filter: blur(10px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        ">
        """, unsafe_allow_html=True)
        
        st.markdown('<h3 style="color: #1DB954; text-align: center; margin-bottom: 32px;">💬 Ask TuneGenie anything about music!</h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #e2e8f0; margin-bottom: 32px;">Get personalized music recommendations, learn about artists and genres, or ask for music advice.</p>', unsafe_allow_html=True)
        
        # Enhanced chat input with examples
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_query = st.text_area(
                "Your question about music:",
                placeholder="e.g., 'What music should I listen to while studying?', 'Tell me about jazz fusion', 'Recommend upbeat songs for working out'",
                height=100,
                key="ai_insight_input"
            )
        
        with col2:
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, rgba(29, 185, 84, 0.1), rgba(30, 215, 96, 0.1));
                border: 1px solid rgba(29, 185, 84, 0.2);
                border-radius: 15px;
                padding: 16px;
                margin-top: 16px;
            ">
                <h4 style="color: #1DB954; margin: 0 0 8px 0;">💡 Try asking about:</h4>
                <ul style="color: #e2e8f0; margin: 0; padding-left: 19px; font-size: 14px;">
                    <li>Moods & emotions</li>
                    <li>Activities & situations</li>
                    <li>Genres & styles</li>
                    <li>Artists & bands</li>
                    <li>Music discovery</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Enhanced submit button
        if st.button("🤖 Ask AI", disabled=not user_query.strip(), type="primary"):
            if user_query.strip():
                try:
                    # Get conversation history for follow-up context
                    chat_history = st.session_state.get('chat_history', [])
                    
                    # Get user context for personalized responses
                    user_context = ""
                    user_context_dict = {}
                    user_id = "anonymous"
                    try:
                        user_context = workflow.get_user_context_for_ai()
                        # Get user ID and context dict for enhanced insights
                        user_profile = workflow.spotify_client.get_user_profile()
                        user_id = user_profile.get('id', 'anonymous')
                        user_context_dict = {
                            'top_artists': workflow.spotify_client.get_user_top_artists(20) if hasattr(workflow.spotify_client, 'get_user_top_artists') else [],
                            'top_tracks': workflow.spotify_client.get_user_top_tracks(20) if hasattr(workflow.spotify_client, 'get_user_top_tracks') else [],
                            'profile': user_profile
                        }
                    except Exception as e:
                        # Continue without personalization if it fails
                        pass
                    
                    # Display response header
                    st.markdown("### 💡 AI Response")
                    
                    # =========================================================
                    # TRY ENHANCED INSIGHTS FIRST (with reasoning & memory)
                    # =========================================================
                    enhanced_result = None
                    reasoning_steps = []
                    confidence = 0.7
                    sources = []
                    memory_stats = None
                    
                    try:
                        # Check if enhanced method is available
                        if hasattr(workflow.llm_agent, 'get_music_insights_enhanced') and workflow.llm_agent.enhanced_enabled:
                            enhanced_result = workflow.llm_agent.get_music_insights_enhanced(
                                question=user_query,
                                user_id=user_id,
                                context=user_context_dict,
                                spotify_client=workflow.spotify_client,
                                show_reasoning=True
                            )
                            
                            if enhanced_result and 'response' in enhanced_result:
                                full_response_text = enhanced_result.get('response', '')
                                reasoning_steps = enhanced_result.get('reasoning_steps', [])
                                confidence = enhanced_result.get('confidence', 0.7)
                                sources = enhanced_result.get('sources', [])
                                memory_stats = enhanced_result.get('memory_stats')
                                
                                # Determine model attribution
                                if enhanced_result.get('enhanced'):
                                    model_used = "TuneGenie AI (Enhanced)"
                                else:
                                    model_used = "TuneGenie AI"
                    except Exception as enhanced_error:
                        logger.warning(f"Enhanced insights failed, falling back to standard: {enhanced_error}")
                        enhanced_result = None
                    
                    # =========================================================
                    # DISPLAY ENHANCED RESPONSE IF AVAILABLE
                    # =========================================================
                    if enhanced_result and enhanced_result.get('response'):
                        # Display the main response with premium styling
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(135deg, rgba(45, 55, 72, 0.9), rgba(74, 85, 104, 0.9));
                            border: 1px solid rgba(29, 185, 84, 0.4);
                            border-radius: 15px;
                            padding: 24px;
                            margin: 16px 0;
                            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                        ">
                            <p style="color: #ffffff; line-height: 1.8; margin: 0; font-size: 1.05rem;">{full_response_text}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Display confidence and model info
                        info_cols = st.columns([2, 2, 2])
                        with info_cols[0]:
                            st.caption(f"🤖 Generated by {model_used}")
                        with info_cols[1]:
                            confidence_color = "#1DB954" if confidence >= 0.7 else "#FFD700" if confidence >= 0.4 else "#FF6B6B"
                            st.caption(f"🎯 Confidence: <span style='color:{confidence_color}'>{confidence:.0%}</span>", unsafe_allow_html=True)
                        with info_cols[2]:
                            if sources:
                                st.caption(f"📚 Sources: {', '.join(sources[:3])}")
                        
                        # Display reasoning steps (collapsible)
                        if reasoning_steps:
                            with st.expander("🧠 View Reasoning Steps", expanded=False):
                                for i, step in enumerate(reasoning_steps, 1):
                                    st.markdown(f"""
                                    <div style="
                                        background: rgba(29, 185, 84, 0.1);
                                        border-left: 3px solid #1DB954;
                                        padding: 10px 15px;
                                        margin: 8px 0;
                                        border-radius: 0 8px 8px 0;
                                    ">
                                        <strong>Step {i}:</strong> {step}
                                    </div>
                                    """, unsafe_allow_html=True)
                        
                        # Display memory stats (collapsible)
                        if memory_stats:
                            with st.expander("💾 Memory Stats", expanded=False):
                                st.json(memory_stats)
                    
                    # =========================================================
                    # FALLBACK TO STANDARD STREAMING IF ENHANCED FAILED
                    # =========================================================
                    elif enhanced_result is None or not enhanced_result.get('response'):
                        # Initialize response text and model info
                        full_response_text = ""
                        model_used = "Unknown"
                        
                        # Create placeholder for streaming response
                        response_placeholder = st.empty()
                        
                        # Stream the response
                        try:
                            # Get streaming generator
                            stream_generator = workflow.llm_agent.get_music_insights_stream(
                                question=user_query,
                                user_context=user_context,
                                conversation_history=chat_history
                            )
                            
                            # Determine model type for attribution
                            if workflow.llm_agent.model_type == "openai":
                                model_used = f"OpenAI ({workflow.llm_agent.model_name})"
                            else:
                                model_used = "Hugging Face (Free)"
                        
                        # Stream and display chunks in real-time
                        for chunk in stream_generator:
                            if chunk:
                                full_response_text += chunk
                                # Update the display with streaming text in real-time
                                response_placeholder.markdown(f"""
                                <div style="
                                    background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8));
                                    border: 1px solid rgba(29, 185, 84, 0.3);
                                    border-radius: 15px;
                                    padding: 24px;
                                    margin: 16px 0;
                                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                                ">
                                    <p style="color: #ffffff; line-height: 1.6; margin: 0;">{full_response_text}</p>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Final update to ensure complete text is displayed
                        if full_response_text.strip():
                            response_placeholder.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8));
                                border: 1px solid rgba(29, 185, 84, 0.3);
                                border-radius: 15px;
                                padding: 24px;
                                margin: 16px 0;
                                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                            ">
                                <p style="color: #ffffff; line-height: 1.6; margin: 0;">{full_response_text.strip()}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Model info
                            # Determine if personalized
                            if user_context and 'USER PROFILE' in user_context:
                                model_used = f"TuneGenie AI (Personalized)"
                            elif chat_history:
                                model_used = f"TuneGenie AI (Conversation Memory)"
                            
                            st.caption(f"🤖 Generated by {model_used}")
                        else:
                            st.error("❌ No response received from AI")
                            full_response_text = "No response received"
                            
                    except Exception as stream_error:
                        logger.error(f"Streaming error: {stream_error}")
                        # Fallback to non-streaming
                        try:
                            response = workflow.llm_agent.get_music_insights(
                                question=user_query,
                                user_context=user_context,
                                conversation_history=chat_history
                            )
                            
                            if 'error' in response:
                                st.error(f"❌ {response['error']}")
                                full_response_text = response.get('error', 'Error occurred')
                            else:
                                full_response_text = response.get('insight', 'No response received')
                                model_used = response.get('model_used', 'Unknown')
                                
                                st.markdown(f"""
                                <div style="
                                    background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8));
                                    border: 1px solid rgba(29, 185, 84, 0.3);
                                    border-radius: 15px;
                                    padding: 24px;
                                    margin: 16px 0;
                                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                                ">
                                    <p style="color: #ffffff; line-height: 1.6; margin: 0;">{full_response_text}</p>
                                </div>
                                """, unsafe_allow_html=True)
                                
                                st.caption(f"🤖 Generated by {model_used}")
                        except Exception as fallback_error:
                            st.error(f"❌ Failed to get AI response: {str(fallback_error)}")
                            full_response_text = f"Error: {str(fallback_error)}"
                        
                        # Save to chat history
                        if 'chat_history' not in st.session_state:
                            st.session_state.chat_history = []
                        
                        st.session_state.chat_history.append({
                            'query': user_query,
                            'response': full_response_text.strip() if full_response_text else 'No response received',
                            'timestamp': datetime.now().isoformat(),
                            'model': model_used
                        })
                        
                except Exception as e:
                    st.error(f"❌ Failed to get AI response: {str(e)}")
        
        # Enhanced chat history with modern styling
        if 'chat_history' in st.session_state and st.session_state.chat_history:
            st.markdown("---")
            st.markdown('<h3 style="color: #1DB954; margin: 32px 0 16px 0;">📝 Chat History</h3>', unsafe_allow_html=True)
            
            # Show last 5 conversations
            for i, chat in enumerate(reversed(st.session_state.chat_history[-5:])):
                with st.expander(f"💬 {chat['query'][:50]}{'...' if len(chat['query']) > 50 else ''} - {chat['timestamp'][:19]}", expanded=False):
                    st.markdown(f"""
                    <div style="
                        background: linear-gradient(135deg, rgba(45, 55, 72, 0.6), rgba(74, 85, 104, 0.6));
                        border: 1px solid rgba(29, 185, 84, 0.2);
                        border-radius: 10px;
                        padding: 16px;
                        margin: 8px 0;
                    ">
                        <p><strong>Question:</strong> {chat['query']}</p>
                        <p><strong>Answer:</strong> {chat['response']}</p>
                        <p style="color: #1DB954; font-size: 14px; margin: 8px 0 0 0;"><em>Model: {chat['model']}</em></p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Clear history button
            if st.button("🗑️ Clear Chat History", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
        
    except Exception as e:
        st.error(f"Failed to initialize AI insights: {str(e)}")
        st.info("Please check your API credentials and try again.")

def show_settings():
    """Display settings interface"""
    st.markdown('<h2 class="sub-header">⚙️ Settings & Configuration</h2>', unsafe_allow_html=True)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Settings tabs
        tab1, tab2, tab3 = st.tabs(["🔑 API Configuration", "🤖 Model Settings", "📊 Data Management"])
        
        with tab1:
            st.markdown("### 🔑 API Configuration")
            
            # Check current configuration
            spotify_status = workflow.get_workflow_status()['spotify_client']
            llm_status = workflow.get_workflow_status()['llm_agent']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Spotify API**")
                if spotify_status.get('authenticated', False):
                    st.success("✅ Connected")
                else:
                    st.error("❌ Not connected")
            
            with col2:
                st.markdown("**Environment Variables**")
                env_vars = {
                    'SPOTIFY_CLIENT_ID': os.getenv('SPOTIFY_CLIENT_ID'),
                    'SPOTIFY_CLIENT_SECRET': os.getenv('SPOTIFY_CLIENT_SECRET'),
                }
                
                for var, value in env_vars.items():
                    if value:
                        st.success(f"✅ {var}")
                    else:
                        st.error(f"❌ {var}")
            
            # ============================================
            # AI PROVIDERS STATUS (5 FREE providers)
            # ============================================
            st.markdown("---")
            st.markdown("### 🤖 AI Providers (All FREE)")
            st.markdown("*TuneGenie uses 5 free AI providers with automatic fallback for $0 cost*")
            
            # Define AI providers and their status
            ai_providers = [
                {
                    'name': 'Groq',
                    'env_key': 'GROQ_API_KEY',
                    'speed': '⚡ Ultra-fast',
                    'limit': '30/min, 14,400/day',
                    'priority': 1
                },
                {
                    'name': 'Google Gemini',
                    'env_key': 'GOOGLE_API_KEY',
                    'speed': '🚀 Fast',
                    'limit': '15/min, 1,500/day',
                    'priority': 2
                },
                {
                    'name': 'OpenRouter',
                    'env_key': 'OPENROUTER_API_KEY',
                    'speed': '🚀 Fast',
                    'limit': '20/min, Unlimited/day',
                    'priority': 3
                },
                {
                    'name': 'DeepSeek',
                    'env_key': 'DEEPSEEK_API_KEY',
                    'speed': '🚀 Fast',
                    'limit': '5M free tokens',
                    'priority': 4
                },
                {
                    'name': 'HuggingFace',
                    'env_key': 'HUGGINGFACE_TOKEN',
                    'speed': '🐢 Slow',
                    'limit': '10/min, 1,000/day',
                    'priority': 5
                }
            ]
            
            # Create columns for provider cards
            col1, col2, col3 = st.columns(3)
            cols = [col1, col2, col3]
            
            configured_count = 0
            for i, provider in enumerate(ai_providers):
                with cols[i % 3]:
                    key_value = os.getenv(provider['env_key'])
                    is_configured = bool(key_value)
                    if is_configured:
                        configured_count += 1
                    
                    status_icon = "✅" if is_configured else "❌"
                    status_color = "green" if is_configured else "red"
                    
                    st.markdown(f"""
                    <div style="border: 1px solid {status_color}; border-radius: 8px; padding: 10px; margin: 5px 0;">
                        <strong>{status_icon} {provider['name']}</strong><br>
                        <small>Priority: #{provider['priority']}</small><br>
                        <small>{provider['speed']}</small><br>
                        <small>Limit: {provider['limit']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Summary card
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Providers Configured", f"{configured_count}/5")
            with col2:
                st.metric("Monthly Cost", "$0.00")
            with col3:
                daily_capacity = 0
                if os.getenv('GROQ_API_KEY'):
                    daily_capacity += 14400
                if os.getenv('GOOGLE_API_KEY'):
                    daily_capacity += 1500
                if os.getenv('OPENROUTER_API_KEY'):
                    daily_capacity += 10000  # Conservative estimate
                if os.getenv('DEEPSEEK_API_KEY'):
                    daily_capacity += 5000
                if os.getenv('HUGGINGFACE_TOKEN'):
                    daily_capacity += 1000
                st.metric("Daily Capacity", f"~{daily_capacity:,} req")
            
            st.info("💡 All API keys are configured in `.env`. Priority order: Groq → Gemini → OpenRouter → DeepSeek → HuggingFace")

        
        with tab2:
            st.markdown("### 🤖 Model Settings")
            
            # Model information
            recommender_info = workflow.get_workflow_status()['recommender']
            llm_info = workflow.get_workflow_status()['llm_agent']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Collaborative Filtering**")
                st.markdown(f"**Algorithm:** {recommender_info.get('algorithm', 'N/A')}")
                st.markdown(f"**Trained:** {'✅ Yes' if recommender_info.get('is_trained', False) else '❌ No'}")
                st.markdown(f"**Users:** {recommender_info.get('user_count', 0)}")
                st.markdown(f"**Items:** {recommender_info.get('item_count', 0)}")
            
            with col2:
                st.markdown("**LLM Agent**")
                st.markdown(f"**Model:** {llm_info.get('model_name', 'N/A')}")
                st.markdown(f"**Temperature:** {llm_info.get('temperature', 'N/A')}")
                st.markdown(f"**Prompts:** {len(llm_info.get('available_prompts', []))}")
            
            # Model training
            st.markdown("### 🏋️ Model Training")
            
            if st.button("🔄 Retrain Model"):
                with st.spinner("🏋️ Training model..."):
                    try:
                        result = workflow.execute_workflow('model_training', cross_validate=True)
                        
                        if 'error' not in result:
                            st.success("✅ Model training completed!")
                            st.json(result)
                        else:
                            st.error(f"❌ Training failed: {result['error']}")
                    
                    except Exception as e:
                        st.error(f"❌ Training error: {str(e)}")
        
        with tab3:
            st.markdown("### 📊 Data Management")
            
            # Data export/import
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Export Data**")
                if st.button("📥 Export User Data"):
                    try:
                        result = workflow.execute_workflow('user_analysis', export_data=True)
                        if 'error' not in result:
                            st.success("✅ Data exported successfully!")
                        else:
                            st.error(f"❌ Export failed: {result['error']}")
                    except Exception as e:
                        st.error(f"❌ Export error: {str(e)}")
            
            with col2:
                st.markdown("**Clear Data**")
                if st.button("🗑️ Clear Session Data"):
                    if 'chat_history' in st.session_state:
                        del st.session_state.chat_history
                    st.success("✅ Session data cleared!")
            
            # Data files
            st.markdown("### 📁 Data Files")
            
            data_dir = 'data'
            if os.path.exists(data_dir):
                files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
                
                if files:
                    for file in files:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{file}**")
                        
                        with col2:
                            if st.button(f"📊 View", key=f"view_{file}"):
                                data = FileManager.load_json(file)
                                if data:
                                    st.json(data)
                        
                        with col3:
                            if st.button(f"🗑️ Delete", key=f"delete_{file}"):
                                try:
                                    os.remove(os.path.join(data_dir, file))
                                    st.success(f"✅ {file} deleted!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to delete {file}: {str(e)}")
                else:
                    st.info("No data files found.")
            else:
                st.info("Data directory not found.")
        
    except Exception as e:
        st.error(f"Failed to initialize settings: {str(e)}")

def show_performance():
    """Display performance metrics interface"""
    st.markdown('<h2 class="sub-header">📈 Performance & Analytics</h2>', unsafe_allow_html=True)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Performance overview
        st.markdown("### 📊 Performance Overview")
        
        # Get workflow status and history
        status = workflow.get_workflow_status()
        workflow_history = status['workflow_history']['recent_executions']
        
        if workflow_history:
            # Calculate metrics
            metrics = MetricsCalculator.calculate_performance_metrics(workflow_history)
            
            # Display metrics - use total_executions from status (same as Dashboard)
            total_executions = status['workflow_history'].get('total_executions', len(workflow_history))
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Executions", total_executions)
            
            with col2:
                st.metric("Success Rate", f"{metrics.get('success_rate', 0):.1%}")
            
            with col3:
                st.metric("Avg Execution Time", f"{metrics.get('avg_execution_time', 0):.2f}s")
            
            with col4:
                st.metric("Error Rate", f"{metrics.get('error_rate', 0):.1%}")
            
            # Workflow distribution
            if 'workflow_distribution' in metrics:
                st.markdown("### 🔄 Workflow Distribution")
                
                workflow_df = pd.DataFrame([
                    {'Workflow': wf, 'Count': count}
                    for wf, count in metrics['workflow_distribution'].items()
                ])
                
                if not workflow_df.empty:
                    # Use Plotly for better label control and styling
                    fig = go.Figure(data=[
                        go.Bar(
                            x=workflow_df['Workflow'],
                            y=workflow_df['Count'],
                            marker=dict(
                                color=workflow_df['Count'],
                                colorscale=[[0, '#1DB954'], [1, '#00D9FF']],
                                line=dict(color='rgba(29, 185, 84, 0.8)', width=1)
                            ),
                            text=workflow_df['Count'],
                            textposition='auto',
                            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
                        )
                    ])
                    fig.update_layout(
                        title=dict(text=''),  # Empty title to prevent undefined
                        showlegend=False,
                        xaxis_title="Workflow Type",
                        yaxis_title="Execution Count",
                        xaxis_tickangle=-45,  # Rotate labels to prevent clipping
                        margin=dict(b=120, t=10, l=60, r=20),  # Reduced top margin
                        height=400,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        xaxis=dict(
                            tickfont=dict(size=11),
                            gridcolor='rgba(255,255,255,0.1)'
                        ),
                        yaxis=dict(
                            gridcolor='rgba(255,255,255,0.1)'
                        )
                    )
                    st.plotly_chart(fig, use_container_width=True)

            
            # Performance visualization
            st.markdown("### 📈 Performance Charts")
            
            try:
                # Create a simple performance chart
                if workflow_history:
                    # Extract execution times
                    execution_times = []
                    for record in workflow_history:
                        if 'duration' in record:
                            # Use duration field if available
                            execution_times.append(record['duration'])
                        elif 'start_time' in record and 'end_time' in record:
                            try:
                                start = datetime.fromisoformat(record['start_time'])
                                end = datetime.fromisoformat(record['end_time'])
                                duration = (end - start).total_seconds()
                                execution_times.append(duration)
                            except:
                                continue
                    
                    if execution_times:
                        # Create histogram of execution times with dark theme
                        fig = go.Figure(data=[go.Histogram(
                            x=execution_times, 
                            nbinsx=10,
                            marker=dict(
                                color='rgba(0, 217, 255, 0.7)',
                                line=dict(color='rgba(29, 185, 84, 0.8)', width=1)
                            )
                        )])
                        fig.update_layout(
                            title=dict(text=''),  # Empty title to prevent undefined
                            showlegend=False,
                            xaxis_title="Execution Time (seconds)",
                            yaxis_title="Frequency",
                            height=400,
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='white'),
                            xaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                tickfont=dict(color='white')
                            ),
                            yaxis=dict(
                                gridcolor='rgba(255,255,255,0.1)',
                                tickfont=dict(color='white')
                            ),
                            margin=dict(t=10, b=60, l=60, r=20)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No execution time data available for visualization")
                else:
                    st.info("No workflow history available for visualization")
                    
            except Exception as e:
                st.warning(f"Could not create performance chart: {str(e)}")
            
            # Recent executions table
            st.markdown("### 📋 Recent Executions")
            
            executions_df = pd.DataFrame([
                {
                    'Workflow': exec_record.get('workflow_type', 'Unknown'),
                    'Status': exec_record.get('status', 'Unknown'),
                    'Start Time': exec_record.get('start_time', 'Unknown')[:19] if exec_record.get('start_time') else 'N/A',
                    'Duration': f"{exec_record.get('duration', 0):.2f}s" if 'duration' in exec_record else 'N/A'
                }
                for exec_record in workflow_history[-10:]  # Last 10 executions
            ])
            
            st.dataframe(executions_df)
            
        else:
            st.info("No workflow executions found. Run some workflows to see performance data.")
        
        # Recommendation metrics (if available)
        st.markdown("### 🎯 Recommendation Quality")
        
        # This would require user feedback data
        st.info("Recommendation quality metrics will appear here once you provide feedback on generated playlists.")
        
    except Exception as e:
        st.error(f"Failed to initialize performance view: {str(e)}")

def save_feedback(playlist_result: dict, feedback_type: str):
    """Save user feedback for recommendations"""
    try:
        feedback_data = {
            'playlist_id': playlist_result.get('metadata', {}).get('generation_timestamp'),
            'feedback_type': feedback_type,
            'timestamp': datetime.now().isoformat(),
            'playlist_data': playlist_result
        }
        
        # Save feedback
        FileManager.save_json(feedback_data, f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'data')
        
    except Exception as e:
        logger.error(f"Failed to save feedback: {e}")

def create_user_profile_chart(analysis):
    """Create a comprehensive user profile chart"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Top Genres', 'Listening Patterns', 'Track Distribution', 'Popularity Overview'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Top Genres Pie Chart
        if 'top_genres' in analysis and analysis['top_genres']:
            genres = analysis['top_genres'][:8]  # Top 8 genres
            fig.add_trace(
                go.Pie(labels=genres, values=[1]*len(genres), name="Genres"),
                row=1, col=1
            )
        
        # Listening Patterns Bar Chart
        if 'listening_patterns' in analysis and analysis['listening_patterns']:
            time_ranges = list(analysis['listening_patterns'].keys())
            track_counts = [analysis['listening_patterns'][tr].get('track_count', 0) for tr in time_ranges]
            
            fig.add_trace(
                go.Bar(x=time_ranges, y=track_counts, name="Track Count"),
                row=1, col=2
            )
        
        # Track Distribution Scatter
        if 'listening_patterns' in analysis and analysis['listening_patterns']:
            time_ranges = list(analysis['listening_patterns'].keys())
            avg_popularity = [analysis['listening_patterns'][tr].get('avg_popularity', 0) for tr in time_ranges]
            
            fig.add_trace(
                go.Scatter(x=time_ranges, y=avg_popularity, mode='lines+markers', name="Avg Popularity"),
                row=2, col=1
            )
        
        # Popularity Overview
        if 'listening_patterns' in analysis and analysis['listening_patterns']:
            time_ranges = list(analysis['listening_patterns'].keys())
            track_counts = [analysis['listening_patterns'][tr].get('track_count', 0) for tr in time_ranges]
            
            fig.add_trace(
                go.Bar(x=time_ranges, y=track_counts, name="Total Tracks"),
                row=2, col=2
            )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            title_text="User Music Profile Overview",
            title_x=0.5
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Failed to create user profile chart: {e}")
        return None

def create_genres_chart(genres):
    """Create a genres distribution chart"""
    try:
        import plotly.graph_objects as go
        
        # Create horizontal bar chart
        fig = go.Figure(data=[
            go.Bar(
                x=[1] * len(genres),
                y=genres,
                orientation='h',
                marker_color='#1DB954'
            )
        ])
        
        fig.update_layout(
            title="Top Genres Distribution",
            xaxis_title="Frequency",
            yaxis_title="Genre",
            height=400,
            showlegend=False
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Failed to create genres chart: {e}")
        return None

def create_listening_patterns_chart(patterns):
    """Create a listening patterns chart"""
    try:
        import plotly.graph_objects as go
        
        time_ranges = list(patterns.keys())
        track_counts = [patterns[tr].get('track_count', 0) for tr in time_ranges]
        avg_popularity = [patterns[tr].get('avg_popularity', 0) for tr in time_ranges]
        
        # Create dual-axis chart
        fig = go.Figure()
        
        # Add track count bars
        fig.add_trace(go.Bar(
            x=time_ranges,
            y=track_counts,
            name='Track Count',
            yaxis='y',
            marker_color='#1DB954'
        ))
        
        # Add popularity line
        fig.add_trace(go.Scatter(
            x=time_ranges,
            y=avg_popularity,
            name='Avg Popularity',
            yaxis='y2',
            line=dict(color='#FF6B6B', width=3)
        ))
        
        fig.update_layout(
            title="Listening Patterns Over Time",
            xaxis_title="Time Range",
            yaxis=dict(title="Track Count", side="left"),
            yaxis2=dict(title="Average Popularity", side="right", overlaying="y"),
            height=400,
            showlegend=True
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Failed to create listening patterns chart: {e}")
        return None

def export_user_data():
    """Export user data"""
    try:
        workflow_ready, workflow = check_workflow_ready()
        if not workflow_ready:
            st.error("❌ Workflow not ready. Please check your API credentials.")
            return
            
        result = workflow.execute_workflow('user_analysis', export_data=True)
        
        if 'error' not in result:
            st.success("✅ User data exported successfully!")
        else:
            st.error(f"❌ Export failed: {result['error']}")
    
    except Exception as e:
        st.error(f"❌ Export error: {str(e)}")

if __name__ == "__main__":
    main()
