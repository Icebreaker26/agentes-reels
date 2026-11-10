"""Herramienta mock del agente de Investigacion.

Simula leer codigo/documentacion real (en el motor de reels real seria
leer `standSlides.js` o un modulo de Kernel) devolviendo datos de un
diccionario local. Nunca "inventa" cifras: si el tema no esta en la
fuente, lo dice explicitamente -- esa es la regla de negocio real del
proyecto (CLAUDE.md §0: "no inventes cifras de negocio").
"""
from __future__ import annotations

import json

from claude_agent_sdk import tool

FUENTE_DEMO: dict[str, dict] = {
    "ahorro_voluntario": {
        "producto": "Ahorro voluntario programado",
        "beneficio_clave": "los aportes quedan disponibles en cualquier momento, sin plazo fijo",
        "dato_ejemplo": "tasa de referencia DTF + 2 puntos (cifra de catalogo demo, confirmar con el cliente antes de publicar)",
        "publico": "asociados activos de la cooperativa",
    },
}


@tool(
    "leer_fuente",
    "Lee los datos verificados de un tema del catalogo de productos (fuente de verdad simulada).",
    {"tema": str},
)
async def leer_fuente(args: dict) -> dict:
    tema = args["tema"]
    datos = FUENTE_DEMO.get(tema)
    if datos is None:
        texto = f"No hay datos verificados para '{tema}' en la fuente. No inventar cifras."
    else:
        texto = json.dumps(datos, ensure_ascii=False)
    return {"content": [{"type": "text", "text": texto}]}
