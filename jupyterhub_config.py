import sys

c.Authenticator.admin_users = set(["dblank"])

c.JupyterHub.services = [
    {
        'name': 'public',
        'url': 'http://127.0.0.1:10101',
        'command': [sys.executable, './public_handler.py'],
    },
    {
        'name': 'accounts',
        'url': 'http://127.0.0.1:10102',
        'command': [sys.executable, './accounts.py'],
    },
]
