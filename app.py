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

# Configuración de página Streamlit
st.set_page_config(
    page_title="FaceFoodChef.com - Motor de Diagramas Culinarios", 
    layout="wide", 
    page_icon="🍳"
)

# Estilos globales optimizados para Móviles, Tablets y Escritorio
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600;700&family=Montserrat:wght@700;900&display=swap');

    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #36393F !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    header, footer { visibility: hidden; }
    
    .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        border: 1px solid #4F545C !important;
        border-radius: 6px !important;
        font-size: 15px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #FFB300 !important;
        box-shadow: none !important;
    }

    /* Botones principales de Streamlit */
    .stButton > button {
        background: #00FF66 !important;
        color: #1E1E1E !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 15px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 24px !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: background 0.2s ease !important;
    }
    .stButton > button:hover {
        background: #00CC52 !important;
    }

    .streamlit-expanderHeader {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        border-radius: 6px !important;
        border: 1px solid #4F545C !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
        color: #FFFFFF !important;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

# Panel Lateral
st.sidebar.header("⚙️ Panel de Control")

API_KEY_INPUT = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google Gemini (Google AI Studio)."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"],
    index=0
)

comensales_objetivo = st.sidebar.number_input(
    "👥 Número de comensales:",
    min_value=1,
    max_value=100,
    value=4,
    step=1,
    help="El sistema recalculará los ingredientes para este número de personas."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🎨 Código de Bloques:
- 🟢 **Verde Neón (`#00FF66`):** Ingredientes / Utensilios / Maridaje
- 🟡 **Amarillo (`#FFB300`):** Acciones / Procesado
- 🔴 **Rojo FaceFoodChef (`#EF4444`):** Alertas / Puntos Críticos
- 🟡 **Dorado (`#FFD700`):** Plato Terminado
""")

# Encabezado Principal
st.markdown("<h1 style='text-align: center; color: #FFFFFF; font-family: Montserrat, sans-serif; font-weight: 900; letter-spacing: 2px; margin-bottom: 0; font-size: clamp(20px, 4vw, 32px);'>FACEFOODCHEF <span style='font-size: clamp(10px, 2vw, 14px); background: #00FF66; color: #1E1E1E; padding: 4px 10px; border-radius: 4px; vertical-align: middle; letter-spacing: 1px;'>MOTOR DE DIAGRAMAS</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #E2E8F0; font-size: clamp(13px, 2vw, 15px); margin-bottom: 30px; font-family: Inter, sans-serif;'>Convierte recetas textuales en diagramas de flujo de producción culinaria con audio guiado</p>", unsafe_allow_html=True)

# Entrada de receta
st.subheader("📥 Entrada de Receta")
entrada_principal = st.text_area(
    "Pega la URL de la receta o el texto completo:", 
    height=130, 
    placeholder="https://www.ejemplo.com/receta\nO pega directamente el texto de la receta aquí..."
)

with st.expander("📁 Adjuntar archivo (PDF, Word, PPT o Imagen)"):
    archivo_subido = st.file_uploader("Subir documento:", type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"])

receta_texto_input = ""
url_origen_detectada = ""
archivo_multimodal = None
tipo_multimodal = None

if entrada_principal.strip():
    texto_limpio = entrada_principal.strip()
    if texto_limpio.startswith("http://") or texto_limpio.startswith("https://"):
        if texto_limpio.count("http") > 1:
            partes = texto_limpio.split("http")
            url_origen_detectada = "http" + partes[-1]
        else:
            url_origen_detectada = texto_limpio
    else:
        receta_texto_input = texto_limpio

if archivo_subido:
    ext = archivo_subido.name.split('.')[-1].lower()
    if ext == "txt":
        receta_texto_input = archivo_subido.getvalue().decode("utf-8")
    elif ext == "docx" and HAS_DOCX:
        doc = docx.Document(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == "pptx"
