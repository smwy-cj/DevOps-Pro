#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: verify-patch.sh <a06-repository-path> <patch-path>" >&2
  exit 2
fi

source_repository="$1"
patch_file="$2"
repair_workdir="$(mktemp -d /tmp/e2-repair-XXXXXX)"

cleanup_repair_workdir() {
  case "$repair_workdir" in
    /tmp/e2-repair-*) rm -rf -- "$repair_workdir" ;;
    *) echo "refusing to remove unexpected path: $repair_workdir" >&2 ;;
  esac
}
trap cleanup_repair_workdir EXIT

git clone -q "$source_repository" "$repair_workdir/repo"
cd "$repair_workdir/repo"
git checkout -q f104b5bc7f4044a119d1b46aab5d64e70cf89de8
git apply --check "$patch_file"
git apply "$patch_file"

cd contracts/fixtures/missing-dependency

echo "ENVIRONMENT"
uname -m
make --version | head -n 1
cc --version | head -n 1

echo "STEP 1: clean build with VALUE=1"
make clean
make
initial_output="$(./app)"
echo "initial_output=$initial_output"

echo "STEP 2: change config.h to VALUE=2, then run ordinary make"
sed -i "s/#define VALUE 1/#define VALUE 2/" config.h
make
incremental_output="$(./app)"
echo "incremental_output=$incremental_output"

echo "STEP 3: clean build from the same modified source"
make clean
make
clean_output="$(./app)"
echo "clean_output=$clean_output"

test "$initial_output" = "1"
test "$incremental_output" = "2"
test "$clean_output" = "2"

echo "RESULT: PASS - config.h now rebuilds main.o during ordinary make"
