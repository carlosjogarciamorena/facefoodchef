import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Generador de Diagramas de Recetas", layout="wide")
st.title("🍳 Motor de Diagramas Culinarios")
st.markdown("Convierte cualquier texto de una receta en un **diagrama de bloques (flujo)** visual para cocinar sin perderte.")

# 2. FUNCIÓN PARA DIBUJAR EL DIAGRAMA (MERMAID)
def renderizar_diagrama_mermaid(codigo_mermaid):
    """Renderiza código Mermaid usando un componente HTML/JS incrustado"""
    html_code = f"""
    <div class="mermaid" style="display: flex; justify-content: center; background-color: white; padding: 20px; border-radius: 10px;">
        {codigo_mermaid}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
    """
    components.html(html_code, height=800, scrolling=True)

# 3. BARRA LATERAL (API KEY)
st.sidebar.header("⚙️ Configuración")
api_key = st.sidebar.text_input("🔑 Tu API Key de Gemini:", type="password")

if not api_key:
    st.warning("👈 Por favor, introduce tu API Key de Google Gemini en el menú lateral para empezar.")

# 4. ÁREA DE TEXTO PARA LA RECETA
receta_texto = st.text_area(
    "📝 Pega aquí el texto de tu receta:", 
    height=200, 
    placeholder="Ejemplo: Para hacer una tortilla, primero bate 2 huevos en un bol. En una sartén, pocha media cebolla y 2 patatas cortadas. Mezcla todo y cuaja en la sartén..."
)

# 5. BOTÓN DE PROCESAMIENTO
if st.button("🚀 Generar Diagrama de Bloques", type="primary"):
    if not api_key:
        st.error("Falta la API Key.")
    elif not receta_texto.strip():
        st.error("Por favor, introduce el texto de la receta.")
    else:
        try:
            with st.spinner("🤖 Analizando la receta y dibujando el diagrama..."):
                # Configurar Gemini
                genai.configure(api_key=api_key.strip())
                modelo = genai.GenerativeModel('gemini-1.5-flash')
                
                # Prompt estricto para generar código de diagrama
                prompt = f"""
                Eres un experto ingeniero de procesos culinarios.
                Tu tarea es leer la siguiente receta y convertirla en un diagrama de flujo usando sintaxis de Mermaid.js.
                
                REGLAS ESTRICTAS:
                1. Usa 'graph TD' (diagrama de arriba hacia abajo).
                2. Los ingredientes deben ir en nodos rectangulares, ej: A[2 Huevos]
                3. Las acciones/procesos deben ir en nodos redondeados, ej: B(Batir)
                4. Las convergencias (mezclas) deben ser claras, uniendo varias flechas en un nodo de acción.
                5. DEVUELVE SOLO EL CÓDIGO MERMAID. No uses formato markdown (```mermaid), ni digas "Aquí tienes". Empieza directamente con "graph TD".

                RECETA A ANALIZAR:
                {receta_texto}
                """
                
                respuesta = modelo.generate_content(prompt)
                codigo_generado = respuesta.text.strip()
                
                # Limpieza de seguridad por si la IA añade formato Markdown
                if codigo_generado.startswith("```mermaid"):
                    codigo_generado = codigo_generado[10:]
                if codigo_generado.startswith("```"):
                    codigo_generado = codigo_generado[3:]
                if codigo_generado.endswith("```"):
                    codigo_generado = codigo_generado[:-3]
                    
                codigo_generado = codigo_generado.strip()
                
                # Mostrar el resultado
                st.success("✅ ¡Diagrama generado con éxito!")
                
                # Renderizar la imagen del diagrama
                st.subheader("📊 Diagrama de Flujo de la Receta")
                renderizar_diagrama_mermaid(codigo_generado)
                
                # Mostrar el código por si el usuario quiere copiarlo
                with st.expander("Ver código del diagrama (Avanzado)"):
                    st.code(codigo_generado, language="mermaid")

        except Exception as e:
            st.error(f"❌ Ha ocurrido un error: {e}")
