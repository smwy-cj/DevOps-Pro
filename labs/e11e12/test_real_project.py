"""Adapter tests run on the host without invoking Docker or strace."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pipeline
from real_project import Project, run

MAKE = shutil.which('make') or shutil.which('mingw32-make')
GCC = shutil.which('gcc')


@unittest.skipUnless(MAKE and GCC and shutil.which('git'), 'GNU Make, GCC and Git required')
class RealProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.project = self.repo / 'components/regex'
        self.project.mkdir(parents=True)
        (self.project / 'engine.c').write_text('#include "engine.h"\nint answer(void){return ANSWER;}\n')
        (self.project / 'engine.h').write_text('#define ANSWER 7\nint answer(void);\n')
        (self.project / 'extra.h').write_text('/* unused input */\n')
        (self.project / 'check.c').write_text('#include "engine.h"\nint main(void){return answer()==ANSWER ? 0 : 1;}\n')
        (self.project / 'Makefile').write_text(
            'CFLAGS = -O0\nHEADERS = extra.h\n'
            'all: check.exe\n'
            'engine.o: engine.c $(HEADERS)\n\tgcc $(CFLAGS) -c engine.c -o engine.o\n'
            'check.o: check.c engine.h\n\tgcc $(CFLAGS) -c check.c -o check.o\n'
            'check.exe: check.o engine.o\n\tgcc check.o engine.o -o check.exe\n', encoding='utf-8')
        run(['git', 'init', '-q', str(self.repo)], self.root)
        run(['git', '-c', 'user.name=AdapterTest', '-c', 'user.email=test@localhost', 'add', '.'], self.repo)
        run(['git', '-c', 'user.name=AdapterTest', '-c', 'user.email=test@localhost', 'commit', '-qm', 'input'], self.repo)
        self.config = {'subdirectory': 'components/regex', 'object_sources': {'engine.o': 'engine.c', 'check.o': 'check.c'},
                       'compiler': GCC, 'flags': ['-O0'], 'build': [MAKE, 'all'],
                       'clean': [sys.executable, '-c', 'from pathlib import Path; [p.unlink() for p in Path(".").glob("*.o")]'],
                       'test': ['./check.exe'], 'header_probe': {'path': 'engine.h', 'target': 'engine.o',
                       'replace': {'old': '#define ANSWER 7', 'new': '#define ANSWER 8'}}}
        self.adapter = Project(self.config)

    def test_scan_cache_and_header_invalidation(self):
        first = self.adapter.scan(self.repo)
        self.assertIn({'type': 'MISSING', 'target': 'engine.o', 'dependency': 'engine.h'}, first['findings'])
        self.assertIn({'type': 'REDUNDANT', 'target': 'engine.o', 'dependency': 'extra.h'}, first['findings'])
        self.assertEqual(self.adapter.scan(self.repo, first)['refreshed'], [])
        (self.project / 'engine.h').write_text('#include "extra.h"\n#define ANSWER 7\nint answer(void);\n')
        self.assertEqual(set(self.adapter.scan(self.repo, first)['refreshed']), {'engine.o', 'check.o'})

    def test_nested_patch_and_real_build_validation(self):
        report = self.adapter.scan(self.repo)
        report['findings'] *= 2
        diff, edits = self.adapter.patch(self.repo, report)
        self.assertEqual(len(edits), 1)
        self.assertIn('b/components/regex/Makefile', diff)
        patchfile = self.root / 'candidate.patch'
        patchfile.write_text(diff, encoding='utf-8')
        verdict = self.adapter.validate(self.repo, patchfile, self.root / 'validation')
        self.assertTrue(verdict['accepted'], verdict)
        self.assertIn('$(HEADERS) engine.h', (self.project / 'Makefile').read_text())
        self.assertNotIn('E12 dependency', (self.project / 'engine.h').read_text())
        self.assertFalse(any(f['type'] == 'MISSING' for f in self.adapter.scan(self.repo)['findings']))

    def test_test_failure_preserves_source(self):
        report = self.adapter.scan(self.repo)
        diff, _ = self.adapter.patch(self.repo, report)
        before = (self.project / 'Makefile').read_bytes()
        patchfile = self.root / 'candidate.patch'
        patchfile.write_text(diff, encoding='utf-8')
        config = dict(self.config, test=[sys.executable, '-c', 'raise SystemExit(1)'])
        result = Project(config).validate(self.repo, patchfile, self.root / 'reject')
        self.assertFalse(result['accepted'])
        self.assertTrue(result['rollback'])
        self.assertEqual((self.project / 'Makefile').read_bytes(), before)

    def test_stale_report_and_complex_rule_rejected(self):
        report = self.adapter.scan(self.repo)
        with self.assertRaisesRegex(ValueError, 'STALE_REPORT'):
            self.adapter.patch(self.repo, dict(report, commit='0' * 40))
        path = self.project / 'Makefile'
        path.write_text(path.read_text().replace('engine.c $(HEADERS)', 'engine.c | extra.h'))
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_RULE'):
            self.adapter.patch(self.repo, report)

    def test_full_sha_required_for_real_snapshot(self):
        with self.assertRaisesRegex(pipeline.Failure, '40-character'):
            pipeline.snapshot(self.repo, 'HEAD', self.root / 'copy', self.root / 'logs', self.adapter)

    def test_source_mapping_change_invalidates_cache(self):
        before = self.adapter.scan(self.repo)
        config = copy.deepcopy(self.config)
        config['flags'] = ['-O1']
        self.assertTrue(Project(config).scan(self.repo, before)['refreshed'])


class ProfileSafety(unittest.TestCase):
    def test_path_traversal_rejected(self):
        from real_project import safe_path
        for value in ('../x', '/tmp/x', 'C:/x', 'x;rm', '.', ''):
            with self.subTest(value=value), self.assertRaises(ValueError):
                safe_path(value)

    def test_existing_sample_projection_preserved(self):
        findings = [{'type': 'MISSING', 'target': t, 'dependency': 'x.h'} for t in ('main.o', 'helper.o', 'other.o')]
        self.assertEqual(len(pipeline.normalized(findings)), 2)
        self.assertEqual(len(pipeline.normalized(findings, ('other.o',))), 1)


if __name__ == '__main__':
    unittest.main()
