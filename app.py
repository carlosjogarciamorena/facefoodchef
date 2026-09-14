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

st.set_page_config(
    page_title="FaceFoodChef.com - Motor de Diagramas Culinarios Pro V3", 
    layout="wide", 
    page_icon="🍳"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;900&family=Inter:wght@400;500&display=swap');

    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #141414 !important;
        color: #E5E5E5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    header, footer { visibility: hidden; }
    
    .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #181818 !important;
        color: #FFFFFF !important;
        border: 1px solid #282828 !important;
        border-radius: 4px !important;
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #E50914 !important;
        box-shadow: none !important;
    }

    .stButton > button {
        background-color: #E50914 !important;
        color: #FFFFFF !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 14px 30px !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: background-color 0.3s ease !important;
    }
    .stButton > button:hover {
        background-color: #F40612 !important;
    }

    .stDownloadButton > button {
        background-color: #181818 !important;
        color: #FFFFFF !important;
        border: 1px solid #E50914 !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
        border-radius: 4px !important;
        width: 100%;
        padding: 10px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stDownloadButton > button:hover {
        background-color: #E50914 !important;
        color: #FFFFFF !important;
    }

    .streamlit-expanderHeader {
        background-color: #181818 !important;
        color: #FFFFFF !important;
        border-radius: 4px !important;
        border: 1px solid #282828 !important;
        font-family: 'Montserrat', sans-serif !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
        color: #FFFFFF !important;
        text-transform: uppercase;
    }
    </style>
""", unsafe_allow_html=True)

st.sidebar.header("⚙️ Panel de Control V3")

API_KEY_INPUT = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google Gemini manualmente."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini (con fallback automático):",
    options=["gemini-2.5-flash", "gemini-3.6-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
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
### 🌟 Mejoras Aplicadas V3.1
- **Estructura Modular Separada:** Utensilios/Menaje y Preparación Previa totalmente independientes.
- **Enlace a Tienda Pro:** Botón directo integrado en la sección de utensilios para adquisición de menaje.
- **Estética Cinematográfica:** Interfaz oscura de alto contraste estilo Netflix.
- **Sommelier Manchego Avanzado:** Propuestas de vino de Castilla-La Mancha y cervezas artesanales.
""")

st.markdown("<h1 style='text-align: center; color: #FFFFFF; font-family: Montserrat, sans-serif; font-weight: 900; letter-spacing: 2px; margin-bottom: 0;'>FACEFOODCHEF <span style='font-size: 14px; background: #E50914; color: #fff; padding: 4px 10px; border-radius: 2px; vertical-align: middle; letter-spacing: 1px;'>PRO V3.1</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #B3B3B3; font-size: 15px; margin-bottom: 30px; font-family: Inter, sans-serif;'>Diagramas de cocina escalables con separación modular de menaje y preparación previa</p>", unsafe_allow_html=True)

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
    html_header = f"""
    <div style="background: #181818; border-radius: 8px; padding: 30px; text-align: center; margin-bottom: 24px; border-left: 6px solid #E50914; border: 1px solid #282828; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <span style="font-size: 11px; font-weight: 700; color: #FFFFFF; text-transform: uppercase; letter-spacing: 2px; background: #E50914; padding: 6px 14px; border-radius: 2px; display: inline-block; font-family: 'Montserrat', sans-serif;">Diagrama de Producción Culinaria V3.1</span>
        <h1 style="color: #FFFFFF; font-size: 28px; margin: 16px 0 8px 0; font-weight: 900; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">{nombre_receta}</h1>
        <p style="color: #B3B3B3; font-size: 14px; margin: 0; font-family: 'Inter', sans-serif;">Calculado y escalado para <b>{comensales} comensales</b>.</p>
    </div>
    """

    html_ing = f"""
    <div style="background-color: #181818; border: 1px solid #282828; border-radius: 8px; padding: 22px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 18px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #E50914; padding-bottom: 10px; display: inline-block;">🛒 1. Ingredientes Exactos ({comensales} pax)</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background-color: #222222; color: #E5E5E5; padding: 8px 16px; border-radius: 4px; font-size: 13px; border: 1px solid #333333; font-weight: 500; font-family: 'Inter', sans-serif;'>{ing}</span>"
    html_ing += "</div></div>"

    html_utensilios = f"""
    <div style="background-color: #181818; border: 1px solid #282828; border-radius: 8px; padding: 22px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E50914; padding-bottom: 10px; margin-bottom: 16px;">
            <h3 style="color: #FFFFFF; margin: 0; font-size: 18px; font-weight: 700; font-family: 'Montserrat', sans-serif;">🛠️ 2. Utensilios y Menaje</h3>
            <a href="https://www.facefoodchef.com/tienda-menaje" target="_blank" style="background-color: #E50914; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-size: 12px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: 1px;">🛒 Ir a la Tienda de Menaje</a>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
    """
    for ut in utensilios_menaje:
        html_utensilios += f"<span style='background-color: #222222; color: #E5E5E5; padding: 8px 16px; border-radius: 4px; font-size: 13px; border: 1px solid #333333; font-weight: 500; font-family: 'Inter', sans-serif;'>{ut}</span>"
    html_utensilios += "</div></div>"

    html_prev = """
    <div style="background-color: #181818; border: 1px solid #282828; border-radius: 8px; padding: 22px; margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 18px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #E50914; padding-bottom: 10px; display: inline-block;">🔪 3. Preparación Previa (Mise en Place)</h3>
        <ul style='margin: 16px 0 0 0; padding-left: 20px; color: #B3B3B3; font-size: 14px; line-height: 1.8; font-family: 'Inter', sans-serif;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div style="font-family: 'Inter', sans-serif;">
        <h3 style="color: #FFFFFF; font-size: 18px; font-weight: 700; margin-bottom: 22px; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #E50914; padding-bottom: 10px; display: inline-block;">4. Diagrama de Ejecución y Tiempos</h3>
    """
    
    BORDER_BLOQUE = "#282828"
    
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "Sin utensilios especificados"
        
        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += '<div style="display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap;">'
            for idx, rama in enumerate(ramas):
                nombre_rama = rama.get("nombre", f"Rama {idx+1}").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                utensilios_rama = ", ".join(rama.get("utensilios", []))
                dur_rama = rama.get("duracion_minutos", 5)
                timer_id = f"timer_par_{i}_{idx}"
                
                color_franja_paralelo = "#E50914"
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 280px; background-color: #222222; border: 1px solid {BORDER_BLOQUE}; border-left: 4px solid {color_franja_paralelo}; border-radius: 4px; padding: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.9);">
                    <div style="margin-bottom: 12px;"><span style="font-size: 11px; font-weight: 700; color: #FFFFFF; background-color: {color_franja_paralelo}; padding: 4px 10px; border-radius: 2px; display: inline-block; text-transform: uppercase; font-family: 'Montserrat', sans-serif; letter-spacing: 1px;">⚙️ PARALELO: {nombre_rama}</span></div>
                    <div style="font-size: 14px; font-weight: 500; color: #FFFFFF; margin: 12px 0; font-family: 'Inter', sans-serif; line-height: 1.6;">{accion}</div>
                    <div style="font-size: 12px; color: #B3B3B3; margin-bottom: 14px; background: #141414; padding: 8px 12px; border-radius: 4px; font-family: 'Inter', sans-serif;">🛠️ <b>Herramientas:</b> {utensilios_rama}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #141414; padding: 10px 14px; border-radius: 4px;">
                        <div style="font-size: 13px; color: #FFFFFF; font-family: 'Inter', sans-serif;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #E50914;">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" style="background-color: #E50914; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            es_convergencia = tipo == "convergencia"
            left_border = "#E50914"
            badge_bg = "#E50914"
            etiqueta = "CONVERGENCIA / UNIÓN" if es_convergencia else f"PASO {i+1}"
            timer_id = f"timer_seq_{i}"

            html_diagrama += f"""
            <div style="background-color: #222222; border: 1px solid {BORDER_BLOQUE}; border-left: 4px solid {left_border}; border-radius: 4px; padding: 20px; margin-bottom: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.9);">
                <div style="margin-bottom: 12px;"><span style="font-size: 11px; font-weight: 700; color: #FFFFFF; background-color: {badge_bg}; padding: 4px 10px; border-radius: 2px; display: inline-block; text-transform: uppercase; font-family: 'Montserrat', sans-serif; letter-spacing: 1px;">{etiqueta}</span></div>
                <div style="font-size: 14px; font-weight: 500; color: #FFFFFF; margin: 12px 0; font-family: 'Inter', sans-serif; line-height: 1.6;">{bloque.get('accion')}</div>
                <div style="font-size: 12px; color: #B3B3B3; margin-bottom: 14px; background: #141414; padding: 8px 12px; border-radius: 4px; font-family: 'Inter', sans-serif;">🛠️ <b>Herramientas:</b> {utensilios_str}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: #141414; padding: 10px 14px; border-radius: 4px;">
                    <div style="font-size: 13px; color: #FFFFFF; font-family: 'Inter', sans-serif;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #E50914;">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" style="background-color: #E50914; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += """
            <div style="display: flex; flex-direction: column; align-items: center; margin: 6px 0 20px 0;">
                <div style="width: 2px; height: 16px; background: #333333;"></div>
                <div style="background-color: #181818; color: #E50914; border: 1px solid #333333; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 700;">↓</div>
                <div style="width: 2px; height: 16px; background: #333333;"></div>
            </div>
            """
    
    html_diagrama += "</div>"

    html_recom = """
    <div style="background-color: #181818; border: 1px solid #282828; border-left: 4px solid #E50914; border-radius: 8px; padding: 22px; margin-top: 24px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 18px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #E50914; padding-bottom: 10px; display: inline-block;">💡 5. Recomendaciones del Chef</h3>
        <ul style='margin: 16px 0 0 0; padding-left: 20px; color: #B3B3B3; font-size: 14px; line-height: 1.8; font-family: 'Inter', sans-serif;'>
    """
    for rec in recomendaciones:
        html_recom += f"<li>{rec}</li>"
    html_recom += "</ul></div>"

    vinos_lista = maridaje.get('vinos', [])
    cervezas_lista = maridaje.get('cervezas', [])
    
    vinos_html = "".join([f"<li style='margin-bottom: 6px;'>{v}</li>" for v in vinos_lista]) if vinos_lista else "<li>Sin propuestas de vino disponibles.</li>"
    cervezas_html = "".join([f"<li style='margin-bottom: 6px;'>{c}</li>" for c in cervezas_lista]) if cervezas_lista else "<li>Sin propuestas de cerveza disponibles.</li>"

    html_maridaje = f"""
    <div style="background-color: #181818; border: 1px solid #282828; border-left: 4px solid #E50914; border-radius: 8px; padding: 22px; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 18px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #E50914; padding-bottom: 10px; display: inline-block;">🍷 6. Sommelier Experto (D.O. Castilla-La Mancha y España)</h3>
        <div style="margin-top: 16px; color: #B3B3B3; font-size: 14px; line-height: 1.7; font-family: 'Inter', sans-serif;">
            <p style="margin-bottom: 8px; color: #E5E5E5;"><b>🍇 Propuestas de Vinos (Mínimo 2, con prioridad en Castilla-La Mancha):</b></p>
            <ul style="margin: 0 0 16px 0; padding-left: 20px;">{vinos_html}</ul>
            <p style="margin-bottom: 8px; color: #E5E5E5;"><b>🍺 Propuestas de Cervezas (Mínimo 2, artesanas y nacionales):</b></p>
            <ul style="margin: 0; padding-left: 20px;">{cervezas_html}</ul>
        </div>
    </div>
    """

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #E50914; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span style="color: #B3B3B3;">{origen_receta}</span>'
    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;900&family=Inter:wght@400;500&display=swap" rel="stylesheet">
        <style>
            body {{ background-color: #141414; color: #E5E5E5; font-family: 'Inter', sans-serif; padding: 16px; margin: 0; }}
            .container-hub {{ max-width: 900px; margin: auto; }}
            .widget-box {{ background-color: #181818; border: 1px solid #282828; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }}
            .btn-control {{ background-color: #E50914; color: white; border: none; padding: 10px 22px; font-size: 13px; font-weight: 700; border-radius: 4px; cursor: pointer; margin: 4px; font-family: 'Montserrat', sans-serif; text-transform: uppercase; letter-spacing: 1px; }}
            .btn-stop {{ background-color: #282828; color: #E5E5E5; }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}
            <div class="widget-box">
                <p style="color: #B3B3B3; font-size: 13px; margin: 0 0 12px 0; font-weight: 600; font-family: 'Montserrat', sans-serif;">👨‍🍳💬 Asistente de Voz de Cocina</p>
                <button id="btnVoz" class="btn-control" onclick="reproducir(this)">🎧 Asistente Manos Libres</button>
                <button class="btn-control btn-stop" onclick="detener()">🔇 Oído Cocina (Silenciar)</button>
            </div>
            {html_ing}
            {html_utensilios}
            {html_prev}
            {html_diagrama}
            {html_recom}
            {html_maridaje}
            <div style="text-align: center; color: #737373; font-size: 13px; margin-top: 35px; border-top: 1px solid #282828; padding-top: 20px;">
                🎬 <b>FaceFoodChef.com V3.1</b> | Fuente: {origen_html}
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
                btn.innerText = "🔊 Reproduciendo Guía...";
                currentUtterance.onend = () => btn.innerText = "🎧 Asistente Manos Libres";
                currentUtterance.onerror = () => btn.innerText = "🎧 Asistente Manos Libres";
                window.speechSynthesis.speak(currentUtterance);
            }}

            function detener() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const btn = document.getElementById('btnVoz');
                    if (btn) btn.innerText = "🎧 Asistente Manos Libres";
                }}
            }}

            function iniciarTemporizador(elementId, minutos) {{
                const elemento = document.getElementById(elementId);
                let segundosRestantes = minutos * 60;
                if (window[elementId + "_interval"]) clearInterval(window[elementId + "_interval"]);

                window[elementId + "_interval"] = setInterval(() => {{
                    if (segundosRestantes <= 0) {{
                        clearInterval(window[elementId + "_interval"]);
                        elemento.innerText = "¡TIEMPO CUMPLIDO! ⏰";
                        sonarAlertaPolifonica();
                    }} else {{
                        segundosRestantes--;
                        const m = Math.floor(segundosRestantes / 60);
                        const s = segundosRestantes % 60;
                        elemento.innerText = m + "m " + (s < 10 ? "0" : "") + s + "s";
                    }}
                }}, 1000);
            }}

            function sonarAlertaPolifonica() {{
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const frecuencias = [523.25, 659.25, 783.99, 1046.50, 1318.51];
                
                frecuencias.forEach((freq, index) => {{
                    setTimeout(() => {{
                        if (audioCtx.state === 'suspended') {{
                            audioCtx.resume();
                        }}
                        const osc = audioCtx.createOscillator();
                        const gain = audioCtx.createGain();
                        osc.type = 'triangle';
                        osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
                        gain.gain.setValueAtTime(0.25, audioCtx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.35);
                        osc.connect(gain);
                        gain.connect(audioCtx.destination);
                        osc.start();
                        osc.stop(audioCtx.currentTime + 0.35);
                    }}, index * 200);
                }});
            }}
        </script>
    </body>
    </html>
    """

procesar_accion = False
contenido_ia = None

if url_origen_detectada:
    try:
        with st.spinner("🌐 Obteniendo datos de la URL..."):
            contenido_ia, url_origen_detectada = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error(f"{e}")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif archivo_multimodal:
    procesar_accion = True

if st.button("🎬 GENERAR DIAGRAMA Y SOMMELIER V3.1"):
    api_key_activa = API_KEY_INPUT.strip()
    
    if not api_key_activa:
        st.error("⚠️ Por favor, introduce una clave de API de Google Gemini en el panel lateral izquierdo.")
    elif not procesar_accion:
        st.warning("⚠️ Introduce una URL, un texto o adjunta un archivo antes de continuar.")
    else:
        try:
            client = genai.Client(api_key=api_key_activa)
            
            prompt_sistema = f"""
            Eres un maestro chef, sumiller experto de Castilla-La Mancha y programador de flujos culinarios. 
            Transforma la receta aportada en un esquema estructurado JSON avanzado bajo los siguientes criterios obligatorios:

            ¡IMPORTANTE! El usuario requiere que la receta sea exactamente para {comensales_objetivo} COMENSALES. 
            Ajusta matemáticamente las cantidades para {comensales_objetivo} raciones.

            REGLAS ESTRICTAS DE FORMATO Y UNIDADES:
            1. UNIDADES DE MEDIDA: Expresar abreviadas siempre que sea posible (g, kg, ml, l, ºC, cm, min). La palabra "cucharada" y "cucharadita" deben mantenerse SIEMPRE escritas completas. Prohibido "al gusto".
            2. MODULARIZACIÓN: 
               - Proporciona una lista separada de "utensilios_menaje" (ej: Cuchillo de cocinero, cazuela de acero inoxidable, batidor de varillas, etc.).
               - Proporciona una lista separada de "pasos_previos" para la preparación previa / mise en place.
            3. SOMMELIER (CASTILLA-LA MANCHA Y ESPAÑA): En la sección 'maridaje', debes proporcionar obligatoriamente:
               - Al menos 2 propuestas de VINO, priorizando Denominaciones de Origen de Castilla-La Mancha.
               - Al menos 2 propuestas de CERVEZA, priorizando artesanales y nacionales.
            4. Devuelve EXCLUSIVAMENTE un JSON válido sin marcas ni textos adicionales fuera del JSON.

            JSON Schema esperado:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["400 g de harina de trigo", "10 g de sal fina"],
              "utensilios_menaje": ["Cuchillo de cocinero", "Cazuela de acero inoxidable", "Espátula de silicona"],
              "pasos_previos": ["Lavar y desinfectar los ingredientes frescos...", "Cortar en brunoise fina..."],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "Paso 1 detallado", "utensilios": ["Cazuela de acero inoxidable"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "100 ºC"}},
                {{
                  "tipo": "paralelo",
                  "ramas": [
                    {{"nombre": "Sartén 1", "accion": "Sofreír...", "utensilios": ["Sartén antiadherente"], "tiempo": "10 min", "duracion_minutos": 10, "temperatura": "90 ºC"}},
                    {{"nombre": "Olla 2", "accion": "Cocer...", "utensilios": ["Olla"], "tiempo": "8 min", "duracion_minutos": 8, "temperatura": "100 ºC"}}
                  ]
                }},
                {{"tipo": "convergencia", "accion": "Unir mezclas", "utensilios": ["Bol grande"], "tiempo": "2 min", "duracion_minutos": 2, "temperatura": "80 ºC"}}
              ],
              "recomendaciones": ["Tip técnico 1"],
              "texto_voz": "Texto descriptivo completo y guiado de la receta",
              "maridaje": {{
                "vinos": [
                  "1. Vino tinto D.O. La Mancha...",
                  "2. Vino blanco D.O. Rueda..."
                ],
                "cervezas": [
                  "1. Cerveza artesana castellano-manchega...",
                  "2. Cerveza tostada española..."
                ]
              }}
            }}
            """

            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append(f"Analiza el archivo adjunto para extraer la receta, escalar a {comensales_objetivo} comensales con separación modular.")
            else:
                contents_payload.append(f"Receta:\n{contenido_ia}")

            modelos_a_probar = [modelo_seleccionado, "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash"]
            modelos_a_probar = list(dict.fromkeys(modelos_a_probar))
            
            response = None
            exito = False
            
            with st.spinner("⚙️ Procesando diagrama V3.1 (Optimizando conexión con IA)..."):
                for mod in modelos_a_probar:
                    intentos = 3
                    for intento in range(intentos):
                        try:
                            response = client.models.generate_content(
                                model=mod,
                                contents=contents_payload,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    temperature=0.1
                                ),
                            )
                            if response and response.text:
                                exito = True
                                break
                        except Exception as api_err:
                            err_str = str(api_err)
                            if "503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str:
                                if intento < intentos - 1:
                                    tiempo_espera = (intento + 1) * 3
                                    time.sleep(tiempo_espera)
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
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto aportado por el usuario")

                html_final = generar_html_dashboard(
                    datos.get("nombre_receta", "Receta Culinaria Pro V3.1"),
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
                
                st.success("¡Diagrama de producción generado con éxito!")
                components.html(html_final, height=1100, scrolling=True)
            else:
                st.error("No se pudo obtener una respuesta válida de los modelos de Gemini tras varios intentos.")
                
        except APIError as e:
            st.error(f"Error de la API de Gemini: {e}")
        except Exception as e:
            st.error(f"Se ha producido un error inesperado: {e}")
