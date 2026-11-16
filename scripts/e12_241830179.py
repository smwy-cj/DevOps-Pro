"""Student handoff: prepare, execute, independently reverify and archive evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen, build_opener, ProxyHandler
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'students/241830179/e12'
DATA = ROOT / 'data/241830179-e12'
REQUEST = 'data/241830179-e12/request.json'
OUT = 'work/241830179-e12'
RECHECK = 'work/241830179-e12-reverify'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def command(argv):
    subprocess.run(argv, cwd=ROOT, check=True)


def output(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True).strip()


def prepare():
    if DATA.exists():
        raise ValueError('data/241830179-e12 already exists; preserve it or use a fresh clone')
    request = load(DOCS / 'request.json')
    for revision in (request['base'], request['target']):
        if output(['git', 'rev-parse', '--verify', revision + '^{commit}']) != revision:
            raise ValueError('Project revision missing')
    DATA.mkdir(parents=True)
    command(['git', 'clone', '--no-hardlinks', '--no-checkout', str(ROOT), str(DATA / 'repo')])
    shutil.copyfile(DOCS / 'candidate.Dockerfile', DATA / 'candidate.Dockerfile')
    request['candidate_sha256'] = hashlib.sha256((DATA / 'candidate.Dockerfile').read_bytes()).hexdigest()
    save(DATA / 'request.json', request)
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    save(DATA / 'api-request.json', {'idempotency_key': '241830179-e12-' + digest[:24], 'input': request})
    save(DATA / 'preparation.json', {
        'student_id': '241830179', 'tool_commit': output(['git', 'rev-parse', 'HEAD']),
        'tool_worktree_status': output(['git', 'status', '--porcelain']),
        'project': load(DOCS / 'project.json'),
        'status': 'PREPARED_NOT_EXECUTED',
        'candidate_sha256': hashlib.sha256((DATA / 'candidate.Dockerfile').read_bytes()).hexdigest()})
    print('Prepared ' + str(DATA))


def check_manifest(evidence):
    result = load(evidence / 'result.json')
    prefix = 'artifact://' + result['job_id'] + '/'
    for item in result['artifacts']:
        if not item['uri'].startswith(prefix):
            raise ValueError('Invalid artifact URI')
        path = (evidence / item['uri'][len(prefix):]).resolve()
        if not path.is_relative_to(evidence.resolve()) or not path.is_file():
            raise ValueError('Artifact missing or outside evidence: ' + item['uri'])
        if path.stat().st_size != item['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('Artifact integrity mismatch: ' + item['uri'])
    return result


def collect():
    evidence, recheck = ROOT / OUT, ROOT / RECHECK
    result = check_manifest(evidence)
    expected = load(DOCS / 'request.json')
    if (result.get('base_commit'), result.get('target_commit')) != (expected['base'], expected['target']):
        raise ValueError('Result uses different project commits')
    replay = load(recheck / 'reverification.json') if (recheck / 'reverification.json').is_file() else {'status': 'NOT_RUN'}
    accepted = result['status'] == replay['status'] == 'SUCCEEDED'
    delivery = ROOT / 'work/241830179-e12-delivery'
    delivery.mkdir(parents=True, exist_ok=True)
    save(delivery / 'delivery-summary.json', {'student_id': '241830179',
         'status': 'VERIFIED' if accepted else 'INCOMPLETE', 'result_status': result['status'],
         'reverification_status': replay['status'], 'artifact_integrity': 'PASSED',
         'project': load(DOCS / 'project.json'), 'tool_commit': output(['git', 'rev-parse', 'HEAD']),
         'tool_worktree_status': output(['git', 'status', '--porcelain'])})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    archive = delivery / ('241830179-e12-' + stamp + '.tar.gz')
    if archive.exists():
        raise ValueError('Archive exists; do not overwrite')
    with tarfile.open(archive, 'w:gz') as bundle:
        for directory in (evidence, recheck, DATA, DOCS):
            if directory.is_dir():
                for path in sorted(directory.rglob('*')):
                    if path.is_file() and not path.is_symlink() and '.git' not in path.parts:
                        bundle.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
        bundle.add(delivery / 'delivery-summary.json', arcname='delivery-summary.json')
    print('ARCHIVE=' + str(archive))
    print('SHA256=' + hashlib.sha256(archive.read_bytes()).hexdigest())
    print('STATUS=' + ('VERIFIED' if accepted else 'INCOMPLETE'))


def api(url):
    # This client intentionally connects only to the student's local service.
    if not (url.startswith('http://127.0.0.1:') or url.startswith('http://localhost:')):
        raise ValueError('Use a loopback API URL, optionally through an SSH tunnel')
    evidence = ROOT / OUT
    if evidence.exists():
        raise ValueError('Evidence directory exists; use a fresh clone for another run')
    evidence.mkdir(parents=True)
    opener = build_opener(ProxyHandler({}))
    def get(path):
        with opener.open(url.rstrip('/') + path, timeout=30) as response:
            return response.read()
    body = load(DATA / 'api-request.json')
    save(evidence / 'submitted-api-request.json', body)
    request = Request(url.rstrip('/') + '/v1/jobs', data=json.dumps(body).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with opener.open(request, timeout=30) as response:
        submitted = json.loads(response.read())
    save(evidence / 'submit-response.json', submitted)
    job = '/v1/jobs/' + submitted['job_id']
    deadline = time.monotonic() + 2400
    while True:
        state = json.loads(get(job))
        if state['status'] not in ('QUEUED', 'RUNNING'):
            break
        if time.monotonic() > deadline:
            save(evidence / 'last-state.json', state)
            raise ValueError('Client polling timed out; job may still be running')
        time.sleep(3)
    save(evidence / 'api-state.json', state)
    result = json.loads(get(job + '/artifacts'))
    prefix = 'artifact://' + submitted['job_id'] + '/'
    for item in result['artifacts']:
        if not item['uri'].startswith(prefix):
            raise ValueError('Invalid artifact URI')
        name = item['uri'][len(prefix):]
        path = (evidence / name).resolve()
        if not path.is_relative_to(evidence):
            raise ValueError('Invalid artifact path')
        data = get(job + '/files/' + quote(name, safe='/'))
        if hashlib.sha256(data).hexdigest() != item['sha256'] or len(data) != item['bytes']:
            raise ValueError('Downloaded artifact hash or size mismatch')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    save(evidence / 'result.json', result)
    print('JOB=' + submitted['job_id'] + ' STATUS=' + result['status'])
    if result['status'] != 'SUCCEEDED':
        raise SystemExit(1)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'build', 'test', 'run', 'serve', 'api', 'reverify', 'collect'))
    p.add_argument('--url', default='http://127.0.0.1:8080')
    args = p.parse_args()
    if args.action == 'prepare':
        prepare()
    elif args.action == 'collect':
        collect()
    elif args.action == 'api':
        api(args.url)
    else:
        if os.name != 'posix':
            raise ValueError('Use Linux/WSL2 or the Linux server for this step')
        if output(['git', 'config', '--local', 'user.name']) != '241830179':
            raise ValueError('Set git config --local user.name 241830179 first')
        argv = [sys.executable, 'run_e11e12.py', args.action]
        if args.action in ('run', 'reverify'):
            if not (DATA / 'request.json').is_file():
                raise ValueError('Run prepare first')
            argv += ['--request', REQUEST, '--out', RECHECK if args.action == 'reverify' else OUT]
        if args.action == 'reverify':
            check_manifest(ROOT / OUT)
            argv += ['--evidence', OUT]
        command(argv)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
