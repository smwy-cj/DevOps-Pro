import json, tempfile, unittest
from pathlib import Path
from lab import fixture,scan,patch,commit

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
if __name__=='__main__':unittest.main()
