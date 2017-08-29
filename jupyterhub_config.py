import sys

c.JupyterHub.services = [
    {
        'name': 'public',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './public_handler.py'],
    }
]
