import os
import streamlit as st
from dotenv import load_dotenv

from src.nlp_parser import RecipeParser
from src.graph_engine import RecipeGraphEngine
from src.mermaid_generator import MermaidGenerator
from src.ui_components import render_header, render_metrics, render_utensils_sidebar

load_dotenv()

st.set_page_config(
    page_title="Generador de Diagramas de Recetas",
    page_icon="🍲",
    layout="wide"
)

render_header()

# --- BARRA LATERAL DE CONFIGURACIÓN ---
st.sidebar.header("⚙️ Configuración del Sistema")
env_key = os.getenv("GEMINI_API_KEY", "")
api_key = st.sidebar.text_input("Gemini API Key:", value=env_key, type="password")

modelo = st.sidebar.selectbox("Modelo LLM:", ["gemini-2.5-flash", "gemini-1.5-flash"])

# Ejemplos predefinidos
receta_ejemplo = """
Lasaña de Carne Tradicional:
1. Picar 1 cebolla, 2 dientes de ajo y 1 zanahoria en brunoise fina.
2. Sofreír las verduras en una sartén con 30ml de aceite de oliva durante 10 minutos a fuego medio.
3. Añadir 500g de carne picada de ternera a la sartén y cocinar 8 minutos hasta que se dore.
4. Verter 400g de tomate triturado, sal, pimienta y orégano. Reducir a fuego lento durante 20 minutos.
5. En un cazo aparte, derretir 50g de mantequilla, incorporar 50g de harina y cocinar 2 minutos.
6. Añadir 500ml de leche poco a poco removiendo constantemente con varillas durante 8 minutos hasta obtener una bechamel espesa.
7. En una fuente para horno, colocar una capa de carne, una capa de placas de pasta para lasaña y una capa de bechamel. Repetir 3 veces.
8. Cubrir con 100g de queso rallado e introducir en el horno precalentado a 200°C durante 25 minutos hasta que el queso esté gratinado y dorado.
"""

# --- CUERPO PRINCIPAL ---
col_in, col_out = st.columns([1, 1])

with col_in:
    st.subheader("📄 Entrada: Texto de la Receta")
    texto_receta = st.text_area("Pega la receta aquí:", value=receta_ejemplo, height=450)
    procesar_btn = st.button("⚡ Generar Diagrama de Bloques", use_container_width=True, type="primary")

with col_out:
    st.subheader("📊 Salida: Grafo de Procesos")
    
    if procesar_btn:
        if not api_key:
            st.error("❌ Se requiere una API Key de Google Gemini válida.")
        elif not texto_receta.strip():
            st.warning("⚠️ Ingresa el texto de la receta.")
        else:
            with st.spinner("Procesando estructura gastronómica con Gemini LLM..."):
                try:
                    # 1. Parsing NLP
                    parser = RecipeParser(api_key=api_key, model_name=modelo)
                    receta_estructurada = parser.parse_recipe(texto_receta)

                    # 2. Análisis de Grafo
                    engine = RecipeGraphEngine(receta_estructurada)
                    es_valido, errores = engine.validar_grafo()

                    if not es_valido:
                        for err in errores:
                            st.error(f"❌ {err}")
                    else:
                        metrics = engine.calcular_camino_critico()
                        render_metrics(metrics)
                        render_utensils_sidebar(receta_estructurada.utensilios)

                        # 3. Generación Mermaid
                        generator = MermaidGenerator(receta_estructurada)
                        codigo_mermaid = generator.generate()

                        # 4. Renderizado
                        st.mermaid(codigo_mermaid)

                        with st.expander("🛠️ Ver Código Fuente Mermaid y JSON Estructurado"):
                            st.tabs(["Mermaid Code", "JSON Data"])
                            st.code(codigo_mermaid, language="mermaid")
                            st.json(receta_estructurada.model_dump())

                except Exception as e:
                    st.error(f"Ocurrió un error en el procesamiento: {str(e)}")
