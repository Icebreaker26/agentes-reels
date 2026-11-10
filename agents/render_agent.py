"""Agente de Render: produce el MP4 real -- deliberadamente NO es un LLM.

Misma razon que QA (ver qa_agent.py): una vez el guion esta aprobado y la
voz es real, ensamblar los props y correr `remotion render` es una accion
mecanica y determinista, no una decision creativa. Dejar que un LLM escriba
el codigo de render a mano por cada corrida seria menos confiable que una
composicion generica y data-driven (`AgenteReel`, en el repo publico
`3d-animations-showcase`) que ya sabe leer `escenas` como prop.

Usa la duracion REAL de cada escena (lo que devolvio OmniVoice), no el
estimado original del guion -- asi el video queda sincronizado con la voz.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from state import ReelState

SHOWCASE = Path(r"C:\Users\aleja\Documents\Projects\3d-animations-showcase")
PROPS_PATH = SHOWCASE / "public" / "agente_demo" / "props.json"


def renderizar(state: ReelState, salida: str = "out/agente_demo.mp4") -> dict:
    duraciones = {e["escena"]: e["duracion_estimada_s"] for e in state.voz}

    escenas_props = []
    for e in state.guion:
        eid = e["id"]
        segundos = duraciones.get(eid, e.get("duracion_s", 3))
        escenas_props.append({"id": eid, "segundos": segundos, "texto": e["texto_pantalla"]})

    PROPS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROPS_PATH.write_text(json.dumps({"escenas": escenas_props}, ensure_ascii=False, indent=2), encoding="utf-8")

    comando = [
        "npx",
        "remotion",
        "render",
        "src/index.ts",
        "AgenteReel",
        salida,
        f"--props={PROPS_PATH}",
    ]
    proceso = subprocess.run(
        comando,
        cwd=str(SHOWCASE),
        capture_output=True,
        text=True,
        shell=True,  # necesario en Windows para resolver npx.cmd
        timeout=600,
    )

    reporte = {
        "exitoso": proceso.returncode == 0,
        "video": str(SHOWCASE / salida) if proceso.returncode == 0 else None,
        "props": str(PROPS_PATH),
        "stdout_tail": proceso.stdout[-1500:],
        "stderr_tail": proceso.stderr[-1500:] if proceso.returncode != 0 else "",
    }
    state.registrar(
        "render",
        "renderizar",
        "video generado" if reporte["exitoso"] else f"fallo (exit {proceso.returncode})",
    )
    return reporte
