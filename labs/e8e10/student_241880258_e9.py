"""Reproduce member 3's duplicate-MD case and retain E9 evidence."""
import argparse
import hashlib
import shutil
from pathlib import Path
from lab import fixture, patch, run, save, scan


def verify(out):
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for style in ['direct', 'macro', 'mixed']:
        project = out / style
        fixture(project, style)
        report = scan(project)
        missing = next(f for f in report['findings'] if f['type'] == 'MISSING')
        report['findings'].append(dict(missing))
        save(out / (style + '-input.json'), report)
        before = (project / 'Makefile').read_bytes()
        (out / (style + '-before.Makefile')).write_bytes(before)
        diff, plan = patch(project, report)
        candidate = out / (style + '.patch')
        candidate.write_text(diff)
        save(out / (style + '-plan.json'), plan)
        after = (project / 'Makefile').read_bytes()
        (out / (style + '-after-generation.Makefile')).write_bytes(after)
        demo = out / 'apply-demo' / style
        shutil.copytree(project, demo)
        run(['git', 'apply', '--check', str(candidate.resolve())], demo)
        run(['git', 'apply', str(candidate.resolve())], demo)
        applied = (demo / 'Makefile').read_text()
        (out / (style + '-build.log')).write_text(run(['make', 'app'], demo))
        output = run(['./app'], demo).strip()
        recheck = scan(demo)
        save(out / (style + '-recheck.json'), recheck)
        expected = [{'target': 'main.o', 'dependency': 'config.h', 'style': style}]
        row = {
            'style': style, 'input_missing_count': 2,
            'applied_config_h_count': applied.split().count('config.h'),
            'plan_count': len(plan), 'plan_matches_expected': plan == expected,
            'source_unchanged': before == after == (project / 'Makefile').read_bytes(),
            'source_before_sha256': hashlib.sha256(before).hexdigest(),
            'source_after_sha256': hashlib.sha256(after).hexdigest(),
            'patch_applies': True, 'output': output,
            'no_missing': not any(f['type'] == 'MISSING' for f in recheck['findings']),
            'recipes_unchanged': [x for x in before.decode().splitlines() if x.startswith('\t')] == [x for x in applied.splitlines() if x.startswith('\t')],
            'redundant_preserved': 'unused.h' in applied,
        }
        row['passed'] = (row['applied_config_h_count'] == 1 and row['plan_matches_expected']
                         and row['source_unchanged'] and row['no_missing'] and output == '1'
                         and row['recipes_unchanged'] and row['redundant_preserved'])
        rows.append(row)
        print(row, flush=True)
    save(out / 'results.json', rows)
    passed = all(row['passed'] for row in rows)
    save(out / 'gate.json', {'student_id': '241880258', 'task': 'E9 duplicate MD', 'passed': passed, 'rows': len(rows)})
    (out / '结论.txt').write_text('重复 MD 去重：' + ('三种风格全部通过' if passed else '未通过；详见 results.json') + '\n')
    assert passed, 'DUPLICATE_MD_NOT_DEDUPLICATED'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    verify(parser.parse_args().out.resolve())
