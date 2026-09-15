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
    from pptx import Presentation
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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&family=Montserrat:wght@700;900&display=swap');

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

    .stButton > button {
        background: #EF4444 !important;
        color: #FFFFFF !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
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
        background: #DC2626 !important;
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
    help="Introduce tu clave de API de Google Gemini."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-3.6-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)

comensales_objetivo = st.sidebar.number_input(
    "👥 Número de comensales:",
    min_value=1,
    max_value=100,
    value=2,
    step=1,
    help="El sistema recalculará los ingredientes para este número de personas."
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🎨 Código de Bordes (Lado Izquierdo):
- 🟢 **Verde Neón (`#00FF66`):** Ingredientes / Entradas / Maridaje
- 🟡 **Amarillo (`#FFB300`):** Acciones / Procesado
- 🔴 **Rojo FaceFoodChef (`#EF4444`):** Alertas / Puntos Críticos
- 🟡 **Dorado (`#FFD700`):** Plato Terminado
""")

# Encabezado Principal
st.markdown("<h1 style='text-align: center; color: #FFFFFF; font-family: Montserrat, sans-serif; font-weight: 900; letter-spacing: 2px; margin-bottom: 0; font-size: clamp(20px, 4vw, 32px);'>FACEFOODCHEF <span style='font-size: clamp(10px, 2vw, 14px); background: #EF4444; color: #FFF; padding: 4px 10px; border-radius: 4px; vertical-align: middle; letter-spacing: 1px;'>MOTOR DE DIAGRAMAS</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #E2E8F0; font-size: clamp(13px, 2vw, 15px); margin-bottom: 30px; font-family: Inter, sans-serif;'>Convierte recetas textuales en diagramas de flujo de producción culinaria</p>", unsafe_allow_html=True)

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
    elif ext in ["pdf", "jpg", "jpeg", "png", "webp"]:
        archivo_multimodal = archivo_subido.getvalue()
        tipo_multimodal = "application/pdf" if ext == "pdf" else archivo_subido.type

def extraer_texto_de_url(url):
    url = url.strip()
    try:
        scraper = scrape_me(url)
        texto = f"Receta de {url}:\nIngredientes: {', '.join(scraper.ingredients())}\nPasos:\n{'\n'.join(scraper.instructions())}"
        return texto, url
    except Exception:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url
        except Exception as e:
            raise Exception(f"Error al procesar la URL: {e}")

def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, utensilios_menaje, pasos_previos, bloques_proceso, recomendaciones, texto_voz, maridaje, comensales):
    COLOR_VERDE_ING = "#00FF66"      
    COLOR_AMARILLO_ACC = "#FFB300"   
    COLOR_ROJO_ALERTA = "#EF4444"    
    COLOR_DORADO_PLATO = "#FFD700"   

    html_header = f"""
    <div style="background-color: #2C2F33; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 20px; border-left: 6px solid {COLOR_DORADO_PLATO}; border-top: none; border-right: none; border-bottom: none;">
        <span style="font-size: 11px; font-weight: 700; color: #2C2F33; text-transform: uppercase; letter-spacing: 2px; background: {COLOR_DORADO_PLATO}; padding: 4px 12px; border-radius: 3px; display: inline-block; font-family: 'Montserrat', sans-serif;">Flujo Culinario Completo</span>
        <h1 style="color: #FFFFFF; font-size: clamp(18px, 4vw, 24px); margin: 10px 0 6px 0; font-weight: 900; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">{nombre_receta}</h1>
        <p style="color: #E2E8F0; font-size: clamp(12px, 2vw, 14px); margin: 0; font-family: 'Inter', sans-serif;">Receta adaptada para <b>{comensales} personas</b></p>
    </div>
    """

    html_ing = f"""
    <div style="background-color: #2C2F33; border-left: 6px solid {COLOR_VERDE_ING}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #4F545C; padding-bottom: 8px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h3 style="color: {COLOR_VERDE_ING}; margin: 0; font-size: clamp(14px, 2.5vw, 16px); font-weight: 700; font-family: 'Montserrat', sans-serif;">🛒 1. Ingredientes ({comensales} pax)</h3>
            <a href="https://www.facefoodchef.com/tienda-gourmet" target="_blank" style="background-color: {COLOR_VERDE_ING}; color: #2C2F33; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">🛒 Ir a la tienda gourmet</a>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background-color: #36393F; color: #E2E8F0; padding: 8px 12px; border-radius: 4px; font-size: clamp(12px, 2vw, 14px); font-family: \"Inter\", sans-serif;'>{ing}</span>"
    html_ing += "</div></div>"

    html_utensilios = f"""
    <div style="background-color: #2C2F33; border-left: 6px solid #4F545C; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #4F545C; padding-bottom: 8px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h3 style="color: #FFFFFF; margin: 0; font-size: clamp(14px, 2.5vw, 16px); font-weight: 700; font-family: 'Montserrat', sans-serif;">🛠️ 2. Utensilios y Menaje</h3>
            <a href="https://www.facefoodchef.com/tienda-menaje" target="_blank" style="background-color: #EF4444; color: #FFFFFF; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">🛒 Tienda de Menaje</a>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    """
    for ut in utensilios_menaje:
        html_utensilios += f"<span style='background-color: #36393F; color: #E2E8F0; padding: 6px 10px; border-radius: 4px; font-size: clamp(12px, 2vw, 14px); font-family: \"Inter\", sans-serif;'>{ut}</span>"
    html_utensilios += "</div></div>"

    html_prev = """
    <div style="background-color: #2C2F33; border-left: 6px solid #4F545C; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-bottom: 20px;">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: clamp(14px, 2.5vw, 16px); font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #4F545C; padding-bottom: 8px;">🔪 3. Preparación Previa (Mise en Place)</h3>
        <ul style='margin: 12px 0 0 0; padding-left: 18px; color: #E2E8F0; font-size: clamp(13px, 2.2vw, 15px); line-height: 1.6; font-family: "Inter", sans-serif;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li style='margin-bottom: 6px;'>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div style="font-family: 'Inter', sans-serif;">
        <h3 style="color: #FFFFFF; font-size: clamp(16px, 3vw, 18px); font-weight: 700; margin-bottom: 16px; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #EF4444; padding-bottom: 6px; display: inline-block;">4. Diagrama de Ejecución y Flujo</h3>
    """

    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        es_critico = bloque.get("es_critico", False)
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "N/A"

        borde_color = COLOR_ROJO_ALERTA if es_critico else COLOR_AMARILLO_ACC

        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += '<div style="display: flex; gap: 12px; margin-bottom: 14px; flex-wrap: wrap;">'
            for idx, rama in enumerate(ramas):
                nombre_rama = rama.get("nombre", f"Subproceso {idx+1}").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                utensilios_rama = ", ".join(rama.get("utensilios", []))
                dur_rama = rama.get("duracion_minutos", 5)
                timer_id = f"timer_par_{i}_{idx}"
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 260px; background-color: #2C2F33; border-left: 6px solid {COLOR_AMARILLO_ACC}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px;">
                    <div style="margin-bottom: 8px;"><span style="font-size: 10px; font-weight: 700; color: #2C2F33; background-color: {COLOR_AMARILLO_ACC}; padding: 3px 8px; border-radius: 2px; text-transform: uppercase; font-family: 'Montserrat', sans-serif;">⚙️ PARALELO: {nombre_rama}</span></div>
                    <div style="font-size: clamp(13px, 2.2vw, 15px); font-weight: 500; color: #FFFFFF; margin: 8px 0; line-height: 1.5; font-family: 'Inter', sans-serif;">{accion}</div>
                    <div style="font-size: clamp(11px, 2vw, 13px); color: #E2E8F0; margin-bottom: 10px; font-family: 'Inter', sans-serif;">🛠️ <b>Utensilios:</b> {utensilios_rama}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #36393F; padding: 8px 12px; border-radius: 4px; flex-wrap: wrap; gap: 6px;">
                        <div style="font-size: clamp(12px, 2vw, 14px); color: #FFB300; font-family: 'JetBrains Mono', monospace; font-weight: 600;">⏱️ <span id="{timer_id}">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" style="background-color: #EF4444; color: #FFF; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            timer_id = f"timer_seq_{i}"
            etiqueta = "UNIÓN / CONVERGENCIA" if tipo == "convergencia" else f"PASO {i+1}"
            
            html_diagrama += f"""
            <div style="background-color: #2C2F33; border-left: 6px solid {borde_color}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-bottom: 14px;">
                <div style="margin-bottom: 8px;">
                    <span style="font-size: 10px; font-weight: 700; color: #2C2F33; background-color: {borde_color}; padding: 3px 8px; border-radius: 2px; text-transform: uppercase; font-family: 'Montserrat', sans-serif;">{etiqueta}</span>
                </div>
                <div style="font-size: clamp(13px, 2.2vw, 15px); font-weight: 500; color: #FFFFFF; margin: 8px 0; line-height: 1.5; font-family: 'Inter', sans-serif;">{bloque.get('accion')}</div>
                <div style="font-size: clamp(11px, 2vw, 13px); color: #E2E8F0; margin-bottom: 10px; font-family: 'Inter', sans-serif;">🛠️ <b>Utensilios:</b> {utensilios_str}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: #36393F; padding: 8px 12px; border-radius: 4px; flex-wrap: wrap; gap: 6px;">
                    <div style="font-size: clamp(12px, 2vw, 14px); color: #FFB300; font-family: 'JetBrains Mono', monospace; font-weight: 600;">⏱️ <span id="{timer_id}">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" style="background-color: #EF4444; color: #FFF; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += f"""
            <div style="text-align: center; margin: 4px 0 10px 0;">
                <span style="color: {COLOR_AMARILLO_ACC}; font-size: 18px; font-weight: bold;">↓</span>
            </div>
            """

    html_diagrama += f"""
    <div style="text-align: center; margin: 4px 0 10px 0;">
        <span style="color: {COLOR_DORADO_PLATO}; font-size: 18px; font-weight: bold;">↓</span>
    </div>
    <div style="background-color: #2C2F33; border-left: 6px solid {COLOR_DORADO_PLATO}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; text-align: center; margin-top: 10px;">
        <span style="font-size: 11px; font-weight: 700; color: #2C2F33; background-color: {COLOR_DORADO_PLATO}; padding: 4px 10px; border-radius: 3px; font-family: 'Montserrat', sans-serif;">RESULTADO FINAL</span>
        <h3 style="color: {COLOR_DORADO_PLATO}; margin: 8px 0 0 0; font-weight: 900; font-family: 'Montserrat', sans-serif; font-size: clamp(15px, 2.8vw, 18px);">🍽️ PLATO LISTO PARA SERVIR</h3>
    </div>
    </div>
    """

    html_recom = f"""
    <div style="background-color: #2C2F33; border-left: 6px solid {COLOR_ROJO_ALERTA}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-top: 20px; margin-bottom: 16px;">
        <h3 style="color: {COLOR_ROJO_ALERTA}; margin-top: 0; font-size: clamp(14px, 2.5vw, 16px); font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #4F545C; padding-bottom: 8px;">🚨 5. Puntos Críticos y Alertas del Chef</h3>
        <ul style='margin: 12px 0 0 0; padding-left: 18px; color: #E2E8F0; font-size: clamp(13px, 2.2vw, 15px); line-height: 1.6; font-family: "Inter", sans-serif;'>
    """
    for rec in recomendaciones:
        html_recom += f"<li style='margin-bottom: 6px;'>{rec}</li>"
    html_recom += "</ul></div>"

    vinos_lista = maridaje.get('vinos', [])
    cervezas_lista = maridaje.get('cervezas', [])
    vinos_html = "".join([f"<li style='margin-bottom: 4px;'>{v}</li>" for v in vinos_lista]) if vinos_lista else "<li>Sin opciones disponibles.</li>"
    cervezas_html = "".join([f"<li style='margin-bottom: 4px;'>{c}</li>" for c in cervezas_lista]) if cervezas_lista else "<li>Sin opciones disponibles.</li>"

    html_maridaje = f"""
    <div style="background-color: #2C2F33; border-left: 6px solid {COLOR_VERDE_ING}; border-top: none; border-right: none; border-bottom: none; border-radius: 6px; padding: 16px; margin-top: 16px; margin-bottom: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #4F545C; padding-bottom: 8px; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <h3 style="color: {COLOR_VERDE_ING}; margin: 0; font-size: clamp(14px, 2.5vw, 16px); font-weight: 700; font-family: 'Montserrat', sans-serif;">🍷 6. Maridaje</h3>
            <a href="https://www.facefoodchef.com/bodega" target="_blank" style="background-color: {COLOR_VERDE_ING}; color: #2C2F33; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">🛒 Ir a la bodega</a>
        </div>
        <div style="margin-top: 12px; color: #E2E8F0; font-size: clamp(13px, 2.2vw, 15px); line-height: 1.6; font-family: 'Inter', sans-serif;">
            <p style="margin-bottom: 4px; color: #FFFFFF;"><b>🍇 Vinos (Denominaciones de Origen):</b></p>
            <ul style="margin: 0 0 10px 0; padding-left: 18px;">{vinos_html}</ul>
            <p style="margin-bottom: 4px; color: #FFFFFF;"><b>🍺 Cervezas:</b></p>
            <ul style="margin: 0; padding-left: 18px;">{cervezas_html}</ul>
        </div>
    </div>
    """

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #9AA0A6; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span style="color: #9AA0A6;">{origen_receta}</span>'
    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;600&family=Montserrat:wght@700;900&display=swap" rel="stylesheet">
        <style>
            body {{ background-color: #36393F; color: #E2E8F0; font-family: 'Inter', sans-serif; padding: 12px; margin: 0; }}
            .container-hub {{ max-width: 900px; margin: auto; }}
            .widget-box {{ background-color: #2C2F33; border-radius: 6px; padding: 16px; text-align: center; margin-bottom: 16px; }}
            .btn-control {{ background: #EF4444; color: #FFF; border: none; padding: 10px 16px; font-size: 12px; font-weight: 700; border-radius: 4px; cursor: pointer; margin: 4px; font-family: 'Montserrat', sans-serif; text-transform: uppercase; }}
            .btn-stop {{ background: #4F545C; color: #FFF; }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}
            <div class="widget-box">
                <p style="color: #E2E8F0; font-size: 12px; margin: 0 0 10px 0; font-weight: 700; font-family: 'Montserrat', sans-serif;">👨‍🍳 ASISTENTE AUDITIVO</p>
                <button id="btnVoz" class="btn-control" onclick="reproducir(this)">🎧 Escuchar Pasos</button>
                <button class="btn-control btn-stop" onclick="detener()">Silenciar</button>
            </div>
            {html_ing}
            {html_utensilios}
            {html_prev}
            {html_diagrama}
            {html_recom}
            {html_maridaje}
            <div style="text-align: center; color: #9AA0A6; font-size: 11px; margin-top: 24px; border-top: 1px solid #4F545C; padding-top: 14px; font-family: 'Inter', sans-serif; word-break: break-all;">
                FaceFoodChef.com | Origen: {origen_html}
            </div>
        </div>
        <script>
            const textoVoz = {texto_voz_seguro};
            let currentUtterance = null;

            function reproducir(btn) {{
                if (!('speechSynthesis' in window)) return alert("Sintetizador no soportado.");
                window.speechSynthesis.cancel();
                currentUtterance = new SpeechSynthesisUtterance(textoVoz);
                currentUtterance.lang = 'es-ES';
                currentUtterance.rate = 0.95;
                btn.innerText = "🔊 Reproduciendo...";
                currentUtterance.onend = () => btn.innerText = "🎧 Escuchar Pasos";
                currentUtterance.onerror = () => btn.innerText = "🎧 Escuchar Pasos";
                window.speechSynthesis.speak(currentUtterance);
            }}

            function detener() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const btn = document.getElementById('btnVoz');
                    if (btn) btn.innerText = "🎧 Escuchar Pasos";
                }}
            }}

            function iniciarTemporizador(elementId, minutos) {{
                const elemento = document.getElementById(elementId);
                let segundosRestantes = minutos * 60;
                if (window[elementId + "_interval"]) clearInterval(window[elementId + "_interval"]);

                window[elementId + "_interval"] = setInterval(() => {{
                    if (segundosRestantes <= 0) {{
                        clearInterval(window[elementId + "_interval"]);
                        elemento.innerText = "¡FINALIZADO!";
                        sonarAlerta();
                    }} else {{
                        segundosRestantes--;
                        const m = Math.floor(segundosRestantes / 60);
                        const s = segundosRestantes % 60;
                        elemento.innerText = m + "m " + (s < 10 ? "0" : "") + s + "s";
                    }}
                }}, 1000);
            }}

            function sonarAlerta() {{
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const freq = 880;
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
                gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.5);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.5);
            }}
        </script>
    </body>
    </html>
    """

procesar_accion = False
contenido_ia = None

if url_origen_detectada:
    try:
        with st.spinner("🌐 Extrayendo datos de la URL..."):
            contenido_ia, url_origen_detectada = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error(f"{e}")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif archivo_multimodal:
    procesar_accion = True

if st.button("🚀 GENERAR DIAGRAMA DE FLUJO CULINARIO"):
    api_key_activa = API_KEY_INPUT.strip()
    
    if not api_key_activa:
        st.error("⚠️ Introduce tu clave de API de Google Gemini.")
    elif not procesar_accion:
        st.warning("⚠️ Debes introducir un texto, URL o adjuntar un archivo.")
    else:
        try:
            client = genai.Client(api_key=api_key_activa)
            
            prompt_sistema = f"""
            Eres un experto programador de flujos culinarios y maestro chef. 
            Transforma la receta dada en una estructura JSON optimizada para generar un diagrama de flujo paso a paso apto para pantallas móviles.

            Recalcula las cantidades exactamente para {comensales_objetivo} COMENSALES.

            REGLAS ESTRUCTURALES Y JSON:
            1. UNIDADES: Abreviadas (g, kg, ml, l, ºC, min). Escribir "cucharada" y "cucharadita" completas. Evita términos ambiguos ("al gusto").
            2. MODULARIZACIÓN:
               - Separa la lista de "utensilios_menaje".
               - Separa la lista de "pasos_previos" (Mise en place).
            3. BLOQUES DE PROCESO:
               - "tipo": "secuencial", "paralelo" or "convergencia".
               - "es_critico": booleano (true si requiere especial precaución técnica o de seguridad).
            4. MARIDAJE:
               - Evalúa todas las Denominaciones de Origen (sin restricción geográfica).
               - Genera EXACTAMENTE 3 propuestas de vinos indicando tipo o Denominación de Origen idónea.
               - Genera EXACTAMENTE 3 propuestas de cervezas acordes al plato.
            5. Devuelve EXCLUSIVAMENTE el JSON estructurado sin formato adicional fuera de él.

            JSON Schema esperado:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["400 g de harina"],
              "utensilios_menaje": ["Cuchillo", "Sartén"],
              "pasos_previos": ["Cortar vegetales"],
              "bloques_proceso": [
                {{"tipo": "secuencial", "es_critico": false, "accion": "Descripción del paso", "utensilios": ["Sartén"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "180 ºC"}},
                {{
                  "tipo": "paralelo",
                  "es_critico": false,
                  "ramas": [
                    {{"nombre": "Salsa", "accion": "Reducir el líquido", "utensilios": ["Cazo"], "tiempo": "10 min", "duracion_minutos": 10, "temperatura": "90 ºC"}}
                  ]
                }}
              ],
              "recomendaciones": ["Punto crítico de cocción"],
              "texto_voz": "Resumen narrado del proceso",
              "maridaje": {{
                "vinos": [
                  "1. Vino Tinto crianza (D.O. Ribera del Duero)",
                  "2. Vino Blanco Verdejo (D.O. Rueda)",
                  "3. Vino Rosado (D.O. Navarra)"
                ],
                "cervezas": [
                  "1. Cerveza Pilsner tradicional",
                  "2. Cerveza de Trigo (Weissbier)",
                  "3. Cerveza Negra (Stout)"
                ]
              }}
            }}
            """

            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append(f"Procesa la receta adjunta ajustada a {comensales_objetivo} personas.")
            else:
                contents_payload.append(f"Receta:\n{contenido_ia}")

            modelos_a_probar = [modelo_seleccionado, "gemini-3.6-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
            modelos_a_probar = list(dict.fromkeys(modelos_a_probar))
            
            response = None
            exito = False
            
            with st.spinner("⚡ Generando diagrama adaptado a dispositivos móviles..."):
                for mod in modelos_a_probar:
                    intentos = 3
                    for intento in range(intentos):
                        try:
                            response = client.models.generate_content(
                                model=mod,
                                contents=contents_payload,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json"
                                ),
                            )
                            if response and response.text:
                                exito = True
                                break
                        except Exception as api_err:
                            err_str = str(api_err)
                            if "503" in err_str or "UNAVAILABLE" in err_str:
                                time.sleep((intento + 1) * 2)
                                continue
                            if intento == intentos - 1:
                                break
                    if exito:
                        break

            if response and exito:
                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                elif texto_respuesta.startswith("```"):
                    texto_respuesta = texto_respuesta[3:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]
                
                datos = json.loads(texto_respuesta.strip())
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto introducido por el usuario")

                html_final = generar_html_dashboard(
                    datos.get("nombre_receta", "Receta Culinaria"),
                    origen_final,
                    datos.get("ingredientes", []),
                    datos.get("utensilios_menaje", []),
                    datos.get("pasos_previos", []),
                    datos.get("bloques_proceso", []),
                    datos.get("recomendaciones", []),
                    datos.get("texto_voz", ""),
                    datos.get("maridaje", {}),
                    comensales_objetivo
                )
                
                st.success("¡Diagrama optimizado generado con éxito!")
                
                nombre_archivo = f"diagrama_{datos.get('nombre_receta', 'receta').lower().replace(' ', '_')}.html"
                st.download_button(
                    label="💾 Descargar Diagrama en HTML",
                    data=html_final,
                    file_name=nombre_archivo,
                    mime="text/html"
                )
                
                components.html(html_final, height=1200, scrolling=True)
            else:
                st.error("No se pudo obtener una respuesta válida del modelo Gemini.")
                
        except APIError as e:
            st.error(f"Error de la API de Gemini: {e}")
        except Exception as e:
            st.error(f"Error inesperado al procesar los datos: {e}")
