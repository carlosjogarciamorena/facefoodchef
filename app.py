import json
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import streamlit as st
from recipe_scrapers import scrape_me
import google.generativeai as genai

# Importaciones opcionales para lectura de documentos
try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from pptx import Presentation
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

# Configuración de página
st.set_page_config(
    page_title="FaceFoodChef.com - Motor de Diagramas Culinarios", 
    layout="wide", 
    page_icon="🍳"
)

# ESTILOS VISUALES
st.markdown("""
    <style>
    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    header, footer { visibility: hidden; }
    
    .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #36393F !important;
        color: #ffffff !important;
        border: 2px solid #4F545C !important;
        border-radius: 6px !important;
        font-size: 16px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #EF4444 !important;
        box-shadow: 0 0 10px rgba(239, 68, 68, 0.4) !important;
    }

    .stButton > button {
        background-color: #EF4444 !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 17px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 14px 28px !important;
        width: 100%;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
    }
    .stButton > button:hover {
        background-color: #dc2626 !important;
    }

    .streamlit-expanderHeader {
        background-color: #36393F !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #4F545C !important;
    }
    </style>
""", unsafe_allow_html=True)

# Panel de Control
st.sidebar.header("⚙️ Panel de Control")

API_KEY = st.sidebar.text_input(
    "🔑 API Key de Google Gemini:", 
    type="password", 
    help="Introduce tu clave API de Google AI Studio."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)

comensales_objetivo = st.sidebar.number_input(
    "👥 Número de comensales:",
    min_value=1,
    max_value=100,
    value=2,
    step=1
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🎬 FaceFoodChef.com
- **Métricas:** Escalado adaptativo (g, ml, ud)
- **Estructura:** Flujos secuenciales y paralelos
- **Sommelier:** Maridaje automático
""")

st.markdown("<h1 style='text-align: center; color: #EF4444; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>FACEFOODCHEF <span style='font-size: 16px; background: #36393F; color: #fff; padding: 4px 10px; border-radius: 4px; border: 1px solid #4F545C;'>PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; font-size: 15px; margin-bottom: 30px;'>Diagramas de cocina escalables + Sommelier Virtual</p>", unsafe_allow_html=True)

# Entrada de Datos
st.subheader("📥 Entrada de Receta")
entrada_principal = st.text_area(
    "Pega la URL de la receta o el texto completo:", 
    height=130, 
    placeholder="https://www.ejemplo.com/receta\nO pega directamente el texto de la receta aquí..."
)

with st.expander("📁 Adjuntar archivo (TXT, PDF, Word, PPT o Imagen)"):
    archivo_subido = st.file_uploader("Subir documento:", type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png"])

receta_texto_input = ""
url_origen_detectada = ""
datos_archivo = None

if entrada_principal.strip():
    texto_limpio = entrada_principal.strip()
    if texto_limpio.startswith("http://") or texto_limpio.startswith("https://"):
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
    elif ext == "pptx" and HAS_PPTX:
        prs = Presentation(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs])
    else:
        datos_archivo = {"mime_type": archivo_subido.type, "data": archivo_subido.getvalue()}

def extraer_texto_de_url(url):
    try:
        scraper = scrape_me(url)
        return f"Ingredientes: {', '.join(scraper.ingredients())}\nPasos:\n{'\n'.join(scraper.instructions())}", url
    except Exception:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()
        return soup.get_text(separator='\n', strip=True), url

def renderizar_dashboard(datos, comensales, origen):
    st.markdown(f"""
    <div style="background: linear-gradient(180deg, #36393F 0%, #2F3136 100%); border-radius: 8px; padding: 25px; text-align: center; margin-bottom: 20px; border-left: 6px solid #EF4444; border: 1px solid #4F545C;">
        <h2 style="color: #ffffff; margin: 0;">{datos.get("nombre_receta", "Receta")}</h2>
        <p style="color: #A0AEC0; font-size: 14px; margin: 5px 0 0 0;">Escalado para <b>{comensales} comensales</b>.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🛒 1. Ingredientes")
    for ing in datos.get("ingredientes", []):
        st.markdown(f"- {ing}")

    st.markdown("### 3. Diagrama de Ejecución")
    for i, bloque in enumerate(datos.get("bloques_proceso", [])):
        tipo = bloque.get("tipo", "secuencial")
        
        if tipo == "paralelo":
            st.markdown("#### ⚙️ Bloque en Paralelo")
            ramas = bloque.get("ramas", [])
            cols = st.columns(len(ramas) if ramas else 1)
            for idx, rama in enumerate(ramas):
                with cols[idx]:
                    st.markdown(f"""
                    <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 5px solid #F59E0B; padding: 15px; border-radius: 6px;">
                        <b style="color: #F59E0B;">{rama.get('nombre', 'Rama')}</b><br>
                        <p style="margin: 8px 0; font-size: 14px;">{rama.get('accion')}</p>
                        <span style="font-size: 12px; color: #A0AEC0;">⏱️ {rama.get('tiempo')} | 🌡️ {rama.get('temperatura')}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            es_conv = tipo == "convergencia"
            color = "#10B981" if es_conv else "#EF4444"
            etiqueta = "CONVERGENCIA" if es_conv else f"PASO {i+1}"
            
            st.markdown(f"""
            <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 6px solid {color}; padding: 16px; border-radius: 6px; margin-bottom: 15px;">
                <span style="font-size: 10px; font-weight: bold; background: {color}; color: white; padding: 3px 8px; border-radius: 3px;">{etiqueta}</span>
                <p style="margin: 10px 0; font-weight: bold;">{bloque.get('accion')}</p>
                <div style="font-size: 13px; color: #A0AEC0;">
                    🛠️ {", ".join(bloque.get('utensilios', []))} | ⏱️ {bloque.get('tiempo')} | 🌡️ {bloque.get('temperatura')}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        if i < len(datos.get("bloques_proceso", [])) - 1:
            st.markdown("<div style='text-align: center;'>⬇️</div>", unsafe_allow_html=True)

    if datos.get("maridaje"):
        st.markdown("### 🍷 4. Sommelier Virtual")
        c1, c2 = st.columns(2)
        c1.info(f"**Vino:** {datos['maridaje'].get('vino', '')}")
        c2.warning(f"**Cerveza:** {datos['maridaje'].get('cerveza', '')}")

procesar_accion = False
contenido_ia = ""

if url_origen_detectada:
    try:
        with st.spinner("🌐 Obteniendo datos de la URL..."):
            contenido_ia, _ = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error("Error al leer la URL.")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif datos_archivo:
    procesar_accion = True

if st.button("🎬 GENERAR DIAGRAMA"):
    if not API_KEY:
        st.error("⚠️ Introduce tu API Key de Google Gemini en el panel izquierdo.")
    elif not procesar_accion:
        st.warning("⚠️ Introduce una receta (texto, URL o archivo).")
    else:
        try:
            # Configuración estable (Estilo Clásico)
            genai.configure(api_key=API_KEY.strip())
            
            prompt = f"""
            Analiza esta receta y conviértela en JSON.
            Recalcula las cantidades de ingredientes EXACTAMENTE para {comensales_objetivo} COMENSALES.

            Estructura JSON obligatoria:
            {{
              "nombre_receta": "Nombre",
              "ingredientes": ["Lista escalada para {comensales_objetivo} pax"],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "Hervir agua", "utensilios": ["Olla"], "tiempo": "10 min", "temperatura": "100°C"}},
                {{
                  "tipo": "paralelo",
                  "ramas": [
                    {{"nombre": "Sartén", "accion": "Freír", "tiempo": "5 min", "temperatura": "Alta"}},
                    {{"nombre": "Olla", "accion": "Cocer", "tiempo": "5 min", "temperatura": "Media"}}
                  ]
                }},
                {{"tipo": "convergencia", "accion": "Mezclar todo", "utensilios": ["Bol"], "tiempo": "2 min", "temperatura": "Ambiente"}}
              ],
              "maridaje": {{
                "vino": "Recomendación y por qué",
                "cerveza": "Recomendación y por qué"
              }}
            }}
            Solo responde con código JSON puro, sin bloques ```json.
            """

            model = genai.GenerativeModel(modelo_seleccionado)
            
            payload = [prompt]
            if datos_archivo:
                payload.append({"mime_type": datos_archivo["mime_type"], "data": datos_archivo["data"]})
            else:
                payload.append(contenido_ia)

            with st.spinner(f"⚙️ Procesando diagrama para {comensales_objetivo} pax..."):
                response = model.generate_content(payload)
                
                texto_json = response.text.strip()
                if texto_json.startswith("```json"): texto_json = texto_json[7:]
                if texto_json.startswith("```"): texto_json = texto_json[3:]
                if texto_json.endswith("```"): texto_json = texto_json[:-3]
                
                datos = json.loads(texto_json.strip())
                renderizar_dashboard(datos, comensales_objetivo, "Fuente")
                
        except Exception as e:
            st.error(f"Error al generar con Gemini: {e}")
