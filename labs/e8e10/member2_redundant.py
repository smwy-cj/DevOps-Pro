"""Student 241830179: real REDUNDANT-only input and auditable no-op evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from lab import commit, fixture, patch, save, scan


def exercise(output, style='direct'):
    output = Path(output)
    if output.exists():
        raise ValueError('OUTPUT_MUST_BE_NEW')
    output.mkdir(parents=True)
    project = output / 'project'
    fixture(project, style)
    makefile = project / 'Makefile'
    text = makefile.read_text()
    # Input preparation: remove the missing edge, retaining the redundant edge.
    old = {'direct': 'main.o: main.c unused.h',
           'macro': 'DEPS = main.c unused.h',
           'mixed': 'main.o: main.c $(HEADERS)'}[style]
    if text.count(old) != 1:
        raise ValueError('FIXTURE_CHANGED')
    makefile.write_text(text.replace(old, old + ' config.h'))
    commit(project, 'member2 REDUNDANT-only input')
    report = scan(project)
    save(output / 'report.json', report)
    before = makefile.read_bytes()
    (output / 'Makefile.before').write_bytes(before)
    diff, plan = patch(project, report)
    after = makefile.read_bytes()
    (output / 'Makefile.after').write_bytes(after)
    (output / 'candidate.patch').write_text(diff, encoding='utf-8')
    save(output / 'patch-plan.json', plan)
    expected = [{'type': 'REDUNDANT', 'target': 'main.o', 'dependency': 'unused.h'}]
    checks = {
        'exact_redundant_only_input': report['findings'] == expected,
        'empty_patch': diff == '',
        'empty_plan': plan == [],
        'makefile_bytes_unchanged': before == after,
        'redundant_edge_retained': 'unused.h' in scan(project)['declared']['main.o'],
    }
    result = {
        'student_id': '241830179', 'stage': 'E8', 'track': 'B',
        'style': style, 'fixture_commit': report['commit'],
        'checks': checks, 'passed': all(checks.values()),
        'before_sha256': hashlib.sha256(before).hexdigest(),
        'after_sha256': hashlib.sha256(after).hexdigest(),
        'patch_bytes': (output / 'candidate.patch').stat().st_size,
        'plan_items': len(plan),
    }
    save(output / 'verification.json', result)
    if not result['passed']:
        raise ValueError('MEMBER2_CHECK_FAILED ' + json.dumps(checks))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error('Use a fresh output directory')
    out.mkdir(parents=True)
    results = [exercise(out / style, style) for style in ('direct', 'macro', 'mixed')]
    save(out / 'summary.json', {'student_id': '241830179',
                              'passed': all(r['passed'] for r in results),
                              'styles': results})
    print('MEMBER2_PASSED', out)


if __name__ == '__main__':
    main()
