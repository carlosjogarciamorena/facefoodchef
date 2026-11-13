import json
import time
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import streamlit as st
import streamlit.components.v1 as components
from recipe_scrapers import scrape_me
from google import genai
from google.genai import types
from google.genai.errors import APIError

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import pptx
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

st.set_page_config(
    page_title="FaceFoodChef.com - Motor de Diagramas Culinarios", 
    layout="wide", 
    page_icon="🍳"
)

st.markdown(
    "<style>"
    "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600;700&family=Montserrat:wght@700;900&display=swap');"
    ".stApp, .block-container, [data-testid=\"stSidebar\"] { background-color: #36393F !important; color: #E2E8F0 !important; font-family: 'Inter', sans-serif !important; }"
    "header, footer { visibility: hidden; }"
    ".stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input { background-color: #2C2F33 !important; color: #E2E8F0 !important; border: 1px solid #4F545C !important; border-radius: 6px !important; font-size: 15px !important; font-family: 'Inter', sans-serif !important; }"
    ".stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus { border-color: #FFB300 !important; box-shadow: none !important; }"
    ".stButton > button { background: #00FF66 !important; color: #1E1E1E !important; font-family: 'Montserrat', sans-serif !important; font-weight: 900 !important; font-size: 15px !important; border: none !important; border-radius: 6px !important; padding: 12px 24px !important; width: 100%; text-transform: uppercase; letter-spacing: 1px; transition: background 0.2s ease !important; }"
    ".stButton > button:hover { background: #00CC52 !important; }"
    "h1, h2, h3, h4, h5, h6 { font-family: 'Montserrat', sans-serif !important; color: #FFFFFF !important; text-transform: uppercase; }"
    "</style>",
    unsafe_allow_html=True
)

st.sidebar.header("⚙️ Panel de Control")

API_KEY_INPUT = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google Gemini (Google AI Studio)."
)

modelo_seleccionado = st
