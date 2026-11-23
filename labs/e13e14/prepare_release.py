"""Restore the E13-exchanged Git revisions and unchanged candidate inputs for E14."""
import hashlib
import json
from pathlib import Path
import shutil
import stat
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / 'labs/e13e14/inputs'
OUTPUT = ROOT / 'data/e14-release'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *map(str, args)], cwd=cwd, text=True).strip()


def prepare():
    if OUTPUT.exists():
        raise ValueError('E14 input directory already exists; preserve existing inputs')
    manifest = json.loads((INPUTS / 'sources.json').read_text())
    assert digest(INPUTS / 'a06-project.bundle') == manifest['a06_bundle_sha256']
    assert digest(INPUTS / 'e13-upstream-student.zip') == manifest['teacher_zip_sha256']
    OUTPUT.mkdir(parents=True)
    records = []
    for item in manifest['projects']:
        group = item['group'].lower()
        folder = OUTPUT / group
        folder.mkdir()
        source = INPUTS / 'a06-project.bundle' if group == 'a06' else ROOT
        repo = folder / 'repo'
        git('clone', '--no-hardlinks', '--no-checkout', source, repo)
        for revision in (item['base'], item['target']):
            assert git('-C', repo, 'rev-parse', '--verify', revision + '^{commit}') == revision
        git('-C', repo, 'checkout', '--detach', item['target'])
        candidate = folder / 'candidate.Dockerfile'
        shutil.copy2(INPUTS / item['candidate'], candidate)
        assert digest(candidate) == item['candidate_sha256']
        request = {k: item[k] for k in ('base', 'target', 'project', 'candidate_sha256', 'expected_output')}
        request.update(mode='e12', repo='/course/' + repo.relative_to(ROOT).as_posix(),
                       candidate='/course/' + candidate.relative_to(ROOT).as_posix(),
                       build_timeout=600)
        path = folder / 'request.json'
        path.write_text(json.dumps(request, indent=2) + '\n')
        records.append({**item, 'request': path.relative_to(ROOT).as_posix()})
    teacher = ROOT / 'data/e14-upstream'
    if teacher.exists():
        raise ValueError('Teacher project directory already exists')
    teacher.mkdir()
    with ZipFile(INPUTS / 'e13-upstream-student.zip') as z:
        for item in z.infolist():
            target = (teacher / item.filename).resolve()
            if not target.is_relative_to(teacher.resolve()) or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Unsafe teacher archive member')
        z.extractall(teacher)
    for name in ('H1-jsmn', 'H2-inih', 'H3-tiny-aes'):
        matches = list(teacher.rglob(name + '/repo'))
        if len(matches) != 1:
            raise ValueError('Expected one teacher repository for ' + name)
        repo = matches[0]
        candidate = repo.parent / 'candidate.Dockerfile'
        request = {'mode': 'e12', 'repo': '/course/' + repo.relative_to(ROOT).as_posix(),
                   'base': git('-C', repo, 'rev-parse', 'HEAD^'),
                   'target': git('-C', repo, 'rev-parse', 'HEAD'),
                   'candidate': '/course/' + candidate.relative_to(ROOT).as_posix(),
                   'candidate_sha256': digest(candidate),
                   'expected_output': '1', 'build_timeout': 600}
        path = OUTPUT / (name + '.json')
        path.write_text(json.dumps(request, indent=2) + '\n')
    (OUTPUT / 'preparation.json').write_text(json.dumps({
        'tool_commit': git('rev-parse', 'HEAD'), 'projects': records,
        'source_manifest_sha256': digest(INPUTS / 'sources.json')
    }, ensure_ascii=False, indent=2) + '\n')
    print('E14_INPUTS_READY', OUTPUT)


if __name__ == '__main__':
    prepare()
