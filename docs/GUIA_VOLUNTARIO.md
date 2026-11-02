# Guía del voluntario — pruebas de Mirada (15–20 min)

Gracias por ayudar. Vas a probar un tablero que se controla con la mirada
y una webcam común. No necesitas cuenta ni key de nada.

## Requisitos

- Windows 10/11 con webcam (integrada o USB).
- Python 3.11 o 3.12 instalado desde python.org (marca "Add python.exe
  to PATH"; el Python de Microsoft Store no sirve para esto).
- Estar frente a la pantalla a ~50–60 cm, con luz frontal (una lámpara
  o ventana frente a ti, no detrás).

## Instalación (una vez)

```powershell
cd <carpeta donde descomprimiste mirada>
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\t3_mediapipe_probe.py
```

La carpeta `.venv` no viene incluida: cada computadora crea la suya con
esos comandos. No necesitas correr `Activate.ps1` ni "activar" nada:
todos los comandos llaman directo al Python del proyecto. El modelo de
cara ya viene en el repo; el último comando solo verifica tu cámara.

## Prueba 1 — tablero de comunicación (~5 min)

```powershell
.\.venv\Scripts\python.exe app\board.py
```

- Si tienes varios monitores o cámaras, aparecen ventanas para elegir
  con click: el monitor muestra una captura de cada pantalla, las
  cámaras muestran vista en vivo (muévete para distinguirlas).
- Mira los 32 puntos blancos sin moverte (calibración).
- Después: mira una palabra y **cierra los ojos ~medio segundo** para
  seleccionarla. Sonará la frase en voz alta.
- Intenta decir las 8 palabras: SI, NO, AGUA, BAÑO, AYUDA, GRACIAS,
  LLAMAR, DOLOR (en el orden que quieras).
- Para salir: mira QUIT (arriba al centro) y cierra los ojos, o Shift+Q.
- Al terminar imprime `session: data\board-...` y `done: said=[...]`.
  **Copia todo el texto de la terminal** y guárdalo.

## Prueba 2 (opcional) — sesión de estudio (~15 min)

```powershell
.\.venv\Scripts\python.exe tools\record_session.py --seconds 900
```

No necesitas saber los números de tu cámara o monitor: si solo hay uno
de cada uno se usan solos, y si hay varios aparece una ventana con vista
en vivo para elegir con click. Calibra con ESPACIO en cada punto y luego
estudia/trabaja normal 15 min. Cada 2 min aparece un punto: míralo fijo
10 segundos.

## Qué devolver

Manda de regreso **solo** estos dos elementos (nada más):

1. La carpeta de tu sesión: `data\board-...` o `data\sess-...`
   (contiene eventos anónimos + recortes de ojos + capturas de pantalla).
2. El texto copiado de la terminal.

No modifiques ningún archivo `.py`. Si algo truena, manda el error tal cual:
un crash con su mensaje vale tanto como una prueba exitosa.

## Privacidad

Tu sesión contiene imágenes de tus ojos y capturas de tu pantalla durante
la prueba. Se usan solo para este hackathon (medir precisión del sistema),
no se publican, y puedes pedir que se borren en cualquier momento.
Evita tener información sensible visible durante la prueba 2.
