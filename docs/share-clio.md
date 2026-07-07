# Textos de presentación para compartir Clio

Clio ya está listo para compartirse. Este archivo reúne versiones cortas y largas para distintos canales.

## Uso rápido

Elegí el texto según el canal:

- **WhatsApp / mensaje breve** → versión corta
- **Mail a colegas** → versión media
- **Post de difusión / web / newsletter** → versión larga

## Versión corta

Comparto **Clio**, un harness agéntico y determinista para trabajar con corpus documentales fotografiados. Hace OCR histórico, calcula métricas de minería de texto y genera reportes por subcarpeta. Incluye un corpus de ejemplo y la estructura completa de entrada/salida. Repo: <https://github.com/agusnieto77/Clio>

## Versión media

Quería compartir **Clio**, un repositorio público pensado para investigar corpus documentales fotografiados de forma reproducible. El flujo combina cuatro roles (orquestación, OCR histórico, análisis cuantitativo y redacción de informes), preserva el estado en el filesystem y valida cada etapa antes de avanzar. El repo incluye un subcorpus de ejemplo ya procesado (`Fuentes/Actas/`) para que se vea de punta a punta cómo entra el material y qué sale.  

Repo: <https://github.com/agusnieto77/Clio>

## Versión larga

Comparto **Clio**, un harness agéntico y determinista para el procesamiento de corpus documentales fotografiados. Está pensado para investigadores que trabajan con actas, recortes, documentación mecanografiada u otros materiales de archivo en imagen y quieren un flujo reproducible desde la transcripción hasta el informe final.

Clio organiza el trabajo en cuatro roles: una orquestadora que valida y reanuda, un OCR histórico que procesa una imagen a la vez preservando layout y ortografía de época, un analista cuantitativo que calcula frecuencia, co-ocurrencia, correlación y TF-IDF, y un redactor que genera un HTML preliminar por imagen y un informe final por subcorpus. El principio rector es el determinismo: todo el estado vive en el filesystem, cada etapa se valida antes de avanzar y el repositorio incluye una suite de regresión para asegurar que el comportamiento se mantenga estable.

El repo ya trae un ejemplo completo (`Fuentes/Actas/`) con imágenes procesadas, transcripciones, métricas, informes y log, de modo que cualquier investigador pueda ver la estructura completa de entrada y salida antes de probarlo con su propio material.

Repo: <https://github.com/agusnieto77/Clio>

## Puntos que conviene remarcar al compartirlo

- trabaja por **subcarpeta = subcorpus**
- preserva la **ortografía de época** en la transcripción primaria
- separa claramente **entrada, estado y entregables**
- trae un **ejemplo completo** para aprender la estructura
- usa un enfoque **reproducible y validado**, no una caja negra

## Qué NO prometer

- No venderlo como OCR mágico universal.
- No decir que reemplaza revisión humana.
- No prometer exactitud perfecta sobre imágenes muy dañadas.
- No presentarlo como producto cerrado si el objetivo es invitar a uso y mejora.
