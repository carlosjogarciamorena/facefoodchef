import os
import json
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
from pypdf import PdfReader
import docx
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO CLARO Y LIMPIO
# ==========================================
st.set_page_config(
    page_title="Generador de Diagramas de Procesos Gastronómicos",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo editorial moderno, profesional y sobre fondo claro (sin estética semáforo/oscura)
CSS_CUSTOM = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #1E293B;
    }
    
    .main-header {
        background-color: #FFFFFF;
        padding: 1.5rem 0rem;
        border-bottom: 2px solid #E2E8F0;
        margin-bottom: 2rem;
    }
    
    .main-header h1 {
        font-weight: 700;
        font-size: 2rem;
        color: #0F172A;
        margin: 0;
    }
    
    .main-header p {
        color: #64748B;
        font-size: 1rem;
        margin-top: 0.3rem;
    }

    .stButton>button {
        background-color: #2563EB;
        color: white;
        font-weight: 600;
        border-radius: 6px;
        border: none;
        padding: 0.6rem 1.2rem;
    }
    
    .stButton>button:hover {
        background-color: #1D4ED8;
        color: white;
    }

    .info-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
</style>
"""
st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

# ==========================================
# 2. PROMPT ORIENTADO A DIAGRAMA OPERATIVO
# ==========================================
PROMPT_DIAGRAMADOR_RECETAS = (
    "Eres un Ingeniero de Procesos y Chef Ejecutivo especializado en diagramación industrial de recetas.\n"
    "Tu tarea es transformar el texto de una receta en un Grafo Dirigido (DAG) claro y preciso para que un cocinero pueda ejecutar el plato siguiendo únicamente el diagrama.\n\n"
    "DEBES DEVOLVER TU RESPUESTA EXCLUSIVAMENTE EN UN BLOQUE JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA:\n\n"
    "{\n"
    '  "nombre_plato": "Nombre del plato",\n'
    '  "tiempo_total_min": 0,\n'
    '  "diagrama_mermaid": "graph TD\\n...",\n'
    '  "resumen_pasos": [\n'
    '    {\n'
    '      "paso": 1,\n'
    '      "fase": "Mise en place / Preparación / Cocción / Emplatado",\n'
    '      "descripcion": "Detalle operativo",\n'
    '      "tiempo": "10 min"\n'
    '    }\n'
    '  ]\n'
    "}\n\n"
    "REGLAS ESTRUCTURALES DEL DIAGRAMA MERMAID:\n"
    "1. Usa sintaxis `graph TD`.\n"
    "2. Nodos de Ingredientes de Entrada: Usa bordes redondeados `id([Ingrediente + Cantidad])`.\n"
    "3. Nodos de Acciones / Tareas: Usa rectángulos `id[Acción + Herramienta]`.\n"
    "4. Nodos de Tiempos / Temperaturas / Control: Usa rombos `id{Tiempo / Fuego / Condición}`.\n"
    "5. Nodo Final: Usa `id[[Resultado final: Nombre del Plato]]`.\n"
    "6. Conecta adecuadamente cómo convergen los ingredientes en recipientes compartidos.\n"
    "7. Agrega los siguientes estilos de colores funcionales al final del diagrama:\n"
    "   classDef ingrediente fill:#E6F4EA,stroke:#34A853,stroke-width:1px,color:#137333;\n"
    "   classDef accion fill:#E8F0FE,stroke:#4285F4,stroke-width:1px,color:#174EA6;\n"
    "   classDef control fill:#FEF7E0,stroke:#FBBC04,stroke-width:1px,color:#B06000;\n"
    "   classDef final fill:#FCE8E6,stroke:#EA4335,stroke-width:2px,color:#C5221F;\n"
    "8. Aplica las clases a los nodos correspondientes mediante `class ID_NODE ingrediente;`, etc.\n"
    "9. NO USES comillas dobles ni caracteres especiales dentro de los nombres de los nodos.\n"
)

# ==========================================
# 3. COMPONENTE HTML/JS NATIVO PARA MERMAID
# ==========================================
def renderizar_diagrama_mermaid(codigo_mermaid: str, alto: int = 600):
    """Renderiza el diagrama Mermaid de forma limpia usando el motor JS oficial."""
    codigo_limpio = codigo_mermaid.replace("```mermaid", "").replace("```", "").strip()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.mjs';
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'neutral',
                securityLevel: 'loose',
                flowchart: {{ useMaxWidth: true, htmlLabels: true, curve: 'basis' }}
            }});
        </script>
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 10px;
                background-color: #FFFFFF;
                display: flex;
                justify-content: center;
            }}
            .mermaid {{
                width: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
            {codigo_limpio}
        </div>
    </body>
    </html>
    """
    components.html(html_content, height=alto, scrolling=True)

# ==========================================
# 4. EXTRACCIÓN Y LECTURA MULTIFORMATO
# ==========================================
def extraer_texto_de_archivo(uploaded_file):
    nombre = uploaded_file.name.lower()
    if nombre.endswith(".txt"):
        return uploaded_file.read().decode("utf-8"), "texto"
    elif nombre.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        texto = "".join([page.extract_text() + "\n" for page in reader.pages])
        return texto, "texto"
    elif nombre.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs]), "texto"
    elif nombre.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return Image.open(uploaded_file), "imagen"
    else:
        raise ValueError("Formato de archivo no compatible.")

# ==========================================
# 5. LLAMADA A LA API DE GEMINI (SDK GenAI)
# ==========================================
def generar_diagrama_receta(api_key: str, modelo: str, contenido, tipo_contenido: str):
    client = genai.Client(api_key=api_key)
    
    if tipo_contenido == "texto":
        contents = [PROMPT_DIAGRAMADOR_RECETAS, "\n\nTEXTO DE LA RECETA:\n" + contenido]
    else:
        contents = [PROMPT_DIAGRAMADOR_RECETAS, "\n\nIMAGEN DE LA RECETA:", contenido]
        
    response = client.models.generate_content(
        model=modelo,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    return json.loads(response.text)

# ==========================================
# 6. PANEL LATERAL DE CONFIGURACIÓN
# ==========================================
st.sidebar.title("⚙️ Configuración")

api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "Gemini API Key:",
    value=api_key_env,
    type="password",
    help="Introduce tu clave API de Google AI Studio"
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo IA:",
    options=["gemini-3.6-flash", "gemini-3.6-pro"],
    index=0
)

st.sidebar.divider()
st.sidebar.markdown("""
**Leyenda del Diagrama:**
* 🟢 **Verde:** Ingredientes / Entradas
* 🔵 **Azul:** Acciones / Meclas / Cortar
* 🟧 **Amarillo/Naranja:** Tiempos / Fuego / Control
* 🔴 **Rojo:** Producto Final
""")

# ==========================================
# 7. INTERFAZ PRINCIPAL
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>👨‍🍳 Generador de Diagramas de Bloques para Recetas</h1>
    <p>Convierte cualquier texto o imagen de receta en un diagrama de flujo operativo ejecutable en cocina.</p>
</div>
""", unsafe_allow_html=True)

col_entrada, col_salida = st.columns([1, 1.3])

with col_entrada:
    st.subheader("1. Entrada de la Receta")
    metodo_entrada = st.radio("Fuente de datos:", ["Escribir / Pegar Texto", "Cargar Archivo (PDF, DOCX, TXT, Imagen)"])
    
    contenido_receta = None
    tipo_entrada = "texto"
    
    if metodo_entrada == "Cargar Archivo (PDF, DOCX, TXT, Imagen)":
        archivo = st.file_uploader("Selecciona el archivo:", type=["txt", "pdf", "docx", "png", "jpg", "jpeg", "webp"])
        if archivo:
            try:
                contenido_receta, tipo_entrada = extraer_texto_de_archivo(archivo)
                if tipo_entrada == "texto":
                    st.text_area("Vista previa del texto:", value=contenido_receta, height=220, disabled=True)
                else:
                    st.image(contenido_receta, caption="Imagen cargada", use_container_width=True)
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")
    else:
        texto_manual = st.text_area(
            "Pega la receta aquí:",
            height=300,
            placeholder="Ejemplo:\nIngredientes:\n- 400g de pasta\n- 200g de panceta\n- 4 yemas de huevo\n- 100g de queso pecorino\n\nPasos:\n1. Hervir agua con sal y cocer la pasta..."
        )
        if texto_manual.strip():
            contenido_receta = texto_manual
            tipo_entrada = "texto"
            
    btn_generar = st.button("🚀 Generar Diagrama de Bloques", use_container_width=True)

with col_salida:
    st.subheader("2. Diagrama Operativo de Ejecución")
    
    if btn_generar:
        if not api_key:
            st.error("⚠️ Introduce tu API Key de Gemini en la barra lateral.")
        elif not contenido_receta:
            st.warning("⚠️ Debes ingresar el texto o cargar un archivo con la receta.")
        else:
            with st.spinner("Analizando la receta y construyendo el diagrama de bloques..."):
                try:
                    resultado = generar_diagrama_receta(api_key, modelo_seleccionado, contenido_receta, tipo_entrada)
                    st.session_state["resultado_receta"] = resultado
                except Exception as e:
                    st.error(f"Error procesando la solicitud: {str(e)}")

    if "resultado_receta" in st.session_state:
        res = st.session_state["resultado_receta"]
        
        st.markdown(f"### 🍽️ {res.get('nombre_plato', 'Plato traducido')}")
        if res.get("tiempo_total_min"):
            st.caption(f"⏱️ Tiempo estimado total: {res.get('tiempo_total_min')} minutos")
            
        tab_diagrama, tab_tabla, tab_codigo = st.tabs(["📌 Diagrama de Flujo", "📋 Desglose de Pasos", "💻 Código Mermaid"])
        
        with tab_diagrama:
            codigo_mermaid = res.get("diagrama_mermaid", "")
            if codigo_mermaid:
                renderizar_diagrama_mermaid(codigo_mermaid, alto=580)
            else:
                st.warning("No se pudo estructurar el diagrama.")
                
        with tab_tabla:
            pasos = res.get("resumen_pasos", [])
            if pasos:
                st.dataframe(pd.DataFrame(pasos), use_container_width=True)
                
        with tab_codigo:
            st.code(res.get("diagrama_mermaid", ""), language="mermaid")
            st.download_button(
                label="Descargar sintaxis .mmd",
                data=res.get("diagrama_mermaid", ""),
                file_name="diagrama_receta.mmd",
                mime="text/plain"
            )
