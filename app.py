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

# Configuración de página
st.set_page_config(
    page_title="FaceFoodChef.com - Motor de Diagramas Culinarios Pro V4", 
    layout="wide", 
    page_icon="🍳"
)

# CSS Global de Streamlit
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;900&family=Inter:wght@400;500;700&display=swap');

    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #0A0A0A !important;
        color: #E5E5E5 !important;
        font-family: 'Inter', sans-serif !important;
    }
    header, footer { visibility: hidden; }
    
    .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #121212 !important;
        color: #FFFFFF !important;
        border: 1px solid #282828 !important;
        border-radius: 6px !important;
        font-size: 16px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #00E5FF !important;
        box-shadow: 0 0 10px rgba(0, 229, 255, 0.2) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #0088FF 100%) !important;
        color: #000000 !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 16px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 14px 30px !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 1px;
        transition: all 0.3s ease !important;
    }
    .stButton > button:hover {
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.6) !important;
        transform: translateY(-1px);
    }

    .streamlit-expanderHeader {
        background-color: #121212 !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
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

# Panel Lateral
st.sidebar.header("⚙️ Panel de Control V4")

API_KEY_INPUT = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google Gemini."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
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
### 🎨 Código de Bordes (Diagrama):
- 🟢 **Borde Verde Neón (#00FF66):** Ingredientes / Entradas
- 🔵 **Borde Azul Brillante (#00E5FF):** Acciones / Mezclas (Procesado)
- 🟡 **Borde Amarillo (#FFB300):** Tiempos / Temperaturas / Puntos de Control
- 🔴 **Borde Rojo (#FF3366):** Alertas / Puntos Críticos
- 🟡 **Borde Dorado (#FFD700):** Resultado / Plato Final
""")

# Encabezado
st.markdown("<h1 style='text-align: center; color: #FFFFFF; font-family: Montserrat, sans-serif; font-weight: 900; letter-spacing: 2px; margin-bottom: 0;'>FACEFOODCHEF <span style='font-size: 14px; background: #00E5FF; color: #000; padding: 4px 10px; border-radius: 4px; vertical-align: middle; letter-spacing: 1px;'>PRO V4</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #B3B3B3; font-size: 15px; margin-bottom: 30px; font-family: Inter, sans-serif;'>Generador de Diagramas de Flujo Culinarios con Código de Colores</p>", unsafe_allow_html=True)

# Sección de entrada
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
    # Definición de Estilos por Categoría (Requisito de bordes y fondos)
    COLOR_INGREDIENTE = "#00FF66"  # Verde Neón
    COLOR_ACCION = "#00E5FF"       # Azul Brillante
    COLOR_CONTROL = "#FFB300"      # Amarillo / Naranja
    COLOR_ALERTA = "#FF3366"       # Rojo
    COLOR_PLATO_FINAL = "#FFD700"  # Dorado

    html_header = f"""
    <div style="background: #000000; border-radius: 8px; padding: 24px; text-align: center; margin-bottom: 24px; border: 2px solid {COLOR_PLATO_FINAL}; box-shadow: 0 0 15px rgba(255, 215, 0, 0.2);">
        <span style="font-size: 11px; font-weight: 700; color: #000; text-transform: uppercase; letter-spacing: 2px; background: {COLOR_PLATO_FINAL}; padding: 4px 12px; border-radius: 3px; display: inline-block; font-family: 'Montserrat', sans-serif;">Flujo de Producción Culinario</span>
        <h1 style="color: #FFFFFF; font-size: 26px; margin: 12px 0 6px 0; font-weight: 900; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">{nombre_receta}</h1>
        <p style="color: #B3B3B3; font-size: 13px; margin: 0; font-family: 'Inter', sans-serif;">Receta adaptada para <b>{comensales} personas</b></p>
    </div>
    """

    # Bloque 1: Ingredientes (Borde Verde Neón #00FF66, Fondo Negro)
    html_ing = f"""
    <div style="background-color: #000000; border: 2px solid {COLOR_INGREDIENTE}; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(0, 255, 102, 0.1);">
        <h3 style="color: {COLOR_INGREDIENTE}; margin-top: 0; font-size: 16px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #222; padding-bottom: 8px;">🛒 1. Ingredientes - Entradas ({comensales} pax)</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background-color: #111111; color: #FFFFFF; padding: 8px 14px; border-radius: 4px; font-size: 13px; border: 1px solid #222; font-family: 'Inter', sans-serif;'>{ing}</span>"
    html_ing += "</div></div>"

    # Bloque 2: Utensilios y Menaje
    html_utensilios = f"""
    <div style="background-color: #000000; border: 1px solid #333333; border-radius: 8px; padding: 20px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; padding-bottom: 8px; margin-bottom: 14px;">
            <h3 style="color: #FFFFFF; margin: 0; font-size: 16px; font-weight: 700; font-family: 'Montserrat', sans-serif;">🛠️ 2. Utensilios y Menaje</h3>
            <a href="https://www.facefoodchef.com/tienda-menaje" target="_blank" style="background-color: #1A1A1A; color: #00E5FF; border: 1px solid #00E5FF; padding: 6px 14px; border-radius: 4px; text-decoration: none; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">🛒 Tienda de Menaje</a>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
    """
    for ut in utensilios_menaje:
        html_utensilios += f"<span style='background-color: #111111; color: #CCCCCC; padding: 6px 12px; border-radius: 4px; font-size: 13px; border: 1px solid #222;'>{ut}</span>"
    html_utensilios += "</div></div>"

    # Bloque 3: Preparación Previa (Mise en place)
    html_prev = """
    <div style="background-color: #000000; border: 1px solid #333333; border-radius: 8px; padding: 20px; margin-bottom: 24px;">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 16px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #222; padding-bottom: 8px;">🔪 3. Preparación Previa (Mise en Place)</h3>
        <ul style='margin: 14px 0 0 0; padding-left: 20px; color: #CCCCCC; font-size: 14px; line-height: 1.7;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li>{prep}</li>"
    html_prev += "</ul></div>"

    # Bloque 4: Diagrama de Proceso Dinámico
    html_diagrama = """
    <div style="font-family: 'Inter', sans-serif;">
        <h3 style="color: #FFFFFF; font-size: 18px; font-weight: 700; margin-bottom: 20px; font-family: 'Montserrat', sans-serif; border-bottom: 2px solid #00E5FF; padding-bottom: 8px; display: inline-block;">4. Diagrama de Ejecución y Flujo</h3>
    """

    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        es_critico = bloque.get("es_critico", False)
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "N/A"

        # Determinación de Color según la especificación del usuario
        if es_critico:
            borde_color = COLOR_ALERTA  # #FF3366
        elif tipo == "convergencia":
            borde_color = COLOR_ACCION  # #00E5FF
        else:
            borde_color = COLOR_ACCION  # #00E5FF por defecto para acciones

        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += '<div style="display: flex; gap: 14px; margin-bottom: 16px; flex-wrap: wrap;">'
            for idx, rama in enumerate(ramas):
                nombre_rama = rama.get("nombre", f"Subproceso {idx+1}").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                utensilios_rama = ", ".join(rama.get("utensilios", []))
                dur_rama = rama.get("duracion_minutos", 5)
                timer_id = f"timer_par_{i}_{idx}"
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 280px; background-color: #000000; border: 2px solid {COLOR_ACCION}; border-radius: 6px; padding: 18px; box-shadow: 0 0 10px rgba(0, 229, 255, 0.1);">
                    <div style="margin-bottom: 10px;"><span style="font-size: 10px; font-weight: 700; color: #000000; background-color: {COLOR_ACCION}; padding: 3px 8px; border-radius: 2px; text-transform: uppercase; font-family: 'Montserrat', sans-serif;">⚙️ ACCIÓN EN PARALELO: {nombre_rama}</span></div>
                    <div style="font-size: 14px; font-weight: 500; color: #FFFFFF; margin: 10px 0; line-height: 1.5;">{accion}</div>
                    <div style="font-size: 12px; color: #888888; margin-bottom: 12px;">🛠️ <b>Utensilios:</b> {utensilios_rama}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: #0A0A0A; padding: 8px 12px; border: 1px solid {COLOR_CONTROL}; border-radius: 4px;">
                        <div style="font-size: 12px; color: {COLOR_CONTROL}; font-weight: bold;">⏱️ <span id="{timer_id}">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" style="background-color: {COLOR_CONTROL}; color: #000; border: none; padding: 4px 10px; border-radius: 3px; cursor: pointer; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            timer_id = f"timer_seq_{i}"
            etiqueta = "UNIÓN / CONVERGENCIA" if tipo == "convergencia" else f"PASO {i+1}"
            
            html_diagrama += f"""
            <div style="background-color: #000000; border: 2px solid {borde_color}; border-radius: 6px; padding: 18px; margin-bottom: 16px; box-shadow: 0 0 10px rgba(0,0,0,0.8);">
                <div style="margin-bottom: 10px;">
                    <span style="font-size: 10px; font-weight: 700; color: #000000; background-color: {borde_color}; padding: 3px 8px; border-radius: 2px; text-transform: uppercase; font-family: 'Montserrat', sans-serif;">{etiqueta}</span>
                </div>
                <div style="font-size: 14px; font-weight: 500; color: #FFFFFF; margin: 10px 0; line-height: 1.5;">{bloque.get('accion')}</div>
                <div style="font-size: 12px; color: #888888; margin-bottom: 12px;">🛠️ <b>Utensilios:</b> {utensilios_str}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: #0A0A0A; padding: 8px 12px; border: 1px solid {COLOR_CONTROL}; border-radius: 4px;">
                    <div style="font-size: 12px; color: {COLOR_CONTROL}; font-weight: bold;">⏱️ <span id="{timer_id}">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" style="background-color: {COLOR_CONTROL}; color: #000; border: none; padding: 4px 10px; border-radius: 3px; cursor: pointer; font-size: 11px; font-weight: 700; font-family: 'Montserrat', sans-serif; text-transform: uppercase;">⏳ Iniciar</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += f"""
            <div style="text-align: center; margin: 4px 0 12px 0;">
                <span style="color: {COLOR_ACCION}; font-size: 18px; font-weight: bold;">↓</span>
            </div>
            """

    # Bloque Final: Plato Terminado (Borde Dorado Resplandeciente #FFD700)
    html_diagrama += f"""
    <div style="text-align: center; margin: 4px 0 12px 0;">
        <span style="color: {COLOR_PLATO_FINAL}; font-size: 18px; font-weight: bold;">↓</span>
    </div>
    <div style="background-color: #000000; border: 2px solid {COLOR_PLATO_FINAL}; border-radius: 8px; padding: 20px; text-align: center; margin-top: 10px; box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);">
        <span style="font-size: 11px; font-weight: 700; color: #000; background-color: {COLOR_PLATO_FINAL}; padding: 4px 10px; border-radius: 3px; font-family: 'Montserrat', sans-serif;">RESULTADO FINAL</span>
        <h3 style="color: {COLOR_PLATO_FINAL}; margin: 10px 0 0 0; font-weight: 900; font-family: 'Montserrat', sans-serif;">🍽️ PLATO LISTO PARA SERVIR</h3>
    </div>
    </div>
    """

    # Alertas y Recomendaciones (Borde Rojo #FF3366)
    html_recom = f"""
    <div style="background-color: #000000; border: 2px solid {COLOR_ALERTA}; border-radius: 8px; padding: 20px; margin-top: 24px; margin-bottom: 20px; box-shadow: 0 0 10px rgba(255, 51, 102, 0.1);">
        <h3 style="color: {COLOR_ALERTA}; margin-top: 0; font-size: 16px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #222; padding-bottom: 8px;">🚨 5. Puntos Críticos y Alertas del Chef</h3>
        <ul style='margin: 14px 0 0 0; padding-left: 20px; color: #CCCCCC; font-size: 14px; line-height: 1.7;'>
    """
    for rec in recomendaciones:
        html_recom += f"<li>{rec}</li>"
    html_recom += "</ul></div>"

    # Sommelier
    vinos_lista = maridaje.get('vinos', [])
    cervezas_lista = maridaje.get('cervezas', [])
    vinos_html = "".join([f"<li>{v}</li>" for v in vinos_lista]) if vinos_lista else "<li>Sin propuestas disponibles.</li>"
    cervezas_html = "".join([f"<li>{c}</li>" for c in cervezas_lista]) if cervezas_lista else "<li>Sin propuestas disponibles.</li>"

    html_maridaje = f"""
    <div style="background-color: #000000; border: 1px solid #333333; border-radius: 8px; padding: 20px; margin-top: 20px; margin-bottom: 20px;">
        <h3 style="color: #FFFFFF; margin-top: 0; font-size: 16px; font-weight: 700; font-family: 'Montserrat', sans-serif; border-bottom: 1px solid #222; padding-bottom: 8px;">🍷 6. Maridaje y Recomendaciones</h3>
        <div style="margin-top: 14px; color: #CCCCCC; font-size: 14px; line-height: 1.6;">
            <p style="margin-bottom: 6px; color: #FFFFFF;"><b>🍇 Vinos (D.O. Castilla-La Mancha / España):</b></p>
            <ul style="margin: 0 0 14px 0; padding-left: 20px;">{vinos_html}</ul>
            <p style="margin-bottom: 6px; color: #FFFFFF;"><b>🍺 Cervezas Artesanales:</b></p>
            <ul style="margin: 0; padding-left: 20px;">{cervezas_html}</ul>
        </div>
    </div>
    """

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #00E5FF; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span style="color: #888888;">{origen_receta}</span>'
    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;700;900&family=Inter:wght@400;500&display=swap" rel="stylesheet">
        <style>
            body {{ background-color: #0A0A0A; color: #E5E5E5; font-family: 'Inter', sans-serif; padding: 16px; margin: 0; }}
            .container-hub {{ max-width: 900px; margin: auto; }}
            .widget-box {{ background-color: #000000; border: 1px solid #222; border-radius: 8px; padding: 18px; text-align: center; margin-bottom: 20px; }}
            .btn-control {{ background: #00E5FF; color: #000; border: none; padding: 8px 18px; font-size: 12px; font-weight: 700; border-radius: 4px; cursor: pointer; margin: 4px; font-family: 'Montserrat', sans-serif; text-transform: uppercase; }}
            .btn-stop {{ background: #222; color: #FFF; }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}
            <div class="widget-box">
                <p style="color: #888; font-size: 12px; margin: 0 0 10px 0; font-weight: 700; font-family: 'Montserrat', sans-serif;">👨‍🍳 ASISTENTE AUDITIVO</p>
                <button id="btnVoz" class="btn-control" onclick="reproducir(this)">🎧 Escuchar Pasos de la Receta</button>
                <button class="btn-control btn-stop" onclick="detener()">Silenciar</button>
            </div>
            {html_ing}
            {html_utensilios}
            {html_prev}
            {html_diagrama}
            {html_recom}
            {html_maridaje}
            <div style="text-align: center; color: #555555; font-size: 12px; margin-top: 30px; border-top: 1px solid #222; padding-top: 16px;">
                FaceFoodChef.com V4 | Origen: {origen_html}
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
                currentUtterance.onend = () => btn.innerText = "🎧 Escuchar Pasos de la Receta";
                currentUtterance.onerror = () => btn.innerText = "🎧 Escuchar Pasos de la Receta";
                window.speechSynthesis.speak(currentUtterance);
            }}

            function detener() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const btn = document.getElementById('btnVoz');
                    if (btn) btn.innerText = "🎧 Escuchar Pasos de la Receta";
                }}
            }}

            function iniciarTemporizador(elementId, minutos) {{
                const elemento = document.getElementById(elementId);
                let segundosRestantes = minutos * 60;
                if (window[elementId + "_interval"]) clearInterval(window[elementId + "_interval"]);

                window[elementId + "_interval"] = setInterval(() => {{
                    if (segundosRestantes <= 0) {{
                        clearInterval(window[elementId + "_interval"]);
                        elemento.innerText = "¡TIEMPO FINALIZADO!";
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
        with st.spinner("🌐 Extrayendo información de la URL..."):
            contenido_ia, url_origen_detectada = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error(f"{e}")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif archivo_multimodal:
    procesar_accion = True

if st.button("🚀 GENERAR DIAGRAMA DE BLOQUES (V4)"):
    api_key_activa = API_KEY_INPUT.strip()
    
    if not api_key_activa:
        st.error("⚠️ Introduce tu clave de API de Google Gemini.")
    elif not procesar_accion:
        st.warning("⚠️ Debes introducir un texto, URL o adjuntar un archivo.")
    else:
        try:
            client = genai.Client(api_key=api_key_activa)
            
            prompt_sistema = f"""
            Eres un ingeniero de procesos culinarios y experto en cocina profesional. 
            Convierte la receta facilitada en un objeto JSON estructurado diseñado para renderizar un diagrama de flujo.

            Debes recalcular y escalar todas las cantidades exactamente para {comensales_objetivo} COMENSALES.

            REGLAS ESTRUCTURALES Y JSON:
            1. UNIDADES: Abreviadas (g, kg, ml, l, ºC, min). Cucharada y cucharadita se escriben completas. Sin expresiones vagamente especificadas como "al gusto".
            2. UTENSILIOS Y MISE EN PLACE:
               - Separa la lista de "utensilios_menaje".
               - Separa la lista de "pasos_previos" (limpieza, cortes preliminares).
            3. BLOQUES DE PROCESO:
               - "tipo": puede ser "secuencial", "paralelo" o "convergencia".
               - "es_critico": booleano (true si el paso requiere atención especial de seguridad, punto de cocción o control térmico sensible).
            4. SOMMELIER: Maridaje de al menos 2 vinos (prioridad D.O. Castilla-La Mancha) y 2 cervezas.
            5. Devuelve ÚNICAMENTE la estructura JSON.

            JSON Schema:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["400 g de harina"],
              "utensilios_menaje": ["Cuchillo", "Sartén"],
              "pasos_previos": ["Cortar cebolla en juliana"],
              "bloques_proceso": [
                {{"tipo": "secuencial", "es_critico": false, "accion": "Descripción del paso", "utensilios": ["Sartén"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "180 ºC"}},
                {{
                  "tipo": "paralelo",
                  "es_critico": false,
                  "ramas": [
                    {{"nombre": "Salsa", "accion": "Reducir el vino", "utensilios": ["Cazo"], "tiempo": "10 min", "duracion_minutos": 10, "temperatura": "90 ºC"}}
                  ]
                }}
              ],
              "recomendaciones": ["Punto crítico: no quemar el ajo"],
              "texto_voz": "Resumen locutado",
              "maridaje": {{
                "vinos": ["1. Vino Tinto D.O. La Mancha"],
                "cervezas": ["1. Cerveza artesanal"]
              }}
            }}
            """

            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append(f"Procesa el documento adjunto escalado a {comensales_objetivo} comensales.")
            else:
                contents_payload.append(f"Receta a procesar:\n{contenido_ia}")

            modelos_a_probar = [modelo_seleccionado, "gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash"]
            modelos_a_probar = list(dict.fromkeys(modelos_a_probar))
            
            response = None
            exito = False
            
            with st.spinner("⚡ Analizando secuencia culinaria y estructurando diagrama..."):
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
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto del usuario")

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
                
                st.success("¡Diagrama generado correctamente!")
                components.html(html_final, height=1200, scrolling=True)
            else:
                st.error("No se pudo obtener una respuesta válida del modelo Gemini.")
                
        except APIError as e:
            st.error(f"Error de la API de Gemini: {e}")
        except Exception as e:
            st.error(f"Error inesperado al procesar los datos: {e}")
