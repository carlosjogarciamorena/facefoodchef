import json
from io import BytesIO
import requests
from bs4 import BeautifulSoup
import streamlit as st
import streamlit.components.v1 as components
from recipe_scrapers import scrape_me
from google import genai
from google.genai import types
from google.genai.errors import APIError

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
    import pptx
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False

st.set_page_config(
    page_title="FaceFoodChef - Diagramas de Bloques Culinarios",
    layout="wide",
    page_icon="🍳"
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600;700&family=Montserrat:wght@700;900&display=swap');
    .stApp, .block-container, [data-testid="stSidebar"] {
        background-color: #36393F !important;
        color: #E2E8F0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div, .stNumberInput input {
        background-color: #2C2F33 !important;
        color: #E2E8F0 !important;
        border: 1px solid #4F545C !important;
        border-radius: 6px !important;
    }
    .stButton > button {
        background-color: #00FF66 !important;
        color: #1E1E1E !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 15px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 12px 20px !important;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .stButton > button:hover {
        background-color: #00D656 !important;
    }
    .stDownloadButton > button {
        background-color: #FFB300 !important;
        color: #1E1E1E !important;
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 900 !important;
        font-size: 14px !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 10px 18px !important;
        width: 100%;
        text-transform: uppercase;
    }
    h1, h2, h3, h4 {
        font-family: 'Montserrat', sans-serif !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.sidebar.header("⚙️ Panel de Control")

api_key_input = st.sidebar.text_input(
    "🔑 Clave de API Gemini:",
    type="password",
    value=st.secrets.get("GEMINI_API_KEY", "") if "GEMINI_API_KEY" in st.secrets else "",
    help="Introduce tu clave de API de Google AI Studio."
)

modelo_seleccionado = st.sidebar.selectbox(
    "🤖 Modelo Gemini:",
    options=["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"],
    index=0
)

comensales_objetivo = st.sidebar.number_input(
    "👥 Comensales:",
    min_value=1,
    max_value=100,
    value=4,
    step=1
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎨 Leyenda de Bloques")
st.sidebar.markdown("- 🟢 **Verde (`#00FF66`):** Ingredientes / Utensilios / Maridaje")
st.sidebar.markdown("- 🟡 **Amarillo (`#FFB300`):** Bloque de cocinado / proceso")
st.sidebar.markdown("- 🔴 **Rojo (`#EF4444`):** Punto crítico o alerta")
st.sidebar.markdown("- 🟡 **Dorado (`#FFD700`):** Plato terminado")

st.markdown(
    "<h1 style='text-align:center; margin-bottom:4px;'>FACEFOODCHEF · MOTOR DE DIAGRAMAS CULINARIOS</h1>",
    unsafe_allow_html=True
)
st.markdown(
    "<p style='text-align:center; color:#CBD5E1; margin-bottom:24px;'>Transforma cualquier receta en un diagrama de bloques paso a paso con cantidades exactas</p>",
    unsafe_allow_html=True
)

st.subheader("📥 Receta de Entrada")
entrada_principal = st.text_area(
    "Pega el texto de la receta o una URL:",
    height=150,
    placeholder="Ejemplo:\nTortilla de patatas: 600 g de patatas, 6 huevos, 150 g de cebolla, 120 ml de aceite de oliva virgen extra, 6 g de sal..."
)

with st.expander("📁 Subir archivo opcional (PDF, Word, PPT, TXT o Imagen)"):
    archivo_subido = st.file_uploader(
        "Selecciona un archivo:",
        type=["pdf", "docx", "pptx", "txt", "jpg", "jpeg", "png", "webp"]
    )

receta_texto_input = ""
url_origen_detectada = ""
archivo_multimodal = None
tipo_multimodal = None

if entrada_principal.strip():
    texto_limpio = entrada_principal.strip()
    if texto_limpio.startswith("http://") or texto_limpio.startswith("https://"):
        url_origen_detectada = texto_limpio
    else:
        receta_texto_input = texto_limpio

if archivo_subido is not None:
    ext = archivo_subido.name.split(".")[-1].lower()
    if ext == "txt":
        receta_texto_input = archivo_subido.getvalue().decode("utf-8", errors="ignore")
    elif ext == "docx" and HAS_DOCX:
        doc = docx.Document(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    elif ext == "pptx" and HAS_PPTX:
        prs = pptx.Presentation(BytesIO(archivo_subido.getvalue()))
        receta_texto_input = "\n".join([
            p.text for slide in prs.slides for shape in slide.shapes if shape.has_text_frame for p in shape.text_frame.paragraphs
        ])
    elif ext in ["pdf", "jpg", "jpeg", "png", "webp"]:
        archivo_multimodal = archivo_subido.getvalue()
        tipo_multimodal = "application/pdf" if ext == "pdf" else archivo_subido.type


def extraer_texto_de_url(url: str):
    try:
        scraper = scrape_me(url)
        pasos = "\n".join(scraper.instructions())
        ingredientes = ", ".join(scraper.ingredients())
        return f"Receta de {url}\nIngredientes: {ingredientes}\nPasos:\n{pasos}", url
    except Exception:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        return f"Contenido de {url}:\n{soup.get_text(separator='\n', strip=True)}", url


def calcular_tiempo_total(bloques_proceso: list, minutos_prep: int = 10) -> int:
    total = minutos_prep
    for bloque in bloques_proceso:
        if bloque.get("tipo") == "paralelo":
            ramas = bloque.get("ramas", [])
            max_rama = max([r.get("duracion_minutos", 5) for r in ramas], default=5)
            total += max_rama
        else:
            total += bloque.get("duracion_minutos", 5)
    return total


def generar_html_diagrama(datos: dict, origen_receta: str, comensales: int) -> str:
    nombre_receta = datos.get("nombre_receta", "Receta Culinaria")
    nivel_dificultad = datos.get("nivel_dificultad", "Cocinero Cualificado")
    ingredientes = datos.get("ingredientes", [])
    utensilios_menaje = datos.get("utensilios_menaje", [])
    pasos_previos = datos.get("pasos_previos", [])
    bloques_proceso = datos.get("bloques_proceso", [])
    recomendaciones = datos.get("recomendaciones", [])
    texto_voz = datos.get("texto_voz", "")
    maridaje = datos.get("maridaje", {})

    tiempo_total_min = calcular_tiempo_total(bloques_proceso, max(5, len(pasos_previos) * 3))

    ing_chips = "".join([
        f"<span style='background:#36393F; color:#E2E8F0; padding:8px 12px; border-radius:4px; font-family:\"JetBrains Mono\", monospace; font-size:13px;'>{item}</span>"
        for item in ingredientes
    ])
    ut_chips = "".join([
        f"<span style='background:#36393F; color:#E2E8F0; padding:6px 10px; border-radius:4px; font-family:\"JetBrains Mono\", monospace; font-size:13px;'>{item}</span>"
        for item in utensilios_menaje
    ])
    prep_items = "".join([f"<li style='margin-bottom:6px;'>{p}</li>" for p in pasos_previos])

    bloques_html = []
    for idx, bloque in enumerate(bloques_proceso):
        b_tipo = bloque.get("tipo", "secuencial")
        es_critico = bool(bloque.get("es_critico", False))
        color_borde = "#EF4444" if es_critico else "#FFB300"

        if b_tipo == "paralelo":
            ramas = bloque.get("ramas", [])
            ramas_cards = []
            for r_idx, rama in enumerate(ramas):
                r_nombre = rama.get("nombre", f"Rama {r_idx + 1}").upper()
                r_accion = rama.get("accion", "")
                r_tiempo = rama.get("tiempo", "5 min")
                r_dur = int(rama.get("duracion_minutos", 5))
                r_temp = rama.get("temperatura", "Ambiente")
                r_ut = ", ".join(rama.get("utensilios", [])) or "N/A"
                timer_id = f"timer_par_{idx}_{r_idx}"
                audio_txt = json.dumps(f"Bloque paralelo {r_nombre}. {r_accion}. Tiempo: {r_tiempo}. Temperatura: {r_temp}.")

                ramas_cards.append(
                    f"<div style='flex:1; min-width:250px; background:#2C2F33; border-left:6px solid #FFB300; border-radius:6px; padding:14px;'>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;'>"
                    f"<span style='background:#FFB300; color:#1E1E1E; padding:3px 8px; border-radius:3px; font-size:11px; font-weight:800; font-family:\"JetBrains Mono\", monospace;'>PARALELO · {r_nombre}</span>"
                    f"<button onclick='hablar({audio_txt})' style='background:#4F545C; color:#FFF; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:700;'>🔊 VOZ</button>"
                    f"</div>"
                    f"<p style='color:#FFFFFF; margin:10px 0; font-family:\"JetBrains Mono\", monospace; font-size:14px; line-height:1.5;'>{r_accion}</p>"
                    f"<div style='color:#CBD5E1; font-size:12px; margin-bottom:10px; font-family:\"JetBrains Mono\", monospace;'>🛠️ {r_ut}</div>"
                    f"<div style='display:flex; justify-content:space-between; align-items:center; background:#36393F; padding:8px 10px; border-radius:4px; gap:8px; flex-wrap:wrap;'>"
                    f"<span style='color:#FFB300; font-family:\"JetBrains Mono\", monospace; font-size:13px; font-weight:700;'>⏱️ <span id='{timer_id}'>{r_tiempo}</span> · 🌡️ {r_temp}</span>"
                    f"<button onclick='iniciarTimer(\"{timer_id}\", {r_dur})' style='background:#EF4444; color:#FFF; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:800;'>⏳ INICIAR</button>"
                    f"</div></div>"
                )
            bloques_html.append(
                f"<div style='display:flex; gap:12px; flex-wrap:wrap; margin-bottom:10px;'>{''.join(ramas_cards)}</div>"
            )
        else:
            etiqueta = "CONVERGENCIA" if b_tipo == "convergencia" else f"BLOQUE {idx + 1}"
            accion = bloque.get("accion", "")
            tiempo = bloque.get("tiempo", "5 min")
            dur = int(bloque.get("duracion_minutos", 5))
            temp = bloque.get("temperatura", "Ambiente")
            ut_str = ", ".join(bloque.get("utensilios", [])) or "N/A"
            timer_id = f"timer_seq_{idx}"
            audio_txt = json.dumps(f"{etiqueta}. {accion}. Tiempo: {tiempo}. Temperatura: {temp}.")

            bloques_html.append(
                f"<div style='background:#2C2F33; border-left:6px solid {color_borde}; border-radius:6px; padding:14px; margin-bottom:10px;'>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;'>"
                f"<span style='background:{color_borde}; color:#1E1E1E; padding:3px 8px; border-radius:3px; font-size:11px; font-weight:800; font-family:\"JetBrains Mono\", monospace;'>{etiqueta}</span>"
                f"<button onclick='hablar({audio_txt})' style='background:#4F545C; color:#FFF; border:none; padding:5px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:700;'>🔊 VOZ</button>"
                f"</div>"
                f"<p style='color:#FFFFFF; margin:10px 0; font-family:\"JetBrains Mono\", monospace; font-size:14px; line-height:1.5;'>{accion}</p>"
                f"<div style='color:#CBD5E1; font-size:12px; margin-bottom:10px; font-family:\"JetBrains Mono\", monospace;'>🛠️ {ut_str}</div>"
                f"<div style='display:flex; justify-content:space-between; align-items:center; background:#36393F; padding:8px 10px; border-radius:4px; gap:8px; flex-wrap:wrap;'>"
                f"<span style='color:#FFB300; font-family:\"JetBrains Mono\", monospace; font-size:13px; font-weight:700;'>⏱️ <span id='{timer_id}'>{tiempo}</span> · 🌡️ {temp}</span>"
                f"<button onclick='iniciarTimer(\"{timer_id}\", {dur})' style='background:#EF4444; color:#FFF; border:none; padding:6px 10px; border-radius:4px; cursor:pointer; font-size:11px; font-weight:800;'>⏳ INICIAR</button>"
                f"</div></div>"
            )

        if idx < len(bloques_proceso) - 1:
            bloques_html.append("<div style='text-align:center; color:#FFB300; font-size:20px; font-weight:900; margin:4px 0 8px 0;'>↓</div>")

    recom_items = "".join([f"<li style='margin-bottom:6px;'>{r}</li>" for r in recomendaciones])
    vinos_items = "".join([f"<li>{v}</li>" for v in maridaje.get("vinos", [])]) or "<li>Sin propuestas</li>"
    cervezas_items = "".join([f"<li>{c}</li>" for c in maridaje.get("cervezas", [])]) or "<li>Sin propuestas</li>"
    saludables_items = "".join([f"<li>{s}</li>" for s in maridaje.get("bebidas_saludables", [])]) or "<li>Sin propuestas</li>"

    resumen_voz_json = json.dumps(texto_voz)
    btn_store_style = (
        "background:#00FF66; color:#1E1E1E; border:none; padding:7px 12px; border-radius:4px; "
        "cursor:pointer; font-size:11px; font-weight:900; font-family:'Montserrat', sans-serif; text-transform:uppercase;"
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;600;700&family=Montserrat:wght@700;900&display=swap" rel="stylesheet">
<style>
  body {{ background:#36393F; color:#E2E8F0; font-family:'Inter', sans-serif; margin:0; padding:12px; }}
  .wrap {{ max-width:920px; margin:auto; }}
  .card {{ background:#2C2F33; border-radius:6px; padding:16px; margin-bottom:16px; }}
  .card-head {{ display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; border-bottom:1px solid #4F545C; padding-bottom:8px; margin-bottom:12px; }}
  h3 {{ margin:0; font-family:'Montserrat', sans-serif; font-size:15px; text-transform:uppercase; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="card" style="border-left:6px solid #FFD700; text-align:center;">
    <span style="background:#FFD700; color:#1E1E1E; padding:3px 10px; border-radius:3px; font-size:11px; font-weight:900; font-family:'Montserrat', sans-serif;">DIAGRAMA DE PRODUCCIÓN</span>
    <h1 style="color:#FFFFFF; margin:10px 0; font-family:'Montserrat', sans-serif; font-size:22px;">{nombre_receta}</h1>
    <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; font-family:'JetBrains Mono', monospace; font-size:13px;">
      <span style="background:#36393F; padding:6px 12px; border-radius:4px;">👥 {comensales} pax</span>
      <span style="background:#36393F; padding:6px 12px; border-radius:4px; color:#FFB300;">⏱️ {tiempo_total_min} min</span>
      <span style="background:#36393F; padding:6px 12px; border-radius:4px; color:#00FF66;">🎯 {nivel_dificultad}</span>
    </div>
    <div style="margin-top:14px;">
      <button onclick='hablar({resumen_voz_json})' style="background:#EF4444; color:#FFF; border:none; padding:9px 14px; border-radius:4px; cursor:pointer; font-weight:800; font-size:12px;">🎧 ESCUCHAR RESUMEN</button>
      <button onclick="silenciar()" style="background:#4F545C; color:#FFF; border:none; padding:9px 14px; border-radius:4px; cursor:pointer; font-weight:800; font-size:12px; margin-left:6px;">🔇 SILENCIAR</button>
    </div>
  </div>

  <div class="card" style="border-left:6px solid #00FF66;">
    <div class="card-head">
      <h3 style="color:#00FF66;">1. Ingredientes Exactos ({comensales} pax)</h3>
      <button style="{btn_store_style}" onclick="alert('Redirigiendo a Delicatessen Gourmet...')">🛒 DELICATESSEN GOURMET</button>
    </div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">{ing_chips}</div>
  </div>

  <div class="card" style="border-left:6px solid #00FF66;">
    <div class="card-head">
      <h3 style="color:#00FF66;">2. Utensilios y Menaje</h3>
      <button style="{btn_store_style}" onclick="alert('Redirigiendo a Pucheros Store...')">🍳 PUCHEROS STORE</button>
    </div>
    <div style="display:flex; flex-wrap:wrap; gap:8px;">{ut_chips}</div>
  </div>

  <div class="card" style="border-left:6px solid #4F545C;">
    <div class="card-head">
      <h3 style="color:#FFFFFF;">3. Preparación Previa (Mise en Place)</h3>
    </div>
    <ul style="margin:0; padding-left:18px; font-family:'JetBrains Mono', monospace; font-size:13px; line-height:1.6;">{prep_items}</ul>
  </div>

  <div style="margin-bottom:16px;">
    <h3 style="color:#FFFFFF; margin-bottom:12px;">4. Diagrama de Bloques de Ejecución</h3>
    {"".join(bloques_html)}
    <div style="text-align:center; color:#FFD700; font-size:20px; font-weight:900; margin:6px 0;">↓</div>
    <div class="card" style="border-left:6px solid #FFD700; text-align:center;">
      <span style="background:#FFD700; color:#1E1E1E; padding:3px 10px; border-radius:3px; font-size:11px; font-weight:900;">FIN DEL FLUJO</span>
      <h3 style="color:#FFD700; margin:10px 0 12px 0; font-size:17px;">🍽️ PLATO TERMINADO Y LISTO PARA SERVIR</h3>
      <button style="{btn_store_style}" onclick="alert('Abriendo guía y menaje de emplatado...')">✨ EMPLATADO</button>
    </div>
  </div>

  <div class="card" style="border-left:6px solid #EF4444;">
    <div class="card-head">
      <h3 style="color:#EF4444;">5. Puntos Críticos y Alertas</h3>
    </div>
    <ul style="margin:0; padding-left:18px; font-family:'JetBrains Mono', monospace; font-size:13px; line-height:1.6;">{recom_items}</ul>
  </div>

  <div class="card" style="border-left:6px solid #00FF66;">
    <div class="card-head">
      <h3 style="color:#00FF66;">6. Sommelier y Maridaje</h3>
      <button style="{btn_store_style}" onclick="alert('Redirigiendo a Líquidos Store...')">🍾 LIQUIDOS STORE</button>
    </div>
    <p style="margin:6px 0 4px 0; font-weight:700;">🍇 Vinos (Denominaciones de Origen):</p>
    <ul style="margin:0 0 10px 0; padding-left:18px; font-family:'JetBrains Mono', monospace; font-size:13px;">{vinos_items}</ul>
    <p style="margin:6px 0 4px 0; font-weight:700;">🍺 Cervezas:</p>
    <ul style="margin:0 0 10px 0; padding-left:18px; font-family:'JetBrains Mono', monospace; font-size:13px;">{cervezas_items}</ul>
    <p style="margin:6px 0 4px 0; font-weight:700; color:#00FF66;">🌿 Bebidas Saludables (Sin Alcohol):</p>
    <ul style="margin:0; padding-left:18px; font-family:'JetBrains Mono', monospace; font-size:13px;">{saludables_items}</ul>
  </div>

  <div style="text-align:center; color:#9AA0A6; font-size:11px; padding:10px 0;">
    FaceFoodChef · Origen: {origen_receta}
  </div>
</div>

<script>
  function hablar(texto) {{
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    u.lang = 'es-ES';
    u.rate = 0.95;
    window.speechSynthesis.speak(u);
  }}
  function silenciar() {{
    if ('speechSynthesis' in window) window.speechSynthesis.cancel();
  }}
  function iniciarTimer(id, minutos) {{
    const el = document.getElementById(id);
    if (!el) return;
    let seg = Math.max(1, minutos) * 60;
    if (window[id + '_iv']) clearInterval(window[id + '_iv']);
    window[id + '_iv'] = setInterval(() => {{
      if (seg <= 0) {{
        clearInterval(window[id + '_iv']);
        el.innerText = '¡LISTO!';
      }} else {{
        seg--;
        const m = Math.floor(seg / 60);
        const s = seg % 60;
        el.innerText = m + 'm ' + (s < 10 ? '0' : '') + s + 's';
      }}
    }}, 1000);
  }}
</script>
</body>
</html>"""


if "diagrama_html" not in st.session_state:
    st.session_state.diagrama_html = None
if "nombre_archivo_html" not in st.session_state:
    st.session_state.nombre_archivo_html = "diagrama_receta.html"

generar_clicked = st.button("🚀 GENERAR DIAGRAMA DE BLOQUES")

if generar_clicked:
    api_key_activa = api_key_input.strip()
    contenido_receta = receta_texto_input.strip()
    origen_final = "Texto introducido por el usuario"

    if url_origen_detectada:
        try:
            with st.spinner("🌐 Extrayendo receta de la URL..."):
                contenido_receta, origen_final = extraer_texto_de_url(url_origen_detectada)
        except Exception as err:
            st.error(f"No se pudo leer la URL: {err}")
            contenido_receta = ""

    if not api_key_activa:
        st.error("⚠️ Introduce tu clave de API de Gemini en el panel lateral.")
    elif not contenido_receta and not archivo_multimodal:
        st.warning("⚠️ Escribe o pega el texto de una receta, introduce una URL o sube un archivo.")
    else:
        prompt_sistema = f"""
Eres un maestro chef e ingeniero de procesos culinarios.
Convierte la receta en un diagrama de bloques claro y ejecutable paso a paso para {comensales_objetivo} COMENSALES.

Reglas obligatorias:
1. CANTIDADES EXACTAS: Elimina medidas ambiguas o relativas como "cucharadita", "cucharada", "pizca", "chorrito" o "al gusto". Conviértelas en cantidades exactas en g, kg, ml, l, mg o unidades ajustadas a {comensales_objetivo} comensales (por ejemplo: "5 g de sal", "15 ml de aceite de oliva virgen extra").
2. NIVEL DE DIFICULTAD: Usa exactamente uno de estos tres valores: "Superviviente Básico", "Cocinero Cualificado" o "Doctor Chef".
3. BLOQUES DE PROCESO: Divide la elaboración en bloques ordenados ("tipo": "secuencial", "paralelo" o "convergencia"), indicando "es_critico" (booleano), "duracion_minutos" (entero), "tiempo" (texto con min), "temperatura" (con ºC o "Ambiente") y "utensilios" (lista).
4. SOMMELIER Y MARIDAJE: Incluye exactamente 3 propuestas en "vinos" (con Denominación de Origen o tipo), 3 en "cervezas" y 3 en "bebidas_saludables" (sin alcohol: infusiones, aguas botánicas, kombuchas o zumos naturales sin azúcares añadidos).
5. Responde ÚNICAMENTE con un JSON válido que siga esta estructura:
{{
  "nombre_receta": "String",
  "nivel_dificultad": "Cocinero Cualificado",
  "ingredientes": ["500 g de patatas", "15 ml de aceite de oliva virgen extra"],
  "utensilios_menaje": ["Sartén", "Cuchillo"],
  "pasos_previos": ["Pelar y cortar las patatas en láminas de 3 mm"],
  "bloques_proceso": [
    {{
      "tipo": "secuencial",
      "es_critico": false,
      "accion": "Calentar el aceite y confitar las patatas",
      "utensilios": ["Sartén"],
      "tiempo": "15 min",
      "duracion_minutos": 15,
      "temperatura": "140 ºC"
    }}
  ],
  "recomendaciones": ["Controlar la temperatura para que no se queme el aceite"],
  "texto_voz": "Resumen breve del proceso",
  "maridaje": {{
    "vinos": ["Vino 1", "Vino 2", "Vino 3"],
    "cervezas": ["Cerveza 1", "Cerveza 2", "Cerveza 3"],
    "bebidas_saludables": ["Bebida 1", "Bebida 2", "Bebida 3"]
  }}
}}
"""
        payload = [prompt_sistema]
        if archivo_multimodal:
            payload.append(types.Part.from_bytes(data=archivo_multimodal, mime_type=tipo_multimodal))
            payload.append(f"Genera el diagrama para {comensales_objetivo} comensales con cantidades exactas.")
        else:
            payload.append(f"Receta:\n{contenido_receta}")

        try:
            client = genai.Client(api_key=api_key_activa)
            candidatos = [modelo_seleccionado, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
            try:
                for m in client.models.list():
                    nombre_m = m.name.replace("models/", "")
                    if "gemini" in nombre_m.lower() and nombre_m not in candidatos:
                        candidatos.append(nombre_m)
            except Exception:
                pass
            candidatos = list(dict.fromkeys(candidatos))

            respuesta_texto = None
            ultimo_error = ""

            with st.spinner("⚡ Generando diagrama de bloques..."):
                for mod in candidatos:
                    try:
                        resp = client.models.generate_content(
                            model=mod,
                            contents=payload,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.2
                            )
                        )
                        if resp and resp.text:
                            respuesta_texto = resp.text.strip()
                            break
                    except Exception as e:
                        ultimo_error = str(e)
                        continue

            if not respuesta_texto:
                st.error(f"❌ No se pudo generar el diagrama. Detalle: {ultimo_error}")
            else:
                if respuesta_texto.startswith("```json"):
                    respuesta_texto = respuesta_texto[7:]
                elif respuesta_texto.startswith("```"):
                    respuesta_texto = respuesta_texto[3:]
                if respuesta_texto.endswith("```"):
                    respuesta_texto = respuesta_texto[:-3]

                datos_json = json.loads(respuesta_texto.strip())
                st.session_state.diagrama_html = generar_html_diagrama(datos_json, origen_final, comensales_objetivo)
                nombre_slug = datos_json.get("nombre_receta", "receta").lower().replace(" ", "_")
                st.session_state.nombre_archivo_html = f"diagrama_{nombre_slug}.html"
                st.success("✅ Diagrama de bloques generado correctamente.")

        except APIError as api_e:
            st.error(f"Error de API Gemini: {api_e}")
        except json.JSONDecodeError as json_e:
            st.error(f"La respuesta de la IA no tenía formato JSON válido: {json_e}")
        except Exception as gen_e:
            st.error(f"Error inesperado: {gen_e}")

if st.session_state.diagrama_html:
    st.download_button(
        label="💾 DESCARGAR DIAGRAMA (HTML)",
        data=st.session_state.diagrama_html,
        file_name=st.session_state.nombre_archivo_html,
        mime="text/html"
    )
    components.html(st.session_state.diagrama_html, height=1200, scrolling=True)
