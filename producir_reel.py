#!/usr/bin/env python
"""CLI para producir un reel con el sistema multiagente.

A diferencia del notebook (un showcase academico de cada agente por
separado), esto es pensado para usarse de verdad: elegir de donde salen
los datos (un repo, una busqueda real, un enlace, o el catalogo demo), ver
el guion, aprobarlo o corregirlo con tu propio feedback, y terminar con un
MP4 real -- todo desde la terminal, sin abrir Jupyter. Cada corrida real
queda registrada en `historial_corridas.jsonl` (ver historial.py).

Uso:
  python producir_reel.py
  python producir_reel.py --fuente-tipo demo --fuente-valor ahorro_voluntario --duracion 20
  python producir_reel.py --fuente-tipo repo --fuente-valor "../kernel/frontend/src/modules/creditos"
  python producir_reel.py --fuente-tipo web --fuente-valor "tasas de ahorro programado en cooperativas en Colombia"
  python producir_reel.py --fuente-tipo url --fuente-valor "https://ejemplo.com/producto"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

if sys.platform == "win32":
    # La consola de Windows por defecto usa cp1252, que no sabe codificar
    # glifos como "⚠" -- rich asume UTF-8.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

import historial
from agents import (
    orchestrator,
    qa_agent,
    render_agent,
    research_agent,
    scriptwriter_agent,
    visual_agent,
    voice_agent,
)
from agents._sdk_helpers import ejecutar
from state import ReelState
from tools.research_tools import FUENTE_DEMO

console = Console()

FUENTES_INFO = {
    "demo": "catalogo controlado, sin salir a internet (rapido, para pruebas)",
    "repo": "una carpeta local real (lee codigo/documentos, como harias tu mismo)",
    "web": "una busqueda real en internet (WebSearch/WebFetch)",
    "url": "un enlace puntual a investigar o replicar (ej. una referencia estetica)",
}


def elegir_fuente() -> tuple[str, str]:
    console.print(Panel("¿De donde saca los datos el agente de Investigacion?", box=box.ROUNDED))
    tipos = list(FUENTES_INFO.keys())
    for i, t in enumerate(tipos, 1):
        console.print(f"  [cyan]{i}[/cyan]. [bold]{t}[/bold] -- {FUENTES_INFO[t]}")
    idx = Prompt.ask("Elige un tipo de fuente", choices=[str(i) for i in range(1, len(tipos) + 1)], default="1")
    tipo = tipos[int(idx) - 1]

    if tipo == "demo":
        temas = list(FUENTE_DEMO.keys())
        for i, t in enumerate(temas, 1):
            console.print(f"  [cyan]{i}[/cyan]. {t}")
        idx2 = Prompt.ask("Elige un tema del catalogo", choices=[str(i) for i in range(1, len(temas) + 1)], default="1")
        return tipo, temas[int(idx2) - 1]
    if tipo == "repo":
        valor = Prompt.ask("Ruta de la carpeta a investigar (local)")
    elif tipo == "web":
        valor = Prompt.ask("¿Qué debe buscar en internet?")
    else:
        valor = Prompt.ask("Pega el enlace (URL)")
    return tipo, valor


def mostrar_guion(state: ReelState) -> None:
    tabla = Table(title="Guion actual", box=box.SIMPLE_HEAVY, show_lines=True)
    tabla.add_column("ID", style="cyan")
    tabla.add_column("Seg", justify="right")
    tabla.add_column("Texto en pantalla")
    tabla.add_column("Voz")
    for e in state.guion:
        tabla.add_row(e["id"], str(e["duracion_s"]), e["texto_pantalla"], e["voz"])
    console.print(tabla)


def aprobar_guion(state: ReelState, duracion_objetivo_s: int, max_rondas: int = 5) -> None:
    """Gate de aprobacion humana real -- aqui si hay stdin de terminal, a
    diferencia del notebook (ver ARCHITECTURE.md, decision de no incluirlo ahi)."""
    for _ in range(max_rondas):
        mostrar_guion(state)
        respuesta = Prompt.ask("\n¿Aprobar? [s = si / escribe tu feedback para corregir]", default="s")
        if respuesta.strip().lower() in ("s", "si", "sí", "y", "yes"):
            state.registrar("humano", "aprobacion", "aprobado sin cambios")
            console.print("[bold green]Guion aprobado.[/bold green]")
            return
        state.registrar("humano", "feedback", respuesta)
        with console.status("[bold yellow]Ajustando el guion con tu feedback..."):
            ejecutar(
                scriptwriter_agent.escribir_guion(
                    state, duracion_objetivo_s=duracion_objetivo_s, observaciones=respuesta
                )
            )
    console.print("[yellow]Se agotaron las rondas de ajuste; se continua con el ultimo guion.[/yellow]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Produce un reel real con el sistema multiagente.")
    parser.add_argument("--fuente-tipo", choices=list(FUENTES_INFO.keys()), help="De donde salen los datos.")
    parser.add_argument("--fuente-valor", help="Tema (demo), ruta (repo), consulta (web) o URL (url).")
    parser.add_argument("--duracion", type=int, default=20, help="Duracion objetivo en segundos.")
    parser.add_argument("--salida", default="out/agente_demo.mp4", help="Ruta de salida, relativa al repo showcase.")
    args = parser.parse_args()

    console.rule("[bold cyan]Agente de produccion de reels")

    if args.fuente_tipo and args.fuente_valor:
        fuente_tipo, fuente_valor = args.fuente_tipo, args.fuente_valor
    else:
        fuente_tipo, fuente_valor = elegir_fuente()

    brief = {
        "fuente_tipo": fuente_tipo,
        "fuente_valor": fuente_valor,
        "cliente_demo": "Cooperativa Demo (dato ficticio)",
        "duracion_objetivo_s": args.duracion,
    }
    state = ReelState(brief=brief)
    llamadas: list[dict] = []

    with console.status("[bold]Orquestador planificando..."):
        llamadas.append(ejecutar(orchestrator.planificar(state)))
    console.print(f"[dim]Plan: {' -> '.join(state.plan)}[/dim]")

    with console.status(f"[bold]Investigando ({fuente_tipo})..."):
        llamadas.append(ejecutar(research_agent.investigar(state, fuente_tipo=fuente_tipo, fuente_valor=fuente_valor)))
    for a in state.dossier.get("advertencias", []):
        console.print(f"[yellow]⚠ {a}[/yellow]")

    with console.status("[bold]Escribiendo el guion..."):
        llamadas.append(ejecutar(scriptwriter_agent.escribir_guion(state, duracion_objetivo_s=args.duracion)))

    aprobar_guion(state, args.duracion)

    with console.status("[bold]Visual/3D decidiendo kit e ideas..."):
        llamadas.append(ejecutar(visual_agent.generar_visual(state, kit="cartoon")))

    console.print("\n[bold]Generando voz real con OmniVoice...[/bold] (puede tardar varios minutos)")
    with console.status("[bold magenta]Sintetizando narracion..."):
        llamadas.append(ejecutar(voice_agent.generar_voz(state)))

    reporte_qa = qa_agent.verificar(state, duracion_objetivo_s=args.duracion)
    if reporte_qa["aprobado"]:
        console.print(f"[green]QA aprobado[/green] -- duracion total {reporte_qa['duracion_total_estimada_s']}s")
    else:
        console.print(f"[red]QA rechazo:[/red] {'; '.join(reporte_qa['problemas'])}")
        if state.intentos_replanificacion < 1 and Confirm.ask("¿Dejar que el Orquestador replanifique?", default=True):
            with console.status("[bold]Replanificando..."):
                decision = ejecutar(
                    orchestrator.replanificar(state, observaciones="; ".join(reporte_qa["problemas"]))
                )
                llamadas.append(decision)
                instruccion = decision["decision"].get("instruccion", "")
                llamadas.append(
                    ejecutar(
                        scriptwriter_agent.escribir_guion(
                            state, duracion_objetivo_s=args.duracion, observaciones=instruccion
                        )
                    )
                )
            aprobar_guion(state, args.duracion)
            with console.status("[bold magenta]Regenerando voz..."):
                llamadas.append(ejecutar(voice_agent.generar_voz(state)))
            reporte_qa = qa_agent.verificar(state, duracion_objetivo_s=args.duracion)
            estado_qa = "[green]aprobado[/green]" if reporte_qa["aprobado"] else "[red]rechazado[/red]"
            console.print(f"QA tras replanificacion: {estado_qa}")

    console.print("\n[bold]Renderizando video real...[/bold] (uno o dos minutos)")
    with console.status("[bold blue]Corriendo remotion render..."):
        reporte_render = render_agent.renderizar(state, salida=args.salida)

    if reporte_render["exitoso"]:
        console.print(Panel(f"[bold green]Listo:[/bold green] {reporte_render['video']}", title="Video generado", box=box.DOUBLE))
    else:
        console.print(Panel(reporte_render["stderr_tail"], title="[bold red]Fallo el render[/bold red]", box=box.DOUBLE))

    registro = historial.registrar_corrida(
        brief=brief,
        llamadas=llamadas,
        qa=reporte_qa,
        video=reporte_render.get("video"),
        exitoso=reporte_render["exitoso"],
    )
    console.print(
        Panel(
            f"Llamadas al modelo: {registro['llamadas_modelo']}\n"
            f"Tokens entrada/salida: {registro['tokens_entrada']} / {registro['tokens_salida']}\n"
            f"Costo de esta corrida: ${registro['costo_usd']:.4f} USD\n"
            f"Costo acumulado (historial completo): ${historial.costo_acumulado():.4f} USD",
            title="Costo medido (no estimado)",
            box=box.ROUNDED,
        )
    )


if __name__ == "__main__":
    main()
