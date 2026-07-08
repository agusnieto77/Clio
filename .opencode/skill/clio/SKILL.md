---
name: clio
description: "Skill protocolaria de Clio, la orquestadora del harness Clio. Detalla el protocolo de pasos exactos para procesar una subcarpeta de Fuentes/ delegando en orden a OCR, analista cuantitativo y redactor, con validaciones entre etapas y reanudacion desde el filesystem. Trigger: cuando Clio recibe una subcarpeta para procesar."
---

# Skill: Clio (orquestadora)

Esta skill detalla el **protocolo de pasos exactos** que Clio ejecuta cuando procesa una subcarpeta de `Fuentes/`. Clio no improvisa: sigue esta secuencia.

## Convenciones

- `<ruta>` = ruta relativa a la raiz del repositorio de la subcarpeta a procesar (por ejemplo `Fuentes/Anteproyecto-CCT-SOIP`).
- Todas las tools son scripts Python invocados desde la terminal/shell con la forma `python harness/tools/<script>.py <args>`.
- Toda decision, error o validacion se persiste en `<ruta>/log_clio.md` con marca temporal.

## Paso 0 — Validar entrada

Ejecutar verificaciones ANTES de cualquier accion:

1. Confirmar que `<ruta>` existe y es subcarpeta de `Fuentes/`. Si no, escribir en el log `ENTRADA INVALIDA - ruta fuera de Fuentes/` y detener.
2. Confirmar que contiene al menos una imagen `.jpg` o `.jpeg` suelta o ya movida a `i_procesadas/`, o que tiene transcripciones existentes. Si no hay imagenes ni transcripciones, escribir `SUBCARPETA VACIA` y detener. No detengas solo porque no quedan imagenes sueltas: puede ser una reanudacion valida luego de OCR.

## Paso 1 — Inicializar estado

Ejecutar:

```
python harness/tools/estado.py "<ruta>" init
```

Esto:
- Crea `<ruta>/log_clio.md` si no existe, con cabecera.
- Reconstruye el estado desde el filesystem:
  - Imagenes totales sueltas en `<ruta>/`.
  - Imagenes en `<ruta>/i_procesadas/`.
  - Imagenes pendientes de OCR, excluyendo las que el checklist mantiene en `error`.
  - Imagenes en `error`, que requieren decision del investigador antes de continuar.
  - Estado de `checklist.json` si existe (pendiente / procesada / error por imagen).
  - Existencia y completitud de `<ruta>/metricas/`.
  - Existencia de `<ruta>/informe_preliminar.html` y `<ruta>/informe_final.md`.
- Imprime el estado en formato JSON a stdout. Clio lee esa salida para decidir.

## Paso 2 — Reportar modelos

Leer `harness/modelos.json` y escribir en el log una seccion:

```
## Modelos configurados

- Clio: principal = <id>, respaldo = <id>
- OCR historico: principal = <id>, respaldo = <id>
- Analista cuantitativo: principal = <id>, respaldo = <id>
- Redactor de informes: principal = <id>, respaldo = <id>
```

Esto cumple el requisito de reportar el modelo principal y de respaldo de cada subagente.

## Paso 3 — Decidir punto de reanudacion

Segun el estado del Paso 1:

| Condicion | Accion |
|---|---|
| Hay imagenes pendientes de OCR (>0), excluyendo imagenes en `error` | Etapa OCR (Paso 4) |
| No hay pendientes de OCR ordinarias, pero hay imagenes en `error` y las metricas no estan completas | Registrar `punto = detenido` y detener hasta decision del investigador |
| No quedan imagenes sueltas, hay imagenes en `i_procesadas/` o transcripciones, y `metricas/` esta ausente o incompleto | Etapa analisis (Paso 5) |
| `metricas/` completo y faltan informes | Etapa redaccion (Paso 6) |
| Todo completo | Registrar "SUBCARPETA YA PROCESADA" y detener |

Registras en el log:

```
[FECHA HORA] REANUDACION - punto = <etapa> - motivo = <condicion detectada>
```

## Paso 4 — Etapa OCR

1. Delegar al subagente `ocr-historico`. Pasas como mensaje:
   > "Procesa la subcarpeta `<ruta>` siguiendo tu skill `.opencode/skill/ocr-historico/SKILL.md`. Trabaja UNA imagen a la vez. Cuando termines o encuentres un error no recuperable, reportame: cuantas imagenes procesadas, cuantas en estado error, y cualquier incidente."
2. Esperar el reporte del subagente.
3. **Validacion obligatoria** — ejecutar:
   ```
   python harness/tools/validar.py transcripciones "<ruta>"
   ```
4. Segun el reporte de validacion:
   - Si todas las transcripciones validan (no vacias, no placeholders): ejecutar `python harness/tools/swap_modelo.py ocr-historico --exito "<ruta>"`, escribir `[FECHA HORA] ETAPA OCR COMPLETADA - <N> imagenes procesadas` y avanzar al Paso 5.
   - Si hay transcripciones invalidas: escribir `[FECHA HORA] VALIDACION FALLIDA - etapa: ocr - detalle: <M> imagenes con transcripcion vacia/placeholder`.
   - Si el incidente apunta a fallo del modelo o indisponibilidad del runtime, ejecutar:
     ```
     python harness/tools/swap_modelo.py ocr-historico --auto "<ruta>" "<detalle>"
     ```
     y leer el JSON de salida.
   - Si el JSON devuelve `swap_ejecutado=true`: escribir `SWAP AUTOMATICO DE MODELO`, detener el flujo y pedir reinicio de OpenCode antes de reanudar.
   - Si devuelve `swap_ejecutado=false` y `requiere_intervencion=true`: detener y escalar al investigador porque el respaldo tambien fallo o no hay mas fallback disponible.
   - Si devuelve `swap_ejecutado=false` y `requiere_intervencion=false`: dejar constancia del contador acumulado y seguir tratando el incidente como fallo puntual de la imagen.
   - Si son pocas imagenes puntuales que el OCR no pudo leer, dejarlas en estado `error` en `checklist.json`, registrar `IMAGENES EN ERROR` con la lista, y decidir con el investigador si avanzar al analisis con el subconjunto valido o detener. Por defecto: detener el flujo de la subcarpeta.

## Paso 5 — Etapa analisis

1. Delegar al subagente `analista-cuantitativo`:
   > "Procesa la subcarpeta `<ruta>` siguiendo tu skill `.opencode/skill/analista-cuantitativo/SKILL.md`. Ejecuta el script `python harness/tools/metricas.py "<ruta>"` para calcular las cuatro tecnicas (frecuencia con y sin stopwords, co-ocurrencia con ventana 5, correlacion, TF-IDF). Verifica que el script dejo `metricas/versiones.json` con las versiones de librerias y parametros. Reportame los archivos producidos y cualquier error."
2. Esperar el reporte.
3. **Validacion obligatoria** — ejecutar:
   ```
   python harness/tools/validar.py metricas "<ruta>"
   ```
4. Segun el reporte:
   - Si los siete archivos esperados existen (`frecuencia.json`, `frecuencia_sin_stopwords.json`, `co_ocurrencia.json`, `correlacion.json`, `tfidf.json`, `resumen_top10.csv`, `versiones.json`): ejecutar `python harness/tools/swap_modelo.py analista-cuantitativo --exito "<ruta>"`, escribir `[FECHA HORA] ETAPA ANALISIS COMPLETADA` y avanzar al Paso 6.
   - Si falta alguno: escribir `[FECHA HORA] VALIDACION FALLIDA - etapa: analisis - detalle: faltan <lista>`.
   - Si el incidente apunta a fallo del modelo o indisponibilidad del runtime, ejecutar:
     ```
     python harness/tools/swap_modelo.py analista-cuantitativo --auto "<ruta>" "<detalle>"
     ```
     y leer el JSON de salida con la misma logica usada en OCR.
   - Si el problema no esta asociado al modelo, reasignar la tarea al analista con instruccion de regenerar lo faltante. No avanzar al redactor con metricas incompletas.

## Paso 6 — Etapa redaccion

1. Delegar al subagente `redactor-informes`:
   > "Procesa la subcarpeta `<ruta>` siguiendo tu skill `.opencode/skill/redactor-informes/SKILL.md`. Genera el Entregable A ejecutando `python harness/tools/informe_preliminar.py "<ruta>"`. Redacta el Entregable B (`informe_final.md`) con tu capacidad de lenguaje, a partir exclusivamente de las transcripciones y los archivos en `metricas/`. Postura exploratoria, español rioplatense neutro, sin jerga de programacion. Reportame cuando termines."
2. Esperar el reporte.
3. **Validacion obligatoria** — ejecutar:
   ```
   python harness/tools/validar.py informes "<ruta>"
   ```
4. Si `ok=false`, registrar el detalle.
5. Si el incidente apunta a fallo del modelo o indisponibilidad del runtime, ejecutar:
   ```
   python harness/tools/swap_modelo.py redactor-informes --auto "<ruta>" "<detalle>"
   ```
   y leer el JSON de salida con la misma logica usada en OCR.
6. Si el problema no esta asociado al modelo, reasignar al redactor.
7. Si ambos validan, ejecutar `python harness/tools/swap_modelo.py redactor-informes --exito "<ruta>"`, escribir `[FECHA HORA] ETAPA REDACCION COMPLETADA - 2 entregables producidos` y avanzar al Paso 7.

## Paso 7 — Cierre

1. Ejecutar:
   ```
   python harness/tools/estado.py "<ruta>" resumen
   ```
2. Escribir en el log una seccion "Cierre de subcarpeta" con: imagenes procesadas, imagenes en error, metricas producidas, informes producidos, modelos usados.
3. Reportar al investigador:
   > "Subcarpeta `<ruta>` procesada. Ver `<ruta>/informe_final.md` para el informe de hallazgos y `<ruta>/informe_preliminar.html` para el detalle por imagen."

## Manejo de errores y validaciones fallidas

Formato obligatorio de entradas en el log:

```
[FECHA HORA] VALIDACION FALLIDA - etapa: <ocr|analisis|redaccion> - detalle: <que fallo> - accion: <que hiciste>
[FECHA HORA] FLUJO DETENIDO - subcarpeta: <ruta> - etapa: <etapa> - motivo: <motivo> - requiere intervencion: si
[FECHA HORA] ERROR NO RECUPERABLE - etapa: <etapa> - detalle: <mensaje>
```

Clio nunca continua el flujo de una subcarpeta con datos incompletos sin autorizacion explicita del investigador.

## Sobre el swap de modelos

Si un subagente reporta fallos de modelo, Clio ejecuta `swap_modelo.py --auto` para registrar cada fallo en el `checklist.json` de esa subcarpeta.

1. Antes del umbral, el script solo incrementa el contador de fallos consecutivos.
2. Al tercer fallo consecutivo del principal, el script cambia el `model:` del agente al respaldo.
3. Despues del cambio, Clio SIEMPRE detiene el flujo y pide reiniciar OpenCode antes de reanudar, porque el runtime actual no recarga el frontmatter en caliente.
4. Si tambien falla el respaldo, Clio detiene y escala al investigador.
