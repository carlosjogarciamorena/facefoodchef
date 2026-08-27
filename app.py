import os
import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(page_title="FaceFoodChef - Diagramas", page_icon="🍳", layout="wide")

ESTILO_NETFLIX = """
<style>
    .stApp { background-color: #141414; color: #E5E5E5; }
    h1, h2, h3 { color: #FFFFFF !important; font-weight: 700; }
    .brand-title { color: #E50914; font-size: 2.5rem; font-weight: 900; text-transform: uppercase; margin-bottom: 0px; }
    .brand-subtitle { color: #A3A3A3; font-size: 1.1rem; margin-bottom: 20px; }
    div.stButton > button { background-color: #E50914 !important; color: white !important; font-weight: bold !important; border: none !important; padding: 0.5rem 1rem !important; }
    div.stButton > button:hover { background-color: #F40612 !important; }
    .stTextArea textarea, .stTextInput input { background-color: #232323 !important; color: white !important; border: 1px solid #3d3d3d !important; }
</style>
"""
st.markdown(ESTILO_NETFLIX, unsafe_allow_html=True)

# 2. LÓGICA DE INTELIGENCIA ARTIFICIAL
PROMPT_SISTEMA = """
Eres un experto en procesos gastronómicos. Convierte la receta facilitada en un diagrama de flujo en sintaxis Mermaid.js (graph TD).
Reglas:
1. Usa 'graph TD'.
2. Ingredientes como nodos iniciales: [Ingrediente].
3. Técnicas como procesos con tiempos y temperaturas: (Hornear | 180°C - 20 min).
4. Agrupa visualmente tareas en paralelo.
5. Termina en el plato final: ((Plato Servido)).
6. Aplica estos estilos exactos:
   classDef ing fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#fff;
   classDef proc fill:#262626,stroke:#ffffff,stroke-width:1px,color:#fff;
   classDef final fill:#7f1d1d,stroke:#ef4444,stroke-width:2px,color:#fff;
7. Devuelve ÚNICAMENTE el código puro de Mermaid. Sin explicaciones ni etiquetas markdown (```).
"""

def generar_diagrama(receta: str, api_key: str) -> str:
    genai.configure(api_key=api_key)
    
    # Actualizado a la versión requerida por la API actual
    nombre_modelo = "models/gemini-3.6-flash" 
    
    try:
        modelo = genai.GenerativeModel(nombre_modelo) 
        respuesta = modelo.generate_content(
            f"{PROMPT_SISTEMA}\n\nRECETA:\n{receta}", 
            generation_config={"temperature": 0.1}
        )
        
        codigo = respuesta.text.strip()
        if "```" in codigo:
            codigo = "\n".join([linea for linea in codigo.split("\n") if not linea.strip().startswith("```")])
        return codigo.strip()
        
    except Exception as e:
        # Si falla, listamos los modelos disponibles para diagnóstico
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        raise ValueError(f"Error con el modelo {nombre_modelo}. Modelos soportados por tu API Key:\n" + "\n".join(modelos_disponibles))

# 3. LÓGICA DE RENDERIZADO VISUAL
def mostrar_diagrama(codigo_mermaid: str):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script type="module">
            import mermaid from '[https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs](https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs)';
            mermaid.initialize({{ startOnLoad: true, theme: 'dark', themeVariables: {{ background: '#181818', primaryColor: '#E50914' }} }});
        </script>
        <style>body {{ background: #141414; margin: 0; display: flex; justify-content: center; }} .mermaid {{ width: 100%; text-align: center; }}</style>
    </head>
    <body><div class="mermaid">{codigo_mermaid}</div></body>
    </html>
    """
    components.html(html, height=600, scrolling=True)

# 4. INTERFAZ DE USUARIO
st.markdown('<p class="brand-title">FaceFoodChef</p>', unsafe_allow_html=True)
st.markdown('<p class="brand-subtitle">Traductor directo de recetas a diagramas de bloques.</p>', unsafe_allow_html=True)

# Panel de API Key
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_input = st.text_input("Google AI Studio API Key", type="password", help="Pega aquí tu API Key de Gemini.")

# Interfaz Principal a dos columnas
col_izq, col_der = st.columns(2, gap="large")

with col_izq:
    st.subheader("📋 Pega tu Receta")
    receta_texto = st.text_area("Ingredientes y Pasos:", height=350, placeholder="Ej: 2 huevos, 1 patata. 1. Pelar patata. 2. Freír. 3. Batir huevos. 4. Mezclar y cuajar.")
    btn_procesar = st.button("🚀 CREAR DIAGRAMA", use_container_width=True)

with col_der:
    st.subheader("📊 Diagrama de Cocina")
    
    if btn_procesar:
        if not api_key_input:
            st.error("❌ Falta la API Key en la barra lateral.")
        elif not receta_texto:
            st.warning("⚠️ Escribe una receta primero.")
        else:
            with st.spinner("Procesando receta..."):
                try:
                    codigo = generar_diagrama(receta_texto, api_key_input)
                    st.session_state["diagrama"] = codigo
                except Exception as e:
                    st.error(f"Error en la API: {e}")

    # Mostrar diagrama si ya existe en la sesión
    if "diagrama" in st.session_state:
        mostrar_diagrama(st.session_state["diagrama"])
        with st.expander("Ver código Mermaid"):
            st.code(st.session_state["diagrama"], language="mermaid")
