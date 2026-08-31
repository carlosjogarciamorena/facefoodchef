from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class TipoNodo(str, Enum):
    INGREDIENTE = "ingrediente"
    UTENSILIO = "utensilio"
    ACCION = "accion"
    DECISION = "decision"
    PUNTO_CONTROL = "punto_control"
    PRODUCTO_FINAL = "producto_final"

class EstacionTrabajo(str, Enum):
    CORTE = "Tabla de corte"
    FUEGO = "Cocción / Fuego"
    MEZCLA = "Bol / Mezclado"
    HORNO = "Horno / Reposado"
    EMPLATADO = "Emplatado / Servicio"

class PasoReceta(BaseModel):
    id: str = Field(description="Identificador único del paso (ej. P1, P2)")
    descripcion: str = Field(description="Descripción clara de la acción realizada")
    estacion: EstacionTrabajo = Field(description="Estación de trabajo donde se ejecuta")
    tiempo_minutos: float = Field(default=0.0, description="Tiempo estimado en minutos")
    temperatura_c: Optional[float] = Field(default=None, description="Temperatura en Celsius si aplica")
    insumos_requeridos: List[str] = Field(default_factory=list, description="IDs de ingredientes o pasos previos necesarios")
    utensilios_requeridos: List[str] = Field(default_factory=list, description="Utensilios necesarios para este paso")
    es_punto_decision: bool = Field(default=False, description="Indica si requiere comprobación de estado")
    pregunta_decision: Optional[str] = Field(default=None, description="Pregunta de control (ej. ¿Está dorado?)")

class Ingrediente(BaseModel):
    id: str = Field(description="Identificador único del ingrediente (ej. ING_1)")
    nombre: str = Field(description="Nombre del ingrediente")
    cantidad: str = Field(description="Cantidad y unidad (ej. 500g, 2 cdas)")

class RecetaEstructurada(BaseModel):
    titulo: str = Field(description="Nombre del plato")
    porciones: int = Field(default=4, description="Número de raciones")
    ingredientes: List[Ingrediente] = Field(description="Lista completa de ingredientes iniciales")
    utensilios: List[str] = Field(default_factory=list, description="Lista de utensilios principales")
    pasos: List[PasoReceta] = Field(description="Secuencia lógica y paralela de pasos")
