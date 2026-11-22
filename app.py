import json
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
    page_title="FaceFoodChef - Diagramas de Bloques Culinarios",
    layout="wide",
    page_icon="🍳"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Montserrat:wght@700;900&display=swap');
    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #36393F !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        border: 1px solid #4F545C !important;
        border-radius: 6px !important;
    }
    .stButton > button {
        background-color: #00FF66 !important;
        color: #1E1E1E !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 15px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 20px !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .stButton > button:hover {
        background-color: #00D656 !important;
    }
    .stDownloadButton > button {
        background-color: #FFB300 !important;
        color: #1E1E1E !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 14px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 18px !important;
        width: 100%;
        text-transform: uppercase;
    }
    h1, h2, h3, h4 {
        font-family: 'Montserrat', sans-serif !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.header("⚙️ Panel de Control")

api_key_input = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google AI Studio."
)

modelo_seleccionado = st.sidebar.selectbox(
    "🤖 Modelo Gemini:",
    options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
    index=0
)

comensales_objetivo = st.sidebar.number_input(
    "👥 Comensales:",
    min_value=1,
    max_value=100,
    value=4,
    step=1
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Leyenda de Bloques")
st.sidebar.markdown("- 🟢 **Verde (`#00FF66`):** Ingredientes / Utensilios / Maridaje")
st.sidebar.markdown("- 🟡 **Amarillo (`#FFB300`):** Bloque de cocinado / proceso")
st.sidebar.markdown("- 🔴 **Rojo (`#EF4444`):** Punto crítico o alerta")
st.sidebar.markdown("- 🟡 **Dorado (`#FFD700`):** Plato terminado")

st.markdown(
    "<h1 style='text-align:center; margin-bottom:4px;'>FACEFOODCHEF · MOTOR DE DIAGRAMAS CULINARIOS</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:#CBD5E1; margin-bottom:24px;'>Transforma cualquier receta en un diagrama de bloques paso a paso con cantidades exactas</p>",
    unsafe_allow_html=True
)

st.subheader("📥 Receta de Entrada")
entrada_principal = st.text_area(
    "Pega el texto de la receta o una URL:",
    height=150,
    placeholder="Ejemplo:\nTortilla de patatas: 600 g de patatas, 6 huevos, 150 g de cebolla, 120 ml de aceite de oliva virgen extra, 6 g de sal..."
)

with st.expander("📁 Subir archivo opcional (PDF, Word, PPT, TXT o Imagen)"):
    archivo_subido = st.file_uploader(
        "Selecciona un archivo:",
        type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"]
    )

receta_texto_input = ""
url_origen_detectada = ""
archivo_multimodal = None
tipo_multimodal = None

if entrada_principal.strip():
    texto_limpio = entrada_principal.strip()
    if texto_limpio.startswith("http://") or texto_limpio.startswith("https://"):
        url_origen_detectada = texto_limpio
    else:
        receta_texto_input = texto_limpio

if archivo_subido is not None:
    ext = archivo_subido.name.split(".")[-1].lower()
    if ext == "txt":
        receta_texto_input = archivo_subido.getvalue().decode("utf-8", errors="ignore")
    elif ext == "docx" and HAS_DOCX:
        doc = docx.Document(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == "pptx" and HAS_PPTX:
        prs = pptx.Presentation(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([
            p.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs
        ])
    elif ext in ["pdf", "jpg", "jpeg", "png", "webp"]:
        archivo_multimodal = archivo_subido.getvalue()
        tipo_multimodal = "application/pdf" if ext == "pdf" else archivo_subido.type


def extraer_texto_de_url(url: str):
    try:
        scraper = scrape_me(url)
        pasos = "\n".join(scraper.instructions())
        ingredientes = ", ".join(scraper.ingredients())
        return f"Receta de {url}\nIngredientes: {ingredientes}\nPasos:\n{pasos}", url
    except Exception:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url


def calcular_tiempo_total(bloques_proceso: list, minutos_prep: int = 10) -> int:
    total = minutos_prep
    for bloque in bloques_proceso:
        if bloque.get("tipo") == "paralelo":
            ramas = bloque.get("ramas", [])
            max_rama = max([r.get("duracion_minutos", 5) for r in ramas], default=5)
            total += max_rama
        else:
            total += bloque.get("duracion_minutos", 5)
    return total


def generar_html_diagrama(datos: dict, origen_receta: str, comensales: int) -> str:
    nombre_receta = datos.get("nombre_receta", "Receta Culinaria")
    nivel_dificultad = datos.get("nivel_dificultad", "Cocinero Cualificado")
    ingredientes = datos.get("ingredientes", [])
    utensilios_menaje = datos.get("utensilios_menaje", [])
    pasos_previos = datos.get("pasos_previos", [])
    bloques_proceso = datos.get("bloques_proceso", [])
    recomendaciones = datos.get("recomendaciones", [])
    texto_voz = datos.get("texto_voz", "")
    maridaje = datos.get("maridaje", {})

    tiempo_total_min = calcular_tiempo_total(bloques_proceso, max(5, len(pasos_previos
