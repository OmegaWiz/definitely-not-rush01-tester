# definitely-not-rush01-tester

Warning: there should be bugs in here, please report them.

## Usage

```sh
# Build your binary first
cc -Wall -Wextra -Werror -o rush-01 *.c

# Run standard suite (eliminatory + features, size 4)
./tester/run.sh -e ./rush-01

# Show board output on failures
./tester/run.sh -e ./rush-01 -v

# Annotated board with view clues on failures
./tester/run.sh -e ./rush-01 -d
```

## Options

| Flag | Description |
|------|-------------|
| `-e PATH` | Path to the `rush-01` binary (default: `../ex00/rush-01`) |
| `-v` | Verbose — show board output on failures |
| `-d` | Debug — annotated board with view clues on failures |
| `-m` | malloc_strike — recompile with malloc_strike and test for crashes |
| `-V` | valgrind — wrap runs with valgrind and check for leaks / invalid access |
| `-E` | Exhaustive — test all unique 4×4 clue combinations (~438 sets) |
| `-b` | Bonus — run all suites for sizes 1–9 |
| `--src-dir PATH` | Directory of `.c` source files (default: same dir as executable) |

Flags can be combined, e.g. `./tester/run.sh -e ./rush-01 -m -V -v`.

## Test suites

### Eliminatory — Checklist
Verbatim cases from the eval sheet: too many numbers, too few numbers, out-of-range value, fused digits (no spaces), non-numeric string, and an impossible grid. All must output `Error`.

### Eliminatory — Extra
Hardened edge cases not in the eval sheet: no argument, two arguments, empty string, whitespace-only, zero, negative, integer overflow (`INT_MAX+1`, `INT_MIN-1`), unsigned overflow (`ULLONG_MAX+1`), double spaces, leading/trailing spaces, tab-separated, float (`1.5`), hex (`0x2`), leading plus (`+1`), and full-width digits. All must output `Error`.

In both suites the base input is a real solvable clue string — only the specific thing being tested is corrupted, so `Error` is never caused by an impossible puzzle.

### Features
20 random solvable grids (verified for correct Latin square + matching view clues) and 10 random impossible grids (must output `Error`).

### malloc_strike (`-m`)
Recompiles the binary with [`malloc_strike.c`](https://github.com/TanawatJukmongkol/malloc_strike) (fetched automatically from GitHub) using `-g -O0 -ldl`. Runs all cases and checks for crashes (`SIGSEGV`, `SIGABRT`). Then runs 20 allocation-failure injection rounds (`-DMALLOC_ID_FAIL=K`) to ensure no crash on any malloc failure.

### valgrind (`-V`)
Recompiles the binary with `-g -O0` and wraps each run with:
```
valgrind --leak-check=full --track-origins=yes --error-exitcode=42 --quiet
```
Flags definite leaks and invalid reads/writes.

### Exhaustive (`-E`)
Enumerates all (4!)⁴ = 331,776 row permutations, filters to 576 valid 4×4 Latin squares, deduplicates by clue string (~438 unique sets), and tests every one. Slow but thorough.

### Bonus (`-b`)
Runs both eliminatory suites + features (+ malloc/valgrind if flags given) for every grid size from 1 to 9. Prints a per-size summary table at the end.

## Files

```
tester/
├── run.sh      entry point (calls tester.py)
└── tester.py   single-file test suite (~820 lines, no external dependencies)
```
