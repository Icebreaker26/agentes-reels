"""Herramienta REAL del agente de Voz: invoca OmniVoice de verdad.

No mockea nada -- llama a `scripts/narracion.py` del motor de reels
(`3d-animations`, repo privado) como subproceso, en el venv propio de
OmniVoice (PyTorch+CUDA). Se le pide TODO el guion en una sola llamada
(una lista de lineas) para cargar el modelo una sola vez, igual que hace
el motor real -- llamarlo escena por escena recargaria el modelo cada vez.

Precondicion conocida (ver CLAUDE.md del motor de reels): esta maquina
tiene poca memoria virtual. Antes de correr esto, cerrar WSL y Chrome
-- nunca se hace automaticamente aqui, es una accion que le corresponde
al usuario decidir.

Escribe el audio directamente en `public/agente_demo/audio/` del repo
publico `3d-animations-showcase`, para que la composicion `AgenteReel`
lo sirva con `staticFile(...)` sin necesidad de copiar nada.
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from claude_agent_sdk import tool

MOTOR_REELS = Path(r"C:\Users\aleja\Documents\Projects\3d-animations")
SHOWCASE = Path(r"C:\Users\aleja\Documents\Projects\3d-animations-showcase")
OMNIVOICE_PY = Path(r"C:\Users\aleja\Documents\Projects\OmniVoice\.venv\Scripts\python.exe")
NARRACION_SCRIPT = MOTOR_REELS / "scripts" / "narracion.py"

# Voz automatica que le gusta al usuario (CLAUDE.md del motor de reels, §0.5):
# se reutiliza como referencia para clonar, asi suena igual en todos los videos.
REF_AUDIO = MOTOR_REELS / "public" / "progresemos" / "audio_auto" / "voz_candidata_0.wav"
REF_TEXT = "Hola, en Progresemos te acompañamos a ahorrar, a crecer y a cumplir tus metas con tranquilidad."

AUDIO_OUT = SHOWCASE / "public" / "agente_demo" / "audio"

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "escenas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "texto": {"type": "string"},
                    "max_segundos": {"type": "number"},
                },
                "required": ["id", "texto", "max_segundos"],
            },
        }
    },
    "required": ["escenas"],
}


@tool(
    "generar_voz_real",
    "Genera la narracion real (OmniVoice) de TODAS las escenas en una sola corrida y devuelve la duracion real de cada una.",
    INPUT_SCHEMA,
)
async def generar_voz_real(args: dict) -> dict:
    escenas = args["escenas"]
    AUDIO_OUT.mkdir(parents=True, exist_ok=True)

    config = {
        "out": str(AUDIO_OUT),
        "language": "es",
        "ref_text": REF_TEXT,
        "ref_audio": str(REF_AUDIO),
        "speed": 1.0,
        "lines": [{"file": e["id"], "text": e["texto"], "max": e["max_segundos"]} for e in escenas],
    }
    config_path = AUDIO_OUT / "_config_generado.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    env = {**os.environ, "HF_HUB_CACHE": "D:/hf-cache", "PYTHONUTF8": "1"}
    proceso = await asyncio.create_subprocess_exec(
        str(OMNIVOICE_PY),
        str(NARRACION_SCRIPT),
        "--config",
        str(config_path),
        cwd=str(MOTOR_REELS),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proceso.communicate()

    if proceso.returncode != 0:
        texto = (
            f"OmniVoice fallo (exit {proceso.returncode}). stderr:\n"
            f"{stderr.decode(errors='replace')[-2000:]}"
        )
        return {"content": [{"type": "text", "text": texto}], "is_error": True}

    resultado = json.loads((AUDIO_OUT / "resultado.json").read_text(encoding="utf-8"))
    salida = {
        "resultados": [
            {
                "escena": item["file"].removesuffix(".wav"),
                "duracion_estimada_s": item["seconds"],
                "archivo_real": str(AUDIO_OUT / item["file"]),
            }
            for item in resultado["lineas"]
        ]
    }
    return {"content": [{"type": "text", "text": json.dumps(salida, ensure_ascii=False)}]}
