# Primeros pasos — Guía de "primer día"

Checklist para quien toma el mantenimiento de **Monitor de Huevos**. Usaremos
**GitHub Copilot dentro de VS Code** (tiene plan gratuito). Sigue los pasos en
orden. Al terminar vas a poder correr la app, pedirle cambios a Copilot y
publicarlos. Tiempo estimado: ~1 hora.

> Detalle de accesos y por qué: ver `MANTENIMIENTO.md`.
> Contexto técnico del proyecto: ver `CLAUDE.md` (lo lee la IA solo).

---

## Parte A — Cuentas y programas (una sola vez)

- [ ] **1. Cuenta de GitHub.** Crea una en https://github.com si no tienes.
      Pídele al mantenedor anterior que te **transfiera el repo** o te agregue
      como **colaborador con permiso de escritura**.

- [ ] **2. Instalar VS Code** (gratis): https://code.visualstudio.com

- [ ] **3. Instalar GitHub Copilot.** En VS Code abre **Extensiones**
      (`Ctrl+Shift+X`) e instala:
      - **GitHub Copilot**
      - **GitHub Copilot Chat**

- [ ] **4. Iniciar sesión con GitHub** dentro de VS Code (icono de la persona,
      abajo a la izquierda → "Sign in with GitHub"). Al entrar, **Copilot Free se
      activa solo** — no pide tarjeta. (Tiene un límite mensual de uso; para
      mantención ocasional alcanza bien.)

- [ ] **5. Instalar Git.** https://git-scm.com/download/win (opciones por defecto).

- [ ] **6. Instalar Python 3.12 o 3.13** (NO 3.14). https://www.python.org/downloads/
      ⚠️ Marca la casilla **"Add Python to PATH"** en la primera pantalla.

---

## Parte B — Bajar el proyecto

- [ ] **7. Clonar el repositorio.** Abre PowerShell y corre:
      ```
      cd %USERPROFILE%\Desktop
      git clone https://github.com/pirarrazabalmujica-dev/calculadora-huevos.git
      ```
      (Si el repo ya se transfirió a otra cuenta/organización, usa esa URL nueva.)

- [ ] **8. Probar que la app corre.** En la carpeta del proyecto:
      ```
      cd calculadora-huevos
      python -m pip install -r requirements.txt
      python -m streamlit run app.py
      ```
      Debería abrirse la app en el navegador. (La primera vez puede tardar varios
      minutos instalando dependencias.)

---

## Parte C — Usar Copilot y hacer un cambio de prueba

- [ ] **9. Abrir la carpeta del proyecto en VS Code.** ⚠️ Paso clave donde más se
      traba la gente: **File → Open Folder…** → elige la carpeta `calculadora-huevos`
      → "Seleccionar carpeta". Si NO abres la carpeta, Copilot no ve los archivos y
      "no funciona". Cuando esté bien, a la izquierda (panel EXPLORER) verás la lista
      de archivos: `app.py`, `CLAUDE.md`, etc.

- [ ] **10. Abrir el chat de Copilot** (icono de chat arriba a la derecha, o
      `Ctrl+Alt+I`). En la fila de abajo del cuadro de chat, deja el modo en
      **"Agent"** (es el que edita los archivos solo). Copilot lee el `CLAUDE.md`
      automáticamente y queda con el contexto del proyecto.

- [ ] **11. Pídele algo simple para probar.** En el cuadro de chat escribe:
      > "Lee el CLAUDE.md y explícame en 5 líneas qué hace esta app y cómo la corro."

      Para un arreglo real, descríbele el problema (ej. "el gráfico de Brasil dejó de
      mostrar datos, revísalo y arréglalo"). Copilot edita los archivos, verifica
      solo que no haya errores, y tú revisas.

- [ ] **12. Publicar el cambio a GitHub.** Cuando ya probaste que funciona:
      - Pídeselo a Copilot: *"haz commit y push de este cambio"*, **o**
      - Hazlo a mano: panel **Source Control** (`Ctrl+Shift+G`) → escribe un
        mensaje → **Commit** → **Sync/Push**.

      La primera vez que subas, GitHub te pedirá iniciar sesión (se abre el
      navegador). Usa tu propia cuenta.

- [ ] **13. Subir la versión** (para que los PCs vean el aviso de actualización):
      editar `version.txt` y la línea `APP_VERSION` en `app.py` con el mismo número
      nuevo, y hacer commit + push. (Copilot lo hace si se lo pides.)

---

## Parte D — Pendientes recomendados del traspaso

- [ ] **14. Tu propia API key de FRED** (datos de USA, gratis):
      sácala en https://fredaccount.stlouisfed.org/apikeys y reemplaza la línea
      `FRED_API_KEY = "..."` en `app.py`. (Opcional pero recomendado.)

- [ ] **15. Confirmar el traspaso del repo** (eres dueño o colaborador con
      escritura) y que tu `git push` funcionó al menos una vez.

---

### Si algo no funciona
- Copilot "no hace nada" / no ve el código → revisa que hayas **abierto la carpeta**
  del proyecto (paso 9), no solo VS Code.
- La app no abre / falta una librería → `python -m pip install -r requirements.txt`
- El OCR de producción no instala → revisa que sea **Python 3.12 o 3.13**, no 3.14.
- No puedes hacer `push` → revisa que tengas permiso de escritura en el repo y que
  hayas iniciado sesión en GitHub.
- Para cualquier duda del código, pregúntale a Copilot dentro del proyecto: tiene
  el contexto en `CLAUDE.md`.
