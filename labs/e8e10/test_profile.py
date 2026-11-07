import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

class Student241880258E9Tests(unittest.TestCase):
    def test_duplicate_md_once_per_style_and_source_unchanged(self):
        import copy
        import shutil
        from lab import run
        for style in ['direct', 'macro', 'mixed']:
            with self.subTest(style=style), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                project = root / 'project'
                fixture(project, style)
                report = scan(project)
                missing = next(f for f in report['findings'] if f['type'] == 'MISSING')
                report['findings'].append(dict(missing))
                input_before = copy.deepcopy(report)
                before = (project / 'Makefile').read_bytes()
                diff, plan = patch(project, report)
                self.assertEqual(plan, [{'target': 'main.o', 'dependency': 'config.h', 'style': style}])
                added = [line for line in diff.splitlines() if line.startswith('+') and not line.startswith('+++')]
                expected = {
                    'direct': '+main.o: main.c unused.h config.h',
                    'macro': '+DEPS = main.c unused.h config.h',
                    'mixed': '+main.o: main.c $(HEADERS) config.h',
                }
                self.assertEqual(added, [expected[style]])
                self.assertEqual((project / 'Makefile').read_bytes(), before)
                self.assertEqual(report, input_before)
                copy_project = root / 'apply-demo'
                shutil.copytree(project, copy_project)
                candidate = root / 'candidate.patch'
                candidate.write_text(diff)
                run(['git', 'apply', '--check', str(candidate)], copy_project)
                run(['git', 'apply', str(candidate)], copy_project)
                self.assertEqual((copy_project / 'Makefile').read_text().split().count('config.h'), 1)
                self.assertFalse(any(f['type'] == 'MISSING' for f in scan(copy_project)['findings']))
                self.assertEqual((project / 'Makefile').read_bytes(), before)

    def test_dedup_key_keeps_distinct_targets_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'project'
            fixture(project)
            report = scan(project)
            edges = [('main.o', 'config.h'), ('helper.o', 'config.h'), ('main.o', 'extra.h')]
            report['findings'] = [
                {'type': 'MISSING', 'target': target, 'dependency': dependency}
                for target, dependency in edges + edges
            ]
            before = (project / 'Makefile').read_bytes()
            diff, plan = patch(project, report)
            self.assertEqual(plan, [
                {'target': target, 'dependency': dependency, 'style': 'direct'}
                for target, dependency in edges
            ])
            self.assertIn('+main.o: main.c unused.h config.h extra.h\n', diff)
            self.assertIn('+helper.o: helper.c config.h\n', diff)
            self.assertEqual((project / 'Makefile').read_bytes(), before)

class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name)/'sample';fixture(self.p)

    def test_independent_known_edges(self):
        r=scan(self.p)
        self.assertEqual(r['actual']['main.o'],['config.h','main.c'])
        self.assertEqual({(f['type'],f['dependency']) for f in r['findings']},{('MISSING','config.h'),('REDUNDANT','unused.h')})

    def test_unchanged_reuses_both_targets(self):
        r=scan(self.p,scan(self.p));self.assertEqual(r['reused'],['main.o','helper.o']);self.assertEqual(r['refreshed'],[])

    def test_include_added_invalidates_cache(self):
        old=scan(self.p)
        (self.p/'main.c').write_text('#include "extra.h"\n'+(self.p/'main.c').read_text());commit(self.p,'new include')
        r=scan(self.p,old)
        self.assertIn(['MISSING','main.o','extra.h'],r['added']);self.assertEqual(len(r['refreshed']),2)

    def test_patch_preserves_redundant_dependency(self):
        r=scan(self.p);diff,plan=patch(self.p,r)
        self.assertIn('+main.o: main.c unused.h config.h',diff)
        self.assertNotIn('-\tgcc',diff)
        self.assertNotIn('config.h',(self.p/'Makefile').read_text())

    def test_old_report_rejected(self):
        r=scan(self.p);r['commit']='0'*40
        with self.assertRaisesRegex(ValueError,'STALE_REPORT'):patch(self.p,r)

    def test_unsafe_dependency_rejected(self):
        r=scan(self.p);r['findings']=[{'type':'MISSING','target':'main.o','dependency':'../outside.h'}]
        with self.assertRaisesRegex(ValueError,'UNSAFE_PATH'):patch(self.p,r)

    def test_unsupported_configuration_rejected(self):
        (self.p/'Makefile').write_text((self.p/'Makefile').read_text().replace('-O0','-include unknown.h'))
        with self.assertRaisesRegex(ValueError,'UNSUPPORTED_FLAGS'):scan(self.p)
class Student241880068E8Tests(unittest.TestCase):
    def test_unknown_target_rejected_source_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'project'
            fixture(project)
            report = scan(project)
            report['findings'] = [{
                'type': 'MISSING',
                'target': 'unknown.o',
                'dependency': 'config.h',
            }]
            before = (project / 'Makefile').read_bytes()

            with self.assertRaisesRegex(
                ValueError, '^UNSUPPORTED_TARGET$'
            ):
                patch(project, report)

            self.assertEqual(
                (project / 'Makefile').read_bytes(), before
            )
class Student241880068E9Tests(unittest.TestCase):
    def test_mixed_shared_headers_only_changes_main_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'project'
            fixture(project, 'mixed')

            makefile = project / 'Makefile'
            text = makefile.read_text()
            text = text.replace(
                'helper.o: helper.c',
                'helper.o: helper.c $(HEADERS)'
            )
            makefile.write_text(text)
            commit(project, 'E9 shared HEADERS fixture')

            report = scan(project)
            before = makefile.read_bytes()
            diff, plan = patch(project, report)

            changes = [
                line for line in diff.splitlines()
                if line.startswith(('+', '-'))
                and not line.startswith(('+++', '---'))
            ]
            self.assertEqual(changes, [
                '-main.o: main.c $(HEADERS)',
                '+main.o: main.c $(HEADERS) config.h',
            ])
            self.assertEqual(plan, [{
                'target': 'main.o',
                'dependency': 'config.h',
                'style': 'mixed',
            }])
            self.assertEqual(makefile.read_bytes(), before)

class Student241880068E10Tests(unittest.TestCase):
    def test_compile_failure_rejected_source_unchanged(self):
        import difflib
        from lab import validate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / 'project'
            fixture(project)

            makefile = project / 'Makefile'
            before = makefile.read_bytes()
            original = before.decode()
            changed = original.replace(
                '-c main.c -o main.o',
                '-c nonexistent.c -o main.o'
            )
            self.assertNotEqual(original, changed)

            diff = ''.join(difflib.unified_diff(
                original.splitlines(True),
                changed.splitlines(True),
                fromfile='a/Makefile',
                tofile='b/Makefile'
            ))
            candidate = root / 'compile-failure.patch'
            candidate.write_text(diff)

            result = validate(
                project, candidate, root / 'validation'
            )

            self.assertTrue(result['checks']['patch_applies'])
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertTrue(result['source_unchanged'])
            self.assertIn(
                'nonexistent.c', result['error'] or ''
            )
            self.assertEqual(makefile.read_bytes(), before)
class Student241880180E10Tests(unittest.TestCase):
    def test_optimization_only_candidate_is_rejected_source_unchanged(self):
        import difflib
        from lab import validate

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / 'project'
            fixture(project)

            makefile = project / 'Makefile'
            before = makefile.read_bytes()
            original = before.decode()
            changed = original.replace('CFLAGS = -O0', 'CFLAGS = -O1', 1)
            self.assertNotEqual(original, changed)

            diff = ''.join(difflib.unified_diff(
                original.splitlines(True),
                changed.splitlines(True),
                fromfile='a/Makefile',
                tofile='b/Makefile'
            ))
            candidate = root / 'optimization-only.patch'
            candidate.write_text(diff)

            result = validate(project, candidate, root / 'validation')

            self.assertTrue(result['checks']['patch_applies'])
            self.assertTrue(result['checks']['build'])
            self.assertTrue(result['checks']['test'])
            self.assertFalse(result['checks']['header_change'])
            self.assertFalse(result['checks']['no_missing'])
            self.assertFalse(result['accepted'])
            self.assertTrue(result['rollback'])
            self.assertTrue(result['source_unchanged'])
            self.assertIsNone(result['error'])
            self.assertEqual(makefile.read_bytes(), before)
if __name__=='__main__':unittest.main()
