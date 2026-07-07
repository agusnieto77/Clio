# Log de Clio

Subcarpeta: `Fuentes\Actas`

[2026-07-07 17:06:49] INIT - subcarpeta=Actas - imagenes_pendientes=10 - imagenes_procesadas=0 - punto_reanudacion=ocr
[2026-07-07 17:07:05] REANUDACION - punto = ocr - motivo = hay 10 imagenes pendientes de OCR (subcarpeta Actas, agosto 1943)

## Modelos configurados

- Clio: principal = minimax/MiniMax-M3, respaldo = opencode/mimo-v2.5-free
- OCR historico: principal = minimax/MiniMax-M3, respaldo = opencode/mimo-v2.5-free
- Analista cuantitativo: principal = minimax/MiniMax-M3, respaldo = opencode/mimo-v2.5-free
- Redactor de informes: principal = minimax/MiniMax-M3, respaldo = opencode/mimo-v2.5-free
[2026-07-07 17:16:30] ETAPA OCR COMPLETADA - 10 imagenes procesadas - 0 errores - modelo=minimax/MiniMax-M3
[2026-07-07 17:49:34] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
[2026-07-07 17:51:08] ETAPA ANALISIS COMPLETADA - 10 documentos - 1385 terminos unicos - 0 excluidos - 7 archivos producidos
[2026-07-07 17:51:33] INFORME PRELIMINAR - 10 secciones -> informe_preliminar.html
[2026-07-07 17:54:02] ETAPA REDACCION COMPLETADA - 2 entregables producidos (informe_preliminar.html + informe_final.md)

## Cierre de subcarpeta

- Imagenes procesadas: 10/10
- Imagenes en error: 0
- Transcripciones producidas: 10 .txt + 10 .json (estructurado)
- Metricas producidas: 7 archivos (frecuencia, frecuencia_sin_stopwords, co_ocurrencia, correlacion, tfidf, resumen_top10.csv, versiones.json)
- Documentos analizados: 10
- Terminos unicos en el subcorpus: 1385
- Informes producidos: informe_preliminar.html (10 secciones, indice navegable, 3 columnas por imagen) + informe_final.md (6 secciones + nota de metodo + anexo)
- Validaciones: validar.py transcripciones ok=true; validar.py metricas ok=true; validar.py informes ok=true
- Modelos usados: ocr-historico = minimax/MiniMax-M3; analista/redactor = minimax/MiniMax-M3
- Punto de reanudacion: completo
- Entregables: Fuentes/Actas/informe_preliminar.html y Fuentes/Actas/informe_final.md
[2026-07-07 17:56:47] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
[2026-07-07 17:57:19] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
[2026-07-07 17:58:01] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
[2026-07-07 17:59:08] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
[2026-07-07 17:59:34] METRICAS - documentos=10 - terminos_unicos=1385 - excluidos=0 - archivos=7
