"""
Standalone launcher for ROESAN-SALVAGUARDAR.

Starts the Flask server and opens the browser automatically. Any startup
error is written to ERROR_ROESAN.txt next to the program so it can be shared
even if the console window closes.
"""

import os
import sys
import time
import threading
import traceback

HOST = '127.0.0.1'
PORT = 5000
URL = f'http://{HOST}:{PORT}/'


def _base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _write_error(text: str) -> None:
    try:
        with open(os.path.join(_base_dir(), 'ERROR_ROESAN.txt'), 'w', encoding='utf-8') as f:
            f.write(text)
    except Exception:
        pass


def _open_browser():
    time.sleep(2.0)
    try:
        import webbrowser
        webbrowser.open(URL)
    except Exception:
        pass


def main():
    # Make bundled package importable when frozen
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, getattr(sys, '_MEIPASS', os.path.dirname(sys.executable)))

    print('=' * 60)
    print('  ROESAN - SALVAGUARDAR')
    print('  Iniciando... abre tu navegador en: ' + URL)
    print('  (No cierres esta ventana mientras uses la app)')
    print('=' * 60)

    # Import the app here so import errors are captured too
    from app import app

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host=HOST, port=PORT, debug=False, threaded=True, use_reloader=False)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        tb = traceback.format_exc()
        _write_error(tb)
        print('\n' + '=' * 60)
        print('  OCURRIO UN ERROR AL INICIAR:')
        print('=' * 60)
        print(tb)
        print('\nSe guardo el detalle en el archivo ERROR_ROESAN.txt')
        print('(esta junto al programa). Enviame ese archivo para revisarlo.')
        try:
            input('\nPresiona ENTER para cerrar...')
        except Exception:
            time.sleep(120)
