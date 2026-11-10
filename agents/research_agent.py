"""Agente de Investigacion: la herramienta que usa depende del TIPO de fuente.

No hay un catalogo fijo de temas -- el usuario decide de donde salen los
datos: un repo local, una busqueda real en internet, un enlace puntual, o
(solo para pruebas rapidas) el catalogo demo. Ver prompts/investigacion.txt.
"""
from __future__ import annotations

from pathlib import Path

from agents._sdk_helpers import extraer_json, llamar_agente
from state import ReelState
from tools.repo_tools import leer_repo
from tools.research_tools import leer_fuente

MODEL = "claude-haiku-5-5"
_PROMPT = (Path(__file__).parent.parent / "prompts" / "investigacion.txt").read_text(encoding="utf-8")

_CONFIG_POR_TIPO = {
    "demo": {"tools": [leer_fuente], "tools_builtin": [], "allowed": ["mcp__herramientas__leer_fuente"]},
    "repo": {"tools": [leer_repo], "tools_builtin": [], "allowed": ["mcp__herramientas__leer_repo"]},
    "web": {"tools": [], "tools_builtin": ["WebSearch", "WebFetch"], "allowed": ["WebSearch", "WebFetch"]},
    "url": {"tools": [], "tools_builtin": ["WebFetch"], "allowed": ["WebFetch"]},
}


async def investigar(state: ReelState, fuente_tipo: str, fuente_valor: str) -> dict:
    if fuente_tipo not in _CONFIG_POR_TIPO:
        raise ValueError(f"fuente_tipo desconocido: {fuente_tipo!r} (usa demo/repo/web/url)")
    cfg = _CONFIG_POR_TIPO[fuente_tipo]

    user_prompt = f"""Fuente:
tipo = "{fuente_tipo}"
valor = "{fuente_valor}"

Usa la herramienta que corresponde a este tipo de fuente (ver tu prompt de
rol) y devuelve el dossier terminando con:
```json
{{"fuente_tipo": "{fuente_tipo}", "fuente_valor": "{fuente_valor}", "datos": {{}}, "advertencias": []}}
```"""
    resultado = await llamar_agente(
        system_prompt=_PROMPT,
        user_prompt=user_prompt,
        model=MODEL,
        tools=cfg["tools"],
        tools_builtin=cfg["tools_builtin"],
        allowed_tools=cfg["allowed"],
        max_turns=6,
    )
    dossier = extraer_json(resultado.texto)
    state.dossier = dossier
    state.registrar("investigacion", "investigar", f"fuente={fuente_tipo}:{fuente_valor}")
    return {"dossier": dossier, "uso": resultado.uso, "costo_usd": resultado.costo_usd}
