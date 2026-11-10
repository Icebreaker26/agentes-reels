"""Agente de QA: chequeo deterministico -- deliberadamente NO es una llamada a un LLM.

Decision de diseño: el criterio de exito (PEAS -> performance measure)
debe ser verificable de forma objetiva, igual que el motor real de reels
verifica con `tsc`, stills y `audio_levels.mjs` en vez de "a ojo". Pedirle
a un LLM que juzgue su propio trabajo es menos confiable que comparar
numeros -- por eso este agente es puro Python.
"""
from __future__ import annotations

from state import ReelState

TOLERANCIA = 0.15  # +/- 15% de la duracion objetivo


def verificar(state: ReelState, duracion_objetivo_s: int) -> dict:
    problemas: list[str] = []
    duraciones = []
    for e in state.voz:
        d = e.get("duracion_estimada_s")
        if not isinstance(d, (int, float)):
            problemas.append(f"La escena '{e.get('escena')}' no trajo una duracion real valida (vino {d!r}).")
            d = 0
        duraciones.append(d)

    total = round(sum(duraciones), 2)
    delta = (total - duracion_objetivo_s) / duracion_objetivo_s if duracion_objetivo_s else 0

    if abs(delta) > TOLERANCIA:
        problemas.append(
            f"Duracion total estimada ({total}s) se desvia {delta:+.0%} del objetivo "
            f"({duracion_objetivo_s}s), fuera de la tolerancia de ±{TOLERANCIA:.0%}."
        )

    ids_guion = {e.get("id") for e in state.guion}
    ids_voz = {e.get("escena") for e in state.voz}
    if ids_guion != ids_voz:
        problemas.append(f"Las escenas del guion {ids_guion} no coinciden con las de voz {ids_voz}.")

    aprobado = not problemas
    reporte = {
        "aprobado": aprobado,
        "duracion_total_estimada_s": total,
        "desviacion": round(delta, 3),
        "problemas": problemas,
    }
    state.qa = reporte
    state.registrar("qa", "verificar", "aprobado" if aprobado else "; ".join(problemas))
    return reporte
