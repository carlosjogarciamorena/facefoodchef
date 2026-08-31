from src.models import RecetaEstructurada

class MermaidGenerator:
    def __init__(self, receta: RecetaEstructurada):
        self.receta = receta

    def generate((self) -> str:
        lines = ["graph TD"]
        
        # Estilos CSS de la paleta
        lines.append("    %% Definición de Estilos")
        lines.append("    classDef ingrediente fill:#E3F2FD,stroke:#1E88E5,stroke-width:2px,color:#0D47A1;")
        lines.append("    classDef corte fill:#FFF3E0,stroke:#FB8C00,stroke-width:2px,color:#E65100;")
        lines.append("    classDef fuego fill:#FFEBEE,stroke:#E53935,stroke-width:2px,color:#B71C1C;")
        lines.append("    classDef mezcla fill:#F3E5F5,stroke:#8E24AA,stroke-width:2px,color:#4A148C;")
        lines.append("    classDef horno fill:#E8F5E9,stroke:#43A047,stroke-width:2px,color:#1B5E20;")
        lines.append("    classDef decision fill:#FFFDE7,stroke:#FDD835,stroke-width:2px,color:#F57F17;")

        # Subgrafo 1: Ingredientes Iniciales
        lines.append("\n    subgraph ING[🥗 INGREDIENTES]");
        for ing in self.receta.ingredientes:
            label = f"{ing.nombre}<br/><b>({ing.cantidad})</b>"
            lines.append(f'        {ing.id}(["{label}"])')
            lines.append(f'        class {ing.id} ingrediente')
        lines.append("    end")

        # Agrupar pasos por Estaciones de Trabajo
        estaciones = {}
        for paso in self.receta.pasos:
            est_nombre = paso.estacion.value
            if est_nombre not in estaciones:
                estaciones[est_nombre] = []
            estaciones[est_nombre].append(paso)

        # Generar Subgrafos por Estación
        idx_est = 1
        for est_nombre, pasos in estaciones.items():
            lines.append(f'\n    subgraph EST_{idx_est}["📍 {est_nombre.upper()}"]')
            for paso in pasos:
                tiempo_str = f"<br/>⏱️ <i>{paso.tiempo_minutos} min</i>" if paso.tiempo_minutos > 0 else ""
                temp_str = f" | 🌡️ <i>{paso.temperatura_c}°C</i>" if paso.temperatura_c else ""
                
                texto_nodo = f"<b>{paso.id}</b>: {paso.descripcion}{tiempo_str}{temp_str}"

                if paso.es_punto_decision:
                    lines.append(f'        {paso.id}{{"{texto_nodo}"}}')
                    lines.append(f'        class {paso.id} decision')
                else:
                    lines.append(f'        {paso.id}["{texto_nodo}"]')
                    
                    # Asignar clase de color según estación
                    if "corte" in est_nombre.lower():
                        lines.append(f'        class {paso.id} corte')
                    elif "fuego" in est_nombre.lower():
                        lines.append(f'        class {paso.id} fuego')
                    elif "mezcla" in est_nombre.lower():
                        lines.append(f'        class {paso.id} mezcla')
                    else:
                        lines.append(f'        class {paso.id} horno')

            lines.append("    end")
            idx_est += 1

        # Generar Conexiones (Relaciones)
        lines.append("\n    %% Relaciones y Dependencias")
        for paso in self.receta.pasos:
            for insumo in paso.insumos_requeridos:
                lines.append(f"    {insumo} --> {paso.id}")
            if paso.es_punto_decision and paso.pregunta_decision:
                lines.append(f'    {paso.id} -.->|"{paso.pregunta_decision}"| {paso.id}')

        return "\n".join(lines)
