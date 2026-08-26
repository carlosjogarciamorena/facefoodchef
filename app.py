import streamlit as st
import re
from io import BytesIO
from gtts import gTTS

# Configuración principal de la aplicación
st.set_page_config(
    page_title="Traductor de Recetas a Diagrama y Voz",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 Generador de Diagramas de Recetas y Asistente de Voz")
st.caption("Transforma el texto de cualquier receta en un diagrama de flujo y escucha la guía paso a paso.")

@st.cache_data(show_spinner=False)
def generate_step_audio(text: str) -> BytesIO:
    """Genera la síntesis de voz en memoria mediante gTTS garantizando compatibilidad."""
    tts = gTTS(text=text, lang='es', slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

def parse_recipe_text(text: str):
    """Extrae secuencialmente los ingredientes y los pasos operativos de la receta."""
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    ingredients = []
    steps = []
    is_steps = False

    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in ["paso", "pasos", "preparación", "elaboración", "instrucciones"]):
            is_steps = True
            continue
        elif "ingrediente" in line_lower:
            is_steps = False
            continue

        clean_line = re.sub(r'^[0-9]+\.\s*|^[-\*]\s*', '', line)

        if is_steps or re.match(r'^[0-9]+\.', line):
            steps.append(clean_line)
        else:
            ingredients.append(clean_line)

    if not steps:
        steps = lines

    return ingredients, steps

def create_mermaid_diagram(steps: list) -> str:
    """Construye la representación lógica del diagrama de bloques en sintaxis Mermaid."""
    diagram = ["graph TD"]
    diagram.append("    Start([🚀 Inicio: Receta]) --> Ing[🛒 Ingredientes Listos]")
    
    for idx, step in enumerate(steps):
        # Sanitización de caracteres especiales para sintaxis Mermaid
        safe_step = step.replace('"', "'").replace('[', '(').replace(']', ')').replace('(', '').replace(')', '')
        short_text = safe_step[:42] + ("..." if len(safe_step) > 42 else "")
        prev_node = "Ing" if idx == 0 else f"Step{idx}"
        curr_node = f"Step{idx + 1}"
        diagram.append(f'    {prev_node} --> {curr_node}["Paso {idx + 1}: {short_text}"]')
    
    last_node = f"Step{len(steps)}" if steps else "Ing"
    diagram.append(f"    {last_node} --> End([🎉 ¡Plato Finalizado!])")
    
    return "\n".join(diagram)

# Estado global para mantener el control de navegación interactivo
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

default_recipe = """Ingredientes:
- 4 patatas grandes
- 1 cebolla
- 6 huevos
- Aceite de oliva y sal

Pasos:
1. Pelar y cortar las patatas en láminas finas y la cebolla en juliana.
2. Freír las patatas y la cebolla en una sartén con abundante aceite a fuego medio hasta que estén tiernas.
3. Batir los huevos en un bol grande con una pizca de sal.
4. Escurrir bien el aceite de las patatas y cebolletas, y mezclarlas con los huevos batidos. Dejar reposar 5 minutos.
5. Verter la mezcla en la sartén y cocinar a fuego medio durante 4 minutos por cada lado hasta dorar."""

# Disposición de la interfaz (2 columnas)
col_input, col_view = st.columns([1, 2])

with col_input:
    st.subheader("📝 Receta de Cocina")
    recipe_input = st.text_area("Introduce el texto de la receta:", value=default_recipe, height=360)
    
    if st.button("⚙️ Generar Diagrama y Asistente", type="primary", use_container_width=True):
        st.session_state.current_step = 0
        st.rerun()

ingredients, steps = parse_recipe_text(recipe_input)

with col_view:
    tab_flow, tab_audio = st.tabs(["📊 Diagrama de Bloques", "🎙️ Asistente de Voz Paso a Paso"])
    
    with tab_flow:
        st.subheader("Diagrama de Flujo del Proceso")
        if steps:
            mermaid_code = create_mermaid_diagram(steps)
            st.markdown(f"```mermaid\n{mermaid_code}\n```")
        else:
            st.warning("No se han detectado pasos para construir el diagrama.")

    with tab_audio:
        st.subheader("Instrucciones Auditivas")
        if steps:
            total_steps = len(steps)
            current = st.session_state.current_step
            
            # Botones de control de pasos
            c_prev, c_info, c_next = st.columns([1, 2, 1])
            with c_prev:
                if st.button("⬅️ Anterior", disabled=(current == 0), use_container_width=True):
                    st.session_state.current_step -= 1
                    st.rerun()
            with c_info:
                st.markdown(f"<h4 style='text-align: center; margin: 0;'>Paso {current + 1} de {total_steps}</h4>", unsafe_allow_html=True)
                st.progress((current + 1) / total_steps)
            with c_next:
                if st.button("Siguiente ➡️", disabled=(current == total_steps - 1), use_container_width=True):
                    st.session_state.current_step += 1
                    st.rerun()

            # Cuadro con la instrucción actual
            current_instruction = steps[current]
            st.info(f"**Paso {current + 1}:** {current_instruction}")

            # Reproductor de voz integrado
            st.subheader("🔊 Audio del Paso Actual")
            try:
                audio_bytes = generate_step_audio(f"Paso {current + 1}: {current_instruction}")
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
            except Exception:
                st.error("No se pudo generar el audio. Comprueba tu conexión a Internet.")
        else:
            st.warning("Escribe o pega una receta válida en el panel izquierdo.")
