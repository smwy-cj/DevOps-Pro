"""Member 2 acceptance: REDUNDANT alone must produce no repair or file change."""
import tempfile
import unittest
from pathlib import Path

from member2_redundant import exercise


class Student241830179Member2Tests(unittest.TestCase):
    def test_redundant_only_is_noop_for_each_declaration_style(self):
        for style in ('direct', 'macro', 'mixed'):
            with self.subTest(style=style), tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / 'evidence'
                result = exercise(out, style)
                self.assertTrue(result['passed'])
                self.assertTrue(all(result['checks'].values()))
                self.assertEqual(result['patch_bytes'], 0)
                self.assertEqual(result['plan_items'], 0)
                self.assertEqual((out / 'Makefile.before').read_bytes(),
                                 (out / 'Makefile.after').read_bytes())


if __name__ == '__main__':
    unittest.main()
