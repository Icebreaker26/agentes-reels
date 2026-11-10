"""Agente de Voz: estima la duracion real de cada linea via `generar_voz_mock`."""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState
from tools.voice_tools import generar_voz_mock

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "voz.txt").read_text(encoding="utf-8")


async def generar_voz(state: ReelState) -> dict:
    user_prompt = f"""Guion:
{state.resumen_json("guion")}

Por cada escena, llama a generar_voz_mock con su id y su linea de voz,
y recoge la duracion estimada. Devuelve terminando con:
```json
{{"resultados": [{{"escena": "...", "duracion_estimada_s": 0, "archivo_simulado": "..."}}]}}
```"""
    resultado = await llamar_agente(
        system_prompt=_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        tools=[generar_voz_mock],
        allowed_tools=["mcp__herramientas__generar_voz_mock"],
        max_turns=8,
    )
    datos = extraer_json(resultado.texto)
    state.voz = datos.get("resultados", [])
    state.registrar("voz", "generar_voz", f"{len(state.voz)} escenas")
    return {"voz": datos, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
