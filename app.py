import os
import re
import json
import base64
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Chef Diagram & Kitchen Studio - Traductor Inteligente de Recetas",
    page_icon="👨‍🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS CSS PERSONALIZADOS DE ESTUDIO GASTRONÓMICO ---
st.markdown("""
<style>
    .main-title {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #1E293B;
        font-weight: 800;
        font-size: 2.4rem;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
    }
    .chef-card {
        background-color: #F8FAFC;
        border-left: 5px solid #F59E0B;
        padding: 1.2rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284C7 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- CABECERA ---
st.markdown('<div class="main-title">👨‍🍳 Chef Diagram & Kitchen Studio</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Traductor Inteligente de Recetas a Diagramas de Bloques Executables + Asistente Técnico Culinario</div>', unsafe_allow_html=True)

# --- BARRA LATERAL ---
st.sidebar.image("https://img.icons8.com/emoji/96/chef-hat-emoji.png", width=70)
st.sidebar.title("🎛️ Centro de Control")

api_key_env = os.getenv("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input(
    "API Key de Google Gemini:",
    value=api_key_env,
    type="password",
    help="Obtén tu API Key gratuita en https://aistudio.google.com/"
)

modelo_opcion = st.sidebar.selectbox(
    "Modelo de Inteligencia Artificial:",
    options=["gemini-1.5-flash", "gemini-1.5-pro"],
    index=0
)

st.sidebar.divider()
st.sidebar.header("⚙️ Preferencias de Cocina")
nivel_detalle = st.sidebar.select_slider(
    "Nivel de detalle del diagrama:",
    options=["Básico (Pocos bloques)", "Estándar (Recomendado)", "Técnico Avanzado (Paso a paso minucioso)"],
    value="Estándar (Recomendado)"
)

# --- PROMPT MASTER DEL CHEF ---
PROMPT_MASTER = f"""
Eres un Chef Ejecutivo con 3 estrellas Michelin y un Ingeniero Industrial de Procesos Gastronómicos.
Tu misión es analizar el texto de la receta provista y generar un análisis exhaustivo en DOS partes:

PARTE 1: CÓDIGO MERMAID (Diagrama de bloques ejecutable)
Debes construir un diagrama de bloques estructurado en sintaxis Mermaid.js (`graph TD`).
Reglas para el diagrama:
1. Agrupa los ingredientes iniciales como nodos redondeados con la forma `id([Ingrediente / Cantidad])`.
2. Las acciones/procesos de cocina deben ser rectángulos: `id[Acción / Tiempo / Temperatura o Fuego]`.
3. Muestra explícitamente cómo los ingredientes se combinan en bowls, sartenes o mezclas conectando las flechas adecuadamente.
4. Si hay puntos de comprobación técnica (ej. ¿está dorado?, ¿temperatura interna 65°C?), usa nodos en rombo: `id{{¿Comprobación?}}` con salidas `-->|Sí|` y `-->|No|`.
5. Muestra claramente las tareas PARALELAS (lo que se puede hacer simultáneamente para optimizar el tiempo).
6. Usa identificadores limpios (A1, A2, B1, B2, C1...).
7. Aplica estilos `classDef` de Mermaid para dar color diferenciado a ingredientes, preparación, fuego, puntos de control y plato final.
8. El nivel de detalle debe ser: {nivel_detalle}.

PARTE 2: RECOMENDACIONES TÉCNICAS DEL CHEF Y ANÁLISIS DE EFICIENCIA
Proporciona un informe detallado con:
- **Consejos del Chef:** Trucos profesionales de técnica, temperatura, corte o sazón.
- **Maridaje Recomendado:** Bebida, vino o acompañamiento ideal para potenciar el plato.
- **Alertas y Puntos Críticos:** Errores comunes a evitar (ej. sobrecocción, corte de salsas).
- **Análisis de Tiempos y Paralelización:** Estimación de tiempo activo vs pasivo.
- **Sustituciones de Ingredientes:** Alternativas para alérgenos o falta de stock.

FORMATO DE RESPUESTA EXIGIDO:
```mermaid
[AQUÍ TU CÓDIGO MERMAID ÚNICAMENTE]
