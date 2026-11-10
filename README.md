# Agente Multi-Rol para Producción de Reels 3D

Proyecto de la materia **Agentes Inteligentes**. Avance inicial: un sistema
multiagente que planifica la producción de un reel corto (video institucional
1080×1920) coordinando seis roles especializados sobre un estado compartido.

## Descripción del proyecto

En producción real (proyecto hermano, no público: motor de reels con
Remotion + Three.js), un desarrollador asistido por un agente de código
pasa por las mismas fases una y otra vez para cada video: investigar los
datos reales del cliente, escribir el guion escena por escena, generar la
narración con un modelo de voz, especificar las animaciones 3D, y verificar
que todo cuadre antes de dar por terminado el reel.

Este proyecto toma esas fases y las modela formalmente como **agentes
especializados** que colaboran bajo un orquestador, en vez de un solo
agente genérico que hace todo. El resultado de esta primera entrega es un
notebook que corre ese sistema de punta a punta con llamadas reales a un
modelo de lenguaje y que **termina produciendo un video MP4 real, con voz
real** generada por OmniVoice — no solo una especificación simulada.

## Objetivo general

Diseñar y demostrar un sistema multiagente donde roles especializados
(Investigación, Guion, Voz, Visual/3D, QA) colaboran bajo un Orquestador
para producir la especificación completa de un video corto, aplicando de
forma explícita los marcos de **PEAS** (Russell & Norvig) y de
**perfilamiento / memoria / planificación / acción** para agentes basados
en LLM (Wang et al., 2023).

## Entregables que delimitan el alcance

Lo que **sí** cubre este avance:
- ✅ Seis agentes funcionando con llamadas reales al modelo (Agent SDK),
  coordinados por un `ReelState` compartido.
- ✅ **Voz real**: el agente de Voz llama de verdad a OmniVoice (subproceso
  al venv de OmniVoice) y obtiene la duración real de cada línea — no una
  estimación.
- ✅ **Video real**: un agente de Render (código puro, no un LLM) ensambla
  el guion + las duraciones reales en una composición genérica de Remotion
  (`AgenteReel`, en el repo público `3d-animations-showcase`) y produce un
  MP4 real.
- ✅ Investigación y Visual/3D usan herramientas reales (tool-calling) que
  siguen **mockeadas** — ver justificación de Visual más abajo.
- ✅ Un ciclo de replanificación: si el QA (determinístico, no un LLM)
  rechaza el resultado, el Orquestador decide una corrección y se repite
  una vez el ciclo Guion → Voz → QA.
- ✅ Medición real del costo/uso de tokens de la corrida (no un estimado).
- ✅ Diagrama de arquitectura (`ARCHITECTURE.md`) y estructura de carpetas
  que refleja esa arquitectura.

Lo que **no** cubre (fuera de alcance de este avance, trabajo futuro):
- ❌ El Visual/3D sigue mockeado: decide kit/idea por escena, pero no
  genera código TSX distinto por reel — la composición `AgenteReel` es
  genérica y data-driven a propósito (ver ARCHITECTURE.md, "Por qué el
  render es código, no un LLM").
- ❌ Integrar este sistema multiagente con el pipeline de producción real
  (reels de clientes, repo privado `3d-animations`) — este avance solo usa
  el motor público (`3d-animations-showcase`).
- ❌ Una interfaz de usuario — este es un notebook de demostración.

**Precondición operativa real, no cosmética:** OmniVoice es pesado y esta
máquina tiene poca memoria virtual (ver `3d-animations/CLAUDE.md`, sección
de problemas conocidos). Antes de correr la celda de voz del notebook hay
que cerrar WSL y Chrome — si no, la generación puede fallar o colgarse. El
notebook lo advierte en la celda correspondiente; no se automatiza porque
cerrar WSL puede tumbar Docker/Postgres de otro trabajo del usuario.

## Autenticación: sin API key, con la suscripción de Claude

Antes de construir el sistema completo se hizo una prueba mínima para
confirmar que el [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
puede autenticarse con la misma sesión OAuth que usa Claude Code (ligada a
una suscripción Pro/Max), **sin necesitar una `ANTHROPIC_API_KEY`** ni
facturación por token separada. La confirmación quedó en el campo
`apiKeySource: "none"` del mensaje `SystemMessage` que el SDK emite al
iniciar cada llamada — ver `agents/_sdk_helpers.py`.

Requisito para ejecutar este notebook en otra máquina: tener el CLI de
Claude Code instalado y logueado (`claude /login`) con una suscripción
activa.

## Costo y elección de modelo por agente

Cada llamada es corta (un prompt de rol + un fragmento acotado del estado
compartido, sin leer archivos completos ni imágenes), así que el costo de
una corrida completa es marginal frente al de una sesión de producción real
en Claude Code. El notebook mide e imprime el uso real al final (celda 9).

La elección de modelo por agente es deliberada, no uniforme:

| Agente | Modelo | Por qué |
|---|---|---|
| Orquestador | Haiku | decisión acotada, formato fijo |
| Investigación | Haiku | una llamada a herramienta, sin creatividad |
| **Guion** | **Sonnet** | única fase creativa real: tono, ritmo, gancho |
| Voz | Haiku | una sola llamada de lote a OmniVoice, sin creatividad |
| Visual/3D | Haiku | decide kit/idea, no genera código |
| QA | — (Python puro) | ver más abajo |
| Render | — (Python puro) | ensamblar props + `remotion render`, ver más abajo |

## Estructura del repo

```
agentes-reels/
  README.md
  ARCHITECTURE.md
  requirements.txt
  state.py                 ← memoria compartida (ReelState)
  prompts/                 ← perfil/rol de cada agente (texto plano)
  tools/                   ← research/visual mockeados; voice_tools.py es REAL (OmniVoice)
  agents/                  ← un módulo por agente + helpers del Agent SDK
    render_agent.py        ← código puro: arma props y corre `remotion render`
  notebooks/
    01_demo_multiagente.ipynb
```

El video real se genera en un repo hermano público,
`3d-animations-showcase` (`src/agente-reel/AgenteReel.tsx` +
`src/Root.tsx`), no dentro de este repo — así el proyecto académico nunca
necesita vendorizar el motor de reels completo.

## Fundamentación en teoría de agentes

Ver `ARCHITECTURE.md` para el detalle punto por punto. Resumen:

- **PEAS**: el *performance measure* es el chequeo determinístico de QA
  (duración total vs. objetivo, consistencia de IDs de escena), no una
  opinión del propio LLM sobre su trabajo.
- **Perfilamiento**: cada agente tiene un rol fijo y acotado, escrito en
  `prompts/*.txt`, con reglas explícitas de qué no debe inventar.
- **Memoria**: un solo objeto compartido (`ReelState`); cada agente ve solo
  el campo que su rol necesita, no todo el estado.
- **Planificación**: el Orquestador decide el plan y, si falla el QA,
  decide una replanificación acotada (un solo reintento).
- **Acción**: Investigación y Visual actúan con herramientas mockeadas del
  Agent SDK; Voz actúa con una herramienta real (`generar_voz_real`) que
  invoca OmniVoice de verdad; el Render final es código determinístico
  (no una herramienta del LLM) que produce el MP4.
