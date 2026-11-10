"""Memoria compartida del sistema multiagente (ReelState).

No hay memoria entre corridas del notebook: cada ejecucion empieza con un
ReelState nuevo. Dentro de una corrida, este objeto es la unica memoria
que se pasa de agente a agente -- lo que no quede aqui (o impreso en las
celdas) se pierde al cerrar el notebook. Ver ARCHITECTURE.md, seccion
"Memoria".
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LogEntry:
    agente: str
    accion: str
    detalle: str


@dataclass
class ReelState:
    brief: dict[str, Any]
    plan: list[str] = field(default_factory=list)
    dossier: dict[str, Any] = field(default_factory=dict)
    guion: list[dict[str, Any]] = field(default_factory=list)
    voz: list[dict[str, Any]] = field(default_factory=list)
    visual: list[dict[str, Any]] = field(default_factory=list)
    qa: dict[str, Any] = field(default_factory=dict)
    intentos_replanificacion: int = 0
    log: list[LogEntry] = field(default_factory=list)

    def registrar(self, agente: str, accion: str, detalle: str) -> None:
        self.log.append(LogEntry(agente=agente, accion=accion, detalle=detalle))

    def resumen_json(self, *campos: str) -> str:
        """Serializa el estado para pasarlo a un agente.

        Si se piden campos especificos, solo esos se incluyen -- cada
        agente ve solo la porcion de memoria relevante a su rol, no todo
        el estado completo.
        """
        data = asdict(self)
        if campos:
            data = {k: data[k] for k in campos if k in data}
        return json.dumps(data, ensure_ascii=False, indent=2)
