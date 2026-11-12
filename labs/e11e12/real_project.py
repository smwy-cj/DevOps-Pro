"""Explicit C/Make project adapter; unsupported rules fail before producing a patch."""
import difflib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import time


def safe_path(value, dot=False):
    if not isinstance(value, str) or (value == '.' and not dot):
        raise ValueError('Invalid project path')
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or '..' in path.parts
            or not re.fullmatch(r'[A-Za-z0-9_./-]+', value) or ':' in value):
        raise ValueError('Unsafe project path: ' + value)
    return value


def run(argv, cwd, log=None):
    if argv[0].startswith('./'):
        argv = [str((Path(cwd) / argv[0]).resolve()), *argv[1:]]
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=120)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise ValueError('COMMAND_FAILED ' + repr(argv) + '\n' + result.stdout + result.stderr)
    return result.stdout


class Project:
    def __init__(self, config):
        self.config = config
        self.subdir = safe_path(config.get('subdirectory', '.'), dot=True)
        self.makefile = safe_path(config.get('makefile', 'Makefile'))
        self.sources = config['object_sources']
        if not self.sources:
            raise ValueError('object_sources must not be empty')
        for target, source in self.sources.items():
            safe_path(target)
            safe_path(source)
            if not target.endswith('.o') or not source.endswith('.c'):
                raise ValueError('Only explicit .o -> .c mappings are supported')
        self.compiler = config.get('compiler', 'gcc')
        self.flags = config.get('flags', ['-O0'])
        for name in ('clean', 'build', 'test'):
            argv = config[name]
            if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
                raise ValueError(name + ' must be a nonempty argument list')
        if Path(config['build'][0]).name.lower().removesuffix('.exe') not in ('make', 'gmake', 'mingw32-make'):
            raise ValueError('Build must use GNU Make')
        self.probe = config['header_probe']
        safe_path(self.probe['path'])
        if self.probe['target'] not in self.sources:
            raise ValueError('Header probe target must be mapped')

    def directory(self, repo):
        root = Path(repo).resolve()
        project = (root / self.subdir).resolve()
        if not project.is_relative_to(root) or not project.is_dir():
            raise ValueError('Project directory missing or outside repository')
        # Git symlinks and submodules require a richer snapshot model.
        if any(p.is_symlink() for p in project.rglob('*')):
            raise ValueError('Symlink projects are unsupported')
        for path in [self.makefile, *self.sources.values(), self.probe['path']]:
            if not (project / path).is_file():
                raise ValueError('Project input missing: ' + path)
        return project

    def database(self, repo):
        from buildchecker.fullcheck import declaration_graph
        project = self.directory(repo)
        result = subprocess.run([self.config['build'][0], '-f', self.makefile, '-qp'],
                                cwd=project, capture_output=True, text=True, encoding='utf-8',
                                errors='replace', env=dict(os.environ, LC_ALL='C', LANG='C'), timeout=120)
        if result.returncode not in (0, 1):
            raise ValueError('MAKE_DATABASE_FAILED\n' + result.stderr)
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'make-db.txt'
            path.write_text(result.stdout, encoding='utf-8')
            graph = declaration_graph(path, project.as_posix())
        if not set(self.sources).issubset(graph):
            raise ValueError('Mapped targets missing from Make database')
        return {t: sorted(graph[t]['dependencies']) for t in self.sources}

    def scan(self, repo, old=None):
        project = self.directory(repo)
        declared = self.database(repo)
        # Conservative invalidation includes complete local C/header/Make contents.
        inputs = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(project.rglob('*')) if p.is_file()
                  and (p.suffix in ('.c', '.h', '.mk') or p == project / self.makefile)}
        key = {'inputs': inputs, 'profile': self.config,
               'compiler': run([self.compiler, '--version'], project).splitlines()[0]}
        reuse = bool(old and old.get('key') == key)
        actual = {}
        for target, source in self.sources.items():
            if reuse:
                actual[target] = old['actual'][target]
            else:
                output = run([self.compiler, *self.flags, '-MM', '-MT', target, source], project)
                deps = shlex.split(output.replace('\\\n', ' ').split(':', 1)[1])
                actual[target] = sorted(set(safe_path(x) for x in deps))
        findings = []
        for target in actual:
            for kind, deps in [('MISSING', set(actual[target]) - set(declared[target])),
                               ('REDUNDANT', set(declared[target]) - set(actual[target]))]:
                findings.extend({'type': kind, 'target': target, 'dependency': d} for d in sorted(deps))
        current = {(f['type'], f['target'], f['dependency']) for f in findings}
        previous = {(f['type'], f['target'], f['dependency']) for f in old['findings']} if old else set()
        return {'schema_version': 'e8e10-1', 'profile': 'EXPLICIT_C_MAKE_PROJECT_V1',
                'commit': run(['git', 'rev-parse', 'HEAD'], repo).strip(), 'key': key,
                'actual': actual, 'declared': declared, 'findings': findings,
                'added': sorted(current - previous), 'resolved': sorted(previous - current),
                'reused': sorted(actual) if reuse else [], 'refreshed': [] if reuse else sorted(actual)}

    def patch(self, repo, report):
        if report['commit'] != run(['git', 'rev-parse', 'HEAD'], repo).strip():
            raise ValueError('STALE_REPORT')
        project = self.directory(repo)
        original = (project / self.makefile).read_text(encoding='utf-8')
        changed = original
        edits = []
        seen = set()
        for finding in report['findings']:
            if finding['type'] != 'MISSING':
                continue
            target, dependency = finding['target'], safe_path(finding['dependency'])
            if target not in self.sources:
                raise ValueError('UNSUPPORTED_TARGET ' + target)
            if (target, dependency) in seen:
                continue
            if not (project / dependency).is_file():
                raise ValueError('MISSING_INPUT ' + dependency)
            matches = list(re.finditer(r'^' + re.escape(target) + r':([^\n]*)$', changed, re.M))
            if len(matches) != 1 or any(x in matches[0][1] for x in ('\\', ';', '|', ':', '#')):
                raise ValueError('UNSUPPORTED_RULE ' + target)
            match = matches[0]
            changed = changed[:match.end()] + ' ' + dependency + changed[match.end():]
            seen.add((target, dependency))
            edits.append({'target': target, 'dependency': dependency, 'style': 'explicit-addition'})
        relative = (PurePosixPath(self.subdir) / self.makefile).as_posix()
        diff = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                           fromfile='a/' + relative, tofile='b/' + relative))
        return diff, edits

    def validate(self, repo, patchfile, evidence):
        evidence.mkdir(parents=True)
        project = self.directory(repo)
        before = (project / self.makefile).read_bytes()
        sandbox = evidence / 'sandbox'
        shutil.copytree(repo, sandbox, ignore=shutil.ignore_patterns('.git', '*.o', '__pycache__'))
        checks, error = {}, None
        try:
            # git apply works outside a repository; do not inherit a containing worktree.
            run(['git', 'init', '-q', str(sandbox)], evidence)
            run(['git', 'apply', '--check', str(patchfile.resolve())], sandbox, evidence / 'apply-check.log')
            run(['git', 'apply', str(patchfile.resolve())], sandbox, evidence / 'apply.log')
            checks['patch_applies'] = True
            work = self.directory(sandbox)
            run(self.config['clean'], work, evidence / 'clean.log')
            run(self.config['build'], work, evidence / 'build.log')
            checks['build'] = True
            run(self.config['test'], work, evidence / 'test.log')
            checks['test'] = True
            target = work / self.probe['target']
            old_mtime = target.stat().st_mtime_ns
            time.sleep(1.1)
            header = work / self.probe['path']
            replacement = self.probe.get('replace')
            if replacement:
                data = header.read_bytes()
                old, new = replacement['old'].encode(), replacement['new'].encode()
                if not old or old == new or data.count(old) != 1:
                    raise ValueError('HEADER_PROBE_REPLACEMENT must match exactly once and change content')
                header.write_bytes(data.replace(old, new))
            else:
                header.write_bytes(header.read_bytes() + b'\n/* E12 dependency rebuild probe */\n')
            run(self.config['build'], work, evidence / 'incremental.log')
            checks['header_change'] = target.stat().st_mtime_ns > old_mtime
            run(self.config['test'], work, evidence / 'incremental-test.log')
            checks['incremental_test'] = True
        except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)
        accepted = len(checks) == 5 and all(checks.values()) and error is None
        # Copy only the validated Makefile; header probe never leaves the sandbox.
        if accepted:
            (project / self.makefile).write_bytes((self.directory(sandbox) / self.makefile).read_bytes())
        unchanged = (project / self.makefile).read_bytes() == before
        verdict = {'accepted': accepted, 'checks': checks, 'error': error,
                   'source_unchanged': unchanged, 'rollback': not accepted and unchanged}
        (evidence / 'validation.json').write_text(json.dumps(verdict, indent=2) + '\n', encoding='utf-8')
        return verdict
