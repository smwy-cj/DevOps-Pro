"""Functional checks for the group's E3 C application; no build performed here."""
from pathlib import Path
import re
import subprocess

value = int(re.search(r'^#define VALUE (\d+)$', Path('config.h').read_text(), re.M)[1])
binary = str((Path('app.exe') if Path('app.exe').exists() else Path('app')).resolve())
for args, expected in [([], str(value)), (['--double'], str(2 * value))]:
    result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result
    assert result.stdout.strip() == expected, (result.stdout, expected)
result = subprocess.run([binary, '--invalid'], capture_output=True, text=True, timeout=10)
assert result.returncode == 2 and 'usage:' in result.stderr, result
print('3 functional cases passed')
