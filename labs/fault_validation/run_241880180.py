"""Isolated real-project fault checks; never stop or configure shared services."""
import argparse
import difflib
import hashlib
from http.server import HTTPServer
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.request import ProxyHandler, build_opener
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'labs/e13e14'), str(ROOT / 'labs/e11e12'),
               str(ROOT / 'labs/e11e12/vendor'),
               str(ROOT / 'labs/e11e12/environment/services/buildchecker')]
import orchestrate
from real_project import Project


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


def fingerprint(repo, config):
    directory = Project(config).directory(repo)
    return {'head': git(repo, 'rev-parse', 'HEAD'),
            'status': git(repo, 'status', '--porcelain=v1', '--untracked-files=all'),
            'files': {path.relative_to(repo).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in sorted(directory.rglob('*'))
                      if path.is_file() and (path.suffix in ('.c', '.h', '.py', '.mk')
                                            or path.name == config['makefile'])}}


def serve(role, port):
    import service
    service.ROLE = role
    original = service.run

    def controlled_run(data):
        result = original(data)
        if role == 'buildchecker' and '/rollback-final-missing/final-full' in data['out']:
            result['result']['findings'].append({
                'type': 'MISSING', 'target': 'main.o', 'dependency': 'fault-injected.h'})
            result['fault_injection'] = 'FINAL_RECHECK_MISSING_RESPONSE_ONLY'
        return result

    service.run = controlled_run
    HTTPServer(('127.0.0.1', port), service.Handler).serve_forever()


class RealProjectFaults(unittest.TestCase):
    request = None
    output = None

    def setUp(self):
        self.config = self.request['project']
        self.repo = orchestrate.host_path(self.request['repo'])

    def check_unchanged(self, before, folder):
        after = fingerprint(self.repo, self.config)
        save(folder / 'source-before.json', before)
        save(folder / 'source-after.json', after)
        self.assertEqual(before, after)

    def test_01_real_draft_timeout_terminates(self):
        request = dict(self.request, build_timeout=0.001)
        folder = self.output / 'timeout'
        before = fingerprint(self.repo, self.config)
        started = time.monotonic()
        result = orchestrate.execute(request, folder)
        elapsed = time.monotonic() - started
        self.check_unchanged(before, folder)
        draft = json.loads((folder / 'draft-build/result.json').read_text())
        save(folder / 'assertions.json', {
            'expected': 'DRAFT TIMED_OUT, pipeline FAILED, duration < 30s, input unchanged',
            'actual': {'pipeline_status': result['status'], 'draft_status': draft['status'],
                       'elapsed_seconds': elapsed, 'error': result.get('error')},
            'job_id': result['job_id'], 'trace_id': result['trace_id']})
        self.assertEqual(draft['status'], 'TIMED_OUT')
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('TIMED_OUT', result['error'])
        self.assertLess(elapsed, 30)
        self.assertTrue(result['input_unchanged'])

    def reject_candidate(self, name, transform, expectation):
        folder = self.output / name
        folder.mkdir()
        before = fingerprint(self.repo, self.config)
        adapter = Project(self.config)
        makefile = adapter.directory(self.repo) / adapter.makefile
        original = makefile.read_text()
        candidate = folder / 'candidate.patch'
        if transform:
            changed = transform(original)
            self.assertNotEqual(original, changed)
            relative = makefile.relative_to(self.repo).as_posix()
            diff = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                               fromfile='a/' + relative, tofile='b/' + relative))
        else:
            diff = 'invalid patch\n'
        candidate.write_text(diff, encoding='utf-8')
        save(folder / 'input.json', {'project': self.request['project'], 'target': self.request['target'],
                                    'candidate_sha256': hashlib.sha256(candidate.read_bytes()).hexdigest(),
                                    'expected': expectation})
        verdict = adapter.validate(self.repo, candidate, folder / 'validation')
        self.check_unchanged(before, folder)
        self.assertFalse(verdict['accepted'])
        self.assertTrue(verdict['source_unchanged'])
        self.assertTrue(verdict['rollback'])
        return adapter, folder, verdict

    def test_02_invalid_patch_rejected(self):
        _, folder, verdict = self.reject_candidate('invalid-patch', None,
            'Patch cannot apply; reject before build; source bytes, HEAD and Git status unchanged')
        self.assertFalse(verdict['checks'].get('patch_applies', False))
        self.assertIsNotNone(verdict['error'])
        save(folder / 'assertions.json', {'passed': True, 'verdict': verdict})

    def test_03_buildable_patch_still_missing_rejected(self):
        adapter, folder, verdict = self.reject_candidate('optimization-only',
            lambda text: text.replace('CFLAGS = -Wall -Wextra', 'CFLAGS = -Wall -Wextra -O1', 1),
            'Patch applies and builds but does not repair config.h; reject and preserve source')
        self.assertTrue(verdict['checks']['patch_applies'])
        self.assertTrue(verdict['checks']['build'])
        self.assertTrue(verdict['checks']['test'])
        self.assertFalse(verdict['checks']['header_change'])
        sandbox = folder / 'validation/sandbox'
        git(sandbox, 'add', self.config['subdirectory'])
        git(sandbox, '-c', 'user.name=241880180', '-c', 'user.email=fixture@localhost',
            'commit', '-qm', 'Evidence snapshot after rejected candidate')
        recheck = adapter.scan(sandbox)
        save(folder / 'recheck.json', recheck)
        self.assertIn({'type': 'MISSING', 'target': 'main.o', 'dependency': 'config.h'}, recheck['findings'])
        save(folder / 'assertions.json', {'passed': True, 'verdict': verdict,
                                         'remaining_missing': [item for item in recheck['findings'] if item['type'] == 'MISSING']})

    def test_04_final_recheck_failure_restores_written_makefile(self):
        folder = self.output / 'rollback-final-missing'
        before = fingerprint(self.repo, self.config)
        result = orchestrate.execute(self.request, folder)
        self.check_unchanged(before, folder)
        validation = json.loads((folder / 'repair-work/validation/validation.json').read_text())
        final_response = json.loads((folder / 'recheck-response.json').read_text())
        target = folder / 'target-project'
        original_makefile = subprocess.check_output(
            ['git', 'show', 'HEAD:' + self.config['subdirectory'] + '/' + self.config['makefile']], cwd=target)
        target_makefile = Project(self.config).directory(target) / self.config['makefile']
        self.assertTrue(validation['accepted'])
        self.assertEqual(final_response['fault_injection'], 'FINAL_RECHECK_MISSING_RESPONSE_ONLY')
        self.assertEqual(result['status'], 'FAILED')
        self.assertIn('Recheck has', result['error'])
        self.assertTrue(result['rollback'])
        self.assertTrue(result['target_makefile_unchanged'])
        self.assertEqual(target_makefile.read_bytes(), original_makefile)
        self.assertEqual(git(target, 'status', '--porcelain=v1', '--untracked-files=no'), '')
        save(folder / 'assertions.json', {
            'passed': True, 'fault_injection': 'test-only HTTP response adds MISSING after real final scan',
            'real_final_scan_retained': 'final-full/findings.json',
            'patched_then_restored': True, 'target_git_status': git(target, 'status', '--porcelain=v1'),
            'original_makefile_sha256': hashlib.sha256(original_makefile).hexdigest(),
            'restored_makefile_sha256': hashlib.sha256(target_makefile.read_bytes()).hexdigest()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve-role', choices=orchestrate.PORTS)
    parser.add_argument('--port', type=int)
    parser.add_argument('--request', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.serve_role:
        serve(args.serve_role, args.port)
        return 0
    if args.out.exists():
        parser.error('Use a fresh output directory')
    args.out.mkdir(parents=True)
    processes = []
    logs = []
    try:
        for role in orchestrate.PORTS:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            orchestrate.PORTS[role] = port
            log = (args.out / (role + '-service.log')).open('w')
            logs.append(log)
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                      '--serve-role', role, '--port', str(port)], stdout=log, stderr=log)
            processes.append(child)
            opener = build_opener(ProxyHandler({}))
            for attempt in range(100):
                try:
                    with opener.open(f'http://127.0.0.1:{port}/health', timeout=1):
                        break
                except OSError:
                    if child.poll() is not None:
                        raise RuntimeError(role + ' private server failed; inspect log')
                    time.sleep(0.1)
            else:
                raise RuntimeError(role + ' health deadline exceeded')
        RealProjectFaults.request = json.loads(args.request.read_text())
        RealProjectFaults.output = args.out.resolve()
        save(args.out / 'scope.json', {
            'tool_commit': git(ROOT, 'rev-parse', 'HEAD'), 'shared_services_used': False,
            'isolated_ports': orchestrate.PORTS, 'request': RealProjectFaults.request,
            'injection': 'final HTTP response only for rollback case; production sources unchanged'})
        with (args.out / 'tests.log').open('w') as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(RealProjectFaults))
        summary = {'tests': result.testsRun, 'failures': len(result.failures),
                   'errors': len(result.errors), 'passed': result.wasSuccessful()}
        save(args.out / 'summary.json', summary)
        print(json.dumps(summary), flush=True)
        return 0 if result.wasSuccessful() else 1
    finally:
        for child in processes:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
