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

# Import TuneGenie components
from src.workflow import MultiAgentWorkflow
from src.intent_classifier import IntentClassifier
from src.utils import DataProcessor, Visualizer, FileManager, MetricsCalculator

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
    
    /* Modern Form Styling */
    .stSelectbox, .stTextInput, .stNumberInput {
        background: linear-gradient(135deg, #2d3748, #4a5568) !important;
        border: 1px solid rgba(29, 185, 84, 0.2) !important;
        border-radius: 10px !important;
        color: white !important;
        transition: all 0.3s ease !important;
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
        background: linear-gradient(135deg, #2d3748, #4a5568) !important;
        border: 2px solid rgba(29, 185, 84, 0.3) !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
        text-align: center !important;
    }
    
    .stNumberInput > div > input:focus {
        border-color: #1DB954 !important;
        box-shadow: 0 0 20px rgba(29, 185, 84, 0.3) !important;
    }
    
    /* Language Selection Styling */
    .stSelectbox > div > div > div {
        background: linear-gradient(135deg, #2d3748, #4a5568) !important;
        border: 2px solid rgba(29, 185, 84, 0.3) !important;
        border-radius: 12px !important;
        color: white !important;
        transition: all 0.3s ease !important;
        padding: 13px 16px !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
        line-height: 1.4 !important;
        font-size: 15px !important;
    }
    
    .stSelectbox > div > div > div:hover {
        border-color: #1DB954 !important;
        box-shadow: 0 0 15px rgba(29, 185, 84, 0.2) !important;
        transform: translateY(-2px) !important;
    }
    
    .stSelectbox > div > div > div:focus-within {
        border-color: #1DB954 !important;
        box-shadow: 0 0 20px rgba(29, 185, 84, 0.3) !important;
        transform: translateY(-1px) !important;
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
    
    /* Enhanced Text Area */
    .stTextArea > div > div > textarea {
        background: linear-gradient(135deg, #2d3748, #4a5568) !important;
        border: 2px solid rgba(29, 185, 84, 0.4) !important;
        border-radius: 15px !important;
        color: white !important;
        padding: 19px !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #1DB954 !important;
        box-shadow: 0 0 25px rgba(29, 185, 84, 0.4) !important;
        transform: translateY(-3px) scale(1.02) !important;
    }
    
    .stTextArea > div > div > textarea:hover {
        border-color: rgba(29, 185, 84, 0.6) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* Enhanced Dropdown Styling for all selectboxes */
    .stSelectbox {
        margin-bottom: 16px !important;
        overflow: visible !important;
    }
    
    /* Ensure dropdown container doesn't clip text */
    .stSelectbox > div {
        overflow: visible !important;
    }
    
    .stSelectbox > div > div {
        overflow: visible !important;
    }
    
    /* Complete override for text clipping - force text to be fully visible */
    .stSelectbox * {
        overflow: visible !important;
        text-overflow: unset !important;
        white-space: normal !important;
    }
    

    

    

    
    /* Ensure all dropdown text is fully visible */
    .stSelectbox > div > div > div {
        min-height: 61px !important;
        padding: 21px 29px !important;
        font-size: 17px !important;
        line-height: 1.5 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: space-between !important;
        overflow: visible !important;
        border-radius: 15px !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
    }
    
    .stSelectbox > div > div > div:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3) !important;
        border-color: rgba(29, 185, 84, 0.6) !important;
    }
    
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
    
    .stSelectbox:hover, .stTextInput:hover, .stNumberInput:hover {
        border-color: rgba(29, 185, 84, 0.4) !important;
        box-shadow: 0 5px 15px rgba(29, 185, 84, 0.2) !important;
    }
    
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
    
    /* Sidebar Styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e, #16213e) !important;
        border-right: 1px solid rgba(29, 185, 84, 0.2) !important;
    }
    
    /* Navigation Menu Styling */
    .css-1d391kg .css-1v0mbdj {
        background: linear-gradient(135deg, #1DB954, #1ed760) !important;
        border-radius: 10px !important;
        margin: 8px 0 !important;
        transition: all 0.3s ease !important;
    }
    
    .css-1d391kg .css-1v0mbdj:hover {
        transform: translateX(5px) !important;
        box-shadow: 0 5px 15px rgba(29, 185, 84, 0.3) !important;
    }
    
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
    
    .stTextArea > div > div > textarea {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05)) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 15px !important;
        padding: 19px !important;
        font-size: 16px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(29, 185, 84, 0.8) !important;
        box-shadow: 0 0 25px rgba(29, 185, 84, 0.4) !important;
        transform: translateY(-3px) !important;
    }
    
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
    
    .stNumberInput > div > input {
        background: linear-gradient(145deg, rgba(255, 255, 255, 0.15), rgba(255, 255, 255, 0.05)) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 15px !important;
        padding: 16px 19px !important;
        font-size: 16px !important;
        color: white !important;
        transition: all 0.3s ease !important;
    }
    
    .stNumberInput > div > input:focus {
        border-color: rgba(29, 185, 84, 0.8) !important;
        box-shadow: 0 0 25px rgba(29, 185, 84, 0.4) !important;
        transform: translateY(-2px) !important;
    }
    
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
    
    # Main header with gradient
    st.markdown('<h1 class="main-header">🎵 TuneGenie</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #e2e8f0; font-size: 19px; margin-bottom: 32px;">AI-Powered Music Recommendation System</p>', unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("## 🧭 Navigation")
        
        selected = option_menu(
            menu_title=None,
            options=["🏠 Dashboard", "🎯 Generate Playlist", "📊 User Analysis", "🤖 AI Insights", "⚙️ Settings", "📈 Performance"],
            icons=["house", "music-note", "bar-chart", "brain", "gear", "graph-up"],
            menu_icon="cast",
            default_index=0,
        )
        
        st.markdown("---")
        st.markdown("## 🔗 Quick Actions")
        
        if st.button("🔄 Refresh Data"):
            st.rerun()
        
        if st.button("📥 Export Data"):
            export_user_data()
    
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
                <h3>Spotify Status</h3>
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
                <h3>AI Model</h3>
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
                <h3>LLM Agent</h3>
                <p><strong>Model:</strong> {}</p>
                <p><strong>Status:</strong> ✅ Active</p>
            </div>
            """.format(
                status['llm_agent'].get('model_name', 'N/A')
            ), unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <h3>Workflows</h3>
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
                st.session_state.show_playlist_generation = True
                st.rerun()
        
        with col2:
            if st.button("📊 Analyze Profile", key="quick_analyze"):
                st.session_state.show_user_analysis = True
                st.rerun()
        
        with col3:
            if st.button("🤖 Ask AI", key="quick_ai"):
                st.session_state.show_ai_insights = True
                st.rerun()
        
        # Recent activity
        if status['workflow_history']['recent_executions']:
            st.markdown("## 📋 Recent Activity")
            
            for execution in status['workflow_history']['recent_executions'][-5:]:
                with st.expander(f"{execution['workflow_type']} - {execution['start_time'][:19]}"):
                    st.json(execution)
        
    except Exception as e:
        st.error(f"Failed to load dashboard: {str(e)}")
        st.info("Please check your API credentials and try again.")

def show_playlist_generation():
    """Display playlist generation interface"""
    # Show which strategy is active (feature flag)
    llm_driven_flag = os.getenv('FEATURE_FLAG_LLM_DRIVEN', 'False').strip().lower() in ('1','true','yes','on')
    strategy_banner = "🤖 LLM-Driven mode is ENABLED" if llm_driven_flag else "🧮 Collaborative Filtering (CF-First) mode"
    st.markdown(f'<h2 class="sub-header">🎯 Generate Personalized Playlist</h2>', unsafe_allow_html=True)
    st.caption(strategy_banner)
    
    # Check if workflow is ready
    workflow_ready, workflow = check_workflow_ready()
    
    if not workflow_ready:
        show_credentials_warning()
        return
    
    try:
        # Fresh global CSS for Generate Playlist
        st.markdown("""
        <style>
        /* ===== FRESH GENERATE PLAYLIST DESIGN SYSTEM ===== */
        .main-container {
            background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460);
            border-radius: 24px;
            padding: 48px;
            margin: 32px auto;
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            max-width: 1200px;
        }
        .main-title {
            color: #1DB954;
            text-align: center;
            margin-bottom: 48px;
            font-size: 42px;
            font-weight: 800;
            text-shadow: 0 4px 8px rgba(29,185,84,0.3);
        }
        .subtitle {
            color: #e2e8f0;
            text-align: center;
            margin-bottom: 40px;
            font-size: 22px;
            opacity: 0.9;
        }
        .form-container {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 40px;
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        .section-header {
            color: #1DB954;
            margin-bottom: 16px;
            font-size: 22px;
            font-weight: 700;
            text-align: left;
        }
        .spacing-div {
            margin: 24px 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(29,185,84,0.3), transparent);
        }
        /* Core widgets */
        .stSelectbox > div > div > div,
        .stNumberInput > div > input,
        .stTextArea > div > div > textarea {
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.35) !important;
            border-radius: 16px !important;
            color: #ffffff !important;
            padding: 20px 24px !important;
            font-size: 16px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.2) !important;
        }
        .stSelectbox > div > div > div { height: 72px !important; display: flex !important; align-items: center !important; border-radius: 16px !important; }
        .stSelectbox [data-baseweb="select"] > div { background: transparent !important; border: 0 !important; box-shadow: none !important; }
        .stSelectbox [role="combobox"] { background: transparent !important; border: 0 !important; box-shadow: none !important; }
        .stTextArea > div > div > textarea { height: 120px !important; line-height: 1.6 !important; resize: none !important; }
        .stRadio > div { background: rgba(255,255,255,0.05) !important; border-radius: 16px !important; padding: 20px !important; border: 1px solid rgba(255,255,255,0.1) !important; }
        
        /* Remove global select hover/jump styling */
        .stSelectbox > div > div > div:hover { transform: none !important; box-shadow: none !important; }
        .stSelectbox > div > div:hover { transform: none !important; box-shadow: none !important; }
        .stSelectbox > div > div > div { gap: initial !important; position: static !important; overflow: visible !important; }
        .stSelectbox > div > div > div > div { background: initial !important; border: initial !important; margin: initial !important; padding: initial !important; box-shadow: none !important; border-radius: initial !important; }
        .stSelectbox > div > div > div > div:last-child { background: initial !important; border-left: initial !important; margin-left: initial !important; padding-left: initial !important; }
        
        /* Mood select: style ONLY the outer wrapper div.stSelectbox (single capsule) */
        .stSelectbox[key="mood_select"] {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease !important;
            overflow: hidden !important;
        }
        .stSelectbox[key="mood_select"]:hover,
        .stSelectbox[key="mood_select"]:focus-within,
        .stSelectbox[key="mood_select"] [data-baseweb="select"]:hover,
        .stSelectbox[key="mood_select"] [data-baseweb="select"]:focus-within,
        div.stSelectbox:has(input[aria-label*="mood" i]):hover,
        div.stSelectbox:has(input[aria-label*="mood" i]):focus-within,
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"]:hover,
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"]:focus-within {
            border-color: #1DB954 !important;
            box-shadow: 0 0 0 3px rgba(29,185,84,0.30), 0 12px 28px rgba(0,0,0,0.35) !important;
            background: linear-gradient(135deg, #34455d, #566578) !important;
            transform: translateY(-4px) scale(1.01) !important;
        }
        /* Neutralize inner segments so they don't render their own boxes */
        .stSelectbox[key="mood_select"] > div,
        .stSelectbox[key="mood_select"] > div > div,
        .stSelectbox[key="mood_select"] [data-baseweb="select"],
        .stSelectbox[key="mood_select"] [data-baseweb="select"] > div,
        .stSelectbox[key="mood_select"] [role="combobox"] {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .stSelectbox[key="mood_select"] [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; }
        .stSelectbox[key="mood_select"] [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }

        /* Explicitly target the mood select wrapper via :has() to ensure override */
        div.stSelectbox:has(input[aria-label*="mood" i]) {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            overflow: hidden !important;
        }
        div.stSelectbox:has(input[aria-label*="mood" i]) * { box-shadow: none !important; }
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"],
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"] > div,
        div.stSelectbox:has(input[aria-label*="mood" i]) [role="combobox"],
        div.stSelectbox:has(input[aria-label*="mood" i]) > div,
        div.stSelectbox:has(input[aria-label*="mood" i]) > div > div,
        div.stSelectbox:has(input[aria-label*="mood" i]) > div > div > div {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"] { width: 100% !important; display: flex !important; align-items: center !important; }
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; padding-left: 16px !important; }
        div.stSelectbox:has(input[aria-label*="mood" i]) [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }

        /* ================= ACTIVITY SELECT: same single-capsule treatment ================= */
        .stSelectbox[key="activity_select"] {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease, transform 0.2s ease !important;
            will-change: transform, box-shadow;
            overflow: hidden !important;
        }
        .stSelectbox[key="activity_select"]:hover,
        .stSelectbox[key="activity_select"]:focus-within,
        .stSelectbox[key="activity_select"] [data-baseweb="select"]:hover,
        .stSelectbox[key="activity_select"] [data-baseweb="select"]:focus-within,
        div.stSelectbox:has(input[aria-label*="activity" i]):hover,
        div.stSelectbox:has(input[aria-label*="activity" i]):focus-within,
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"]:hover,
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"]:focus-within { 
            border-color: #1DB954 !important; 
            box-shadow: 0 0 0 3px rgba(29,185,84,0.30), 0 12px 28px rgba(0,0,0,0.35) !important; 
            background: linear-gradient(135deg, #34455d, #566578) !important; 
            transform: translateY(-4px) scale(1.01) !important;
        }
        .stSelectbox[key="activity_select"] > div,
        .stSelectbox[key="activity_select"] > div > div,
        .stSelectbox[key="activity_select"] [data-baseweb="select"],
        .stSelectbox[key="activity_select"] [data-baseweb="select"] > div,
        .stSelectbox[key="activity_select"] [role="combobox"] {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .stSelectbox[key="activity_select"] [data-baseweb="select"] { width: 100% !important; display: flex !important; align-items: center !important; }
        .stSelectbox[key="activity_select"] [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; padding-left: 16px !important; }
        .stSelectbox[key="activity_select"] [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }

        /* Robust aria-label based targeting as fallback */
        div.stSelectbox:has(input[aria-label*="activity" i]) {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease, transform 0.2s ease !important;
            will-change: transform, box-shadow;
            overflow: hidden !important;
        }
        div.stSelectbox:has(input[aria-label*="activity" i]) * { box-shadow: none !important; }
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"],
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"] > div,
        div.stSelectbox:has(input[aria-label*="activity" i]) [role="combobox"],
        div.stSelectbox:has(input[aria-label*="activity" i]) > div,
        div.stSelectbox:has(input[aria-label*="activity" i]) > div > div,
        div.stSelectbox:has(input[aria-label*="activity" i]) > div > div > div {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"] { width: 100% !important; display: flex !important; align-items: center !important; }
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; padding-left: 16px !important; }
        div.stSelectbox:has(input[aria-label*="activity" i]) [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }

        /* ================= LANGUAGE SELECT: same single-capsule treatment ================= */
        .stSelectbox[key="language_select"] {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease, transform 0.2s ease !important;
            will-change: transform, box-shadow;
            overflow: hidden !important;
        }
        .stSelectbox[key="language_select"]:hover,
        .stSelectbox[key="language_select"]:focus-within,
        .stSelectbox[key="language_select"] [data-baseweb="select"]:hover,
        .stSelectbox[key="language_select"] [data-baseweb="select"]:focus-within,
        div.stSelectbox:has(input[aria-label*="language" i]):hover,
        div.stSelectbox:has(input[aria-label*="language" i]):focus-within,
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"]:hover,
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"]:focus-within { 
            border-color: #1DB954 !important; 
            box-shadow: 0 0 0 3px rgba(29,185,84,0.30), 0 12px 28px rgba(0,0,0,0.35) !important; 
            background: linear-gradient(135deg, #34455d, #566578) !important; 
            transform: translateY(-4px) scale(1.01) !important;
        }
        .stSelectbox[key="language_select"] > div,
        .stSelectbox[key="language_select"] > div > div,
        .stSelectbox[key="language_select"] [data-baseweb="select"],
        .stSelectbox[key="language_select"] [data-baseweb="select"] > div,
        .stSelectbox[key="language_select"] [role="combobox"] {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            box-shadow: none !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .stSelectbox[key="language_select"] [data-baseweb="select"] { width: 100% !important; display: flex !important; align-items: center !important; }
        .stSelectbox[key="language_select"] [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; padding-left: 16px !important; }
        .stSelectbox[key="language_select"] [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }
        /* Fallback via aria-label */
        div.stSelectbox:has(input[aria-label*="language" i]) {
            height: 74px !important;
            border-radius: 16px !important;
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            display: flex !important;
            align-items: center !important;
            padding: 0 12px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease, transform 0.2s ease !important;
            will-change: transform, box-shadow;
            overflow: hidden !important;
        }
        div.stSelectbox:has(input[aria-label*="language" i]):hover,
        div.stSelectbox:has(input[aria-label*="language" i]):focus-within {
            border-color: #1DB954 !important;
            box-shadow: 0 0 0 3px rgba(29,185,84,0.30), 0 12px 28px rgba(0,0,0,0.35) !important;
            background: linear-gradient(135deg, #34455d, #566578) !important; 
            transform: translateY(-4px) scale(1.01) !important;
        }
        div.stSelectbox:has(input[aria-label*="language" i]) * { box-shadow: none !important; }
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"],
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"] > div,
        div.stSelectbox:has(input[aria-label*="language" i]) [role="combobox"],
        div.stSelectbox:has(input[aria-label*="language" i]) > div,
        div.stSelectbox:has(input[aria-label*="language" i]) > div > div,
        div.stSelectbox:has(input[aria-label*="language" i]) > div > div > div {
            background: transparent !important;
            border: 0 !important;
            border-radius: 0 !important;
            height: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"] { width: 100% !important; display: flex !important; align-items: center !important; }
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"] > div:first-child { flex: 1 1 auto !important; min-width: 0 !important; display: flex !important; align-items: center !important; padding-left: 16px !important; }
        div.stSelectbox:has(input[aria-label*="language" i]) [data-baseweb="select"] > div:last-child { width: 42px !important; display: flex !important; align-items: center !important; justify-content: center !important; }

        /* ================= CONTEXT TEXTAREA: single-capsule treatment ================= */
        .stTextArea[key="context_input"] > div {
            background: linear-gradient(135deg, #2d3748, #4a5568) !important;
            border: 2px solid rgba(29,185,84,0.45) !important;
            border-radius: 16px !important;
            min-height: 160px !important;
            padding: 16px !important;
            box-sizing: border-box !important;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25) !important;
            transition: box-shadow 0.25s ease, border-color 0.25s ease, background 0.25s ease, transform 0.2s ease !important;
            will-change: transform, box-shadow;
            overflow: hidden !important;
        }
        .stTextArea[key="context_input"] > div:hover,
        .stTextArea[key="context_input"] > div:focus-within {
            border-color: #1DB954 !important;
            box-shadow: 0 0 0 3px rgba(29,185,84,0.30), 0 12px 28px rgba(0,0,0,0.35) !important;
            background: linear-gradient(135deg, #34455d, #566578) !important;
            transform: translateY(-3px) scale(1.01) !important;
        }
        /* Neutralize inner wrappers and textarea so no double boxes */
        .stTextArea[key="context_input"] > div > div { background: transparent !important; border: 0 !important; box-shadow: none !important; }
        .stTextArea[key="context_input"] textarea {
            background: transparent !important;
            border: 0 !important;
            box-shadow: none !important;
            color: #ffffff !important;
            font-size: 16px !important;
            line-height: 1.6 !important;
            width: 100% !important;
            height: 100% !important;
            resize: vertical !important;
            padding: 0 !important;
        }
        .stButton > button {
            background: linear-gradient(135deg, #1DB954, #46CD73) !important;
            color: white !important;
            border: none !important;
            border-radius: 20px !important;
            padding: 20px 40px !important;
            font-size: 18px !important;
            font-weight: 700 !important;
            width: 100% !important;
            height: 72px !important;
            box-shadow: 0 8px 24px rgba(29,185,84,0.3) !important;
            cursor: pointer !important;
        }
        .summary-section { background: rgba(255,255,255,0.05); border-radius: 20px; padding: 32px; margin-top: 40px; border: 1px solid rgba(255,255,255,0.1); }
        .summary-header { color: #1DB954; text-align: center; margin-bottom: 24px; font-size: 24px; font-weight: 700; }
        .metric-card { background: linear-gradient(135deg, #2d3748, #4a5568); border-radius: 16px; padding: 24px; text-align: center; border: 1px solid rgba(29,185,84,0.2); box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
        .metric-value { color: #1DB954; font-size: 28px; font-weight: 800; margin-bottom: 8px; }
        .metric-label { color: #e2e8f0; font-size: 14px; opacity: 0.85; }
        @media (max-width: 768px) {
            .main-container { padding: 24px; margin: 16px; }
            .main-title { font-size: 32px; }
            .form-container { padding: 24px; }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # ===== FRESH, PERFECT PLAYLIST GENERATION FORM =====
        st.markdown('<div class="main-container">', unsafe_allow_html=True)
        st.markdown('<h1 class="main-title">🎵 Generate Your Perfect Playlist</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">Let TuneGenie create the perfect soundtrack for your mood, activity, and preferences</p>', unsafe_allow_html=True)
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        
        # Main Form Container
        with st.form("playlist_generation_form"):
            # Perfect Three-Column Layout
            col1, col2, col3 = st.columns([2.2, 2.2, 1.6])
            
            # ===== COLUMN 1: MOOD & CONTEXT =====
            with col1:
                st.markdown('<h3 class="section-header">😊 Mood & Context</h3>', unsafe_allow_html=True)
                
                # Perfect Mood Selection
                mood = st.selectbox(
                    "Select your mood",
                    ["Happy", "Sad", "Energetic", "Calm", "Focused", "Relaxed", "Motivated", "Melancholic", "Excited", "Peaceful"],
                    key="mood_select",
                    label_visibility="collapsed"
                )
                
                # Perfect Spacing
                st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                
                # Perfect Context Input
                user_context = st.text_area(
                    "Describe your situation",
                    placeholder="What are you doing? Any specific preferences?",
                    key="context_input",
                    label_visibility="collapsed",
                    height=120
                )

                # Keywords input
                st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                keywords_input = st.text_input(
                    "Enter keywords (e.g., artist: The Weeknd, title: Blinding Lights, album: After Hours, genre: pop)",
                    value="",
                    key="keywords_input",
                )
            
            # ===== COLUMN 2: ACTIVITY & LANGUAGE =====
            with col2:
                st.markdown('<h3 class="section-header">🏃‍♂️ Activity & Language</h3>', unsafe_allow_html=True)
                
                # Perfect Activity Selection
                activity = st.selectbox(
                    "Select your activity",
                    ["Working", "Exercising", "Studying", "Commuting", "Cooking", "Cleaning", "Socializing", "Meditating", "Creative Work", "Relaxing"],
                    key="activity_select",
                    label_visibility="collapsed"
                )
                
                # Perfect Spacing
                st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                
                # Perfect Language Selection
                language_preference = st.selectbox(
                    "Choose your preferred language",
                    ["Any Language", "English", "Tamil", "Telugu", "Hindi", "Kannada", "Malayalam", "Bengali", "Marathi", "Gujarati", "Punjabi", "Urdu", "Spanish", "French", "German", "Italian", "Portuguese", "Korean", "Japanese", "Chinese", "Arabic", "Russian"],
                    key="language_select"
                )
                
                # Perfect Spacing
                st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                
                # Perfect Language Info
                if language_preference == "English":
                    st.info("🇺🇸 English tracks will be prioritized")
                elif language_preference != "Any Language":
                    st.info(f"🌍 {language_preference} language tracks will be prioritized")
            
            # ===== COLUMN 3: TRACK COUNT =====
            with col3:
                st.markdown('<h3 class="section-header">🎯 Track Count</h3>', unsafe_allow_html=True)
                
                # Perfect Track Count Method
                track_count_method = st.radio(
                    "Choose your method:",
                    ["Quick Select", "Custom Number"],
                    key="track_method_radio",
                    horizontal=True,
                    label_visibility="collapsed"
                )
                
                # Perfect Spacing
                st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                
                # Perfect Track Count Selection
                if track_count_method == "Quick Select":
                    n_recommendations = st.slider(
                        "Number of tracks", 
                        min_value=5, 
                        max_value=50, 
                        value=20, 
                        step=5, 
                        key="tracks_slider"
                    )
                else:
                    st.markdown('<p style="color: #f39c12; font-size: 16px; margin-bottom: 24px; text-align: center;">💡 Enter any number from 1 to 250 tracks</p>', unsafe_allow_html=True)
                    n_recommendations = st.number_input(
                        "Number of tracks", 
                        min_value=1, 
                        max_value=250, 
                        value=20, 
                        step=1, 
                        help="Enter any number from 1 to 250 tracks", 
                        key="tracks_custom_input"
                    )
                    
                    # Perfect Spacing
                    st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                    
                    # Perfect Track Examples
                    if n_recommendations == 1:
                        st.markdown('<p style="color: #e74c3c; font-size: 16px; font-style: italic; text-align: center;">🎵 Single track - Perfect for a quick mood boost!</p>', unsafe_allow_html=True)
                    elif n_recommendations <= 5:
                        st.markdown('<p style="color: #f39c12; font-size: 16px; font-style: italic; text-align: center;">🎵 Mini playlist - Great for short activities!</p>', unsafe_allow_html=True)
                    elif n_recommendations <= 15:
                        st.markdown('<p style="color: #3498db; font-size: 16px; font-style: italic; text-align: center;">🎵 Standard playlist - Perfect for most activities!</p>', unsafe_allow_html=True)
                    elif n_recommendations <= 50:
                        st.markdown('<p style="color: #2ecc71; font-size: 16px; font-style: italic; text-align: center;">🎵 Extended playlist - For longer sessions!</p>', unsafe_allow_html=True)
                    elif n_recommendations <= 100:
                        st.markdown('<p style="color: #9b59b6; font-size: 16px; font-style: italic; text-align: center;">🎵 Mega playlist - Epic listening sessions!</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p style="color: #e67e22; font-size: 16px; font-style: italic; text-align: center;">🎵 Ultimate playlist - The ultimate music marathon!</p>', unsafe_allow_html=True)
            
            # ===== PERFECT SUMMARY SECTION =====
            st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
            
            with st.container():
                st.markdown('<div class="summary-section">', unsafe_allow_html=True)
                st.markdown('<h3 class="summary-header">🎯 Your Selection Summary</h3>', unsafe_allow_html=True)
                
                # Perfect Summary Grid
                summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)
                
                with summary_col1:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-value">😊</div>
                        <div class="metric-label">Mood</div>
                        <div class="metric-value" style="font-size: 20px; color: #1DB954;">{}</div>
                    </div>
                    """.format(mood), unsafe_allow_html=True)
                
                with summary_col2:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-value">🏃‍♂️</div>
                        <div class="metric-label">Activity</div>
                        <div class="metric-value" style="font-size: 20px; color: #46CD73;">{}</div>
                    </div>
                    """.format(activity), unsafe_allow_html=True)
                
                with summary_col3:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-value">🌍</div>
                        <div class="metric-label">Language</div>
                        <div class="metric-value" style="font-size: 20px; color: #2ECC71;">{}</div>
                    </div>
                    """.format(language_preference), unsafe_allow_html=True)
                
                with summary_col4:
                    st.markdown("""
                    <div class="metric-card">
                        <div class="metric-value">🎵</div>
                        <div class="metric-label">Tracks</div>
                        <div class="metric-value" style="font-size: 20px; color: #9B59B6;">{}</div>
                    </div>
                    """.format(n_recommendations), unsafe_allow_html=True)

                # Show keywords summary if provided
                if keywords_input.strip():
                    st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
                    st.info(f"🔍 Keywords: {keywords_input}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            # ===== PERFECT GENERATE BUTTON =====
            st.markdown('<div class="spacing-div"></div>', unsafe_allow_html=True)
            
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
        
        # Close containers
        st.markdown("</div>", unsafe_allow_html=True)  # form-container
        st.markdown("</div>", unsafe_allow_html=True)  # main-container
        
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
            if st.button("🔍 Run Analysis"):
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
                # Modern loading animation
                with st.spinner("🤖 TuneGenie is thinking..."):
                    try:
                        # Get AI insights
                        response = workflow.llm_agent.get_music_insights(user_query)
                        
                        # Display response in modern card
                        st.markdown("### 💡 AI Response")
                        
                        if 'error' in response:
                            st.error(f"❌ {response['error']}")
                        else:
                            # Success response card
                            st.markdown(f"""
                            <div style="
                                background: linear-gradient(135deg, rgba(45, 55, 72, 0.8), rgba(74, 85, 104, 0.8));
                                border: 1px solid rgba(29, 185, 84, 0.3);
                                border-radius: 15px;
                                padding: 24px;
                                margin: 16px 0;
                                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
                            ">
                                <p style="color: #ffffff; line-height: 1.6; margin: 0;">{response.get('insight', 'No response received')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Model info
                            if 'model_used' in response:
                                st.caption(f"🤖 Generated by {response['model_used']}")
                        
                        # Save to chat history
                        if 'chat_history' not in st.session_state:
                            st.session_state.chat_history = []
                        
                        st.session_state.chat_history.append({
                            'query': user_query,
                            'response': response.get('insight', 'No response received'),
                            'timestamp': response.get('timestamp', datetime.now().isoformat()),
                            'model': response.get('model_used', 'Unknown')
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
                
                st.markdown("**OpenAI API**")
                if llm_status.get('model_name', 'N/A') != 'N/A':
                    st.success("✅ Configured")
                else:
                    st.error("❌ Not configured")
            
            with col2:
                st.markdown("**Environment Variables**")
                env_vars = {
                    'SPOTIFY_CLIENT_ID': os.getenv('SPOTIFY_CLIENT_ID'),
                    'SPOTIFY_CLIENT_SECRET': os.getenv('SPOTIFY_CLIENT_SECRET'),
                    'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY')
                }
                
                for var, value in env_vars.items():
                    if value:
                        st.success(f"✅ {var}")
                    else:
                        st.error(f"❌ {var}")
            
            st.info("💡 To configure APIs, create a `.env` file with your credentials. See `env.example` for reference.")
        
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
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Executions", metrics.get('total_executions', 0))
            
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
                    st.bar_chart(workflow_df.set_index('Workflow'))
            
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
                        # Create histogram of execution times
                        fig = go.Figure(data=[go.Histogram(x=execution_times, nbinsx=10)])
                        fig.update_layout(
                            title="Workflow Execution Time Distribution",
                            xaxis_title="Execution Time (seconds)",
                            yaxis_title="Frequency",
                            height=400
                        )
                        st.plotly_chart(fig)
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
