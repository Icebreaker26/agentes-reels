"""Historial de corridas reales del CLI -- costo MEDIDO, no estimado.

A diferencia del notebook (que solo imprime el costo de esa corrida y se
pierde al cerrar), el CLI es una herramienta de uso repetido: cada corrida
real (voz + render reales, no mocks) queda registrada en
`historial_corridas.jsonl`, una linea JSON por corrida, para poder ver
cuanto ha costado usar esto en el tiempo.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORIAL_PATH = Path(__file__).parent / "historial_corridas.jsonl"


def registrar_corrida(
    *,
    brief: dict[str, Any],
    llamadas: list[dict[str, Any]],
    qa: dict[str, Any],
    video: str | None,
    exitoso: bool,
) -> dict[str, Any]:
    total_input = sum((l.get("uso") or {}).get("input_tokens", 0) for l in llamadas)
    total_output = sum((l.get("uso") or {}).get("output_tokens", 0) for l in llamadas)
    total_costo = sum(l.get("costo_usd", 0) or 0 for l in llamadas)

    registro = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "brief": brief,
        "llamadas_modelo": len(llamadas),
        "tokens_entrada": total_input,
        "tokens_salida": total_output,
        "costo_usd": round(total_costo, 6),
        "qa": qa,
        "video": video,
        "exitoso": exitoso,
    }
    with open(HISTORIAL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return registro


def costo_acumulado() -> float:
    if not HISTORIAL_PATH.exists():
        return 0.0
    total = 0.0
    with open(HISTORIAL_PATH, encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                total += json.loads(linea).get("costo_usd", 0.0)
    return round(total, 6)
