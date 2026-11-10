"""Agente Orquestador.

Decide el plan de fases al inicio y, si el QA (chequeo deterministico,
ver qa_agent.py) encuentra un problema, decide como replanificar. El
notebook limita esto a un solo intento de replanificacion para que la
corrida termine siempre en un numero acotado de llamadas al modelo.
"""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "orquestador.txt").read_text(encoding="utf-8")


async def planificar(state: ReelState) -> dict:
    user_prompt = f"""Brief del reel:
{state.resumen_json("brief")}

Decide el plan de fases (orden de agentes a ejecutar) para producir el
guion, la voz y el visual de este reel. Devuelve:
```json
{{"fases": ["investigacion", "guion", "voz_y_visual", "qa"], "razon": "..."}}
```"""
    resultado = await llamar_agente(system_prompt=_PROMPT, user_prompt=user_prompt, model=MODEL, max_turns=2)
    plan = extraer_json(resultado.texto)
    state.plan = plan.get("fases", [])
    state.registrar("orquestador", "planificar", plan.get("razon", ""))
    return {"plan": plan, "uso": resultado.uso, "costo_usd": resultado.costo_usd}


async def replanificar(state: ReelState, observaciones: str) -> dict:
    state.intentos_replanificacion += 1
    user_prompt = f"""El QA encontro este problema con el guion actual:
{observaciones}

Guion actual:
{state.resumen_json("guion")}

Decide que agente debe corregir el problema y con que instruccion
especifica. Devuelve:
```json
{{"agente_a_repetir": "guion", "instruccion": "..."}}
```"""
    resultado = await llamar_agente(system_prompt=_PROMPT, user_prompt=user_prompt, model=MODEL, max_turns=2)
    decision = extraer_json(resultado.texto)
    state.registrar("orquestador", "replanificar", decision.get("instruccion", ""))
    return {"decision": decision, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
