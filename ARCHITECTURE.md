# Arquitectura

## Diagrama

```
                         ┌─────────────────┐
                         │   ReelState      │   memoria compartida
                         │  (state.py)      │   (brief, plan, dossier,
                         └───────▲──────────┘    guion, voz, visual, qa, log)
                                 │  lee / actualiza
            ┌────────────────────┼────────────────────┐
            │                    │                     │
   ┌────────▼────────┐  ┌────────▼────────┐   ┌────────▼────────┐
   │   Orquestador    │  │  Investigacion   │   │     Guion       │
   │  (Haiku)         │  │  (Haiku)         │   │    (Sonnet)     │
   │  planifica,      │  │  tool REAL segun │   │  escribe la     │
   │  replanifica     │  │  fuente_tipo:    │   │  tabla de       │
   │                  │  │  leer_repo /     │   │  escenas        │
   │                  │  │  WebSearch+Fetch │   │                 │
   │                  │  │  / leer_fuente   │   │                 │
   └────────┬─────────┘  └──────────────────┘   └────────┬────────┘
            │                                               │
            │  si falla QA, decide correccion              │
            │                                               │
            │              ┌────────────────────────────────┘
            │              │
   ┌────────▼────────┐  ┌──▼──────────────┐
   │      Voz         │  │    Visual/3D     │
   │   (Haiku)         │  │   (Haiku)        │
   │  tool REAL:       │  │  tool mock:      │
   │  generar_voz_real │  │  generar_visual_mock │
   │  (OmniVoice, 1    │  │  (decide kit/idea,   │
   │  llamada por lote)│  │  no genera codigo)   │
   └────────┬──────────┘  └────────┬─────────┘
            │                      │
            └──────────┬───────────┘
                        │
               ┌────────▼─────────┐
               │       QA          │   determinístico, NO es un LLM
               │  (Python puro)    │   compara duracion total vs.
               │                   │   objetivo + consistencia de IDs
               └────────┬──────────┘
                        │
              aprobado ─┴─ no aprobado → vuelve al Orquestador (1 reintento)
                        │
               ┌────────▼─────────┐
               │     Render         │   determinístico, NO es un LLM
               │  (Python puro)     │   arma props (guion + duracion real
               │                    │   de voz) y corre `remotion render`
               └────────┬───────────┘
                        │
                  MP4 real, con voz real
                  (composicion AgenteReel en 3d-animations-showcase)
```

Cada flecha hacia `ReelState` es una lectura (`resumen_json`, acotada a los
campos que ese rol necesita) o una escritura (el agente actualiza su campo
y llama a `state.registrar(...)` para dejar rastro en la bitácora).

## Perfilamiento (rol)

Framework de 4 módulos para agentes basados en LLM (Wang et al., *"A
Survey on Large Language Model based Autonomous Agents"*, arXiv:2308.11432):
el *profiling module* define quién es el agente antes de que actúe. Aquí
cada agente tiene un prompt de rol propio en `prompts/*.txt`, con reglas
explícitas de qué NO debe hacer (inventar cifras, decidir fuera de su
fase). El agente de QA no tiene prompt porque no es un rol de LLM — es una
decisión de diseño explicada en `agents/qa_agent.py`.

## Entorno — PEAS (Russell & Norvig)

- **Performance**: el reporte de QA (`qa_agent.verificar`) — determinístico,
  no depende de que el LLM se autoevalúe.
- **Environment**: parcialmente observable (cada agente solo ve el campo
  del `ReelState` que le corresponde, no el estado completo); secuencial
  dentro de una corrida (el guion depende del dossier, la voz del guion);
  episódico entre corridas del notebook (no hay memoria persistente);
  multiagente con un orquestador central, a diferencia del motor real de
  reels (documentado como agente único en el repo `3d-animations-showcase`).
- **Actuators**: cada agente solo tiene acceso a la(s) herramienta(s) de
  su propio rol (`allowed_tools` en `agents/_sdk_helpers.py`) — Investigación
  no puede llamar a `generar_voz_mock`, por ejemplo. Nunca tienen acceso a
  herramientas built-in (`Bash`, `Read`, etc.) porque `tools=[]` las
  desactiva explícitamente.
- **Sensors**: la respuesta de texto del modelo (parseada como JSON) y el
  resultado de las herramientas mock, que simulan lo que en producción
  real serían los "sensores" del motor de reels (stills, transcripción,
  niveles de audio).

## Memoria

Un solo objeto, `ReelState`, pasado explícitamente de agente a agente — no
hay memoria implícita ni persistente entre corridas del notebook. Cada
agente ve solo el campo que necesita (`state.resumen_json("dossier")`,
por ejemplo), no el objeto completo: esto modela el hecho de que en un
sistema multiagente real cada rol tiene acceso acotado a la información,
no un contexto compartido sin filtro.

## Planificación

El Orquestador decide el plan al inicio (`orchestrator.planificar`) y,
si el QA rechaza el resultado, decide una corrección específica
(`orchestrator.replanificar`). El notebook limita esto a **un solo
reintento** — no porque la teoría lo exija, sino para que la demo termine
en un número acotado y predecible de llamadas al modelo.

## Acción

Los agentes de Investigación, Voz y Visual actúan llamando a herramientas
reales del Agent SDK (`@tool`, `create_sdk_mcp_server`, o herramientas ya
incluidas en el SDK como `WebSearch`/`WebFetch`) — esto es tool-calling
genuino, no un JSON simulado: el modelo decide cuándo y con qué argumentos
llamar a la herramienta, y el SDK ejecuta la función correspondiente.

Investigación es el caso más rico: la herramienta que recibe depende del
`fuente_tipo` (ver `agents/research_agent.py` → `_CONFIG_POR_TIPO`) — un
repo local (`leer_repo`, solo lectura, real), internet (`WebSearch` +
`WebFetch`, reales) o el catálogo demo (`leer_fuente`, mock, solo para
pruebas rápidas sin red). Voz también es real (`generar_voz_real`, invoca
OmniVoice). Lo que sigue mockeado es Visual/3D — **la implementación** de
`generar_visual_mock`, no el mecanismo de acción del agente.

## Por qué QA es código, no un agente LLM

Pedirle a un modelo que evalúe su propio trabajo (o el de otro agente) es
menos confiable que una verificación objetiva cuando la verificación se
puede expresar como una comparación de números. El motor real de reels
sigue el mismo principio: verifica con `tsc`, stills leídos como imagen,
y métricas de audio (`audio_levels.mjs`) en vez de pedirle a un agente que
diga "se ve bien". Aquí, `qa_agent.verificar` es Python puro.

## Por qué el render es código, no un LLM

Una vez el guion está aprobado y la voz es real, producir el video es una
acción mecánica: tomar el texto y la duración real de cada escena y
pasárselos a un renderer. Dejar que el LLM escriba TSX distinto cada vez
sería frágil (el código podría no compilar, desalinear el tiempo de la
voz, romper convenciones del motor) para una ganancia nula, porque no hay
ninguna decisión creativa en ese paso.

Por eso `agents/render_agent.py` no llama al modelo: arma un `props.json`
con `{id, segundos (real), texto}` por escena y lo pasa a una composición
Remotion ya escrita y genérica, `AgenteReel` (en el repo público
`3d-animations-showcase`), que no sabe nada de este reel en particular —
solo sabe renderizar "una lista de escenas con texto y audio". La única
decisión que el agente Visual/3D sí toma (kit, idea visual por escena) es
documental en este avance: no cambia qué composición se usa.
