import os
import json
import logging
import requests
from typing import Optional
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Cargar variables desde archivo .env local si existe
load_dotenv()

# =============================================================================
# CONFIGURACIÓN Y GESTIÓN RIGUROSA DE CREDENCIALES
# =============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FaceFoodChef")

def obtener_credencial(clave: str, valor_defecto: str = "") -> str:
    """Obtiene la credencial desde st.secrets o variables de entorno os.getenv."""
    if hasattr(st, "secrets") and clave in st.secrets:
        return str(st.secrets[clave]).strip()
    return os.getenv(clave, valor_defecto).strip()

GEMINI_API_KEY = obtener_credencial("GEMINI_API_KEY")
WP_SITE_URL = obtener_credencial("WP_SITE_URL", "https://facefoodchef.com").rstrip("/")
WP_USER = obtener_credencial("WP_USER")
WP_APP_PASSWORD = obtener_credencial("WP_APP_PASSWORD")


# =============================================================================
# VALIDADOR DE ESQUEMA CULINARIO (DAG)
# =============================================================================
class ValidadorEsquemaCulinario:
    @staticmethod
    def validar(datos: dict) -> bool:
        campos_requeridos = ["titulo_plato", "tiempo_total_estimado", "bloques_proceso"]
        if not all(campo in datos for campo in campos_requeridos):
            logger.error("Faltan campos maestros en el JSON de la receta.")
            return False
        
        for idx, bloque in enumerate(datos.get("bloques_proceso", [])):
            if "tipo" not in bloque:
                return False
            if bloque["tipo"] == "paralelo" and "ramas" not in bloque:
                return False
        return True


# =============================================================================
# MOTOR DE ANÁLISIS SEMÁNTICO (IA CON CONTROL DE ERRORES)
# =============================================================================
class MotorAnalisisSemantico:
    def __init__(self, api_key: str):
        # Validación limpia previa a la llamada
        if not api_key or not api_key.startswith("AIzaSy"):
            raise ValueError(
                "La clave 'GEMINI_API_KEY' introducida no tiene el formato válido de Google AI Studio "
                "(debe comenzar por 'AIzaSy...'). Verifique sus Secrets o el archivo .env."
            )
        self.client = genai.Client(api_key=api_key)
        self.modelo = "gemini-2.5-flash"
        
    def procesar_texto(self, texto_receta: str) -> dict:
        prompt = """
        Eres un arquitecto de software y chef ejecutivo. Analiza la receta y conviértela en un diagrama de bloques estructurado en formato JSON estricto.
        
        Clasifica las acciones en:
        1. "secuencial": Pasos lineales independientes o preparativos previos.
        2. "paralelo": Tareas simultáneas agrupadas dentro de una clave llamada "ramas" (array de objetos con "estacion", "accion" y "duracion_minutos").
        3. "convergencia": El punto donde las ramas paralelas se unifican en el plato final.

        Devuelve UNICAMENTE un objeto JSON válido con este formato exacto:
        {
          "titulo_plato": "Nombre completo",
          "tiempo_total_estimado": "X minutos",
          "bloques_proceso": [
            {
              "id": 1,
              "tipo": "secuencial",
              "accion": "Descripción clara",
              "duracion_minutos": 5
            },
            {
              "id": 2,
              "tipo": "paralelo",
              "ramas": [
                {"estacion": "Estación A", "accion": "Acción 1", "duracion_minutos": 10},
                {"estacion": "Estación B", "accion": "Acción 2", "duracion_minutos": 8}
              ]
            },
            {
              "id": 3,
              "tipo": "convergencia",
              "accion": "Unión final",
              "duracion_minutos": 2
            }
          ]
        }
        Sin bloques Markdown ni texto conversacional. Solo JSON puro.
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.modelo,
                contents=[prompt, f"Receta:\n{texto_receta}"],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                ),
            )
            return json.loads(response.text.strip())
        except Exception as e:
            if "API_KEY_INVALID" in str(e) or "400" in str(e):
                raise ValueError("🚨 Error de Autenticación: La API Key de Gemini introducida no es válida o fue rechazada por Google.")
            raise e


# =============================================================================
# MOTOR DE RENDERIZADO FRONTEND (INTERFAZ VISUAL EN HTML/JS)
# =============================================================================
class MotorRenderizadoFrontend:
    def generar_html_interactivo(self, datos: dict) -> str:
        html_salida = f"""
        <div class="facefoodchef-diagrama" style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; background: #fff; border-radius: 8px;">
            <h2 style="text-align: center; color: #ff3b3b;">{datos.get('titulo_plato')}</h2>
            <p style="text-align: center; font-weight: bold; color: #666;">⏱️ Tiempo Total Estimado: {datos.get('tiempo_total_estimado')}</p>
            <hr style="border: 0; height: 1px; background: #eee; margin: 20px 0;">
        """
        
        for bloque in datos.get("bloques_proceso", []):
            tipo = bloque.get("tipo")
            b_id = bloque.get("id")
            
            if tipo in ["secuencial", "convergencia"]:
                html_salida += self._renderizar_lineal(bloque, b_id, tipo)
            elif tipo == "paralelo":
                html_salida += self._renderizar_paralelo(bloque, b_id)
                
        html_salida += "</div>"
        html_salida += self._obtener_css_js()
        return html_salida

    def _renderizar_lineal(self, bloque: dict, b_id: int, tipo: str) -> str:
        accion = bloque.get("accion", "")
        minutos = bloque.get("duracion_minutos", 0)
        clase = "ffc-secuencial" if tipo == "secuencial" else "ffc-convergencia"
        icono = "⬇️" if tipo == "secuencial" else "🔗"
        
        return f"""
        <div class="ffc-bloque {clase}" id="bloque-{b_id}">
            <div class="ffc-header">{icono} {tipo.upper()}</div>
            <div class="ffc-body">{accion}</div>
            <div class="ffc-footer">
                <button class="ffc-timer-btn" onclick="startTimer(this, {minutos})">⏱️ Iniciar ({minutos} min)</button>
            </div>
        </div>
        """

    def _renderizar_paralelo(self, bloque: dict, b_id: int) -> str:
        ramas = bloque.get("ramas", [])
        html = f'<div class="ffc-bloque-paralelo" id="bloque-{b_id}">'
        for idx, rama in enumerate(ramas):
            estacion = rama.get("estacion", f"Estación {idx+1}")
            accion = rama.get("accion", "")
            minutos = rama.get("duracion_minutos", 0)
            html += f"""
            <div class="ffc-rama">
                <div class="ffc-header">🔀 {estacion}</div>
                <div class="ffc-body">{accion}</div>
                <div class="ffc-footer">
                    <button class="ffc-timer-btn" onclick="startTimer(this, {minutos})">⏱️ {minutos} min</button>
                </div>
            </div>
            """
        html += '</div>'
        return html

    def _obtener_css_js(self) -> str:
        return """
        <style>
            .ffc-bloque { background: #fcfcfc; border-left: 4px solid #333; margin-bottom: 20px; padding: 18px; border-radius: 6px; }
            .ffc-convergencia { border-left-color: #ff3b3b; background: #fff8f8; }
            .ffc-bloque-paralelo { display: flex; gap: 15px; margin-bottom: 20px; }
            .ffc-rama { flex: 1; background: #f0f6ff; border-left: 4px solid #0066cc; padding: 15px; border-radius: 6px; }
            .ffc-header { font-weight: bold; font-size: 0.85em; text-transform: uppercase; margin-bottom: 8px; color: #555; }
            .ffc-body { font-size: 1.05em; margin-bottom: 12px; color: #222; }
            .ffc-timer-btn { background: #1a1a1a; color: #fff; border: none; padding: 8px 14px; border-radius: 20px; cursor: pointer; font-weight: 600; width: 100%; }
            .ffc-timer-btn.active { background: #ff3b3b; }
            @media (max-width: 650px) { .ffc-bloque-paralelo { flex-direction: column; } }
        </style>
        <script>
            function startTimer(btn, minutes) {
                if(btn.classList.contains('active')) return;
                btn.classList.add('active');
                let seconds = minutes * 60;
                let interval = setInterval(() => {
                    seconds--;
                    let m = Math.floor(seconds / 60);
                    let s = seconds % 60;
                    btn.innerHTML = `⏳ ${m}:${s.toString().padStart(2, '0')}`;
                    if (seconds <= 0) {
                        clearInterval(interval);
                        btn.innerHTML = "✅ ¡Paso completado!";
                        btn.style.background = "#28a745";
                    }
                }, 1000);
            }
        </script>
        """


# =============================================================================
# INTERFAZ GRÁFICA Y CONTROLADOR
# =============================================================================
def main():
    st.set_page_config(page_title="FaceFoodChef - Diagramas Culinarios", page_icon="🍳")
    st.title("🍳 FaceFoodChef: Generador de Diagramas Culinarios")

    # Permite sobrescribir la clave manualmente desde la interfaz si falla el archivo de configuración
    api_key_input = st.sidebar.text_input("🔑 API Key de Gemini", value=GEMINI_API_KEY, type="password")

    texto_ingresado = st.text_area(
        "✍️ Introduce la receta a procesar:",
        value="Spaghetti Carbonara: Cocer pasta 10 minutos. En paralelo, dorar panceta 8 minutos. Batir yemas con pecorino. Mezclar la pasta con la panceta fuera del fuego y añadir las yemas.",
        height=150
    )

    if st.button("🚀 Generar Diagrama de Bloques", type="primary", use_container_width=True):
        if not api_key_input:
            st.error("🚨 Debe proporcionar una API Key de Gemini en la barra lateral o en el archivo de entorno (`.env` / Secrets).")
            return

        with st.spinner("Procesando receta con Gemini..."):
            try:
                analizador = MotorAnalisisSemantico(api_key_input)
                validador = ValidadorEsquemaCulinario()
                renderizador = MotorRenderizadoFrontend()
                
                datos_grafo = analizador.procesar_texto(texto_ingresado)
                
                if not validador.validar(datos_grafo):
                    st.error("Error: La respuesta estructurada no pasó el control de calidad.")
                    return
                
                html_resultado = renderizador.generar_html_interactivo(datos_grafo)
                
                st.success("¡Diagrama generado correctamente!")
                st.components.v1.html(html_resultado, height=500, scrolling=True)
                
            except Exception as e:
                st.error(f"❌ {str(e)}")

if __name__ == "__main__":
    main()
