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

# Cargar variables de entorno si existe archivo .env
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

st.set_page_config(page_title="FaceFoodChef Pro - Motor de Diagramas Culinarios", layout="wide", page_icon="🍳")

# --- SISTEMA DE CARGA AUTOMÁTICA DE API KEY ---
API_KEY = None
if "GEMINI_API_KEY" in st.secrets:
    API_KEY = st.secrets["GEMINI_API_KEY"]
elif os.getenv("GEMINI_API_KEY"):
    API_KEY = os.getenv("GEMINI_API_KEY")

st.sidebar.header("⚙️ Panel de Control")

if API_KEY:
    st.sidebar.success("🔑 API Key cargada correctamente.")
else:
    API_KEY = st.sidebar.text_input(
        "API Key de Google Gemini:", 
        type="password", 
        help="Consíguela en aistudio.google.com"
    )

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 Normas del Sistema\n- **Medidas:** Estrictamente en gramos (g), mililitros (ml) o unidades (ud).\n- **Temperaturas:** Siempre en grados Celsius (°C).\n- **Flujo:** Detección de tareas simultáneas (paralelo) y uniones (convergencia).")

# Estilos visuales Dark Glassmorphism Pro
st.markdown("""
    <style>
    .main { background-color: #07090e; }
    .stTextArea textarea, .stFileUploader {
        background-color: #0d1117; color: #f0f6fc;
        border-radius: 12px; border: 1px solid #30363d; font-size: 14px;
    }
    h1, h2, h3 { color: #f0f6fc; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #ff7b72;'>🍳 FaceFoodChef Pro <span style='font-size: 16px; background: #1f6feb; color: white; padding: 4px 10px; border-radius: 20px; vertical-align: middle;'>Diagram Engine</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b949e;'>Transforma recetas en diagramas de flujo lógicos con medidas métricas exactas (g, ml), temperaturas en °C y temporizadores integrados.</p>", unsafe_allow_html=True)

# ENTRADA ÚNICA SIMPLIFICADA (Sin buscadores ni entradas duplicadas)
st.subheader("📥 Entrada de Receta")
entrada_principal = st.text_area(
    "Pega la URL web o el texto completo de la receta:", 
    height=140, 
    placeholder="Ejemplo URL: https://www.ejemplo.com/receta-paella\nO pega directamente el texto de la receta aquí..."
)

with st.expander("📁 Subir archivo alternativo (PDF, Word, PPT o Imagen)"):
    archivo_subido = st.file_uploader("Carga un documento o fotografía:", type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"])

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
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url
        except Exception as e:
            raise Exception(f"Error al leer la URL: {e}")

def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, pasos_previos, bloques_proceso, recomendaciones, texto_voz):
    html_header = f"""
    <div style="background: linear-gradient(135deg, #1f242d 0%, #111418 100%); border: 1px solid #30363d; border-bottom: 4px solid #ff7b72; border-radius: 20px; padding: 28px; text-align: center; margin-bottom: 24px;">
        <span style="font-size: 12px; font-weight: 800; color: #ff7b72; text-transform: uppercase; letter-spacing: 1.5px; background: rgba(255,123,114,0.15); padding: 6px 14px; border-radius: 20px;">📜 Receta Magistral</span>
        <h1 style="color: #f0f6fc; font-size: 28px; margin: 16px 0 8px 0; font-weight: 800;">{nombre_receta}</h1>
        <p style="color: #8b949e; font-size: 14px; margin: 0;">Diagrama de ejecución de cocina paso a paso</p>
    </div>
    """

    html_ing = """
    <div style="background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); border: 1px solid #30363d; border-radius: 18px; padding: 22px; margin-bottom: 20px;">
        <h3 style="color: #ff7b72; margin-top: 0; font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>🛒</span> 1. Ingredientes (Cantidades Métricas Exactas: g, ml, ud)
        </h3>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background: #21262d; color: #c9d1d9; padding: 6px 14px; border-radius: 10px; font-size: 13px; border: 1px solid #30363d; font-weight: 500;'>⚖️ {ing}</span>"
    html_ing += "</div></div>"

    html_prev = """
    <div style="background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); border: 1px solid #30363d; border-radius: 18px; padding: 22px; margin-bottom: 24px;">
        <h3 style="color: #58a6ff; margin-top: 0; font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>🔪</span> 2. Mise en Place (Preparación Previa)
        </h3>
        <ul style='margin: 10px 0 0 0; padding-left: 20px; color: #8b949e; font-size: 14px; line-height: 1.7;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li style='margin-bottom: 6px; color: #c9d1d9;'>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 100%; margin: auto;">
        <h3 style="color: #3fb950; font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
            <span>📊</span> 3. Diagrama de Flujo Ejecutable
        </h3>
    """
    
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        duracion_min = bloque.get("duracion_minutos", 5)
        utensilios = bloque.get("utensilios", [])
        utensilios_str = ", ".join(utensilios) if utensilios else "Ninguno específico"
        
        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += '<div style="display: flex; gap: 14px; margin-bottom: 18px; flex-wrap: wrap;">'
            for idx, rama in enumerate(ramas):
                nombre_rama = rama.get("nombre", f"Rama {idx+1}").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                utensilios_rama = ", ".join(rama.get("utensilios", []))
                dur_rama = rama.get("duracion_minutos", 5)
                timer_id = f"timer_par_{i}_{idx}"
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 270px; background: linear-gradient(135deg, #1f1a3a 0%, #11112b 100%); border: 1px solid #483699; border-left: 5px solid #8957e5; border-radius: 16px; padding: 20px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-size: 11px; font-weight: 800; color: #d2a8ff; background: rgba(137,87,229,0.2); padding: 4px 10px; border-radius: 6px;">🔀 TAREA PARALELA: {nombre_rama}</span>
                    </div>
                    <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin-bottom: 10px; line-height: 1.5;">{accion}</div>
                    <div style="font-size: 12px; color: #a5d6ff; margin-bottom: 12px; background: rgba(0,0,0,0.2); padding: 6px 10px; border-radius: 8px;">🛠️ <b>Utensilios:</b> {utensilios_rama}</div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; background: rgba(0,0,0,0.3); padding: 10px 14px; border-radius: 10px;">
                        <div style="font-size: 13px; color: #c9d1d9;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #58a6ff;">{tiempo}</span> | 🌡️ {temp}</div>
                        <button onclick="iniciarTemporizador('{timer_id}', {dur_rama})" style="background: #238636; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">▶️ Iniciar</button>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            es_convergencia = tipo == "convergencia"
            bg = "linear-gradient(135deg, #0d2818 0%, #081a10 100%)" if es_convergencia else "linear-gradient(135deg, #161b22 0%, #0d1117 100%)"
            border_color = "#2ea043" if es_convergencia else "#30363d"
            left_border = "#3fb950" if es_convergencia else "#ff7b72"
            badge_bg = "rgba(46,160,67,0.2)" if es_convergencia else "rgba(255,123,114,0.15)"
            icono = "🔗" if es_convergencia else "🔥"
            etiqueta = "CONVERGENCIA / UNIÓN" if es_convergencia else f"PASO {i+1}"
            
            timer_id = f"timer_seq_{i}"
            html_diagrama += f"""
            <div style="background: {bg}; border: 1px solid {border_color}; border-left: 5px solid {left_border}; border-radius: 16px; padding: 20px; margin-bottom: 18px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 11px; font-weight: 800; color: #8b949e; background: {badge_bg}; padding: 4px 10px; border-radius: 6px;">{icono} {etiqueta}</span>
                </div>
                <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin-bottom: 10px; line-height: 1.5;">{bloque.get('accion')}</div>
                <div style="font-size: 12px; color: #a5d6ff; margin-bottom: 12px; background: rgba(0,0,0,0.2); padding: 6px 10px; border-radius: 8px;">🛠️ <b>Utensilios:</b> {utensilios_str}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.25); padding: 10px 14px; border-radius: 10px;">
                    <div style="font-size: 13px; color: #c9d1d9;">⏱️ <span id="{timer_id}" style="font-weight: bold; color: #58a6ff;">{bloque.get('tiempo')}</span> | 🌡️ {bloque.get('temperatura')}</div>
                    <button onclick="iniciarTemporizador('{timer_id}', {duracion_min})" style="background: #238636; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;">▶️ Iniciar Timer</button>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += '<div style="text-align: center; color: #3fb950; font-size: 24px; margin: -4px 0 4px 0; font-weight: bold;">⬇️</div>'
    
    html_diagrama += "</div>"

    html_recom = """
    <div style="background: linear-gradient(135deg, #1f1f11 0%, #12120a 100%); border: 1px solid #d29922; border-radius: 18px; padding: 22px; margin-top: 24px; margin-bottom: 20px;">
        <h3 style="color: #e3b341; margin-top: 0; font-size: 17px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>💡</span> 4. Recomendaciones de Chef
        </h3>
        <ul style='margin: 10px 0 0 0; padding-left: 20px; color: #e6edf3; font-size: 14px; line-height: 1.7;'>
    """
    for rec in recomendaciones:
        html_recom += f"<li style='margin-bottom: 6px;'>{rec}</li>"
    html_recom += "</ul></div>"

    # Pie de página ajustado estrictamente a "Fuente de Origen"
    if origen_receta.startswith("http://") or origen_receta.startswith("https://"):
        origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #58a6ff; text-decoration: underline;">{origen_receta}</a>'
    else:
        origen_html = f'<span style="color: #c9d1d9;">{origen_receta}</span>'

    html_footer = f"""
    <div style="text-align: center; color: #8b949e; font-size: 13px; margin-top: 35px; border-top: 1px solid #30363d; padding-top: 20px;">
        🌍 <b>Fuente de Origen:</b> {origen_html}
    </div>
    """

    texto_voz_seguro = json.dumps(texto_voz)

    documento_completo = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ background-color: #07090e; color: #f0f6fc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; margin: 0; }}
            .container-hub {{ display: grid; grid-template-columns: 1fr; gap: 20px; max-width: 900px; margin: auto; }}
            .widget-box {{ background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border: 1px solid #30363d; border-radius: 18px; padding: 18px; text-align: center; }}
            .btn-control {{ background-color: #238636; color: white; border: none; padding: 10px 20px; font-size: 13px; font-weight: 700; border-radius: 10px; cursor: pointer; margin: 4px; }}
            .btn-stop {{ background-color: #da3633; }}
        </style>
    </head>
    <body>
        <div class="container-hub">
            {html_header}

            <div class="widget-box">
                <p style="color: #8b949e; font-size: 13px; margin: 0 0 10px 0; font-weight: 600;">🎙️ Asistente de Voz Integrado</p>
                <button id="btnVoz" class="btn-control" onclick="reproducir(this)">▶️ Escuchar Guía de Cocina</button>
                <button class="btn-control btn-stop" onclick="detener()">⏹️ Silenciar</button>
            </div>

            {html_ing}
            {html_prev}
            {html_diagrama}
            {html_recom}
            {html_footer}
        </div>

        <script>
            const textoVoz = {texto_voz_seguro};
            let currentUtterance = null;

            function reproducir(btn) {{
                if (!('speechSynthesis' in window)) return alert("Tu navegador no soporta síntesis de voz.");
                window.speechSynthesis.cancel();
                currentUtterance = new SpeechSynthesisUtterance(textoVoz);
                currentUtterance.lang = 'es-ES'; 
                currentUtterance.rate = 0.95;
                btn.innerText = "🔊 Reproduciendo...";
                currentUtterance.onend = () => btn.innerText = "▶️ Escuchar Guía de Cocina";
                currentUtterance.onerror = () => btn.innerText = "▶️ Escuchar Guía de Cocina";
                window.speechSynthesis.speak(currentUtterance);
            }}

            function detener() {{
                if ('speechSynthesis' in window) {{ 
                    window.speechSynthesis.cancel(); 
                    const btn = document.getElementById('btnVoz');
                    if (btn) btn.innerText = "▶️ Escuchar Guía de Cocina";
                }}
            }}

            function iniciarTemporizador(elementId, minutos) {{
                const elemento = document.getElementById(elementId);
                let segundosRestantes = minutos * 60;
                if (window[elementId + "_interval"]) clearInterval(window[elementId + "_interval"]);

                window[elementId + "_interval"] = setInterval(() => {{
                    if (segundosRestantes <= 0) {{
                        clearInterval(window[elementId + "_interval"]);
                        elemento.innerText = "¡TIEMPO CUMPLIDO! 🎉";
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
                gainNode.gain.setValueAtTime(0.2, audioCtx.currentTime);
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.start();
                setTimeout(() => {{ oscillator.stop(); }}, 1200);
            }}
        </script>
    </body>
    </html>
    """
    return documento_completo

# Ejecución del procesador
procesar_accion = False
contenido_ia = None

if url_origen_detectada:
    try:
        with st.spinner("🌐 Leyendo contenido de la URL..."):
            contenido_ia, url_origen_detectada = extraer_texto_de_url(url_origen_detectada)
            procesar_accion = True
    except Exception as e:
        st.error(f"{e}")
elif receta_texto_input:
    contenido_ia = receta_texto_input
    procesar_accion = True
elif archivo_multimodal:
    procesar_accion = True

if procesar_accion and API_KEY:
    try:
        client = genai.Client(api_key=API_KEY)
        
        prompt_sistema = f"""
        Eres un chef ejecutor e ingeniero de procesos gastronómicos. Convierte la receta en un esquema JSON estructurado.

        REGLAS DE ORO OBLIGATORIAS:
        1. Devuelve ÚNICAMENTE un objeto JSON válido (sin Markdown adicional).
        2. 'ingredientes': NUNCA uses medidas vagas como "sal al gusto", "media cucharadita", "pizca" o "chorrito". Convierte OBLIGATORIAMENTE todas las medidas a métricas exactas: gramos (g), mililitros (ml) o unidades (ud). Ejemplo: "3 g de sal", "15 ml de aceite de oliva", "250 g de harina".
        3. 'temperatura' en los bloques de proceso: NUNCA pongas solo "fuego lento" o "fuego medio". Incluye SIEMPRE la temperatura en grados Celsius (°C). Ejemplo: "90°C (Fuego medio)", "180°C (Horno)", "100°C (Ebullición)".
        4. 'origen_receta': Utiliza exactamente la URL provista ({url_origen_detectada if url_origen_detectada else 'Texto aportado por el usuario'}).
        5. 'bloques_proceso': Detecta y separa tareas simultáneas usando el tipo "paralelo" con sus respectivas ramas, y usa "convergencia" cuando se unan las preparaciones.

        Estructura JSON esperada:
        {{
          "nombre_receta": "Nombre de la receta",
          "origen_receta": "{url_origen_detectada if url_origen_detectada else 'Texto aportado por el usuario'}",
          "ingredientes": ["200 g de harina", "5 g de sal", "15 ml de aceite"],
          "pasos_previos": ["Mise en place de verduras"],
          "bloques_proceso": [
            {{"tipo": "secuencial", "accion": "Paso 1...", "utensilios": ["Olla"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "100°C"}},
            {{
              "tipo": "paralelo",
              "ramas": [
                {{"nombre": "Sartén 1", "accion": "Sofreír...", "utensilios": ["Sartén"], "tiempo": "10 min", "duracion_minutos": 10, "temperatura": "90°C (Fuego medio)"}},
                {{"nombre": "Olla 2", "accion": "Cocer pasta...", "utensilios": ["Olla"], "tiempo": "8 min", "duracion_minutos": 8, "temperatura": "100°C (Ebullición)"}}
              ]
            }},
            {{"tipo": "convergencia", "accion": "Mezclar salsa con la pasta...", "utensilios": ["Sartén grande"], "tiempo": "2 min", "duracion_minutos": 2, "temperatura": "80°C"}}
          ],
          "recomendaciones": ["Consejo 1", "Consejo 2"],
          "texto_voz": "Resumen completo para escuchar"
        }}
        """

        contents_payload = [prompt_sistema]
        if archivo_multimodal:
            contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
            contents_payload.append("Analiza esta receta adjunta extrayendo ingredientes en g/ml y temperaturas en °C.")
        else:
            contents_payload.append(f"Receta a procesar:\n{contenido_ia}")

        with st.spinner("⚙️ Diseñando diagrama de flujo en formato métrico..."):
            response = client.models.generate_content(
                model='gemini-2.5-flash',
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
            
            origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto aportado por el usuario")

            html_final = generar_html_dashboard(
                datos.get("nombre_receta", "Receta Culinaria Pro"),
                origen_final,
                datos.get("ingredientes", []),
                datos.get("pasos_previos", []),
                datos.get("bloques_proceso", []),
                datos.get("recomendaciones", []),
                datos.get("texto_voz", "")
            )
            
            st.download_button(
                label="📥 Descargar Diagrama en HTML",
                data=html_final,
                file_name="diagrama_receta.html",
                mime="text/html"
            )
            
            components.html(html_final, height=1350, scrolling=True)
            
    except Exception as e:
        st.error(f"Error procesando la receta: {e}")
elif not API_KEY:
    st.info("👈 Agrega tu API Key de Gemini en la barra lateral para comenzar.")
