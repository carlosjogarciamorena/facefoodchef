import os
import json
import time
import logging
from typing import Dict, Any, Optional
import requests
from google import genai
from google.genai import types

# =============================================================================
# 1. CONFIGURACIÓN Y LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("facefoodchef_engine.log")]
)
logger = logging.getLogger("FaceFoodChef-Core")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "TU_GEMINI_API_KEY")
WP_SITE_URL = os.getenv("WP_SITE_URL", "https://facefoodchef.com").rstrip("/")
WP_USER = os.getenv("WP_USER", "usuario_wp")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "password_aplicacion")


# =============================================================================
# 2. VALIDACIÓN DEL ESQUEMA (DAG)
# =============================================================================
class ValidadorEsquemaCulinario:
    """Garantiza que la IA devuelva una estructura de datos perfecta antes de renderizar."""
    
    @staticmethod
    def validar(datos: dict) -> bool:
        campos_requeridos = ["titulo_plato", "tiempo_total_estimado", "bloques_proceso"]
        if not all(campo in datos for campo in campos_requeridos):
            logger.error("Faltan campos maestros en el JSON.")
            return False
        
        for idx, bloque in enumerate(datos.get("bloques_proceso", [])):
            if "tipo" not in bloque:
                return False
            
            if bloque["tipo"] == "paralelo" and "ramas" not in bloque:
                logger.error(f"El bloque paralelo {idx} no contiene 'ramas'.")
                return False
                
        return True


# =============================================================================
# 3. MOTOR DE ANÁLISIS SEMÁNTICO (IA)
# =============================================================================
class MotorAnalisisSemantico:
    """Conecta con Gemini para traducir lenguaje natural a un Grafo Acíclico Dirigido."""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.modelo = "gemini-2.5-flash"
        
    def procesar_texto(self, texto_receta: str) -> dict:
        prompt = """
        Eres un arquitecto de software y chef. Convierte esta receta en un diagrama de bloques JSON.
        Clasifica estrictamente en:
        1. "secuencial": Tareas lineales.
        2. "paralelo": Tareas simultáneas agrupadas en "ramas".
        3. "convergencia": Unión de tareas previas.

        Estructura requerida:
        {
          "titulo_plato": "Nombre",
          "tiempo_total_estimado": "Minutos",
          "bloques_proceso": [
            {
              "id": 1,
              "tipo": "secuencial",
              "accion": "Paso 1",
              "duracion_minutos": 5
            },
            {
              "id": 2,
              "tipo": "paralelo",
              "ramas": [
                {"estacion": "A", "accion": "Hervir", "duracion_minutos": 10},
                {"estacion": "B", "accion": "Sofreír", "duracion_minutos": 8}
              ]
            }
          ]
        }
        Devuelve SOLO el JSON.
        """
        logger.info("Solicitando análisis de la receta a Gemini...")
        response = self.client.models.generate_content(
            model=self.modelo,
            contents=[prompt, f"Receta:\n{texto_receta}"],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            ),
        )
        return json.loads(response.text.strip())


# =============================================================================
# 4. MOTOR DE RENDERIZADO FRONTEND (NUEVA FUNCIONALIDAD CLAVE)
# =============================================================================
class MotorRenderizadoFrontend:
    """
    Toma el JSON estructurado y genera el código HTML, CSS y JS necesario para 
    crear la interfaz interactiva con temporizadores en WordPress.
    """
    
    def generar_html_interactivo(self, datos: dict) -> str:
        logger.info("Generando interfaz de usuario (HTML/JS) a partir del diagrama...")
        
        html_salida = f"""
        <div class="facefoodchef-diagrama" style="font-family: sans-serif; max-width: 800px; margin: auto;">
            <h2 style="text-align: center; color: #ff3b3b;">{datos.get('titulo_plato')}</h2>
            <p style="text-align: center; font-weight: bold;">⏱️ Tiempo Total: {datos.get('tiempo_total_estimado')}</p>
            <hr style="border: 1px solid #eee; margin-bottom: 20px;">
        """
        
        for bloque in datos.get("bloques_proceso", []):
            tipo = bloque.get("tipo")
            b_id = bloque.get("id")
            
            if tipo in ["secuencial", "convergencia"]:
                html_salida += self._renderizar_bloque_lineal(bloque, b_id, tipo)
            elif tipo == "paralelo":
                html_salida += self._renderizar_bloque_paralelo(bloque, b_id)
                
        html_salida += "</div>"
        
        # Añadir CSS y JS inyectado
        html_salida += self._obtener_css()
        html_salida += self._obtener_js()
        
        return html_salida

    def _renderizar_bloque_lineal(self, bloque: dict, b_id: int, tipo: str) -> str:
        accion = bloque.get("accion", "")
        minutos = bloque.get("duracion_minutos", 0)
        clase = "ffc-secuencial" if tipo == "secuencial" else "ffc-convergencia"
        icono = "⬇️" if tipo == "secuencial" else "🔗"
        
        return f"""
        <div class="ffc-bloque {clase}" id="bloque-{b_id}">
            <div class="ffc-header">{icono} {tipo.capitalize()}</div>
            <div class="ffc-body">{accion}</div>
            <div class="ffc-footer">
                <button class="ffc-timer-btn" onclick="startTimer(this, {minutos})">⏱️ Iniciar {minutos} min</button>
            </div>
        </div>
        """

    def _renderizar_bloque_paralelo(self, bloque: dict, b_id: int) -> str:
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
            .ffc-bloque { background: #f9f9f9; border-left: 4px solid #333; margin-bottom: 20px; padding: 15px; border-radius: 4px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
            .ffc-convergencia { border-left-color: #ff3b3b; background: #fff5f5; }
            .ffc-bloque-paralelo { display: flex; gap: 15px; margin-bottom: 20px; }
            .ffc-rama { flex: 1; background: #f0f7ff; border-left: 4px solid #0066cc; padding: 15px; border-radius: 4px; }
            .ffc-header { font-weight: bold; font-size: 0.9em; text-transform: uppercase; margin-bottom: 10px; color: #555; }
            .ffc-body { font-size: 1.1em; margin-bottom: 15px; line-height: 1.5; }
            .ffc-timer-btn { background: #222; color: #fff; border: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-weight: bold; width: 100%; transition: background 0.3s; }
            .ffc-timer-btn:hover { background: #ff3b3b; }
            .ffc-timer-btn.active { background: #ff3b3b; animation: pulse 1.5s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.8; } 100% { opacity: 1; } }
            @media (max-width: 600px) { .ffc-bloque-paralelo { flex-direction: column; } }
        </style>
        """

    def _obtener_js(self) -> str:
        return """
        <script>
            function startTimer(btn, minutes) {
                if(btn.classList.contains('active')) return;
                btn.classList.add('active');
                let seconds = minutes * 60;
                let originalText = btn.innerHTML;
                
                let interval = setInterval(() => {
                    seconds--;
                    let m = Math.floor(seconds / 60);
                    let s = seconds % 60;
                    btn.innerHTML = `⏳ ${m}:${s.toString().padStart(2, '0')}`;
                    
                    if (seconds <= 0) {
                        clearInterval(interval);
                        btn.innerHTML = "✅ ¡Listo!";
                        btn.classList.remove('active');
                        btn.style.background = "#28a745";
                        // Aquí se puede integrar la API de voz Web Speech
                        let speech = new SpeechSynthesisUtterance("Atención, tiempo finalizado para este paso.");
                        window.speechSynthesis.speak(speech);
                    }
                }, 1000);
            }
        </script>
        """


# =============================================================================
# 5. GESTOR DE WORDPRESS (REST API)
# =============================================================================
class GestorSincronizacionWordPress:
    """Publica la receta: el HTML visual al contenido y el JSON técnico a ACF."""
    
    def __init__(self, site_url: str, user: str, app_password: str):
        self.endpoint = f"{site_url}/wp-json/wp/v2/receta_pro"
        self.auth = (user, app_password)
        self.headers = {"Content-Type": "application/json"}

    def publicar(self, titulo: str, html_content: str, json_meta: dict) -> Optional[int]:
        logger.info(f"Subiendo '{titulo}' a WordPress...")
        
        payload = {
            "title": titulo,
            "content": html_content,      # El usuario ve el diagrama interactivo
            "status": "publish",
            "meta": {
                "json_diagrama": json.dumps(json_meta, ensure_ascii=False) # El JSON queda guardado para el futuro
            }
        }

        try:
            response = requests.post(self.endpoint, json=payload, headers=self.headers, auth=self.auth, timeout=20)
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Éxito -> ID: {data.get('id')} | URL: {data.get('link')}")
                return data.get('id')
            else:
                logger.error(f"Error WP ({response.status_code}): {response.text}")
                return None
        except Exception as e:
            logger.error(f"Fallo de conexión: {e}")
            return None


# =============================================================================
# 6. ORQUESTADOR PRINCIPAL
# =============================================================================
class FaceFoodChefEngine:
    """Controlador que unifica todas las piezas del sistema."""
    
    def __init__(self):
        self.ia = MotorAnalisisSemantico(GEMINI_API_KEY)
        self.validador = ValidadorEsquemaCulinario()
        self.frontend = MotorRenderizadoFrontend()
        self.wp = GestorSincronizacionWordPress(WP_SITE_URL, WP_USER, WP_APP_PASSWORD)

    def ejecutar(self, receta_texto: str):
        logger.info("=== INICIANDO PIPELINE DE CONVERSIÓN ===")
        
        # 1. Obtener JSON de Gemini
        diagrama_json = self.ia.procesar_texto(receta_texto)
        
        # 2. Validar estructura
        if not self.validador.validar(diagrama_json):
            logger.critical("Proceso abortado por esquema JSON inválido.")
            return
            
        # 3. Generar HTML/JS interactivo
        html_interactivo = self.frontend.generar_html_interactivo(diagrama_json)
        
        # 4. Publicar en WordPress
        titulo = diagrama_json.get("titulo_plato", "Receta sin Título")
        self.wp.publicar(titulo, html_interactivo, diagrama_json)
        
        logger.info("=== PIPELINE COMPLETADO ===")


# =============================================================================
# 7. EJECUCIÓN (CLI)
# =============================================================================
if __name__ == "__main__":
    receta_entrada = """
    Tacos Al Pastor Express:
    Ingredientes: 500g carne de cerdo, tortillas, piña, cebolla, cilantro, marinada (achiote, vinagre).
    Primero, preparar la marinada mezclando el achiote con vinagre y especias, embadurnar la carne y dejar reposar 15 minutos.
    Pasado el tiempo, arrancar dos procesos a la vez:
    Por un lado, en una plancha bien caliente, asar la carne junto con la piña cortada en cubos durante 10 minutos.
    Por otro lado, en un comal o sartén pequeña, calentar las tortillas de maíz durante 3 minutos y picar finamente la cebolla y el cilantro.
    Finalmente, montar los tacos colocando la carne y piña sobre las tortillas calientes, espolvorear la cebolla y cilantro fresco, y servir inmediatamente.
    """
    
    motor = FaceFoodChefEngine()
    motor.ejecutar(receta_entrada)
