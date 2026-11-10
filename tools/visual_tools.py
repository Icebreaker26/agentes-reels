"""Herramienta mock del agente Visual/3D.

Simula generar la especificacion de render de Remotion para una escena
(kit de estilo + archivo esperado), sin ejecutar `remotion render` de verdad.
"""
from __future__ import annotations

import json

from claude_agent_sdk import tool


@tool(
    "generar_visual_mock",
    "Simula generar la especificacion de assets 3D/HTML de una escena para Remotion.",
    {"escena": str, "kit": str, "descripcion": str},
)
async def generar_visual_mock(args: dict) -> dict:
    resultado = {
        "escena": args["escena"],
        "kit": args["kit"],
        "archivo_simulado": f"src/demo/{args['escena']}.tsx",
        "nota": "mock: no se ejecuto remotion render",
    }
    return {"content": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]}
