import os
import re
import streamlit as st
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Cargar variables de entorno desde un archivo .env si existe
load_dotenv()

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Traductor de Recetas a Diagrama de Bloques",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 Traductor de Recetas a Diagrama de Bloques")
st.markdown("""
Esta aplicación transforma el texto plano de una receta de cocina en un **diagrama de flujo/bloques** claro,
secuencial y ejecutable para que puedas cocinar siguiendo paso a paso el proceso.
""")

# --- BARRA LATERAL: Configuración de API Key ---
st.sidebar.header("🔑 Configuración")

# Intentar obtener la API Key del entorno o permitir al usuario ingresarla
env_api_key = os.getenv("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "API Key de Google Gemini:",
    value=env_api_key,
    type="password",
    help="Consigue tu API Key en https://aistudio.google.com/"
)

# Selección del modelo
modelo_seleccionado = st.sidebar.selectbox(
    "Modelo de Gemini:",
    options=["gemini-2.5-flash", "gemini-1.5-flash"],
    index=0
)

# --- PROMPT DEL SISTEMA ---
PROMPT_SISTEMA = """
Eres un experto en modelado de procesos, ingeniería de alimentos y cocina profesional.
Tu misión es transformar el texto de una receta de cocina en un diagrama de bloques ejecutable escrito en código Mermaid.js (sintaxis `graph TD`).

REGLAS ESTRICTAS PARA EL DIAGRAMA:
1. Identifica TODOS los ingredientes y ponlos al inicio como nodos rectangulares redondeados con bordes claros o forma de entrada. Formato: `id_ingrediente([Nombre del Ingrediente / Cantidad])`.
2. Las acciones/procesos deben ser nodos rectangulares: `id_accion[Acción: Nombre / Tiempo / Tª o Fuego]`.
3. Si hay decisiones o comprobaciones (ej. ¿está dorado?, ¿está tierno?), usa nodos en forma de rombo: `id_decision{¿Comprobación?}` con salidas `-->|Sí|` y `-->|No|`.
4. Muestra claramente la convergencia de ingredientes y mezclas. Varias flechas deben unirse en una sola acción cuando se mezclan componentes.
5. Usa identificadores de nodos limpios y únicos (ej. A1, A2, B1, C1).
6. Asigna estilos CSS visuales usando classDef de Mermaid:
   - Ingredientes: fondo verde claro o azul suave (`fill:#d4edda,stroke:#28a745,color:#155724`).
   - Acciones/Cocción: fondo naranja o amarillo suave (`fill:#fff3cd,stroke:#ffc107,color:#856404`).
   - Resultado Final: fondo rosa o verde intenso (`fill:#d1ecf1,stroke:#17a2b8,color:#0c5460`).
7. Devuelve ÚNICAMENTE el bloque de código Mermaid delimitado por ```mermaid y ```. No agregues explicaciones adicionales fuera del código.
"""

def limpiar_codigo_mermaid(texto_respuesta: str) -> str:
    """Extrae únicamente el código dentro del bloque ```mermaid ... ```"""
    patron = r"```mermaid\s*(.*?)\s*```"
    coincidencia = re.search(patron, texto_respuesta, re.DOTALL)
    if coincidencia:
        return coincidencia.group(1).strip()
    # Si la IA no colocó los delimitadores correctamente, devolver el texto completo
    return texto_respuesta.replace("```mermaid", "").replace("```", "").strip()

# --- INTERFAZ PRINCIPAL ---
col_izquierda, col_derecha = st.columns([1, 1])

receta_ejemplo = """Tortilla de patatas tradicional:
1. Pelar y cortar 4 patatas grandes y 1 cebolla grande en láminas finas.
2. Calentar 300ml de aceite de oliva en una sartén y freír la patata con la cebolla a fuego medio-bajo durante 18 minutos hasta que estén blandas.
3. Mientras se fríen las patatas, batir 6 huevos M en un bol grande con una pizca de sal.
4. Escurrir bien el aceite de las patatas y la cebolla mediante un colador.
5. Verter las patatas y cebolla escurridas en el bol con el huevo batido. Mezclar bien y dejar reposar 5 minutos.
6. Calentar una sartén antiadherente con unas gotas de aceite. Cuajar la mezcla durante 2.5 minutos por el primer lado.
7. Dar la vuelta a la tortilla con un plato y cuajar por el otro lado durante 1.5 minutos más a fuego medio.
"""

with col_izquierda:
    st.subheader("📝 Receta de cocina")
    texto_receta = st.text_area(
        "Pega aquí la receta completa (ingredientes y pasos):",
        value=receta_ejemplo,
        height=380
    )
    boton_generar = st.button("🚀 Generar Diagrama de Bloques", use_container_width=True)

with col_derecha:
    st.subheader("📊 Diagrama de Bloques")
    
    if boton_generar:
        if not api_key_input:
            st.error("⚠️ Por favor, ingresa una API Key válida en la barra lateral.")
        elif not texto_receta.strip():
            st.warning("⚠️ Por favor, escribe o pega el texto de una receta.")
        else:
            with st.spinner("Procesando receta y estructurando el diagrama..."):
                try:
                    # Inicializar el cliente oficial de Google GenAI
                    client = genai.Client(api_key=api_key_input)
                    
                    # Realizar la llamada al modelo seleccionado
                    response = client.models.generate_content(
                        model=modelo_seleccionado,
                        contents=f"{PROMPT_SISTEMA}\n\nReceta a procesar:\n{texto_receta}",
                        config=types.GenerateContentConfig(
                            temperature=0.2
                        )
                    )
                    
                    # Extraer y limpiar el código Mermaid
                    codigo_mermaid = limpiar_codigo_mermaid(response.text)
                    
                    # Renderizar el diagrama usando el componente nativo de Streamlit
                    st.mermaid(codigo_mermaid)
                    
                    # Expandible para ver/copiar el código fuente
                    with st.expander("📄 Ver código Mermaid fuente"):
                        st.code(codigo_mermaid, language="mermaid")
                        
                except Exception as e:
                    st.error(f"❌ Error durante el procesamiento: {str(e)}")
