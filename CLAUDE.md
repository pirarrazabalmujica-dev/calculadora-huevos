# CLAUDE.md — Contexto del proyecto para Claude Code

Claude Code lee este archivo automáticamente al abrir el proyecto. Le da el
contexto para hacer cambios sin tener que explorar todo desde cero.

## Qué es

App local en **Python + Streamlit**. No tiene servidor ni nube: corre en el PC de
cada usuario con doble clic a `Monitor_Huevos.bat` (copia los archivos a
`%TEMP%\MHuevos`, instala dependencias si faltan, abre `http://localhost:8501`).

Dos módulos:
- **Precios internacionales** del huevo: Brasil, Argentina, Chile, USA.
- **Importaciones a Chile** + **producción nacional** (Chilehuevos).

## Cómo correr / probar

```
python -m streamlit run app.py
```
Usar **Python 3.12 o 3.13** (NO 3.14: el OCR `easyocr`/`torch` no instala en 3.14).

## Estructura

- `app.py` — toda la lógica (Streamlit + scrapers). Es un solo archivo.
- `importaciones.html` — gráfico del módulo 2 (se embebe en un iframe).
  Tiene caracteres acentuados UTF-8: editarlo leyendo en binario, `decode('utf-8')`,
  normalizar `\r\n`→`\n`, reemplazar, y escribir con `encoding='utf-8', newline='\n'`.
- `produccion_historica.json` — base histórica de producción (versionada).
- `requirements.txt`, `Monitor_Huevos.bat`, `version.txt`.
- `MANTENIMIENTO.md` — guía de traspaso (accesos, cómo publicar, etc.).

## Flujo de trabajo

- La app que corre el usuario vive en `%TEMP%\MHuevos` (el `.bat` copia ahí). El
  **repo es la fuente**. Hacer cambios: editar → probar → copiar al repo → commit → push.
- Publicar un update: subir `version.txt` y la línea `APP_VERSION` en `app.py`
  (mismo número), commit + push. Eso dispara el aviso de "nueva versión" en los PCs.

## Fuentes de datos (cada una puede romperse si el sitio oficial cambia)

| Fuente | Función en `app.py` |
|---|---|
| 🇧🇷 Brasil | `_brasil_proconsp` — API WP de Procon-SP + PDFs anuales/mensuales |
| 🇦🇷 Argentina | `scrape_argentina` — `.xls` de INDEC |
| 🇨🇱 Chile | `scrape_chile` + `_odepa_urls` — API CKAN de ODEPA (años dinámicos) |
| 🇺🇸 USA | `scrape_usa` — FRED (API key) + USDA AMS |
| 🥚 Producción CL | `scrape_produccion_cl` — boletines Chilehuevos |
| 💱 Tipo de cambio | `get_fx` — en vivo (mindicador / awesomeapi / dolarapi-BCRA), con respaldo |

## Principios de diseño (MANTENERLOS)

- **La historia pasada no se re-descarga.** Producción y Brasil guardan la
  historia en JSON que crece solo por PC (`produccion_acumulada.json`,
  `brasil_acumulado.json`, gitignored) más una base versionada. Si una fuente se
  cae, la app sigue mostrando lo guardado.
- **Soluciones sostenibles, no parches.** Descubrir años/URLs dinámicamente en
  vez de hardcodear; que la solución sobreviva al paso del tiempo.
- **OCR de producción.** Los boletines 2026+ son imágenes. La tabla autoritativa
  es **"ESTIMACIÓN DE PRODUCCIÓN (miles de unidades)"** — grilla mes×año, valores
  en miles (×1000). La tabla "por ciclo" (etiquetas `mes-yy`) es frágil (sus filas
  se desalinean en el OCR) y la columna correcta es la última (**Total**), no la
  primera (Primer ciclo).
- **Verificar antes de decir que algo está hecho.** Correr/probar el cambio con
  datos reales; no asumir que funciona.

## Notas

- `FRED_API_KEY` está hardcodeada en `app.py` (gratis, cuenta personal) — ver
  `MANTENIMIENTO.md` para reemplazarla.
- El tipo de cambio NO es fijo: `get_fx` lo baja en vivo (caché 1 h). Los números
  hardcodeados en `get_fx` son solo respaldo por si las APIs no responden.
