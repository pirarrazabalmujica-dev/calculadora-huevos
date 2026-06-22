# Instrucciones para el agente — Monitor de Huevos

App **Python + Streamlit**. Lee `CLAUDE.md` en la raíz para el contexto completo
(qué hace, fuentes de datos, principios de diseño).

## Flujo al hacer cambios de código

1. Edita los archivos necesarios.
2. **Verifica automáticamente, sin pedir confirmación:** ejecuta
   `python -m py_compile app.py`. Si da error, corrígelo antes de continuar.
   (Confirma que el código no tiene errores que impidan arrancar la app.)
3. Resume al usuario qué cambiaste y el resultado de la verificación.
4. **NUNCA ejecutes `git commit` ni `git push` sin que el usuario lo confirme
   explícitamente.** Subir a GitHub afecta a todos los que bajan la app.

## Notas

- Python 3.12 o 3.13 (NO 3.14: el OCR `easyocr`/`torch` no instala en 3.14).
- La prueba visual completa (`python -m streamlit run app.py`, mirar el navegador)
  la hace una persona. El `py_compile` es el chequeo automático mínimo.
- No reintroducir "parches" momentáneos: mantener los principios de `CLAUDE.md`
  (historia persistente, descubrimiento dinámico de URLs/años, etc.).
