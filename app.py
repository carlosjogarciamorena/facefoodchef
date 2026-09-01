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
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILO OSCURO
# ==========================================
st.set_page_config(
    page_title="Kitchen Process Studio - Dark Mode",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estética de interfaz oscura (Dark UI) tipo pantalla de cocina industrial
CSS_DARK_THEME = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #090D16;
        color: #F1F5F9;
    }
    
    .stApp {
        background-color: #090D16;
    }
    
    .main-header {
        background: linear-gradient(135deg, #111827 0%, #0F172A 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        border: 1px solid #1E293B;
        border-left: 5px solid #00FF66;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
    }
    
    .main-header h1 {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 800;
        font-size: 2rem;
        margin: 0;
        color: #00FF66;
        text-shadow: 0 0 10px rgba(0, 255, 102, 0.3);
    }
    
    .main-header p {
        color: #94A3B8;
        font-size: 0.95rem;
        margin-top: 0.4rem;
    }

    /* Ajuste de cajas de texto y componentes en tema oscuro */
    .stTextArea textarea, .stSelectbox select {
        background-color: #0F172A !important;
        color: #F8FAFC !important;
        border: 1px solid #334155 !important;
    }

    .stButton>button {
        background: linear-gradient(90deg, #00E5FF 0%, #0088FF 100%);
        color: #000000;
        font-weight: 800;
        border-radius: 8px;
        border: none;
        padding: 0.75rem 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.4);
    }
    
    .stButton>button:hover {
        background: linear-gradient(90deg, #00FF66 0%, #00E5FF 100%);
        box-shadow: 0 0 20px rgba(0, 255, 102, 0.6);
        color: #000;
    }

    .legend-card {
        background-color: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 8px;
        padding: 1rem;
        margin-top: 1rem;
    }
</style>
"""
st.markdown(CSS_DARK_THEME, unsafe_allow_html=True)

# ==========================================
# 2. PROMPT CORE CON ESTILOS DE BORDES NEÓN
# ==========================================
PROMPT_CORE_NEON = (
    "Eres un Ingeniero de Procesos Industriales Gastronómicos y Programador de Software.\n"
    "Tu misión es convertir el texto o imagen de una receta de cocina en un Grafo Dirigido (DAG) ejecutable paso a paso en cocina.\n\n"
    "DEBES DEVOLVER LA RESPUESTA EXCLUSIVAMENTE EN UN BLOQUE JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA:\n\n"
    "{\n"
    '  "nombre_plato": "Nombre del plato",\n'
    '  "tiempo_total_min": 0,\n'
    '  "diagrama_mermaid": "graph TD\\n...",\n'
    '  "pasos_operativos": [\n'
    '    {\n'
    '      "id": "N1",\n'
    '      "fase": "Mise en place / Preparación / Cocción / Emplatado",\n'
    '      "descripcion": "Detalle paso",\n'
    '      "tiempo": "10 min"\n'
    '    }\n'
    '  ]\n'
    "}\n\n"
    "REGLAS OBLIGATORIAS PARA EL DIAGRAMA MERMAID (ESTILO FONDO NEGRO Y BORDES DE COLOR):\n"
    "1. Inicia con la sintaxis `graph TD`.\n"
    "2. Nodos de Ingredientes (Mise en place): Usa bordes redondeados `ID([Ingrediente + Cantidad])`.\n"
    "3. Nodos de Acciones / Mezclas: Usa rectángulos `ID[Acción de Procesado]`.\n"
    "4. Nodos de Tiempos / Temperatura / Fuego: Usa rombos `ID{Tiempo / Fuego / Control}`.\n"
    "5. Nodo Resultado Final: Usa rectángulo doble `ID[[Plato Final Listo]]`.\n"
    "6. Conecta con flechas la secuencia lógica y dónde convergen los ingredientes en recipientes compartidos.\n"
    "7. AL FINAL DEL CÓDIGO MERMAID DEBES INCLUIR OBLIGATORIAMENTE LAS SIGUIENTES DEFINICIONES DE CLASES CON FONDO NEGRO Y BORDES DE COLOR NEÓN:\n\n"
    "   classDef ingrediente fill:#0D1117,stroke:#00FF66,stroke-width:2px,color:#00FF66;\n"
    "   classDef accion fill:#0D1117,stroke:#00E5FF,stroke-width:2px,color:#00E5FF;\n"
    "   classDef control fill:#0D1117,stroke:#FFB300,stroke-width:2px,color:#FFB300;\n"
    "   classDef Alerta fill:#0D1117,stroke:#FF3366,stroke-width:2px,color:#FF3366;\n"
    "   classDef final fill:#0D1117,stroke:#FFD700,stroke-width:3px,color:#FFD700;\n\n"
    "8. Asigna cada clase a sus nodos respetando la sintaxis:\n"
    "   class ING1,ING2 ingrediente;\n"
    "   class ACC1,ACC2 accion;\n"
    "   class CTR1 control;\n"
    "   class FIN1 final;\n"
    "9. NO utilices comillas dentro del texto de los nodos para evitar roturas de sintaxis.\n"
)

# ==========================================
# 3. COMPONENTE HTML/JS (CANVAS NEGRO MERMAID)
# ==========================================
def renderizar_canvas_negro_mermaid(codigo_mermaid: str, alto: int = 620):
    """Renderiza el diagrama sobre un lienzo negro con Javascript nativo (tema oscuro)."""
    codigo_limpio = codigo_mermaid.replace("```mermaid", "").replace("```", "").strip()
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.mjs';
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'dark',
                securityLevel: 'loose',
                themeVariables: {{
                    darkMode: true,
                    background: '#0D1117',
                    mainBkg: '#0D1117',
                    lineColor: '#64748B',
                    textColor: '#F8FAFC'
                }}
            }});
        </script>
        <style>
            body {{
                margin: 0;
                padding: 15px;
                background-color: #0D1117;
                border: 1px solid #1E293B;
                border-radius: 10px;
                display: flex;
                justify-content: center;
                box-shadow: inset 0 0 20px rgba(0,0,0,0.8);
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
    components.html(html_code, height=alto, scrolling=True)

# ==========================================
# 4. LECTURA MULTIFORMATO DE RECETAS
# ==========================================
def extraer_contenido_archivo(uploaded_file):
    nombre = uploaded_file.name.lower()
    if nombre.endswith(".txt"):
        return uploaded_file.read().decode("utf-8"), "texto"
    elif nombre.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        return "".join([p.extract_text() + "\n" for p in reader.pages]), "texto"
    elif nombre.endswith(".docx"):
        doc = docx.Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs]), "texto"
    elif nombre.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return Image.open(uploaded_file), "imagen"
    else:
        raise ValueError("Formato de archivo no soportado.")

# ==========================================
# 5. INTEGRACIÓN GEMINI API (google-genai)
# ==========================================
def procesar_receta_core(api_key: str, modelo: str, contenido, tipo_contenido: str):
    client = genai.Client(api_key=api_key)
    
    if tipo_contenido == "texto":
        contents = [PROMPT_CORE_NEON, "\n\nRECETA EN TEXTO:\n" + contenido]
    else:
        contents = [PROMPT_CORE_NEON, "\n\nRECETA EN IMAGEN:", contenido]
        
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
# 6. PANEL LATERAL (CONTROL BAR)
# ==========================================
st.sidebar.markdown("<h2 style='color:#00FF66; font-family: monospace;'>⚡ CONTROL CORE</h2>", unsafe_allow_html=True)

api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input(
    "API Key (Gemini):",
    value=api_key_env,
    type="password"
)

modelo_seleccionado = st.sidebar.selectbox(
    "Modelo IA:",
    options=["gemini-3.6-flash", "gemini-3.6-pro"],
    index=0
)

st.sidebar.markdown("""
<div class="legend-card">
    <h4 style="margin-top:0; color:#F8FAFC;">🎨 Codificación Visual Neón</h4>
    <p style="color:#00FF66; margin:4px 0;">🟩 <b>Verde:</b> Ingrediente / Entrada</p>
    <p style="color:#00E5FF; margin:4px 0;">🟦 <b>Azul:</b> Acción / Mezcla</p>
    <p style="color:#FFB300; margin:4px 0;">🟨 <b>Amarillo:</b> Fuego / Tiempo</p>
    <p style="color:#FF3366; margin:4px 0;">🟥 <b>Rojo:</b> Alerta Crítica</p>
    <p style="color:#FFD700; margin:4px 0;">🟨 <b>Dorado:</b> Resultado Final</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7. INTERFAZ PRINCIPAL
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>🎛️ KITCHEN PROCESS DIAGRAMMER</h1>
    <p>Traductor de Recetas a Grafo Dirigido Ejecutable paso a paso (Modo Oscuro & Bordes de Color)</p>
</div>
""", unsafe_allow_html=True)

col_in, col_out = st.columns([1, 1.25])

with col_in:
    st.markdown("### 📄 1. Receta de Entrada")
    metodo = st.radio("Origen de la Receta:", ["Cargar Archivo (PDF, DOCX, TXT, PNG/JPG)", "Pegar Texto"])
    
    contenido_receta = None
    tipo_entrada = "texto"
    
    if metodo == "Cargar Archivo (PDF, DOCX, TXT, PNG/JPG)":
        archivo = st.file_uploader("Arrastra o selecciona el documento:", type=["txt", "pdf", "docx", "png", "jpg", "jpeg", "webp"])
        if archivo:
            try:
                contenido_receta, tipo_entrada = extraer_contenido_archivo(archivo)
                if tipo_entrada == "texto":
                    st.text_area("Texto interpretado:", value=contenido_receta, height=250, disabled=True)
                else:
                    st.image(contenido_receta, caption="Vista previa del documento", use_container_width=True)
            except Exception as e:
                st.error(f"Error al procesar archivo: {e}")
    else:
        texto_input = st.text_area(
            "Pega aquí la receta completa:",
            height=320,
            placeholder="Ingredientes:\n- 500g Arroz\n- 1L Caldo de Pescado...\n\nElaboración:\n1. Dorar el marisco en la paella..."
        )
        if texto_input.strip():
            contenido_receta = texto_input
            tipo_entrada = "texto"
            
    btn_generar = st.button("🚀 COMPILAR DIAGRAMA DE BLOQUES", use_container_width=True)

with col_out:
    st.markdown("### 🖥️ 2. Panel de Ejecución en Cocina")
    
    if btn_generar:
        if not api_key:
            st.error("⚠️ Falta la API Key de Gemini en el panel lateral.")
        elif not contenido_receta:
            st.warning("⚠️ Debes proporcionar una receta (texto o archivo).")
        else:
            with st.spinner("⚡ Compilando grafo de bloques con diseño neón..."):
                try:
                    resultado = procesar_receta_core(api_key, modelo_seleccionado, contenido_receta, tipo_entrada)
                    st.session_state["core_resultado"] = resultado
                except Exception as e:
                    st.error(f"❌ Error durante el procesamiento: {str(e)}")

    if "core_resultado" in st.session_state:
        res = st.session_state["core_resultado"]
        
        st.markdown(f"#### 🍽️ {res.get('nombre_plato', 'Receta Procesada')}")
        if res.get("tiempo_total_min"):
            st.markdown(f"⏱️ **Tiempo estimado:** `{res.get('tiempo_total_min')} minutos`")
            
        t_diagrama, t_pasos, t_codigo = st.tabs(["🎛️ Diagrama Neón (Canvas Negro)", "📋 Pasos Secuenciales", "💻 Código Mermaid"])
        
        with t_diagrama:
            codigo_mermaid = res.get("diagrama_mermaid", "")
            if codigo_mermaid:
                renderizar_canvas_negro_mermaid(codigo_mermaid, alto=620)
            else:
                st.warning("No se generó el código del diagrama.")
                
        with t_pasos:
            pasos = res.get("pasos_operativos", [])
            if pasos:
                st.dataframe(pd.DataFrame(pasos), use_container_width=True)
                
        with t_codigo:
            st.code(res.get("diagrama_mermaid", ""), language="mermaid")
            st.download_button(
                label="📥 Descargar archivo .mmd",
                data=res.get("diagrama_mermaid", ""),
                file_name="diagrama_receta_neon.mmd",
                mime="text/plain"
            )
