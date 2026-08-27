import os
import streamlit as st
import streamlit.components.v1 as components

# Configuración de página
st.set_page_config(
    page_title="FaceFoodChef — Recetas en Diagrama",
    page_icon="🍿",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS con estética tipo Netflix
NETFLIX_STYLE = """
<style>
    /* Fondo principal y textos */
    .stApp {
        background-color: #141414;
        color: #E5E5E5;
    }
    
    /* Encabezados y títulos */
    h1, h2, h3, h4 {
        color: #FFFFFF !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
    }
    
    /* Marca principal */
    .brand-title {
        color: #E50914;
        font-size: 2.8rem;
        font-weight: 900;
        letter-spacing: 1px;
        margin-bottom: 0px;
        text-transform: uppercase;
    }
    .brand-subtitle {
        color: #B3B3B3;
        font-size: 1.1rem;
        margin-bottom: 25px;
    }

    /* Botones estilo Netflix */
    div.stButton > button {
        background-color: #E50914 !important;
        color: #FFFFFF !important;
        font-weight: bold !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:hover {
        background-color: #F40612 !important;
        transform: scale(1.02);
    }

    /* Cajas de texto y campos */
    .stTextArea textarea, .stTextInput input {
        background-color: #2F2F2F !important;
        color: #FFFFFF !important;
        border: 1px solid #404040 !important;
        border-radius: 4px !important;
    }
    
    /* Contenedor del Diagrama */
    .diagram-container {
        background-color: #181818;
        border-radius: 8px;
        padding: 20px;
        border: 1px solid #333333;
    }
</style>
"""
st.markdown(NETFLIX_STYLE, unsafe_allow_html=True)

# Manejo seguro de importación de OpenAI
try:
    from openai import OpenAI
except ModuleNotFoundError:
    st.error("⚠️ La librería `openai` no está instalada. Asegúrate de añadir `requirements.txt` a tu repositorio.")
    st.stop()

SYSTEM_PROMPT = """
Eres un ingeniero de procesos gastronómicos. Tu único objetivo es transformar el texto de una receta en un diagrama de flujo en sintaxis Mermaid.js (graph TD) listo para ejecutar.

Reglas de salida:
1. Usa 'graph TD'.
2. Representa ingredientes como nodos iniciales: [Ingrediente].
3. Modela las técnicas de cocina como nodos centrales con tiempos explícitos (ej. "Hornear | 180°C - 20 min").
4. Agrupa visualmente los procesos que se pueden realizar en paralelo.
5. Usa las clases de estilo para personalizar los nodos con estética oscura:
   classDef ing fill:#221f1f,stroke:#e50914,stroke-width:2px,color:#fff;
   classDef proc fill:#333333,stroke:#ffffff,stroke-width:1px,color:#fff;
   classDef final fill:#e50914,stroke:#ffffff,stroke-width:2px,color:#fff;
6. Aplica class ID ing a ingredientes, class ID proc a procesos y class ID final al plato terminado.
7. Devuelve ÚNICAMENTE el código Mermaid puro dentro de la respuesta, sin etiquetas Markdown ```mermaid.
"""

def generar_diagrama_mermaid(receta: str, api_key: str) -> str:
    """Consulta a OpenAI para obtener la representación en Mermaid."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": receta}
        ],
        temperature=0.1
    )
    codigo = response.choices[0].message.content.strip()
    if codigo.startswith("```"):
        codigo = "\n".join([linea for linea in codigo.split("\n") if not linea.startswith("```")])
    return codigo.strip()

def renderizar_mermaid_dark(codigo_mermaid: str, altura: int = 600):
    """Renderiza el diagrama utilizando el CDN de Mermaid con tema Dark."""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from '[https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs](https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs)';
            mermaid.initialize({{ 
                startOnLoad: true, 
                theme: 'dark',
                themeVariables: {{
                    darkMode: true,
                    background: '#181818',
                    primaryColor: '#E50914',
                    lineColor: '#FFFFFF'
                }}
            }});
        </script>
        <style>
            body {{
                background-color: #181818;
                margin: 0;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .mermaid {{
                width: 100%;
                text-align: center;
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
    components.html(html_code, height=altura, scrolling=True)

# Encabezado
st.markdown('<div class="brand-title">FaceFoodChef</div>', unsafe_allow_html=True)
st.markdown('<div class="brand-subtitle">Convierte cualquier receta en una secuencia gráfica de ejecución.</div>', unsafe_allow_html=True)

# Barra Lateral (Configuración)
with st.sidebar:
    st.header("⚙️ Panel de Control")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Introduce tu clave de API de OpenAI."
    )
    st.info("Asegúrate de configurar `OPENAI_API_KEY` en los Secrets de Streamlit Cloud para omitir este paso.")

# Interfaz Principal
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("📋 Receta Original")
    receta_defecto = """Pizza Margherita Casera

Ingredientes: 250g harina de fuerza, 150ml agua templada, 5g levadura fresca, 100g tomate triturado, 125g mozzarella fresca, hojas de albahaca fresca, aceite de oliva, sal.

Pasos:
1. Disolver la levadura en el agua templada y dejar reposar 5 minutos.
2. En un bol, mezclar la harina con la sal, añadir el agua con levadura y amasar durante 10 minutos hasta obtener una masa lisa.
3. Dejar fermentar la masa tapada en un bol durante 2 horas hasta que doble su volumen.
4. Mientras la masa fermenta, sazonar el tomate triturado con sal y un chorrito de aceite de oliva.
5. Precalentar el horno a 250°C.
6. Estirar la masa sobre papel de horno formando un disco.
7. Extender la salsa de tomate sobre la base y añadir la mozzarella troceada.
8. Hornear a 250°C durante 8-10 minutos hasta que los bordes estén dorados y el queso fundido.
9. Decorar con albahaca fresca antes de servir."""

    texto_receta = st.text_area("Ingresa o edita el texto de la receta:", value=receta_defecto, height=400)
    procesar = st.button("🎬 GENERAR DIAGRAMA", use_container_width=True)

with col_right:
    st.subheader("📊 Flujograma de Cocina")

    if procesar:
        if not api_key:
            st.error("❌ Falta la OpenAI API Key. Ingrésala en la barra lateral.")
        elif not texto_receta.strip():
            st.warning("⚠️ Introduce una receta válida.")
        else:
            with st.spinner("Analizando pasos, tiempos y tareas paralelas..."):
                try:
                    codigo = generar_diagrama_mermaid(texto_receta, api_key)
                    st.session_state["mermaid_code"] = codigo
                except Exception as err:
                    st.error(f"Error al procesar: {err}")

    if "mermaid_code" in st.session_state:
        renderizar_mermaid_dark(st.session_state["mermaid_code"])
        with st.expander("Ver sintaxis Mermaid generada"):
            st.code(st.session_state["mermaid_code"], language="mermaid")
