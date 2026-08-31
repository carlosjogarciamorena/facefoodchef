import os
import re
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Chef Diagram & Kitchen Studio",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .main-title {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1E293B;
        font-weight: 800;
        font-size: 2.2rem;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748B;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .chef-card {
        background-color: #F8FAFC;
        border-left: 5px solid #F59E0B;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">👨‍🍳 Chef Diagram & Kitchen Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Traductor Inteligente de Recetas a Diagramas de Bloques Executables + Asistente Técnico Culinario</div>', unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.title("🎛️ Centro de Control")

api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "API Key de Google Gemini:",
    value=api_key_env,
    type="password",
    help="Obtén tu API Key en https://aistudio.google.com/"
)

modelo_opcion = st.sidebar.selectbox(
    "Modelo IA:",
    options=["gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)

st.sidebar.divider()
nivel_detalle = st.sidebar.select_slider(
    "Nivel de detalle del diagrama:",
    options=["Básico", "Estándar", "Avanzado"],
    value="Estándar"
)

# --- PROMPT MASTER DE LA IA (Corregido sin errores de f-string) ---
PROMPT_MASTER = """
Eres un Chef Ejecutivo con 3 estrellas Michelin y un Ingeniero de Procesos Gastronómicos.
Tu misión es analizar la receta provista y generar un análisis exhaustivo en DOS partes:

PARTE 1: CÓDIGO MERMAID (Diagrama de bloques ejecutable)
Construye un diagrama de bloques estructurado en sintaxis Mermaid.js (graph TD).
Reglas estricta para el diagrama:
1. Agrupa los ingredientes iniciales como nodos redondeados: id([Ingrediente / Cantidad]).
2. Las acciones o procesos deben ser rectángulos: id[Acción / Tiempo / Fuego o Temperatura].
3. Muestra explícitamente la combinación de ingredientes hacia las acciones de mezclado o cocción.
4. Si hay puntos de control, usa nodos en rombo con preguntas de comprobación.
5. Muestra claramente las tareas PARALELAS (lo que se puede hacer simultáneamente para ahorrar tiempo).
6. Usa identificadores limpios (A1, A2, B1, B2...).
7. Aplica clases de estilo visual (classDef) para colorear diferentemente ingredientes, preparación, fuego y plato final.

PARTE 2: RECOMENDACIONES TÉCNICAS DEL CHEF
Proporciona un informe detallado con:
- Consejos del Chef (técnica, temperaturas, puntos clave).
- Maridaje Recomendado (bebida o vino ideal).
- Alertas y Puntos Críticos (errores comunes a evitar).
- Análisis de Tiempos y Paralelización.
- Sustituciones de Ingredientes para alérgenos o alternativas.

FORMATO OBLIGATORIO DE RESPUESTA:
```mermaid
[AQUÍ TU CÓDIGO MERMAID ÚNICAMENTE]
