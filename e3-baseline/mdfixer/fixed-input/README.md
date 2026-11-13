# B06 C application maintained for E12

Source: `smwy-cj/DevOps-Pro`, `e3/b06-test-baseline`, original project commit
`be73686c6a9fdbb7c4d3eadb45779233afa33083`, directory
`e3-baseline/mdfixer/fixed-input`. The original Makefile, config header and C
program were restored byte for byte as the new acceptance baseline.

The application prints the configured integer. The E12 target adds `--double`,
rejects unknown arguments and adds three executable functional test cases.

```sh
make app
python3 test_app.py
```

The pre-existing missing `main.o -> config.h` declaration is intentionally
preserved for the E12 repair stage. No defect was removed or newly injected in
the Makefile. The candidate patch must be generated from the live detector
report, applied to an isolated copy, tested, and rechecked by BuildChecker.

This is a group-authored course C/Make project with recorded maintenance;
it remains a small course-origin project. Its applicability to the course's
"real project" criterion must be stated using this provenance.
