"""E11-B MDFixer macro extension: two missing headers in DEPS."""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'e8e10'))
from lab import buildchecker, commit, fixture, patch, run, save, scan, validate


def prepare(project):
    fixture(project, 'macro')
    base = run(['git', 'rev-parse', 'HEAD'], project).strip()
    main = project / 'main.c'
    main.write_text('#include "extra.h"\n' + main.read_text())
    target = commit(project, 'E11-B macro: include extra.h')
    return base, target, scan(project)


def verify(out):
    out.mkdir(parents=True, exist_ok=False)
    project = out / 'project'
    base, target, report = prepare(project)
    save(out / 'dataset.json', {'source': 'course E11 prepare scenario adapted to macro style',
                               'base_commit': base, 'target_commit': target})
    save(out / 'fixed-md.json', {'schema_version': 'e11e12-1', 'kind': 'fixed-md',
                               'status': 'SUCCEEDED', 'commit': target, 'data': report})
    before = (project / 'Makefile').read_bytes()
    (out / 'before.Makefile').write_bytes(before)
    diff, plan = patch(project, report)
    candidate = out / 'candidate.patch'
    candidate.write_text(diff)
    save(out / 'repair-plan.json', plan)
    expected = [{'target': 'main.o', 'dependency': name, 'style': 'macro'}
                for name in ['config.h', 'extra.h']]
    assert plan == expected
    assert report['commit'] == target
    assert before == (project / 'Makefile').read_bytes()
    assert '+DEPS = main.c unused.h config.h extra.h\n' in diff
    assert '+main.o:' not in diff and '-main.o:' not in diff
    run(['git', 'apply', '--check', str(candidate.resolve())], project)
    verdict = validate(project, candidate, out / 'validation')
    assert verdict['accepted'] and all(verdict['checks'].values())
    after = (project / 'Makefile').read_bytes()
    (out / 'after.Makefile').write_bytes(after)
    assert after == before.replace(b'DEPS = main.c unused.h\n',
                                  b'DEPS = main.c unused.h config.h extra.h\n')
    assert b'main.o: $(DEPS)\n' in after
    assert (project / 'config.h').read_text() == '#define VALUE 1\n'
    buildchecker(project, out / 'final-buildchecker')
    findings = scan(project)['findings']
    assert not any(f['type'] == 'MISSING' for f in findings)
    result = {'student_id': '241880258', 'task': 'E11-B macro', 'passed': True,
              'base_commit': base, 'target_commit': target,
              'deps': ['main.c', 'unused.h', 'config.h', 'extra.h'],
              'main_rule': 'main.o: $(DEPS)', 'plan_count': len(plan),
              'source_unchanged_during_generation': True,
              'accepted': verdict['accepted'], 'checks': verdict['checks'],
              'only_deps_definition_changed': True, 'findings': findings,
              'before_sha256': hashlib.sha256(before).hexdigest(),
              'after_sha256': hashlib.sha256(after).hexdigest()}
    save(out / 'result.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    verify(parser.parse_args().out.resolve())
