"""Herramienta mock del agente de Voz.

Simula una llamada a OmniVoice (scripts/narracion.py en el motor real
de reels): no genera audio, pero estima la duracion con la misma
heuristica que usa el proyecto real para la voz automatica
(~2.3 palabras/segundo, ver CLAUDE.md §4 del motor de reels).
"""
from __future__ import annotations

import json

from claude_agent_sdk import tool

PALABRAS_POR_SEGUNDO = 2.3


@tool(
    "generar_voz_mock",
    "Simula generar la narracion de una linea de guion y estima su duracion real.",
    {"escena": str, "texto": str},
)
async def generar_voz_mock(args: dict) -> dict:
    texto = args["texto"]
    n_palabras = len(texto.split())
    duracion_s = round(n_palabras / PALABRAS_POR_SEGUNDO, 2)
    resultado = {
        "escena": args["escena"],
        "archivo_simulado": f"public/demo/audio_mock/{args['escena']}.wav",
        "duracion_estimada_s": duracion_s,
        "nota": "mock: no se llamo a OmniVoice de verdad",
    }
    return {"content": [{"type": "text", "text": json.dumps(resultado, ensure_ascii=False)}]}
