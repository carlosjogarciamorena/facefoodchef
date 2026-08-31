import networkx as nx
from typing import Dict, List, Tuple
from src.models import RecetaEstructurada, PasoReceta

class RecipeGraphEngine:
    def __init__(self, receta: RecetaEstructurada):
        self.receta = receta
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        # Insertar Ingredientes como Nodos
        for ing in self.receta.ingredientes:
            self.graph.add_node(
                ing.id,
                type="ingrediente",
                label=f"{ing.nombre}\n({ing.cantidad})",
                tiempo=0
            )

        # Insertar Pasos como Nodos y crear bordes de dependencia
        for paso in self.receta.pasos:
            label_paso = f"{paso.descripcion}"
            if paso.tiempo_minutos > 0:
                label_paso += f"\n⏱️ {paso.tiempo_minutos} min"
            if paso.temperatura_c:
                label_paso += f" | 🌡️ {paso.temperatura_c}°C"

            self.graph.add_node(
                paso.id,
                type="paso",
                label=label_paso,
                estacion=paso.estacion.value,
                tiempo=paso.tiempo_minutos,
                es_decision=paso.es_punto_decision,
                pregunta=paso.pregunta_decision
            )

            # Conectar insumos requeridos con el paso actual
            for insumo_id in paso.insumos_requeridos:
                self.graph.add_edge(insumo_id, paso.id)

    def validar_grafo(self) -> Tuple[bool, List[str]]:
        errores = []
        # Verificar si hay ciclos (imposible en recetas)
        if not nx.is_directed_acyclic_graph(self.graph):
            errores.append("Error crítico: Se ha detectado un bucle infinito en las dependencias de la receta.")

        # Verificar insumos inexistentes
        for paso in self.receta.pasos:
            for insumo_id in paso.insumos_requeridos:
                if not self.graph.has_node(insumo_id):
                    errores.append(f"El paso {paso.id} requiere un insumo inexistente: {insumo_id}")

        return len(errores) == 0, errores

    def calcular_camino_critico(self) -> Dict[str, float]:
        """Calcula el tiempo mínimo total y la ruta crítica de pasos que determinan la duración."""
        # Asignar pesos inversos para encontrar el camino más largo (critical path)
        try:
            # Ordenamiento topológico
            orden_topologico = list(nx.topological_sort(self.graph))
            distancias = {node: 0.0 for node in self.graph.nodes()}
            
            for node in orden_topologico:
                tiempo_nodo = self.graph.nodes[node].get("tiempo", 0.0)
                for successor in self.graph.successors(node):
                    if distancias[node] + tiempo_nodo > distancias[successor]:
                        distancias[successor] = distancias[node] + tiempo_nodo

            tiempo_total = max(distancias.values()) if distancias else 0.0
            return {
                "tiempo_total_estimado": tiempo_total,
                "total_ingredientes": len(self.receta.ingredientes),
                "total_pasos": len(self.receta.pasos)
            }
        except Exception:
            return {"tiempo_total_estimado": 0.0, "total_ingredientes": 0, "total_pasos": 0}
