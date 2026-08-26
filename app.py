import streamlit as st
import streamlit.components.v1 as components

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Traductor de Recetas a Diagrama y Voz",
    page_icon="🍳",
    layout="wide"
)

st.title("🍳 Traductor de Recetas: Diagrama de Bloques y Asistente de Voz")
st.markdown("Convierte cualquier receta de cocina en un flujo visual paso a paso con asistente de voz integrado.")

# Código HTML, Tailwind CSS y JavaScript encapsulado para garantizar 
# que la API de Voz del navegador (SpeechSynthesis) funcione correctamente sin bloqueos de iframe.
recipe_app_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Asistente de Recetas Pro</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({ startOnLoad: false, theme: 'neutral' });
    </script>
</head>
<body class="bg-gray-50 text-gray-800 p-4 font-sans">
    <div class="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- Panel Izquierdo: Entrada de Texto -->
        <div class="bg-white p-5 rounded-2xl shadow-lg lg:col-span-1 flex flex-col justify-between">
            <div>
                <h2 class="font-bold text-lg text-orange-600 mb-3">📝 Texto de la Receta</h2>
                <textarea id="recipeInput" rows="10" class="w-full p-3 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-orange-500 focus:outline-none">Ejemplo: Tortilla de Patatas Tradicional
Ingredientes:
- 4 patatas grandes
- 1 cebolla
- 6 huevos
- Aceite de oliva y sal

Pasos:
1. Pelar y cortar las patatas en láminas finas y la cebolla en juliana.
2. Freír las patatas y la cebolla en una sartén con abundante aceite a fuego medio hasta que estén tiernas.
3. Batir los huevos en un bol grande con una pizca de sal.
4. Escurrir el aceite, mezclar las patatas con el huevo y dejar reposar 5 minutos.
5. Cuajar la mezcla en la sartén 3 minutos por cada lado hasta dorar.</textarea>
                
                <button onclick="processRecipe()" class="mt-4 w-full bg-orange-600 hover:bg-orange-700 text-white font-bold py-2.5 px-4 rounded-lg transition duration-200 shadow">
                    ⚙️ Generar Diagrama y Asistente
                </button>
            </div>

            <div class="mt-6 pt-4 border-t border-gray-200">
                <span class="text-xs font-semibold text-gray-500 uppercase block mb-1">Estado de la Voz</span>
                <div id="voiceStatus" class="flex items-center space-x-2 text-sm text-green-600 font-medium">
                    <span class="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse"></span>
                    <span id="voiceStatusText">Asistente de voz listo</span>
                </div>
            </div>
        </div>

        <!-- Panel Derecho: Diagrama y Reproductor -->
        <div class="lg:col-span-2 space-y-6">
            <!-- Diagrama de Bloques -->
            <div class="bg-white p-5 rounded-2xl shadow-lg">
                <h2 class="font-bold text-lg text-gray-700 mb-3">📊 Diagrama de Flujo Lógico</h2>
                <div id="diagramContainer" class="bg-gray-50 p-4 rounded-xl border border-gray-200 min-h-[200px] flex items-center justify-center overflow-x-auto">
                    <p class="text-gray-400 italic text-sm">Generando diagrama...</p>
                </div>
            </div>

            <!-- Reproductor Guiado Paso a Paso -->
            <div class="bg-white p-5 rounded-2xl shadow-lg">
                <div class="flex justify-between items-center mb-3">
                    <h2 class="font-bold text-lg text-orange-600">🎙️ Instrucciones de Cocina Guiadas</h2>
                    <span id="stepCounter" class="bg-orange-100 text-orange-800 text-xs font-semibold px-2.5 py-1 rounded-full">Paso 0 de 0</span>
                </div>

                <div id="currentStepCard" class="bg-orange-50 border-l-4 border-orange-500 p-4 rounded-r-lg mb-4 min-h-[80px] flex flex-col justify-center">
                    <p id="currentStepText" class="text-gray-700 italic text-sm">Procesa una receta para comenzar...</p>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    <button onclick="prevStep()" class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-3 rounded-lg transition text-xs">⬅️ Anterior</button>
                    <button onclick="speakCurrentStep()" class="bg-green-600 hover:bg-green-700 text-white font-semibold py-2 px-3 rounded-lg transition shadow text-xs">🔊 Leer Paso</button>
                    <button onclick="stopSpeech()" class="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-3 rounded-lg transition text-xs">⏹️ Detener</button>
                    <button onclick="nextStep()" class="bg-orange-600 hover:bg-orange-700 text-white font-semibold py-2 px-3 rounded-lg transition shadow text-xs">Siguiente ➡️</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let synth = window.speechSynthesis;
        let stepsList = [];
        let currentStepIndex = 0;
        let voices = [];
        
        function loadVoices() {
            if (synth) voices = synth.getVoices();
        }
        loadVoices();
        if (synth && synth.onvoiceschanged !== undefined) synth.onvoiceschanged = loadVoices;

        function speakText(text) {
            if (!synth) return;
            synth.cancel();
            if (!text) return;
            
            let utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'es-ES';
            utterance.rate = 0.95;
            
            let spanishVoice = voices.find(v => v.lang.startsWith('es') || v.lang.includes('ES'));
            if (spanishVoice) utterance.voice = spanishVoice;
            
            utterance.onstart = () => {
                document.getElementById('voiceStatusText').innerText = "Reproduciendo instrucciones...";
            };
            utterance.onend = () => {
                document.getElementById('voiceStatusText').innerText = "Asistente de voz listo";
            };

            window.persistentUtterance = utterance;
            synth.speak(utterance);
        }

        function stopSpeech() {
            if (synth) {
                synth.cancel();
                document.getElementById('voiceStatusText').innerText = "Asistente detenido";
            }
        }

        function processRecipe() {
            let text = document.getElementById('recipeInput').value;
            let lines = text.split('\\n');
            stepsList = [];
            let ingredients = [];
            let parsingSteps = false;

            for (let l of lines) {
                let t = l.trim();
                if (!t) continue;
                if (t.toLowerCase().includes('ingrediente')) {
                    parsingSteps = false;
                    continue;
                }
                if (t.toLowerCase().includes('paso') || t.toLowerCase().includes('preparacion') || /^[0-9]+\./.test(t)) {
                    parsingSteps = true;
                }
                
                if (parsingSteps || /^[0-9]+\./.test(t)) {
                    let clean = t.replace(/^[0-9]+\.\s*/, '').replace(/^[-\*]\s*/, '');
                    stepsList.push(clean);
                } else {
                    ingredients.push(t);
                }
            }

            if (stepsList.length === 0) {
                stepsList = lines.filter(l => l.trim().length > 0);
            }

            currentStepIndex = 0;
            updateDisplay();
            renderDiagram(stepsList);
        }

        function renderDiagram(steps) {
            let container = document.getElementById('diagramContainer');
            let code = "graph TD\\n";
            code += "    Start([Inicio]) --> Ing[Ingredientes Listos]\\n";
            
            steps.forEach((s, i) => {
                let prev = i === 0 ? "Ing" : `Step${i}`;
                let safeText = s.replace(/"/g, "'").substring(0, 35) + (s.length > 35 ? "..." : "");
                code += `    ${prev} --> Step${i+1}["Paso ${i+1}: ${safeText}"]\\n`;
            });

            if (steps.length > 0) {
                code += `    Step${steps.length} --> End([¡Plato Listo! 🎉])\\n`;
            } else {
                code += `    Ing --> End([¡Plato Listo! 🎉])\\n`;
            }

            container.innerHTML = `<pre class="mermaid">${code}</pre>`;
            mermaid.contentLoaded();
        }

        function updateDisplay() {
            if (stepsList.length === 0) return;
            document.getElementById('stepCounter').innerText = `Paso ${currentStepIndex + 1} de ${stepsList.length}`;
            document.getElementById('currentStepText').innerText = stepsList[currentStepIndex];
            speakText(`Paso ${currentStepIndex + 1}: ${stepsList[currentStepIndex]}`);
        }

        function nextStep() {
            if (stepsList.length === 0) return;
            if (currentStepIndex < stepsList.length - 1) {
                currentStepIndex++;
                updateDisplay();
            } else {
                speakText("¡Felicidades! Has completado todos los pasos.");
            }
        }

        function prevStep() {
            if (stepsList.length === 0) return;
            if (currentStepIndex > 0) {
                currentStepIndex--;
                updateDisplay();
            }
        }

        window.onload = processRecipe;
    </script>
</body>
</html>
"""

# Renderizar el componente web en Streamlit con altura adaptada
components.html(recipe_app_html, height=720, scrolling=True)
