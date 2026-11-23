"""Run and audit E14's actual four-container acceptance on Linux."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'work/e14-release'
ASSETS = ROOT / 'work/e14-release-assets'
STAGES = ['draft', 'full-check', 'incremental-check', 'repair', 'recheck']
COMPOSE = ['docker', 'compose', '-f', 'labs/e13e14/compose.yaml', '-p', 'e14-release-ci']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def read(path):
    return json.loads(path.read_text())


def run(argv, log, timeout=1800):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as stream:
        result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise ValueError('Command failed: ' + repr(argv) + '; see ' + str(log))


def capture(argv):
    return subprocess.check_output(argv, cwd=ROOT, text=True).strip()


def verify(folder, composed=True, expected='SUCCEEDED'):
    result = read(folder / 'result.json')
    assert result['status'] == expected, result.get('error')
    request = read(folder / 'request.json')
    assert result['base_commit'] == request['base']
    assert result['target_commit'] == request['target']
    prefix = '' if composed else 'artifact://' + result['job_id'] + '/'
    verified = 0
    for item in result['artifacts']:
        assert item['uri'].startswith(prefix)
        path = (folder / item['uri'][len(prefix):]).resolve()
        assert path.is_relative_to(folder.resolve()) and path.is_file(), item['uri']
        assert sha(path) == item['sha256'] and path.stat().st_size == item['bytes'], item['uri']
        verified += 1
    if expected == 'SUCCEEDED':
        assert [s['name'] for s in result['stages']] == STAGES
        for name in STAGES:
            stage = read(folder / (name + '.json'))
            assert stage['status'] == 'SUCCEEDED'
            assert stage['job_id'] == result['job_id'] and stage['trace_id'] == result['trace_id']
            assert stage['commit'] == result['target_commit'] or name == 'full-check'
        if composed:
            repair = read(folder / 'repair.json')['data']
            assert repair['input_report']['sha256'] == sha(folder / 'incremental/incremental-check.json')
            assert repair['input_report']['commit'] == result['target_commit']
            assert repair['validation']['accepted'] and all(repair['validation']['checks'].values())
            findings = read(folder / 'recheck.json')['data']['result']['result']['findings']
            assert result['input_unchanged']
        else:
            repair = read(folder / 'repair.json')['data']
            assert repair['input_report']['sha256'] == sha(folder / 'incremental-check.json')
            assert read(folder / 'validation/validation.json')['accepted']
            findings = read(folder / 'recheck.json')['data']['findings']
        assert not any(f['type'] == 'MISSING' for f in findings)
    return {'directory': folder.relative_to(ROOT).as_posix(), 'status': result['status'],
            'job_id': result['job_id'], 'trace_id': result['trace_id'],
            'base': result['base_commit'], 'target': result['target_commit'],
            'verified_artifacts': verified, 'result_sha256': sha(folder / 'result.json')}


def compose_case(name, request_path):
    folder = WORK / name
    run(['python3', 'labs/e13e14/orchestrate.py', '--request', str(request_path),
         '--out', str(folder)], WORK / (name + '.console.log'))
    return verify(folder)


def processes_for(output):
    script = (
        'import json,pathlib; rows=[]\n'
        'for p in pathlib.Path("/proc").glob("[0-9]*/cmdline"):\n'
        ' try: a=[x.decode(errors="replace") for x in p.read_bytes().split(bytes([0])) if x]\n'
        ' except OSError: continue\n'
        ' if len(a)>1 and pathlib.Path(a[0]).name=="docker" and a[1]=="build"'
        ' and any(' + repr(output) + ' in x for x in a): rows.append(a)\n'
        'print(json.dumps(rows))\n')
    return json.loads(capture([*COMPOSE, 'exec', '-T', 'draft', 'python3', '-c', script]))


def container_inventory():
    ids = capture([*COMPOSE, 'ps', '-q']).splitlines()
    assert len(ids) == 4
    rows = json.loads(capture(['docker', 'inspect', *ids]))
    selected = []
    for row in rows:
        assert row['State']['Health']['Status'] == 'healthy'
        ports = row['NetworkSettings']['Ports'].get('8080/tcp', [])
        assert ports and all(x['HostIp'] == '127.0.0.1' for x in ports)
        selected.append({'role': row['Config']['Labels']['com.docker.compose.service'],
                         'id': row['Id'], 'image': row['Image'], 'user': row['Config']['User'],
                         'group_add': row['HostConfig']['GroupAdd'], 'health': row['State']['Health'],
                         'ports': ports, 'mounts': row['Mounts']})
    assert {r['role'] for r in selected} == {'draft', 'buildchecker', 'echecker', 'mdfixer'}
    return selected


def log_audit(records, failure):
    content = capture([*COMPOSE, 'logs', '--no-color'])
    (WORK / 'four-services.log').write_text(content + '\n')
    events = []
    for line in content.splitlines():
        if '{' not in line:
            continue
        try:
            event = json.loads(line[line.index('{'):])
        except ValueError:
            continue
        if isinstance(event, dict) and 'role' in event and 'job_id' in event:
            events.append(event)
    for name in ('sample', 'a06', 'b06', 'recovery'):
        record = records[name]
        matching = [e for e in events if e['job_id'] == record['job_id']]
        assert {e['role'] for e in matching} == {'draft', 'buildchecker', 'echecker', 'mdfixer'}, (name, matching)
        assert all(e['status'] == 'SUCCEEDED' and e['trace_id'] == record['trace_id'] for e in matching)
    failed = [e for e in events if e['job_id'] == failure['job_id']]
    assert any(e['role'] == 'draft' and e['status'] == 'FAILED' and e['error_code'] == 'TIMEOUT'
               and e['trace_id'] == failure['trace_id'] for e in failed), failed
    save(WORK / 'service-events.json', events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--compose-project', default='e14-release-ci')
    args = parser.parse_args()
    COMPOSE[-1] = args.compose_project
    if platform.system() != 'Linux':
        raise SystemExit('Run in Linux CI or the Linux cloud host with Docker')
    if WORK.exists() or ASSETS.exists():
        raise SystemExit('Preserve existing results; use a fresh checkout for acceptance')
    WORK.mkdir(parents=True)
    ASSETS.mkdir()
    records = {}
    inventory = container_inventory()
    save(WORK / 'containers-before.json', inventory)
    run([*COMPOSE, 'exec', '-T', 'buildchecker', 'cat', '/opt/toolchain.lock'], WORK / 'toolchain.lock')
    records['sample'] = compose_case('sample', ROOT / 'data/integration-sample/e12.json')
    for group in ('a06', 'b06'):
        records[group] = compose_case(group, ROOT / 'data/e14-release' / group / 'request.json')
    faulty = read(ROOT / 'data/e14-release/a06/request.json')
    faulty['build_timeout'] = 0.01
    save(WORK / 'timeout-request.json', faulty)
    failed_folder = WORK / 'timeout'
    with (WORK / 'timeout.console.log').open('w') as log:
        process = subprocess.run(['python3', 'labs/e13e14/orchestrate.py', '--request',
                                  str(WORK / 'timeout-request.json'), '--out', str(failed_folder)],
                                 cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert process.returncode != 0
    failure = verify(failed_folder, expected='FAILED')
    draft = read(failed_folder / 'draft-build/result.json')
    assert draft['status'] == 'TIMED_OUT'
    assert read(failed_folder / 'result.json')['input_unchanged']
    clients = processes_for('/course/' + failed_folder.relative_to(ROOT).as_posix())
    assert clients == [], clients
    save(WORK / 'timeout-client-processes.json', clients)
    (WORK / 'timeout-container-snapshot.txt').write_text(capture(['docker', 'ps', '--no-trunc']) + '\n')
    before_failed = sha(failed_folder / 'result.json')
    records['recovery'] = compose_case('recovery', ROOT / 'data/e14-release/a06/request.json')
    assert records['recovery']['job_id'] != failure['job_id']
    assert records['recovery']['trace_id'] != failure['trace_id']
    assert sha(failed_folder / 'result.json') == before_failed
    save(WORK / 'failure-recovery.json', {
        'passed': True, 'failed': failure, 'recovered': records['recovery'],
        'failed_result_unchanged': True, 'remaining_build_clients': clients,
        'scope': 'Build client process group terminated; running-container snapshot at observation time'})
    for name in ('H1-jsmn', 'H2-inih', 'H3-tiny-aes'):
        folder = WORK / name
        run(['python3', 'run_e11e12.py', 'run', '--request',
             'data/e14-release/' + name + '.json', '--out', folder.relative_to(ROOT).as_posix()],
            WORK / (name + '.console.log'))
        records[name] = verify(folder, composed=False)
    log_audit(records, failure)
    save(WORK / 'containers-after.json', container_inventory())
    service_image = json.loads(capture(['docker', 'image', 'inspect', args.image]))[0]
    images = {service_image['Id']}
    for record in records.values():
        drafted = read(ROOT / record['directory'] / 'draft-build/result.json')
        images.add(drafted['attempts'][-1]['image_id'])
    for index, image in enumerate(sorted(images)):
        argv = ['python3', 'labs/e11e12/environment/scripts/secret_scan.py', '.', '--image', image]
        if image == service_image['Id']:
            argv.append('--history')
        run(argv, WORK / 'image-scans' / (str(index) + '.txt'))
    run(['python3', 'labs/e13e14/scan_runtime_logs.py', str(WORK)], WORK / 'runtime-scan.txt')
    export_images = {service_image['Id']}
    for group in ('a06', 'b06'):
        export_images.add(read(WORK / group / 'draft-build/result.json')['attempts'][-1]['image_id'])
    image_rows = []
    for image in sorted(images):
        data = json.loads(capture(['docker', 'image', 'inspect', image]))[0]
        image_rows.append({k: data[k] for k in ('Id', 'Architecture', 'Os', 'RepoTags', 'RepoDigests')})
    save(ASSETS / 'image-inventory.json', {
        'service_image': service_image['Id'], 'scanned_images': image_rows,
        'exported_images': sorted(export_images), 'platform': 'linux/amd64'})
    archive = ASSETS / 'runtime-images-linux-amd64.tar'
    run(['docker', 'image', 'save', '-o', str(archive), *sorted(export_images)], WORK / 'image-export.log')
    with archive.open('rb') as source, (ASSETS / (archive.name + '.gz')).open('wb') as target:
        with gzip.GzipFile(fileobj=target, mode='wb', mtime=0) as compressed:
            shutil.copyfileobj(source, compressed)
    archive.unlink()
    gate = {'passed': True, 'runtime': 'GitHub Actions Linux runner' if os.environ.get('GITHUB_ACTIONS') else 'Linux Docker host',
            'tool_commit': capture(['git', 'rev-parse', 'HEAD']),
            'ci_run_id': os.environ.get('GITHUB_RUN_ID'), 'records': records, 'failure': failure,
            'service_image': service_image['Id'], 'scanned_image_count': len(images),
            'exported_images': sorted(export_images),
            'a06_acknowledgement': 'PENDING', 'rc_status_at_execution': 'NOT_YET_PUBLISHED'}
    save(WORK / 'release-gate.json', gate)
    shutil.copy2(WORK / 'release-gate.json', ASSETS / 'release-gate.json')

    def filter_tar(item):
        if '.git' in Path(item.name).parts:
            return None
        if any(part == '.env' or (part.startswith('.env.') and part not in ('.env.example', '.env.template'))
               for part in Path(item.name).parts):
            raise ValueError('Unexpected environment file in release evidence: ' + item.name)
        if item.issym() or item.islnk():
            return None
        return item

    with tarfile.open(ASSETS / 'e14-evidence.tar.gz', 'w:gz') as tar:
        for relative in ('work/e14-release', 'data/e14-release', 'data/e14-upstream', 'labs/e13e14/inputs'):
            tar.add(ROOT / relative, arcname=relative, filter=filter_tar)
    with tarfile.open(ASSETS / 'e14-evidence.tar.gz', 'r:gz') as tar:
        for record in [*records.values(), failure]:
            folder = ROOT / record['directory']
            result = read(folder / 'result.json')
            prefix = '' if result['schema_version'] == 'e14-compose-1' else 'artifact://' + result['job_id'] + '/'
            for item in result['artifacts']:
                name = record['directory'] + '/' + item['uri'][len(prefix):]
                member = tar.getmember(name)
                assert member.size == item['bytes']
                with tar.extractfile(member) as stream:
                    assert hashlib.sha256(stream.read()).hexdigest() == item['sha256'], name
    manifest = {'tool_commit': gate['tool_commit'], 'ci_run_id': gate['ci_run_id'], 'files': [
        {'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
        for p in sorted(ASSETS.iterdir()) if p.is_file()]}
    save(ASSETS / 'SHA256SUMS.json', manifest)
    print(json.dumps(gate, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
