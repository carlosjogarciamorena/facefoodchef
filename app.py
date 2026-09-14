import json
import os
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai.errors import APIError

# Configuración de la página con estética de streaming
st.set_page_config(
    page_title="Traductor de Recetas - Diagrama de Bloques",
    page_icon="🍳",
    layout="wide"
)

# Inicializar cliente de Gemini (Asegúrate de configurar tu GEMINI_API_KEY en las variables de entorno)
# os.environ["GEMINI_API_KEY"] = "TU_API_KEY"

def obtener_cliente_gemini():
    try:
        return genai.Client()
    except Exception as e:
        return None

# Estilos CSS globales inyectados basados estrictamente en el manual de diseño proporcionado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Montserrat:wght@700;900&display=swap');

    .stApp {
        background-color: #141414;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif;
        font-weight: 900;
        color: #FFFFFF;
    }
    
    .netflix-card {
        background-color: #1F1F1F;
        border-radius: 4px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.7);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .netflix-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
    }
    
    .badge-match {
        background-color: #46D369;
        color: #141414;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.85rem;
    }
    
    .btn-netflix {
        background-color: #E50914;
        color: #FFFFFF;
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        border: none;
        padding: 10px 20px;
        border-radius: 4px;
        cursor: pointer;
        text-transform: uppercase;
    }
    
    .btn-netflix:hover {
        background-color: #f40612;
    }
    
    .secondary-text {
        color: #AAAAAA;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown("<h1 style='color: #E50914; text-align: center;'>🎬 TRADUCTOR DE RECETAS: STREAMLITCHEF</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #AAAAAA;'>Transforma cualquier receta en un diagrama de bloques interactivo al estilo de tu plataforma favorita.</p>", unsafe_allow_html=True)

    # Sidebar para entrada de datos
    with st.sidebar:
        st.markdown("### 📝 Ingresar Receta")
        receta_texto = st.text_area(
            "Pega el texto de tu receta aquí:", 
            height=300,
            placeholder="Ejemplo: Paella valenciana tradicional... Ingredientes: arroz, pollo, conejo, sofrito..."
        )
        generar_btn = st.button("▶ Generar Diagrama", use_container_width=True)

    if generar_btn:
        if not receta_texto.strip():
            st.warning("Por favor, introduce el texto de una receta.")
            return

        client = obtener_cliente_gemini()
        if not client:
            st.error("No se pudo inicializar el cliente de Gemini. Comprueba tu clave de API.")
            return

        prompt = f"""
        Eres un experto chef y arquitecto de software de cocina. Analiza la siguiente receta de cocina y desglózala en un DIAGRAMA DE BLOQUES Secuencial/Paralelo optimizado para seguirse paso a paso en la cocina sin fatiga.
        
        Devuelve la respuesta EXCLUSIVAMENTE en un objeto JSON válido con la siguiente estructura:
        {{
          "titulo": "Nombre de la receta",
          "match_porcentaje": "98%",
          "tiempo_total": "45 mins",
          "dificultad": "Media",
          "raciones": "4 personas",
          "imagen_url": "URL de una imagen panorámica representativa (16:9) libre de derechos o placeholder temático",
          "bloques": [
            {{
              "id": 1,
              "fase": "Preparación y Mise en place",
              "tiempo": "10 mins",
              "instrucciones": ["Picar la cebolla en brunoise", "Cortar el pollo en trozos regulares"],
              "dependencias": []
            }},
            {{
              "id": 2,
              "fase": "Cocinado de la base",
              "tiempo": "20 mins",
              "instrucciones": ["Dorar el pollo con aceite de oliva", "Añadir el sofrito"],
              "dependencias": [1]
            }}
          ]
        }}
        
        Receta a procesar:
        {receta_texto}
        """

        with st.spinner("🎬 Renderizando diagrama de bloques cinematográfico..."):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                texto_respuesta = response.text
                
                # Limpiar bloques de código markdown si los hubiera
                if "```json" in texto_respuesta:
                    texto_respuesta = texto_respuesta.split("```json")[1].split("```")[0].strip()
                elif "```" in texto_respuesta:
                    texto_respuesta = texto_respuesta.split("```")[1].split("```")[0].strip()
                    
                datos_receta = json.loads(texto_respuesta)
                
                # Renderizado visual del plato principal (Estilo Carátula Netflix con Proporción 16:9 y Gradiente)
                st.markdown(f"""
                <div style="position: relative; width: 100%; height: 400px; border-radius: 4px; overflow: hidden; background: url('{datos_receta.get('imagen_url', 'https://images.unsplash.com/photo-1498837167922-ddd27525d352')}') center/cover no-repeat;">
                    <div style="position: absolute; bottom: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(to top, #141414 10%, transparent 90%);"></div>
                    <div style="position: absolute; bottom: 20px; left: 20px; right: 20px;">
                        <span class="badge-match">Match {datos_receta.get('match_porcentaje', '95%')} para ti</span>
                        <h1 style="margin: 10px 0 5px 0; font-size: 2.5rem; text-shadow: 2px 2px 4px rgba(0,0,0,0.8);">{datos_receta.get('titulo', 'Receta')}</h1>
                        <p class="secondary-text">⏱️ {datos_receta.get('tiempo_total')} &nbsp;|&nbsp; 📊 {datos_receta.get('dificultad')} &nbsp;|&nbsp; 🍽️ {datos_receta.get('raciones')}</p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("<h2 style='margin-top: 30px;'>🗺️ Diagrama de Bloques de Ejecución</h2>", unsafe_allow_html=True)
                
                # Generar bloques interactivos tipo flujo de trabajo
                bloques = datos_receta.get('bloques', [])
                
                html_bloques = "<div style='display: flex; flex-direction: column; gap: 15px;'>"
                for b in bloques:
                    instrucciones_html = "".join([f"<li>{ins}</li>" for ins in b.get('instrucciones', [])])
                    deps = ", ".join(map(str, b.get('dependencias', [])))
                    dep_text = f"<span class='secondary-text'>Requiere Bloque(s): #{deps}</span>" if deps else "<span class='secondary-text'>Fase Inicial / Independiente</span>"
                    
                    html_bloques += f"""
                    <div style="background-color: #1F1F1F; border-left: 5px solid #E50914; padding: 20px; border-radius: 4px; box-shadow: 0 4px 10px rgba(0,0,0,0.5);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                            <h3 style="margin: 0; color: #FFFFFF; font-family: 'Montserrat', sans-serif;">Bloque #{b.get('id')}: {b.get('fase')}</h3>
                            <span style="background-color: #333333; color: #46D369; padding: 4px 10px; border-radius: 4px; font-weight: 600;">⏱️ {b.get('tiempo')}</span>
                        </div>
                        <div style="margin-bottom: 10px;">{dep_text}</div>
                        <ul style="color: #FFFFFF; font-family: 'Inter', sans-serif; margin: 0; padding-left: 20px; line-height: 1.6;">
                            {instrucciones_html}
                        </ul>
                    </div>
                    """
                html_bloques += "</div>"
                
                st.markdown(html_bloques, unsafe_allow_html=True)
                
                st.success("¡Diagrama generado con éxito!")
                
            except json.JSONDecodeError:
                st.error("Error al procesar la respuesta de la IA en formato JSON. Inténtalo de nuevo.")
                if 'texto_respuesta' in locals():
                    with st.expander("Ver respuesta raw de la IA"):
                        st.text(texto_respuesta)
            except APIError as e:
                st.error(f"Error de la API de Gemini: {e}")
            except Exception as e:
                st.error(f"Se ha producido un error inesperado: {e}")

if __name__ == "__main__":
    main()
