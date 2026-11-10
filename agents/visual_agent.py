"""Agente Visual/3D: decide kit de estilo y especifica assets via `generar_visual_mock`."""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState
from tools.visual_tools import generar_visual_mock

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "visual.txt").read_text(encoding="utf-8")


async def generar_visual(state: ReelState, kit: str = "cartoon") -> dict:
    user_prompt = f"""Guion:
{state.resumen_json("guion")}

Kit de estilo sugerido: {kit}.
Por cada escena, llama a generar_visual_mock con el kit y una descripcion
breve de la idea visual de esa escena. Devuelve terminando con:
```json
{{"resultados": [{{"escena": "...", "kit": "...", "archivo_simulado": "..."}}]}}
```"""
    resultado = await llamar_agente(
        system_prompt=_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        tools=[generar_visual_mock],
        allowed_tools=["mcp__herramientas__generar_visual_mock"],
        max_turns=8,
    )
    datos = extraer_json(resultado.texto)
    state.visual = datos.get("resultados", [])
    state.registrar("visual", "generar_visual", f"{len(state.visual)} escenas")
    return {"visual": datos, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
