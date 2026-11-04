#!/usr/bin/env bash
# Run from a Linux server; keep a fresh evidence root for every invocation.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "$(uname -s)" == Linux ]] || { echo 'Run on the Linux server'; exit 1; }
[[ "$(git branch --show-current)" == student/241830179/e8-e10 ]] || { echo 'Wrong branch'; exit 1; }
[[ "$(git config --local user.name)" == 241830179 ]] || { echo 'Set local git user.name to 241830179'; exit 1; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="work/241830179-${stamp}-$$"
mkdir -p "$out/logs"
echo "EVIDENCE_ROOT=$out"
run_logged() {
  local label="$1"; shift
  local code
  set +e
  "$@" 2>&1 | tee "$out/logs/$label.log"
  code=${PIPESTATUS[0]}
  set -e
  printf '%s\n' "$code" > "$out/logs/$label.exit-code.txt"
  return "$code"
}
git rev-parse HEAD > "$out/source-commit.txt"
git status --short > "$out/source-status.txt"
git diff --binary HEAD > "$out/source-changes.patch"
python3 --version > "$out/python-version.txt"
docker --version > "$out/docker-version.txt"
run_logged build python3 run_lab.py build
docker image inspect course-e8e10:241830179 > "$out/image-inspect.json"
for stage in e8 e9 e10; do
  run_logged "$stage" python3 run_lab.py "$stage" --track B --out "$out/B-$stage"
done
container=(docker run --rm --network none --cap-add SYS_PTRACE --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/course" -w /course course-e8e10:241830179)
run_logged member2 "${container[@]}" python3 labs/e8e10/member2_redundant.py --out "/course/$out/B-member2-e8"
run_logged unit-tests "${container[@]}" python3 -m unittest discover -s labs/e8e10 -p 'test_*.py' -v
echo "ALL_PASSED: $out"
