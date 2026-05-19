#!/usr/bin/env python3
"""
rush01 comprehensive test suite — single-file edition.

Usage: ./run.sh [options]   (or: python3 tester.py [options])
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import random
from dataclasses import dataclass
from itertools import permutations
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Output helpers
# ═══════════════════════════════════════════════════════════════════════════════

RED    = "\033[91m"
REDD   = "\033[31m"
GREEN  = "\033[92m"
YELLOW = "\033[1;33m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}"

def _ok(label: str) -> None:
    print(f"  {_c(GREEN, 'PASS')}  {label}")

def _fail(label: str, detail: str = "") -> None:
    msg = f"  {_c(RED, 'FAIL')}  {label}"
    if detail:
        msg += f"\n        {_c(REDD, detail)}"
    print(msg)

def _section(title: str) -> None:
    print(f"\n{_c(YELLOW, '─── ' + title + ' ───')}")

def _summary(suite: str, passed: int, failed: int) -> None:
    total = passed + failed
    color = GREEN if failed == 0 else RED
    print(f"  {_c(color, f'{passed}/{total}')}  {suite}")

def _banner(title: str) -> None:
    bar = "═" * (len(title) + 4)
    print(f"\n{YELLOW}╔{bar}╗{RESET}")
    print(f"{YELLOW}║  {title}  ║{RESET}")
    print(f"{YELLOW}╚{bar}╝{RESET}\n")

def _print_board(board: list[list[int]]) -> None:
    for row in board:
        print("    " + " ".join(map(str, row)))

def _print_nice_board(board: list[list[int]], views: list[int], size: int) -> None:
    top   = views[:size]
    bot   = views[size:size * 2]
    left  = views[size * 2:size * 3]
    right = views[size * 3:size * 4]
    print("     " + " ".join(map(str, top)))
    print("    " + "-" * (size * 2 + 1))
    for i, row in enumerate(board):
        print(f"  {left[i]} | " + " ".join(map(str, row)) + f" | {right[i]}")
    print("    " + "-" * (size * 2 + 1))
    print("     " + " ".join(map(str, bot)))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Binary runner & result assertions
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RunResult:
    stdout:     str
    stderr:     str
    returncode: int
    timed_out:  bool = False


def _run_binary(
    executable: str,
    args: list[str],
    timeout: int = 10,
    prefix_cmd: Optional[list[str]] = None,
) -> RunResult:
    cmd = (prefix_cmd or []) + [executable] + args
    try:
        proc = subprocess.run(
            cmd, capture_output=True, encoding="utf-8", timeout=timeout,
        )
        return RunResult(proc.stdout, proc.stderr, proc.returncode)
    except subprocess.TimeoutExpired:
        return RunResult("", "", -1, timed_out=True)
    except FileNotFoundError:
        print(_c(RED, f"Executable not found: {executable}"), file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(_c(RED, f"Permission denied: {executable}  (not executable or wrong arch?)"), file=sys.stderr)
        sys.exit(1)


def _assert_error(result: RunResult) -> tuple[bool, str]:
    if result.timed_out:
        return False, "timed out"
    if "Error\n" in result.stdout + result.stderr:
        return True, ""
    return False, f"expected 'Error\\n', got stdout={result.stdout!r} stderr={result.stderr!r}"


def _assert_valid(result: RunResult, views: list[int], size: int) -> tuple[bool, str]:
    if result.timed_out:
        return False, "timed out"
    if result.returncode != 0:
        return False, f"non-zero exit {result.returncode}"
    try:
        board = _parse_board(result.stdout, size)
    except Exception as e:
        return False, str(e)
    ok_latin, msg = _check_latin(board, size)
    if not ok_latin:
        return False, msg
    ok_views, msg = _check_views(board, views, size)
    if not ok_views:
        return False, msg
    return True, ""


def _parse_board(output: str, size: int) -> list[list[int]]:
    lines = [l for l in output.strip().split("\n") if l.strip()]
    if len(lines) != size:
        raise ValueError(f"expected {size} rows, got {len(lines)}")
    board = []
    for line in lines:
        cells = line.split()
        if len(cells) != size:
            raise ValueError(f"expected {size} cols, got {len(cells)} in {line!r}")
        board.append([int(c) for c in cells])
    return board


def _check_latin(board: list[list[int]], size: int) -> tuple[bool, str]:
    digits = set(range(1, size + 1))
    for i, row in enumerate(board):
        if set(row) != digits:
            return False, f"row {i} is not a permutation of 1..{size}: {row}"
    for j in range(size):
        col = [board[i][j] for i in range(size)]
        if set(col) != digits:
            return False, f"col {j} is not a permutation of 1..{size}: {col}"
    return True, ""


def _check_views(board: list[list[int]], views: list[int], size: int) -> tuple[bool, str]:
    def visible(seq):
        count, mx = 0, 0
        for v in seq:
            if v > mx:
                mx = v; count += 1
        return count

    for j in range(size):
        col = [board[i][j] for i in range(size)]
        if visible(col) != views[j]:
            return False, f"col {j} top: expected {views[j]}, got {visible(col)}"
        if visible(list(reversed(col))) != views[size + j]:
            return False, f"col {j} bottom: expected {views[size+j]}, got {visible(list(reversed(col)))}"
    for i in range(size):
        row = board[i]
        if visible(row) != views[size * 2 + i]:
            return False, f"row {i} left: expected {views[size*2+i]}, got {visible(row)}"
        if visible(list(reversed(row))) != views[size * 3 + i]:
            return False, f"row {i} right: expected {views[size*3+i]}, got {visible(list(reversed(row)))}"
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Generator (ported from tester-tsomsa; no external import needed)
# ═══════════════════════════════════════════════════════════════════════════════

def _rm_unavailable(tbl, avail_num, i, j, size):
    for tmp in range(size):
        try: avail_num.remove(tbl[i][tmp])
        except ValueError: pass
    for tmp in range(size):
        try: avail_num.remove(tbl[tmp][j])
        except ValueError: pass
    return avail_num


def _generate_possible_table(size: int) -> list[list[int]]:
    tbl = [[0] * size for _ in range(size)]
    for i in range(size):
        for j in range(size):
            avail = list(range(1, size + 1))
            avail = _rm_unavailable(tbl, avail, i, j, size)
            if not avail:
                return _generate_possible_table(size)
            tbl[i][j] = random.choice(avail)
    return tbl


def _get_views(tbl: list[list[int]], size: int) -> list[int]:
    def visible_from(seq):
        count, mx = 0, 0
        for v in seq:
            if v > mx:
                mx = v; count += 1
        return count

    views = []
    for j in range(size):
        views.append(visible_from(tbl[i][j] for i in range(size)))
    for j in range(size):
        views.append(visible_from(tbl[i][j] for i in range(size - 1, -1, -1)))
    for i in range(size):
        views.append(visible_from(tbl[i]))
    for i in range(size):
        views.append(visible_from(reversed(tbl[i])))
    return views


def _get_solvable(size: int) -> tuple[list[int], list[list[int]]]:
    board = _generate_possible_table(size)
    return _get_views(board, size), board


def _get_impossible_clue_str(size: int) -> str:
    board = _generate_possible_table(size)
    views = _get_views(board, size)
    idx = random.randrange(len(views))
    original = views[idx]
    views[idx] = (original % size) + 1   # stays in [1,size], guaranteed != original
    return " ".join(map(str, views))


def _compute_views(board: list[list[int]], size: int) -> str:
    return " ".join(map(str, _get_views(board, size)))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Compilation helpers
# ═══════════════════════════════════════════════════════════════════════════════

_MALLOC_STRIKE_URL = (
    "https://raw.githubusercontent.com/"
    "TanawatJukmongkol/malloc_strike/main/malloc_strike.c"
)
_TMP = tempfile.gettempdir()


def _fetch_malloc_strike() -> str:
    path = os.path.join(_TMP, "malloc_strike.c")
    if not os.path.exists(path):
        print("  Fetching malloc_strike.c …", end=" ", flush=True)
        urllib.request.urlretrieve(_MALLOC_STRIKE_URL, path)
        print("done")
    return path


def _compile(
    src_dir: str,
    out_path: str,
    extra_flags: Optional[list[str]] = None,
    with_malloc_strike: bool = False,
    malloc_id_fail: Optional[int] = None,
) -> tuple[bool, str]:
    sources = sorted(
        os.path.join(src_dir, f)
        for f in os.listdir(src_dir)
        if f.endswith(".c")
    )
    if not sources:
        return False, f"no .c files found in {src_dir}"

    cmd = ["cc", "-Wall", "-Wextra", "-Werror"] + (extra_flags or [])

    if with_malloc_strike:
        ms = _fetch_malloc_strike()
        sources = sources + [ms]
        cmd += ["-ldl"]
        if malloc_id_fail is not None:
            cmd += [f"-DMALLOC_ID_FAIL={malloc_id_fail}UL"]

    cmd += sources + ["-o", out_path]
    result = subprocess.run(cmd, capture_output=True, encoding="utf-8")
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Eliminatory: checklist (verbatim eval sheet cases)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_eliminatory_checklist(
    executable: str, size: int, verbose: bool,
) -> tuple[int, int]:
    _section(f"Eliminatory — Checklist  (size {size})")
    passed = failed = 0
    n = size * 4

    valid_views, _ = _get_solvable(size)
    valid_list = list(map(str, valid_views))
    valid_str  = " ".join(valid_list)

    def _run(label: str, arg) -> None:
        nonlocal passed, failed
        args = [] if arg is None else [arg]
        result = _run_binary(executable, args)
        good, detail = _assert_error(result)
        if good:
            _ok(label); passed += 1
        else:
            _fail(label, detail)
            if verbose:
                print(f"        stdout: {result.stdout!r}")
                print(f"        stderr: {result.stderr!r}")
            failed += 1

    _run("Too many numbers",   valid_str + " " + valid_list[0])
    _run("Too few numbers",    " ".join(valid_list[:-1]))

    oor = valid_list[:]; oor[n // 2] = str(size + 1)
    _run("Out-of-range value", " ".join(oor))

    _run("No spaces (fused)",  "".join(valid_list))
    _run("Non-numeric string", "Bonjours")
    _run("Impossible grid",    _get_impossible_clue_str(size))

    _summary(f"Checklist eliminatory (size {size})", passed, failed)
    return passed, failed


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Eliminatory: extra hardened edge cases
# ═══════════════════════════════════════════════════════════════════════════════

_INT_MAX    =  2_147_483_647
_INT_MIN    = -2_147_483_648
_ULLONG_MAX = 18_446_744_073_709_551_615


def _run_eliminatory_extra(
    executable: str, size: int, verbose: bool,
) -> tuple[int, int]:
    _section(f"Eliminatory — Extra  (size {size})")
    passed = failed = 0

    valid_views, _ = _get_solvable(size)
    base     = list(map(str, valid_views))
    good_str = " ".join(base)

    def _run(label: str, arg) -> None:
        nonlocal passed, failed
        if arg is None:
            args = []
        elif isinstance(arg, list):
            args = arg
        else:
            args = [str(arg)]
        result = _run_binary(executable, args)
        good, detail = _assert_error(result)
        if good:
            _ok(label); passed += 1
        else:
            _fail(label, detail)
            if verbose:
                print(f"        stdout: {result.stdout!r}")
                print(f"        stderr: {result.stderr!r}")
            failed += 1

    def _splice(value: str, pos: int = 0) -> str:
        t = base[:]
        t[pos] = value
        return " ".join(t)

    # Argument count / structure
    _run("No argument",            None)
    _run("Two arguments",          [good_str, good_str])
    _run("Empty string",           "")
    _run("Whitespace-only",        "   ")

    # Value range
    _run("Zero value",             _splice("0"))
    _run("Negative value (-1)",    _splice("-1"))
    _run(f"Value {size+1} (max+1)", _splice(str(size + 1)))

    # Signed integer overflow
    _run("INT_MAX+1 overflow",     _splice(str(_INT_MAX + 1)))
    _run("INT_MIN-1 overflow",     _splice(str(_INT_MIN - 1)))

    # Unsigned long long overflow
    _run("ULLONG_MAX+1 overflow",  _splice(str(_ULLONG_MAX + 1)))
    _run("Negative ULLONG",        _splice(str(-(_ULLONG_MAX + 1))))

    # Spacing / formatting
    half = len(base) // 2
    mid_spaced = " ".join(base[:half]) + "  " + " ".join(base[half:])
    _run("Double space mid",       mid_spaced)
    _run("Leading spaces",         "  " + good_str)
    _run("Trailing spaces",        good_str + "  ")
    _run("Tab-separated",          "\t".join(base))
    _run("Mixed tabs and spaces",  base[0] + "\t" + " ".join(base[1:]))

    # Junk content
    _run("Float value (1.5)",      _splice("1.5"))
    _run("Hex literal (0x2)",      _splice("0x2"))
    _run("Leading plus (+1)",      _splice("+1"))
    _run("Full-width digit (１)",  _splice("１"))   # U+FF11

    _summary(f"Extra eliminatory (size {size})", passed, failed)
    return passed, failed


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — Features (random solvable + impossible)
# ═══════════════════════════════════════════════════════════════════════════════

_SOLVABLE_COUNT   = 20
_IMPOSSIBLE_COUNT = 10


def _run_features(
    executable: str, size: int, verbose: bool, debug: bool,
) -> tuple[int, int]:
    _section(f"Features  (size {size})")
    passed = failed = 0

    print(f"  Solvable ({_SOLVABLE_COUNT} random):")
    for i in range(_SOLVABLE_COUNT):
        views, board = _get_solvable(size)
        clue_str = " ".join(map(str, views))
        result = _run_binary(executable, [clue_str])
        good, detail = _assert_valid(result, views, size)
        label = f"solvable [{i:02d}] {clue_str}"
        if good:
            _ok(label); passed += 1
        else:
            _fail(label, detail)
            if verbose or debug:
                print("      Expected (one valid solution):")
                if debug:
                    _print_nice_board(board, views, size)
                else:
                    _print_board(board)
                print(f"      Got: {result.stdout!r}")
            failed += 1

    print(f"  Impossible ({_IMPOSSIBLE_COUNT} random):")
    for i in range(_IMPOSSIBLE_COUNT):
        clue_str = _get_impossible_clue_str(size)
        result = _run_binary(executable, [clue_str])
        good, detail = _assert_error(result)
        label = f"impossible [{i:02d}] {clue_str}"
        if good:
            _ok(label); passed += 1
        else:
            _fail(label, detail)
            if verbose:
                print(f"      stdout: {result.stdout!r}")
                print(f"      stderr: {result.stderr!r}")
            failed += 1

    _summary(f"Features (size {size})", passed, failed)
    return passed, failed


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — malloc_strike + valgrind
# ═══════════════════════════════════════════════════════════════════════════════

_VALGRIND_FLAGS = [
    "--leak-check=full",
    "--track-origins=yes",
    "--error-exitcode=42",
    "--quiet",
]
_MALLOC_FEATURE_COUNT = 10
_MALLOC_INJECT_MAX    = 20

_LEAK_RE  = re.compile(r"definitely lost: [^0]")
_INVAL_RE = re.compile(r"Invalid (read|write)")


def _malloc_cases(size: int) -> list[tuple[str, list[str], str]]:
    n = size * 4
    cases: list[tuple[str, list[str], str]] = [
        ("too-many",    [" ".join(["1"] * (n + 1))], "error"),
        ("non-numeric", ["Bonjours"],                 "error"),
        ("no-arg",      [],                           "error"),
    ]
    for i in range(_MALLOC_FEATURE_COUNT):
        views, _ = _get_solvable(size)
        cases.append((f"solvable-{i:02d}", [" ".join(map(str, views))], "valid"))
    for i in range(5):
        cases.append((f"impossible-{i:02d}", [_get_impossible_clue_str(size)], "error"))
    return cases


def _check_result(result: RunResult, expect: str, views: Optional[list[int]], size: int) -> tuple[bool, str]:
    if expect == "error":
        return _assert_error(result)
    return _assert_valid(result, views or [], size)


def _run_malloc_strike(src_dir: str, size: int, verbose: bool) -> tuple[int, int]:
    _section(f"malloc_strike  (size {size})")
    passed = failed = 0

    ms_bin = os.path.join(_TMP, "rush-01-mstrike")
    print("  Compiling debug binary with malloc_strike …", end=" ", flush=True)
    ok_c, err = _compile(src_dir, ms_bin, extra_flags=["-g", "-O0"], with_malloc_strike=True)
    if not ok_c:
        print(); _fail("compile", err)
        return 0, 1
    print("ok")

    for label, args, expect in _malloc_cases(size):
        views = list(map(int, args[0].split())) if args and expect == "valid" else None
        result = _run_binary(ms_bin, args)
        good, detail = _check_result(result, expect, views, size)
        if result.returncode in (-11, -6):
            good, detail = False, f"crash (signal {-result.returncode})"
        if good:
            _ok(f"mstrike/{label}"); passed += 1
        else:
            _fail(f"mstrike/{label}", detail)
            if verbose:
                print(f"      stderr: {result.stderr[:400]!r}")
            failed += 1

    # Allocation failure injection
    _section(f"malloc_strike — failure injection  (size {size})")
    inj_views, _ = _get_solvable(size)
    inj_str = " ".join(map(str, inj_views))

    for mid in range(1, _MALLOC_INJECT_MAX + 1):
        bin_path = os.path.join(_TMP, f"rush-01-mstrike-fail{mid}")
        ok_c, err = _compile(
            src_dir, bin_path,
            extra_flags=["-g", "-O0"],
            with_malloc_strike=True,
            malloc_id_fail=mid,
        )
        if not ok_c:
            _fail(f"inject/compile@{mid}", err); failed += 1; continue
        result = _run_binary(bin_path, [inj_str])
        if result.returncode in (-11, -6) or result.timed_out:
            _fail(f"inject/malloc@{mid}", f"crash/timeout on malloc failure #{mid}"); failed += 1
        else:
            _ok(f"inject/malloc@{mid}"); passed += 1

    _summary(f"malloc_strike (size {size})", passed, failed)
    return passed, failed


def _run_valgrind(src_dir: str, size: int, verbose: bool) -> tuple[int, int]:
    _section(f"valgrind  (size {size})")
    passed = failed = 0

    vg_bin = os.path.join(_TMP, "rush-01-vg")
    print("  Compiling debug binary for valgrind …", end=" ", flush=True)
    ok_c, err = _compile(src_dir, vg_bin, extra_flags=["-g", "-O0"])
    if not ok_c:
        print(); _fail("compile", err)
        return 0, 1
    print("ok")

    mem_errors = leak_errors = 0

    for label, args, expect in _malloc_cases(size):
        views = list(map(int, args[0].split())) if args and expect == "valid" else None
        result = _run_binary(vg_bin, args, timeout=30, prefix_cmd=["valgrind"] + _VALGRIND_FLAGS)
        logic_ok, detail = _check_result(result, expect, views, size)
        has_leak  = bool(_LEAK_RE.search(result.stderr))
        has_inval = bool(_INVAL_RE.search(result.stderr))
        vg_err    = result.returncode == 42

        issues = []
        if not logic_ok:
            issues.append(f"logic: {detail}")
        if has_leak:
            issues.append("memory leak"); leak_errors += 1
        if has_inval:
            issues.append("invalid read/write"); mem_errors += 1
        if vg_err and not has_leak and not has_inval:
            issues.append("valgrind error (see stderr)"); mem_errors += 1

        if not issues:
            _ok(f"vg/{label}"); passed += 1
        else:
            _fail(f"vg/{label}", " | ".join(issues))
            if verbose:
                print(f"      stderr: {result.stderr[:600]!r}")
            failed += 1

    if mem_errors or leak_errors:
        print(f"  Summary: {mem_errors} invalid access(es), {leak_errors} leak(s)")

    _summary(f"valgrind (size {size})", passed, failed)
    return passed, failed


def _run_malloc(
    src_dir: str, size: int,
    malloc_strike: bool, valgrind: bool, verbose: bool,
) -> tuple[int, int]:
    p = f = 0
    if malloc_strike:
        pp, ff = _run_malloc_strike(src_dir, size, verbose)
        p += pp; f += ff
    if valgrind:
        pp, ff = _run_valgrind(src_dir, size, verbose)
        p += pp; f += ff
    return p, f


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — Exhaustive 4×4
# ═══════════════════════════════════════════════════════════════════════════════

_EX_SIZE   = 4
_EX_DIGITS = list(range(1, _EX_SIZE + 1))


def _all_latin_squares_4x4() -> list[list[list[int]]]:
    squares = []
    for r0 in permutations(_EX_DIGITS):
        for r1 in permutations(_EX_DIGITS):
            if any(r1[j] == r0[j] for j in range(_EX_SIZE)):
                continue
            for r2 in permutations(_EX_DIGITS):
                if any(r2[j] in (r0[j], r1[j]) for j in range(_EX_SIZE)):
                    continue
                r3 = []
                for j in range(_EX_SIZE):
                    rem = [x for x in _EX_DIGITS if x not in {r0[j], r1[j], r2[j]}]
                    if len(rem) != 1:
                        break
                    r3.append(rem[0])
                else:
                    squares.append([list(r0), list(r1), list(r2), r3])
    return squares


def _run_exhaustive(executable: str, verbose: bool) -> tuple[int, int]:
    _section("Exhaustive 4×4 — all unique clue combinations")

    print("  Enumerating valid 4×4 Latin squares …", end=" ", flush=True)
    squares = _all_latin_squares_4x4()
    print(f"{len(squares)} found")

    seen: dict[str, list[list[int]]] = {}
    for board in squares:
        clue = _compute_views(board, _EX_SIZE)
        if clue not in seen:
            seen[clue] = board
    print(f"  Unique clue sets: {len(seen)}\n")

    passed = failed = 0
    for clue_str, _ in seen.items():
        views = list(map(int, clue_str.split()))
        result = _run_binary(executable, [clue_str])
        good, detail = _assert_valid(result, views, _EX_SIZE)
        if good:
            _ok(clue_str); passed += 1
        else:
            _fail(clue_str, detail)
            if verbose:
                print(f"      stdout: {result.stdout!r}")
            failed += 1

    _summary(f"Exhaustive 4×4 ({len(seen)} clue sets)", passed, failed)
    return passed, failed


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — Bonus (sizes 1–9)
# ═══════════════════════════════════════════════════════════════════════════════

def _run_bonus(
    executable: str,
    src_dir: str,
    malloc_strike: bool,
    valgrind: bool,
    verbose: bool,
    debug: bool,
) -> tuple[int, int]:
    print(f"\n{YELLOW}{'═' * 50}{RESET}")
    print(f"{YELLOW}  BONUS — sizes 1–9{RESET}")
    print(f"{YELLOW}{'═' * 50}{RESET}")

    total_p = total_f = 0
    per_size: dict[int, tuple[int, int]] = {}

    for size in range(1, 10):
        print(f"\n{YELLOW}  ── Size {size} ──{RESET}")
        sp = sf = 0

        pp, ff = _run_eliminatory_checklist(executable, size, verbose)
        sp += pp; sf += ff

        pp, ff = _run_eliminatory_extra(executable, size, verbose)
        sp += pp; sf += ff

        pp, ff = _run_features(executable, size, verbose, debug)
        sp += pp; sf += ff

        if malloc_strike or valgrind:
            pp, ff = _run_malloc(src_dir, size, malloc_strike, valgrind, verbose)
            sp += pp; sf += ff

        per_size[size] = (sp, sf)
        total_p += sp; total_f += sf

    print(f"\n{YELLOW}── Bonus summary ──{RESET}")
    for size, (p, f) in per_size.items():
        _summary(f"size {size}", p, f)

    return total_p, total_f


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — CLI / main
# ═══════════════════════════════════════════════════════════════════════════════

def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="run.sh",
        description="rush01 comprehensive test suite",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument(
        "-e", "--executable",
        default=os.path.join(os.path.dirname(__file__), "..", "ex00", "rush-01"),
        metavar="PATH",
        help="path to rush-01 binary  (default: ../ex00/rush-01)",
    )
    p.add_argument(
        "--src-dir",
        default=None,
        metavar="PATH",
        help="directory of *.c sources  (default: same dir as executable)",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="show board output on failures")
    p.add_argument("-d", "--debug",   action="store_true", help="annotated board with view clues")
    p.add_argument(
        "-m", "--malloc-strike", action="store_true",
        help="compile debug binary linked with malloc_strike.c\n"
             "(cloned from GitHub) and re-run all cases against it",
    )
    p.add_argument(
        "-V", "--valgrind", action="store_true",
        help="compile debug binary (-g -O0) and wrap runs with valgrind\n"
             "(--leak-check=full --track-origins=yes --error-exitcode=42)",
    )
    p.add_argument(
        "-E", "--exhaustive", action="store_true",
        help="run all unique 4×4 view-clue combinations\n"
             "((4!)^4 = 331,776 row combos → 576 Latin squares → unique clue sets)",
    )
    p.add_argument(
        "-b", "--bonus", action="store_true",
        help="run bonus suite for sizes 1–9\n"
             "(both eliminatory suites + features + malloc; no exhaustive)",
    )
    p.add_argument(
        "-c", "--recompile", action="store_true",
        help="recompile the binary from sources before running\n"
             "(auto-compile also runs if the binary does not exist yet)",
    )
    return p.parse_args()


def main() -> None:
    args   = _parse()
    exe    = os.path.abspath(args.executable)
    srcdir = os.path.abspath(args.src_dir) if args.src_dir else os.path.dirname(exe)

    needs_compile = args.recompile or not os.path.isfile(exe)
    if needs_compile:
        action = "Recompiling" if os.path.isfile(exe) else "Auto-compiling"
        print(f"  {action} from {srcdir} …", end=" ", flush=True)
        ok, err = _compile(srcdir, exe)
        if not ok:
            print()
            print(_c(RED, f"Compilation failed:\n{err}"), file=sys.stderr)
            sys.exit(1)
        print(_c(GREEN, "ok"))

    if not os.path.isfile(exe):
        print(_c(RED, f"Executable not found: {exe}"), file=sys.stderr)
        print("Build with:  cc -Wall -Wextra -Werror -o rush-01 *.c", file=sys.stderr)
        sys.exit(1)

    _banner("rush01 test suite")
    print(f"  executable : {exe}")
    print(f"  src dir    : {srcdir}")
    print()

    gp = gf = 0

    def _acc(p: int, f: int) -> None:
        nonlocal gp, gf
        gp += p; gf += f

    _acc(*_run_eliminatory_checklist(exe, 4, args.verbose))
    _acc(*_run_eliminatory_extra(exe, 4, args.verbose))
    _acc(*_run_features(exe, 4, args.verbose, args.debug))

    if args.malloc_strike or args.valgrind:
        _acc(*_run_malloc(srcdir, 4, args.malloc_strike, args.valgrind, args.verbose))

    if args.exhaustive:
        _acc(*_run_exhaustive(exe, args.verbose))

    if args.bonus:
        _acc(*_run_bonus(exe, srcdir, args.malloc_strike, args.valgrind, args.verbose, args.debug))

    total = gp + gf
    color = GREEN if gf == 0 else RED
    print(f"\n{YELLOW}{'─' * 40}{RESET}")
    print(f"  TOTAL  {color}{gp}/{total}{RESET}  passed")
    if gf:
        print(f"         {RED}{gf} failed{RESET}")
    print()


if __name__ == "__main__":
    main()
