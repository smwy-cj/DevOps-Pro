"""Independent fresh-checkout replay of the produced patch; run by the student."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from pipeline import artifact, command, full, save, snapshot
from real_project import Project


def reverify(request, evidence, out):
    if out.exists():
        raise ValueError('Use a new revalidation directory')
    out.mkdir(parents=True)
    verdict = {'status': 'RUNNING', 'checks': {}}
    try:
        result = json.loads((evidence / 'result.json').read_text(encoding='utf-8'))
        if result['status'] != 'SUCCEEDED' or result['target_commit'] != request['target']:
            raise ValueError('E12 did not succeed for the requested target')
        patchfile = evidence / 'candidate.patch'
        descriptor = next(a for a in result['artifacts'] if a['uri'].endswith('/candidate.patch'))
        if (hashlib.sha256(patchfile.read_bytes()).hexdigest() != descriptor['sha256']
                or patchfile.stat().st_size != descriptor['bytes']):
            raise ValueError('Patch integrity mismatch')
        verdict['checks']['patch_integrity'] = True
        adapter = Project(request['project'])
        project = out / 'project'
        sha = snapshot(Path(request['repo']), request['target'], project, out / 'logs', adapter)
        verdict['target_commit'] = sha
        checked = adapter.validate(project, patchfile, out / 'validation')
        if not checked['accepted']:
            raise ValueError('Fresh-copy validation failed: ' + str(checked))
        verdict['checks']['fresh_checkout_build_tests_and_header_rebuild'] = True
        final = full(project, out / 'full-check', adapter)
        if any(f['type'] == 'MISSING' for f in final['findings']):
            raise ValueError('Full recheck still has missing dependencies')
        verdict['checks']['no_missing_in_full_recheck'] = True
        verdict['status'] = 'SUCCEEDED'
    except (ValueError, OSError, KeyError, StopIteration, subprocess.TimeoutExpired) as exc:
        verdict.update(status='FAILED', error=str(exc))
    save(out / 'reverification.json', verdict)
    return verdict


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--request', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    result = reverify(json.loads(args.request.read_text(encoding='utf-8')), args.evidence.resolve(), args.out.resolve())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'SUCCEEDED' else 1)
