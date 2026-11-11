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
from html_renderer import generar_html_dashboard

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
    }
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
    }
    .stButton > button:hover { background: #00CC52 !important; }
    h1, h2, h3, h4, h5, h6 { font-family: 'Montserrat', sans-serif !important; color: #FFFFFF !important; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Panel de Control")
API_KEY_INPUT = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else ""
)
modelo_seleccionado = st.sidebar.selectbox("Modelo Gemini:", options=["gemini-2.5-flash", "gemini-2.5-pro"], index=0)
comensales_objetivo = st.sidebar.number_input("👥 Comensales:", min_value=1, max_value=100, value=4, step=1)

st.markdown("<h1 style='text-align: center; color: #FFFFFF; font-weight: 900;'>FACEFOODCHEF <span style='font-size: 14px; background: #00FF66; color: #1E1E1E; padding: 4px 10px; border-radius: 4px;'>MOTOR DE DIAGRAMAS</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #E2E8F0; margin-bottom: 30px;'>Convierte recetas textuales en diagramas de flujo de producción culinaria con audio guiado</p>", unsafe_allow_html=True)

entrada_principal = st.text_area("Pega la URL de la receta o el texto completo:", height=130)

with st.expander("📁 Adjuntar archivo (PDF, Word, PPT o Imagen)"):
    archivo_subido = st.file_uploader("Subir documento:", type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"])

receta_texto_input = ""
url_origen_detectada = ""
archivo_multimodal = None
tipo_multimodal = None

if entrada_principal.strip():
    texto_limpio = entrada_principal.strip()
    if texto_limpio.startswith("http://") or texto_limpio.startswith("https://"):
        url_origen_detectada = texto_limpio.split("http")[-1]
        url_origen_detectada = "http" + url_origen_detectada if not url_origen_detectada.startswith("http") else url_origen_detectada
    else:
        receta_texto_input = texto_limpio

if archivo_subido:
    ext = archivo_subido.name.split('.')[-1].lower()
    if ext == "txt":
        receta_texto_input = archivo_subido.getvalue().decode("utf-8")
    elif ext == "docx" and HAS_DOCX:
        doc = docx.Document(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == "pptx" and HAS_PPTX:
        prs = pptx.Presentation(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs])
    elif ext in ["pdf", "jpg", "jpeg", "png", "webp"]:
        archivo_multimodal = archivo_subido.getvalue()
        tipo_multimodal = "application/pdf" if ext == "pdf" else archivo_subido.type

def extraer_texto_de_url(url):
    url = url.strip()
    try:
        scraper = scrape_me(url)
        return f"Receta de {url}:\nIngredientes: {', '.join(scraper.ingredients())}\nPasos:\n{'\n'.join(scraper.instructions())}", url
    except Exception:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()
        return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url

procesar_accion = bool(url_origen_detectada or receta_texto_input or archivo_multimodal)
contenido_ia = url_origen_detectada if url_origen_detectada else receta_texto_input

if st.button("🚀 GENERAR DIAGRAMA DE FLUJO CULINARIO"):
    if not API_KEY_INPUT.strip():
        st.error("⚠️ Introduce tu clave de API de Gemini.")
    elif not procesar_accion:
        st.warning("⚠️ Debes introducir un texto, URL o archivo.")
    else:
        try:
            client = genai.Client(api_key=API_KEY_INPUT.strip())
            prompt_sistema = f"""
            Eres maestro chef y experto en flujos culinarios. Transforma la receta en un JSON estricto recalculado para {comensales_objetivo} comensales.
            Nivel de dificultad: "Superviviente Básico", "Cocinero Cualificado" o "Doctor Chef".
            Estructura JSON exacta requerida:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "nivel_dificultad": "Cocinero Cualificado",
              "ingredientes": ["400 g de harina"],
              "utensilios_menaje": ["Cuchillo"],
              "pasos_previos": ["Cortar verduras"],
              "bloques_proceso": [
                {{"tipo": "secuencial", "es_critico": false, "accion": "Paso 1", "utensilios": ["Sartén"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "180 ºC"}}
              ],
              "recomendaciones": ["Alerta importante"],
              "texto_voz": "Resumen narrado",
              "maridaje": {{"vinos": ["Vino A"], "cervezas": ["Cerveza A"]}}
            }}
            """
            contents_payload = [prompt_sistema, f"Receta:\n{contenido_ia}"]
            if archivo_multimodal:
                contents_payload = [prompt_sistema, types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal)]

            response = client.models.generate_content(
                model=modelo_seleccionado,
                contents=contents_payload,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
            )
            
            datos = json.loads(response.text.strip())
            html_final = generar_html_dashboard(datos, comensales_objetivo)
            
            st.success("¡Diagrama generado con éxito!")
            st.download_button("💾 Descargar HTML", data=html_final, file_name="diagrama.html", mime="text/html")
            components.html(html_final, height=1250, scrolling=True)
        except Exception as e:
            st.error(f"Error al generar: {e}")
