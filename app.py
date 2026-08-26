import streamlit as st
import re
from io import BytesIO
from gtts import gTTS

# Configuración de la página
st.set_page_config(
    page_title="Traductor de Recetas a Diagrama y Voz",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 Traductor de Recetas: Diagrama de Flujo y Asistente de Voz")
st.caption("Convierte recetas en diagramas de bloques y escucha las instrucciones paso a paso.")

# Función para generar audio en memoria (evita guardar archivos en disco)
def text_to_audio(text: str) -> BytesIO:
    tts = gTTS(text=text, lang='es')
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# Procesador de texto para separar ingredientes y pasos
def parse_recipe(text: str):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    ingredients = []
    steps = []
    is_steps = False

    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in ["paso", "pasos", "preparación", "elaboración"]):
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

# Generador de sintaxis Mermaid para el diagrama de bloques
def generate_mermaid(steps: list) -> str:
    mermaid_code = "graph TD\n"
    mermaid_code += "    Start([🚀 Inicio: Preparación]) --> Ing[🛒 Ingredientes listos]\n"
    
    for idx, step in enumerate(steps):
        safe_text = step.replace('"', "'").replace('[', '(').replace(']', ')')
        short_text = safe_text[:40] + ("..." if len(safe_text) > 40 else "")
        prev_node = "Ing" if idx == 0 else f"Step{idx}"
        current_node = f"Step{idx + 1}"
        mermaid_code += f'    {prev_node} --> {current_node}["Paso {idx + 1}: {short_text}"]\n'
    
    last_node = f"Step{len(steps)}" if steps else "Ing"
    mermaid_code += f"    {last_node} --> End([🎉 ¡Plato listo!])\n"
    return mermaid_code

# Estado global de la sesión para la navegación
if "current_step" not in st.session_state:
    st.session_state.current_step = 0

# Receta de ejemplo
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

# Disposición de la interfaz
col_input, col_display = st.columns([1, 2])

with col_input:
    st.subheader("📝 Entrada de la Receta")
    recipe_text = st.text_area("Pega la receta aquí:", value=default_recipe, height=350)
    
    if st.button("⚙️ Generar Diagrama y Voz", type="primary", use_container_width=True):
        st.session_state.current_step = 0
        st.rerun()

ingredients, steps = parse_recipe(recipe_text)

with col_display:
    tab1, tab2 = st.tabs(["📊 Diagrama de Bloques", "🎙️ Asistente de Voz Guiado"])
    
    with tab1:
        st.subheader("Diagrama de Flujo del Proceso")
        mermaid_syntax = generate_mermaid(steps)
        st.markdown(f"```mermaid\n{mermaid_syntax}\n```")

    with tab2:
        st.subheader("Instrucciones Paso a Paso")
        
        if steps:
            total_steps = len(steps)
            current = st.session_state.current_step
            
            # Controles de navegación interactivos
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                if st.button("⬅️ Anterior", disabled=(current == 0), use_container_width=True):
                    st.session_state.current_step -= 1
                    st.rerun()
            with c2:
                st.markdown(f"<h4 style='text-align: center;'>Paso {current + 1} de {total_steps}</h4>", unsafe_allow_html=True)
                st.progress((current + 1) / total_steps)
            with c3:
                if st.button("Siguiente ➡️", disabled=(current == total_steps - 1), use_container_width=True):
                    st.session_state.current_step += 1
                    st.rerun()

            # Texto de la instrucción actual
            current_instruction = steps[current]
            st.info(f"**Paso {current + 1}:** {current_instruction}")

            # Asistente de voz
            st.subheader("🔊 Audio del Paso Actual")
            try:
                audio_file = text_to_audio(f"Paso {current + 1}: {current_instruction}")
                st.audio(audio_file, format="audio/mp3", autoplay=True)
            except Exception:
                st.error("No se pudo conectar con el servidor de voz. Verifica tu conexión a internet.")
        else:
            st.warning("No se detectaron pasos claros en la receta. Revisa el texto formateado.")
