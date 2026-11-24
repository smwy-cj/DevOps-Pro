"""Link preserved task evidence and verify its recorded content hashes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root):
    rows = []
    for name in ('normal-20261124-104407', 'down-20261124-104838', 'recovered-20261124-105020'):
        folder = root / 'work/microservice-runs' / name
        result_path = folder / 'result.json'
        result = json.loads(result_path.read_text(encoding='utf-8'))
        record = json.loads((root / 'work/microservice-observer' / (name + '.json')).read_text(encoding='utf-8'))
        checks = {'result_sha256': digest(result_path) == record['result_sha256'],
                  'job_id': result['job_id'] == record['job_id'],
                  'trace_id': result['trace_id'] == record['trace_id'],
                  'status': result['status'] == record['result_status']}
        artifacts = [entry for entry in result['artifacts'] if (folder / entry['uri']).is_file()]
        omitted = [entry['uri'] for entry in result['artifacts'] if not (folder / entry['uri']).is_file()]
        checks['omissions_are_git_metadata_only'] = all('.git' in Path(name).parts for name in omitted)
        checks['available_artifact_hashes'] = all(digest(folder / entry['uri']) == entry['sha256'] for entry in artifacts)
        rows.append({'case': name, 'job_id': result['job_id'], 'trace_id': result['trace_id'],
                     'status': result['status'], 'error': result.get('error'),
                     'input_unchanged': result['input_unchanged'], 'checks': checks,
                     'result': result_path.relative_to(root).as_posix(),
                     'console': 'work/microservice-runs/' + name + '.console.log',
                     'observer': 'work/microservice-observer/' + name + '.json',
                     'completed_stages': [stage['name'] for stage in result['stages']],
                     'available_artifacts_checked': len(artifacts),
                     'omitted_git_metadata': omitted,
                     'artifact_entries_total': len(result['artifacts'])})
    metrics = json.loads((root / 'echecker-up-range.json').read_text())
    transitions = []
    for series in metrics['data']['result']:
        for timestamp, value in series['values']:
            if not transitions or transitions[-1]['value'] != value:
                transitions.append({'time_utc': datetime.fromtimestamp(timestamp, timezone.utc).isoformat(),
                                    'value': value})
    return {'historical_cases': rows, 'echecker_up_transitions': transitions,
            'shared_status_unchanged': (root / 'shared-status-before.txt').read_bytes() == (root / 'shared-status-after.txt').read_bytes(),
            'shared_extension_unchanged': (root / 'shared-extension-before.sha256').read_bytes() == (root / 'shared-extension-after.sha256').read_bytes(),
            'passed': all(all(row['checks'].values()) for row in rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.root)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
