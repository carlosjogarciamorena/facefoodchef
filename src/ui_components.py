import streamlit as st
from typing import Dict

def render_header():
    st.title("🍳 Industrial Recipe Flowchart Generator")
    st.caption("Sistema de conversión de recetas a diagramas de flujo de procesos gastronómicos.")

def render_metrics(metrics: Dict[str, float]):
    col1, col2, col3 = st.columns(3)
    col1.metric("Tiempo Total Estimado", f"{metrics.get('tiempo_total_estimado', 0)} min")
    col2.metric("Ingredientes Procesados", int(metrics.get('total_ingredientes', 0)))
    col3.metric("Pasos / Operaciones", int(metrics.get('total_pasos', 0)))

def render_utensils_sidebar(utensilios: list):
    st.sidebar.markdown("### 🍳 Utensilios Necesarios")
    if utensilios:
        for u in utensilios:
            st.sidebar.markdown(f"- {u}")
    else:
        st.sidebar.info("No se especificaron utensilios especiales.")
