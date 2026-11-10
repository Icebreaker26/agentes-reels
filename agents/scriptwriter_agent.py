"""Agente de Guion: convierte el dossier en una tabla de escenas.

Es el unico agente con modelo Sonnet en vez de Haiku -- es la fase mas
creativa (decidir texto, ritmo, gancho) y la que mas se beneficia de un
modelo mas capaz; el resto son tareas acotadas donde Haiku alcanza. Ver
README, seccion "Costo y eleccion de modelo por agente".
"""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState

MODEL = "claude-sonnet-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "guion.txt").read_text(encoding="utf-8")


async def escribir_guion(state: ReelState, duracion_objetivo_s: int, observaciones: str = "") -> dict:
    extra = f"\nObservaciones de la ronda anterior de QA: {observaciones}\n" if observaciones else ""
    user_prompt = f"""Dossier verificado:
{state.resumen_json("dossier")}

Duracion objetivo del reel: {duracion_objetivo_s} segundos.
{extra}
Devuelve el guion terminando con:
```json
{{"escenas": [{{"id": "...", "duracion_s": 0, "texto_pantalla": "...", "voz": "...", "visual_idea": "..."}}]}}
```"""
    resultado = await llamar_agente(system_prompt=_PROMPT, user_prompt=user_prompt, model=MODEL, max_turns=2)
    guion = extraer_json(resultado.texto)
    state.guion = guion.get("escenas", [])
    state.registrar("guion", "escribir_guion", f"{len(state.guion)} escenas")
    return {"guion": guion, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
