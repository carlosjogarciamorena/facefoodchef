import os
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

# Cargar variables de entorno locales (.env)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# ESTILOS VISUALES - FONDO GRIS METÁLICO PROFESIONAL
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

    .stDownloadButton > button {
        background-color: #36393F !important;
        color: #ffffff !important;
        border: 1px solid #EF4444 !important;
        font-weight: 600 !important;
        border-radius: 6px !important;
        width: 100%;
        padding: 10px;
    }
    .stDownloadButton > button:hover {
        background-color: #EF4444 !important;
        color: #ffffff !important;
    }

    .streamlit-expanderHeader {
        background-color: #36393F !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #4F545C !important;
    }
    </style>
""", unsafe_allow_html=True)

# Autenticación API Key
API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif os.getenv("GEMINI_API_KEY"):
    API_KEY = os.getenv("GEMINI_API_KEY")

st.sidebar.header("⚙️ Panel de Control")

if API_KEY:
    st.sidebar.success("🔑 API Key vinculada.")
else:
    API_KEY = st.sidebar.text_input(
        "API Key de Google Gemini:", 
        type="password", 
        help="Introduce la clave manualmente o configúrala en secretos."
    )

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash"],
    index=0
)

# NUEVO: Selector de comensales para escalar la receta
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
### 🎬 FaceFoodChef.com
- **Métricas:** Recálculo para comensales (g, ml, ud)
- **Estructura:** Bloques unificados con temporizadores
- **Maridaje:** Sugerencia automatizada (Vino/Cerveza)
""")

st.markdown("<h1 style='text-align: center; color: #EF4444; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>FACEFOODCHEF <span style='font-size: 16px; background: #36393F; color: #fff; padding: 4px 10px; border-radius: 4px; vertical-align: middle; border: 1px solid #4F545C;'>PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; font-size: 15px; margin-bottom: 30px;'>Diagramas de cocina escalables + Sommelier Virtual</p>", unsafe_allow_html=True)

# Entrada de Datos
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

def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, pasos_previos, bloques_proceso, recomendaciones, texto_voz, maridaje, comensales):
    
    html_header = f"""
    <div style="background: linear-gradient(180deg, #36393F 0%, #2F3136 100%); border-radius: 8px; padding: 30px; text-align: center; margin-bottom: 24px; border-left: 6px solid #EF4444; border: 1px solid #4F545C; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <span style="font-size: 11px; font-weight: 800; color: #FFFFFF; text-transform: uppercase; letter-spacing: 2px; background: #EF4444; padding: 6px 14px; border-radius: 4px; display: inline-block;">Diagrama de Producción Culinaria</span>
        <h1 style="color: #ffffff; font-size: 30px; margin: 16px 0 8px 0; font-weight: 800;">{nombre_receta}</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin: 0;">Calculado y escalado para <b>{comensales} comensales</b>.</p>
    </div>
    """

    html_ing = f"""
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-radius: 8px; padding: 22px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <h3 style="color: #EF4444; margin-top: 0; font-size: 18px; font-weight: 700;">🛒 1. Ingredientes ({comensales} pax)</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background-color: #2F3136; color: #E2E8F0; padding: 8px 16px; border-radius: 20px; font-size: 13px; border: 1px solid #5C626B; font-weight: 500;'> {ing}</span>"
    html_ing += "</div></div>"

    html_prev = """
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-radius: 8px; padding: 22px; margin-bottom: 24px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <h3 style="color: #FBBF24; margin-top: 0; font-size: 18px; font-weight: 700;">🔪 2. Mise en Place (Preparación Previa)</h3>
        <ul style='margin: 12px 0 0 0; padding-left: 20px; color: #CBD5E0; font-size: 14px; line-height: 1.8;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;">
        <h3 style="color: #ffffff; font-size: 20px; font-weight: 800; margin-bottom: 22px;">3. Diagrama de Ejecución</h3>
    """
    
    BG_BLOQUE = "#36393F"
    BORDER_BLOQUE = "#4F545C"
    
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "Sin utensilios específicos"
        
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
                
                color_franja_paralelo = "#F59E0B"
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 280px; background-color: {BG_BLOQUE}; border: 1px solid {BORDER_BLOQUE}; border-left: 6px solid {color_franja_paralelo}; border-radius: 8px; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                    <div style="margin-bottom: 12px;"><span style="font-size: 11px; font-weight: 800; color: #FFFFFF; background-color: {color_franja_paralelo}; padding: 5px 12px; border-radius: 4px; display: inline-block; text-transform: uppercase;">⚙️ PARALELO: {nombre_rama}</span></div>
                    <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin: 12px 0;">{accion}</div>
                    <div style="font-size: 12px; color: #A0AEC0; margin-bottom: 14px; background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 4px;">🛠️ <b>Utensilios:</b> {utensilios_rama}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.4); padding: 10px 14px; border-radius: 6px;">
                        <div style="font-size: 13px; color: #ffffff;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #FBBF24;">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" style="background-color: #EF4444; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 700;">⏳ Iniciar</button>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            es_convergencia = tipo == "convergencia"
            left_border = "#10B981" if es_convergencia else "#EF4444"
            badge_bg = "#10B981" if es_convergencia else "#EF4444"
            etiqueta = "CONVERGENCIA / UNIÓN" if es_convergencia else f"PASO {i+1}"
            timer_id = f"timer_seq_{i}"

            html_diagrama += f"""
            <div style="background-color: {BG_BLOQUE}; border: 1px solid {BORDER_BLOQUE}; border-left: 6px solid {left_border}; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
                <div style="margin-bottom: 12px;"><span style="font-size: 11px; font-weight: 800; color: #FFFFFF; background-color: {badge_bg}; padding: 5px 12px; border-radius: 4px; display: inline-block; text-transform: uppercase;">{etiqueta}</span></div>
                <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin: 12px 0;">{bloque.get('accion')}</div>
                <div style="font-size: 12px; color: #A0AEC0; margin-bottom: 14px; background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 4px;">🛠️ <b>Utensilios:</b> {utensilios_str}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.4); padding: 10px 14px; border-radius: 6px;">
                    <div style="font-size: 13px; color: #ffffff;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #FBBF24;">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" style="background-color: #EF4444; color: white; border: none; padding: 6px 14px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 700;">⏳ Iniciar</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += """
            <div style="display: flex; flex-direction: column; align-items: center; margin: 6px 0 20px 0;">
                <div style="width: 4px; height: 16px; background: #ffffff; box-shadow: 0 0 8px rgba(255,255,255,0.6);"></div>
                <div style="background-color: #ffffff; color: #2C2F33; border: 2px solid #ffffff; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 900; box-shadow: 0 0 12px rgba(255,255,255,0.8);">👇</div>
                <div style="width: 4px; height: 16px; background: #ffffff; box-shadow: 0 0 8px rgba(255,255,255,0.6);"></div>
            </div>
            """
    
    html_diagrama += "</div>"

    html_recom = """
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 6px solid #FBBF24; border-radius: 8px; padding: 22px; margin-top: 24px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <h3 style="color: #FBBF24; margin-top: 0; font-size: 18px; font-weight: 700;">💡 4. Recomendaciones del Chef</h3>
        <ul style='margin: 12px 0 0 0; padding-left: 20px; color: #CBD5E0; font-size: 14px; line-height: 1.8;'>
    """
    for rec in recomendaciones:
        html_recom += f"<li>{rec}</li>"
    html_recom += "</ul></div>"

    html_maridaje = f"""
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 6px solid #9D4EDD; border-radius: 8px; padding: 22px; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <h3 style="color: #9D4EDD; margin-top: 0; font-size: 18px; font-weight: 700;">🍷 5. Sommelier Virtual (Maridaje)</h3>
        <div style="margin-top: 12px; color: #CBD5E0; font-size: 15px; line-height: 1.6;">
            <p style="margin-bottom: 12px;"><b>🍇 Sugerencia de Vino:</b><br>{maridaje.get('vino', 'Sin sugerencia disponible.')}</p>
            <p><b>🍺 Sugerencia de Cerveza:</b><br>{maridaje.get('cerveza', 'Sin sugerencia disponible.')}</p>
        </div>
    </div>
    """

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #EF4444; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span style="color: #A0AEC0;">{origen_receta}</span>'
    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ background-color: #2C2F33; color: #E2E8F0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; padding: 16px; margin: 0; }}
            .container-hub {{ max-width: 900px; margin: auto; }}
            .widget-box {{ background-color: #36393F; border: 1px solid #4F545C; border-radius: 8px; padding: 20px; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }}
            .btn-control {{ background-color: #EF4444; color: white; border: none; padding: 10px 22px; font-size: 13px; font-weight: 700; border-radius: 4px; cursor: pointer; margin: 4px; }}
            .btn-stop {{ background-color: #4F545C; color: #ffffff; }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}
            <div class="widget-box">
                <p style="color: #A0AEC0; font-size: 13px; margin: 0 0 12px 0; font-weight: 600;">👨‍🍳💬 Asistente de Voz de Cocina</p>
                <button id="btnVoz" class="btn-control" onclick="reproducir(this)">🎧 Asistente Manos Libres</button>
                <button class="btn-control btn-stop" onclick="detener()">🔇 Oído Cocina (Silenciar)</button>
            </div>
            {html_ing}
            {html_prev}
            {html_diagrama}
            {html_recom}
            {html_maridaje}
            <div style="text-align: center; color: #718096; font-size: 13px; margin-top: 35px; border-top: 1px solid #4F545C; padding-top: 20px;">
                🎬 <b>FaceFoodChef.com</b> | Fuente: {origen_html}
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
                        sonarAlerta();
                    }} else {{
                        segundosRestantes--;
                        const m = Math.floor(segundosRestantes / 60);
                        const s = segundosRestantes % 60;
                        elemento.innerText = `${{m}}m ${{s < 10 ? '0' : ''}}${{s}}s`;
                    }}
                }}, 1000);
            }}

            function sonarAlerta() {{
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.type = 'sine';
                oscillator.frequency.setValueAtTime(587.33, audioCtx.currentTime);
                gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.start();
                setTimeout(() => {{ oscillator.stop(); }}, 1200);
            }}
        </script>
    </body>
    </html>
    """

# Procesamiento principal
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

if st.button("🎬 GENERAR DIAGRAMA Y MARIDAJE"):
    if not API_KEY:
        st.error("⚠️ Es necesaria una API Key de Google Gemini para procesar la receta.")
    elif not procesar_accion:
        st.warning("⚠️ Introduce una URL, un texto o adjunta un archivo antes de continuar.")
    else:
        try:
            client = genai.Client(api_key=API_KEY)
            
            prompt_sistema = f"""
            Eres un experto en gastronomía, sommelier y programador de flujos de trabajo en cocina. 
            Transforma la siguiente receta en un esquema estructurado JSON para renderizar un diagrama de bloques técnico y recomendar un maridaje.

            ¡IMPORTANTE! El usuario requiere que la receta sea para {comensales_objetivo} COMENSALES. 
            Debes ajustar matemáticamente las cantidades de la lista de 'ingredientes' para que correspondan exactamente a {comensales_objetivo} raciones. Si la receta original no indica raciones, asume que era para 2 personas y escala desde ahí.

            REGLAS ESTRICTAS:
            1. Devuelve EXCLUSIVAMENTE un JSON válido sin marcas ni textos adicionales fuera del JSON.
            2. 'ingredientes': Unidades métricas exactas (g, ml, ud) recalculadas para {comensales_objetivo} comensales.
            3. 'temperatura': Grados Celsius (°C).
            4. 'origen_receta': Asigna exactamente ({url_origen_detectada if url_origen_detectada else 'Texto/Archivo aportado por el usuario'}).
            5. 'bloques_proceso': Asigna 'paralelo' para acciones simultáneas y 'convergencia' para las uniones.
            6. 'maridaje': Analiza el perfil organoléptico y sugiere un vino y una cerveza con justificación técnica.

            JSON Schema esperado:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["400 g de harina", "10 g de sal"],
              "pasos_previos": ["Mise en place..."],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "Paso 1", "utensilios": ["Olla"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "100°C"}},
                {{
                  "tipo": "paralelo",
                  "ramas": [
                    {{"nombre": "Sartén 1", "accion": "Sofreír...", "utensilios": ["Sartén"], "tiempo": "10 min", "duracion_minutos": 10, "temperatura": "90°C"}},
                    {{"nombre": "Olla 2", "accion": "Cocer...", "utensilios": ["Olla"], "tiempo": "8 min", "duracion_minutos": 8, "temperatura": "100°C"}}
                  ]
                }},
                {{"tipo": "convergencia", "accion": "Unir mezclas", "utensilios": ["Sartén grande"], "tiempo": "2 min", "duracion_minutos": 2, "temperatura": "80°C"}}
              ],
              "recomendaciones": ["Tip 1"],
              "texto_voz": "Texto descriptivo completo de la receta",
              "maridaje": {{
                "vino": "Recomendación de vino y justificación",
                "cerveza": "Recomendación de cerveza y justificación"
              }}
            }}
            """

            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append(f"Analiza el archivo adjunto para extraer la receta, escalar a {comensales_objetivo} comensales y recomendar maridaje.")
            else:
                contents_payload.append(f"Receta:\n{contenido_ia}")

            with st.spinner(f"⚙️ Procesando diagrama (Escalando a {comensales_objetivo} pax) y sommelier con {modelo_seleccionado}..."):
                response = client.models.generate_content(
                    model=modelo_seleccionado,
                    contents=contents_payload,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    ),
                )

            if response:
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
                    datos.get("nombre_receta", "Receta Culinaria Pro"),
                    origen_final,
                    datos.get("ingredientes", []),
                    datos.get("pasos_previos", []),
                    datos.get("bloques_proceso", []),
                    datos.get("recomendaciones", []),
                    datos.get("texto_voz", ""),
                    datos.get("maridaje", {}),
                    comensales_objetivo
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 Descargar Diagrama HTML Autónomo",
                    data=html_final,
                    file_name="diagrama_facefoodchef_pro.html",
                    mime="text/html"
                )
                
                components.html(html_final, height=1450, scrolling=True)
                
        except Exception as e:
            st.error(f"Error durante el procesamiento: {e}")
