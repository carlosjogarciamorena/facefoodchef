"""FaceFoodChef.com - Motor de Diagramas Culinarios (Streamlit + Gemini)."""
from __future__ import annotations
 
import ipaddress
import json
import os
import re
import socket
import time
import unicodedata
from html import escape
from io import BytesIO
from urllib.parse import urlparse
 
import requests
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from google import genai
from google.genai import types
from google.genai.errors import APIError
from recipe_scrapers import scrape_me
 
try:
    from dotenv import load_dotenv
 
    load_dotenv()
except ImportError:
    pass
 
try:
    import docx
 
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
 
try:
    from pptx import Presentation
 
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False
 
# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
MODELOS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]
MAX_CHARS_RECETA = 30_000
MAX_MB_ARCHIVO = 15
NIVELES = {"SUPERVIVIENTE": "verde", "CUALIFICADO": "amarillo", "DOCTOR": "rojo"}
MIME_IMAGENES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
 
ESQUEMA_EJEMPLO = {
    "nombre_receta": "String",
    "origen_receta": "String",
    "nivel_dificultad": "Superviviente Básico",
    "ingredientes": ["400 g de harina"],
    "utensilios_menaje": ["Cuchillo", "Sartén"],
    "pasos_previos": ["Cortar vegetales"],
    "bloques_proceso": [
        {
            "tipo": "secuencial",
            "es_critico": False,
            "accion": "Descripción del paso",
            "utensilios": ["Sartén"],
            "tiempo": "5 min",
            "duracion_minutos": 5,
            "temperatura": "180 ºC",
        },
        {
            "tipo": "paralelo",
            "es_critico": False,
            "ramas": [
                {
                    "nombre": "Salsa",
                    "accion": "Reducir el líquido",
                    "utensilios": ["Cazo"],
                    "tiempo": "10 min",
                    "duracion_minutos": 10,
                    "temperatura": "90 ºC",
                }
            ],
        },
    ],
    "recomendaciones": ["Punto crítico de cocción"],
    "texto_voz": "Resumen narrado del proceso",
    "maridaje": {
        "vinos": ["Vino 1", "Vino 2", "Vino 3"],
        "cervezas": ["Cerveza 1", "Cerveza 2", "Cerveza 3"],
    },
}
 
 
class GeminiError(Exception):
    def __init__(self, mensaje: str, code: int | None = None):
        super().__init__(mensaje)
        self.code = code
 
 
# ---------------------------------------------------------------------------
# Estilos de la app Streamlit
# ---------------------------------------------------------------------------
CSS_STREAMLIT = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600;700&family=Montserrat:wght@700;900&display=swap');
 
.stApp, .block-container, [data-testid="stSidebar"] {
    background-color: #36393F !important;
    color: #E2E8F0 !important;
    font-family: 'Inter', sans-serif !important;
}
footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent !important; }
 
.stTextArea textarea, .stTextInput input, .stNumberInput input {
    background-color: #2C2F33 !important;
    color: #E2E8F0 !important;
    border: 1px solid #4F545C !important;
    border-radius: 6px !important;
    font-size: 15px !important;
    font-family: 'Inter', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus, .stNumberInput input:focus {
    border-color: #FFB300 !important;
    box-shadow: none !important;
}
.stButton > button {
    background: #00FF66 !important;
    color: #1E1E1E !important;
    font-family: 'Montserrat', sans-serif !important;
    font-weight: 900 !important;
    font-size: 15px !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 12px 24px !important;
    width: 100%;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: background 0.2s ease !important;
}
.stButton > button:hover { background: #00CC52 !important; }
.streamlit-expanderHeader {
    background-color: #2C2F33 !important;
    color: #E2E8F0 !important;
    border-radius: 6px !important;
    border: 1px solid #4F545C !important;
    font-family: 'Montserrat', sans-serif !important;
}
h1, h2, h3, h4, h5, h6 {
    font-family: 'Montserrat', sans-serif !important;
    color: #FFFFFF !important;
    text-transform: uppercase;
}
</style>
"""
 
TITULO_HTML = (
    "<h1 style='text-align:center;color:#FFFFFF;font-family:Montserrat,sans-serif;font-weight:900;"
    "letter-spacing:2px;margin-bottom:0;font-size:clamp(20px,4vw,32px);'>FACEFOODCHEF "
    "<span style='font-size:clamp(10px,2vw,14px);background:#00FF66;color:#1E1E1E;padding:4px 10px;"
    "border-radius:4px;vertical-align:middle;letter-spacing:1px;'>MOTOR DE DIAGRAMAS</span></h1>"
    "<p style='text-align:center;color:#E2E8F0;font-size:clamp(13px,2vw,15px);margin-bottom:30px;"
    "font-family:Inter,sans-serif;'>Convierte recetas textuales en diagramas de flujo de producción culinaria</p>"
)
 
# ---------------------------------------------------------------------------
# Estilos y JS del dashboard generado (HTML independiente)
# ---------------------------------------------------------------------------
CSS_DASHBOARD = """
:root{--verde:#00FF66;--amarillo:#FFB300;--rojo:#EF4444;--dorado:#FFD700;
--bg:#36393F;--card:#2C2F33;--borde:#4F545C;--texto:#E2E8F0;}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--texto);font-family:'Inter',sans-serif;padding:12px;margin:0}
.hub{max-width:900px;margin:auto}
.mono{font-family:'JetBrains Mono',monospace}
h1,h2,h3{font-family:'Montserrat',sans-serif;text-transform:uppercase;margin:0}
.card{--c:var(--borde);background:var(--card);border-left:6px solid var(--c);border-radius:6px;padding:16px;margin-bottom:16px}
.card.verde{--c:var(--verde)} .card.amarillo{--c:var(--amarillo)}
.card.rojo{--c:var(--rojo)} .card.dorado{--c:var(--dorado)}
.card-head{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--borde);
padding-bottom:8px;margin-bottom:12px;flex-wrap:wrap;gap:8px}
.card-head h3{font-size:clamp(14px,2.5vw,16px);color:var(--c)}
.hero{text-align:center;padding:20px;border-radius:8px}
.hero h1{color:#fff;font-size:clamp(18px,4vw,24px);margin:10px 0 8px;font-weight:900}
.pills{display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-top:10px;font-size:clamp(12px,2vw,14px)}
.pill{background:var(--bg);padding:6px 12px;border-radius:4px}
.tag{display:inline-block;font-size:11px;font-weight:700;color:var(--card);background:var(--c);
padding:3px 8px;border-radius:2px;text-transform:uppercase;font-family:'JetBrains Mono',monospace}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:var(--bg);padding:8px 12px;border-radius:4px;font-size:clamp(12px,2vw,14px)}
ul.lista{margin:12px 0 0;padding-left:18px;font-size:clamp(13px,2.2vw,15px);line-height:1.6}
ul.lista li{margin-bottom:6px}
.accion{font-size:clamp(13px,2.2vw,15px);font-weight:500;color:#fff;margin:8px 0;line-height:1.5}
.meta{font-size:clamp(11px,2vw,13px);margin-bottom:10px}
.timer-row{display:flex;justify-content:space-between;align-items:center;background:var(--bg);
padding:8px 12px;border-radius:4px;flex-wrap:wrap;gap:6px}
.timer{font-size:clamp(12px,2vw,14px);color:var(--amarillo);font-weight:600}
.paralelo{display:flex;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.paralelo .card{flex:1;min-width:260px;margin-bottom:0}
.flecha{text-align:center;margin:4px 0 10px;font-size:18px;font-weight:bold}
.titulo-diagrama{color:#fff;font-size:clamp(16px,3vw,18px);margin-bottom:16px;border-bottom:2px solid var(--rojo);
padding-bottom:6px;display:inline-block}
.widget{background:var(--card);border-radius:6px;padding:16px;text-align:center;margin-bottom:16px}
.btn{border:none;border-radius:4px;cursor:pointer;font-family:'Montserrat',sans-serif;font-weight:900;
text-transform:uppercase;transition:filter .2s,transform .1s}
.btn:hover{filter:brightness(.9)} .btn:active{transform:scale(.96)}
.btn-store{background:var(--verde);color:#1E1E1E;padding:8px 14px;font-size:11px;box-shadow:0 2px 4px rgba(0,0,0,.2)}
.btn-rojo{background:var(--rojo);color:#fff;padding:6px 12px;font-size:11px}
.btn-voz{background:var(--rojo);color:#fff;padding:10px 16px;font-size:12px;margin:4px}
.btn-gris{background:var(--borde);color:#fff;padding:10px 16px;font-size:12px;margin:4px}
.pie{text-align:center;color:#9AA0A6;font-size:11px;margin-top:24px;border-top:1px solid var(--borde);
padding-top:14px;word-break:break-all}
.pie a{color:#9AA0A6}
"""
 
JS_DASHBOARD = """
const textoVoz = __TEXTO_VOZ__;
const timers = {};
let audioCtx = null;
 
function getAudio() {
  if (!audioCtx) {
    const C = window.AudioContext || window.webkitAudioContext;
    if (C) audioCtx = new C();
  }
  if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}
 
function reproducir(btn) {
  if (!('speechSynthesis' in window)) return alert('Sintetizador no soportado.');
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(textoVoz);
  u.lang = 'es-ES';
  u.rate = 0.95;
  btn.textContent = '🔊 Reproduciendo...';
  u.onend = u.onerror = () => { btn.textContent = '🎧 Escuchar Pasos'; };
  window.speechSynthesis.speak(u);
}
 
function detener() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  const btn = document.getElementById('btnVoz');
  if (btn) btn.textContent = '🎧 Escuchar Pasos';
}
 
function iniciarTemporizador(id, minutos) {
  getAudio(); // el gesto del usuario desbloquea el audio para el aviso final
  const el = document.getElementById(id);
  clearInterval(timers[id]);
  const fin = Date.now() + minutos * 60000;
  const pintar = () => {
    const rest = Math.max(0, Math.ceil((fin - Date.now()) / 1000));
    if (rest === 0) {
      clearInterval(timers[id]);
      el.textContent = '¡FINALIZADO!';
      sonarAlerta();
      return;
    }
    el.textContent = Math.floor(rest / 60) + 'm ' + String(rest % 60).padStart(2, '0') + 's';
  };
  pintar();
  timers[id] = setInterval(pintar, 250); // basado en la hora real: no se descuadra
}
 
function sonarAlerta() {
  const ctx = getAudio();
  if (!ctx) return;
  for (let i = 0; i < 10; i++) {
    const t = ctx.currentTime + i * 0.35;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, t);
    gain.gain.setValueAtTime(0.3, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.2);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.2);
  }
}
"""
 
 
# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def e(valor) -> str:
    """Escapa cualquier valor para insertarlo de forma segura en HTML."""
    return escape("" if valor is None else str(valor))
 
 
def api_key_por_defecto() -> str:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.getenv("GEMINI_API_KEY", "")
 
 
def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", texto.lower()).strip("_") or "receta"
 
 
def minutos(valor, defecto: int = 5) -> int:
    try:
        return max(0, int(float(valor)))
    except (TypeError, ValueError):
        return defecto
 
 
def lista_str(valor) -> list[str]:
    if not isinstance(valor, (list, tuple)):
        return []
    return [str(x).strip() for x in valor if str(x).strip()]
 
 
def clasificar_entrada(texto: str) -> tuple[str, str]:
    """Devuelve (url, texto_receta). Si se pegó una URL (incluso repetida), devuelve la última."""
    texto = texto.strip()
    if not texto:
        return "", ""
    if re.match(r"https?://", texto):
        trozos = [t.strip() for t in re.split(r"(?=https?://)", texto) if t.strip()]
        if all(not re.search(r"\s", t) for t in trozos):
            return trozos[-1], ""
    return "", texto
 
 
def url_es_segura(url: str) -> bool:
    """Evita SSRF: solo http(s) y hosts que no resuelvan a IPs internas."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        for info in socket.getaddrinfo(p.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
    except (socket.gaierror, ValueError):
        return False
    return True
 
 
@st.cache_data(ttl=3600, show_spinner=False)
def extraer_texto_de_url(url: str) -> str:
    url = url.strip()
    if not url_es_segura(url):
        raise ValueError("La URL no es válida o no está permitida.")
    try:
        scraper = scrape_me(url)
        try:
            pasos = scraper.instructions_list()
        except Exception:
            pasos = [p for p in scraper.instructions().split("\n") if p.strip()]
        return (
            f"Receta de {url}:\nIngredientes: {', '.join(scraper.ingredients())}\n"
            "Pasos:\n" + "\n".join(pasos)
        )
    except Exception:
        pass
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
            el.decompose()
        return f"Contenido de {url}:\n" + soup.get_text(separator="\n", strip=True)
    except Exception as exc:
        raise ValueError(
            f"Error al procesar la URL (comprueba que sea accesible o pega el texto directamente): {exc}"
        ) from exc
 
 
def leer_archivo(archivo) -> tuple[str, bytes | None, str | None]:
    """Devuelve (texto, bytes_multimodal, mime). Lanza ValueError si no se puede leer."""
    if archivo.size > MAX_MB_ARCHIVO * 1024 * 1024:
        raise ValueError(f"El archivo supera el límite de {MAX_MB_ARCHIVO} MB.")
    ext = archivo.name.rsplit(".", 1)[-1].lower()
    datos = archivo.getvalue()
    if ext == "txt":
        return datos.decode("utf-8", errors="replace"), None, None
    if ext == "docx":
        if not HAS_DOCX:
            raise ValueError("Falta la librería python-docx para leer archivos Word.")
        d = docx.Document(BytesIO(datos))
        partes = [p.text for p in d.paragraphs if p.text.strip()]
        for tabla in d.tables:
            for fila in tabla.rows:
                partes.append(" | ".join(c.text.strip() for c in fila.cells))
        return "\n".join(partes), None, None
    if ext == "pptx":
        if not HAS_PPTX:
            raise ValueError("Falta la librería python-pptx para leer presentaciones.")
        prs = Presentation(BytesIO(datos))
        return (
            "\n".join(
                p.text
                for slide in prs.slides
                for shape in slide.shapes
                if shape.has_text_frame
                for p in shape.text_frame.paragraphs
                if p.text.strip()
            ),
            None,
            None,
        )
    if ext == "pdf":
        return "", datos, "application/pdf"
    if ext in MIME_IMAGENES:
        return "", datos, MIME_IMAGENES[ext]
    raise ValueError("Formato de archivo no soportado.")
 
 
# ---------------------------------------------------------------------------
# Gemini
# ---------------------------------------------------------------------------
def construir_prompt(comensales: int) -> str:
    esquema = json.dumps(ESQUEMA_EJEMPLO, ensure_ascii=False, indent=2)
    return f"""Eres un experto programador de flujos culinarios y maestro chef.
Transforma la receta dada en una estructura JSON optimizada para generar un diagrama de flujo paso a paso.
 
Recalcula las cantidades exactamente para {comensales} COMENSALES.
 
EVALUACIÓN DE NIVEL DE DIFICULTAD:
Asigna obligatoriamente uno de estos tres niveles en el campo "nivel_dificultad" según la complejidad técnica:
1. "Superviviente Básico" (recetas sencillas, sin técnicas complejas, pocos ingredientes, rápida ejecución).
2. "Cocinero Cualificado" (cierta soltura en cocina, tiempos de cocción combinados, sofritos elaborados o técnicas moderadas).
3. "Doctor Chef" (técnicas exigentes, control estricto de temperaturas, emulsiones delicadas, limpieza compleja o múltiples procesos paralelos).
 
REGLAS ESTRUCTURALES Y JSON:
1. UNIDADES: abreviadas (g, kg, ml, l, ºC, min). Escribe "cucharada" y "cucharadita" completas. Evita términos ambiguos ("al gusto").
2. MODULARIZACIÓN:
   - Separa la lista de "utensilios_menaje".
   - Separa la lista de "pasos_previos" (Mise en place).
3. BLOQUES DE PROCESO:
   - "tipo": "secuencial", "paralelo" o "convergencia".
   - "es_critico": booleano (true si requiere especial precaución técnica o de seguridad).
   - "duracion_minutos": número entero con los minutos estimados de ese bloque.
4. MARIDAJE:
   - Evalúa todas las Denominaciones de Origen (sin restricción geográfica).
   - Genera EXACTAMENTE 3 propuestas de vinos indicando tipo o Denominación de Origen idónea.
   - Genera EXACTAMENTE 3 propuestas de cervezas acordes al plato.
5. Devuelve EXCLUSIVAMENTE un objeto JSON válido con la estructura indicada, sin texto fuera del JSON.
 
JSON esperado (ejemplo de estructura):
{esquema}
"""
 
 
def parsear_json(texto: str) -> dict:
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.IGNORECASE)
    datos = json.loads(texto)  # json.JSONDecodeError es subclase de ValueError
    if not isinstance(datos, dict):
        raise ValueError("El modelo no devolvió un objeto JSON.")
    return datos
 
 
def llamar_gemini(client, modelos: list[str], contents, config) -> dict:
    """Prueba cada modelo con reintentos para 5xx/JSON inválido; salta de modelo en 429."""
    ultimo_error, ultimo_code = "Sin respuesta del modelo.", None
    for modelo in modelos:
        for intento in range(3):
            try:
                resp = client.models.generate_content(model=modelo, contents=contents, config=config)
                if not resp.text:
                    ultimo_error = "Respuesta vacía del modelo."
                    continue
                return parsear_json(resp.text)
            except APIError as exc:
                ultimo_error, ultimo_code = str(exc), getattr(exc, "code", None)
                if ultimo_code == 429:
                    break  # cuota agotada: probar otro modelo
                if ultimo_code in (500, 503, 504):
                    if intento < 2:
                        time.sleep(3 * (intento + 1))
                    continue
                break
            except ValueError as exc:  # JSON mal formado
                ultimo_error, ultimo_code = f"JSON inválido: {exc}", None
                continue
    raise GeminiError(ultimo_error, ultimo_code)
 
 
def mensaje_error_gemini(exc: GeminiError) -> str:
    if exc.code == 429:
        return ("⚠️ **Límite de cuota alcanzado (Error 429).** Has superado las solicitudes "
                "permitidas por la API de Google.")
    if exc.code in (500, 503, 504):
        return ("⚠️ **Servidores con alta demanda.** Google tiene tráfico elevado; "
                "vuelve a pulsar el botón en unos segundos.")
    return f"No se pudo obtener una respuesta válida del modelo: {exc}"
 
 
# ---------------------------------------------------------------------------
# Normalización de datos del modelo
# ---------------------------------------------------------------------------
def _paso(p: dict) -> dict:
    dur = minutos(p.get("duracion_minutos"))
    return {
        "nombre": str(p.get("nombre") or ""),
        "accion": str(p.get("accion") or ""),
        "utensilios": lista_str(p.get("utensilios")),
        "tiempo": str(p.get("tiempo") or f"{dur} min"),
        "duracion": dur,
        "temperatura": str(p.get("temperatura") or ""),
    }
 
 
def normalizar_datos(d: dict) -> dict:
    bloques = []
    for b in d.get("bloques_proceso") or []:
        if not isinstance(b, dict):
            continue
        critico = bool(b.get("es_critico"))
        tipo = str(b.get("tipo", "")).lower()
        if tipo == "paralelo":
            ramas = [_paso(r) for r in (b.get("ramas") or []) if isinstance(r, dict)]
            if ramas:
                bloques.append({"tipo": "paralelo", "es_critico": critico, "ramas": ramas})
        else:
            tipo = "convergencia" if tipo == "convergencia" else "secuencial"
            bloques.append({**_paso(b), "tipo": tipo, "es_critico": critico})
    mar = d.get("maridaje") if isinstance(d.get("maridaje"), dict) else {}
    return {
        "nombre_receta": str(d.get("nombre_receta") or "Receta Culinaria"),
        "origen_receta": str(d.get("origen_receta") or ""),
        "nivel_dificultad": str(d.get("nivel_dificultad") or "Cocinero Cualificado"),
        "ingredientes": lista_str(d.get("ingredientes")),
        "utensilios_menaje": lista_str(d.get("utensilios_menaje")),
        "pasos_previos": lista_str(d.get("pasos_previos")),
        "bloques_proceso": bloques,
        "recomendaciones": lista_str(d.get("recomendaciones")),
        "texto_voz": str(d.get("texto_voz") or ""),
        "vinos": lista_str(mar.get("vinos")),
        "cervezas": lista_str(mar.get("cervezas")),
    }
 
 
def calcular_tiempo_total(bloques: list[dict], minutos_prep: int = 10) -> int:
    total = minutos_prep
    for b in bloques:
        if b["tipo"] == "paralelo":
            total += max((r["duracion"] for r in b["ramas"]), default=0)
        else:
            total += b["duracion"]
    return total
 
 
# ---------------------------------------------------------------------------
# Generación del HTML
# ---------------------------------------------------------------------------
def _chips(items: list[str]) -> str:
    return "".join(f'<span class="chip mono">{e(i)}</span>' for i in items)
 
 
def _ul(items: list[str], vacio: str = "Sin opciones disponibles.") -> str:
    if not items:
        return f"<li>{e(vacio)}</li>"
    return "".join(f"<li>{e(i)}</li>" for i in items)
 
 
def _tarjeta_paso(paso: dict, timer_id: str, color: str, etiqueta: str) -> str:
    temp = f" | 🌡️ {e(paso['temperatura'])}" if paso["temperatura"] else ""
    utens = ", ".join(e(u) for u in paso["utensilios"]) or "N/A"
    return f"""
    <div class="card {color}">
      <span class="tag">{e(etiqueta)}</span>
      <div class="accion mono">{e(paso['accion'])}</div>
      <div class="meta mono">🛠️ <b>Utensilios:</b> {utens}</div>
      <div class="timer-row">
        <div class="timer mono">⏱️ <span id="{timer_id}">{e(paso['tiempo'])}</span>{temp}</div>
        <button class="btn btn-rojo" onclick="iniciarTemporizador('{timer_id}', {paso['duracion']})">⏳ INICIAR</button>
      </div>
    </div>"""
 
 
def _diagrama(bloques: list[dict]) -> str:
    partes = ['<h3 class="titulo-diagrama">4. Diagrama de Ejecución y Flujo</h3>']
    for i, b in enumerate(bloques):
        color = "rojo" if b["es_critico"] else "amarillo"
        if b["tipo"] == "paralelo":
            tarjetas = "".join(
                _tarjeta_paso(
                    r, f"timer_{i}_{j}", color,
                    "⚙️ PARALELO: " + (r["nombre"] or f"Subproceso {j + 1}"),
                )
                for j, r in enumerate(b["ramas"])
            )
            partes.append(f'<div class="paralelo">{tarjetas}</div>')
        else:
            etiqueta = "UNIÓN / CONVERGENCIA" if b["tipo"] == "convergencia" else f"PASO {i + 1}"
            partes.append(_tarjeta_paso(b, f"timer_{i}", color, etiqueta))
        if i < len(bloques) - 1:
            partes.append('<div class="flecha" style="color:var(--amarillo)">↓</div>')
    partes.append(
        """
    <div class="flecha" style="color:var(--dorado)">↓</div>
    <div class="card dorado" style="text-align:center">
      <span class="tag">RESULTADO FINAL</span>
      <h3 style="color:var(--dorado);margin:12px 0;font-weight:900;font-size:clamp(15px,2.8vw,18px)">🍽️ PLATO LISTO PARA SERVIR</h3>
      <button class="btn btn-store" onclick="alert('Enlace a técnicas de emplatado o equipo...')">✨ EMPLATADO</button>
    </div>"""
    )
    return "".join(partes)
 
 
def _tarjeta_tienda(color: str, titulo: str, boton: str, mensaje: str, cuerpo: str) -> str:
    return f"""
    <div class="card {color}">
      <div class="card-head">
        <h3>{titulo}</h3>
        <button class="btn btn-store" onclick="alert('{mensaje}')">{boton}</button>
      </div>
      {cuerpo}
    </div>"""
 
 
def generar_html_dashboard(d: dict, origen: str, comensales: int) -> str:
    prep_est = len(d["pasos_previos"]) * 3 if d["pasos_previos"] else 10
    tiempo_total = calcular_tiempo_total(d["bloques_proceso"], prep_est)
    nivel_up = d["nivel_dificultad"].upper()
    color_nivel = next((c for k, c in NIVELES.items() if k in nivel_up), "")
    estilo_nivel = f"color:var(--{color_nivel});font-weight:700" if color_nivel else ""
 
    cabecera = f"""
    <div class="card dorado hero">
      <span class="tag" style="letter-spacing:2px;font-family:'Montserrat',sans-serif">Flujo Culinario Completo</span>
      <h1>{e(d['nombre_receta'])}</h1>
      <div class="pills mono">
        <span class="pill">👥 <b>Comensales:</b> {comensales} pax</span>
        <span class="pill" style="color:var(--amarillo)">⏱️ <b>Tiempo total:</b> {tiempo_total} min</span>
        <span class="pill" style="{estilo_nivel}">🎯 <b>Nivel:</b> {e(d['nivel_dificultad'])}</span>
      </div>
    </div>"""
 
    ingredientes = _tarjeta_tienda(
        "verde", f"🛒 1. Ingredientes ({comensales} pax)", "🛒 DELICATESSEN GOURMET",
        "Redirigiendo a la tienda de ingredientes...", f'<div class="chips">{_chips(d["ingredientes"])}</div>',
    )
    utensilios = _tarjeta_tienda(
        "verde", "🛠️ 2. Utensilios y Menaje", "🍳 PUCHEROS STORE",
        "Redirigiendo a la tienda de menaje...", f'<div class="chips">{_chips(d["utensilios_menaje"])}</div>',
    )
    previos = f"""
    <div class="card">
      <div class="card-head"><h3 style="color:#fff">🔪 3. Preparación Previa (Mise en Place)</h3></div>
      <ul class="lista mono">{_ul(d['pasos_previos'], 'Sin pasos previos.')}</ul>
    </div>"""
    recomendaciones = f"""
    <div class="card rojo" style="margin-top:20px">
      <div class="card-head"><h3>🚨 5. Puntos Críticos y Alertas del Chef</h3></div>
      <ul class="lista mono">{_ul(d['recomendaciones'], 'Sin alertas.')}</ul>
    </div>"""
    maridaje = _tarjeta_tienda(
        "verde", "🍷 6. Maridaje", "🍾 LIQUIDOS STORE", "Redirigiendo a la bodega de líquidos...",
        f"""<div class="mono" style="font-size:clamp(13px,2.2vw,15px);line-height:1.6">
        <p style="margin:0 0 4px;color:#fff"><b>🍇 Vinos (Denominaciones de Origen):</b></p>
        <ul style="margin:0 0 10px;padding-left:18px">{_ul(d['vinos'])}</ul>
        <p style="margin:0 0 4px;color:#fff"><b>🍺 Cervezas:</b></p>
        <ul style="margin:0;padding-left:18px">{_ul(d['cervezas'])}</ul></div>""",
    )
 
    if re.match(r"https?://", origen):
        origen_html = f'<a href="{e(origen)}" target="_blank" rel="noopener noreferrer">{e(origen)}</a>'
    else:
        origen_html = f"<span>{e(origen)}</span>"
 
    voz = json.dumps(d["texto_voz"], ensure_ascii=False).replace("<", "\\u003c")
    js = JS_DASHBOARD.replace("__TEXTO_VOZ__", voz)
 
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600;700&family=Montserrat:wght@700;900&display=swap" rel="stylesheet">
<style>{CSS_DASHBOARD}</style>
</head>
<body>
<div class="hub">
  {cabecera}
  <div class="widget">
    <p style="font-size:12px;margin:0 0 10px;font-weight:700;font-family:'Montserrat',sans-serif">👨‍🍳 ASISTENTE AUDITIVO</p>
    <button id="btnVoz" class="btn btn-voz" onclick="reproducir(this)">🎧 Escuchar Pasos</button>
    <button class="btn btn-gris" onclick="detener()">OIDO COCINA (silenciar)</button>
  </div>
  {ingredientes}
  {utensilios}
  {previos}
  <div>{_diagrama(d['bloques_proceso'])}</div>
  {recomendaciones}
  {maridaje}
  <div class="pie">FaceFoodChef.com | Origen: {origen_html}</div>
</div>
<script>{js}</script>
</body>
</html>"""
 
 
# ---------------------------------------------------------------------------
# Interfaz Streamlit
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="FaceFoodChef.com - Motor de Diagramas Culinarios",
        layout="wide",
        page_icon="🍳",
    )
    st.markdown(CSS_STREAMLIT, unsafe_allow_html=True)
 
    st.sidebar.header("⚙️ Panel de Control")
    api_key = st.sidebar.text_input(
        "🔑 Clave de API Gemini:",
        type="password",
        value=api_key_por_defecto(),
        help="Introduce tu clave de API de Google Gemini (Google AI Studio).",
    )
    modelo = st.sidebar.selectbox("Modelo Gemini:", options=MODELOS, index=0)
    comensales = int(
        st.sidebar.number_input(
            "👥 Número de comensales:",
            min_value=1, max_value=100, value=4, step=1,
            help="El sistema recalculará los ingredientes para este número de personas.",
        )
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
### 🎨 Código de Bloques:
- 🟢 **Verde Neón (`#00FF66`):** Ingredientes / Utensilios / Maridaje
- 🟡 **Amarillo (`#FFB300`):** Acciones / Procesado
- 🔴 **Rojo FaceFoodChef (`#EF4444`):** Alertas / Puntos Críticos
- 🟠 **Dorado (`#FFD700`):** Plato Terminado
"""
    )
 
    st.markdown(TITULO_HTML, unsafe_allow_html=True)
    st.subheader("📥 Entrada de Receta")
    entrada = st.text_area(
        "Pega la URL de la receta o el texto completo:",
        height=130,
        placeholder="https://www.ejemplo.com/receta\nO pega directamente el texto de la receta aquí...",
    )
    with st.expander("📁 Adjuntar archivo (PDF, Word, PPT o Imagen)"):
        archivo = st.file_uploader(
            "Subir documento:",
            type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"],
        )
 
    url, texto = clasificar_entrada(entrada)
    texto_archivo, bytes_archivo, mime_archivo = "", None, None
    if archivo:
        try:
            texto_archivo, bytes_archivo, mime_archivo = leer_archivo(archivo)
        except Exception as exc:
            st.error(f"No se pudo leer el archivo: {exc}")
 
    if st.button("🚀 GENERAR DIAGRAMA DE FLUJO CULINARIO"):
        st.session_state.pop("resultado", None)
        if not api_key.strip():
            st.error("⚠️ Introduce tu clave de API de Google Gemini en el panel lateral.")
        elif not (url or texto or texto_archivo or bytes_archivo):
            st.warning("⚠️ Debes introducir un texto, URL o adjuntar un archivo con la receta.")
        else:
            try:
                contenido = ""
                if url:
                    with st.spinner("🌐 Extrayendo datos de la URL..."):
                        contenido = extraer_texto_de_url(url)
                elif texto:
                    contenido = texto
                elif texto_archivo:
                    contenido = texto_archivo
 
                if len(contenido) > MAX_CHARS_RECETA:
                    contenido = contenido[:MAX_CHARS_RECETA]
                    st.warning(f"La receta era muy larga; se ha recortado a {MAX_CHARS_RECETA:,} caracteres.")
 
                if contenido:
                    contents = [f"Receta:\n{contenido}"]
                else:
                    contents = [
                        types.Part.from_bytes(data=bytes_archivo, mime_type=mime_archivo),
                        f"Procesa la receta adjunta ajustada a {comensales} personas.",
                    ]
 
                config = types.GenerateContentConfig(
                    system_instruction=construir_prompt(comensales),
                    response_mime_type="application/json",
                    temperature=0.2,
                )
                client = genai.Client(api_key=api_key.strip())
                modelos = list(dict.fromkeys([modelo, *MODELOS]))
 
                with st.spinner("⚡ Conectando con Gemini y generando el diagrama..."):
                    datos = normalizar_datos(llamar_gemini(client, modelos, contents, config))
 
                origen = url or datos["origen_receta"] or "Texto introducido por el usuario"
                st.session_state["resultado"] = {
                    "html": generar_html_dashboard(datos, origen, comensales),
                    "archivo": f"diagrama_{slug(datos['nombre_receta'])}.html",
                }
            except GeminiError as exc:
                st.error(mensaje_error_gemini(exc))
            except ValueError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Error inesperado al procesar los datos: {exc}")
 
    # El resultado vive en session_state: sobrevive a reruns (p. ej. al pulsar "Descargar").
    resultado = st.session_state.get("resultado")
    if resultado:
        st.success("¡Diagrama optimizado generado con éxito!")
        st.download_button(
            label="💾 Descargar Diagrama en HTML",
            data=resultado["html"],
            file_name=resultado["archivo"],
            mime="text/html",
        )
        components.html(resultado["html"], height=1250, scrolling=True)
 
 
if __name__ == "__main__":
    main()
 
