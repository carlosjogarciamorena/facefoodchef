import os
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

st.set_page_config(
    page_title="Traductor de Recetas a Diagrama",
    page_icon="🍳",
    layout="wide"
)

SYSTEM_PROMPT = """
Eres un experto en gastronomía e ingeniería de procesos. Convierte la receta facilitada en un diagrama de flujo Mermaid.js (graph TD).

Reglas de generación:
1. Usa la sintaxis 'graph TD'.
2. Identifica ingredientes iniciales como nodos de entrada con corchetes [Ingrediente].
3. Representa acciones o técnicas como procesos con flechas explicativas.
4. Muestra explícitamente las tareas en paralelo (ej. hervir agua mientras se pican los vegetales).
5. Agrega tiempos de cocción, temperaturas o reposos explícitos dentro de los nodos o conectores.
6. Asigna clases de estilo CSS integradas en Mermaid para diferenciar visualmente los tipos de nodo:
   - Ingredientes (fondo verde claro: fill:#e1f5fe,stroke:#0288d1)
   - Acciones de corte/preparación (fondo azul claro: fill:#e8f5e9,stroke:#388e3c)
   - Cocción/Calor (fondo naranja claro: fill:#fff3e0,stroke:#f57c00)
   - Emplatado/Final (fondo amarillo claro: fill:#fffde7,stroke:#fbc02d)
7. Devuelve ÚNICAMENTE el código Mermaid puro, sin bloques Markdown de código (```mermaid) ni texto aclaratorio.
"""

def generar_mermaid(receta_texto: str, api_key: str) -> str:
    """Procesa la receta con OpenAI y devuelve la sintaxis Mermaid."""
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": receta_texto}
        ],
        temperature=0.1
    )
    codigo = response.choices[0].message.content.strip()
    
    # Limpieza de etiquetas sobrantes si el modelo las incluye
    if codigo.startswith("```"):
        lineas = codigo.split("\n")
        codigo = "\n".join([l for l in lineas if not l.startswith("```")])
    return codigo.strip()

def renderizar_mermaid(codigo_mermaid: str, height: int = 650):
    """Renderiza el diagrama dentro de la interfaz usando CDN de Mermaid.js."""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from '[https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs](https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs)';
            mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
        </script>
        <style>
            body {{
                margin: 0;
                background-color: transparent;
                display: flex;
                justify-content: center;
                align-items: center;
            }}
            .mermaid {{
                background: #ffffff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                width: 100%;
                overflow-x: auto;
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
    components.html(html_code, height=height, scrolling=True)

# Interfaz Principal
st.title("🍳 Generador de Flujogramas de Cocina")
st.caption("Estructura cualquier receta paso a paso con tiempos y tareas en paralelo.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_input = st.text_input(
        "OpenAI API Key", 
        type="password", 
        value=os.getenv("OPENAI_API_KEY", ""),
        help="Introduce tu clave de API de OpenAI para procesar el texto."
    )

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Receta de Entrada")
    receta_ejemplo = """Espaguetis a la Carbonara Tradicional

Ingredientes: 200g guanciale, 4 yemas de huevo, 100g queso Pecorino Romano, 320g espaguetis, pimienta negra molida.

Pasos:
1. Cortar el guanciale en tiras gruesas de 1 cm.
2. En una sartén a fuego medio, dorar el guanciale durante 8 minutos hasta que quede crujiente. Retirar del fuego y reservar la grasa líquida sobrante.
3. Poner a hervir 3 litros de agua con sal en una olla grande y cocinar la pasta durante 9 minutos (al dente).
4. Mientras la pasta se cocina, batir las yemas de huevo con el queso Pecorino y abundante pimienta en un bol grande hasta formar una crema densa.
5. Integrar 2 cucharadas de la grasa del guanciale a la mezcla de huevo y queso.
6. Escurrir la pasta reservando media taza del agua caliente de cocción.
7. Verter la pasta directamente en la sartén con el guanciale (fuera del fuego).
8. Añadir la crema de huevo y queso sobre la pasta, junto con un chorrito del agua de cocción reservada. Mezclar de forma enérgica durante 1 minuto para formar una salsa cremosa sin cuajar el huevo.
9. Servir inmediatamente con Pecorino extra por encima."""

    texto_receta = st.text_area("Pega o escribe la receta aquí:", value=receta_ejemplo, height=420)
    boton_generar = st.button("🚀 Generar Diagrama de Bloques", use_container_width=True)

with col2:
    st.subheader("Diagrama de Procesos")

    if boton_generar:
        if not api_key_input:
            st.error("⚠️ Es necesario proporcionar una API Key de OpenAI en la barra lateral.")
        elif not texto_receta.strip():
            st.warning("⚠️ Introduce el texto de una receta antes de continuar.")
        else:
            with st.spinner("Analizando secuencia, tiempos e ingredientes..."):
                try:
                    codigo_generado = generar_mermaid(texto_receta, api_key_input)
                    st.session_state["codigo_mermaid"] = codigo_generado
                except Exception as e:
                    st.error(f"Error al generar el diagrama: {e}")

    if "codigo_mermaid" in st.session_state:
        renderizar_mermaid(st.session_state["codigo_mermaid"])
        with st.expander("🛠️ Ver código de sintaxis Mermaid"):
            st.code(st.session_state["codigo_mermaid"], language="mermaid")
