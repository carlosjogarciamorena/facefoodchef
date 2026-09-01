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
    /* Fondo general gris metálico industrial */
    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    header, footer { visibility: hidden; }
    
    /* Controles de entrada de texto */
    .stTextArea textarea, .stTextInput input, .stSelectbox select {
    .stTextArea textarea, .stTextInput input, .stSelectbox select, .stNumberInput input {
        background-color: #36393F !important;
        color: #ffffff !important;
        border: 2px solid #4F545C !important;
        border-radius: 6px !important;
        font-size: 16px !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
    .stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #EF4444 !important;
        box-shadow: 0 0 10px rgba(239, 68, 68, 0.4) !important;
    }

    /* Botón principal de acción */
    .stButton > button {
        background-color: #EF4444 !important;
        color: #ffffff !important;
@@ -110,7 +107,7 @@
st.sidebar.header("⚙️ Panel de Control")

if API_KEY:
    st.sidebar.success("🔑 API Key vinculada correctamente.")
    st.sidebar.success("🔑 API Key vinculada.")
else:
    API_KEY = st.sidebar.text_input(
        "API Key de Google Gemini:", 
@@ -124,18 +121,26 @@
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
- **Estética:** Fondo Gris Metálico (`#2C2F33`)
- **Métricas:** Decimales métricos (g, ml, ud)
- **Temperatura:** Escala °C
- **Métricas:** Recálculo para comensales (g, ml, ud)
- **Estructura:** Bloques unificados con temporizadores
- **Maridaje:** Sugerencia automatizada (Vino/Cerveza)
""")

st.markdown("<h1 style='text-align: center; color: #EF4444; font-weight: 800; letter-spacing: -1px; margin-bottom: 0;'>FACEFOODCHEF <span style='font-size: 16px; background: #36393F; color: #fff; padding: 4px 10px; border-radius: 4px; vertical-align: middle; border: 1px solid #4F545C;'>PRO</span></h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; font-size: 15px; margin-bottom: 30px;'>Generador interactivo de diagramas de cocina + Sommelier Virtual</p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AEC0; font-size: 15px; margin-bottom: 30px;'>Diagramas de cocina escalables + Sommelier Virtual</p>", unsafe_allow_html=True)

# Entrada de Datos
st.subheader("📥 Entrada de Receta")
@@ -182,7 +187,7 @@
        return texto, url
    except Exception:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
@@ -192,19 +197,19 @@
        except Exception as e:
            raise Exception(f"Error al procesar la URL: {e}")

def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, pasos_previos, bloques_proceso, recomendaciones, texto_voz, maridaje):
def generar_html_dashboard(nombre_receta, origen_receta, ingredientes, pasos_previos, bloques_proceso, recomendaciones, texto_voz, maridaje, comensales):

    html_header = f"""
    <div style="background: linear-gradient(180deg, #36393F 0%, #2F3136 100%); border-radius: 8px; padding: 30px; text-align: center; margin-bottom: 24px; border-left: 6px solid #EF4444; border: 1px solid #4F545C; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <span style="font-size: 11px; font-weight: 800; color: #FFFFFF; text-transform: uppercase; letter-spacing: 2px; background: #EF4444; padding: 6px 14px; border-radius: 4px; display: inline-block;">Diagrama de Producción Culinaria</span>
        <h1 style="color: #ffffff; font-size: 30px; margin: 16px 0 8px 0; font-weight: 800;">{nombre_receta}</h1>
        <p style="color: #A0AEC0; font-size: 14px; margin: 0;">Flujo ejecutable paso a paso optimizado para alta visibilidad</p>
        <p style="color: #A0AEC0; font-size: 14px; margin: 0;">Calculado y escalado para <b>{comensales} comensales</b>.</p>
    </div>
    """

    html_ing = """
    html_ing = f"""
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-radius: 8px; padding: 22px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <h3 style="color: #EF4444; margin-top: 0; font-size: 18px; font-weight: 700;">🛒 1. Ingredientes (Sistema Métrico Exacto)</h3>
        <h3 style="color: #EF4444; margin-top: 0; font-size: 18px; font-weight: 700;">🛒 1. Ingredientes ({comensales} pax)</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px;">
    """
    for ing in ingredientes:
@@ -299,7 +304,6 @@
        html_recom += f"<li>{rec}</li>"
    html_recom += "</ul></div>"

    # NUEVO BLOQUE: MARIDAJE SOMMELIER INTEGRAD EN HTML
    html_maridaje = f"""
    <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 6px solid #9D4EDD; border-radius: 8px; padding: 22px; margin-top: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <h3 style="color: #9D4EDD; margin-top: 0; font-size: 18px; font-weight: 700;">🍷 5. Sommelier Virtual (Maridaje)</h3>
@@ -311,7 +315,6 @@
    """

    origen_html = f'<a href="{origen_receta}" target="_blank" style="color: #EF4444; text-decoration: underline;">{origen_receta}</a>' if origen_receta.startswith("http") else f'<span style="color: #A0AEC0;">{origen_receta}</span>'

    texto_voz_seguro = json.dumps(texto_voz)

    return f"""
@@ -434,9 +437,12 @@
            Eres un experto en gastronomía, sommelier y programador de flujos de trabajo en cocina. 
            Transforma la siguiente receta en un esquema estructurado JSON para renderizar un diagrama de bloques técnico y recomendar un maridaje.

            ¡IMPORTANTE! El usuario requiere que la receta sea para {comensales_objetivo} COMENSALES. 
            Debes ajustar matemáticamente las cantidades de la lista de 'ingredientes' para que correspondan exactamente a {comensales_objetivo} raciones. Si la receta original no indica raciones, asume que era para 2 personas y escala desde ahí.

            REGLAS ESTRICTAS:
            1. Devuelve EXCLUSIVAMENTE un JSON válido sin marcas ni textos adicionales fuera del JSON.
            2. 'ingredientes': Unidades métricas exactas (g, ml, ud).
            2. 'ingredientes': Unidades métricas exactas (g, ml, ud) recalculadas para {comensales_objetivo} comensales.
            3. 'temperatura': Grados Celsius (°C).
            4. 'origen_receta': Asigna exactamente ({url_origen_detectada if url_origen_detectada else 'Texto/Archivo aportado por el usuario'}).
            5. 'bloques_proceso': Asigna 'paralelo' para acciones simultáneas y 'convergencia' para las uniones.
@@ -446,7 +452,7 @@
            {{
              "nombre_receta": "String",
              "origen_receta": "String",
              "ingredientes": ["200 g de harina", "5 g de sal"],
              "ingredientes": ["400 g de harina", "10 g de sal"],
              "pasos_previos": ["Mise en place..."],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "Paso 1", "utensilios": ["Olla"], "tiempo": "5 min", "duracion_minutos": 5, "temperatura": "100°C"}},
@@ -471,11 +477,11 @@
            contents_payload = [prompt_sistema]
            if archivo_multimodal:
                contents_payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
                contents_payload.append("Analiza el archivo adjunto para extraer la receta y el maridaje.")
                contents_payload.append(f"Analiza el archivo adjunto para extraer la receta, escalar a {comensales_objetivo} comensales y recomendar maridaje.")
            else:
                contents_payload.append(f"Receta:\n{contenido_ia}")

            with st.spinner(f"⚙️ Procesando diagrama y sommelier con {modelo_seleccionado}..."):
            with st.spinner(f"⚙️ Procesando diagrama (Escalando a {comensales_objetivo} pax) y sommelier con {modelo_seleccionado}..."):
                response = client.models.generate_content(
                    model=modelo_seleccionado,
                    contents=contents_payload,
@@ -497,7 +503,6 @@
                datos = json.loads(texto_respuesta.strip())
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto aportado por el usuario")

                # Llamada actualizada con el maridaje
                html_final = generar_html_dashboard(
                    datos.get("nombre_receta", "Receta Culinaria Pro"),
                    origen_final,
@@ -506,7 +511,8 @@
                    datos.get("bloques_proceso", []),
                    datos.get("recomendaciones", []),
                    datos.get("texto_voz", ""),
                    datos.get("maridaje", {}) # <-- Inyección del maridaje
                    datos.get("maridaje", {}),
                    comensales_objetivo
                )

                st.markdown("<br>", unsafe_allow_html=True)
