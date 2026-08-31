import os
import re
import json
import time
import base64
import pandas as pd
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="Kitchen Process Studio & Diagram Translator",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS avanzados para interfaz técnica gastronómica
CSS_CUSTOM = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        padding: 1.8rem 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
        border-bottom: 4px solid #F59E0B;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        font-weight: 800;
        font-size: 2.2rem;
        margin: 0;
        color: #F8FAFC;
    }
    .main-header p {
        color: #94A3B8;
        font-size: 1rem;
        margin-top: 0.4rem;
        margin-bottom: 0;
    }
    .chef-recommendation-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 6px solid #D97706;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .critical-alert-card {
        background-color: #FEF2F2;
        border: 1px solid #FECACA;
        border-left: 6px solid #EF4444;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .metric-container {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
    }
    .metric-label {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #F1F5F9;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        color: white !important;
    }
</style>
"""
st.markdown(CSS_CUSTOM, unsafe_allow_html=True)

# ==========================================
# 2. PROMPTS DE INGENIERÍA Y GASTRONOMÍA
# ==========================================
# Se construye usando concatenación estricta para evitar conflictos de llaves en f-strings
PROMPT_INGENIERIA_PROCESOS = (
    "Eres un Chef Ejecutivo Michelin e Ingeniero de Procesos Industriales Gastronómicos.\n"
    "Tu objetivo es convertir el texto de una receta en un Grafo Dirigido Acíclico (DAG) que describa la ejecución de la cocina.\n\n"
    "DEBES DEVOLVER TU RESPUESTA EN UN ÚNICO BLOQUE JSON VÁLIDO CON LA SIGUIENTE ESTRUCTURA:\n\n"
    "{\n"
    '  "resumen_ejecutivo": {\n'
    '    "nombre_plato": "Nombre del plato",\n'
    '    "tiempo_total_estimado_min": 0,\n'
    '    "tiempo_manos_a_la_obra_min": 0,\n'
    '    "dificultad_tecnica": "Baja / Media / Alta / Profesional",\n'
    '    "herramientas_clave": ["utensilio 1", "utensilio 2"]\n'
    '  },\n'
    '  "diagrama_mermaid": "Código Mermaid.js comenzando por graph TD...",\n'
    '  "secuencia_pasos": [\n'
    '    {\n'
    '      "id": "A1",\n'
    '      "fase": "Mise en Place / Preparación / Cocción / Emplatado",\n'
    '      "accion": "Descripción de la acción",\n'
    '      "ingredientes_involucrados": ["Ingrediente 1"],\n'
    '      "tiempo_min": 10,\n'
    '      "es_paralelo": true,\n'
    '      "puede_hacerse_durante": "Mientas se fríe la patata",\n'
    '      "temperatura_o_fuego": "Fuego medio / 180°C / N/A"\n'
    '    }\n'
    '  ],\n'
    '  "recomendaciones_chef": {\n'
    '    "tecnicas_clave": ["Consejo técnico 1", "Consejo técnico 2"],\n'
    '    "puntos_criticos_alerta": ["Punto crítico a evitar 1"],\n'
    '    "maridaje_sugerido": "Vino o bebida ideal",\n'
    '    "sustituciones_posibles": ["Sustitución para alergias o falta de stock"]\n'
    '  }\n'
    '}\n\n'
    "REGLAS DEL DIAGRAMA MERMAID:\n"
    "1. Usa sintaxis `graph TD`.\n"
    "2. Identifica ingredientes de entrada con nodos redondeados: `id([Ingrediente / Cantidad])`.\n"
    "3. Identifica acciones de procesado con rectángulos: `id[Acción / Tiempo / Fuego]`.\n"
    "4. Identifica puntos de decisión/control con rombos: `id{¿Verificación?}`.\n"
    "5. Muestra claramente la convergencia de ingredientes en recipientes o mezclas con flechas conectadas.\n"
    "6. Aplica estilos con `classDef` para dar colores a ingredientes (verde), acciones (naranja), fuego (rojo) y resultado final (azul).\n"
)

# ==========================================
# 3. BASE DE DATOS DE RECETAS DE EJEMPLO
# ==========================================
RECETAS_COMPLETAS = {
    "Tortilla de Patatas Tradicional": """Tortilla de patatas con cebolla tradicional:

Ingredientes:
- 4 patatas grandes (approx. 800g)
- 1 cebolla grande
- 6 huevos camperos M
- 300ml de aceite de oliva virgen extra
- Sal al gusto

Elaboración:
1. Pelar y cortar las patatas en láminas finas y de grosor uniforme. Cortar la cebolla en juliana fina.
2. Calentar el aceite de oliva virgen extra en una sartén antiadherente profunda. Pochar la patata junto con la cebolla a fuego medio-bajo durante 18 minutos hasta que estén confitadas y tiernas, sin llegar a dorarse en exceso.
3. Mientras se fríen las patatas y la cebolla, cascar los 6 huevos en un bol grande y batirlos enérgicamente con una pizca de sal.
4. Una vez tiernas las patatas y cebollas, escurrir bien el aceite usando un colador (reservar el aceite para otros usos).
5. Incorporar las patatas y la cebolla bien calientes al bol con el huevo batido. Mezclar bien con una lengua de cocina y dejar reposar la mezcla durante 5 minutos para que la patata absorba el huevo.
6. Calentar una sartén antiadherente a fuego medio con 1 cucharada del aceite reservado. Verter la mezcla y cuajar durante 2 minutos moviendo suavemente los bordes.
7. Colocar un plato llano sobre la sartén, dar la vuelta a la tortilla con un movimiento rápido y firme.
8. Deslizar la tortilla de nuevo en la sartén y cuajar por el segundo lado durante 1.5 minutos a fuego medio para mantener el centro jugoso. Servir inmediatamente.""",

    "Risotto de Setas y Mantequilla de Trufa": """Risotto cremoso de setas silvestres y parmesano:

Ingredientes:
- 320g de arroz Carnaroli o Arborio
- 300g de setas variadas (Boletus, champiñones, portobello)
- 1 litro de caldo de verduras
- 1 chalota grande
- 100ml de vino blanco seco
- 50g de mantequilla fría en cubos
- 70g de queso Parmesano Reggiano recién rallado
- Aceite de oliva virgen extra, sal y pimienta negra.

Elaboración:
1. Calentar el caldo de verduras en un cazo a fuego lento y mantenerlo hirviendo suavemente durante todo el proceso.
2. Limpiar las setas con un paño húmedo y trocearlas en dados de 1.5cm. Picar la chalota en brunoise muy fina.
3. En una cazuela baja y ancha, calentar 2 cucharadas de aceite de oliva y sofreír la chalota picada durante 3 minutos hasta que esté transparente.
4. Saltear las setas en la cazuela a fuego vivo durante 5 minutos hasta que pierdan el agua y se doren. Retirar una tercera parte de las setas para la decoración final.
5. Añadir los 320g de arroz a la cazuela y nacarar (tostar el grano) durante 2 minutos removiendo constantemente hasta que los bordes del arroz transparenten.
6. Verter los 100ml de vino blanco seco y remover a fuego fuerte durante 2 minutos hasta que el alcohol se evapore por completo.
7. Comenzar a añadir el caldo hirviendo cazo a cazo, removiendo continuamente con cuchara de madera a fuego medio. Esperar a que el arroz absorba casi todo el líquido antes de añadir el siguiente cazo. Este proceso dura entre 16 y 18 minutos.
8. Retirar la cazuela del fuego cuando el arroz esté al dente. Añadir los 50g de mantequilla fría y los 70g de Parmesano rallado.
9. Mantecar enérgicamente haciendo movimientos circulares durante 2 minutos para emulsionar los almidones con la grasa.
10. Tapar la cazuela, dejar reposar 2 minutos y servir decorando con las setas salteadas reservadas."""
}

# ==========================================
# 4. FUNCIONES DE PROCESAMIENTO E IA
# ==========================================
def procesar_receta_con_gemini(api_key: str, modelo_nombre: str, receta_texto: str, nivel_detalle: str):
    """Envía la receta a la API de Gemini y devuelve la estructura analizada."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=modelo_nombre,
        generation_config={"temperature": 0.2, "top_p": 0.95}
    )
    
    prompt_completo = (
        PROMPT_INGENIERIA_PROCESOS +
        "\n\nNIVEL DE DETALLE REQUERIDO: " + nivel_detalle +
        "\n\nRECETA A ANALIZAR:\n" + receta_texto
    )
    
    response = model.generate_content(prompt_completo)
    
    # Limpieza de bloque de código Markdown si la IA lo envuelve en ```json ... ```
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
        
    raw_text = raw_text.strip()
    return json.loads(raw_text)

# ==========================================
# 5. BARRA LATERAL (CENTRO DE CONTROL)
# ==========================================
st.sidebar.image("[https://img.icons8.com/emoji/96/chef-hat-emoji.png](https://img.icons8.com/emoji/96/chef-hat-emoji.png)", width=75)
st.sidebar.title("🎛️ Control de Procesos")

api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "API Key de Google Gemini:",
    value=api_key_env,
    type="password",
    help="Consigue tu API Key gratuita en [https://aistudio.google.com/](https://aistudio.google.com/)"
)

modelo_opcion = st.sidebar.selectbox(
    "Motor de Inteligencia Artificial:",
    options=["gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)

st.sidebar.divider()
st.sidebar.subheader("⚙️ Parámetros de Diagramación")
nivel_detalle = st.sidebar.select_slider(
    "Nivel de desglose técnico:",
    options=["Básico (Consolidado)", "Estándar (Recomendado)", "Avanzado (Micro-pasos)"],
    value="Estándar (Recomendado)"
)

st.sidebar.info(
    "💡 **Nota sobre tareas paralelas:** El algoritmo analiza qué tareas se pueden realizar durante "
    "tiempos de espera (ej. picar mientras se fríe) para optimizar la secuencia en cocina."
)

# ==========================================
# 6. CABECERA PRINCIPAL
# ==========================================
st.markdown("""
<div class="main-header">
    <h1>👨‍🍳 Kitchen Process Studio</h1>
    <p>Traductor Inteligente de Recetas a Diagramas de Flujo Ejecutables & Análisis de Eficiencia Gastronómica</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7. ESTRUCTURA DE LA INTERFAZ PRINCIPAL
# ==========================================
col_izq, col_der = st.columns([1, 1.15])

with col_izq:
    st.subheader("📝 Entrada de Receta")
    
    ejemplo_sel = st.selectbox(
        "Cargar receta de ejemplo:",
        options=["-- Escribir Receta Propia --"] + list(RECETAS_COMPLETAS.keys())
    )
    
    texto_inicial = ""
    if ejemplo_sel != "-- Escribir Receta Propia --":
        texto_inicial = RECETAS_COMPLETAS[ejemplo_sel]
        
    receta_input = st.text_area(
        "Pega aquí el texto completo de la receta (ingredientes + pasos):",
        value=texto_inicial,
        height=420,
        placeholder="Ejemplo:\n- 2 huevos\n- 100g de harina...\n\nPasos:\n1. Mezclar ingredientes...\n2. Hornear a 180°C..."
    )
    
    btn_procesar = st.button("🚀 Generar Diagrama y Estudio de Cocina", use_container_width=True, type="primary")

with col_der:
    st.subheader("📊 Panel de Ejecución y Visualización")
    
    if btn_procesar:
        if not api_key_input:
            st.error("⚠️ Introduce tu API Key de Gemini en el panel lateral para continuar.")
        elif not receta_input.strip():
            st.warning("⚠️ Escribe o selecciona una receta antes de procesar.")
        else:
            with st.spinner("👨‍🍳 La IA está compilando los pasos, identificando secuencias paralelas y generando el diagrama..."):
                try:
                    resultado = procesar_receta_con_gemini(
                        api_key=api_key_input,
                        modelo_nombre=modelo_opcion,
                        receta_texto=receta_input,
                        nivel_detalle=nivel_detalle
                    )
                    st.session_state["resultado_gastronomico"] = resultado
                    st.success("¡Diagrama y análisis técnico generados con éxito!")
                except Exception as e:
                    st.error(f"❌ Error durante el análisis del proceso: {str(e)}")

    if "resultado_gastronomico" in st.session_state:
        res = st.session_state["resultado_gastronomico"]
        
        # Tarjetas de métricas rápidas
        resumen = res.get("resumen_ejecutivo", {})
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f'<div class="metric-container"><div class="metric-value">{resumen.get("tiempo_total_estimado_min", "N/A")} min</div><div class="metric-label">Tiempo Total</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-container"><div class="metric-value">{resumen.get("tiempo_manos_a_la_obra_min", "N/A")} min</div><div class="metric-label">Tiempo Activo</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-container"><div class="metric-value">{resumen.get("dificultad_tecnica", "Media")}</div><div class="metric-label">Dificultad</div></div>', unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Pestañas principales de entrega de contenido
        tab_diagrama, tab_secuencia, tab_chef, tab_codigo = st.tabs([
            "📌 Diagrama de Flujo (Mermaid)",
            "📋 Secuencia de Pasos Paralelos",
            "👨‍🍳 Recomendaciones del Chef",
            "💻 Código Fuente Mermaid"
        ])
        
        with tab_diagrama:
            st.markdown("#### Grafo Dirigido Ejecutable de la Receta")
            st.caption("💡 Sigue las flechas. Los bloques alineados en horizontal representan procesos paralelos.")
            
            codigo_mermaid = res.get("diagrama_mermaid", "")
            try:
                st.mermaid(codigo_mermaid)
            except Exception:
                st.warning("Renderizando como código estructurado debido a especificaciones del navegador:")
                st.code(codigo_mermaid, language="mermaid")
                
        with tab_secuencia:
            st.markdown("#### Desglose Técnico de Tareas")
            pasos = res.get("secuencia_pasos", [])
            if pasos:
                df_pasos = pd.DataFrame(pasos)
                st.dataframe(df_pasos, use_container_width=True)
            else:
                st.info("No se devolvió desglose en formato tabla.")
                
        with tab_chef:
            chef_data = res.get("recomendaciones_chef", {})
            
            st.markdown('<div class="chef-recommendation-card">', unsafe_allow_html=True)
            st.markdown("### 🎓 Técnicas Clave de Cocina")
            for tec in chef_data.get("tecnicas_clave", []):
                st.markdown(f"* **{tec}**")
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="critical-alert-card">', unsafe_allow_html=True)
            st.markdown("### ⚠️ Alertas y Puntos Críticos")
            for alt in chef_data.get("puntos_criticos_alerta", []):
                st.markdown(f"* {alt}")
            st.markdown('</div>', unsafe_allow_html=True)
            
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.markdown("#### 🍷 Maridaje Recomendado")
                st.write(chef_data.get("maridaje_sugerido", "No especificado"))
            with col_m2:
                #### 🔄 Sustituciones de Ingredientes
                for sust in chef_data.get("sustituciones_posibles", []):
                    st.markdown(f"* {sust}")
                    
        with tab_codigo:
            st.markdown("#### Código Fuente .mmd")
            st.code(res.get("diagrama_mermaid", ""), language="mermaid")
            st.download_button(
                label="📥 Descargar Diagrama (.mmd)",
                data=res.get("diagrama_mermaid", ""),
                file_name="diagrama_receta.mmd",
                mime="text/plain"
            )
