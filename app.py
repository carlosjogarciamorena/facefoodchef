import os
import re
import json
import time
import streamlit as st
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FaceFoodChef — Generador de Flujogramas de Cocina",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. ESTILOS CSS PERSONALIZADOS (ESTÉTICA DARK / NETFLIX)
# -----------------------------------------------------------------------------
NETFLIX_DARK_STYLE = """
<style>
    /* Estilos Generales y Fondo */
    .stApp {
        background-color: #141414;
        color: #E5E5E5;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* Ocultar elementos nativos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    
    /* Header estilo Marca Netflix */
    .brand-container {
        display: flex;
        align-items: center;
        gap: 15px;
        margin-bottom: 20px;
        border-bottom: 1px solid #282828;
        padding-bottom: 15px;
    }
    .brand-title {
        color: #E50914;
        font-size: 3rem;
        font-weight: 900;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin: 0;
        line-height: 1;
    }
    .brand-badge {
        background-color: #E50914;
        color: #FFFFFF;
        font-size: 0.75rem;
        font-weight: 800;
        padding: 4px 8px;
        border-radius: 3px;
        text-transform: uppercase;
    }
    .brand-subtitle {
        color: #A3A3A3;
        font-size: 1.05rem;
        margin-top: 5px;
    }

    /* Botones Rojos Primarios */
    div.stButton > button {
        background-color: #E50914 !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.65rem 1.4rem !important;
        font-size: 1rem !important;
        transition: all 0.2s ease-in-out !important;
        box-shadow: 0 4px 10px rgba(229, 9, 20, 0.3);
    }
    div.stButton > button:hover {
        background-color: #F40612 !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 15px rgba(229, 9, 20, 0.5);
    }
    
    /* Inputs y Textareas */
    .stTextArea textarea, .stTextInput input, .stSelectbox select {
        background-color: #232323 !important;
        color: #FFFFFF !important;
        border: 1px solid #3d3d3d !important;
        border-radius: 6px !important;
        font-size: 0.95rem !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #E50914 !important;
        box-shadow: 0 0 0 1px #E50914 !important;
    }

    /* Contenedores de Tarjetas (Cards) */
    .css-card {
        background-color: #181818;
        border: 1px solid #2B2B2B;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
    }

    /* Pestañas (Tabs) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        border-bottom: 1px solid #2B2B2B;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 4px;
        color: #A3A3A3;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #232323 !important;
        color: #E50914 !important;
        border-bottom: 2px solid #E50914 !important;
    }
    
    /* Checklist Modo Cocina */
    .step-box {
        background-color: #1F1F1F;
        border-left: 4px solid #E50914;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 0 6px 6px 0;
    }
</style>
"""
st.markdown(NETFLIX_DARK_STYLE, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. VERIFICACIÓN E IMPORTACIÓN DE GOOGLE GENERATIVE AI
# -----------------------------------------------------------------------------
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ModuleNotFoundError:
    GENAI_AVAILABLE = False

# -----------------------------------------------------------------------------
# 4. GESTIÓN DE ESTADO DE SESIÓN (SESSION STATE)
# -----------------------------------------------------------------------------
if "mermaid_code" not in st.session_state:
    st.session_state["mermaid_code"] = ""
if "recipe_history" not in st.session_state:
    st.session_state["recipe_history"] = []
if "completed_steps" not in st.session_state:
    st.session_state["completed_steps"] = {}
if "last_processed_recipe" not in st.session_state:
    st.session_state["last_processed_recipe"] = ""

# -----------------------------------------------------------------------------
# 5. RECETAS PREDEFINIDAS DE EJEMPLO
# -----------------------------------------------------------------------------
PRESET_RECIPES = {
    "Tortilla Española Tradicional": """Ingredientes: 6 huevos, 1 kg de patatas, 1 cebolla grande, aceite de oliva virgen extra, sal.

Pasos de preparación:
1. Pelar y cortar las patatas en láminas finas. Picar la cebolla en juliana fina.
2. Calentar abundante aceite de oliva en una sartén grande a fuego medio.
3. Añadir las patatas y la cebolla a la sartén. Freír a fuego lento durante 18-20 minutos hasta que estén tiernas pero no tostadas.
4. Mientras se fríen las patatas, batir los 6 huevos en un bol grande con sal al gusto.
5. Escurrir bien el aceite de las patatas y la cebolla usando un colador.
6. Meclarse las patatas y la cebolla calientes con el huevo batido en el bol. Dejar reposar la mezcla durante 5 minutos para que absorba el huevo.
7. En una sartén antiadherente con una cucharada de aceite a fuego alto, verter la mezcla.
8. Cuajar durante 2 minutos a fuego medio-alto. Dar la vuelta a la tortilla con un plato plano y cuajar el otro lado durante 2 minutos más.
9. Servir en un plato y dejar atemperar 5 minutos antes de cortar.""",

    "Paella Valenciana": """Ingredientes: 400g arroz bomba, 500g pollo troceado, 400g conejo troceado, 200g judías verdes (bajoqueta), 100g garrofó, 1 tomate maduro rallado, hebras de azafrán, pimentón dulce, 1.2L caldo de pollo o agua, aceite de oliva, sal y romero fresco.

Pasos de preparación:
1. Calentar aceite de oliva en la paella a fuego medio-alto y añadir sal en los bordes.
2. Dorar el pollo y el conejo durante 12 minutos hasta que estén bien sellados.
3. Apartar la carne hacia los bordes de la paella y sofreír las judías verdes y el garrofó en el centro durante 5 minutos.
4. Añadir el tomate rallado al centro y sofreír durante 3 minutos. Incorporar el pimentón dulce y remover rápidamente sin quemar.
5. Verter el caldo y añadir las hebras de azafrán. Cocer todo junto a fuego vivo durante 15 minutos para crear el caldo base.
6. Añadir el arroz bomba repartiéndolo en una diagonal en la paella.
7. Cocinar a fuego fuerte durante 8 minutos y luego bajar a fuego lento durante 10 minutos.
8. Colocar una ramita de romero encima durante los últimos 5 minutos de cocción y luego retirarla.
9. Dejar reposar la paella cubierta con un paño durante 5 minutos antes de servir.""",

    "Brownie de Chocolate y Nueces": """Ingredientes: 200g chocolate negro 70%, 150g mantequilla, 200g azúcar, 3 huevos, 80g harina de trigo, 100g nueces troceadas, 1 pizca de sal.

Pasos de preparación:
1. Precalentar el horno a 180°C y engrasar un molde cuadrado con mantequilla y harina.
2. Derretir el chocolate negro junto con la mantequilla al baño María o en microondas a intervalos de 30 segundos. Reservar y atemperar.
3. En un bol, batir los huevos con el azúcar durante 3 minutos hasta que la mezcla blanquee ligeramente.
4. Verter el chocolate fundido sobre los huevos batidos e integrar con espátula.
5. Tamizar la harina con la sal e incorporarla a la mezcla con movimientos envolventes.
6. Añadir las nueces troceadas y mezclar suavemente.
7. Verter la masa en el molde horneando durante 22 minutos a 180°C.
8. Retirar del horno, dejar enfriar completamente en el molde antes de desmoldar y cortar en cuadrados."""
}

# -----------------------------------------------------------------------------
# 6. PROMPT ENGINEERING Y MOTOR LLM
# -----------------------------------------------------------------------------
PROMPT_SISTEMA_MERMAID = """
Eres un ingeniero experto en optimización de procesos gastronómicos. Tu trabajo consiste en convertir el texto de una receta de cocina en un diagrama de flujo estructurado usando la sintaxis exacta de Mermaid.js (graph TD).

REGLAS DE CONSTRUCCIÓN DEL DIAGRAMA:
1. El código debe comenzar SIEMPRE con la línea: `graph TD`.
2. Nodos de Ingredientes: Utiliza corchetes rectangulares `[Ingrediente]`.
3. Nodos de Proceso / Técnica: Utiliza corchetes redondeados `(Acción / Técnica)`. Incluye explícitamente el tiempo y la temperatura si existen (ej. "(Hornear | 180°C - 20 min)").
4. Agrupamiento Paralelo: Identifica qué tareas pueden hacerse simultáneamente (ej. calentar agua mientras se pican las verduras) y represéntalas como ramas independientes que convergen más adelante.
5. Nodos de Decisión / Verificación: Usa rombos `{¿Condición?}` para comprobaciones (ej. `{¿Está dorado?}`).
6. Nodo Final: Termina en el plato servido con doble paréntesis `((Plato Listo))`.
7. APLICA ESTILOS CSS MEDIANTE CLASES EN MERMAID:
   Agrega estas definiciones al inicio del código:
   classDef ing fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
   classDef proc fill:#262626,stroke:#ffffff,stroke-width:1px,color:#fff;
   classDef cook fill:#451a03,stroke:#f97316,stroke-width:2px,color:#fff;
   classDef final fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff;

   Y asigna las clases a cada nodo según corresponda:
   class NODO_ID ing;
   class NODO_ID proc;
   class NODO_ID cook;
   class NODO_ID final;

ESTRICCIÓN DE SALIDA:
Devuelve EXCLUSIVAMENTE el código de Mermaid.js puro sin bloques de código Markdown (sin ```mermaid ni ```), sin textos introductorios ni explicaciones posteriores.
"""

def generar_diagrama_mermaid(receta_texto: str, api_key: str, modelo_nombre: str) -> str:
    """Envía la receta a la API de Google Gemini y devuelve el código de Mermaid estructurado."""
    if not GENAI_AVAILABLE:
        raise ImportError("La librería `google-generativeai` no está instalada.")
        
    genai.configure(api_key=api_key)
    
    # Manejo de modelo configurado
    model = genai.GenerativeModel(modelo_nombre)
    prompt_completo = f"{PROMPT_SISTEMA_MERMAID}\n\nRECETA A PROCESAR:\n{receta_texto}"
    
    respuesta = model.generate_content(
        prompt_completo,
        generation_config={"temperature": 0.1, "max_output_tokens": 2048}
    )
    
    codigo_raw = respuesta.text.strip()
    
    # Limpieza de marcado markdown en caso de existir
    if "```" in codigo_raw:
        lineas = codigo_raw.split("\n")
        lineas_limpias = [l for l in lineas if not l.strip().startswith("```")]
        codigo_raw = "\n".join(lineas_limpias)
        
    return codigo_raw.strip()

# -----------------------------------------------------------------------------
# 7. COMPONENTE RENDERIZADOR HTML/MERMAID
# -----------------------------------------------------------------------------
def renderizar_mermaid_html(codigo_mermaid: str, orientacion: str = "TD", tema_mermaid: str = "dark", alto: int = 650):
    """Renderiza la sintaxis Mermaid dentro de un IFrame interactivo."""
    
    # Reemplazar la dirección si el usuario la cambia
    if orientacion == "LR" and "graph TD" in codigo_mermaid:
        codigo_mermaid = codigo_mermaid.replace("graph TD", "graph LR")
    elif orientacion == "TD" and "graph LR" in codigo_mermaid:
        codigo_mermaid = codigo_mermaid.replace("graph LR", "graph TD")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{
                startOnLoad: true,
                theme: '{tema_mermaid}',
                securityLevel: 'loose',
                themeVariables: {{
                    darkMode: true,
                    background: '#181818',
                    primaryColor: '#E50914',
                    edgeLabelBackground: '#262626',
                    lineColor: '#A3A3A3'
                }}
            }});
        </script>
        <style>
            body {{
                background-color: #181818;
                margin: 0;
                padding: 10px;
                display: flex;
                justify-content: center;
                align-items: center;
                font-family: sans-serif;
                overflow: auto;
            }}
            .mermaid {{
                width: 100%;
                display: flex;
                justify-content: center;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
        {codigo_mermaid}
        </div>
    </body>
    </html>
    """
    components.html(html_content, height=alto, scrolling=True)

def exportar_html_autonomo(codigo_mermaid: str, titulo: str) -> str:
    """Genera una página HTML independiente para que el usuario la descargue y abra en cualquier navegador."""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo} — Flujograma FaceFoodChef</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    </script>
    <style>
        body {{
            background-color: #141414;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 30px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        h1 {{ color: #E50914; margin-bottom: 5px; }}
        p {{ color: #a3a3a3; margin-bottom: 30px; }}
        .card {{
            background: #181818;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            max-width: 95%;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <h1>{titulo}</h1>
    <p>Flujograma de preparación de receta generado por FaceFoodChef</p>
    <div class="card">
        <div class="mermaid">
        {codigo_mermaid}
        </div>
    </div>
</body>
</html>"""

# -----------------------------------------------------------------------------
# 8. ENCABEZADO Y MARCA DE LA APLICACIÓN
# -----------------------------------------------------------------------------
st.markdown("""
<div class="brand-container">
    <div>
        <h1 class="brand-title">FaceFoodChef <span class="brand-badge">PRO</span></h1>
        <div class="brand-subtitle">Traductor inteligente de recetas a flujogramas interactivos de ejecución.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 9. BARRA LATERAL (SIDEBAR DE CONFIGURACIÓN)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuración del Sistema")
    
    # Obtener API Key de los Secrets de Streamlit o del campo de entrada
    api_key_secret = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else ""
    
    api_key_input = st.text_input(
        "Google AI Studio API Key",
        value=os.getenv("GEMINI_API_KEY", api_key_secret),
        type="password",
        help="Consigue tu API Key en Google AI Studio (aistudio.google.com)."
    )
    
    st.divider()
    
    st.subheader("🤖 Modelo e Inteligencia")
    modelo_seleccionado = st.selectbox(
        "Modelo de Gemini",
        options=["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        index=0,
        help="Gemini 2.0 Flash es el modelo recomendado por su velocidad para diagramación estricta."
    )
    
    st.divider()
    
    st.subheader("🎨 Personalización de Diagrama")
    orientacion_diagrama = st.radio(
        "Orientación del Flujo",
        options=["Vertical (TD)", "Horizontal (LR)"],
        index=0
    )
    orientacion_code = "TD" if "Vertical" in orientacion_diagrama else "LR"
    
    tema_mermaid_val = st.selectbox(
        "Tema Visual Mermaid",
        options=["dark", "forest", "neutral", "default"],
        index=0
    )
    
    st.divider()
    
    st.subheader("⏱️ Temporizador de Cocina")
    minutos_timer = st.number_input("Minutos", min_value=1, max_value=180, value=5, step=1)
    if st.button("⏲️ Iniciar Cuenta Regresiva", use_container_width=True):
        ph = st.empty()
        segundos_totales = minutos_timer * 60
        while segundos_totales > 0:
            mins, secs = divmod(segundos_totales, 60)
            ph.metric("Tiempo Restante", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
            segundos_totales -= 1
        ph.success("🔔 ¡TIEMPO CONCLUIDO!")

# -----------------------------------------------------------------------------
# 10. ESTRUCTURA PRINCIPAL DE PESTAÑAS (TABS)
# -----------------------------------------------------------------------------
tab_generador, tab_cocina, tab_historial, tab_editor = st.tabs([
    "🍳 Generador de Flujograma",
    "👨‍🍳 Modo Cocina Activo",
    "📜 Plantillas y Ejemplos",
    "🛠️ Editor de Código Mermaid"
])

# -----------------------------------------------------------------------------
# TAB 1: GENERADOR PRINCIPAL
# -----------------------------------------------------------------------------
with tab_generador:
    col_input, col_output = st.columns([1, 1], gap="large")
    
    with col_input:
        st.subheader("📋 Receta de Entrada")
        
        # Selección rápida de receta de ejemplo
        ejemplo_sel = st.selectbox(
            "Cargar receta predefinida:",
            options=["-- Escribir Receta Propia --"] + list(PRESET_RECIPES.keys())
        )
        
        val_inicial = ""
        if ejemplo_sel in PRESET_RECIPES:
            val_inicial = PRESET_RECIPES[ejemplo_sel]
            
        texto_receta = st.text_area(
            "Ingresa los ingredientes y pasos de la receta:",
            value=val_inicial,
            height=380,
            placeholder="Pega aquí tu receta completa..."
        )
        
        btn_generar = st.button("🚀 GENERAR DIAGRAMA DE BLOQUES", use_container_width=True)
        
    with col_output:
        st.subheader("📊 Flujograma de Procesos")
        
        if btn_generar:
            if not api_key_input:
                st.error("❌ Falta la API Key de Google AI Studio. Introdúcela en el panel lateral.")
            elif not texto_receta.strip():
                st.warning("⚠️ Introduce el texto de una receta antes de continuar.")
            else:
                with st.spinner(f"Analizando estructura de procesos con {modelo_seleccionado}..."):
                    try:
                        codigo_mermaid = generar_diagrama_mermaid(texto_receta, api_key_input, modelo_seleccionado)
                        st.session_state["mermaid_code"] = codigo_mermaid
                        st.session_state["last_processed_recipe"] = texto_receta
                        
                        # Guardar en historial
                        st.session_state["recipe_history"].append({
                            "timestamp": time.strftime("%H:%M:%S"),
                            "receta": texto_receta[:40] + "...",
                            "codigo": codigo_mermaid
                        })
                        st.success("✨ ¡Diagrama generado correctamente!")
                    except Exception as err:
                        st.error(f"Error al procesar con Gemini: {err}")
                        
        if st.session_state["mermaid_code"]:
            renderizar_mermaid_html(
                st.session_state["mermaid_code"],
                orientacion=orientacion_code,
                tema_mermaid=tema_mermaid_val,
                alto=580
            )
            
            # Botón para descargar archivo HTML independiente
            html_descargable = exportar_html_autonomo(st.session_state["mermaid_code"], "Receta de Cocina")
            st.download_button(
                label="💾 Descargar Diagrama HTML Autónomo",
                data=html_descargable,
                file_name="diagrama_receta.html",
                mime="text/html",
                use_container_width=True
            )

# -----------------------------------------------------------------------------
# TAB 2: MODO COCINA INTERACTIVO (CHECKLIST)
# -----------------------------------------------------------------------------
with tab_cocina:
    st.subheader("👨‍🍳 Asistente de Ejecución Paso a Paso")
    
    if not st.session_state["last_processed_recipe"]:
        st.info("💡 Genera un diagrama en la pestaña principal para activar la guía interactiva paso a paso.")
    else:
        st.write("Sigue y marca cada instrucción a medida que la completas en la cocina:")
        
        # Extraer líneas de pasos mediante expresiones regulares básicas
        pasos = [p.strip() for p in st.session_state["last_processed_recipe"].split("\n") if len(p.strip()) > 0]
        
        for idx, paso in enumerate(pasos):
            if re.match(r'^(\d+\.|\*|\-)', paso) or "Pasos" in paso or "Ingredientes" in paso:
                col_check, col_text = st.columns([0.08, 0.92])
                with col_check:
                    estado = st.checkbox("", key=f"step_chk_{idx}")
                with col_text:
                    if estado:
                        st.markdown(f"~~{paso}~~")
                    else:
                        st.markdown(f"**{paso}**")

# -----------------------------------------------------------------------------
# TAB 3: PLANTILLAS Y HISTORIAL
# -----------------------------------------------------------------------------
with tab_historial:
    st.subheader("📜 Historial de Diagramas Generados")
    
    if not st.session_state["recipe_history"]:
        st.write("Aún no has generado diagramas en esta sesión.")
    else:
        for item in reversed(st.session_state["recipe_history"]):
            with st.expander(f"🕒 {item['timestamp']} — {item['receta']}"):
                st.code(item['codigo'], language="mermaid")
                if st.button("Cargar este código al editor", key=f"btn_hist_{item['timestamp']}"):
                    st.session_state["mermaid_code"] = item['codigo']
                    st.rerun()

# -----------------------------------------------------------------------------
# TAB 4: EDITOR DIRECTO MERMAID
# -----------------------------------------------------------------------------
with tab_editor:
    st.subheader("🛠️ Editor Manual de Sintaxis Mermaid")
    
    codigo_editado = st.text_area(
        "Edita directamente el código Mermaid.js si deseas ajustar nodos o estilos:",
        value=st.session_state["mermaid_code"],
        height=300
    )
    
    if st.button("🔄 Actualizar Diagrama con Código Editado"):
        st.session_state["mermaid_code"] = codigo_editado
        st.rerun()
        
    if st.session_state["mermaid_code"]:
        st.divider()
        st.subheader("Vista Previa del Editor")
        renderizar_mermaid_html(
            st.session_state["mermaid_code"],
            orientacion=orientacion_code,
            tema_mermaid=tema_mermaid_val,
            alto=500
        )
