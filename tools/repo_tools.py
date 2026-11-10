"""Herramienta REAL del agente de Investigacion: lee un repo/carpeta local.

Es exactamente lo que ya haces tu mismo en el motor de reels real (CLAUDE.md
§0.1: "lee su codigo en ../kernel/"), pero como tool del agente. Solo
lectura, nunca sale de la carpeta dada, y limita cuanto devuelve para no
reventar el contexto del modelo.
"""
from __future__ import annotations

from pathlib import Path

from claude_agent_sdk import tool

MAX_ARCHIVOS = 8
MAX_BYTES_POR_ARCHIVO = 6000
EXTENSIONES_TEXTO = {".ts", ".tsx", ".js", ".jsx", ".py", ".json", ".md", ".txt", ".yaml", ".yml"}

INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "ruta": {"type": "string", "description": "Carpeta local a leer (no sale de ahi)."},
        "patron": {"type": "string", "description": "Patron glob, ej. '*.tsx'. Por defecto '*'."},
    },
    "required": ["ruta"],
}


@tool(
    "leer_repo",
    "Lee archivos de texto dentro de una carpeta local (solo lectura) para investigar un repo o proyecto real.",
    INPUT_SCHEMA,
)
async def leer_repo(args: dict) -> dict:
    base = Path(args["ruta"]).expanduser().resolve()
    patron = args.get("patron") or "*"

    if not base.exists() or not base.is_dir():
        return {
            "content": [{"type": "text", "text": f"La ruta '{base}' no existe o no es una carpeta."}],
            "is_error": True,
        }

    archivos = [p for p in sorted(base.rglob(patron)) if p.is_file() and p.suffix.lower() in EXTENSIONES_TEXTO][
        :MAX_ARCHIVOS
    ]
    if not archivos:
        texto = f"No se encontraron archivos de texto que coincidan con '{patron}' en {base}."
        return {"content": [{"type": "text", "text": texto}]}

    partes = []
    for p in archivos:
        try:
            contenido = p.read_text(encoding="utf-8", errors="replace")[:MAX_BYTES_POR_ARCHIVO]
        except OSError as e:
            contenido = f"(no se pudo leer: {e})"
        partes.append(f"--- {p.relative_to(base)} ---\n{contenido}")

    return {"content": [{"type": "text", "text": "\n\n".join(partes)}]}
