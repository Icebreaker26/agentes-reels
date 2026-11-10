"""Utilidades compartidas para llamar al Agent SDK desde cada agente.

Punto clave: nunca se usa una API key. ClaudeAgentOptions no recibe
credenciales -- el SDK invoca el CLI de Claude Code instalado en la
maquina, que reutiliza la sesion de suscripcion (login OAuth) con la
que ya se trabaja a diario. Verificado con una prueba minima antes de
construir el resto del sistema (ver README, seccion "Autenticacion").
"""
from __future__ import annotations

import asyncio
import json
import re
import threading
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    McpServerConfig,
    ResultMessage,
    SdkMcpTool,
    TextBlock,
    create_sdk_mcp_server,
    query,
)


class RespuestaVaciaError(RuntimeError):
    """El modelo termino la llamada sin texto final -- usualmente por agotar
    `max_turns` antes de redactar el bloque ```json que se le pidio, o por
    un error que interrumpio la conversacion a medias."""


@dataclass
class LlamadaResultado:
    texto: str
    uso: dict
    costo_usd: float


async def llamar_agente(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    tools: list[SdkMcpTool] | None = None,
    tools_builtin: list[str] | None = None,
    allowed_tools: list[str] | None = None,
    max_turns: int = 6,
    cwd: str | None = None,
) -> LlamadaResultado:
    """Hace una llamada al Agent SDK y devuelve el texto final + el uso medido.

    Cada agente recibe solo las herramientas que su rol necesita (scoping
    de actuators por agente, ver ARCHITECTURE.md). Sin `tools` ni
    `tools_builtin`, el agente no tiene ninguna herramienta -- razona solo
    con lo que le pasa el prompt.

    `tools_builtin` habilita herramientas YA incluidas en el Agent SDK (ej.
    `WebSearch`, `WebFetch`) en vez de una propia -- se usa para el agente
    de Investigacion cuando la fuente es internet.

    `cwd` fija el directorio de trabajo del subproceso. Ningun agente lo usa
    hoy (se probo para un agente de codigo con Write/Edit/Bash, descartado:
    la plataforma rechaza crear un subagente con esas herramientas sin
    supervision humana -- "Create Unsafe Agents"). Se deja disponible por
    si algun agente futuro necesita fijar un directorio de trabajo.
    """
    mcp_servers: dict[str, McpServerConfig] = {}
    if tools:
        mcp_servers["herramientas"] = create_sdk_mcp_server(name="herramientas", tools=tools)

    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        model=model,
        mcp_servers=mcp_servers,
        allowed_tools=allowed_tools or [],
        max_turns=max_turns,
        tools=tools_builtin or [],  # sin herramientas built-in salvo que el rol las pida explicitamente
        permission_mode="bypassPermissions",  # corre sin humano para aprobar
        cwd=cwd,
    )

    texto_final = ""
    uso_total: dict = {}
    costo = 0.0
    resultado_msg: ResultMessage | None = None
    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    texto_final = block.text
        if isinstance(message, ResultMessage):
            resultado_msg = message
            uso_total = message.usage or {}
            costo = message.total_cost_usd or 0.0

    if not texto_final.strip():
        detalle = ""
        if resultado_msg is not None:
            detalle = (
                f" (stop_reason={resultado_msg.stop_reason!r}, "
                f"terminal_reason={getattr(resultado_msg, 'terminal_reason', None)!r}, "
                f"is_error={resultado_msg.is_error!r}, "
                f"result={str(getattr(resultado_msg, 'result', ''))[:300]!r})"
            )
        raise RespuestaVaciaError(
            f"El modelo no devolvio texto final tras {max_turns} max_turns.{detalle} "
            "Prueba subiendo max_turns o revisa si una herramienta devolvio un error."
        )

    return LlamadaResultado(texto=texto_final, uso=uso_total, costo_usd=costo)


def extraer_json(texto: str) -> dict:
    """Extrae el primer bloque ```json ... ``` de la respuesta del modelo."""
    m = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
    bruto = m.group(1) if m else texto
    try:
        return json.loads(bruto)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"No se pudo parsear JSON de la respuesta del modelo: {e}\n"
            f"Texto recibido (primeros 1000 caracteres):\n{texto[:1000]!r}"
        ) from e


T = TypeVar("T")


def ejecutar(coro: Coroutine[Any, Any, T]) -> T:
    """Corre una coroutina en un hilo nuevo con su propio event loop.

    El Agent SDK crea un subproceso (el CLI de Claude Code) con
    `asyncio.create_subprocess_exec`. Dentro del kernel de Jupyter en
    Windows, el event loop que ejecuta las celdas no soporta subprocesos
    de forma confiable (`NotImplementedError` en `_make_subprocess_transport`)
    -- es una limitacion conocida de asyncio+Jupyter en Windows, no del SDK.
    Este wrapper evita el problema corriendo la llamada en un hilo aparte
    con un `ProactorEventLoop` propio, que si soporta subprocesos.
    """
    resultado: dict[str, Any] = {}

    def _runner() -> None:
        loop = asyncio.ProactorEventLoop()  # type: ignore[attr-defined]
        asyncio.set_event_loop(loop)
        try:
            resultado["valor"] = loop.run_until_complete(coro)
        except BaseException as exc:  # noqa: BLE001 - se re-lanza en el hilo principal
            resultado["error"] = exc
        finally:
            loop.close()

    hilo = threading.Thread(target=_runner)
    hilo.start()
    hilo.join()

    if "error" in resultado:
        raise resultado["error"]
    return resultado["valor"]
