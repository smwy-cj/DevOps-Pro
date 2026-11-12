"""Integrity and preparation checks; full Docker execution is deliberately external."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

import pipeline
from draft.autobuild import prepare_candidate
from real_project import Project

spec = importlib.util.spec_from_file_location('student_handoff', pipeline.ROOT / 'scripts/e12_241830179.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def test_recorded_revisions_and_candidate_contract(self):
        request = handoff.load(handoff.DOCS / 'request.json')
        manifest = handoff.load(handoff.DOCS / 'project.json')
        self.assertEqual(request['base'], manifest['base_commit'])
        self.assertEqual(request['target'], manifest['target_commit'])
        adapter = Project(request['project'])
        broken = (adapter.directory(pipeline.ROOT) / 'Dockerfile.broken').read_text()
        candidate = (handoff.DOCS / 'candidate.Dockerfile').read_text()
        baseline = prepare_candidate(broken, candidate)
        self.assertIn('RUN make app', baseline)
        self.assertNotIn('apt-get', baseline)

    def test_manifest_checks_hash_and_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root / 'candidate.patch'
            path.write_bytes(b'patch')
            descriptor = {'uri': 'artifact://job-test/candidate.patch', 'bytes': 5,
                          'sha256': hashlib.sha256(b'patch').hexdigest()}
            handoff.save(root / 'result.json', {'job_id': 'job-test', 'artifacts': [descriptor]})
            handoff.check_manifest(root)
            path.write_bytes(b'other')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                handoff.check_manifest(root)
            descriptor['uri'] = 'artifact://job-test/../outside'
            handoff.save(root / 'result.json', {'job_id': 'job-test', 'artifacts': [descriptor]})
            with self.assertRaisesRegex(ValueError, 'outside'):
                handoff.check_manifest(root)

    def test_prepare_does_not_overwrite_inputs(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(handoff, 'DATA', Path(temp)):
            with self.assertRaisesRegex(ValueError, 'already exists'):
                handoff.prepare()

    def test_api_downloads_unicode_artifact_with_integrity(self):
        content = '本机传输测试'.encode('utf-8')
        result = {'job_id': 'job-test', 'status': 'SUCCEEDED', 'artifacts': [
            {'uri': 'artifact://job-test/目录/证据.txt', 'bytes': len(content),
             'sha256': hashlib.sha256(content).hexdigest()}]}
        def response(request, **kwargs):
            if not isinstance(request, str):
                value = {'job_id': 'job-test', 'status': 'QUEUED'}
            elif request.endswith('/artifacts'):
                value = result
            elif '/files/' in request:
                self.assertIn('%E7%9B%AE', request)
                return io.BytesIO(content)
            else:
                value = {'job_id': 'job-test', 'status': 'SUCCEEDED'}
            return io.BytesIO(json.dumps(value).encode())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / 'data'
            handoff.save(data / 'api-request.json', {'input': {}, 'idempotency_key': 'test'})
            with patch.object(handoff, 'ROOT', root), patch.object(handoff, 'DATA', data), \
                    patch.object(handoff, 'build_opener', return_value=Mock(open=response)):
                handoff.api('http://127.0.0.1:8080')
                evidence = root / handoff.OUT
                self.assertEqual((evidence / '目录/证据.txt').read_bytes(), content)
                handoff.check_manifest(evidence)


if __name__ == '__main__':
    unittest.main()
