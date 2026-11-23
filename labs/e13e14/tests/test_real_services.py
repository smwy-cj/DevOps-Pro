"""Exercise real single-target Git/Make projects through the E14 HTTP handlers."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import service
import orchestrate
from real_project import Project


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()


class Projects(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / 'data/source'
        folder = self.repo / 'components/counter'
        folder.mkdir(parents=True)
        (folder / 'unit.c').write_text(
            '#include <stdio.h>\n#include "config.h"\n'
            'int main(void){printf("%d\\n",VALUE);return 0;}\n')
        (folder / 'config.h').write_text('#define VALUE 1\n')
        (folder / 'unused.h').write_text('/* retained */\n')
        (folder / 'Makefile').write_text(
            'app: unit.o\n\tgcc unit.o -o app\n'
            'unit.o: unit.c unused.h\n\tgcc -O0 -c unit.c -o unit.o\n'
            '.PHONY: clean\nclean:\n\trm -f unit.o app\n')
        (self.repo / '.gitignore').write_text('*.o\napp\n')
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.name', 'Fixture')
        git(self.repo, 'config', 'user.email', 'fixture@localhost')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'base')
        self.base_sha = git(self.repo, 'rev-parse', 'HEAD')
        (folder / 'unit.c').write_text((folder / 'unit.c').read_text() + '/* target */\n')
        git(self.repo, 'commit', '-qam', 'target')
        self.target_sha = git(self.repo, 'rev-parse', 'HEAD')
        self.config = {
            'subdirectory': 'components/counter', 'makefile': 'Makefile',
            'object_sources': {'unit.o': 'unit.c'}, 'compiler': 'gcc', 'flags': ['-O0'],
            'clean': ['make', 'clean'], 'build': ['make', 'app'],
            'test': [sys.executable, '-c',
                     'import pathlib,re,subprocess; '
                     'v=re.search(r"VALUE (\\d+)",pathlib.Path("config.h").read_text())[1]; '
                     'assert subprocess.check_output(["./app"],text=True).strip()==v'],
            'header_probe': {'path': 'config.h', 'target': 'unit.o',
                             'replace': {'old': '#define VALUE 1', 'new': '#define VALUE 2'}},
        }
        self.candidate = self.root / 'data/candidate.Dockerfile'
        self.candidate.write_text('FROM python:3.13-slim@sha256:' + 'a' * 64 + '\n')
        self.adapter = Project(self.config)
        self.work = self.root / 'work/current'
        self.work.parent.mkdir()
        git(self.root, 'clone', '-q', str(self.repo), str(self.work))

    def payload(self, project, out, **extra):
        return {'project': str(project), 'out': str(out), 'project_config': self.config,
                'job_id': 'job-real', 'trace_id': 'trace-real',
                'target_commit': self.target_sha, **extra}

    def handler(self, role, payload):
        with mock.patch.object(service, 'ROOT', self.root), mock.patch.object(service, 'ROLE', role):
            return service.run(payload)

    def test_draft_uses_nested_directory_and_rejects_changed_candidate(self):
        with mock.patch.object(service, 'auto_build', return_value={'status': 'SUCCEEDED'}) as build:
            request = self.payload(self.work, self.root / 'work/draft',
                                   candidate=str(self.candidate),
                                   candidate_sha256=service.sha(self.candidate))
            self.handler('draft', request)
            self.assertEqual(build.call_args.args[0], self.adapter.directory(self.work))
            request['candidate_sha256'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'CANDIDATE_HASH_MISMATCH'):
                self.handler('draft', request)
            self.assertEqual(build.call_count, 1)

    def test_full_check_uses_actual_subdirectory_and_configured_commands(self):
        with mock.patch.object(service, 'full_check', return_value={'status': 'SUCCEEDED'}) as full:
            self.handler('buildchecker', self.payload(self.work, self.root / 'work/full'))
            self.assertEqual(full.call_args.args[0], self.adapter.directory(self.work))
            self.assertEqual(full.call_args.kwargs, {'clean_command': 'make clean', 'build_command': 'make app'})

    def test_incremental_handler_supports_one_mapped_target(self):
        base = self.root / 'work/base'
        base.parent.mkdir(exist_ok=True)
        git(self.root, 'clone', '-q', str(self.work), str(base))
        git(base, 'checkout', '-q', '--detach', self.base_sha)
        old = self.adapter.scan(base)
        current = self.adapter.scan(self.work)
        graph = self.root / 'work/graph.json'
        graph.write_text(json.dumps([{'target': t, 'dependency': d}
                                    for t, deps in old['actual'].items() for d in deps]))
        reference = self.root / 'work/findings.json'
        reference.write_text(json.dumps({'status': 'SUCCEEDED', 'findings': current['findings']}))
        response = self.handler('echecker', self.payload(
            self.work, self.root / 'work/incremental', base=str(base),
            baseline_graph=str(graph), baseline_graph_sha256=service.sha(graph),
            target_findings=str(reference), target_findings_sha256=service.sha(reference)))
        envelope = json.loads(Path(response['report']).read_text())
        self.assertEqual(set(envelope['data']['actual']), {'unit.o'})
        self.assertEqual(envelope['data']['commit'], self.target_sha)
        self.assertEqual(envelope['job_id'], 'job-real')

    def test_nested_patch_validates_real_build_and_preserves_header(self):
        report = self.root / 'work/report.json'
        report.parent.mkdir(exist_ok=True)
        report.write_text(json.dumps({
            'schema_version': 'e11e12-1', 'kind': 'incremental-check',
            'status': 'SUCCEEDED', 'commit': self.target_sha,
            'job_id': 'job-real', 'trace_id': 'trace-real', 'data': self.adapter.scan(self.work)}))
        request = self.payload(self.work, self.root / 'work/repair',
                               report=str(report), report_sha256=service.sha(report))
        original = (self.adapter.directory(self.work) / 'Makefile').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Report transfer hash mismatch'):
            self.handler('mdfixer', dict(request, report_sha256='0' * 64))
        self.assertEqual((self.adapter.directory(self.work) / 'Makefile').read_bytes(), original)
        response = self.handler('mdfixer', request)
        self.assertTrue(response['validation']['accepted'], response)
        self.assertEqual(response['input_report']['sha256'], service.sha(report))
        self.assertIn('components/counter/Makefile', Path(response['patch']).read_text())
        self.assertIn('unit.c unused.h config.h', (self.adapter.directory(self.work) / 'Makefile').read_text())
        self.assertEqual((self.adapter.directory(self.work) / 'config.h').read_text(), '#define VALUE 1\n')

    def run_orchestrator(self, final_missing=False, bad_hash=False):
        request = {'mode': 'e12', 'repo': '/course/data/source',
                   'candidate': '/course/data/candidate.Dockerfile',
                   'candidate_sha256': '0' * 64 if bad_hash else service.sha(self.candidate),
                   'base': self.base_sha, 'target': self.target_sha, 'project': self.config}
        calls = []

        def fake_call(role, payload, evidence):
            calls.append((role, payload))
            self.assertEqual(payload['project_config'], self.config)
            folder = self.root / payload['out'].removeprefix('/course/')
            folder.mkdir(parents=True)
            if role == 'buildchecker':
                (folder / 'actual-graph.json').write_text('[]\n')
                findings = ([{'type': 'MISSING', 'target': 'unit.o', 'dependency': 'config.h'}]
                            if final_missing or folder.name != 'final-full' else [])
                (folder / 'findings.json').write_text(json.dumps({'status': 'SUCCEEDED', 'findings': findings}))
                response = {'status': 'SUCCEEDED', 'result': {'status': 'SUCCEEDED', 'findings': findings}}
            elif role == 'echecker':
                report = folder / 'incremental-check.json'
                report.write_text('{}\n')
                response = {'status': 'SUCCEEDED', 'report': '/course/' + report.relative_to(self.root).as_posix(),
                            'sha256': service.sha(report)}
            elif role == 'mdfixer':
                makefile = self.root / payload['project'].removeprefix('/course/') / self.config['subdirectory'] / 'Makefile'
                makefile.write_text(makefile.read_text().replace('unit.c unused.h', 'unit.c unused.h config.h'))
                response = {'status': 'SUCCEEDED', 'input_report': {'sha256': payload['report_sha256']},
                            'validation': {'accepted': True}}
            else:
                response = {'status': 'SUCCEEDED'}
            orchestrate.save(evidence, response)
            return response

        with mock.patch.object(orchestrate, 'ROOT', self.root), mock.patch.object(
                orchestrate, 'call', side_effect=fake_call):
            result = orchestrate.execute(request, self.root / 'work/e2e')
        return result, calls

    def test_orchestrator_passes_profile_to_every_role(self):
        result, calls = self.run_orchestrator()
        self.assertEqual(result['status'], 'SUCCEEDED', result.get('error'))
        self.assertEqual([s['name'] for s in result['stages']],
                         ['draft', 'full-check', 'incremental-check', 'repair', 'recheck'])
        self.assertTrue(result['input_unchanged'])
        self.assertEqual({role for role, _ in calls}, {'draft', 'buildchecker', 'echecker', 'mdfixer'})

    def test_final_missing_rolls_back_only_working_copy(self):
        result, _ = self.run_orchestrator(final_missing=True)
        self.assertEqual(result['status'], 'FAILED')
        self.assertTrue(result['rollback'])
        self.assertTrue(result['target_makefile_unchanged'])
        self.assertTrue(result['input_unchanged'])

    def test_changed_candidate_is_rejected_before_http_calls(self):
        result, calls = self.run_orchestrator(bad_hash=True)
        self.assertEqual(result['status'], 'FAILED')
        self.assertEqual(result['error'], 'CANDIDATE_HASH_MISMATCH')
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
