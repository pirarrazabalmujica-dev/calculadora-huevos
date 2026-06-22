# Primeros pasos — Guía de "primer día"

Checklist para quien toma el mantenimiento de **Monitor de Huevos**. Síguela en
orden. Al terminar vas a poder correr la app, pedirle cambios a Claude y
publicarlos. Tiempo estimado: ~1 hora.

> Detalle de accesos y por qué: ver `MANTENIMIENTO.md`.
> Contexto técnico del proyecto: ver `CLAUDE.md` (lo lee Claude solo).

---

## Parte A — Cuentas y programas (una sola vez)

- [ ] **1. Cuenta de GitHub.** Crea una en https://github.com si no tienes.
      Pídele al mantenedor anterior que te **transfiera el repo** o te agregue
      como **colaborador con permiso de escritura**.

- [ ] **2. Una IA que te ayude con el código.** Elige según tu presupuesto:

      **Opción A — Claude Code (de pago, lo más cómodo).** Edita y prueba los
      archivos solo. Necesita suscripción **Claude Pro/Max** (https://claude.ai) o
      cuenta de **API por uso** (https://console.anthropic.com). Instálalo desde
      https://claude.com/claude-code (app de escritorio, extensión de VS Code/
      JetBrains o CLI) e inicia sesión.

      **Opción B — GitHub Copilot Free (gratis, recomendado si no pagas).** Tiene
      plan gratuito, se integra en **VS Code**, lee los archivos y aplica cambios.
      Activa https://github.com/features/copilot e instala la extensión en VS Code.

      **Opción C — Chat gratis (claude.ai / ChatGPT / Gemini).** Sin costo, pero NO
      editan archivos: copias el código, preguntas, pegas la respuesta y la pruebas
      tú con `streamlit run app.py`. Para esta app (un solo archivo) funciona bien.

      💡 Con cualquier opción, pega primero el contenido de `CLAUDE.md` para que la
      IA tenga el contexto del proyecto.

- [ ] **3. (Solo opción A o B)** Instalar la herramienta elegida e iniciar sesión.

- [ ] **4. Instalar Git.** https://git-scm.com/download/win
      Durante la instalación deja las opciones por defecto.

- [ ] **5. Instalar Python 3.12 o 3.13** (NO 3.14). https://www.python.org/downloads/
      ⚠️ Marca la casilla **"Add Python to PATH"** en la primera pantalla.

---

## Parte B — Bajar el proyecto

- [ ] **6. Clonar el repositorio.** Abre una terminal (PowerShell) y corre:
      ```
      cd %USERPROFILE%\Desktop
      git clone https://github.com/pirarrazabalmujica-dev/calculadora-huevos.git
      ```
      (Si el repo ya se transfirió a otra cuenta/organización, usa esa URL nueva.)

- [ ] **7. Probar que la app corre.** En la carpeta del proyecto:
      ```
      cd calculadora-huevos
      python -m pip install -r requirements.txt
      python -m streamlit run app.py
      ```
      Debería abrirse la app en el navegador. Si funciona, ya estás listo.
      (La primera vez instalar las dependencias puede tardar varios minutos.)

---

## Parte C — Hablar con Claude y hacer un cambio de prueba

- [ ] **8. Abrir la IA en la carpeta del proyecto.** Con Claude Code o Copilot:
      abre la carpeta `calculadora-huevos` como proyecto (así la IA lee `CLAUDE.md`
      y entiende todo). Con un chat gratis (opción C): pega el contenido de
      `CLAUDE.md` al inicio de la conversación.

- [ ] **9. Pídele algo simple para probar.** Por ejemplo:
      > "Lee el CLAUDE.md y explícame en 5 líneas qué hace esta app y cómo la corro."

      La IA no recuerda conversaciones de otras personas, pero con el `CLAUDE.md`
      arranca sabiendo cómo funciona todo. Descríbele lo que quieres; Claude Code o
      Copilot pueden hacer y probar los cambios solos, con un chat gratis tendrás
      que pegar el código corregido y probarlo tú.

- [ ] **10. Publicar un cambio (cuando hagas uno real).** El flujo es:
      ```
      git add .
      git commit -m "descripción del cambio"
      git push
      ```
      La primera vez que hagas `push`, GitHub te pedirá iniciar sesión (se abre el
      navegador). Usa tu propia cuenta. Claude también puede hacer estos pasos por
      ti si se lo pides.

- [ ] **11. Subir la versión** (para que los PCs vean el aviso de actualización):
      editar `version.txt` y la línea `APP_VERSION` en `app.py` con el mismo número
      nuevo, y hacer commit + push. (Claude lo hace si se lo pides.)

---

## Parte D — Pendientes recomendados del traspaso

- [ ] **12. Tu propia API key de FRED** (datos de USA, gratis):
      sácala en https://fredaccount.stlouisfed.org/apikeys y reemplaza la línea
      `FRED_API_KEY = "..."` en `app.py`. (Opcional pero recomendado.)

- [ ] **13. Confirmar el traspaso del repo** está hecho (eres dueño o colaborador
      con escritura) y que tu `git push` funcionó al menos una vez.

---

### Si algo no funciona
- La app no abre / falta una librería → `python -m pip install -r requirements.txt`
- El OCR de producción no instala → revisa que sea **Python 3.12 o 3.13**, no 3.14.
- No puedo hacer `push` → revisa que tengas permiso de escritura en el repo y que
  hayas iniciado sesión en GitHub.
- Para cualquier duda del código, pregúntale a Claude dentro del proyecto: tiene
  el contexto en `CLAUDE.md`.
