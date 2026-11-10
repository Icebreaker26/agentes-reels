"""Agente de Voz: genera la narracion REAL (OmniVoice) en una sola llamada."""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState
from tools.voice_tools import generar_voz_real

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "voz.txt").read_text(encoding="utf-8")


async def generar_voz(state: ReelState) -> dict:
    user_prompt = f"""Guion:
{state.resumen_json("guion")}

Llama UNA sola vez a generar_voz_real con la lista completa de escenas
(id, texto = la linea de voz de cada escena, max_segundos = su duracion_s).
Devuelve terminando con:
```json
{{"resultados": [{{"escena": "...", "duracion_estimada_s": 0, "archivo_real": "..."}}]}}
```"""
    resultado = await llamar_agente(
        system_prompt=_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        tools=[generar_voz_real],
        allowed_tools=["mcp__herramientas__generar_voz_real"],
        max_turns=8,
    )
    datos = extraer_json(resultado.texto)
    state.voz = datos.get("resultados", [])
    state.registrar("voz", "generar_voz", f"{len(state.voz)} escenas (OmniVoice real)")
    return {"voz": datos, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
