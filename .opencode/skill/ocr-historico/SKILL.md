---
name: ocr-historico
description: "Skill protocolaria del subagente OCR historico del harness Clio. Detalla el protocolo de pasos exactos para transcribir UNA imagen a la vez de una subcarpeta, mantener checklist.json, mover imagenes procesadas a i_procesadas/ tras verificar el guardado, y manejar errores sin mover imagenes fallidas. Trigger: cuando Clio delega la etapa OCR de una subcarpeta."
---

# Skill: OCR historico

Protocolo **estricto y secuencial** para transcribir una subcarpeta de fotografias de documentacion mecanografiada y prensa del siglo XX.

## Convenciones

- `<ruta>` = ruta relativa de la subcarpeta (por ejemplo `Fuentes/Anteproyecto-CCT-SOIP`).
- `<base>` = nombre base de una imagen sin extension (por ejemplo `DSC01940`).

## Desafios del material (a contemplar activamente)

Las fotografias son caseras y el material es del siglo XX. Espera encontrar:

- **Iluminacion irregular** (sombras, brillos, viñetas).
- **Inclinacion** de la pagina.
- **Tinta desigual** (manchas, desvanecimiento, contrastes variables).
- **Tipografia mecanografica** (espaciado irregular, caracteres rotos) y **tipografia de prensa** (tipos variables, columnas estrechas).
- **Ortografia de epoca**: preservala sin normalizar en la transcripcion primaria. Si dice "govierno", "naçion", " America" o usa tildes distintas, lo dejás tal cual.
- **Sellos, membretes, firmas, anotaciones manuscritas**: transcribilos marcando claramente su tipo.
- **Notas al margen y correcciones**: preservadas como parte del texto.

## Protocolo por subcarpeta

### Paso 0 — Inicializar checklist

Ejecutar:

```
python harness/tools/checklist.py "<ruta>" init
```

Esto crea o actualiza `<ruta>/checklist.json` con todas las imagenes `.jpg`/`.jpeg` sueltas en `<ruta>/` que NO esten en `i_procesadas/`. Cada entrada queda en estado `pendiente`. Las imagenes ya en `i_procesadas/` quedan fuera.

### Paso 1 — Seleccionar la siguiente imagen pendiente

Ejecutar:

```
python harness/tools/checklist.py "<ruta>" siguiente
```

Devuelve JSON con el campo `siguiente`: nombre de archivo de la siguiente imagen `pendiente`, o `null` si no quedan.

- Si `siguiente` es `null`: ir al Paso 8 (Cierre de etapa).
- Si devuelve un nombre: continuar al Paso 2 con esa imagen.

### Paso 2 — Leer la imagen y detectar layout

Con la tool `read`, abrir la imagen `<ruta>/<imagen>`. NO uses scripts para esto: tu capacidad de vision como modelo declarado para OCR en `harness/modelos.json` es la herramienta.

Antes de transcribir, **detecta el layout de la pagina**:

- Orientacion (vertical / horizontal).
- Numero de columnas y su disposicion.
- Zonas identificables: membrete, titulo, cuerpo, firmas, sellos, anotaciones, numeracion.
- Tipo de documento (carta, recorte de prensa, acta, memo, factura, contrato, etc.).

### Paso 3 — Transcribir preservando estructura

Transcribi el texto completo preservando la estructura. Usá marcas semanticas explicitas para reflejar el layout detectado:

```
[MEMBRETE]
<texto del membrete>

[TITULO]
<titulo>

[CUERPO]
<texto del cuerpo, respetando saltos de parrafo>

[COLUMNAS: 2]
[COLUMNA 1]
<texto columna 1>
[COLUMNA 2]
<texto columna 2>

[FIRMA]
<firma o rúbrica>

[SELLO]
<texto legible del sello, o "sello ilegible">

[ANOTACION_MANUSCRITA]
<texto manuscrito>

[NOTA AL MARGEN]
<texto>
```

Reglas de transcripcion:

- **NO normalices** ortografia, puntuacion ni mayusculas. Copia literal.
- **NO interpretes** ni resumas. Texto completo, palabra por palabra.
- Si una palabra es ilegible, escribi `[ILEGIBLE]`. Si una zona es ilegible, `[ZONA ILEGIBLE]`.
- Si hay tachaduras, transcribi el texto tachado entre `[TACHADO]` y `[/TACHADO]`.
- Si hay inserciones manuscritas sobre texto mecanografiado, separalas con marcas `[MANUSCRITO]...[/MANUSCRITO]`.
- Conserva los saltos de linea y parrafo significativos.

### Paso 4 — Guardar la transcripcion

Guarda la transcripcion en `<ruta>/<base>.txt` (texto plano con las marcas semanticas) Y opcionalmente `<ruta>/<base>.json` con la estructura:

```json
{
  "imagen": "<archivo>",
  "base": "<base>",
  "tipo_documento_detectado": "<carta|recorte_prensa|acta|...>",
  "layout": {
    "orientacion": "<vertical|horizontal>",
    "columnas": <int>,
    "zonas": ["membrete", "titulo", "cuerpo", ...]
  },
  "transcripcion": "<texto completo con marcas semanticas>",
  "notas_ocr": "<observaciones sobre dificultades de lectura: manchas, tinta desigual, inclinacion, etc.>",
  "modelo_utilizado": "<modelo OCR vigente>"
}
```

Como minimo, el `.txt` es obligatorio. El `.json` es el formato preferido cuando el layout lo amerita.

### Paso 5 — Verificar guardado y mover la imagen

Despues de escribir el archivo:

1. Verifica con la tool read que el `.txt` (o `.json`) existe y tiene contenido no vacio y no placeholder.
2. Si la verificacion pasa, ejecuta:
   ```
   python harness/tools/mover_imagen.py "<ruta>" "<imagen>"
   ```
   Esto mueve `<ruta>/<imagen>` a `<ruta>/i_procesadas/<imagen>`. Crea `i_procesadas/` si no existe.
3. Ejecuta:
   ```
   python harness/tools/checklist.py "<ruta>" marcar "<imagen>" procesada
   ```

Si la verificacion FALLA (archivo vacio, no se guardo, contenido es `[ILEGIBLE]` en toda la imagen, etc.) **NO muevas la imagen**. Vas al Paso 6.

### Paso 6 — Manejo de errores (sin mover la imagen)

Si la transcripcion fallo (texto vacio, ilegible total, el modelo no pudo procesar la imagen):

1. Asegurate de borrar cualquier archivo `.txt`/`.json` parcial que haya quedado.
2. Ejecuta:
   ```
   python harness/tools/checklist.py "<ruta>" marcar "<imagen>" error "<detalle>"
   ```
3. La imagen queda en su lugar original (no se mueve a `i_procesadas/`).
4. Reportas a Clio: "Imagen `<imagen>` no pudo ser transcrita. Motivo: <detalle>. Estado en checklist: error."

### Paso 7 — Repetir

Volve al Paso 1 hasta que el campo `siguiente` devuelva `null`.

### Paso 8 — Cierre de etapa

Reporta a Clio:
- Total de imagenes procesadas.
- Total de imagenes en estado error.
- Lista de imagenes en error con motivo.
- Modelo utilizado.

NO avances a la etapa de analisis vos misma. Eso lo decide Clio.

## Que NO haces

- No proceses dos o mas imagenes en una misma respuesta. Una por respuesta.
- No reescribis una transcripcion existente para una imagen ya en `i_procesadas/` sin confirmacion de Clio.
- No inventes texto. `[ILEGIBLE]` es preferible a una palabra adivinada.
- No normalices ortografia ni limpies el texto. Eso lo decide el investigador en una capa posterior.
- No interpretes el contenido. Tu rol es transcribir, no analizar.
- No uses la tool `edit` sobre las imagenes ni las rotes. Transcribis lo que ves.
