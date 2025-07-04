import streamlit as st
import json
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import sys
import re
from pathlib import Path
import random
import base64
from PIL import Image
import io
import calendar

import subprocess
import threading
from pathlib import Path
from dotenv import load_dotenv

# LOAD ENVIRONMENT VARIABLES FROM .env FILE
load_dotenv()

# Try to import MongoDB
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# Try to import required packages for content generation
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Try to import ChromaDB functions
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Configure the page
st.set_page_config(
    page_title="LinkedIn Content Calendar Planner",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS with better dropdown colors and calendar styling
def load_css():
    st.markdown("""
    <style>
        /* Modern gradient background with sophisticated colors */
        .stApp {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #667eea 100%) !important;
            min-height: 100vh;
        }
        
        .main .block-container {
            background-color: #ffffff !important;
            padding: 2rem 1rem;
            border-radius: 24px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            margin: 1rem;
            border: 1px solid rgba(255,255,255,0.2);
        }
        
        /* Professional text colors with better hierarchy */
        .stMarkdown, .stText, p, div, span, label, .stSelectbox label, .stMultiSelect label {
            color: #1a202c !important;
            font-weight: 500 !important;
        }
        
        /* Elegant gradient headers */
        h1, h2, h3, h4, h5, h6 {
            background: linear-gradient(135deg, #2d3748 0%, #4a5568 50%, #1e3c72 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            font-weight: 700 !important;
        }
        
        /* Subtle, blended input fields */
        .stTextInput > div > div > input {
            background-color: rgba(248, 250, 252, 0.7) !important;
            color: #1a202c !important;
            border: 1px solid rgba(226, 232, 240, 0.6) !important;
            border-radius: 12px !important;
            font-weight: 500 !important;
            font-size: 16px !important;
            padding: 14px 18px !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #3182ce !important;
            box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.15) !important;
            background-color: rgba(255, 255, 255, 0.9) !important;
        }
        
        .stTextArea > div > div > textarea {
            background-color: rgba(248, 250, 252, 0.7) !important;
            color: #1a202c !important;
            border: 1px solid rgba(226, 232, 240, 0.6) !important;
            border-radius: 12px !important;
            font-weight: 500 !important;
            font-size: 16px !important;
            padding: 14px 18px !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .stTextArea > div > div > textarea:focus {
            border-color: #3182ce !important;
            box-shadow: 0 0 0 3px rgba(49, 130, 206, 0.15) !important;
            background-color: rgba(255, 255, 255, 0.9) !important;
        }
        
        /* COMPLETELY REWRITTEN DROPDOWN STYLING - SIMPLIFIED AND WORKING */
        
        /* Main selectbox container */
        .stSelectbox > div > div > div {
            background-color: white !important;
            color: #1a202c !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        
        /* Selected value display */
        .stSelectbox > div > div > div > div {
            color: #1a202c !important;
            background-color: transparent !important;
        }
        
        /* Arrow and container on hover */
        .stSelectbox > div > div:hover > div {
            border-color: #3182ce !important;
        }
        
        /* Dropdown menu container - CRITICAL FIX */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="listbox"] {
            background-color: white !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
            max-height: 200px !important;
            overflow-y: auto !important;
        }
        
        /* Individual dropdown options - CRITICAL FIX */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="option"] {
            background-color: white !important;
            color: #1a202c !important;
            padding: 12px 16px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
            border-bottom: 1px solid #f7fafc !important;
            cursor: pointer !important;
        }
        
        /* Dropdown option hover state - CRITICAL FIX */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] div[role="option"]:hover {
            background-color: #f0f8ff !important;
            color: #1a202c !important;
        }
        
        /* Alternative selector for dropdown options */
        .stSelectbox ul li {
            background-color: white !important;
            color: #1a202c !important;
            padding: 12px 16px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
        }
        
        .stSelectbox ul li:hover {
            background-color: #f0f8ff !important;
            color: #1a202c !important;
        }
        
        /* Even more specific selectors for stubborn dropdowns */
        [data-baseweb="select"] [role="listbox"] {
            background: white !important;
        }
        
        [data-baseweb="select"] [role="option"] {
            background: white !important;
            color: #1a202c !important;
        }
        
        [data-baseweb="select"] [role="option"]:hover {
            background: #f0f8ff !important;
            color: #1a202c !important;
        }
        
        /* Nuclear option - target everything */
        div[data-baseweb="select"] * {
            color: #1a202c !important;
        }
        
        div[data-baseweb="select"] div[role="listbox"] * {
            background-color: white !important;
            color: #1a202c !important;
        }
        
        /* MULTISELECT FIXES */
        
        /* Main multiselect container */
        .stMultiSelect > div > div > div {
            background-color: white !important;
            color: #1a202c !important;
            border: 2px solid #e2e8f0 !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
        }
        
        /* Multiselect dropdown options */
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="listbox"] {
            background-color: white !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
        
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="option"] {
            background-color: white !important;
            color: #1a202c !important;
            padding: 12px 16px !important;
            font-size: 16px !important;
            font-weight: 500 !important;
        }
        
        div[data-testid="stMultiSelect"] div[data-baseweb="select"] div[role="option"]:hover {
            background-color: #f0f8ff !important;
            color: #1a202c !important;
        }
        
        /* Enhanced radio buttons */
        .stRadio > div {
            color: #1a202c !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        
        .stRadio > div > label {
            color: #1a202c !important;
            font-weight: 600 !important;
        }
        
        /* Modern checkboxes */
        .stCheckbox > label {
            color: #1a202c !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        
        /* Sophisticated button design */
        .stButton > button {
            background: linear-gradient(135deg, #3182ce 0%, #2b77cb 50%, #2c5aa0 100%) !important;
            color: #ffffff !important;
            border: none !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            padding: 0.75rem 1.5rem !important;
            border-radius: 12px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(49, 130, 206, 0.25) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(49, 130, 206, 0.35) !important;
            background: linear-gradient(135deg, #2c5aa0 0%, #2b77cb 50%, #3182ce 100%) !important;
        }
        
        /* Accent buttons for primary actions */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #38a169 0%, #2f855a 50%, #276749 100%) !important;
            box-shadow: 0 4px 15px rgba(56, 161, 105, 0.25) !important;
        }
        
        .stButton > button[kind="primary"]:hover {
            box-shadow: 0 8px 25px rgba(56, 161, 105, 0.35) !important;
            background: linear-gradient(135deg, #276749 0%, #2f855a 50%, #38a169 100%) !important;
        }
        
        /* Premium glassmorphism cards */
        .content-card {
            background: rgba(255, 255, 255, 0.95) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 20px !important;
            padding: 2rem !important;
            margin-bottom: 1.5rem !important;
            box-shadow: 0 10px 40px rgba(30, 60, 114, 0.12) !important;
        }
        
        /* Enhanced creator cards */
        .creator-card {
            background: rgba(248, 250, 252, 0.95) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(226, 232, 240, 0.4) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            margin-bottom: 1rem !important;
            box-shadow: 0 6px 25px rgba(30, 60, 114, 0.08) !important;
            transition: all 0.3s ease !important;
        }
        
        .creator-card:hover {
            transform: translateY(-5px) !important;
            box-shadow: 0 15px 45px rgba(30, 60, 114, 0.15) !important;
            border-color: rgba(49, 130, 206, 0.3) !important;
        }
        
        /* Professional profile cards */
        .profile-card {
            display: flex;
            align-items: center;
            padding: 1.5rem;
            background: rgba(248, 250, 252, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(226, 232, 240, 0.4);
            border-radius: 16px;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        
        .profile-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 35px rgba(30, 60, 114, 0.12);
            border-color: rgba(49, 130, 206, 0.3);
        }
        
        .profile-image {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%);
            color: #ffffff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 24px;
            margin-right: 1.5rem;
            box-shadow: 0 6px 20px rgba(49, 130, 206, 0.25);
        }
        
        .profile-name {
            font-size: 20px !important;
            font-weight: 700 !important;
            color: #1a202c !important;
            margin-bottom: 0.5rem;
        }
        
        .profile-title {
            font-size: 16px !important;
            color: #4a5568 !important;
            font-weight: 600 !important;
        }
        
        .profile-description {
            font-size: 14px !important;
            color: #2d3748 !important;
            margin-top: 0.5rem;
            line-height: 1.5;
        }
        
        /* Modern metrics display */
        .metric-container {
            background: rgba(248, 250, 252, 0.95);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(226, 232, 240, 0.4);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }
        
        .metric-container:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 35px rgba(30, 60, 114, 0.12);
            border-color: rgba(49, 130, 206, 0.3);
        }
        
        .metric-value {
            font-size: 32px !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .metric-label {
            font-size: 16px !important;
            color: #4a5568 !important;
            font-weight: 600 !important;
        }
        
        /* Professional calendar styling */
        .calendar-container {
            background: rgba(248, 250, 252, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 20px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 10px 40px rgba(30, 60, 114, 0.12);
            border: 1px solid rgba(226, 232, 240, 0.4);
        }
        
        .calendar-day {
            background: rgba(255, 255, 255, 0.9);
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 12px;
            text-align: center;
            margin: 4px;
            transition: all 0.3s ease;
            min-height: 100px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        .calendar-day:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(30, 60, 114, 0.1);
            border-color: #cbd5e0;
        }
        
        .calendar-posting-day {
            background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%);
            color: white;
            border: 2px solid #3182ce;
            box-shadow: 0 6px 20px rgba(49, 130, 206, 0.25);
        }
        
        .calendar-posting-day:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(49, 130, 206, 0.35);
        }
        
        .calendar-day-number {
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .calendar-post-preview {
            font-size: 10px;
            background-color: rgba(255, 255, 255, 0.2);
            padding: 4px 6px;
            border-radius: 6px;
            margin-top: 4px;
            line-height: 1.2;
        }
        
        /* Professional post containers */
        .post-container {
            background: rgba(248, 250, 252, 0.95) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(226, 232, 240, 0.4) !important;
            border-radius: 16px !important;
            padding: 1.5rem !important;
            margin: 1rem 0 !important;
            color: #1a202c !important;
            font-weight: 500 !important;
            box-shadow: 0 6px 25px rgba(30, 60, 114, 0.08) !important;
            transition: all 0.3s ease !important;
        }
        
        .post-container:hover {
            transform: translateY(-3px) !important;
            box-shadow: 0 10px 35px rgba(30, 60, 114, 0.12) !important;
            border-color: rgba(49, 130, 206, 0.3) !important;
        }
        
        .generated-post-container {
            background: linear-gradient(135deg, rgba(49, 130, 206, 0.08) 0%, rgba(44, 90, 160, 0.12) 100%) !important;
            backdrop-filter: blur(20px) !important;
            border: 2px solid rgba(49, 130, 206, 0.25) !important;
            border-radius: 16px !important;
            padding: 20px !important;
            margin: 20px 0 !important;
            box-shadow: 0 10px 40px rgba(49, 130, 206, 0.15) !important;
        }
        
        /* Modern status messages */
        .stSuccess {
            background: linear-gradient(135deg, rgba(56, 161, 105, 0.08) 0%, rgba(47, 133, 90, 0.12) 100%) !important;
            border: 1px solid rgba(56, 161, 105, 0.25) !important;
            border-radius: 12px !important;
            color: #1a365d !important;
            font-weight: 600 !important;
        }
        
        .stError {
            background: linear-gradient(135deg, rgba(229, 62, 62, 0.08) 0%, rgba(197, 48, 48, 0.12) 100%) !important;
            border: 1px solid rgba(229, 62, 62, 0.25) !important;
            border-radius: 12px !important;
            color: #742a2a !important;
            font-weight: 600 !important;
        }
        
        .stWarning {
            background: linear-gradient(135deg, rgba(237, 137, 54, 0.08) 0%, rgba(213, 119, 41, 0.12) 100%) !important;
            border: 1px solid rgba(237, 137, 54, 0.25) !important;
            border-radius: 12px !important;
            color: #744210 !important;
            font-weight: 600 !important;
        }
        
        .stInfo {
            background: linear-gradient(135deg, rgba(49, 130, 206, 0.08) 0%, rgba(44, 90, 160, 0.12) 100%) !important;
            border: 1px solid rgba(49, 130, 206, 0.25) !important;
            border-radius: 12px !important;
            color: #1a365d !important;
            font-weight: 600 !important;
        }
        
        /* Professional tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(248, 250, 252, 0.8);
            padding: 8px;
            border-radius: 16px;
            backdrop-filter: blur(20px);
            border: 1px solid rgba(226, 232, 240, 0.4);
        }
        
        .stTabs [data-baseweb="tab"] {
            background: rgba(255, 255, 255, 0.8) !important;
            color: #2d3748 !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 12px 24px !important;
            border-radius: 12px !important;
            border: 1px solid rgba(226, 232, 240, 0.4) !important;
            transition: all 0.3s ease !important;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 4px 15px rgba(49, 130, 206, 0.25) !important;
            border-color: transparent !important;
        }
        
        /* Modern progress bar */
        .stProgress > div > div {
            background: linear-gradient(135deg, #3182ce 0%, #2c5aa0 100%) !important;
            border-radius: 10px !important;
        }
        
        /* Professional sidebar */
        .css-1d391kg {
            background: linear-gradient(135deg, rgba(248, 250, 252, 0.95) 0%, rgba(237, 242, 247, 0.95) 100%) !important;
            backdrop-filter: blur(20px) !important;
            border-right: 1px solid rgba(226, 232, 240, 0.4) !important;
        }
        
        /* Enhanced dialog styling */
        .content-dialog {
            background: rgba(248, 250, 252, 0.98);
            backdrop-filter: blur(25px);
            border: 1px solid rgba(226, 232, 240, 0.4);
            border-radius: 20px;
            padding: 2rem;
            margin: 1rem 0;
            box-shadow: 0 15px 50px rgba(30, 60, 114, 0.15);
        }
        
        /* Smooth animations */
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        .loading-pulse {
            animation: pulse 2s infinite;
        }
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {
            .main .block-container {
                padding: 1rem 0.5rem;
                margin: 0.5rem;
                border-radius: 16px;
            }
            
            .content-card {
                padding: 1rem !important;
                border-radius: 16px !important;
            }
            
            .profile-card {
                flex-direction: column;
                text-align: center;
            }
            
            .profile-image {
                margin-right: 0;
                margin-bottom: 1rem;
            }
        }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state for content cache and calendar
if 'content_cache' not in st.session_state:
    st.session_state.content_cache = {}

if 'show_dialog' not in st.session_state:
    st.session_state.show_dialog = False

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = None

if 'show_full_generation' not in st.session_state:
    st.session_state.show_full_generation = False

if 'calendar_topic' not in st.session_state:
    st.session_state.calendar_topic = ''

# Calendar-related functions
def initialize_groq_client():
    """Initialize Groq client with API key"""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("⚠️ Groq API key not found. Please set GROQ_API_KEY in environment variables.")
        return None
    return Groq(api_key=api_key)

# Post type rotation system
if 'post_type_rotation' not in st.session_state:
    st.session_state.post_type_rotation = []

def get_user_topics(profile):
    """Extract user's topics from profile"""
    topics = []
    
    # Get topics from LinkedIn profile
    if profile['basic_info']['active_on_linkedin'] and 'linkedin_profile' in profile:
        if 'topics_of_interest' in profile['linkedin_profile']:
            topics.extend(profile['linkedin_profile']['topics_of_interest'])
    
    # Get topics from selected categories
    if profile['basic_info']['active_on_linkedin'] and 'linkedin_profile' in profile:
        if "selected_categories" in profile["linkedin_profile"]:
            topics.extend(profile["linkedin_profile"]["selected_categories"])
    elif 'reference_info' in profile:
        if "selected_categories" in profile['reference_info']:
            topics.extend(profile['reference_info']['selected_categories'])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_topics = []
    for topic in topics:
        if topic not in seen:
            seen.add(topic)
            unique_topics.append(topic)
    
    return unique_topics

def display_topic_selection_interface(profile):
    """Display topic selection interface with enhanced UI"""
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 20px; border-radius: 15px; margin: 20px 0;">
        <h3 style="color: white; text-align: center; margin-bottom: 20px;">
            🎯 Select Topics for Content Generation
        </h3>
        <p style="color: #e2e8f0; text-align: center; margin-bottom: 0;">
            Choose the topics you want to focus on for your LinkedIn content calendar
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get user's existing topics
    user_topics = get_user_topics(profile)
    
    # Default comprehensive topic list
    default_topics = [
        "Artificial Intelligence", "Machine Learning", "Blockchain", "Cryptocurrency",
        "Data Science", "Cloud Computing", "Cybersecurity", "Digital Marketing",
        "Leadership", "Entrepreneurship", "Startup", "Innovation", "Technology",
        "Business Strategy", "Personal Development", "Career Growth", "Networking",
        "Industry Trends", "Digital Transformation", "Remote Work", "Productivity",
        "Sales", "Marketing", "Finance", "HR", "Project Management", "Customer Experience",
        "Social Media", "Content Marketing", "SEO", "E-commerce", "Sustainability",
        "Diversity & Inclusion", "Mental Health", "Work-Life Balance", "Team Building", "Skills Development", "Training", "Education",
        "Consulting", "Freelancing", "Side Hustle", "Passive Income", "Investment",
        "Real Estate", "Healthcare", "Fintech", "EdTech", "SaaS", "Mobile Apps","Parenting",
        "Web Development", "UX/UI Design", "Product Management", "Agile", "DevOps"
    ]
    
    # Combine user topics with defaults, prioritizing user topics
    all_topics = user_topics + [topic for topic in default_topics if topic not in user_topics]
    
    # Initialize session state for selected topics
    if 'selected_topics_for_calendar' not in st.session_state:
        st.session_state.selected_topics_for_calendar = user_topics.copy()
    
    # Create search functionality
    st.markdown("### 🔍 Search Topics")
    search_term = st.text_input("Search for topics...", key="topic_search", placeholder="Type to search topics...")
    
    # Filter topics based on search
    if search_term:
        filtered_topics = [topic for topic in all_topics if search_term.lower() in topic.lower()]
    else:
        filtered_topics = all_topics
    
    # Display topic selection interface
    st.markdown("### 📋 Select Your Topics")
    
    # Add bulk selection options
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("✅ Select All", key="select_all_topics"):
            st.session_state.selected_topics_for_calendar = filtered_topics.copy()
            st.rerun()
    
    with col2:
        if st.button("❌ Clear All", key="clear_all_topics"):
            st.session_state.selected_topics_for_calendar = []
            st.rerun()
    
    with col3:
        if st.button("🔄 Reset to Profile", key="reset_to_profile"):
            st.session_state.selected_topics_for_calendar = user_topics.copy()
            st.rerun()
    
    with col4:
        if st.button("➕ Add Custom Topic", key="add_custom_topic"):
            st.session_state.show_custom_topic_input = True
            st.rerun()
    
    # Custom topic input
    if st.session_state.get('show_custom_topic_input', False):
        st.markdown("#### Add Custom Topic")
        col1, col2 = st.columns([3, 1])
        with col1:
            custom_topic = st.text_input("Enter custom topic:", key="custom_topic_input")
        with col2:
            if st.button("Add", key="add_custom_topic_btn"):
                if custom_topic and custom_topic not in all_topics:
                    all_topics.append(custom_topic)
                    filtered_topics.append(custom_topic)
                    st.session_state.selected_topics_for_calendar.append(custom_topic)
                    st.session_state.show_custom_topic_input = False
                    st.success(f"Added '{custom_topic}' to your topics!")
                    st.rerun()
    
    # Display topics in a grid with checkboxes
    st.markdown("#### Available Topics:")
    
    # Create columns for grid layout
    num_cols = 3
    cols = st.columns(num_cols)
    
    # Style for topic cards
    st.markdown("""
    <style>
    .topic-card {
        background: white;
        border: 2px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px;
        margin: 5px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .topic-card:hover {
        border-color: #667eea;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    .topic-card.selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    .topic-checkbox {
        margin-right: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display topics in grid
    for i, topic in enumerate(filtered_topics):
        col = cols[i % num_cols]
        with col:
            # Check if topic is selected
            is_selected = topic in st.session_state.selected_topics_for_calendar
            
            # Create unique key for each checkbox
            checkbox_key = f"topic_{topic.replace(' ', '_').replace('&', 'and')}"
            
            # Display checkbox with custom styling
            selected = st.checkbox(
                topic,
                value=is_selected,
                key=checkbox_key,
                help=f"Click to {'remove' if is_selected else 'add'} {topic}"
            )
            
            # Update selected topics based on checkbox state
            if selected and topic not in st.session_state.selected_topics_for_calendar:
                st.session_state.selected_topics_for_calendar.append(topic)
            elif not selected and topic in st.session_state.selected_topics_for_calendar:
                st.session_state.selected_topics_for_calendar.remove(topic)
    
    # Display selected topics summary
    if st.session_state.selected_topics_for_calendar:
        st.markdown("### 🎯 Selected Topics Summary")
        
        # Create a nice display of selected topics
        selected_topics_html = ""
        for topic in st.session_state.selected_topics_for_calendar:
            selected_topics_html += f"""
            <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                         color: white; padding: 8px 15px; border-radius: 25px; 
                         margin: 5px; display: inline-block; font-size: 14px;">
                {topic}
            </span>
            """
        
        st.markdown(f"""
        <div style="background: #f7fafc; padding: 20px; border-radius: 10px; 
                    border-left: 4px solid #667eea; margin: 20px 0;">
            <p style="margin: 0; color: #2d3748; font-weight: 500;">
                You have selected {len(st.session_state.selected_topics_for_calendar)} topics:
            </p>
            <div style="margin-top: 15px;">
                {selected_topics_html}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Confirmation button
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Generate Calendar with Selected Topics", 
                        key="generate_calendar_with_topics", 
                        type="primary",
                        use_container_width=True):
                st.session_state.topics_confirmed = True
                st.success("✅ Topics confirmed! Generating calendar...")
                return True
    else:
        st.warning("⚠️ Please select at least one topic to generate your content calendar.")
        return False
    
    return False

def generate_post_type_rotation(profile, num_posts):
    """Generate a balanced rotation of post types for the month"""
    # Define the available post types (added Articles)
    available_post_types = [
        "Storytelling", "Life Lesson", "Personal Experience", "Factual", 
        "Data Driven", "Motivational", "Inspirational", "Thought Provoking",
        "How-to/Educational", "Behind the Scenes", "Industry Insights", 
        "Question/Poll", "Articles"
    ]
    
    # Use user's preferred post types if available, otherwise use all types
    if 'preferred_post_types' in profile.get('content_preferences', {}):
        post_types = profile['content_preferences']['preferred_post_types']
    else:
        # Default to a balanced mix of popular types (including Articles)
        post_types = ["Storytelling", "Personal Experience", "Data Driven", "Industry Insights", 
                     "How-to/Educational", "Motivational", "Articles"]
    
    # Create a balanced distribution
    rotation = []
    posts_per_type = num_posts // len(post_types)
    remaining_posts = num_posts % len(post_types)
    
    # Add equal distribution for each type
    for post_type in post_types:
        rotation.extend([post_type] * posts_per_type)
    
    # Add remaining posts randomly
    for _ in range(remaining_posts):
        rotation.append(random.choice(post_types))
    
    # Shuffle to avoid predictable patterns
    random.shuffle(rotation)
    
    return rotation

def get_post_type_for_date(date_key, posting_dates, profile):
    """Get the assigned post type for a specific date"""
    # Create a sorted list of posting dates for consistent ordering
    sorted_dates = sorted(posting_dates)
    
    # Generate rotation if not exists or if length doesn't match
    if (not st.session_state.post_type_rotation or 
        len(st.session_state.post_type_rotation) != len(sorted_dates)):
        st.session_state.post_type_rotation = generate_post_type_rotation(profile, len(sorted_dates))
    
    # Find the index of current date in sorted posting dates
    try:
        day = int(date_key.split('-')[2])
        date_index = sorted_dates.index(day)
        return st.session_state.post_type_rotation[date_index]
    except (ValueError, IndexError):
        # Fallback to random selection
        available_post_types = [
            "Storytelling", "Life Lesson", "Personal Experience", "Factual", 
            "Data Driven", "Motivational", "Inspirational", "Thought Provoking",
            "How-to/Educational", "Behind the Scenes", "Industry Insights", "Question/Poll"
        ]
        return random.choice(available_post_types)

import random

def generate_content_prompt(profile, date_str, post_type=None):
    """Generate a prompt for content creation based on user profile and post type"""
    name = profile["basic_info"]["name"]
    role = profile["basic_info"]["role"]
    goal = profile["basic_info"]["linkedin_goal"]
    is_company = profile["basic_info"].get("is_company", False)
    content_types = ", ".join(profile["content_preferences"]["preferred_content_types"])
    tone = ", ".join(profile["content_preferences"]["preferred_tone"])
    
    # Get selected topics from session state or fallback to profile topics
    selected_topics = st.session_state.get('selected_topics_for_calendar', [])
    if not selected_topics:
        # Fallback to profile topics
        selected_topics = get_user_topics(profile)
    
    # Smart topic selection logic
    if not selected_topics:
        topics = "general professional topics"
        topic_instruction = "Focus on general professional topics relevant to your industry."
    else:
        # 70% chance for single topic, 30% chance for combining two topics
        if len(selected_topics) == 1 or random.random() < 0.7:
            # Single topic
            chosen_topic = random.choice(selected_topics)
            topics = chosen_topic
            topic_instruction = f"Focus specifically on: {chosen_topic}"
        else:
            # Combine two topics (only if we have at least 2 topics)
            if len(selected_topics) >= 2:
                chosen_topics = random.sample(selected_topics, 2)
                topics = " and ".join(chosen_topics)
                topic_instruction = f"Create content that connects or relates these two topics: {chosen_topics[0]} and {chosen_topics[1]}"
            else:
                # Fallback to single topic if we somehow don't have enough
                chosen_topic = selected_topics[0]
                topics = chosen_topic
                topic_instruction = f"Focus specifically on: {chosen_topic}"
    
    # Get differentiation goals if available
    diff_goals = ""
    if profile['basic_info']['active_on_linkedin'] and 'linkedin_profile' in profile:
        if "differentiation_goals" in profile["linkedin_profile"]:
            diff_goals = ", ".join(profile["linkedin_profile"]["differentiation_goals"])
    
    # Post Type Specific Instructions for Companies vs Individuals
    if is_company:
        post_type_instructions = {
            "Company Updates": "Share important company news, milestones, product launches, or organizational changes that showcase growth and progress.",
            "Case Study": "Present a detailed analysis of how your company solved a client problem or achieved specific results with measurable outcomes.",
            "Industry Analysis": "Provide expert analysis of industry trends, market conditions, or regulatory changes that affect your sector.",
            "Factual": "Present industry-relevant facts, statistics, or data that positions your company as knowledgeable and authoritative.",
            "Data Driven": "Share market research, industry analytics, or performance metrics that demonstrate your company's expertise and results.",
            "Thought Leadership": "Position your company as an industry leader by sharing innovative ideas, predictions, or strategic insights.",
            "Expert Insights": "Share professional expertise and deep knowledge about industry-specific topics or challenges.",
            "Market Trends": "Analyze and discuss emerging trends, technologies, or shifts in your industry landscape.",
            "How-to/Educational": "Provide valuable business tips, tutorials, or educational content that showcases your company's expertise.",
            "Behind the Scenes": "Show your company culture, processes, team, or the work that goes into delivering your services/products.",
            "Industry Insights": "Share professional analysis, trends, or observations about your industry that demonstrate thought leadership.",
            "Question/Poll": "Engage your audience with business-related questions or polls that encourage professional discussion.",
            "Articles": "Create compelling article titles that position your company as a thought leader and knowledge expert in your industry."
        }
        
        # Company-specific prompt structure
        entity_type = "company"
        pronoun = "we"
        perspective = "company"
        tone_guidance = "professional, authoritative, and business-focused"
        
    else:
        post_type_instructions = {
            "Storytelling": "Create a compelling narrative that shares a personal or professional story with a clear beginning, middle, and end. Include emotions and lessons learned.",
            "Life Lesson": "Share a valuable lesson learned from experience. Make it relatable and actionable for your audience.",
            "Personal Experience": "Draw from your real experiences, challenges, or successes. Be authentic and vulnerable while maintaining professionalism.",
            "Factual": "Present well-researched facts, statistics, or industry data. Be informative and educational.",
            "Data Driven": "Focus on numbers, metrics, research findings, or analytical insights. Include specific data points or trends.",
            "Motivational": "Inspire and energize your audience. Focus on overcoming obstacles and achieving success.",
            "Inspirational": "Uplift and encourage your audience with positive messages and hope for the future.",
            "Thought Provoking": "Challenge conventional thinking or present controversial but professional viewpoints that spark discussion.",
            "How-to/Educational": "Provide step-by-step guidance or teach something valuable to your audience.",
            "Behind the Scenes": "Show the real work, process, or journey behind your success or projects.",
            "Industry Insights": "Share professional observations, trends, or analysis about your industry.",
            "Question/Poll": "Engage your audience with thought-provoking questions or interactive polls.",
            "Articles": "Create engaging article titles that showcase your expertise and provide valuable insights to your professional network."
        }
        
        # Individual-specific prompt structure
        entity_type = "individual"
        pronoun = "I"
        perspective = "personal"
        tone_guidance = "authentic, relatable, and professionally personal"
    
    post_type_instruction = ""
    if post_type:
        post_type_instruction = f"\nPost Type: {post_type}\nPost Type Instruction: {post_type_instructions.get(post_type, 'Create engaging content that matches the specified post type.')}"

    if is_company:
        prompt = f"""
        You are helping {name}, a {role}, create LinkedIn content to achieve: {goal}.

        Company Profile Details:
        - Company Name: {name}
        - Industry/Type: {role}
        - Goal: {goal}
        - Preferred content type: {content_types}
        - Preferred tone: {tone}
        - Topic focus for this post: {topics}
        {f"- Differentiation goal: {diff_goals}" if diff_goals else ""}
        {post_type_instruction}

        Create a unique, engaging LinkedIn post title for {date_str} that:
        1. Uses a {tone_guidance} tone appropriate for a company
        2. Falls under {content_types} category
        3. {topic_instruction}
        4. Avoids personal pronouns like "I" - use "we", "our company", or company name instead
        5. Positions the company as knowledgeable and trustworthy
        6. Is professional and business-focused, not personal
        7. Would help achieve: {goal}
        8. Speaks from a company perspective, not individual perspective
        {f"9. Follows the {post_type} post type format and style for companies" if post_type else ""}

        IMPORTANT: This is for a COMPANY, not an individual. Use corporate language and avoid personal storytelling unless it's about company milestones or achievements. {topic_instruction}. Respond with ONLY the post title. No introduction, no explanation, no additional text - just the title itself.
        """
    else:
        prompt = f"""
        You are helping {name}, a {role}, create LinkedIn content to achieve: {goal}.

        Individual Profile Details:
        - Name: {name}
        - Role: {role}
        - Goal: {goal}
        - Preferred content type: {content_types}
        - Preferred tone: {tone}
        - Topic focus for this post: {topics}
        {f"- Differentiation goal: {diff_goals}" if diff_goals else ""}
        {post_type_instruction}

        Create a unique, engaging LinkedIn post title for {date_str} that:
        1. Matches the {tone} tone
        2. Falls under {content_types} category
        3. {topic_instruction}
        4. Is not generic - should be unique and attention-grabbing
        5. Can use personal pronouns and personal experiences
        6. Is authentic and relatable while maintaining professionalism
        7. Would help achieve: {goal}
        {f"8. Follows the {post_type} post type format and style" if post_type else ""}

        IMPORTANT: This is for an INDIVIDUAL professional. Use personal language and authentic storytelling. {topic_instruction}. Respond with ONLY the post title. No introduction, no explanation, no additional text - just the title itself.
        """
    
    return prompt

def generate_calendar_content_with_groq(client, prompt):
    """Generate content using Groq API for calendar"""
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=500
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating content: {str(e)}"

# Add these new MongoDB functions for calendar content

def save_calendar_content_to_mongodb(profile_id, year, month, content_data):
    """Save calendar content to MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return False
        
        calendar_key = f"calendar_{year}_{month:02d}"
        
        # Update the profile with calendar content
        result = collection.update_one(
            {"_id": profile_id},
            {
                "$set": {
                    f"calendar_data.{calendar_key}": {
                        "content_cache": content_data.get("content_cache", {}),
                        "post_type_rotation": content_data.get("post_type_rotation", []),
                        "selected_topics": content_data.get("selected_topics", []),
                        "topics_confirmed": True,
                        "year": year,
                        "month": month,
                        "updated_at": datetime.now().isoformat()
                    }
                }
            },
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None
    except Exception as e:
        st.error(f"Error saving calendar content to MongoDB: {str(e)}")
        return False

def load_calendar_content_from_mongodb(profile_id, year, month):
    """Load calendar content from MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return None
        
        calendar_key = f"calendar_{year}_{month:02d}"
        
        profile = collection.find_one(
            {"_id": profile_id},
            {f"calendar_data.{calendar_key}": 1}
        )
        
        if profile and "calendar_data" in profile and calendar_key in profile["calendar_data"]:
            calendar_data = profile["calendar_data"][calendar_key]
            # Restore topic state to session
            if "selected_topics" in calendar_data:
                st.session_state.selected_topics_for_calendar = calendar_data["selected_topics"]
            if calendar_data.get("topics_confirmed", False):
                st.session_state.topics_confirmed = True
            return calendar_data
        
        return None
    except Exception as e:
        st.error(f"Error loading calendar content from MongoDB: {str(e)}")
        return None

def get_or_create_calendar_content(profile_id, year, month, posting_dates, profile, groq_client):
    """Get calendar content from MongoDB or create new if doesn't exist"""
    # Try to load from MongoDB first
    calendar_data = load_calendar_content_from_mongodb(profile_id, year, month)
    
    if calendar_data:
        # Load existing data into session state
        st.session_state.content_cache.update(calendar_data.get("content_cache", {}))
        st.session_state.post_type_rotation = calendar_data.get("post_type_rotation", [])
        return True
    else:
        # Generate new calendar content
        if posting_dates:
            # Generate post type rotation
            st.session_state.post_type_rotation = generate_post_type_rotation(profile, len(posting_dates))
            
            # Generate content for each posting date
            with st.spinner("Generating calendar content..."):
                progress_bar = st.progress(0)
                total_dates = len(posting_dates)
                
                for i, day in enumerate(posting_dates):
                    date_key = f"{year}-{month:02d}-{day:02d}"
                    if date_key not in st.session_state.content_cache:
                        date_str = f"{calendar.month_name[month]} {day}, {year}"
                        post_type = get_post_type_for_date(date_key, posting_dates, profile)
                        prompt = generate_content_prompt(profile, date_str, post_type)
                        content = generate_calendar_content_with_groq(groq_client, prompt)
                        st.session_state.content_cache[date_key] = content
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total_dates)
                
                progress_bar.empty()
            
            # Save to MongoDB
            calendar_content_data = {
                "content_cache": {k: v for k, v in st.session_state.content_cache.items() 
                                if k.startswith(f"{year}-{month:02d}")},
                "post_type_rotation": st.session_state.post_type_rotation,
                "selected_topics": st.session_state.get('selected_topics_for_calendar', [])
            }
            
            save_calendar_content_to_mongodb(profile_id, year, month, calendar_content_data)
            return True
    
    return False

def improve_content_with_groq(client, original_content, improvement_request, post_type=None):
    """Improve existing content based on user feedback"""
    post_type_context = f" while maintaining the {post_type} post type style" if post_type else ""
    
    prompt = f"""
    Original LinkedIn post title{f" ({post_type} type)" if post_type else ""}:
    {original_content}

    User improvement request:
    {improvement_request}

    Please rewrite/improve the LinkedIn post title based on the user's feedback{post_type_context}. 
    Keep it engaging and concise.
    
    IMPORTANT: Respond with ONLY the improved post title. No introduction, no explanation, no additional text - just the title itself.
    """
    
    return generate_calendar_content_with_groq(client, prompt)

def get_posting_dates_for_month(year, month, posting_days, posts_per_week):
    """Get all posting dates for a given month based on preferences"""
    # Convert posting days to weekday numbers (Monday=0, Sunday=6)
    day_mapping = {
        'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
        'Friday': 4, 'Saturday': 5, 'Sunday': 6
    }
    
    target_weekdays = [day_mapping[day] for day in posting_days]
    
    # Get all days in the month
    cal = calendar.monthcalendar(year, month)
    posting_dates = []
    
    for week in cal:
        week_posts = 0
        for day in week:
            if day == 0:  # Empty day in calendar
                continue
            
            date_obj = datetime(year, month, day)
            if date_obj.weekday() in target_weekdays and week_posts < posts_per_week:
                posting_dates.append(day)
                week_posts += 1
    
    return posting_dates

# Modified show_content_dialog function to save changes to MongoDB
def show_content_dialog(date_key, date_str, profile, groq_client, posting_dates):
    """Show content dialog for a specific date with post type support"""
    # Get post type for this date
    post_type = get_post_type_for_date(date_key, posting_dates, profile)
    
    # Generate content if not in cache
    if date_key not in st.session_state.content_cache:
        with st.spinner("Generating content..."):
            prompt = generate_content_prompt(profile, date_str, post_type)
            content = generate_calendar_content_with_groq(groq_client, prompt)
            st.session_state.content_cache[date_key] = content
            
            # Save to MongoDB immediately
            profile_id = st.session_state.get('persona_id')
            if profile_id:
                year, month, _ = date_key.split('-')
                year, month = int(year), int(month)
                calendar_content_data = {
                    "content_cache": {k: v for k, v in st.session_state.content_cache.items() 
                                    if k.startswith(f"{year}-{month:02d}")},
                    "post_type_rotation": st.session_state.post_type_rotation,
                    "selected_topics": st.session_state.get('selected_topics_for_calendar', [])
                }
                save_calendar_content_to_mongodb(profile_id, year, month, calendar_content_data)
    
    # Dialog container with enhanced styling
    with st.container():
        st.markdown(f"""
        <div class="content-dialog">
            <h3 style="color: #2d3748; font-size: 24px; margin-bottom: 20px;">📝 Content for {date_str}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Show post type
        st.markdown(f"**📌 Post Type:** `{post_type}`")
        
        # Display the post title
        st.markdown("### Post Title:")
        st.info(st.session_state.content_cache[date_key])
        
        # Action buttons
        col1, col2, col3, col4, col5 = st.columns(5)
        
        def save_changes_to_mongodb():
            """Helper function to save changes to MongoDB"""
            profile_id = st.session_state.get('persona_id')
            if profile_id:
                year, month, _ = date_key.split('-')
                year, month = int(year), int(month)
                calendar_content_data = {
                    "content_cache": {k: v for k, v in st.session_state.content_cache.items() 
                                    if k.startswith(f"{year}-{month:02d}")},
                    "post_type_rotation": st.session_state.post_type_rotation,
                    "selected_topics": st.session_state.get('selected_topics_for_calendar', [])
                }
                save_calendar_content_to_mongodb(profile_id, year, month, calendar_content_data)
        
        with col1:
            if st.button("🔁 Regenerate", key=f"dialog_regen_{date_key}", use_container_width=True):
                with st.spinner("Regenerating..."):
                    prompt = generate_content_prompt(profile, date_str, post_type)
                    new_content = generate_calendar_content_with_groq(groq_client, prompt)
                    st.session_state.content_cache[date_key] = new_content
                    save_changes_to_mongodb()
                    st.rerun()
        
        with col2:
            if st.button("✍️ Improve", key=f"dialog_improve_{date_key}", use_container_width=True):
                st.session_state[f"show_improve_{date_key}"] = True
                st.rerun()
        
        with col3:
            if st.button("🔄 Change Type", key=f"dialog_change_type_{date_key}", use_container_width=True):
                st.session_state[f"show_change_type_{date_key}"] = True
                st.rerun()
        
        with col4:
            if st.button("🚀 Generate Full Post", key=f"dialog_generate_{date_key}", use_container_width=True):
                # Set the topic for full content generation
                st.session_state.calendar_topic = st.session_state.content_cache[date_key]
                st.session_state.show_full_generation = True
                st.rerun()
        
        with col5:
            if st.button("❌ Close", key=f"dialog_close_{date_key}", use_container_width=True):
                st.session_state.show_dialog = False
                st.session_state.selected_date = None
                st.rerun()
        
        # Show change post type interface
        if st.session_state.get(f"show_change_type_{date_key}", False):
            st.markdown("---")
            st.markdown("### Change Post Type:")
            available_types = [
                "Storytelling", "Life Lesson", "Personal Experience", "Factual", 
                "Data Driven", "Motivational", "Inspirational", "Thought Provoking",
                "How-to/Educational", "Behind the Scenes", "Industry Insights", 
                "Question/Poll", "Articles"
            ]
            new_post_type = st.selectbox(
                "Select new post type:",
                available_types,
                index=available_types.index(post_type) if post_type in available_types else 0,
                key=f"new_type_{date_key}"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply New Type", key=f"apply_type_{date_key}", use_container_width=True):
                    # Update the post type rotation for this specific date
                    day = int(date_key.split('-')[2])
                    sorted_dates = sorted(posting_dates)
                    try:
                        date_index = sorted_dates.index(day)
                        st.session_state.post_type_rotation[date_index] = new_post_type
                    except (ValueError, IndexError):
                        pass
                    
                    # Regenerate content with new type
                    with st.spinner("Generating content with new type..."):
                        prompt = generate_content_prompt(profile, date_str, new_post_type)
                        new_content = generate_calendar_content_with_groq(groq_client, prompt)
                        st.session_state.content_cache[date_key] = new_content
                        st.session_state[f"show_change_type_{date_key}"] = False
                        save_changes_to_mongodb()
                        st.rerun()
            
            with col2:
                if st.button("Cancel", key=f"cancel_type_{date_key}", use_container_width=True):
                    st.session_state[f"show_change_type_{date_key}"] = False
                    st.rerun()
        
        # Show improvement input if requested
        if st.session_state.get(f"show_improve_{date_key}", False):
            st.markdown("---")
            st.markdown("### Improve This Title:")
            improvement_request = st.text_area(
                "How would you like to improve this post title?",
                key=f"dialog_improve_input_{date_key}",
                placeholder="E.g., make it more engaging, add a question, change the tone..."
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Apply Improvement", key=f"dialog_apply_{date_key}", use_container_width=True):
                    if improvement_request:
                        with st.spinner("Improving content..."):
                            improved_content = improve_content_with_groq(
                                groq_client, 
                                st.session_state.content_cache[date_key],
                                improvement_request,
                                post_type
                            )
                            st.session_state.content_cache[date_key] = improved_content
                            st.session_state[f"show_improve_{date_key}"] = False
                            save_changes_to_mongodb()
                            st.rerun()
                    else:
                        st.warning("Please enter an improvement request.")
            
            with col2:
                if st.button("Cancel", key=f"dialog_cancel_{date_key}", use_container_width=True):
                    st.session_state[f"show_improve_{date_key}"] = False
                    st.rerun()
def main_calendar_page(profile, groq_client, year, month, posting_dates):
    """Main calendar page with topic selection interface"""
    # Load topics from profile if not already in session state
    if 'selected_topics_for_calendar' not in st.session_state:
        # Try to load from profile's saved calendar topics
        profile_id = st.session_state.get('persona_id')
        if profile_id:
            try:
                collection = get_profiles_collection()
                if collection is not None:
                    profile_data = collection.find_one({"_id": profile_id}, {"calendar_topics": 1})
                    if profile_data and "calendar_topics" in profile_data:
                        st.session_state.selected_topics_for_calendar = profile_data["calendar_topics"]
                        st.session_state.topics_confirmed = True
                    else:
                        # Fallback to profile's existing topics
                        st.session_state.selected_topics_for_calendar = get_user_topics(profile)
                        st.session_state.topics_confirmed = bool(st.session_state.selected_topics_for_calendar)
            except Exception as e:
                st.error(f"Error loading topics: {str(e)}")
                st.session_state.selected_topics_for_calendar = get_user_topics(profile)
                st.session_state.topics_confirmed = bool(st.session_state.selected_topics_for_calendar)
    
    # Show change topics button if topics are already confirmed
    if st.session_state.get('topics_confirmed', False):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 📅 {calendar.month_name[month]} {year} Content Calendar")
            # Show current selected topics
            if st.session_state.get('selected_topics_for_calendar'):
                topics_preview = ", ".join(st.session_state.selected_topics_for_calendar[:5])
                if len(st.session_state.selected_topics_for_calendar) > 5:
                    topics_preview += f" (+{len(st.session_state.selected_topics_for_calendar) - 5} more)"
                st.markdown(f"**Current Topics:** {topics_preview}")
        with col2:
            if st.button("🔄 Change Topics", key="change_topics_btn", use_container_width=True):
                st.session_state.topics_confirmed = False
                st.rerun()
        
        # Show calendar with confirmed topics
        display_calendar(year, month, posting_dates, profile, groq_client)
    else:
        # Show topic selection interface first
        topics_confirmed = display_topic_selection_interface(profile)
        if topics_confirmed:
            # Save topics to profile in MongoDB
            profile_id = st.session_state.get('persona_id')
            if profile_id:
                try:
                    collection = get_profiles_collection()
                    if collection is not None:
                        collection.update_one(
                            {"_id": profile_id},
                            {"$set": {"calendar_topics": st.session_state.selected_topics_for_calendar}},
                            upsert=True
                        )
                except Exception as e:
                    st.error(f"Error saving topics: {str(e)}")
            
            # Show calendar with selected topics
            display_calendar(year, month, posting_dates, profile, groq_client)
        else:
            return  # Don't show calendar until topics are confirmed
        
def display_calendar(year, month, posting_dates, profile, groq_client):
    """Display the monthly calendar with interactive content and post types"""
    st.markdown(f"""
    <div class="calendar-container">
        <h2 style="text-align: center; margin-bottom: 2rem;">📅 {calendar.month_name[month]} {year} Content Calendar</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Get or create calendar content
    profile_id = st.session_state.get('persona_id')
    if profile_id:
        get_or_create_calendar_content(profile_id, year, month, posting_dates, profile, groq_client)
    
    # Show post type distribution
    if posting_dates:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("### 📊 Post Type Distribution This Month")
        with col2:
            if st.button("🔄 Regenerate Distribution", key="regen_distribution"):
                # Clear existing data
                st.session_state.post_type_rotation = []
                month_key_prefix = f"{year}-{month:02d}"
                keys_to_remove = [key for key in st.session_state.content_cache.keys() if key.startswith(month_key_prefix)]
                for key in keys_to_remove:
                    del st.session_state.content_cache[key]
                
                # Generate new content
                if profile_id:
                    st.session_state.post_type_rotation = generate_post_type_rotation(profile, len(posting_dates))
                    
                    # Generate new titles
                    with st.spinner("Regenerating all content..."):
                        progress_bar = st.progress(0)
                        for i, day in enumerate(posting_dates):
                            date_key = f"{year}-{month:02d}-{day:02d}"
                            date_str = f"{calendar.month_name[month]} {day}, {year}"
                            post_type = get_post_type_for_date(date_key, posting_dates, profile)
                            prompt = generate_content_prompt(profile, date_str, post_type)
                            content = generate_calendar_content_with_groq(groq_client, prompt)
                            st.session_state.content_cache[date_key] = content
                            progress_bar.progress((i + 1) / len(posting_dates))
                        progress_bar.empty()
                    
                    # Save updated content to MongoDB
                    calendar_content_data = {
                        "content_cache": {k: v for k, v in st.session_state.content_cache.items() 
                                        if k.startswith(f"{year}-{month:02d}")},
                        "post_type_rotation": st.session_state.post_type_rotation
                    }
                    save_calendar_content_to_mongodb(profile_id, year, month, calendar_content_data)
                
                st.rerun()
        
        # Generate and show post type rotation
        if (not st.session_state.post_type_rotation or 
            len(st.session_state.post_type_rotation) != len(posting_dates)):
            st.session_state.post_type_rotation = generate_post_type_rotation(profile, len(posting_dates))
        
        # Display post type distribution
        post_type_counts = {}
        for post_type in st.session_state.post_type_rotation:
            post_type_counts[post_type] = post_type_counts.get(post_type, 0) + 1
        
        # Show distribution in a nice format
        if post_type_counts:
            cols = st.columns(min(len(post_type_counts), 4))
            for i, (post_type, count) in enumerate(post_type_counts.items()):
                with cols[i % 4]:
                    st.metric(post_type, f"{count} posts")
    
    # Show dialog if a date is selected
    if st.session_state.show_dialog and st.session_state.selected_date:
        date_key = st.session_state.selected_date
        day = int(date_key.split('-')[2])
        date_str = f"{calendar.month_name[month]} {day}, {year}"
        
        # Show dialog in a prominent container
        with st.container():
            st.markdown("---")
            show_content_dialog(date_key, date_str, profile, groq_client, posting_dates)
            st.markdown("---")
    
    # Get calendar data
    cal = calendar.monthcalendar(year, month)
    days_of_week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    # Display days of week header
    cols = st.columns(7)
    for i, day in enumerate(days_of_week):
        cols[i].markdown(f"<div style='text-align: center; font-weight: 700; font-size: 18px; color: #4a5568; padding: 10px;'>{day}</div>", unsafe_allow_html=True)
    
    # Display calendar weeks
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            with cols[i]:
                if day == 0:
                    st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)  # Empty day
                elif day in posting_dates:
                    # This is a posting day
                    date_key = f"{year}-{month:02d}-{day:02d}"
                    post_type = get_post_type_for_date(date_key, posting_dates, profile)
                    
                    # Content should already be in cache from get_or_create_calendar_content
                    title_preview = st.session_state.content_cache.get(date_key, "Loading...")
                    if len(title_preview) > 30:
                        title_preview = title_preview[:30] + "..."
                    
                    st.markdown(f"""
                    <div class="calendar-posting-day">
                        <div class="calendar-day-number">{day}</div>
                        <div style="font-size: 12px; margin: 4px 0;">🎯 POST DAY</div>
                        <div style="font-size: 10px; color: #ffd700; font-weight: bold; margin: 2px 0;">{post_type}</div>
                        <div class="calendar-post-preview">{title_preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Click to view full content
                    if st.button("📖 View", key=f"view_{date_key}", help="Click to view full content", use_container_width=True):
                        st.session_state.show_dialog = True
                        st.session_state.selected_date = date_key
                        st.rerun()
                else:
                    # Regular day (no posting)
                    st.markdown(f"""
                    <div class="calendar-day">
                        <div class="calendar-day-number" style="color: #a0aec0;">{day}</div>
                    </div>
                    """, unsafe_allow_html=True)

# MongoDB connection setup (KEEP ALL EXISTING FUNCTIONS)
def get_mongodb_client():
    """Get MongoDB client connection"""
    try:
        if not MONGODB_AVAILABLE:
            return None
        
        # Try to get MongoDB URI from environment, fallback to local
        mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        st.error(f"MongoDB connection failed: {str(e)}")
        return None
    except Exception as e:
        st.error(f"MongoDB error: {str(e)}")
        return None

def get_profiles_collection():
    """Get the profiles collection"""
    client = get_mongodb_client()
    if client is not None:
        db = client.linkedin_content_planner
        return db.profiles
    return None

def save_profile_to_mongodb(persona):
    """Save user profile to MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return False
        
        # Add timestamp
        persona['updated_at'] = datetime.now().isoformat()
        
        # Use upsert to update if exists, insert if new
        result = collection.replace_one(
            {"_id": persona["_id"]}, 
            persona, 
            upsert=True
        )
        
        return True
    except Exception as e:
        st.error(f"Error saving profile to MongoDB: {str(e)}")
        return False

def load_profiles_from_mongodb():
    """Load all profiles from MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return []
        
        profiles = list(collection.find().sort("updated_at", -1))
        return profiles
    except Exception as e:
        st.error(f"Error loading profiles from MongoDB: {str(e)}")
        return []

def delete_profile_from_mongodb(profile_id):
    """Delete a profile from MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return False
        
        result = collection.delete_one({"_id": profile_id})
        return result.deleted_count > 0
    except Exception as e:
        st.error(f"Error deleting profile: {str(e)}")
        return False

def load_profile_from_mongodb(profile_id):
    """Load a specific profile from MongoDB"""
    try:
        collection = get_profiles_collection()
        if collection is None:
            return None
        
        profile = collection.find_one({"_id": profile_id})
        return profile
    except Exception as e:
        st.error(f"Error loading profile: {str(e)}")
        return None

def load_profile_into_session(profile):
    """Load a profile from MongoDB into session state"""
    try:
        # Basic info
        st.session_state.name = profile['basic_info']['name']
        st.session_state.role = profile['basic_info']['role']
        st.session_state.linkedin_goal = profile['basic_info']['linkedin_goal']
        st.session_state.active_on_linkedin = profile['basic_info']['active_on_linkedin']
        
        # Content preferences
        st.session_state.posts_per_week = profile['content_preferences']['posts_per_week']
        st.session_state.posting_days = profile['content_preferences']['posting_days']
        st.session_state.preferred_content_types = profile['content_preferences']['preferred_content_types']
        st.session_state.preferred_tone = profile['content_preferences']['preferred_tone']
        st.session_state.preferred_post_types = profile['content_preferences'].get('preferred_post_types', ["Storytelling", "Personal Experience", "Industry Insights", "How-to/Educational"])
        
        # Clear any existing calendar data in session state
        st.session_state.content_cache = {}
        st.session_state.post_type_rotation = []
        
        # Active user specific data
        if profile['basic_info']['active_on_linkedin'] and 'linkedin_profile' in profile:
            linkedin_profile = profile['linkedin_profile']
            st.session_state.linkedin_url = linkedin_profile['url']
            st.session_state.current_style = linkedin_profile['current_style']
            st.session_state.differentiation_goals = linkedin_profile['differentiation_goals']
            st.session_state.topics_of_interest = linkedin_profile['topics_of_interest']
            st.session_state.allow_analysis = linkedin_profile['allow_analysis']
            
            # Load reference creators for active users
            if 'reference_creators' in linkedin_profile:
                st.session_state.reference_creators = [creator['url'] for creator in linkedin_profile['reference_creators']]
                st.session_state.creator_preferences = {}
                for creator in linkedin_profile['reference_creators']:
                    if 'preferences' in creator:
                        st.session_state.creator_preferences[creator['url']] = creator['preferences']
                st.session_state.creator_likes = linkedin_profile.get('creator_likes', '')
                # Handle both old single category and new multiple categories
                if 'selected_categories' in linkedin_profile:
                    st.session_state.selected_categories = linkedin_profile['selected_categories']
                elif 'selected_category' in linkedin_profile:
                    st.session_state.selected_categories = [linkedin_profile['selected_category']]
                else:
                    st.session_state.selected_categories = []
        
        # Inactive user specific data
        if not profile['basic_info']['active_on_linkedin'] and 'reference_info' in profile:
            reference_info = profile['reference_info']
            # Handle both old single category and new multiple categories
            if 'selected_categories' in reference_info:
                st.session_state.selected_categories = reference_info['selected_categories']
            elif 'selected_category' in reference_info:
                st.session_state.selected_categories = [reference_info['selected_category']]
            else:
                st.session_state.selected_categories = []
            
            st.session_state.creator_likes = reference_info['creator_likes']
            
            # Load reference creators
            st.session_state.reference_creators = [creator['url'] for creator in reference_info['reference_creators']]
            
            # Load creator preferences
            st.session_state.creator_preferences = {}
            for creator in reference_info['reference_creators']:
                if 'preferences' in creator:
                    st.session_state.creator_preferences[creator['url']] = creator['preferences']
        
        # Load custom creators if they exist in the profile
        if 'custom_creators_list' in profile:
            st.session_state.custom_creators_list = profile['custom_creators_list']
        
        # Set completion flags
        st.session_state.form_completed = True
        st.session_state.persona = profile
        st.session_state.persona_id = profile['_id']
        st.session_state.current_step = 4  # Go directly to final step
        
        # Load company type
        st.session_state.is_company = profile['basic_info'].get('is_company', False)

        # Load achievements and context
        if 'achievements_list' in profile:
            st.session_state.achievements_list = profile['achievements_list']

        if 'company_info_list' in profile:
            st.session_state.company_info_list = profile['company_info_list']

        if 'personal_context_list' in profile:
            st.session_state.personal_context_list = profile['personal_context_list']
        
    except Exception as e:
        st.error(f"Error loading profile: {str(e)}")

def get_posts_by_influencers(profile_names: list[str]):
    """Get posts by specific influencer names from ChromaDB"""
    try:
        # Step 1: Connect to ChromaDB
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection(name="posts_collection")

        # Step 2: Fetch all metadata + documents
        results = collection.get(include=["documents", "metadatas"])

        # Step 3: Filter by selected profile_names
        posts = [
            {
                "profile_name": meta["profile_name"],
                "category": meta["category"],
                "post_text": doc,
                "scraped_at": meta.get("scraped_at", "Unknown"),
                "post_length": len(doc)
            }
            for doc, meta in zip(results["documents"], results["metadatas"])
            if meta["profile_name"] in profile_names
        ]

        return posts
    except Exception as e:
        st.error(f"Error accessing ChromaDB: {str(e)}")
        return []

def check_influencers_in_chromadb(profile_names: list[str]):
    """Check which influencers have posts available in ChromaDB"""
    try:
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection(name="posts_collection")
        
        results = collection.get(include=["metadatas"])
        
        available_influencers = set()
        for meta in results["metadatas"]:
            if meta["profile_name"] in profile_names:
                available_influencers.add(meta["profile_name"])
        
        return list(available_influencers)
    except Exception as e:
        st.error(f"Error checking ChromaDB: {str(e)}")
        return []

def load_embedding_model():
    """Load the sentence transformer model for embeddings"""
    try:
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            st.error("Sentence Transformers not available. Please install: pip install sentence-transformers")
            return None
        model = SentenceTransformer('all-MiniLM-L6-v2')
        return model
    except Exception as e:
        st.error(f"Error loading embedding model: {str(e)}")
        return None

def search_similar_posts(query, selected_creators, top_k=5, include_user_posts=False, user_name=None):
    """Search for similar posts in ChromaDB based on query and selected creators"""
    try:
        # Load embedding model
        model = load_embedding_model()
        if not model:
            return []
        
        # Embed the query
        query_embedding = model.encode([query])
        
        # Connect to ChromaDB
        client = chromadb.PersistentClient(path="chroma_db")
        collection = client.get_collection(name="posts_collection")
        
        # Build the list of creators to search
        creators_to_search = selected_creators.copy() if selected_creators else []
        
        # Add user's own posts if requested and user_name is provided
        if include_user_posts and user_name:
            creators_to_search.append(user_name)
        
        # If no creators to search, return empty
        if not creators_to_search:
            return []
        
        # Search for similar posts
        results = collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=top_k * 3,  # Get more results to filter by creators
            include=["documents", "metadatas", "distances"]
        )
        
        # Filter results by selected creators (including user if specified)
        filtered_posts = []
        for i, (doc, meta, distance) in enumerate(zip(
            results["documents"][0], 
            results["metadatas"][0], 
            results["distances"][0]
        )):
            if meta["profile_name"] in creators_to_search:
                filtered_posts.append({
                    "profile_name": meta["profile_name"],
                    "category": meta["category"],
                    "post_text": doc,
                    "similarity_score": 1 - distance,  # Convert distance to similarity
                    "distance": distance,
                    "is_user_post": meta["profile_name"] == user_name if user_name else False
                })
        
        # Sort by similarity and return top_k
        filtered_posts.sort(key=lambda x: x["similarity_score"], reverse=True)
        return filtered_posts[:top_k]
        
    except Exception as e:
        st.error(f"Error searching similar posts: {str(e)}")
        return []
    
def generate_content_with_groq(query, similar_posts, user_persona, user_posts=None, is_company_post=False, selected_achievements=None, selected_company_info=None, selected_personal_context=None):
    """Generate content using Groq API based on similar posts, user preferences, and optionally user's own posts"""
    try:
        if not GROQ_AVAILABLE:
            st.error("Groq not available. Please install: pip install groq")
            return None
        
        # Initialize Groq client
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            st.error("GROQ_API_KEY not found in environment variables")
            return None
        
        client = Groq(api_key=groq_api_key)
        
        # Prepare context from similar posts
        posts_context = ""
        for i, post in enumerate(similar_posts, 1):
            posts_context += f"\n--- Reference Post {i} (by {post['profile_name']}) ---\n"
            posts_context += f"Similarity Score: {post['similarity_score']:.3f}\n"
            posts_context += f"Content: {post['post_text'][:500]}...\n"
        
        # Prepare user's own posts context if available
        user_posts_context = ""
        if user_posts and len(user_posts) > 0:
            user_posts_context = "\n\nYOUR PREVIOUS POSTS (for style reference):\n"
            for i, post in enumerate(user_posts[:3], 1):  # Use up to 3 recent posts
                user_posts_context += f"\n--- Your Post {i} ---\n"
                user_posts_context += f"Content: {post['post_text'][:400]}...\n"
        
        # Prepare user preferences context
        user_context = f"""
User Profile:
- Name: {user_persona['basic_info']['name']}
- Role: {user_persona['basic_info']['role']}
- LinkedIn Goal: {user_persona['basic_info']['linkedin_goal']}
- Preferred Content Types: {', '.join(user_persona['content_preferences']['preferred_content_types'])}
- Preferred Tone: {', '.join(user_persona['content_preferences']['preferred_tone'])}
"""
        
        # Prepare creator preferences context
        creator_context = ""
        if user_persona['basic_info']['active_on_linkedin'] and 'linkedin_profile' in user_persona:
            # For active users
            if 'reference_creators' in user_persona['linkedin_profile']:
                creator_context += f"\nWhat user likes about reference creators: {user_persona['linkedin_profile'].get('creator_likes', '')}\n"
                
                for creator in user_persona['linkedin_profile']['reference_creators']:
                    if 'preferences' in creator:
                        creator_context += f"\nAbout {creator['name']}:\n"
                        prefs = creator['preferences']
                        if prefs.get('tone'):
                            creator_context += f"- Liked tone: {', '.join(prefs['tone'])}\n"
                        if prefs.get('content_type'):
                            creator_context += f"- Liked content types: {', '.join(prefs['content_type'])}\n"
                        if prefs.get('style'):
                            creator_context += f"- Liked style: {', '.join(prefs['style'])}\n"
        elif 'reference_info' in user_persona:
            # For inactive users
            creator_context += f"\nWhat user likes about reference creators: {user_persona['reference_info']['creator_likes']}\n"
            
            for creator in user_persona['reference_info']['reference_creators']:
                if 'preferences' in creator:
                    creator_context += f"\nAbout {creator['name']}:\n"
                    prefs = creator['preferences']
                    if prefs.get('tone'):
                        creator_context += f"- Liked tone: {', '.join(prefs['tone'])}\n"
                    if prefs.get('content_type'):
                        creator_context += f"- Liked content types: {', '.join(prefs['content_type'])}\n"
                    if prefs.get('style'):
                        creator_context += f"- Liked style: {', '.join(prefs['style'])}\n"
        
        # Prepare achievements and context
        achievements_context = ""
        if selected_achievements:
            achievements_context += "\n\nACHIEVEMENTS TO INCORPORATE:\n"
            for achievement in selected_achievements:
                achievements_context += f"\n- {achievement['title']}: {achievement['description']}"
                if achievement['impact']:
                    achievements_context += f" (Impact: {achievement['impact']})"

        company_context = ""
        if selected_company_info:
            company_context += "\n\nCOMPANY INFORMATION TO INCORPORATE:\n"
            for info in selected_company_info:
                company_context += f"\n- {info['title']}: {info['content']}"

        personal_context_info = ""
        if selected_personal_context:
            personal_context_info += "\n\nPERSONAL CONTEXT TO INCORPORATE:\n"
            for context in selected_personal_context:
                personal_context_info += f"\n- {context['title']}: {context['content']}"
        
        # Create the prompt based on post type
        if is_company_post:
            prompt = f"""
You are a LinkedIn content creation expert specializing in company posts. Based on the user's query and their company profile, create engaging LinkedIn content that is educational and includes a clear call to action.

USER QUERY: "{query}"

{user_context}

{achievements_context}

{company_context}

{personal_context_info}

INSTRUCTIONS FOR COMPANY POST:
1. Create a LinkedIn post that addresses the user's query: "{query}"
2. Keep it SHORT - under 200 words maximum
3. Use an EDUCATIONAL tone - provide valuable information or insights
4. Include a clear CALL TO ACTION at the end (e.g., "Learn more," "Visit our website," "Contact us," "Book a consultation")
5. If achievements or company info are provided, naturally incorporate them into the post
6. Make it professional but engaging
7. Include relevant hashtags (3-5) at the end
8. Use emojis sparingly and professionally
9. Structure: Hook → Educational content → Call to action → Hashtags
10. Focus on business value and industry insights

Generate a compelling LinkedIn company post:
"""
        else:
            prompt = f"""
You are a LinkedIn content creation expert. Based on the user's query, reference posts, and their own writing style, create engaging LinkedIn content that matches their preferences.

USER QUERY: "{query}"

{user_context}

{creator_context}

REFERENCE POSTS (for inspiration):
{posts_context}

{user_posts_context}

INSTRUCTIONS FOR PERSONAL POST:
1. Create a LinkedIn post that addresses the user's query: "{query}"
2. Draw inspiration from the reference posts but make it original and unique
3. If user's previous posts are provided, maintain consistency with their established writing style and voice
4. Match the user's preferred content types and tone
5. Incorporate elements that the user likes about their reference creators
6. Make it engaging, authentic, and valuable for LinkedIn audience
7. Include relevant hashtags (3-5) at the end
8. Keep it within 1300 characters for optimal LinkedIn engagement
9. Use emojis and proper formatting for LinkedIn
10. Focus on personal experiences, lessons learned, or motivational insights
11. If the user is active on LinkedIn, blend their existing style with inspiration from reference creators

Generate a compelling LinkedIn personal post:
"""
        
        # Generate content using Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1000
        )
        
        return chat_completion.choices[0].message.content
        
    except Exception as e:
        st.error(f"Error generating content with Groq: {str(e)}")
        return None

def add_custom_creator_section():
    """Display section for adding custom creators"""
    st.markdown("""
    <div class="content-card">
        <h3 style="color: #2d3748; font-size: 24px;">➕ Add Custom Creator</h3>
        <p style="color: #2d3748; font-size: 16px; font-weight: 600;">Add LinkedIn creators you want to follow and scrape their content.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize custom creators in session state
    if 'custom_creators_list' not in st.session_state:
        st.session_state.custom_creators_list = []
    
    # Form to add new creator
    with st.form("add_custom_creator"):
        col1, col2 = st.columns(2)
        
        with col1:
            creator_name = st.text_input(
                "**Creator Name**",
                placeholder="e.g., Gary Vaynerchuk"
            )
            
            creator_url = st.text_input(
                "**LinkedIn Profile URL**",
                placeholder="https://linkedin.com/in/profile-name"
            )
        
        with col2:
            # Load categories from existing CSV for consistency
            df = load_linkedin_profiles()
            categories = sorted(df['Cat'].unique()) if not df.empty else [
                "Marketing", "Leadership", "Entrepreneurship", "Technology", 
                "Sales", "Personal Development", "Business Strategy"
            ]
            
            creator_category = st.selectbox(
                "**Category**",
                options=categories
            )
            
            creator_description = st.text_area(
                "**Description (Optional)**",
                placeholder="Brief description of what you like about this creator...",
                height=80
            )
        
        # Preferences for this creator
        st.markdown("**What do you like about this creator's content?**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            tone_prefs = st.multiselect(
                "**Tone**",
                options=["Inspirational", "Honest/Authentic", "Tactical/Practical", "Funny/Humorous", "Analytical/Data-driven", "Direct/Blunt"]
            )
        
        with col2:
            content_prefs = st.multiselect(
                "**Content Type**",
                options=["Stories/Personal", "Tips & How-to", "Industry Insights", "Opinion/Hot Takes", "Educational", "Behind-the-scenes"]
            )
        
        with col3:
            style_prefs = st.multiselect(
                "**Style**",
                options=["Visual/Graphics", "Long-form posts", "Short & punchy", "Data-driven", "Storytelling", "Question-based"]
            )
        
        submitted = st.form_submit_button("**➕ Add Creator**", type="primary", use_container_width=True)
        
        if submitted:
            if creator_name.strip() and creator_url.strip():
                # Validate LinkedIn URL
                if "linkedin.com/in/" not in creator_url:
                    st.error("Please enter a valid LinkedIn profile URL (should contain 'linkedin.com/in/')")
                else:
                    # Add creator to list
                    new_creator = {
                        'name': creator_name.strip(),
                        'url': creator_url.strip(),
                        'category': creator_category,
                        'description': creator_description.strip(),
                        'preferences': {
                            'tone': tone_prefs,
                            'content_type': content_prefs,
                            'style': style_prefs
                        },
                        'added_at': datetime.now().isoformat(),
                        'scraped': False,
                        'posts_count': 0
                    }
                    
                    # Check for duplicates
                    existing_urls = [c['url'] for c in st.session_state.custom_creators_list]
                    if creator_url.strip() not in existing_urls:
                        st.session_state.custom_creators_list.append(new_creator)
                        st.success(f"✅ Added {creator_name} to your custom creators list!")
                        st.rerun()
                    else:
                        st.error("This creator is already in your list!")
            else:
                st.error("Please fill in both creator name and LinkedIn URL")

def display_custom_creators_list():
    """Display the list of custom creators"""
    if not st.session_state.get('custom_creators_list', []):
        st.info("**No custom creators added yet. Use the form above to add creators.**")
        return
    
    st.markdown("### **Your Custom Creators**")
    
    for i, creator in enumerate(st.session_state.custom_creators_list):
        with st.container():
            st.markdown(f"""
            <div class="creator-card">
                <div class="profile-card">
                    <div class="profile-image">
                        {get_creator_initials(creator['name'])}
                    </div>
                    <div class="profile-info">
                        <div class="profile-name">{creator['name']}</div>
                        <div class="profile-title">{creator['category']}</div>
                        <div class="profile-description">{creator.get('description', 'No description')}</div>
                        <a href="{creator['url']}" target="_blank" style="color: #667eea; font-weight: 600; text-decoration: none;">🔗 View LinkedIn Profile</a>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Status and actions
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                if creator['scraped']:
                    st.success(f"✅ Scraped ({creator['posts_count']} posts)")
                else:
                    st.warning("⏳ Not scraped yet")
            
            with col2:
                if st.button(f"🔄 Scrape Posts", key=f"scrape_{i}", use_container_width=True):
                    scrape_creator_posts(creator, i)
            
            with col3:
                if st.button(f"✏️ Edit", key=f"edit_{i}", use_container_width=True):
                    st.session_state[f'editing_creator_{i}'] = True
                    st.rerun()
            
            with col4:
                if st.button(f"🗑️ Remove", key=f"remove_{i}", use_container_width=True):
                    st.session_state.custom_creators_list.pop(i)
                    st.success(f"Removed {creator['name']}")
                    st.rerun()
            
            # Show preferences
            if creator['preferences']['tone'] or creator['preferences']['content_type'] or creator['preferences']['style']:
                st.markdown('<div style="background: rgba(102, 126, 234, 0.1); border-radius: 12px; padding: 15px; margin-top: 15px; border: 1px solid rgba(102, 126, 234, 0.2);">', unsafe_allow_html=True)
                st.markdown('<div style="font-weight: 600; color: #4a5568; margin-bottom: 10px; font-size: 14px;">Your Preferences:</div>', unsafe_allow_html=True)
                
                badges_html = ""
                for tone in creator['preferences']['tone']:
                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">{tone}</span>'
                for content in creator['preferences']['content_type']:
                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #48bb78 0%, #38b2ac 100%);">{content}</span>'
                for style in creator['preferences']['style']:
                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">{style}</span>'
                
                st.markdown(badges_html, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")

def scrape_creator_posts(creator, creator_index):
    """Scrape posts for a specific creator using the LinkedIn scraper"""
    try:
        # Show progress without detailed logs
        with st.spinner(f"Scraping posts for {creator['name']}..."):
            try:
                # Import the scraper class
                sys.path.append(str(Path.cwd()))
                from linkedin_scraper import LinkedInScraper
                
                # Initialize scraper
                scraper = LinkedInScraper(
                    headless=True,
                    debug=False,
                    max_posts=50,
                    chroma_db_path="chroma_db"
                )
                
                # Scrape posts
                posts = scraper.scrape_user_profile(creator['url'], creator['category'])                
                # Update creator status
                st.session_state.custom_creators_list[creator_index]['scraped'] = True
                st.session_state.custom_creators_list[creator_index]['posts_count'] = len(posts) if posts else 0
                st.session_state.custom_creators_list[creator_index]['last_scraped'] = datetime.now().isoformat()
                
                # Close scraper
                if hasattr(scraper, 'close'):
                    scraper.close()
                
                # Show success
                if posts and len(posts) > 0:
                    st.success(f"✅ Successfully scraped {len(posts)} posts from {creator['name']}!")
                else:
                    st.warning(f"⚠️ No posts found for {creator['name']}. This could be due to privacy settings or login issues.")
                
                st.rerun()
                
            except ImportError as e:
                st.error(f"Could not import LinkedIn scraper: {str(e)}")
                st.info("Please ensure 'linkedin_scraper.py' exists and contains the LinkedInScraper class.")
                
            except Exception as e:
                st.error(f"Error during scraping {creator['name']}: {str(e)}")
                
    except Exception as e:
        st.error(f"Error setting up scraper: {str(e)}")

def scrape_user_own_posts(user_url, user_name):
    """Scrape the user's own LinkedIn posts"""
    try:
        with st.spinner(f"Scraping your LinkedIn posts..."):
            try:
                # Import the scraper class
                sys.path.append(str(Path.cwd()))
                from linkedin_scraper import LinkedInScraper
                
                # Initialize scraper
                scraper = LinkedInScraper(
                    headless=True,
                    debug=False,
                    max_posts=30,  # Get recent posts
                    chroma_db_path="chroma_db"
                )
                
                # Scrape posts with user's name as profile name and "Personal" as category
                posts = scraper.scrape_user_profile(user_url, "Personal", profile_name_override=user_name)
                
                # Close scraper
                if hasattr(scraper, 'close'):
                    scraper.close()
                
                return posts
                
            except ImportError as e:
                st.error(f"Could not import LinkedIn scraper: {str(e)}")
                return []
                
            except Exception as e:
                st.error(f"Error during scraping your posts: {str(e)}")
                return []
                
    except Exception as e:
        st.error(f"Error setting up scraper for your posts: {str(e)}")
        return []

def display_memory_feeder_interface():
    """Interface for adding user/company context"""
    
    st.markdown("### 🧠 Memory Feeder - Add Your Context")
    st.markdown("**Add personal achievements, company news, or context that you want to incorporate into your posts.**")
    
    tab1, tab2, tab3 = st.tabs(["👤 Personal Context", "🏢 Company Info", "🏆 Achievements"])
    
    # Initialize lists if they don't exist
    if 'personal_context_list' not in st.session_state:
        st.session_state.personal_context_list = []
    if 'company_info_list' not in st.session_state:
        st.session_state.company_info_list = []
    if 'achievements_list' not in st.session_state:
        st.session_state.achievements_list = []
    
    with tab1:
        st.markdown("#### Add Personal Context")
        
        with st.form("personal_context_form"):
            context_type = st.selectbox(
                "Context Type",
                ["Personal", "Professional", "Experience", "Background", "Values"]
            )
            
            context_title = st.text_input("Title", placeholder="e.g., 'My Remote Work Philosophy'")
            context_content = st.text_area(
                "Content", 
                placeholder="Describe your experience, philosophy, or background...",
                height=100
            )
            
            context_tags = st.text_input(
                "Tags (comma-separated)", 
                placeholder="remote work, leadership, team management"
            )
            
            importance = st.slider("Importance Level", 0.0, 1.0, 0.5, 0.1)
            
            if st.form_submit_button("💾 Save Personal Context"):
                if context_title and context_content:
                    tags_list = [tag.strip() for tag in context_tags.split(",") if tag.strip()]
                    context_item = {
                        'id': f"context_{len(st.session_state.personal_context_list)}_{int(time.time())}",
                        'type': context_type.lower(),
                        'title': context_title,
                        'content': context_content,
                        'tags': tags_list,
                        'importance': importance,
                        'created_at': datetime.now().isoformat()
                    }
                    st.session_state.personal_context_list.append(context_item)
                    st.success(f"✅ Personal context saved!")
                    st.rerun()
                else:
                    st.warning("Please fill in title and content")
        
        # Display existing personal context
        if st.session_state.personal_context_list:
            st.markdown("#### Your Personal Context")
            for i, context in enumerate(st.session_state.personal_context_list):
                with st.expander(f"**{context['title']}** ({context['type']})"):
                    st.markdown(f"**Content:** {context['content']}")
                    if context['tags']:
                        st.markdown(f"**Tags:** {', '.join(context['tags'])}")
                    st.markdown(f"**Importance:** {context['importance']}")
                    if st.button(f"🗑️ Delete", key=f"del_context_{i}"):
                        st.session_state.personal_context_list.pop(i)
                        st.rerun()
    
    with tab2:
        st.markdown("#### Add Company Information")
        
        with st.form("company_info_form"):
            company_name = st.text_input("Company Name")
            info_type = st.selectbox(
                "Information Type",
                ["Culture", "Values", "News", "Achievements", "Products", "Industry", "Mission", "Partnership", "Launch"]
            )
            
            company_title = st.text_input("Title", placeholder="e.g., 'New Partnership with TechCorp'")
            company_content = st.text_area(
                "Content",
                placeholder="Describe company culture, recent news, achievements, partnerships...",
                height=100
            )
            
            relevance = st.slider("Relevance to Your Content", 0.0, 1.0, 0.5, 0.1)
            
            if st.form_submit_button("💾 Save Company Info"):
                if company_name and company_title and company_content:
                    company_item = {
                        'id': f"company_{len(st.session_state.company_info_list)}_{int(time.time())}",
                        'company_name': company_name,
                        'type': info_type.lower(),
                        'title': company_title,
                        'content': company_content,
                        'relevance': relevance,
                        'created_at': datetime.now().isoformat()
                    }
                    st.session_state.company_info_list.append(company_item)
                    st.success(f"✅ Company info saved!")
                    st.rerun()
                else:
                    st.warning("Please fill in all fields")
        
        # Display existing company info
        if st.session_state.company_info_list:
            st.markdown("#### Your Company Information")
            for i, info in enumerate(st.session_state.company_info_list):
                with st.expander(f"**{info['title']}** ({info['company_name']})"):
                    st.markdown(f"**Type:** {info['type']}")
                    st.markdown(f"**Content:** {info['content']}")
                    st.markdown(f"**Relevance:** {info['relevance']}")
                    if st.button(f"🗑️ Delete", key=f"del_company_{i}"):
                        st.session_state.company_info_list.pop(i)
                        st.rerun()
    
    with tab3:
        st.markdown("#### Add Achievements & Experiences")
        
        with st.form("achievements_form"):
            achievement_type = st.selectbox(
                "Achievement Type",
                ["Project", "Award", "Milestone", "Learning", "Leadership", "Innovation", "Recognition", "Launch"]
            )
            
            achievement_title = st.text_input("Title", placeholder="e.g., 'Led Digital Transformation Project'")
            achievement_desc = st.text_area(
                "Description",
                placeholder="Describe what you accomplished...",
                height=100
            )
            
            impact = st.text_area(
                "Impact (Optional)",
                placeholder="What was the result or impact?",
                height=68
            )
            
            date = st.text_input("Date (Optional)", placeholder="2024 or Q1 2024")
            skills = st.text_input(
                "Skills Used (comma-separated)", 
                placeholder="leadership, python, project management"
            )
            
            if st.form_submit_button("💾 Save Achievement"):
                if achievement_title and achievement_desc:
                    skills_list = [skill.strip() for skill in skills.split(",") if skill.strip()]
                    achievement_item = {
                        'id': f"achievement_{len(st.session_state.achievements_list)}_{int(time.time())}",
                        'type': achievement_type.lower(),
                        'title': achievement_title,
                        'description': achievement_desc,
                        'impact': impact,
                        'date': date,
                        'skills': skills_list,
                        'created_at': datetime.now().isoformat()
                    }
                    st.session_state.achievements_list.append(achievement_item)
                    st.success(f"✅ Achievement saved!")
                    st.rerun()
                else:
                    st.warning("Please fill in title and description")
        
        # Display existing achievements
        if st.session_state.achievements_list:
            st.markdown("#### Your Achievements")
            for i, achievement in enumerate(st.session_state.achievements_list):
                with st.expander(f"**{achievement['title']}** ({achievement['type']})"):
                    st.markdown(f"**Description:** {achievement['description']}")
                    if achievement['impact']:
                        st.markdown(f"**Impact:** {achievement['impact']}")
                    if achievement['date']:
                        st.markdown(f"**Date:** {achievement['date']}")
                    if achievement['skills']:
                        st.markdown(f"**Skills:** {', '.join(achievement['skills'])}")
                    if st.button(f"🗑️ Delete", key=f"del_achievement_{i}"):
                        st.session_state.achievements_list.pop(i)
                        st.rerun()

def display_content_generation_page():
    """Display the content generation page for both active and inactive users"""
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #2d3748; font-size: 32px;">🚀 AI Content Generation</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Generate LinkedIn content based on your reference creators and preferences.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if user has completed profile setup
    if not st.session_state.get('form_completed', False) or not st.session_state.get('persona', {}):
        st.warning("**⚠️ Please complete your profile setup first before generating content.**")
        if st.button("**Go to Profile Setup**", type="primary"):
            st.session_state.current_step = 1
            st.rerun()
        return
    
    persona = st.session_state.persona
    
    # Check if this is a company profile from the stored profile data
    is_company_profile = persona.get('basic_info', {}).get('is_company', False)
    
    # Collect all creator names from both reference creators and custom creators
    all_creator_names = []
    
    # Add reference creators (works for both active and inactive users)
    if persona['basic_info']['active_on_linkedin'] and 'linkedin_profile' in persona:
        # For active users
        if 'reference_creators' in persona['linkedin_profile']:
            reference_creator_names = [creator['name'] for creator in persona['linkedin_profile']['reference_creators']]
            all_creator_names.extend(reference_creator_names)
    elif 'reference_info' in persona:
        # For inactive users
        reference_creator_names = [creator['name'] for creator in persona['reference_info']['reference_creators']]
        all_creator_names.extend(reference_creator_names)
    
    # Add custom creators that have been scraped
    if st.session_state.get('custom_creators_list', []):
        custom_creator_names = [creator['name'] for creator in st.session_state.custom_creators_list if creator['scraped']]
        all_creator_names.extend(custom_creator_names)
    
    # Get available creators from ChromaDB (only needed for personal posts)
    available_creators = []
    if not is_company_profile:
        available_creators = check_influencers_in_chromadb(all_creator_names) if all_creator_names else []
    
    # For active users, show option to scrape their own posts (only for personal profiles)
    user_posts = []
    if persona['basic_info']['active_on_linkedin'] and not is_company_profile:
        st.markdown("### **Your LinkedIn Posts**")
        
        # Check if user's own posts are available
        user_name = persona['basic_info']['name']
        user_available = check_influencers_in_chromadb([user_name])
        
        col1, col2 = st.columns(2)
        
        with col1:
            if user_available:
                user_posts = get_posts_by_influencers([user_name])
                st.success(f"✅ Found {len(user_posts)} of your posts in database")
            else:
                st.info("📝 Your posts not found in database")
        
        with col2:
            if st.button("**🔄 Scrape My Posts**", use_container_width=True, key="scrape_posts_generate_tab"):
                if 'linkedin_profile' in persona and 'url' in persona['linkedin_profile']:
                    scraped_posts = scrape_user_own_posts(persona['linkedin_profile']['url'], user_name)
                    if scraped_posts:
                        st.success(f"✅ Scraped {len(scraped_posts)} of your posts!")
                        st.rerun()
                    else:
                        st.warning("⚠️ No posts found or scraping failed")
                else:
                    st.error("❌ LinkedIn URL not found in profile")
    
    # Content generation interface
    st.markdown("### **Generate Content**")

    # Use company post logic if this is a company profile
    is_company_post = is_company_profile

    # Check if we're showing full generation from calendar
    if st.session_state.get('show_full_generation', False) and st.session_state.get('calendar_topic', ''):
        st.info(f"**📅 Generating full post for calendar topic:** {st.session_state.calendar_topic}")
        topic_query = st.text_area(
            "**Edit the topic or use as-is:**",
            value=st.session_state.calendar_topic,
            height=100,
            key="content_topic_from_calendar"
        )
        
        # Clear the calendar generation flag after setting the topic
        if st.button("**Clear Calendar Topic**", key="clear_calendar_topic"):
            st.session_state.show_full_generation = False
            st.session_state.calendar_topic = ''
            st.rerun()
    else:
        # Topic input and post type selection
        if is_company_profile:
            # For company profiles, always use company post logic
            st.info("🏢 **Company Profile**: Using company post generation (shorter, educational content with CTAs)")
            topic_query = st.text_area(
                "**What topic do you want to create content about?**",
                placeholder="e.g., 'Benefits of our integration platform', 'How to streamline business processes', 'Industry trends in integration systems'...",
                height=100,
                key="content_topic"
            )
        else:
            # For personal profiles, show the choice
            col1, col2 = st.columns([3, 1])

            with col1:
                topic_query = st.text_area(
                    "**What topic do you want to create content about?**",
                    placeholder="e.g., 'How to build personal brand on LinkedIn', 'Tips for remote work productivity', 'Lessons learned from startup failure'...",
                    height=100,
                    key="content_topic"
                )

            with col2:
                # Add company post checkbox with explanation
                is_company_post = st.checkbox(
                    "**Company Post**",
                    value=False,
                    help="Company posts are shorter (~200 words), educational, and include CTAs. Personal posts are longer (~500 words) and experience-based."
                )

    # Check if we can proceed
    if not is_company_post and not available_creators:
        st.warning("**⚠️ No reference creators found. Please add reference creators or switch to Company Post mode.**")
        return

    # Advanced options
    with st.expander("**⚙️ Advanced Options**"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if not is_company_post:
                num_reference_posts = st.slider(
                    "**Number of reference posts to use**",
                    min_value=3,
                    max_value=10,
                    value=5,
                    help="More posts provide more context but may slow down generation"
                )
            else:
                st.info("Reference posts not used for company posts")
                num_reference_posts = 0
        
        with col2:
            if user_posts and not is_company_profile:
                use_own_posts_for_style = st.checkbox(
                    "**Use your posts for writing style**",
                    value=True,
                    help="Include your previous posts to maintain your writing style"
                )
                
                if not is_company_post:
                    include_own_posts_in_search = st.checkbox(
                        "**Include your posts in similarity search**",
                        value=True,
                        help="Search through your own posts for similar content inspiration"
                    )
                else:
                    include_own_posts_in_search = False
            else:
                use_own_posts_for_style = False
                include_own_posts_in_search = False
        
        with col3:
            content_length = st.selectbox(
                "**Preferred content length**",
                options=["Short (< 500 chars)", "Medium (500-1000 chars)", "Long (1000+ chars)"],
                index=0 if is_company_post else 1
            )

    # Memory Feeder Interface (only for personal profiles)
    if not is_company_profile:
        display_memory_feeder_interface()
    else:
        # For company profiles, still show memory feeder but focused on company content
        display_memory_feeder_interface()

    st.markdown("---")

    # Initialize context selection variables
    selected_achievements = []
    selected_company_info = []
    selected_personal_context = []
# Achievement/Context Selection for Content Generation
    if (st.session_state.get('achievements_list', []) or 
        st.session_state.get('company_info_list', []) or 
        st.session_state.get('personal_context_list', [])):

        st.markdown("### **📋 Select Context to Include**")
        context_description = "company information" if is_company_profile else "achievements, company info, or personal context"
        st.markdown(f"**Choose {context_description} to incorporate into your post:**")

        if is_company_profile:
            # For company profiles, focus only on company info
            if st.session_state.get('company_info_list', []):
                st.markdown("**🏢 Company Information:**")
                cols = st.columns(2)
                for i, info in enumerate(st.session_state.company_info_list):
                    with cols[i % 2]:
                        # 👇 Fix: Make key unique to company profile
                        if st.checkbox(f"{info['title']}", key=f"select_company_company_{info['id']}"):
                            selected_company_info.append(info)

        else:
            # For personal profiles, show achievements, company info, and personal context
            col1, col2, col3 = st.columns(3)

            with col1:
                if st.session_state.get('achievements_list', []):
                    st.markdown("**🏆 Achievements:**")
                    for achievement in st.session_state.achievements_list:
                        if st.checkbox(f"{achievement['title']}", key=f"select_achievement_{achievement['id']}"):
                            selected_achievements.append(achievement)

            with col2:
                if st.session_state.get('company_info_list', []):
                    st.markdown("**🏢 Company Info:**")
                    for info in st.session_state.company_info_list:
                        # 👇 Fix: Make key unique to personal profile
                        if st.checkbox(f"{info['title']}", key=f"select_company_personal_{info['id']}"):
                            selected_company_info.append(info)

            with col3:
                if st.session_state.get('personal_context_list', []):
                    st.markdown("**👤 Personal Context:**")
                    for context in st.session_state.personal_context_list:
                        if st.checkbox(f"{context['title']}", key=f"select_context_{context['id']}"):
                            selected_personal_context.append(context)

        st.markdown("---")


    # Generate button
    post_type_label = "Company Post" if is_company_post else "Personal Post"
    button_text = f"**🚀 Generate {post_type_label}**"
    
    if st.button(button_text, type="primary", use_container_width=True):
        if not topic_query.strip():
            st.error("**Please enter a topic for content generation.**")
            return
        
        # Search for similar posts only if we have creators and it's not a company post
        similar_posts = []
        if available_creators and not is_company_post:
            with st.spinner("**🔍 Searching for similar posts...**"):
                # For active users, include their own posts in the search
                include_user_posts = persona['basic_info']['active_on_linkedin'] and len(user_posts) > 0 and include_own_posts_in_search
                user_name = persona['basic_info']['name'] if include_user_posts else None
                
                # Search for similar posts
                similar_posts = search_similar_posts(
                    query=topic_query,
                    selected_creators=available_creators,
                    top_k=num_reference_posts,
                    include_user_posts=include_user_posts,
                    user_name=user_name
                )
        
        # For personal posts, check if we have similar posts
        if not is_company_post and not similar_posts:
            st.error("**No similar posts found. Try a different topic or check if your creators have posts in the database.**")
            return
        
        # Display similar posts found (only for personal posts)
        if similar_posts and not is_company_post:
            user_posts_in_results = [p for p in similar_posts if p.get('is_user_post', False)]
            reference_posts_in_results = [p for p in similar_posts if not p.get('is_user_post', False)]
            
            success_message = f"**✅ Found {len(similar_posts)} similar posts"
            if user_posts_in_results:
                success_message += f" ({len(reference_posts_in_results)} from reference creators, {len(user_posts_in_results)} from your posts)"
            else:
                success_message += " from your reference creators"
            success_message += "!**"
            
            st.success(success_message)
            
            with st.expander("**📋 View Reference Posts Used**"):
                for i, post in enumerate(similar_posts, 1):
                    post_source = "Your Post" if post.get('is_user_post', False) else f"{post['profile_name']} (Reference)"
                    st.markdown(f"**Reference Post {i} - {post_source} (Similarity: {post['similarity_score']:.1%})**")
                    content_preview = post['post_text'][:200] + "..." if len(post['post_text']) > 200 else post['post_text']
                    st.markdown(f"\`\`\`\n{content_preview}\n\`\`\`")
                    st.markdown("---")
        
        # Prepare user's own posts if requested (only for personal profiles)
        user_posts_for_generation = []
        if use_own_posts_for_style and user_posts and not is_company_profile:
            user_posts_for_generation = sorted(user_posts, key=lambda x: x.get('scraped_at', ''), reverse=True)[:3]
            st.info(f"**📝 Using {len(user_posts_for_generation)} of your recent posts for style consistency**")
        
        generation_message = "**🤖 Generating company content with AI...**" if is_company_post else "**🤖 Generating content with AI...**"
        
        with st.spinner(generation_message):
            # Generate content with Groq
            generated_content = generate_content_with_groq(
                query=topic_query,
                similar_posts=similar_posts,
                user_persona=persona,
                user_posts=user_posts_for_generation,
                is_company_post=is_company_post,
                selected_achievements=selected_achievements,
                selected_company_info=selected_company_info,
                selected_personal_context=selected_personal_context
            )
        
        if generated_content:
            st.markdown(f"### **🎉 Generated {post_type_label}**")
            
            # Display generated content in a nice format
            border_color = "#f59e0b" if is_company_post else "#667eea"
            bg_color = "rgba(245, 158, 11, 0.1)" if is_company_post else "rgba(102, 126, 234, 0.1)"
            
            profile_type_indicator = " (Company Profile)" if is_company_profile else " (Personal Profile)"
            
            st.markdown(f"""
            <div class="generated-post-container" style="background: {bg_color}; border: 2px solid {border_color};">
                <div style="color: #2d3748; font-weight: 600; margin-bottom: 15px; font-size: 16px;">
                    {'🏢' if is_company_post else '📝'} Generated LinkedIn {post_type_label}{profile_type_indicator}
                </div>
                <div style="color: #2d3748; line-height: 1.6; font-size: 15px; white-space: pre-wrap; background-color: white; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0;">
{generated_content}
                </div>
                <div style="margin-top: 15px; font-size: 12px; color: #64748b;">
                    Character count: {len(generated_content)} | {post_type_label} | Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    {f" | Used {len(user_posts_for_generation)} of your posts for style" if user_posts_for_generation else ""}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("**📋 Copy to Clipboard**", use_container_width=True):
                    st.code(generated_content, language=None)
                    st.success("**Content ready to copy!**")
        
            with col2:
                # Download as text file
                profile_suffix = "company" if is_company_profile else "personal"
                st.download_button(
                    label="**📥 Download as Text**",
                    data=generated_content,
                    file_name=f"linkedin_{profile_suffix}_{post_type_label.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
            with col3:
                if st.button("**🔄 Generate Another**", use_container_width=True):
                    st.rerun()
        
            # Save to session state for history
            if 'generated_content_history' not in st.session_state:
                st.session_state.generated_content_history = []
        
            st.session_state.generated_content_history.append({
                'topic': topic_query,
                'content': generated_content,
                'timestamp': datetime.now().isoformat(),
                'reference_posts_count': len(similar_posts),
                'used_own_posts': len(user_posts_for_generation) > 0,
                'own_posts_count': len(user_posts_for_generation),
                'post_type': post_type_label,
                'is_company_profile': is_company_profile
            })
            
            # Clear calendar generation flag after successful generation
            if st.session_state.get('show_full_generation', False):
                st.session_state.show_full_generation = False
                st.session_state.calendar_topic = ''
    
        else:
            st.error("**Failed to generate content. Please try again.**")
    
    # Content history
    if st.session_state.get('generated_content_history'):
        st.markdown("---")
        st.markdown("### **📚 Content History**")
        
        history = st.session_state.generated_content_history
        
        for i, item in enumerate(reversed(history[-5:]), 1):  # Show last 5 items
            post_type_emoji = "🏢" if item.get('post_type') == 'Company Post' or item.get('is_company_profile', False) else "📝"
            profile_type = " (Company)" if item.get('is_company_profile', False) else " (Personal)"
            with st.expander(f"**{post_type_emoji} {item['topic'][:50]}...{profile_type}** - {item['timestamp'][:16]}"):
                st.markdown("**Topic:**")
                st.markdown(item['topic'])
                st.markdown("**Generated Content:**")
                st.code(item['content'], language=None)
                st.markdown(f"**Post Type:** {item.get('post_type', 'Personal Post')}")
                st.markdown(f"**Profile Type:** {'Company' if item.get('is_company_profile', False) else 'Personal'}")
                st.markdown(f"**Reference posts used:** {item['reference_posts_count']}")
                if item.get('used_own_posts', False):
                    st.markdown(f"**Your posts used for style:** {item.get('own_posts_count', 0)}")

# Initialize session state and load CSS
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        'current_step': 1,
        'name': '',
        'role': '',
        'linkedin_goal': '',
        'active_on_linkedin': None,
        'linkedin_url': '',
        'current_style': [],
        'differentiation_goals': [],
        'topics_of_interest': [],
        'allow_analysis': False,
        'selected_categories': [],  # Changed from single category to multiple
        'reference_creators': [],
        'custom_creators': [],
        'creator_preferences': {},
        'creator_likes': '',
        'preferred_content_types': [],
        'preferred_tone': [],
        'posts_per_week': 3,
        'posting_days': [],
        'form_completed': False,
        'persona': {},
        'persona_id': '',
        'generated_content_history': [],
        'custom_creators_list': [],
        'show_full_generation': False,
        'calendar_topic': '',
        'preferred_post_types': ["Storytelling", "Personal Experience", "Industry Insights", "How-to/Educational"],
        'is_company': None,
        'achievements_list': [],
        'company_info_list': [],
        'personal_context_list': [],
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_form():
    """Reset all form data"""
    keys_to_reset = [
        'name', 'role', 'linkedin_goal', 'active_on_linkedin', 'linkedin_url',
        'current_style', 'differentiation_goals', 'topics_of_interest', 'allow_analysis',
        'selected_categories', 'reference_creators', 'custom_creators', 'creator_preferences',
        'creator_likes', 'preferred_content_types', 'preferred_tone', 'posts_per_week', 
        'posting_days', 'form_completed', 'persona', 'persona_id', 'generated_content_history',
        'custom_creators_list', 'preferred_post_types', 'is_company', 'achievements_list', 'company_info_list', 'personal_context_list'
    ]
    
    for key in keys_to_reset:
        if key in st.session_state:
            if isinstance(st.session_state[key], list):
                st.session_state[key] = []
            elif isinstance(st.session_state[key], dict):
                st.session_state[key] = {}
            elif isinstance(st.session_state[key], bool):
                st.session_state[key] = False
            elif isinstance(st.session_state[key], int):
                st.session_state[key] = 3 if key == 'posts_per_week' else 0
            else:
                st.session_state[key] = '' if key != 'active_on_linkedin' else None
    
    st.session_state.current_step = 1

def next_step():
    """Move to next step"""
    st.session_state.current_step += 1

def prev_step():
    """Move to previous step"""
    if st.session_state.current_step > 1:
        st.session_state.current_step -= 1

def validate_step_1():
    """Validate step 1 inputs"""
    return (st.session_state.name.strip() and 
            st.session_state.role.strip() and 
            st.session_state.linkedin_goal.strip() and 
            st.session_state.active_on_linkedin is not None and
            st.session_state.get('is_company') is not None)

def validate_step_2a():
    """Validate step 2A inputs (active users) - now includes reference creators"""
    basic_validation = (st.session_state.linkedin_url.strip() and
                       len(st.session_state.current_style) > 0 and
                       len(st.session_state.differentiation_goals) > 0 and
                       len(st.session_state.topics_of_interest) > 0)
    
    # Check if they have reference creators and preferences
    has_creators = len(st.session_state.reference_creators) > 0
    has_likes = bool(st.session_state.creator_likes.strip())
    
    # Check if at least one creator has preferences selected
    has_preferences = False
    for creator_url in st.session_state.reference_creators:
        prefs = st.session_state.creator_preferences.get(creator_url, {})
        if (prefs.get('tone', []) or prefs.get('content_type', []) or prefs.get('style', [])):
            has_preferences = True
            break
    
    return basic_validation and has_creators and has_likes and has_preferences

def validate_step_2b():
    """Validate step 2B inputs (inactive users)"""
    has_creators = (len(st.session_state.reference_creators) > 0 or 
                    len(st.session_state.custom_creators) > 0)
    has_likes = bool(st.session_state.creator_likes.strip())
    
    # Check if at least one creator has preferences selected
    has_preferences = False
    for creator_url in st.session_state.reference_creators:
        prefs = st.session_state.creator_preferences.get(creator_url, {})
        if (prefs.get('tone', []) or prefs.get('content_type', []) or prefs.get('style', [])):
            has_preferences = True
            break
    
    return has_creators and has_likes and has_preferences

def validate_step_3():
    """Validate step 3 inputs"""
    return (len(st.session_state.preferred_content_types) > 0 and
            len(st.session_state.preferred_tone) > 0 and
            len(st.session_state.posting_days) > 0 and
            len(st.session_state.get('preferred_post_types', [])) > 0)

def generate_user_persona():
    """Generate the complete user persona"""
    persona_id = f"persona_{st.session_state.name.replace(' ', '_').lower()}_{int(time.time())}"
    st.session_state.persona_id = persona_id
    
    persona = {
        "_id": persona_id,
        "basic_info": {
            "name": st.session_state.name,
            "role": st.session_state.role,
            "linkedin_goal": st.session_state.linkedin_goal,
            "active_on_linkedin": st.session_state.active_on_linkedin,
            "is_company": st.session_state.get('is_company', False),
        },
        "content_preferences": {
            "posts_per_week": st.session_state.posts_per_week,
            "posting_days": st.session_state.posting_days,
            "preferred_content_types": st.session_state.preferred_content_types,
            "preferred_tone": st.session_state.preferred_tone,
            "preferred_post_types": st.session_state.get('preferred_post_types', ["Storytelling", "Personal Experience", "Industry Insights", "How-to/Educational"]),
        },
        "created_at": datetime.now().isoformat()
    }
    
    # Add custom creators list to persona
    if st.session_state.get('custom_creators_list', []):
        persona["custom_creators_list"] = st.session_state.custom_creators_list
    
    if st.session_state.active_on_linkedin:
        # For active users - include reference creators
        reference_creators = []
        
        # Add database creators
        df = load_linkedin_profiles()
        for url in st.session_state.reference_creators:
            creator_info = df[df['LinkedIn_URL'] == url]
            if not creator_info.empty:
                creator = {
                    "name": creator_info.iloc[0]['Name'],
                    "url": url,
                    "category": creator_info.iloc[0]['Cat'],
                    "description": creator_info.iloc[0]['Desc'],
                }
                
                if url in st.session_state.creator_preferences:
                    creator["preferences"] = st.session_state.creator_preferences[url]
                
                reference_creators.append(creator)
        
        persona["linkedin_profile"] = {
            "url": st.session_state.linkedin_url,
            "current_style": st.session_state.current_style,
            "differentiation_goals": st.session_state.differentiation_goals,
            "topics_of_interest": st.session_state.topics_of_interest,
            "allow_analysis": st.session_state.allow_analysis,
            "reference_creators": reference_creators,
            "creator_likes": st.session_state.creator_likes,
            "selected_categories": st.session_state.selected_categories  # Multiple categories
        }
    else:
        # For inactive users
        reference_creators = []
        
        # Add database creators
        df = load_linkedin_profiles()
        for url in st.session_state.reference_creators:
            creator_info = df[df['LinkedIn_URL'] == url]
            if not creator_info.empty:
                creator = {
                    "name": creator_info.iloc[0]['Name'],
                    "url": url,
                    "category": creator_info.iloc[0]['Cat'],
                    "description": creator_info.iloc[0]['Desc'],
                }
                
                if url in st.session_state.creator_preferences:
                    creator["preferences"] = st.session_state.creator_preferences[url]
                
                reference_creators.append(creator)
        
        # Add custom creators
        for url in st.session_state.custom_creators:
            creator = {
                "name": "Custom Creator",
                "url": url,
                "category": st.session_state.selected_categories[0] if st.session_state.selected_categories else "General",
                "custom": True
            }
            
            if url in st.session_state.creator_preferences:
                creator["preferences"] = st.session_state.creator_preferences[url]
                if "name" in creator["preferences"]:
                    creator["name"] = creator["preferences"]["name"]
            
            reference_creators.append(creator)
        
        persona["reference_info"] = {
            "selected_categories": st.session_state.selected_categories,  # Multiple categories
            "reference_creators": reference_creators,
            "creator_likes": st.session_state.creator_likes
        }
    
    # Save to MongoDB
    if MONGODB_AVAILABLE:
        if save_profile_to_mongodb(persona):
            st.success("✅ Profile saved to database!")
        else:
            st.warning("⚠️ Could not save profile to database")
    
    if st.session_state.get('achievements_list', []):
        persona["achievements_list"] = st.session_state.achievements_list

    if st.session_state.get('company_info_list', []):
        persona["company_info_list"] = st.session_state.company_info_list

    if st.session_state.get('personal_context_list', []):
        persona["personal_context_list"] = st.session_state.personal_context_list
    
    return persona

def load_linkedin_profiles():
    """Load LinkedIn profiles from CSV file"""
    try:
        csv_path = Path("linkedin_profiles_summary.csv")
        if not csv_path.exists():
            st.error(f"CSV file not found: {csv_path}")
            return pd.DataFrame()
        
        df = pd.read_csv(csv_path)
        return df
    except Exception as e:
        st.error(f"Error loading LinkedIn profiles: {str(e)}")
        return pd.DataFrame()

def get_profiles_by_category(category):
    """Get LinkedIn profiles matching the selected category"""
    df = load_linkedin_profiles()
    if df.empty:
        return pd.DataFrame()
    
    matching_profiles = df[df['Cat'] == category]
    return matching_profiles

def get_creator_initials(name):
    """Get initials from creator name"""
    words = name.split()
    if len(words) >= 2:
        return f"{words[0][0]}{words[1][0]}".upper()
    elif len(words) == 1:
        return words[0][:2].upper()
    else:
        return "??"

def display_influencer_post_card(post, show_stats=True):
    """Display an influencer post in a professional card format"""
    content_preview = post['post_text'][:300] + "..." if len(post['post_text']) > 300 else post['post_text']
    
    # Count hashtags and mentions
    hashtags = len([word for word in post['post_text'].split() if word.startswith('#')])
    mentions = len([word for word in post['post_text'].split() if word.startswith('@')])
    
    st.markdown(f"""
    <div class="post-container" style="margin-bottom: 20px; border-left: 4px solid #667eea;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <strong style="color: #2d3748; font-size: 18px; font-weight: 700;">{post['profile_name']}</strong>
                <span style="color: #4a5568; font-size: 14px; margin-left: 15px; background-color: #e2e8f0; padding: 4px 8px; border-radius: 12px; font-weight: 600;">{post['category']}</span>
            </div>
            <div style="color: #718096; font-size: 12px; text-align: right;">
                <div>{post['post_length']} characters</div>
                <div>{post.get('scraped_at', 'Unknown')[:10]}</div>
            </div>
        </div>
        <div style="color: #2d3748; line-height: 1.6; font-size: 15px; font-weight: 500; margin-bottom: 10px; background-color: #f8f9fa; padding: 12px; border-radius: 6px; border: 1px solid #e9ecef;">
            {content_preview.replace(chr(10), '<br>')}
        </div>
    """, unsafe_allow_html=True)
    
    if show_stats and (hashtags > 0 or mentions > 0):
        st.markdown(f"""
        <div style="display: flex; gap: 15px; margin-top: 10px; font-size: 12px; color: #4a5568;">
            {f'<span style="background-color: #bee3f8; padding: 2px 6px; border-radius: 8px; font-weight: 600;">#{hashtags} hashtags</span>' if hashtags > 0 else ''}
            {f'<span style="background-color: #c6f6d5; padding: 2px 6px; border-radius: 8px; font-weight: 600;">@{mentions} mentions</span>' if mentions > 0 else ''}
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add expandable full content for longer posts
    if len(post['post_text']) > 300:
        with st.expander("**View Full Post**"):
            st.markdown("**Full Content:**")
            st.text_area("", value=post['post_text'], height=200, disabled=True, key=f"full_post_{hash(post['post_text'])}", label_visibility="collapsed")

def display_custom_metric(label, value, icon="📊"):
    """Display a custom styled metric"""
    st.markdown(f"""
    <div class="metric-container">
        <div style="font-size: 28px; margin-bottom: 8px;">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

# Enhanced reference creator selection with multiple categories
def display_enhanced_reference_creator_selection(user_type="active"):
    """Enhanced reference creator selection with multiple categories"""
    st.markdown("### **📚 Reference Creators Selection**")
    st.markdown("**Choose creators from multiple categories whose content style you want to learn from:**")
    
    # Load categories from CSV
    df = load_linkedin_profiles()
    categories = sorted(df['Cat'].unique()) if not df.empty else []
    
    # Multiple category selection
    selected_categories = st.multiselect(
        "**Select content categories you're interested in** *",
        options=categories,
        default=st.session_state.get('selected_categories', []),
        help="You can select multiple categories to find creators from different areas"
    )
    
    st.session_state.selected_categories = selected_categories
    
    if selected_categories:
        st.success(f"**✅ Selected {len(selected_categories)} categories: {', '.join(selected_categories)}**")
        
        # Get all profiles from selected categories
        all_matching_profiles = pd.DataFrame()
        for category in selected_categories:
            category_profiles = get_profiles_by_category(category)
            if not category_profiles.empty:
                all_matching_profiles = pd.concat([all_matching_profiles, category_profiles], ignore_index=True)
        
        if not all_matching_profiles.empty:
            # Remove duplicates if any
            all_matching_profiles = all_matching_profiles.drop_duplicates(subset=['LinkedIn_URL'])
            
            st.info(f"**📊 Found {len(all_matching_profiles)} unique creators across all selected categories**")
            
            # Group creators by category for better organization
            st.markdown("### **Select Creators by Category**")
            
            total_selected_creators = []
            
            for category in selected_categories:
                category_profiles = all_matching_profiles[all_matching_profiles['Cat'] == category]
                
                if not category_profiles.empty:
                    st.markdown(f"#### **{category} ({len(category_profiles)} creators)**")
                    
                    # Creator selection for this category
                    category_selected_indices = st.multiselect(
                        f"Select creators from {category}",
                        options=list(range(len(category_profiles))),
                        format_func=lambda i: f"**{category_profiles.iloc[i]['Name']}** - {category_profiles.iloc[i]['Desc'][:60]}...",
                        default=[i for i in range(len(category_profiles)) if category_profiles.iloc[i]['LinkedIn_URL'] in st.session_state.get('reference_creators', [])],
                        key=f"creators_{category}",
                        label_visibility="collapsed"
                    )
                    
                    # Add selected creators from this category
                    if category_selected_indices:
                        category_selected_urls = category_profiles.iloc[category_selected_indices]['LinkedIn_URL'].tolist()
                        total_selected_creators.extend(category_selected_urls)
                        
                        # Display selected creators from this category
                        for idx in category_selected_indices:
                            creator_info = category_profiles.iloc[idx]
                            creator_url = creator_info['LinkedIn_URL']
                            name = creator_info['Name']
                            desc = creator_info['Desc']
                            
                            # Get current preferences
                            current_prefs = st.session_state.creator_preferences.get(creator_url, {
                                'tone': [],
                                'content_type': [],
                                'style': []
                            })
                            
                            # Create the card
                            st.markdown(f"""
                            <div class="creator-card">
                                <div class="profile-card">
                                    <div class="profile-image">
                                        {get_creator_initials(name)}
                                    </div>
                                    <div class="profile-info">
                                        <div class="profile-name">{name}</div>
                                        <div class="profile-title">{category}</div>
                                        <div class="profile-description">{desc}</div>
                                        <a href="{creator_url}" target="_blank" style="color: #667eea; font-weight: 600; text-decoration: none;">🔗 View LinkedIn Profile</a>
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Preferences selection
                            st.markdown(f"**What do you like about {name}'s content?**")
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("**Tone:**")
                                tone_options = ["Inspirational", "Honest/Authentic", "Tactical/Practical", "Funny/Humorous", "Analytical/Data-driven"]
                                selected_tone = st.multiselect(
                                    "Tone",
                                    options=tone_options,
                                    default=current_prefs.get('tone', []),
                                    key=f"tone_{user_type}_{creator_url}_{category}",
                                    label_visibility="collapsed"
                                )
                            
                            with col2:
                                st.markdown("**Content Type:**")
                                content_options = ["Stories/Personal", "Tips & How-to", "Industry Insights", "Opinion/Hot Takes", "Educational", "Behind-the-scenes"]
                                selected_content = st.multiselect(
                                    "Content Type",
                                    options=content_options,
                                    default=current_prefs.get('content_type', []),
                                    key=f"content_{user_type}_{creator_url}_{category}",
                                    label_visibility="collapsed"
                                )
                            
                            with col3:
                                st.markdown("**Style:**")
                                style_options = ["Visual/Graphics", "Long-form posts", "Short & punchy", "Data-driven", "Storytelling", "Question-based"]
                                selected_style = st.multiselect(
                                    "Style",
                                    options=style_options,
                                    default=current_prefs.get('style', []),
                                    key=f"style_{user_type}_{creator_url}_{category}",
                                    label_visibility="collapsed"
                                )
                            
                            # Update preferences in session state
                            st.session_state.creator_preferences[creator_url] = {
                                'tone': selected_tone,
                                'content_type': selected_content,
                                'style': selected_style
                            }
                            
                            # Display selected preferences as badges
                            if selected_tone or selected_content or selected_style:
                                st.markdown('<div style="background: rgba(102, 126, 234, 0.1); border-radius: 12px; padding: 15px; margin-top: 15px; border: 1px solid rgba(102, 126, 234, 0.2);">', unsafe_allow_html=True)
                                st.markdown('<div style="font-weight: 600; color: #4a5568; margin-bottom: 10px; font-size: 14px;">Selected Preferences:</div>', unsafe_allow_html=True)
                                
                                badges_html = ""
                                for tone in selected_tone:
                                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">{tone}</span>'
                                for content in selected_content:
                                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #48bb78 0%, #38b2ac 100%);">{content}</span>'
                                for style in selected_style:
                                    badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">{style}</span>'
                                
                                st.markdown(badges_html, unsafe_allow_html=True)
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            st.markdown("---")
            
            # Update session state with all selected creators
            st.session_state.reference_creators = list(set(total_selected_creators))  # Remove duplicates
            
            if total_selected_creators:
                st.success(f"**✅ Total selected: {len(set(total_selected_creators))} creators across {len(selected_categories)} categories**")
            
        else:
            st.warning("**No creators found in the selected categories**")
    
    return len(st.session_state.get('reference_creators', [])) > 0

# Initialize everything
init_session_state()
load_css()

# Main app header with enhanced styling
st.markdown("""
<div class="content-card">
    <div style="display: flex; align-items: center; justify-content: center; text-align: center;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; width: 100px; height: 100px; border-radius: 20px; display: flex; align-items: center; justify-content: center; margin-right: 30px; font-size: 48px; box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);">
            📅
        </div>
        <div>
            <h1 style="margin: 0; font-size: 42px;">LinkedIn Content Calendar Planner</h1>
            <p style="margin: 0; color: #4a5568; font-size: 22px; font-weight: 600;">Build your personalized content strategy with AI-powered calendar</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Profile Management Section
st.markdown("---")
st.markdown("### **👤 Profile Management**")

# Check MongoDB availability
if MONGODB_AVAILABLE:
    # Test MongoDB connection first
    client = get_mongodb_client()
    if client is not None:
        st.success("**✅ MongoDB Connected**")
        
        # Load existing profiles
        existing_profiles = load_profiles_from_mongodb()
        
        if existing_profiles and len(existing_profiles) > 0:
            st.success(f"**✅ Found {len(existing_profiles)} saved profiles**")
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                profile_options = ["Create New Profile"] + [
                    f"{profile['basic_info']['name']} ({profile['basic_info']['role']}) - {profile.get('updated_at', '')[:10]}"
                    for profile in existing_profiles
                ]
                
                selected_profile_option = st.selectbox(
                    "**Select Profile or Create New:**",
                    options=profile_options,
                    index=0,
                    key="profile_selector"
                )
            
            with col2:
                # Load selected profile
                if selected_profile_option != "Create New Profile":
                    if st.button("**📂 Load Profile**", type="primary", use_container_width=True, key="load_profile_btn"):
                        selected_index = profile_options.index(selected_profile_option) - 1
                        selected_profile = existing_profiles[selected_index]
                        
                        # Load profile data into session state
                        load_profile_into_session(selected_profile)
                        st.success(f"✅ Loaded profile: {selected_profile['basic_info']['name']}")
                        st.rerun()
            
            with col3:
                # Delete profile option
                if selected_profile_option != "Create New Profile":
                    if st.button("**🗑️ Delete**", use_container_width=True, key="delete_profile_btn"):
                        selected_index = profile_options.index(selected_profile_option) - 1
                        profile_to_delete = existing_profiles[selected_index]
                        
                        # Confirmation
                        if st.session_state.get('confirm_delete') != profile_to_delete['_id']:
                            st.session_state.confirm_delete = profile_to_delete['_id']
                            st.warning("Click Delete again to confirm")
                        else:
                            if delete_profile_from_mongodb(profile_to_delete['_id']):
                                st.success("✅ Profile deleted!")
                                if 'confirm_delete' in st.session_state:
                                    del st.session_state.confirm_delete
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete profile")
        else:
            st.info("**📝 No saved profiles found. Create your first profile below.**")
        
        # Show current profile info if loaded
        if st.session_state.get('form_completed', False) and st.session_state.get('persona', {}):
            current_persona = st.session_state.persona
            st.info(f"**📋 Current Profile:** {current_persona['basic_info']['name']} ({current_persona['basic_info']['role']})")
            
            # Quick actions for current profile
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("**🔄 Update Current Profile**", use_container_width=True, key="update_profile_btn"):
                    # Update the persona with current session data
                    updated_persona = generate_user_persona()
                    if 'persona_id' in st.session_state and st.session_state.persona_id:
                        updated_persona['_id'] = st.session_state.persona_id  # Keep same ID
                    if save_profile_to_mongodb(updated_persona):
                        st.success("✅ Profile updated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update profile")
            
            with col2:
                if st.button("**📊 Go to Dashboard**", use_container_width=True, key="go_to_dashboard_btn"):
                    st.session_state.current_step = 4
                    st.rerun()
            
            with col3:
                if st.button("**🆕 Create New Profile**", use_container_width=True, key="create_new_profile_btn"):
                    reset_form()
                    st.rerun()
        
        # Quick start option
        if st.button("**🚀 Start Creating Profile**", type="primary", use_container_width=True, key="start_creating_profile_btn"):
            st.session_state.current_step = 1
            st.rerun()
            
    else:
        st.error("**❌ MongoDB Connection Failed**")
        st.info("Please check your MongoDB connection and try again.")

else:
    st.warning("**⚠️ MongoDB not available. Profiles will not be saved between sessions.**")
    st.info("To enable profile saving, install pymongo: `pip install pymongo`")

# Show system status
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if MONGODB_AVAILABLE:
        client = get_mongodb_client()
        if client:
            st.success("**✅ MongoDB Connected**")
            try:
                profiles_count = get_profiles_collection().count_documents({})
                st.info(f"**📊 {profiles_count} Total Profiles**")
            except:
                st.info("**📊 Database Ready**")
        else:
            st.error("**❌ MongoDB Connection Failed**")
    else:
        st.error("**❌ MongoDB Not Available**")

with col2:
    if CHROMADB_AVAILABLE:
        st.success("**✅ ChromaDB Ready**")
    else:
        st.error("**❌ ChromaDB Missing**")

with col3:
    if SENTENCE_TRANSFORMERS_AVAILABLE:
        st.success("**✅ AI Models Ready**")
    else:
        st.error("**❌ AI Models Missing**")

with col4:
    if GROQ_AVAILABLE and os.getenv("GROQ_API_KEY"):
        st.success("**✅ Content Generation Ready**")
    else:
        st.error("**❌ Content Generation Not Ready**")

# Progress indicator
progress_steps = ["Basic Info", "Profile Setup", "Content Preferences", "Complete"]
current_step_index = min(st.session_state.current_step - 1, len(progress_steps) - 1)

progress_percentage = (current_step_index + 1) / len(progress_steps)
st.progress(progress_percentage)

cols = st.columns(len(progress_steps))
for i, (col, step) in enumerate(zip(cols, progress_steps)):
    with col:
        if i <= current_step_index:
            st.markdown(f"<div style='text-align: center; color: #667eea; font-weight: 700; font-size: 18px;'>✅ {step}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='text-align: center; color: #718096; font-size: 18px;'>⭕ {step}</div>", unsafe_allow_html=True)

st.markdown("---")

# Step 1: Introduction
if st.session_state.current_step == 1:
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #2d3748; font-size: 32px;">🎯 Let's Get Started</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Tell us about yourself and your LinkedIn goals.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("step1_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.name = st.text_input(
                "**Name or Brand Name** *", 
                value=st.session_state.name,
                placeholder="e.g., Jane Doe or Acme Corp"
            )
        
        with col2:
            st.session_state.role = st.text_input(
                "**Your Professional Role/Title** *", 
                value=st.session_state.role,
                placeholder="e.g., Life Coach, CFO, Marketing Director"
            )
        
        st.session_state.linkedin_goal = st.text_area(
            "**Describe your goal on LinkedIn** *", 
            value=st.session_state.linkedin_goal,
            placeholder="e.g., build authority in my field, attract potential clients, grow my network...",
            height=120
        )
        
        st.session_state.active_on_linkedin = st.radio(
            "**Are you currently active on LinkedIn?** *",
            options=[True, False],
            format_func=lambda x: "Yes, I post regularly" if x else "No, I'm just starting out",
            index=None if st.session_state.active_on_linkedin is None else (0 if st.session_state.active_on_linkedin else 1),
            horizontal=True
        )
        
        # Add this after the active_on_linkedin radio button in Step 1
        st.session_state.is_company = st.radio(
            "**Are you representing a company or personal brand?** *",
            options=[False, True],
            format_func=lambda x: "Company/Organization" if x else "Personal Brand",
            index=None if st.session_state.get('is_company') is None else (1 if st.session_state.get('is_company') else 0),
            horizontal=True
        )
        
        submitted = st.form_submit_button("**Next Step →**", type="primary", use_container_width=True)
        
        if submitted:
            if validate_step_1():
                next_step()
                st.rerun()
            else:
                st.error("**Please fill in all required fields marked with ***")

# Step 2A: Active User Details (ENHANCED with multiple category reference creators)
elif st.session_state.current_step == 2 and st.session_state.active_on_linkedin:
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #2d3748; font-size: 32px;">📊 Active User Profile</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Since you're already active on LinkedIn, let's understand your current approach and find reference creators to inspire you.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("step2a_form"):
        st.session_state.linkedin_url = st.text_input(
            "**Your LinkedIn profile URL** *",
            value=st.session_state.linkedin_url,
            placeholder="https://linkedin.com/in/your-profile"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            style_options = ["Storytelling", "Tips & Advice", "Analytical", "Casual/Conversational", "Personal", "Thought Leadership"]
            st.session_state.current_style = st.multiselect(
                "**How would you describe your current content style?** *",
                options=style_options,
                default=st.session_state.current_style
            )
        
        with col2:
            differentiation_options = [
                "More honest/authentic posts", 
                "More tactical advice", 
                "More storytelling", 
                "Less generic content",
                "More personal insights",
                "More data-driven content",
                "More controversial takes",
                "More behind-the-scenes content"
            ]
            st.session_state.differentiation_goals = st.multiselect(
                "**What kind of differentiation do you want to create?** *",
                options=differentiation_options,
                default=st.session_state.differentiation_goals
            )
        
        topic_options = [
            "AI & Technology", "Leadership", "Startups", "Hiring & Recruitment", 
            "Marketing", "Sales", "Productivity", "Career Development", 
            "Entrepreneurship", "Finance", "Personal Branding", "Industry Insights"
        ]
        st.session_state.topics_of_interest = st.multiselect(
            "**Topics you want to go deeper into** *",
            options=topic_options,
            default=st.session_state.topics_of_interest
        )
        
        st.session_state.allow_analysis = st.checkbox(
            "**Allow the system to analyze your past LinkedIn posts?**",
            value=st.session_state.allow_analysis,
            help="This will help us understand your current style and suggest improvements."
        )
        
        st.markdown("---")
        
        # Enhanced reference creator selection with multiple categories
        has_creators = display_enhanced_reference_creator_selection("active")
        
        # What do you like about these creators
        st.session_state.creator_likes = st.text_area(
            "**What do you like about these creators' content approach?** *",
            value=st.session_state.creator_likes,
            placeholder="Describe their overall style, tone, topics, approach that resonates with you...",
            height=120
        )
        
        col1, col2 = st.columns(2)
        with col1:
            back_clicked = st.form_submit_button("**← Back**", use_container_width=True)
        with col2:
            next_clicked = st.form_submit_button("**Next Step →**", type="primary", use_container_width=True)
        
        if back_clicked:
            prev_step()
            st.rerun()
        elif next_clicked:
            if validate_step_2a():
                next_step()
                st.rerun()
            else:
                st.error("**Please fill in all required fields marked with *** and select at least one reference creator with preferences**")

# Step 2B: Inactive User / Category Selection Path (ENHANCED with multiple categories)
elif st.session_state.current_step == 2 and not st.session_state.active_on_linkedin:
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #2d3748; font-size: 32px;">🔍 Content Categories & Reference Creators</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Let's find the right content categories and reference creators to inspire your LinkedIn strategy.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Enhanced reference creator selection with multiple categories
    has_creators = display_enhanced_reference_creator_selection("inactive")
    
    # What do you like about these creators
    st.session_state.creator_likes = st.text_area(
        "**What do you like about these creators' content approach?** *",
        value=st.session_state.creator_likes,
        placeholder="Describe their overall style, tone, topics, approach that resonates with you...",
        height=120
    )

    st.markdown("---")
    st.markdown("### **Or Add Custom Creators**")
    
    # Custom creator management
    add_custom_creator_section()
    
    # Display custom creators list
    display_custom_creators_list()
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("**← Back**", use_container_width=True):
            prev_step()
            st.rerun()
    with col2:
        has_likes = bool(st.session_state.creator_likes.strip())
        
        if st.button("**Next Step →**", type="primary", use_container_width=True):
            if has_creators and has_likes:
                # Check if at least one creator has preferences
                has_preferences = False
                for creator_url in st.session_state.reference_creators:
                    prefs = st.session_state.creator_preferences.get(creator_url, {})
                    if (prefs.get('tone', []) or prefs.get('content_type', []) or prefs.get('style', [])):
                        has_preferences = True
                        break
                
                if has_preferences:
                    next_step()
                    st.rerun()
                else:
                    st.error("**Please specify what you like about at least one creator's content using the preference options**")
            else:
                if not has_creators:
                    st.error("**Please select at least one reference creator**")
                if not has_likes:
                    st.error("**Please describe what you like about these creators' content**")

# Step 3: Tone & Content Style
elif st.session_state.current_step == 3:
    st.markdown("""
    <div class="content-card">
        <h2 style="color: #2d3748; font-size: 32px;">🎨 Content Style & Preferences</h2>
        <p style="color: #2d3748; font-size: 20px; font-weight: 600;">Define your content strategy and posting schedule.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("step3_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            content_type_options = [
                "Story/Personal Experience", 
                "Opinion/Hot Takes", 
                "Tips & How-to", 
                "Casual/Conversational", 
                "Life Lessons", 
                "Informational/Educational"
            ]
            st.session_state.preferred_content_types = st.multiselect(
                "**What types of content do you prefer to post?**",
                options=content_type_options,
                default=st.session_state.preferred_content_types
            )
        
        with col2:
            tone_options = [
                "Inspirational", 
                "Honest/Authentic", 
                "Tactical/Practical", 
                "Funny/Humorous", 
                "Direct/Blunt", 
                "Analytical/Data-driven"
            ]
            st.session_state.preferred_tone = st.multiselect(
                "**Preferred tone** *",
                options=tone_options,
                default=st.session_state.preferred_tone
            )
        
        st.markdown("### **Post Types**")
        post_type_options = [
            "Storytelling", "Life Lesson", "Personal Experience", "Factual", 
            "Data Driven", "Motivational", "Inspirational", "Thought Provoking",
            "How-to/Educational", "Behind the Scenes", "Industry Insights", "Question/Poll"
        ]

        if 'preferred_post_types' not in st.session_state:
            st.session_state.preferred_post_types = ["Storytelling", "Personal Experience", "Industry Insights", "How-to/Educational"]

        st.session_state.preferred_post_types = st.multiselect(
            "**What types of posts do you want to create?** *",
            options=post_type_options,
            default=st.session_state.preferred_post_types,
            help="Select the post types you want to include in your content calendar rotation"
        )
        
        st.markdown("### **Posting Schedule**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.session_state.posts_per_week = st.slider(
                "**How many posts per week?**",
                min_value=1,
                max_value=7,
                value=st.session_state.posts_per_week
            )
        
        with col2:
            day_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            st.session_state.posting_days = st.multiselect(
                "**Preferred posting days?** *",
                options=day_options,
                default=st.session_state.posting_days
            )
        
        col1, col2 = st.columns(2)
        with col1:
            back_clicked = st.form_submit_button("**← Back**", use_container_width=True)
        with col2:
            next_clicked = st.form_submit_button("**Complete Setup →**", type="primary", use_container_width=True)
        
        if back_clicked:
            prev_step()
            st.rerun()
        elif next_clicked:
            if validate_step_3():
                # Generate persona and move to final step
                st.session_state.persona = generate_user_persona()
                st.session_state.form_completed = True
                next_step()
                st.rerun()
            else:
                st.error("**Please fill in all required fields marked with ***")

# Step 4: Final Dashboard with Calendar Integration
elif st.session_state.current_step == 4:
    if not st.session_state.get('form_completed', False):
        st.error("**Please complete the profile setup first.**")
        if st.button("**Start Setup**", type="primary"):
            st.session_state.current_step = 1
            st.rerun()
    else:
        persona = st.session_state.persona
        
        # Enhanced header with glassmorphism
        st.markdown(f"""
        <div class="content-card">
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <h1 style="margin: 0; font-size: 36px;">🎉 Welcome, {persona['basic_info']['name']}!</h1>
                    <p style="margin: 0; color: #4a5568; font-size: 20px; font-weight: 600;">Your LinkedIn Content Strategy is Ready</p>
                </div>
                <div style="text-align: right;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border-radius: 16px; font-weight: 700; font-size: 18px; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                        {persona['basic_info']['role']}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Enhanced tabs with better styling
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 **Dashboard**", "📅 **Content Calendar**", "🚀 **Generate Content**", "➕ **Custom Creators**", "📋 **Profile Summary**"])
        
        with tab1:
            # Enhanced Dashboard with metrics
            st.markdown("### **📊 Your Content Strategy Overview**")
            
            # Metrics row with enhanced styling
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                display_custom_metric("Posts per Week", persona['content_preferences']['posts_per_week'], "📈")
            
            with col2:
                display_custom_metric("Posting Days", len(persona['content_preferences']['posting_days']), "📅")
            
            with col3:
                if persona['basic_info']['active_on_linkedin'] and 'linkedin_profile' in persona:
                    creator_count = len(persona['linkedin_profile'].get('reference_creators', []))
                elif 'reference_info' in persona:
                    creator_count = len(persona['reference_info'].get('reference_creators', []))
                else:
                    creator_count = 0
                display_custom_metric("Reference Creators", creator_count, "👥")
            
            with col4:
                custom_creator_count = len(st.session_state.get('custom_creators_list', []))
                display_custom_metric("Custom Creators", custom_creator_count, "⭐")
            
            st.markdown("---")
            
            # Content preferences overview
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### **🎯 Content Types**")
                for content_type in persona['content_preferences']['preferred_content_types']:
                    st.markdown(f"• **{content_type}**")
                
                st.markdown("### **📅 Posting Schedule**")
                posting_days = ", ".join(persona['content_preferences']['posting_days'])
                st.markdown(f"**{persona['content_preferences']['posts_per_week']} posts per week**")
                st.markdown(f"**Days:** {posting_days}")
            
            with col2:
                st.markdown("### **🎨 Preferred Tone**")
                for tone in persona['content_preferences']['preferred_tone']:
                    st.markdown(f"• **{tone}**")
                
                st.markdown("### **🎯 LinkedIn Goal**")
                st.markdown(f"*{persona['basic_info']['linkedin_goal']}*")
            
            # Reference creators overview
            st.markdown("---")
            st.markdown("### **👥 Your Reference Creators**")
            
            if persona['basic_info']['active_on_linkedin'] and 'linkedin_profile' in persona:
                creators = persona['linkedin_profile'].get('reference_creators', [])
                categories = persona['linkedin_profile'].get('selected_categories', [])
            elif 'reference_info' in persona:
                creators = persona['reference_info'].get('reference_creators', [])
                categories = persona['reference_info'].get('selected_categories', [])
            else:
                creators = []
                categories = []
            
            if categories:
                st.info(f"**📂 Selected Categories:** {', '.join(categories)}")
            
            if creators:
                for creator in creators:
                    st.markdown(f"""
                    <div class="creator-card">
                        <div class="profile-card">
                            <div class="profile-image">
                                {get_creator_initials(creator['name'])}
                            </div>
                            <div class="profile-info">
                                <div class="profile-name">{creator['name']}</div>
                                <div class="profile-title">{creator['category']}</div>
                                <div class="profile-description">{creator.get('description', 'No description')}</div>
                                <a href="{creator['url']}" target="_blank" style="color: #667eea; font-weight: 600; text-decoration: none;">🔗 View LinkedIn Profile</a>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Show preferences if available
                    if 'preferences' in creator:
                        prefs = creator['preferences']
                        if prefs.get('tone') or prefs.get('content_type') or prefs.get('style'):
                            st.markdown('<div style="background: rgba(102, 126, 234, 0.1); border-radius: 12px; padding: 15px; margin-top: 15px; border: 1px solid rgba(102, 126, 234, 0.2);">', unsafe_allow_html=True)
                            st.markdown('<div style="font-weight: 600; color: #4a5568; margin-bottom: 10px; font-size: 14px;">Your Preferences:</div>', unsafe_allow_html=True)
                            
                            badges_html = ""
                            for tone in prefs.get('tone', []):
                                badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">{tone}</span>'
                            for content in prefs.get('content_type', []):
                                badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #48bb78 0%, #38b2ac 100%);">{content}</span>'
                            for style in prefs.get('style', []):
                                badges_html += f'<span style="display: inline-block; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; margin-right: 8px; margin-bottom: 8px; color: white; background: linear-gradient(135deg, #ed8936 0%, #dd6b20 100%);">{style}</span>'
                            
                            st.markdown(badges_html, unsafe_allow_html=True)
                            st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("**No reference creators selected yet.**")
        
        with tab2:
            # NEW CALENDAR TAB
            st.markdown("### **📅 Your Content Calendar**")
            
            # Initialize Groq client for calendar
            groq_client = initialize_groq_client()
            
            if not groq_client:
                st.error("**❌ Calendar requires Groq API key. Please set GROQ_API_KEY in environment variables.**")
            else:
                # Calendar controls
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    current_date = datetime.now()
                    selected_year = st.selectbox(
                        "**Year**",
                        options=[current_date.year - 1, current_date.year, current_date.year + 1],
                        index=1
                    )
                
                with col2:
                    selected_month = st.selectbox(
                        "**Month**",
                        options=list(range(1, 13)),
                        format_func=lambda x: calendar.month_name[x],
                        index=current_date.month - 1
                    )
                
                with col3:
                    if st.button("**🔄 Regenerate All Content**", use_container_width=True):
                        # Clear content cache for this month
                        month_key_prefix = f"{selected_year}-{selected_month:02d}"
                        keys_to_remove = [key for key in st.session_state.content_cache.keys() if key.startswith(month_key_prefix)]
                        for key in keys_to_remove:
                            del st.session_state.content_cache[key]
                        st.success("**✅ Content cache cleared! Calendar will regenerate content.**")
                        st.rerun()
                
                # Get posting dates for the selected month
                posting_dates = get_posting_dates_for_month(
                    selected_year, 
                    selected_month, 
                    persona['content_preferences']['posting_days'],
                    persona['content_preferences']['posts_per_week']
                )
                
                # Display calendar
                main_calendar_page(persona, groq_client, selected_year, selected_month, posting_dates)
                
                # Calendar summary
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.info(f"**📊 {len(posting_dates)} posting days this month**")
                
                with col2:
                    cached_content = len([key for key in st.session_state.content_cache.keys() if key.startswith(f"{selected_year}-{selected_month:02d}")])
                    st.info(f"**💾 {cached_content} content pieces generated**")
                
                with col3:
                    if st.button("**📥 Export Calendar**", use_container_width=True):
                        # Create export data
                        export_data = []
                        for day in posting_dates:
                            date_key = f"{selected_year}-{selected_month:02d}-{day:02d}"
                            content = st.session_state.content_cache.get(date_key, "Content not generated")
                            export_data.append(f"{calendar.month_name[selected_month]} {day}, {selected_year}: {content}")
                        
                        export_text = "\n\n".join(export_data)
                        st.download_button(
                            label="**📥 Download Calendar**",
                            data=export_text,
                            file_name=f"content_calendar_{selected_year}_{selected_month:02d}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
        
        with tab3:
            # Enhanced Content Generation Tab
            display_content_generation_page()
        
        with tab4:
            # Custom Creators Management Tab
            st.markdown("### **⭐ Custom Creators Management**")
            
            # Add new custom creator
            add_custom_creator_section()
            
            # Display existing custom creators
            display_custom_creators_list()
            
            # Show posts from custom creators if any are scraped
            scraped_custom_creators = [c for c in st.session_state.get('custom_creators_list', []) if c['scraped']]
            
            if scraped_custom_creators:
                st.markdown("---")
                st.markdown("### **📊 Posts from Custom Creators**")
                
                creator_names = [c['name'] for c in scraped_custom_creators]
                posts = get_posts_by_influencers(creator_names)
                
                if posts:
                    st.success(f"**✅ Found {len(posts)} posts from {len(creator_names)} custom creators**")
                    
                    # Display posts
                    for post in posts[:5]:  # Show first 5 posts
                        display_influencer_post_card(post)
                    
                    if len(posts) > 5:
                        st.info(f"**Showing 5 of {len(posts)} posts. Use the Generate Content tab to search through all posts.**")
                else:
                    st.info("**No posts found from custom creators yet.**")
        
        with tab5:
            # Profile Summary Tab
            st.markdown("### **📋 Complete Profile Summary**")
            
            # Display complete persona as JSON
            st.markdown("**Your complete profile data:**")
            st.json(persona)
            
            # Export options
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # Download profile as JSON
                profile_json = json.dumps(persona, indent=2)
                st.download_button(
                    label="**📥 Download Profile (JSON)**",
                    data=profile_json,
                    file_name=f"linkedin_profile_{persona['basic_info']['name'].replace(' ', '_').lower()}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col2:
                if st.button("**🔄 Edit Profile**", use_container_width=True):
                    st.session_state.current_step = 1
                    st.rerun()
            
            with col3:
                if st.button("**🆕 Create New Profile**", use_container_width=True):
                    reset_form()
                    st.rerun()

