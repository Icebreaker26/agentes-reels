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
    allowed_tools: list[str] | None = None,
    max_turns: int = 6,
) -> LlamadaResultado:
    """Hace una llamada al Agent SDK y devuelve el texto final + el uso medido.

    Cada agente recibe solo las herramientas que su rol necesita (scoping
    de actuators por agente, ver ARCHITECTURE.md). Sin `tools`, el agente
    no tiene ninguna herramienta -- razona solo con lo que le pasa el prompt.
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
        tools=[],  # sin herramientas built-in (Bash, Read, ...): solo las propias del rol
        permission_mode="bypassPermissions",  # corre sin humano para aprobar; las tools son mocks inocuos
    )

    texto_final = ""
    uso_total: dict = {}
    costo = 0.0
    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    texto_final = block.text
        if isinstance(message, ResultMessage):
            uso_total = message.usage or {}
            costo = message.total_cost_usd or 0.0

    return LlamadaResultado(texto=texto_final, uso=uso_total, costo_usd=costo)


def extraer_json(texto: str) -> dict:
    """Extrae el primer bloque ```json ... ``` de la respuesta del modelo."""
    m = re.search(r"```json\s*(.*?)\s*```", texto, re.DOTALL)
    bruto = m.group(1) if m else texto
    return json.loads(bruto)


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
