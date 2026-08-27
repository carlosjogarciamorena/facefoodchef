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
    page_title="FaceFoodChef PRO - Diagramador Culinario", 
    layout="wide", 
    page_icon="👨‍🍳"
)

# Estilos visuales de Streamlit
st.markdown("""
    <style>
    .stApp {
        background-color: #0f172a !important;
        color: #f8fafc !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    header, footer { visibility: hidden; }
    
    .stTextArea textarea, .stTextInput input, .stSelectbox select {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 6px !important;
        font-size: 15px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #f59e0b !important;
        box-shadow: 0 0 8px rgba(245, 158, 11, 0.4) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 18px !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 16px 28px !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        width: 100%;
        min-height: 54px;
        cursor: pointer;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4) !important;
    }

    .stDownloadButton > button {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 2px solid #10b981 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        width: 100%;
        min-height: 48px;
    }
    .stDownloadButton > button:hover {
        background-color: #10b981 !important;
        color: #ffffff !important;
    }

    .streamlit-expanderHeader {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #334155 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Autenticación API Key
API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif os.getenv("GEMINI_API_KEY"):
    API_KEY = os.getenv("GEMINI_API_KEY")

st.sidebar.header("⚙️ Configuración")

if API_KEY:
    st.sidebar.success("🔑 API Key detectada correctamente.")
else:
    API_KEY = st.sidebar.text_input(
        "API Key de Google Gemini:", 
        type="password", 
        help="Introduce tu clave de Google AI Studio."
    )

# Selección de modelo de IA
modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
### 🍳 Guía Culinaria Ergonomizada
- **🟠 Naranja:** Cocción / Calor Directo
- **🟣 Violeta:** Tareas Simultáneas (Paralelas)
- **🟢 Verde:** Convergencia / Mezcla / Ensamble
- **🔵 Azul:** Mise en Place / Preparación
""")

st.markdown("<h1 style='text-align: center; color: #f59e0b; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>👨‍🍳 FACEFOODCHEF <span style='font-size: 16px; background: #1e293b; color: #10b981; padding: 4px 12px; border-radius: 6px; vertical-align: middle; border: 1px solid #10b981;'>KITCHEN PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 16px; margin-bottom: 30px;'>Generador de flujos ejecutables de cocina optimizados para lectura y control en tiempo real</p>", unsafe_allow_html=True)

# Entrada de Datos
st.subheader("📥 Receta de Origen")
entrada_principal = st.text_area(
    "Pega la URL de la receta o el texto completo:", 
    height=130, 
    placeholder="Ejemplo: https://www.directoalpaladar.com/receta...\nO pega aquí los ingredientes y pasos de tu receta..."
)

with st.expander("📁 Adjuntar archivo (PDF, Word, PPT o Imagen)"):
    archivo_subido = st.file_uploader("Subir archivo:", type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"])

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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url
        except Exception as e:
            raise Exception(f"No se pudo extraer información automáticamente de la URL: {e}")

def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, pasos_previos, bloques_proceso, recomendaciones, texto_voz):
    
    html_header = f"""
    <div class="header-card">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <span class="badge-tag">📊 Diagrama de Ejecución Culinaria</span>
            <button onclick="toggleModoCocina()" class="btn-theme-toggle" id="btnTheme">☀️ Modo Luz (Alto Contraste)</button>
        </div>
        <h1 class="main-title">{nombre_receta}</h1>
        <p class="sub-title">Flujo paso a paso con código semántico de colores y control de progreso</p>
    </div>
    """

    html_ing = """
    <div class="section-card card-mise">
        <h3 class="section-title text-blue">🛒 1. Ingredientes Exactos (Sistema Métrico)</h3>
        <div class="ingredients-grid">
    """
    for ing in ingredientes:
        html_ing += f"<div class='ing-chip'>⚖️ {ing}</div>"
    html_ing += "</div></div>"

    html_prev = """
    <div class="section-card card-mise">
        <h3 class="section-title text-blue">🔪 2. Mise en Place (Preparación Previa)</h3>
        <ul class="step-list">
    """
    for prep in pasos_previos:
        html_prev += f"<li>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div>
        <h3 class="section-title" style="font-size: 22px; margin-bottom: 20px;">⚡ 3. Diagrama de Producción Interactiva</h3>
    """
    
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "Sin utensilios específicos"
        card_id = f"block_card_{i}"
        
        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += f'<div id="{card_id}" class="block-card card-paralelo-container">'
            html_diagrama += f'''
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span class="badge-tag badge-paralelo">🔀 TAREAS PARALELAS (HACER SIMULTÁNEAMENTE)</span>
                <button onclick="toggleCompletado('{card_id}')" class="btn-done">✓ Marcar completado</button>
            </div>
            <div class="parallel-grid">
            '''
            for idx, rama in enumerate(ramas):
                nombre_rama = rama.get("nombre", f"Tarea {idx+1}").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                utensilios_rama = ", ".join(rama.get("utensilios", []))
                dur_rama = rama.get("duracion_minutos", 5)
                timer_id = f"timer_par_{i}_{idx}"
                
                html_diagrama += f"""
                <div class="parallel-subcard">
                    <span class="branch-title">📌 {nombre_rama}</span>
                    <div class="action-text">{accion}</div>
                    <div class="utensil-box">🛠️ <b>Utensilios:</b> {utensilios_rama}</div>
                    <div class="timer-bar">
                        <div class="timer-info">⏱️ <span id="{timer_id}" class="timer-display">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" class="btn-timer">▶️ Temporizador</button>
                    </div>
                </div>
                """
            html_diagrama += '</div></div>'
        else:
            es_convergencia = tipo == "convergencia"
            card_class = "card-convergencia" if es_convergencia else "card-secuencial"
            badge_class = "badge-convergencia" if es_convergencia else "badge-secuencial"
            etiqueta = "🟢 CONVERGENCIA / UNIÓN DE PREPARACIONES" if es_convergencia else f"🔥 PASO {i+1} (COCCIÓN / ACCIÓN)"
            timer_id = f"timer_seq_{i}"

            html_diagrama += f"""
            <div id="{card_id}" class="block-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="badge-tag {badge_class}">{etiqueta}</span>
                    <button onclick="toggleCompletado('{card_id}')" class="btn-done">✓ Marcar completado</button>
                </div>
                <div class="action-text">{bloque.get('accion')}</div>
                <div class="utensil-box">🛠️ <b>Utensilios necesarios:</b> {utensilios_str}</div>
                <div class="timer-bar">
                    <div class="timer-info">⏱️ <span id="{timer_id}" class="timer-display">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" class="btn-timer">▶️ Iniciar Timer</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += '<div class="arrow-down">⬇️</div>'
    
    html_diagrama += "</div>"

    html_recom = """
    <div class="section-card card-recom">
        <h3 class="section-title" style="color: #f59e0b;">💡 4. Recomendaciones del Chef & Presentación</h3>
        <ul class="step-list">
    """
    for rec in recomendaciones:
        html_recom += f"<li>{rec}</li>"
    html_recom += "</ul></div>"

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #f59e0b; font-weight: bold; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span>{origen_receta}</span>'
    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            :root {{
                --bg-main: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f8fafc;
                --text-sub: #94a3b8;
                --border-color: #334155;
                
                --secuencial-bg: #1f1912;
                --secuencial-border: #f59e0b;
                
                --paralelo-bg: #1e1832;
                --paralelo-border: #8b5cf6;
                
                --convergencia-bg: #0d281e;
                --convergencia-border: #10b981;
                
                --mise-bg: #0f2338;
                --mise-border: #3b82f6;

                --btn-timer-bg: #f59e0b;
                --btn-timer-text: #0f172a;
            }}

            body.light-mode {{
                --bg-main: #f8fafc;
                --card-bg: #ffffff;
                --text-main: #0f172a;
                --text-sub: #475569;
                --border-color: #cbd5e1;
                
                --secuencial-bg: #fffbeeb;
                --secuencial-border: #d97706;
                
                --paralelo-bg: #f5f3ff;
                --paralelo-border: #7c3aed;
                
                --convergencia-bg: #ecfdf5;
                --convergencia-border: #059669;
                
                --mise-bg: #eff6ff;
                --mise-border: #2563eb;

                --btn-timer-bg: #d97706;
                --btn-timer-text: #ffffff;
            }}

            body {{ 
                background-color: var(--bg-main); 
                color: var(--text-main); 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
                padding: 12px; 
                margin: 0; 
                transition: background-color 0.3s ease, color 0.3s ease;
            }}

            .container-hub {{ max-width: 950px; margin: auto; }}
            
            .header-card {{ 
                background: var(--card-bg); 
                border-radius: 12px; 
                padding: 24px; 
                margin-bottom: 20px; 
                border: 1px solid var(--border-color); 
                border-left: 8px solid #f59e0b;
            }}

            .main-title {{ font-size: 28px; margin: 12px 0 6px 0; font-weight: 800; color: var(--text-main); }}
            .sub-title {{ color: var(--text-sub); font-size: 15px; margin: 0; }}

            .btn-theme-toggle {{
                background-color: var(--border-color);
                color: var(--text-main);
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 700;
                cursor: pointer;
                font-size: 13px;
            }}

            .widget-voice {{ 
                background-color: var(--card-bg); 
                border: 1px solid var(--border-color); 
                border-radius: 10px; 
                padding: 16px; 
                text-align: center; 
                margin-bottom: 24px; 
            }}

            .btn-kitchen-action {{ 
                background-color: #f59e0b; 
                color: #0f172a; 
                border: none; 
                padding: 14px 24px; 
                font-size: 16px; 
                font-weight: 800; 
                border-radius: 8px; 
                cursor: pointer; 
                margin: 6px; 
                min-height: 48px;
            }}
            .btn-stop {{ background-color: var(--border-color); color: var(--text-main); }}

            .section-card {{
                background-color: var(--card-bg);
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 24px;
                border: 1px solid var(--border-color);
            }}

            .card-mise {{ border-left: 6px solid var(--mise-border); background-color: var(--mise-bg); }}
            .card-recom {{ border-left: 6px solid #f59e0b; }}

            .section-title {{ margin-top: 0; font-size: 18px; font-weight: 800; }}
            .text-blue {{ color: #3b82f6; }}

            .ingredients-grid {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
            .ing-chip {{ 
                background-color: var(--card-bg); 
                color: var(--text-main); 
                padding: 10px 16px; 
                border-radius: 20px; 
                font-size: 14px; 
                font-weight: 600;
                border: 1px solid var(--border-color); 
            }}

            .step-list {{ margin: 10px 0 0 0; padding-left: 20px; color: var(--text-main); font-size: 15px; line-height: 1.7; }}

            .block-card {{ 
                border-radius: 12px; 
                padding: 20px; 
                margin-bottom: 16px; 
                border: 2px solid; 
                transition: opacity 0.3s ease, filter 0.3s ease;
            }}

            .card-secuencial {{ background-color: var(--secuencial-bg); border-color: var(--secuencial-border); }}
            .card-convergencia {{ background-color: var(--convergencia-bg); border-color: var(--convergencia-border); }}
            .card-paralelo-container {{ background-color: var(--paralelo-bg); border-color: var(--paralelo-border); }}

            .badge-tag {{ font-size: 12px; font-weight: 800; padding: 5px 12px; border-radius: 6px; letter-spacing: 0.5px; text-transform: uppercase; }}
            .badge-secuencial {{ background: rgba(245, 158, 11, 0.2); color: #f59e0b; }}
            .badge-convergencia {{ background: rgba(16, 185, 129, 0.2); color: #10b981; }}
            .badge-paralelo {{ background: rgba(139, 92, 246, 0.2); color: #a78bfa; }}

            .action-text {{ font-size: 17px; font-weight: 700; color: var(--text-main); margin: 14px 0; line-height: 1.5; }}
            .utensil-box {{ font-size: 13px; color: var(--text-sub); margin-bottom: 14px; background: rgba(0,0,0,0.15); padding: 8px 12px; border-radius: 6px; }}

            .parallel-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 10px; }}
            .parallel-subcard {{ 
                flex: 1; 
                min-width: 280px; 
                background: var(--card-bg); 
                border: 1px solid var(--paralelo-border); 
                border-radius: 8px; 
                padding: 16px; 
            }}
            .branch-title {{ font-size: 13px; font-weight: 800; color: #a78bfa; display: block; }}

            .timer-bar {{ 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                background: rgba(0,0,0,0.2); 
                padding: 10px 14px; 
                border-radius: 8px; 
                gap: 10px; flex-wrap: wrap;
            }}
            .timer-info {{ font-size: 14px; font-weight: 700; color: var(--text-main); }}
            .timer-display {{ color: #f59e0b; font-size: 16px; font-weight: 800; }}

            .btn-timer {{ 
                background-color: var(--btn-timer-bg); 
                color: var(--btn-timer-text); 
                border: none; 
                padding: 10px 18px; 
                border-radius: 6px; 
                cursor: pointer; 
                font-size: 14px; 
                font-weight: 800; 
                min-height: 44px;
            }}

            .btn-done {{
                background-color: transparent;
                color: var(--text-sub);
                border: 1px solid var(--border-color);
                padding: 6px 12px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 600;
            }}

            .arrow-down {{ text-align: center; color: #f59e0b; font-size: 24px; margin: -6px 0 10px 0; font-weight: bold; }}

            /* Estado de bloque completado */
            .is-completed {{
                opacity: 0.45 !important;
                filter: grayscale(80%) !important;
            }}
            .is-completed .btn-done {{
                background-color: #10b981 !important;
                color: #ffffff !important;
                border-color: #10b981 !important;
            }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}
            <div class="widget-voice">
                <p style="color: var(--text-sub); font-size: 14px; margin: 0 0 10px 0; font-weight: 700;">🎙️ ASISTENTE DE VOZ PARA COCINA</p>
                <button id="btnVoz" class="btn-kitchen-action" onclick="reproducir(this)">🔊 Escuchar Instrucciones Completas</button>
                <button class="btn-kitchen-action btn-stop" onclick="detener()">⏹️ Silenciar</button>
            </div>
            {html_ing}
            {html_prev}
            {html_diagrama}
            {html_recom}
            <div style="text-align: center; color: var(--text-sub); font-size: 13px; margin-top: 35px; border-top: 1px solid var(--border-color); padding-top: 20px;">
                👨‍🍳 <b>FaceFoodChef PRO</b> | Fuente: {origen_html}
            </div>
        </div>

        <script>
            const textoVoz = {texto_voz_seguro};
            let currentUtterance = null;

            function toggleModoCocina() {{
                document.body.classList.toggle('light-mode');
                const btn = document.getElementById('btnTheme');
                if (document.body.classList.contains('light-mode')) {{
                    btn.innerText = "🌙 Modo Oscuro";
                }} else {{
                    btn.innerText = "☀️ Modo Luz (Alto Contraste)";
                }}
            }}

            function toggleCompletado(cardId) {{
                const el = document.getElementById(cardId);
                if (el) {{
                    el.classList.toggle('is-completed');
                }}
            }}

            function reproducir(btn) {{
                if (!('speechSynthesis' in window)) return alert("Sintetizador de voz no soportado en este navegador.");
                window.speechSynthesis.cancel();
                currentUtterance = new SpeechSynthesisUtterance(textoVoz);
                currentUtterance.lang = 'es-ES';
                currentUtterance.rate = 0.95;
                btn.innerText = "🔊 Reproduciendo receta...";
                currentUtterance.onend = () => btn.innerText = "🔊 Escuchar Instrucciones Completas";
                currentUtterance.onerror = () => btn.innerText = "🔊 Escuchar Instrucciones Completas";
                window.speechSynthesis.speak(currentUtterance);
            }}

            function detener() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const btn = document.getElementById('btnVoz');
                    if (btn) btn.innerText = "🔊 Escuchar Instrucciones Completas";
                }}
            }}

            function iniciarTemporizador(elementId, minutos) {{
                const elemento = document.getElementById(elementId);
                let segundosRestantes = minutos * 60;
                if (window[elementId + "_interval"]) clearInterval(window[elementId + "_interval"]);

                window[elementId + "_interval"] = setInterval(() => {{
                    if (segundosRestantes <= 0) {{
                        clearInterval(window[elementId + "_interval"]);
                        elemento.innerText = "¡TIEMPO! 🎉";
                        elemento.style.color = "#ef4444";
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
                try {{
                    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    const oscillator = audioCtx.createOscillator();
                    const gainNode = audioCtx.createGain();
                    oscillator.type = 'sine';
                    oscillator.frequency.setValueAtTime(659.25, audioCtx.currentTime); // Mi
                    gainNode.gain.setValueAtTime(0.4, audioCtx.currentTime);
                    oscillator.connect(gainNode);
                    gainNode.connect(audioCtx.destination);
                    oscillator.start();
                    setTimeout(() => {{ oscillator.stop(); }}, 1500);
                }} catch(e) {{
                    console.log("Audio no permitido sin interacción previa.");
                }}
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
        with st.spinner("🌐 Obteniendo receta desde la URL..."):
            contenido_ia, url_origen_detectada = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error(f"{e}")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif archivo_multimodal:
    procesar_accion = True

if st.button("🚀 GENERAR DIAGRAMA DE COCINA"):
    if not API_KEY:
        st.error("⚠️ Es necesaria una API Key de Google Gemini en el panel lateral para procesar la receta.")
    elif not procesar_accion:
        st.warning("⚠️ Introduce una URL, pega el texto de una receta o sube un archivo antes de continuar.")
    else:
        try:
            client = genai.Client(api_key=API_KEY)
            
            prompt_sistema = f"""
            Eres un chef ejecutivo y programador de procesos culinarios.
            Convierte la receta proporcionada en una estructura JSON válida para generar un diagrama de producción.

            REGLAS STRICTAS:
            1. Devuelve EXCLUSIVAMENTE el JSON solicitado sin bloques de código tipo markdown adicionales.
            2. 'ingredientes': Convierte cantidades imprecisas (pizca, al gusto) a unidades métricas claras: gramos (g), mililitros (ml) o unidades (ud).
            3. 'temperatura': Especifica siempre en Celsius (°C) o indica 'Fuego Medio', 'Fuego Vivo', 'Temperatura Ambiente'.
            4. 'origen_receta': Asigna exactamente ({url_origen_detectada if url_origen_detectada else 'Texto o documento del usuario'}).
            5. 'bloques_proceso': Asigna 'paralelo' para tareas simultáneas (ej. picar cebolla mientras hierva agua) y 'convergencia' cuando se unen preparaciones previas.

            JSON Schema requerido:
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["300 g de arroz arborio", "100 ml de vino blanco"],
              "pasos_previos": ["Mise en place: Picar la cebolla fino y rallar el queso."],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "Paso 1: Calentar el caldo", "utensilios": ["Cazo"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "90°C"}},
                {{
                  "tipo": "paralelo",
                  "ramas": [
                    {{"nombre": "Sartén Principal", "accion": "Sofrreír cebolla", "utensilios": ["Sartén grande"], "tiempo": "8 min", "duracion_minutos": 8, "temperatura": "Fuego medio"}},
                    {{"nombre": "Cazo de Caldo", "accion": "Mantener el caldo a fuego lento", "utensilios": ["Cazo"], "tiempo": "8 min", "duracion_minutos": 8, "temperatura": "85°C"}}
                  ]
                }},
                {{"tipo": "convergencia", "accion": "Añadir el vino y el caldo progresivamente al arroz", "utensilios": ["Espátula de madera"], "tiempo": "18 min", "duracion_minutos": 18, "temperatura": "Fuego medio-bajo"}}
              ],
              "recomendaciones": ["Consejo de emplatado o maridaje"],
              "texto_voz": "Texto descriptivo fluido paso a paso para lectura por voz."
            }}
            """

            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append("Analiza el contenido del documento/imagen adjunto para estructurar la receta.")
            else:
                contents_payload.append(f"Receta a procesar:\n{contenido_ia}")

            with st.spinner(f"⚡ Analizando receta y diagramando flujo con {modelo_seleccionado}..."):
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
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]
                
                datos = json.loads(texto_respuesta.strip())
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto o documento del usuario")

                html_final = generar_html_dashboard(
                    datos.get("nombre_receta", "Receta Culinaria Pro"),
                    origen_final,
                    datos.get("ingredientes", []),
                    datos.get("pasos_previos", []),
                    datos.get("bloques_proceso", []),
                    datos.get("recomendaciones", []),
                    datos.get("texto_voz", "")
                )
                
                st.markdown("<br>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 Descargar Diagrama Autónomo (HTML)",
                    data=html_final,
                    file_name="diagrama_receta_facefoodchef.html",
                    mime="text/html"
                )
                
                components.html(html_final, height=1450, scrolling=True)
                
        except Exception as e:
            st.error(f"Error durante el procesamiento: {e}")
