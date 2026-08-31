import json
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import streamlit as st
from recipe_scrapers import scrape_me
from google import genai
from google.genai import types

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

# Panel de Control - Autenticación Manual
st.sidebar.header("⚙️ Panel de Control")

API_KEY = st.sidebar.text_input(
    "🔑 API Key de Google Gemini:", 
    type="password", 
    help="Introduce tu clave API manualmente para esta sesión."
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo Gemini:",
    options=["gemini-2.5-flash", "gemini-1.5-flash"],
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
### 🎬 FaceFoodChef.com
- **Métricas:** Recálculo para comensales (g, ml, ud)
- **Estructura:** Bloques unificados estables
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
        archivo_multimodal = archivo_subido

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

def renderizar_dashboard_nativo(datos, comensales, origen_receta):
    nombre = datos.get("nombre_receta", "Receta Culinaria Pro")
    ingredientes = datos.get("ingredientes", [])
    pasos_previos = datos.get("pasos_previos", [])
    bloques_proceso = datos.get("bloques_proceso", [])
    recomendaciones = datos.get("recomendaciones", [])
    maridaje = datos.get("maridaje", {})

    st.markdown(f"""
    <div style="background: linear-gradient(180deg, #36393F 0%, #2F3136 100%); border-radius: 8px; padding: 25px; text-align: center; margin-bottom: 20px; border-left: 6px solid #EF4444; border: 1px solid #4F545C;">
        <span style="font-size: 11px; font-weight: 800; color: #FFFFFF; text-transform: uppercase; letter-spacing: 2px; background: #EF4444; padding: 5px 12px; border-radius: 4px;">Diagrama de Producción Culinaria</span>
        <h2 style="color: #ffffff; margin: 12px 0 6px 0; font-weight: 800;">{nombre}</h2>
        <p style="color: #A0AEC0; font-size: 14px; margin: 0;">Calculado y escalado para <b>{comensales} comensales</b>.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"### 🛒 1. Ingredientes ({comensales} pax)")
    cols_ing = st.columns(2)
    for idx, ing in enumerate(ingredientes):
        cols_ing[idx % 2].markdown(f"- {ing}")

    if pasos_previos:
        st.markdown("### 🔪 2. Mise en Place (Preparación Previa)")
        for prev in pasos_previos:
            st.markdown(f"- {prev}")

    st.markdown("### 3. Diagrama de Ejecución")
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        utensilios_str = ", ".join(bloque.get("utensilios", [])) or "Sin utensilios específicos"
        
        if tipo == "paralelo":
            st.markdown("#### ⚙️ Bloque en Paralelo")
            ramas = bloque.get("ramas", [])
            cols_ramas = st.columns(len(ramas) if ramas else 1)
            for r_idx, rama in enumerate(ramas):
                with cols_ramas[r_idx]:
                    st.markdown(f"""
                    <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 5px solid #F59E0B; border-radius: 6px; padding: 15px; margin-bottom: 10px;">
                        <b style="color: #F59E0B;">{rama.get('nombre', f'Rama {r_idx+1}')}</b><br>
                        <p style="margin: 8px 0; color: #E2E8F0; font-size: 14px;">{rama.get('accion')}</p>
                        <hr style="border-color: #4F545C; margin: 8px 0;">
                        <span style="font-size: 12px; color: #A0AEC0;">🛠️ {', '.join(rama.get('utensilios', []))}</span><br>
                        <span style="font-size: 12px; color: #FBBF24;">⏱️ {rama.get('tiempo')} | 🌡️ {rama.get('temperatura')}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            es_conv = tipo == "convergencia"
            b_color = "#10B981" if es_conv else "#EF4444"
            etiqueta = "CONVERGENCIA / UNIÓN" if es_conv else f"PASO {i+1}"
            
            st.markdown(f"""
            <div style="background-color: #36393F; border: 1px solid #4F545C; border-left: 6px solid {b_color}; border-radius: 6px; padding: 16px; margin-bottom: 15px;">
                <span style="font-size: 10px; font-weight: 800; background: {b_color}; color: white; padding: 3px 8px; border-radius: 3px; text-transform: uppercase;">{etiqueta}</span>
                <p style="margin: 10px 0; font-size: 15px; font-weight: 600; color: #ffffff;">{bloque.get('accion')}</p>
                <div style="font-size: 13px; color: #A0AEC0; background: rgba(0,0,0,0.2); padding: 6px 10px; border-radius: 4px;">
                    🛠️ <b>Utensilios:</b> {utensilios_str} &nbsp;|&nbsp; ⏱️ <b style="color: #FBBF24;">{bloque.get('tiempo')}</b> &nbsp;|&nbsp; 🌡️ {bloque.get('temperatura')}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        if i < len(bloques_proceso) - 1:
            st.markdown("<div style='text-align: center; color: #ffffff; font-size: 18px; margin: -5px 0 10px 0;'>⬇️</div>", unsafe_allow_html=True)

    if recomendaciones:
        st.markdown("### 💡 4. Recomendaciones del Chef")
        for rec in recomendaciones:
            st.markdown(f"- {rec}")

    if maridaje:
        st.markdown("### 🍷 5. Sommelier Virtual (Maridaje)")
        col_vino, col_cerveza = st.columns(2)
        with col_vino:
            st.info(f"**🍇 Sugerencia de Vino:**\n\n{maridaje.get('vino', 'N/D')}")
        with col_cerveza:
            st.warning(f"**🍺 Sugerencia de Cerveza:**\n\n{maridaje.get('cerveza', 'N/D')}")

    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: #718096; font-size: 12px;'>🎬 <b>FaceFoodChef.com</b> | Fuente: {origen_receta}</div>", unsafe_allow_html=True)

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
        st.error("⚠️ Es necesaria una API Key de Google Gemini para procesar la receta. Introdúcela en el menú lateral.")
    elif not procesar_accion:
        st.warning("⚠️ Introduce una URL, un texto o adjunta un archivo antes de continuar.")
    else:
        try:
            # Inicialización con el SDK oficial y actualizado google-genai
            client = genai.Client(api_key=API_KEY.strip())

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
                bytes_data = archivo_multimodal.getvalue()
                mime_t = archivo_multimodal.type
                contents_payload.append(types.Part.from_bytes(data=bytes_data, mime_t=mime_t))
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
                    )
                )

            if response and response.text:
                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                elif texto_respuesta.startswith("```"):
                    texto_respuesta = texto_respuesta[3:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]
                
                datos = json.loads(texto_respuesta.strip())
                origen_final = url_origen_detectada if url_origen_detectada else datos.get("origen_receta", "Texto aportado por el usuario")

                renderizar_dashboard_nativo(datos, comensales_objetivo, origen_final)
                
        except Exception as e:
            st.error(f"Error durante el procesamiento: {e}")
