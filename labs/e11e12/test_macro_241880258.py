import copy
import tempfile
import unittest
from pathlib import Path
from macro_241880258 import prepare
from lab import patch, scan, validate


class Student241880258E11MacroTests(unittest.TestCase):
    def test_two_headers_go_into_deps_and_main_keeps_macro_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'project'
            _, target, report = prepare(project)
            self.assertEqual(report['commit'], target)
            self.assertEqual(
                {(f['target'], f['dependency']) for f in report['findings'] if f['type'] == 'MISSING'},
                {('main.o', 'config.h'), ('main.o', 'extra.h')})
            before = (project / 'Makefile').read_bytes()
            input_before = copy.deepcopy(report)
            diff, plan = patch(project, report)
            self.assertEqual(plan, [
                {'target': 'main.o', 'dependency': 'config.h', 'style': 'macro'},
                {'target': 'main.o', 'dependency': 'extra.h', 'style': 'macro'}])
            changes = [line for line in diff.splitlines()
                       if line.startswith(('+', '-')) and not line.startswith(('+++', '---'))]
            self.assertEqual(changes, ['-DEPS = main.c unused.h',
                                       '+DEPS = main.c unused.h config.h extra.h'])
            self.assertEqual((project / 'Makefile').read_bytes(), before)
            self.assertEqual(report, input_before)
            candidate = root / 'candidate.patch'
            candidate.write_text(diff)
            result = validate(project, candidate, root / 'validation')
            self.assertTrue(result['accepted'])
            self.assertEqual(result['checks'], dict.fromkeys(
                ['patch_applies', 'build', 'test', 'header_change', 'no_missing'], True))
            after = (project / 'Makefile').read_bytes()
            self.assertEqual(after, before.replace(b'DEPS = main.c unused.h\n',
                b'DEPS = main.c unused.h config.h extra.h\n'))
            self.assertIn(b'main.o: $(DEPS)\n', after)
            self.assertFalse(any(f['type'] == 'MISSING' for f in scan(project)['findings']))
            self.assertIn({'type': 'REDUNDANT', 'target': 'main.o', 'dependency': 'unused.h'},
                          scan(project)['findings'])


if __name__ == '__main__':
    unittest.main()
