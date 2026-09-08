#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading
import webbrowser


def open_browser_for_runserver():
    """Open the local site when the development server starts."""
    if len(sys.argv) < 2 or sys.argv[1] != 'runserver':
        return

    # Django's auto-reloader starts a parent and child process. Open the
    # browser only from the serving process so it does not pop up twice.
    if os.environ.get('RUN_MAIN') != 'true' and '--noreload' not in sys.argv:
        return

    address = '127.0.0.1:8000'
    for arg in sys.argv[2:]:
        if not arg.startswith('-'):
            address = arg
            break

    if ':' not in address:
        address = f'127.0.0.1:{address}'
    if address.startswith('0.0.0.0:'):
        address = address.replace('0.0.0.0:', '127.0.0.1:', 1)

    url = f'http://{address}/'
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiep_backend.settings')
    open_browser_for_runserver()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
