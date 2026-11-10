"""Agente de Investigacion: su unica fuente de verdad es la tool `leer_fuente`."""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState
from tools.research_tools import leer_fuente

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "investigacion.txt").read_text(encoding="utf-8")


async def investigar(state: ReelState, tema: str) -> dict:
    user_prompt = f"""Investiga el tema '{tema}' usando la herramienta leer_fuente.
Devuelve el dossier terminando con:
```json
{{"tema": "...", "datos": {{}}, "advertencias": []}}
```"""
    resultado = await llamar_agente(
        system_prompt=_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        tools=[leer_fuente],
        allowed_tools=["mcp__herramientas__leer_fuente"],
        max_turns=4,
    )
    dossier = extraer_json(resultado.texto)
    state.dossier = dossier
    state.registrar("investigacion", "investigar", f"tema={tema}")
    return {"dossier": dossier, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
