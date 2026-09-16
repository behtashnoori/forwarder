"""Own native loopback cluster only; never discover/connect an ambient database."""
import os
import secrets
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from uuid import uuid4


def main():
    binary = Path(r'C:\Program Files\PostgreSQL\18\bin')
    # Python 3.13 mkdtemp(mode=0700) installs a Windows ACL that PostgreSQL's
    # restricted process cannot traverse. Inherit the temporary parent's ACL.
    root = (Path(tempfile.gettempdir()) / ('forwarder-fwd05-qualification-' + uuid4().hex)).resolve()
    root.mkdir(mode=0o777)
    data = root / 'data'
    assert data.resolve().is_relative_to(root)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    environment = dict(os.environ)
    for key in list(environment):
        if 'DATABASE_URL' in key or key.startswith('PG'):
            del environment[key]
    environment.update(APP_ENV='uat', SECRET_KEY=secrets.token_hex(32),
        JWT_SECRET_KEY=secrets.token_hex(64),
        DATABASE_URL='sqlite:///:memory:', TEST_DATABASE_URL='sqlite:///:memory:')

    def run(args, **kwargs):
        return subprocess.run([str(a) for a in args], env=environment, check=True, **kwargs)

    run([binary / 'initdb.exe', '-D', data, '-U', 'fwd05_qualification', '-A', 'trust', '--no-locale', '-E', 'UTF8'], stdout=subprocess.DEVNULL)
    started = False
    try:
        run([binary / 'pg_ctl.exe', '-D', data, '-l', root / 'server.log', '-o',
             f'-h 127.0.0.1 -p {port}', '-w', 'start'], stdout=subprocess.DEVNULL)
        started = True
        lines = (data / 'postmaster.pid').read_text().splitlines()
        assert Path(lines[1]).resolve() == data.resolve() and int(lines[3]) == port
        run([binary / 'createdb.exe', '-h', '127.0.0.1', '-p', port, '-U', 'fwd05_qualification', 'forwarder_fwd05_qualification'])
        environment['FWD05_DISPOSABLE_DATABASE_URL'] = f'postgresql+psycopg2://fwd05_qualification@127.0.0.1:{port}/forwarder_fwd05_qualification'
        environment['FWD05_OWN_CLUSTER_DATA'] = str(data)
        environment['DATABASE_URL'] = environment['FWD05_DISPOSABLE_DATABASE_URL']
        run([sys.executable, '-B', '-m', 'pytest', '-q', '--tb=no', '-p', 'no:cacheprovider',
             *sys.argv[1:]])
    finally:
        if started:
            # A checked, explicitly created data directory identifies this process.
            assert data.resolve().is_relative_to(root)
            run([binary / 'pg_ctl.exe', '-D', data, '-m', 'fast', '-w', 'stop'], stdout=subprocess.DEVNULL)
        print(f'SYNTHETIC_CLUSTER_STOPPED; retained diagnostics: {root}')


if __name__ == '__main__':
    main()
