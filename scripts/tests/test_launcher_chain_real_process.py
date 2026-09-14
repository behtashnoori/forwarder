"""Local OS smoke for the cmd -> runtime serve -> surviving Waitress child chain.

The Scheduled Task and IIS boundary replay lives in the PowerShell matrix.
This test uses real cmd, the unchanged packaged runtime, real os.execv and TCP.
Only release/launcher paths are rebased under a disposable local directory.
"""
import http.client
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET

import psutil


ROOT = Path(__file__).resolve().parents[2]


def test_real_cmd_runtime_launcher_waitress_child(tmp_path):
    package = ROOT / 'release-candidates/Forwarder-Operational-Workspace-Production-CERTIFIED'
    runtime = package / 'artifact/runtime'
    assert os.name == 'nt' and (runtime / 'python.exe').is_file()
    # Refuse an occupied local port; never stop a pre-existing listener.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 5101))
    # Match Production's no-space release path. Windows os.execv in the
    # externally managed helper forwards argv without adding path quotes.
    release = tmp_path / 'release'
    shutil.copytree(runtime, release / 'runtime')
    python = release / 'runtime/python.exe'
    backend = release / 'backend'
    backend.mkdir()
    (backend / '__init__.py').write_text('')
    (backend / 'wsgi.py').write_text(
        "def app(environ, start_response):\n"
        "    start_response('200 OK', [('Content-Type', 'text/plain')])\n"
        "    return [b'local launcher health']\n")
    launcher = tmp_path / 'phase1b_production_cutover_runtime.py'
    evidence = tmp_path / 'launcher.json'
    # Same serve mechanism as the captured runtime helper. No product edits.
    launcher.write_text('''import argparse, json, os, sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('command', choices=['serve'])
for name in ('repo','host','port','log','env'): p.add_argument('--'+name, required=True)
a=p.parse_args()
os.chdir(a.repo)
Path(a.log).write_text(json.dumps({'pid':os.getpid(),'parent':os.getppid(),'runtime':sys.executable,'repo':os.getcwd()}))
os.execv(sys.executable,[sys.executable,'-m','waitress','--listen='+a.host+':'+a.port,'backend.wsgi:app'])
''')
    approved = r'C:\1-webapp\forwarder-runtime\phase1b_production_cutover_runtime.py'
    old = str(tmp_path / 'previous-release')
    document = ET.Element('Task')
    action = ET.SubElement(ET.SubElement(document, 'Actions'), 'Exec')
    ET.SubElement(action, 'Command').text = r'C:\Windows\System32\cmd.exe'
    payload = (
        f'set PYTHONPATH={old}&& cd /d "{old}"&& "{old}\\runtime\\python.exe" "{approved}" serve '
        f'--repo "{old}" --env "{tmp_path / "unused-local.env"}" '
        f'--host 127.0.0.1 --port 5101 --log "{evidence}"')
    ET.SubElement(action, 'Arguments').text = '/d /c "' + payload.replace('"', '""') + '"'
    ET.SubElement(action, 'WorkingDirectory').text = old
    task_xml = tmp_path / 'task.xml'
    ET.ElementTree(document).write(task_xml, encoding='unicode')
    transform = tmp_path / 'transform.ps1'
    transform.write_text('''param($DeployScript,$TaskXml,$Target)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($DeployScript,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'syntax failure'}
foreach($function in @($ast.EndBlock.Statements|Where-Object {$_ -is [Management.Automation.Language.FunctionDefinitionAst]})){. ([scriptblock]::Create($function.Extent.Text))}
[xml]$candidate=New-TaskLaunchXml (Get-Content -LiteralPath $TaskXml -Raw) $Target
$candidate.Task.Actions.Exec.Arguments
''')
    args = subprocess.check_output([
        'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
        '-File', str(transform), '-DeployScript',
        str(ROOT / 'scripts/deploy/deploy_windows_iis_waitress_operational.ps1'),
        '-TaskXml', str(task_xml), '-Target', str(release),
    ], text=True, timeout=20).strip()
    assert approved in args and old not in args
    # Rebase only the external helper location at the local OS boundary.
    args = args.replace(approved, str(launcher))
    command = f'"{os.environ["SystemRoot"]}\\System32\\cmd.exe" {args}'
    child = None
    launcher_process = None
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    with (tmp_path / 'output.log').open('w') as output:
        process = subprocess.Popen(command, cwd=release, env=environment,
                                   stdout=output, stderr=output,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                rows = [c for c in psutil.net_connections('tcp')
                        if c.status == psutil.CONN_LISTEN and
                        c.laddr.ip == '127.0.0.1' and c.laddr.port == 5101]
                owners = {row.pid for row in rows}
                if owners:
                    assert len(owners) == 1
                    observed = psutil.Process(owners.pop())
                    assert Path(observed.exe()).resolve() == python.resolve()
                    child = observed
                    break
                time.sleep(.2)
            assert child is not None, (tmp_path / 'output.log').read_text()
            launched = json.loads(evidence.read_text())
            launcher_process = launched['pid']
            assert launched['parent'] == process.pid
            assert child.ppid() == launcher_process
            assert child.cmdline() == [str(python), '-m', 'waitress',
                                       '--listen=127.0.0.1:5101', 'backend.wsgi:app']
            assert process.wait(timeout=10) == 0
            assert child.is_running()
            cim = json.loads(subprocess.check_output([
                'powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                f"Get-CimInstance Win32_Process -Filter 'ProcessId={child.pid}' | "
                'Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json',
            ], text=True, timeout=15))
            assert Path(cim['ExecutablePath']).resolve() == python.resolve()
            assert cim['CommandLine'].endswith(
                '-m waitress --listen=127.0.0.1:5101 backend.wsgi:app')
            connection = http.client.HTTPConnection('127.0.0.1', 5101, timeout=5)
            try:
                connection.request('GET', '/api/health')
                response = connection.getresponse()
                assert response.status == 200
                assert response.read() == b'local launcher health'
            finally:
                connection.close()
            result = {
                'LOCAL_REAL_CMD_LAUNCHER_CHILD': 'PASS',
                'cmd_pid': process.pid, 'cmd_exit': process.returncode,
                'launcher_pid': launcher_process, 'listener_pid': child.pid,
                'listener_executable': child.exe(), 'listener_command': child.cmdline(),
                'unique_listener_owners': 1, 'internal_health': 200,
                'child_alive_after_launcher_return': True,
                'Win32_Process': cim,
                'scope': 'Local OS process chain with disposable WSGI health app; Task/IIS covered separately by captured-boundary replay.',
            }
            (ROOT / 'qualification/launcher-chain-real-process.json').write_text(json.dumps(result, indent=2)+'\n')
        finally:
            # Only a process whose executable was verified in this owned temp
            # release can be terminated. Existing port owners are never stopped.
            if child is not None and child.is_running():
                assert Path(child.exe()).resolve() == python.resolve()
                child.terminate()
                child.wait(timeout=10)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
