import json
import os
from google import genai
from google.genai import types
from src.models import RecetaEstructurada

PROMPT_SISTEMA_PARSER = """
Eres un Ingeniero de Procesos Gastronómicos de nivel industrial. Tu objetivo es analizar la receta de cocina proporcionada y convertirla en una estructura de grafo de procesos rigurosa.

Debes extraer:
1. Todos los ingredientes iniciales con sus cantidades exactas.
2. Todos los utensilios necesarios.
3. La secuencia exacta de pasos, dividida en operaciones unitarias.

REGLAS DE GRAFO Y DEPENDENCIAS:
- Identifica qué operaciones pueden ocurrir EN PARALELO (ej. mientras se fríe la cebolla, batir los huevos).
- Cada paso debe listar explícitamente los `insumos_requeridos` (ya sean IDs de ingredientes iniciales como 'ING_1' o IDs de pasos anteriores como 'P1').
- Asigna cada paso a una `estacion` de trabajo válida: 'Tabla de corte', 'Cocción / Fuego', 'Bol / Mezclado', 'Horno / Reposado', 'Emplatado / Servicio'.
- Si hay un control visual/térmico (ej. 'hasta que esté tierno'), marca `es_punto_decision=True` y añade `pregunta_decision`.

Responde estrictamente en formato JSON que cumpla el esquema requerido.
"""

class RecipeParser:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def parse_recipe(self, raw_text: str) -> RecetaEstructurada:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=f"{PROMPT_SISTEMA_PARSER}\n\nTexto de la Receta:\n{raw_text}",
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=RecetaEstructurada,
            )
        )
        
        datos_json = json.loads(response.text)
        return RecetaEstructurada(**datos_json)
