import os
import json
import logging
import requests
from typing import Optional
import streamlit as st
from google import genai
from google.genai import types

# =============================================================================
# CONFIGURACIÓN Y LOGGING DEL SISTEMA
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("FaceFoodChef-Production")

# Carga de credenciales con tolerancia a fallos (Soporta Streamlit Cloud y Local)
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    WP_SITE_URL = st.secrets.get("WP_SITE_URL", os.getenv("WP_SITE_URL", "https://facefoodchef.com")).rstrip("/")
    WP_USER = st.secrets.get("WP_USER", os.getenv("WP_USER", ""))
    WP_APP_PASSWORD = st.secrets.get("WP_APP_PASSWORD", os.getenv("WP_APP_PASSWORD", ""))
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    WP_SITE_URL = os.getenv("WP_SITE_URL", "https://facefoodchef.com").rstrip("/")
    WP_USER = os.getenv("WP_USER", "")
    WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")


# =============================================================================
# VALIDADOR DE ESQUEMA CULINARIO (DAG)
# =============================================================================
class ValidadorEsquemaCulinario:
    @staticmethod
    def validar(datos: dict) -> bool:
        campos_requeridos = ["titulo_plato", "tiempo_total_estimado", "bloques_proceso"]
        if not all(campo in datos for campo in campos_requeridos):
            logger.error("Faltan campos maestros obligatorios en el JSON generado.")
            return False
        
        for idx, bloque in enumerate(datos.get("bloques_proceso", [])):
            if "tipo" not in bloque:
                logger.error(f"El bloque #{idx} no especifica el tipo.")
                return False
            if bloque["tipo"] == "paralelo" and "ramas" not in bloque:
                logger.error(f"El bloque paralelo #{idx} carece de la clave 'ramas'.")
                return False
        return True


# =============================================================================
# MOTOR DE ANÁLISIS SEMÁNTICO (GEMINI AI)
# =============================================================================
class MotorAnalisisSemantico:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("La API Key de Gemini no está configurada.")
        self.client = genai.Client(api_key=api_key)
        self.modelo = "gemini-2.5-flash"
        
    def procesar_texto(self, texto_receta: str) -> dict:
        prompt = """
        Eres un arquitecto de software y chef experto en optimización de procesos culinarios concurrentes.
        Analiza la receta de cocina suministrada y descompón sus pasos en un diagrama de bloques estructurado en formato JSON estricto.
        
        Clasifica las acciones obligatoriamente en uno de estos tres tipos de bloques:
        1. "secuencial": Pasos lineales independientes o preparativos previos.
        2. "paralelo": Tareas independientes que ocurren al mismo tiempo en diferentes estaciones. Deben agruparse dentro de una clave llamada "ramas" (array de objetos con "estacion", "accion" y "duracion_minutos").
        3. "convergencia": El punto donde las ramas paralelas o los pasos previos se unifican en el plato final.

        Devuelve UNICAMENTE un objeto JSON válido que cumpla estrictamente con esta estructura:
        {
          "titulo_plato": "Nombre completo de la receta",
          "tiempo_total_estimado": "X minutos",
          "bloques_proceso": [
            {
              "id": 1,
              "tipo": "secuencial",
              "accion": "Descripción clara del paso",
              "duracion_minutos": 5
            },
            {
              "id": 2,
              "tipo": "paralelo",
              "ramas": [
                {"estacion": "Estación A", "accion": "Acción paralela 1", "duracion_minutos": 10},
                {"estacion": "Estación B", "accion": "Acción paralela 2", "duracion_minutos": 8}
              ]
            },
            {
              "id": 3,
              "tipo": "convergencia",
              "accion": "Unión final y emplatado",
              "duracion_minutos": 2
            }
          ]
        }
        No incluyas etiquetas Markdown (como ```json) ni texto adicional de cortesía. Devuelve exclusivamente la cadena JSON pura.
        """
        
        response = self.client.models.generate_content(
            model=self.modelo,
            contents=[prompt, f"Receta a procesar:\n{texto_receta}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            ),
        )
        return json.loads(response.text.strip())


# =============================================================================
# MOTOR DE RENDERIZADO FRONTEND (HTML / CSS / JS INTERACTIVO)
# =============================================================================
class MotorRenderizadoFrontend:
    def generar_html_interactivo(self, datos: dict) -> str:
        html_salida = f"""
        <div class="facefoodchef-diagrama" style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: auto; padding: 20px; background: #fff; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.05);">
            <h2 style="text-align: center; color: #ff3b3b; margin-bottom: 5px;">{datos.get('titulo_plato')}</h2>
            <p style="text-align: center; font-weight: bold; color: #666; font-size: 1.1em;">⏱️ Tiempo Total Estimado: {datos.get('tiempo_total_estimado')}</p>
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
        html_salida += self._obtener_css()
        html_salida += self._obtener_js()
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
                <button class="ffc-timer-btn" onclick="startTimer(this, {minutos})">⏱️ Iniciar Temporizador ({minutos} min)</button>
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

    def _obtener_css(self) -> str:
        return """
        <style>
            .ffc-bloque { background: #fcfcfc; border-left: 4px solid #333; margin-bottom: 20px; padding: 18px; border-radius: 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.03); }
            .ffc-convergencia { border-left-color: #ff3b3b; background: #fff8f8; }
            .ffc-bloque-paralelo { display: flex; gap: 15px; margin-bottom: 20px; }
            .ffc-rama { flex: 1; background: #f0f6ff; border-left: 4px solid #0066cc; padding: 15px; border-radius: 6px; }
            .ffc-header { font-weight: bold; font-size: 0.85em; text-transform: uppercase; margin-bottom: 8px; color: #555; letter-spacing: 0.5px; }
            .ffc-body { font-size: 1.05em; margin-bottom: 12px; line-height: 1.5; color: #222; }
            .ffc-timer-btn { background: #1a1a1a; color: #fff; border: none; padding: 8px 14px; border-radius: 20px; cursor: pointer; font-weight: 600; width: 100%; transition: background 0.2s; font-size: 0.9em; }
            .ffc-timer-btn:hover { background: #ff3b3b; }
            .ffc-timer-btn.active { background: #ff3b3b; animation: ffc-pulse 1.5s infinite; }
            @keyframes ffc-pulse { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
            @media (max-width: 650px) { .ffc-bloque-paralelo { flex-direction: column; } }
        </style>
        """

    def _obtener_js(self) -> str:
        return """
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
                        btn.classList.remove('active');
                        btn.style.background = "#28a745";
                        try {
                            let speech = new SpeechSynthesisUtterance("Atención cocinero, temporizador finalizado.");
                            window.speechSynthesis.speak(speech);
                        } catch(e) {}
                    }
                }, 1000);
            }
        </script>
        """


# =============================================================================
# GESTOR DE SINCRONIZACIÓN WORDPRESS (REST API)
# =============================================================================
class GestorSincronizacionWordPress:
    def __init__(self, site_url: str, user: str, app_password: str):
        self.endpoint = f"{site_url}/wp-json/wp/v2/receta_pro"
        self.auth = (user, app_password)
        self.headers = {"Content-Type": "application/json"}

    def publicar(self, titulo: str, html_content: str, json_meta: dict) -> Optional[dict]:
        if not self.auth[0] or not self.auth[1]:
            logger.warning("Credenciales de WordPress no provistas. Omitiendo sincronización remota.")
            return None
            
        payload = {
            "title": titulo,
            "content": html_content,
            "status": "publish",
            "meta": {
                "json_diagrama": json.dumps(json_meta, ensure_ascii=False)
            }
        }

        try:
            response = requests.post(self.endpoint, json=payload, headers=self.headers, auth=self.auth, timeout=15)
            if response.status_code == 201:
                return response.json()
            else:
                logger.error(f"WordPress rechazó la petición ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"Excepción de red al conectar con WordPress: {e}")
            return None


# =============================================================================
# INTERFAZ GRÁFICA DE USUARIO (STREAMLIT)
# =============================================================================
def main():
    st.set_page_config(page_title="FaceFoodChef - Generador de Diagramas Culinarios", page_icon="🍳", layout="centered")
    
    st.title("🍳 FaceFoodChef: Generador de Diagramas Culinarios")
    st.markdown("Transforma cualquier texto de receta en un **grafo de bloques interactivo** optimizado para ejecución simultánea en cocina y sincronízalo automáticamente con tu plataforma WordPress.")

    # Verificación preventiva de la clave de IA
    if not GEMINI_API_KEY:
        st.error("🚨 **Falta configurar la API Key de Gemini.** Añádela en los Secrets de Streamlit o como variable de entorno local (`GEMINI_API_KEY`).")
        st.stop()

    receta_por_defecto = """Spaghetti alla Carbonara Tradicional:
Ingredientes: 200g espaguetis, 100g panceta curada, 2 yemas de huevo, queso pecorino rallado.
Paso 1: Poner a calentar una olla con abundante agua y sal hasta que hierva, después cocer los espaguetis durante 10 minutos exactos.
Paso 2: En paralelo, cortar la panceta en tiras finas y dorarla a fuego medio en una sartén durante 8 minutos sin aceite añadido.
Paso 3: En un bol, batir enérgicamente las yemas de huevo con el queso pecorino.
Paso 4: Convergencia: Escurrir la pasta, incorporarla a la sartén junto a la panceta fuera del fuego y verter la mezcla de huevo y queso para emulsionar de inmediato."""

    texto_ingresado = st.text_area("✍️ Introduce o pega el texto de tu receta:", value=receta_por_defecto, height=200)

    col1, col2 = st.columns([1, 1])
    sincronizar_wp = col1.checkbox("Sincronizar automáticamente con WordPress", value=False)
    
    if st.button("🚀 Generar Diagrama de Bloques", type="primary", use_container_width=True):
        if not texto_ingresado.strip():
            st.warning("Por favor, introduce un texto de receta válido.")
            return

        with st.spinner("Analizando la semántica culinaria con Gemini y generando el grafo..."):
            try:
                analizador = MotorAnalisisSemantico(GEMINI_API_KEY)
                validador = ValidadorEsquemaCulinario()
                renderizador = MotorRenderizadoFrontend()
                
                # 1. Extracción de IA
                datos_grafo = analizador.procesar_texto(texto_ingresado)
                
                # 2. Validación de esquema
                if not validador.validar(datos_grafo):
                    st.error("El modelo devolvió una estructura no válida. Inténtalo de nuevo.")
                    return
                
                # 3. Renderizado de interfaz visual HTML/JS
                html_resultado = renderizador.generar_html_interactivo(datos_grafo)
                
                st.success("¡Diagrama de bloques generado con éxito!")
                
                # 4. Sincronización opcional con WordPress
                if sincronizar_wp:
                    with st.spinner("Publicando entrada y metadatos en WordPress..."):
                        wp_manager = GestorSincronizacionWordPress(WP_SITE_URL, WP_USER, WP_APP_PASSWORD)
                        res_wp = wp_manager.publicar(datos_grafo.get("titulo_plato", "Receta Automatizada"), html_resultado, datos_grafo)
                        if res_wp:
                            st.success(f"✅ ¡Publicado en WordPress con éxito! ID: {res_wp.get('id')} | [Ver enlace]({res_wp.get('link')})")
                        else:
                            st.warning("⚠️ El diagrama se generó localmente, pero falló la sincronización con WordPress. Revisa las credenciales en los ajustes.")

                st.markdown("---")
                st.subheader("👀 Vista Previa del Diagrama Interactivo:")
                st.components.v1.html(html_resultado, height=550, scrolling=True)
                
                with st.expander("Ver código JSON técnico subyacente (DAG):"):
                    st.json(datos_grafo)

            except Exception as e:
                st.error(f"Se ha producido un error crítico durante el pipeline de ejecución: {e}")
                logger.error(f"Excepción en la app: {e}")

if __name__ == "__main__":
    main()
