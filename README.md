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
notebook que corre ese sistema de punta a punta usando llamadas reales a
un modelo de lenguaje (no simuladas), aunque las herramientas externas que
en producción generarían audio y video real (OmniVoice, Remotion) están
mockeadas a propósito — ver "Entregables" abajo.

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
- ✅ Tres de ellos usan herramientas reales (tool-calling) que **simulan**
  (mockean) una llamada a un servicio externo (lectura de fuente, voz, 3D).
- ✅ Un ciclo de replanificación: si el QA (determinístico, no un LLM)
  rechaza el resultado, el Orquestador decide una corrección y se repite
  una vez el ciclo Guion → Voz → QA.
- ✅ Medición real del costo/uso de tokens de la corrida (no un estimado).
- ✅ Diagrama de arquitectura (`ARCHITECTURE.md`) y estructura de carpetas
  que refleja esa arquitectura.

Lo que **no** cubre (fuera de alcance de este avance, trabajo futuro):
- ❌ Generar audio o video real (eso vive en el proyecto de producción,
  privado, con datos de clientes reales).
- ❌ Integrar este sistema multiagente con el pipeline de producción real.
- ❌ Una interfaz de usuario — este es un notebook de demostración.

Mockear la herramienta de voz no es solo para que la demo sea barata: el
modelo real de voz (OmniVoice) es pesado y en esta máquina compite por
memoria virtual con todo lo demás (ver `3d-animations/CLAUDE.md`, sección
de problemas conocidos — a veces hay que cerrar WSL y Chrome solo para
generar un audio). Que un notebook de clase dependa de esa carga sería
frágil; la herramienta mock aisla por completo el diseño del agente de
esa fragilidad de infraestructura.

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
| Voz | Haiku | traduce guion a llamadas de herramienta |
| Visual/3D | Haiku | idem |
| QA | — (Python puro) | ver más abajo |

## Estructura del repo

```
agentes-reels/
  README.md
  ARCHITECTURE.md
  requirements.txt
  state.py                 ← memoria compartida (ReelState)
  prompts/                 ← perfil/rol de cada agente (texto plano)
  tools/                   ← herramientas mock (research/voice/visual)
  agents/                  ← un módulo por agente + helpers del Agent SDK
  notebooks/
    01_demo_multiagente.ipynb
```

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
- **Acción**: los agentes de Investigación, Voz y Visual actúan a través
  de herramientas reales del Agent SDK (`@tool`), que en este avance están
  mockeadas — simulan la llamada a OmniVoice/Remotion sin ejecutarla.
