import streamlit as st
from google import genai
from google.genai import types
import streamlit.components.v1 as components
from recipe_scrapers import scrape_me
import json
import re

st.set_page_config(page_title="FaceFoodChef - Executive Culinary Engine", layout="centered", page_icon="🍳")

st.markdown("""
    <style>
    .main { background-color: #090d16; }
    .stTextArea textarea {
        background-color: #111827; color: #f9fafb;
        border-radius: 14px; border: 1px solid #1f2937; font-size: 15px;
    }
    h1, h2, h3 { color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align: center; color: #f97316;'>🍳 FaceFoodChef Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #9ca3af;'>Motor inteligente de conversión de recetas en diagramas de bloques (Google Gemini Flash).</p>", unsafe_allow_html=True)

st.sidebar.header("⚙️ Panel de Control")
API_KEY = st.sidebar.text_input("API Key de Google Gemini:", type="password", help="Consíguela gratis en aistudio.google.com")
st.sidebar.markdown("---")
st.sidebar.markdown("### 💎 Características\n- Interfaz Glassmorphism Dark.\n- Bloques en paralelo reales.\n- Sincronización y convergencia.\n- Asistente de voz integrado.")

entrada_usuario = st.text_area(
    "📝 Pega la URL de una receta web o escribe el texto (ej: Bacalao al pil-pil, risotto...):", 
    height=120, 
    placeholder="Ej: https://www.receta.com/bacalao-al-pil-pil o escribe los pasos..."
)

def generar_html_diagrama(ingredientes, pasos_previos, bloques_proceso, texto_voz):
    html_ing = """
    <div style="background: linear-gradient(145deg, #111827, #0f172a); border: 1px solid #1f2937; border-radius: 16px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);">
        <h3 style="color: #f97316; margin-top: 0; font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>🛒</span> 1. Ingredientes Necesarios
        </h3>
        <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px;">
    """
    for ing in ingredientes:
        html_ing += f"<span style='background: #1e293b; color: #e5e7eb; padding: 6px 12px; border-radius: 8px; font-size: 13px; border: 1px solid #334155; font-weight: 500;'>{ing}</span>"
    html_ing += "</div></div>"

    html_prev = """
    <div style="background: linear-gradient(145deg, #111827, #0f172a); border: 1px solid #1f2937; border-radius: 16px; padding: 20px; margin-bottom: 24px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);">
        <h3 style="color: #38bdf8; margin-top: 0; font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
            <span>🔪</span> 2. Mise en Place (Pasos Previos)
        </h3>
        <ul style='margin: 10px 0 0 0; padding-left: 20px; color: #cbd5e1; font-size: 14px; line-height: 1.6;'>
    """
    for prep in pasos_previos:
        html_prev += f"<li style='margin-bottom: 6px;'>{prep}</li>"
    html_prev += "</ul></div>"

    html_diagrama = """
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 100%; margin: auto;">
        <h3 style="color: #10b981; font-size: 18px; font-weight: 700; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
            <span>📊</span> 3. Diagrama de Flujo y Procesos Culinarios
        </h3>
    """
    
    for i, bloque in enumerate(bloques_proceso):
        tipo = bloque.get("tipo", "secuencial")
        
        if tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            html_diagrama += '<div style="display: flex; gap: 14px; margin-bottom: 16px; flex-wrap: wrap;">'
            for rama in ramas:
                nombre_rama = rama.get("nombre", "Rama").upper()
                accion = rama.get("accion", "")
                tiempo = rama.get("tiempo", "")
                temp = rama.get("temperatura", "")
                
                html_diagrama += f"""
                <div style="flex: 1; min-width: 260px; background: linear-gradient(145deg, #1e1b4b, #312e81); border: 1px solid #4338ca; border-left: 5px solid #818cf8; border-radius: 14px; padding: 18px; box-shadow: 0 8px 20px rgba(0,0,0,0.4);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <span style="font-size: 11px; font-weight: 800; color: #c7d2fe; letter-spacing: 0.5px; background: rgba(0,0,0,0.25); padding: 3px 8px; border-radius: 6px;">🔀 PARALELO: {nombre_rama}</span>
                    </div>
                    <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin-bottom: 14px; line-height: 1.5;">
                        {accion}
                    </div>
                    <div style="display: flex; gap: 8px; font-size: 12px; color: #e0e7ff;">
                        <div style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 6px; font-weight: 500;">⏱️ {tiempo}</div>
                        <div style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 6px; font-weight: 500;">🌡️ {temp}</div>
                    </div>
                </div>
                """
            html_diagrama += '</div>'
        else:
            es_convergencia = tipo == "convergencia"
            if es_convergencia:
                bg = "linear-gradient(145deg, #064e3b, #065f46)"
                border_color = "#059669"
                left_border = "#34d399"
                badge_bg = "rgba(6, 78, 59, 0.6)"
                icono = "🔗"
                etiqueta = "CONVERGENCIA / UNIÓN FINAL"
            else:
                bg = "linear-gradient(145deg, #111827, #1f2937)"
                border_color = "#374151"
                left_border = "#f97316"
                badge_bg = "rgba(31, 41, 55, 0.8)"
                icono = "🔥"
                etiqueta = f"BLOQUE SECUENCIAL {i+1}"
            
            html_diagrama += f"""
            <div style="background: {bg}; border: 1px solid {border_color}; border-left: 5px solid {left_border}; border-radius: 14px; padding: 18px; margin-bottom: 16px; box-shadow: 0 8px 20px rgba(0,0,0,0.4);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 11px; font-weight: 800; color: #9ca3af; letter-spacing: 0.5px; background: {badge_bg}; padding: 3px 8px; border-radius: 6px;">{icono} {etiqueta}</span>
                </div>
                <div style="font-size: 15px; font-weight: 600; color: #ffffff; margin-bottom: 14px; line-height: 1.5;">
                    {bloque.get('accion')}
                </div>
                <div style="display: flex; gap: 8px; font-size: 12px; color: #d1d5db;">
                    <div style="background: rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 6px; font-weight: 500;">⏱️ {bloque.get('tiempo')}</div>
                    <div style="background: rgba(255,255,255,0.08); padding: 4px 10px; border-radius: 6px; font-weight: 500;">🌡️ {bloque.get('temperatura')}</div>
                </div>
            </div>
            """
            
        if i < len(bloques_proceso) - 1:
            html_diagrama += '<div style="text-align: center; color: #4b5563; font-size: 18px; margin: -6px 0 6px 0; font-weight: bold;">↓</div>'
    
    html_diagrama += "</div>"

    documento_completo = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <style>
            body {{ background-color: #090d16; color: #f9fafb; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 16px; margin: 0; }}
            .voice-box {{ background: linear-gradient(145deg, #111827, #0f172a); border: 1px solid #1f2937; padding: 16px; border-radius: 16px; text-align: center; margin-bottom: 24px; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); }}
            .btn-audio {{ background-color: #f97316; color: white; border: none; padding: 10px 20px; font-size: 13px; font-weight: 700; border-radius: 10px; cursor: pointer; margin: 4px; transition: all 0.2s; box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3); }}
            .btn-audio:hover {{ opacity: 0.9; transform: translateY(-1px); }}
            .btn-stop {{ background-color: #ef4444; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }}
        </style>
    </head>
    <body>
        <div class="voice-box">
            <p style="color: #9ca3af; font-size: 13px; margin: 0 0 12px 0; font-weight: 500;">🎙️ Asistente de Voz Integrado por Bloques</p>
            <button class="btn-audio" onclick="reproducir()">▶️ Escuchar Guía de Cocina</button>
            <button class="btn-audio btn-stop" onclick="detener()">⏹️ Silenciar</button>
        </div>

        {html_ing}
        {html_prev}
        {html_diagrama}

        <script>
            const textoVoz = "{texto_voz.replace('"', '').replace(chr(10), '. ')}";
            function reproducir() {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const msg = new SpeechSynthesisUtterance(textoVoz);
                    msg.lang = 'es-ES'; msg.rate = 0.95;
                    window.speechSynthesis.speak(msg);
                }}
            }}
            function detener() {{
                if ('speechSynthesis' in window) {{ window.speechSynthesis.cancel(); }}
            }}
        </script>
    </body>
    </html>
    """
    return documento_completo

if entrada_usuario and API_KEY:
    receta_texto = ""
    if entrada_usuario.strip().startswith("http://") or entrada_usuario.strip().startswith("https://"):
        try:
            with st.spinner("🌐 Extrayendo datos de la web..."):
                scraper = scrape_me(entrada_usuario.strip())
                receta_texto = f"Receta: {scraper.title()}\nIngredientes: {', '.join(scraper.ingredients())}\nInstrucciones:\n{'\n'.join(scraper.instructions())}"
        except Exception as e:
            st.error(f"No se pudo extraer la URL: {e}")
    else:
        receta_texto = entrada_usuario

    if receta_texto:
        try:
            # Inicializamos el cliente oficial de Google Gemini
            client = genai.Client(api_key=API_KEY)
            
            prompt = f"""
            Eres un chef ejecutivo e ingeniero de procesos culinarios. Analiza la receta y estructúrala detectando tareas secuenciales, en paralelo (columnas simultáneas) y convergencias finales.
            
            Devuélvela estrictamente en formato JSON válido con esta estructura exacta:
            
            REGLAS DE ORO:
            1. 'ingredientes': Lista de ingredientes y cantidades exactas.
            2. 'pasos_previos': Lista con la preparación previa (mise en place).
            3. 'bloques_proceso': Una lista de objetos con los siguientes tipos:
               - TIPO 1: {{"tipo": "secuencial", "accion": "...", "tiempo": "...", "temperatura": "..."}}
               - TIPO 2: {{"tipo": "paralelo", "ramas": [{{"nombre": "...", "accion": "...", "tiempo": "...", "temperatura": "..."}}, {{"nombre": "...", "accion": "...", "tiempo": "...", "temperatura": "..."}}]}}
               - TIPO 3: {{"tipo": "convergencia", "accion": "...", "tiempo": "...", "temperatura": "..."}}
            4. 'texto_voz': Resumen estructurado para lectura por voz.

            Estructura JSON obligatoria:
            {{
              "ingredientes": ["..."],
              "pasos_previos": ["..."],
              "bloques_proceso": [
                {{"tipo": "secuencial", "accion": "🔥 ...", "tiempo": "5 min", "temperatura": "Fuego medio"}},
                {{
                  "tipo": "paralelo",
                  "ramas": [
                    {{"nombre": "Rama 1", "accion": "...", "tiempo": "10 min", "temperatura": "65°C"}},
                    {{"nombre": "Rama 2", "accion": "...", "tiempo": "8 min", "temperatura": "Fuego bajo"}}
                  ]
                }},
                {{"tipo": "convergencia", "accion": "🔗 Juntar todo...", "tiempo": "2 min", "temperatura": "Fuego medio"}}
              ],
              "texto_voz": "..."
            }}
            
            Receta a procesar:
            {receta_texto}
            """
            
            with st.spinner("⚙️ Procesando con IA de Google Gemini 2.5 Flash..."):
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    ),
                )
                
                # Limpieza robusta del texto JSON devuelto
                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]
                
                datos = json.loads(texto_respuesta.strip())
                
                html_final = generar_html_diagrama(
                    datos.get("ingredientes", []),
                    datos.get("pasos_previos", []),
                    datos.get("bloques_proceso", []),
                    datos.get("texto_voz", "")
                )
                
                st.download_button(
                    label="📥 Descargar Dashboard HTML de Alta Gama",
                    data=html_final,
                    file_name="facefoodchef_dashboard.html",
                    mime="text/html"
                )
                
                components.html(html_final, height=900, scrolling=True)
                
        except Exception as e:
            st.error(f"Error procesando con la IA: {e}")
elif not API_KEY:
    st.info("👈 Introduce tu API Key gratuita de Google AI Studio en la barra lateral para comenzar.")
else:
    st.info("👆 Pega una receta de cocina para transformarla en un diagrama de bloques.")
