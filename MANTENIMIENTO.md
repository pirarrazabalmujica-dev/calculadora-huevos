# Guía de mantenimiento — Monitor de Huevos

Documento para quien continúe el mantenimiento de la herramienta.
Está pensado para leerse "en frío", sin contexto previo.

---

## 1. Qué es y cómo funciona (resumen)

Aplicación local hecha en **Python + Streamlit**. No tiene servidor ni hosting:
corre en el PC de cada usuario con doble clic a `Monitor_Huevos.bat`, que copia
los archivos a una carpeta temporal, instala dependencias si faltan y abre la
app en el navegador (`http://localhost:8501`).

Tiene **dos módulos**:

- **Precios internacionales** — precio del huevo en Brasil, Argentina, Chile y
  USA. Cada país se obtiene "scrapeando" su fuente oficial.
- **Importaciones a Chile** — el usuario sube archivos de aduana; la app calcula
  N° de huevos importados y los grafica junto a la **producción nacional**
  (Chilehuevos).

### Archivos del proyecto

| Archivo | Qué es | ¿Se versiona en git? |
|---|---|---|
| `app.py` | Toda la lógica de la app (Streamlit + scrapers) | Sí |
| `importaciones.html` | Gráfico/herramienta del módulo 2 (se embebe en un iframe) | Sí |
| `Monitor_Huevos.bat` | Lanzador para Windows (copia archivos, instala deps, abre la app) | Sí |
| `requirements.txt` | Dependencias de Python | Sí |
| `produccion_historica.json` | Historia base de producción Chilehuevos (no cambia) | Sí |
| `version.txt` | Versión publicada (dispara el aviso "nueva versión") | Sí |
| `produccion_acumulada.json` | Historia de producción que crece sola en cada PC | No (gitignored) |
| `brasil_acumulado.json` | Historia de Brasil que crece sola en cada PC | No (gitignored) |
| `_prod_cl_cache.pkl` | Caché de 24 h de producción (cada PC) | No (gitignored) |

---

## 2. Accesos que necesita el nuevo mantenedor

### 🔴 CRÍTICO — Repositorio de GitHub
Hoy el repo está bajo una **cuenta personal**:
`https://github.com/pirarrazabalmujica-dev/calculadora-huevos`

Cuando el dueño de esa cuenta se va, nadie más puede publicar cambios. **Antes de
irte**, hacer UNA de estas dos cosas (la primera es la recomendada):

1. **Transferir el repositorio** a una cuenta/organización de la empresa
   (GitHub → Settings del repo → *Transfer ownership*). Así queda independiente
   de cualquier persona.
2. **Agregar al nuevo mantenedor como colaborador con permiso de escritura**
   (GitHub → Settings → Collaborators → Add people). Mínimo viable, pero el repo
   sigue colgando de una cuenta personal.

El nuevo mantenedor publica con **su propia cuenta de GitHub** (usuario + token
personal / *Personal Access Token*). No se comparten contraseñas.

### 🟡 API key de FRED (datos de USA)
En `app.py` hay una key hardcodeada (`FRED_API_KEY`). Es **gratis** y está atada
a una cuenta personal. Si se desactiva, USA pierde el historial largo de FRED
(igual sigue funcionando con el dato de USDA como respaldo). Recomendado: el
nuevo mantenedor saca su propia key gratis en
`https://fredaccount.stlouisfed.org/apikeys` y reemplaza la línea.

### 🟢 PCs de los usuarios
- **Python 3.12 o 3.13** instalado, marcando *"Add Python to PATH"*.
  ⚠️ **No usar Python 3.14**: el OCR (easyocr/torch) todavía no tiene soporte y
  puede no instalarse. Con 3.12/3.13 funciona todo.
- Conexión a internet (las fuentes se descargan en vivo).

### No se necesita
No hay servidor, base de datos, dominio ni nube. Nada de credenciales de hosting.

---

## 3. Cómo publicar un cambio

1. Editar los archivos (`app.py`, `importaciones.html`, etc.).
2. Probar localmente: `python -m streamlit run app.py`
3. Subir el cambio a GitHub:
   ```
   git add .
   git commit -m "descripción del cambio"
   git push
   ```
4. **Subir la versión** para que los PCs vean el aviso de "nueva versión":
   - Editar `version.txt` (ej. `2.0.0` → `2.1.0`).
   - Editar en `app.py` la línea `APP_VERSION = "2.0.0"` con el mismo número.
   - Commit + push.
5. En cada PC: volver a bajar los archivos del repo y reemplazar los locales
   (o re-descargar el ZIP del repo). El `.bat` se encarga del resto.

---

## 4. Qué puede fallar y cómo diagnosticarlo

Cada fuente puede romperse si el sitio oficial cambia URLs o formato. Todas
tienen respaldos, pero conviene saber dónde mirar. La función de cada fuente
está en `app.py`:

| Fuente | Función | Si falla, revisar… |
|---|---|---|
| 🇧🇷 Brasil | `_brasil_proconsp` | API de Procon-SP (`/wp-json/wp/v2/posts`) y los PDFs `CB-Anual-NN.pdf`. Si falta un mes reciente, suele ser que Procon-SP aún no subió el PDF. |
| 🇦🇷 Argentina | `scrape_argentina` | El `.xls` de INDEC (URL fija). Si cambian el orden de filas/columnas, ajustar el mapeo. |
| 🇨🇱 Chile | `scrape_chile` + `_odepa_urls` | API CKAN de ODEPA. Los años se descubren solos; si cambia el `ODEPA_DATASET`, actualizarlo. |
| 🇺🇸 USA | `scrape_usa` | FRED (`series_id` APU0000708111) + USDA AMS (`nw_py018.txt` / `ams_2848.pdf`). |
| 🥚 Producción CL | `scrape_produccion_cl` | Boletines Chilehuevos. Solo se baja el más reciente (OCR si es imagen); la historia sale de `produccion_historica.json`. |
| 💱 Tipo de cambio | `get_fx` | mindicador.cl, awesomeapi (BRL), dolarapi/BCRA (ARS). Tiene valores por defecto si todo falla. |

**Principio de diseño (importante):** la historia pasada **no se vuelve a
descargar**. Producción y Brasil guardan su historia en archivos JSON que crecen
solos. Si una fuente se cae, la app sigue mostrando lo ya guardado.

### Refrescar la base histórica de producción
`produccion_historica.json` es el "piso" de la producción nacional (2019→2025).
Normalmente no hay que tocarlo (cada PC acumula los meses nuevos solo en
`produccion_acumulada.json`). Si algún día se quiere "consolidar" meses nuevos en
la base versionada, copiar los valores nuevos al JSON y hacer commit.

---

## 5. Dependencias

Ver `requirements.txt`. Las pesadas son `easyocr` + `pymupdf` (OCR de los
boletines de producción 2026+, que vienen como imagen). El `.bat` las instala
solas la primera vez. Si el OCR no se puede instalar (ej. Python 3.14), la app
igual funciona pero sin la previsión de producción del año en curso.

---

## 6. Checklist de traspaso (antes de irte)

- [ ] Transferir el repo a una cuenta de la empresa **o** agregar al nuevo
      mantenedor como colaborador con permiso de escritura.
- [ ] Que el nuevo mantenedor saque su propia API key de FRED y la reemplace.
- [ ] Confirmar que el nuevo mantenedor puede hacer `git push` con su cuenta.
- [ ] Entregar este documento y hacer una pasada juntos por los dos módulos.
- [ ] Verificar que los PCs de los usuarios tengan Python 3.12/3.13.
