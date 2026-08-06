"""
Standalone launcher for ROESAN-SALVAGUARDAR.

When packaged with PyInstaller this is the entry point: it starts the Flask
server and opens the default browser automatically. No Python installation
needed on the target computer.
"""

import os
import sys
import time
import threading
import webbrowser

# Ensure the bundled package root is importable when frozen
if getattr(sys, 'frozen', False):
    sys.path.insert(0, getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))

from app import app  # noqa: E402

HOST = '127.0.0.1'
PORT = 5000
URL = f'http://{HOST}:{PORT}/'


def _open_browser():
    time.sleep(1.8)
    try:
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    print('=' * 60)
    print('  ROESAN - SALVAGUARDAR')
    print('  Servidor iniciando...')
    print(f'  Abre tu navegador en: {URL}')
    print('  (Esta ventana debe permanecer abierta mientras uses la app)')
    print('  Para cerrar la aplicacion, cierra esta ventana.')
    print('=' * 60)

    threading.Thread(target=_open_browser, daemon=True).start()

    # Use Flask's built-in server; threaded so multiple requests work
    app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
