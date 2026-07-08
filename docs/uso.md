# Uso

## 1. Preparar un subcorpus

Crear una subcarpeta dentro de `Fuentes/` y copiar ahí las imágenes `.jpg` o `.jpeg` sueltas.

Ejemplo:

```text
Fuentes/
└── MiSubcorpus/
    ├── img_001.jpg
    ├── img_002.jpg
    └── img_003.jpg
```

## 2. Correr el flujo completo

Desde una sesión OpenCode abierta en este repo (recordá: OpenCode es el runtime nativo del harness):

```text
/clio Fuentes/MiSubcorpus
```

Si antes querés revisar o cambiar los modelos, corré:

```bash
python harness/tools/configurar_modelos.py
```

## 3. Qué produce

```text
Fuentes/MiSubcorpus/
├── i_procesadas/
├── *.txt
├── *.json
├── checklist.json
├── metricas/
├── informe_preliminar.html
├── informe_final.md
└── log_clio.md
```

## 4. Reanudar una corrida interrumpida

El estado vive en el filesystem. Basta volver a invocar Clio sobre la misma subcarpeta; `estado.py` reconstruye el punto de reanudación.

## 5. Fallback — herramientas manuales

Solo para debug o cuando no podés abrir OpenCode. Sin OpenCode perdés la orquestación unificada y el comando `/clio`: tenés que invocar los scripts uno a uno en el orden correcto.

```bash
python harness/tools/estado.py Fuentes/MiSubcorpus init
python harness/tools/checklist.py Fuentes/MiSubcorpus mostrar
python harness/tools/validar.py transcripciones Fuentes/MiSubcorpus
python harness/tools/metricas.py Fuentes/MiSubcorpus
python harness/tools/validar.py metricas Fuentes/MiSubcorpus
python harness/tools/informe_preliminar.py Fuentes/MiSubcorpus
python harness/tools/validar.py informes Fuentes/MiSubcorpus
python harness/tools/estado.py Fuentes/MiSubcorpus resumen
```
