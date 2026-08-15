"""Covering-array generator for constrained parameter sets.

Why this is Python and not a prompt
-----------------------------------
D-003: models produce plausible-looking coverage sets that are neither minimal nor
complete, and the error is invisible on inspection. A missing pair is not visible by
reading the table; a redundant row is not visible either. Both are visible here, because
this module *counts* them and prints the count.

The output is a t-wise covering array: every combination of values for every t-sized
subset of parameters appears in at least one row, unless a constraint makes that
combination impossible.

The three-way distinction that matters
--------------------------------------
A pair that does not appear in the output is one of three very different things, and
conflating them is how a bad constraint silently deletes real coverage:

  COVERED     the pair appears in at least one row. Nothing to say.
  PREVENTED   no constraint-satisfying assignment contains this pair, so it cannot be
              tested and its absence is correct. Reported, with the constraint id.
  UNCOVERED   the pair is reachable but no row contains it. This is a generator bug and
              is reported as a hard failure, not a warning.

`filter-inventory.md`'s own sanity note says a 2-wise array over the core block should
land in the low tens of rows, and that "fewer than ~25 rows means a constraint is
over-broad and is deleting real combinations". PREVENTED counts are what let a human
check that claim instead of trusting it.

Constraint expressions
----------------------
Each constraint carries a human-readable `rule` and a machine-evaluable `expr` whose
identifiers are parameter names. Expressions are evaluated with no builtins in scope, so
an expression can read parameter values and nothing else. A constraint is only evaluated
once every parameter it references is assigned — partial rows are never judged against a
rule that cannot yet be decided.

CLI
---
    python tools/pairwise.py selftest
    python tools/pairwise.py generate --input context/filter-inventory.md
    python tools/pairwise.py generate --input plan.yaml --strength 2 --format markdown
    python tools/pairwise.py generate --input context/filter-inventory.md --json out.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

__all__ = ["Model", "Constraint", "CoveringArray", "build", "parse_model"]

# A fenced ```yaml block inside a Markdown file. filter-inventory.md keeps its parameter
# block inline with the prose that explains it (D-005) — one file, so the two cannot
# drift apart. That means this tool must be able to read a block out of Markdown, not
# only a standalone .yaml.
_YAML_FENCE = re.compile(r"```ya?ml\s*\n(.*?)\n```", re.DOTALL)

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Quoted literals are stripped before identifier extraction, otherwise the `Rent` in
# `purpose == 'Rent'` reads as a parameter reference and every expression looks like it
# names an unknown parameter.
_STRING_LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"")

# Operators and literals that are valid in an expression but are not parameter names.
# Anything left over after removing these is either a parameter or a typo, and a typo
# must fail loudly: a constraint that references nothing silently stops constraining,
# which deletes no combinations and is invisible in the output.
_EXPR_KEYWORDS = frozenset(
    {"and", "or", "not", "in", "is", "if", "else", "True", "False", "None"}
)


def _referenced_identifiers(expr: str) -> set[str]:
    """Every identifier an expression reads, ignoring string contents and keywords."""
    without_strings = _STRING_LITERAL.sub("''", expr)
    return {
        m.group(0)
        for m in _IDENTIFIER.finditer(without_strings)
        if m.group(0) not in _EXPR_KEYWORDS
    }


class PairwiseError(RuntimeError):
    """Raised for a malformed model or an unsatisfiable one."""


@dataclass(frozen=True)
class Constraint:
    id: str
    rule: str
    expr: str
    params: frozenset[str]

    def decidable(self, assignment: dict[str, Any]) -> bool:
        """True when every parameter this constraint reads has been assigned."""
        return self.params.issubset(assignment.keys())

    def holds(self, assignment: dict[str, Any]) -> bool:
        """Evaluate against a complete-enough assignment.

        No builtins in scope: an expression can read parameter values and do nothing
        else. These expressions come from a repo file that a human edits, not from
        model output, but a config file is still not a place to accept arbitrary code.
        """
        try:
            return bool(eval(self.expr, {"__builtins__": {}}, dict(assignment)))
        except Exception as exc:  # noqa: BLE001 - surfaced with the offending id
            raise PairwiseError(
                f"constraint {self.id} failed to evaluate: {exc}\n"
                f"  expr: {self.expr}\n"
                f"  assignment: {assignment}"
            ) from exc


@dataclass
class Model:
    parameters: dict[str, list[Any]]
    constraints: list[Constraint] = field(default_factory=list)

    def validate(self) -> None:
        if not self.parameters:
            raise PairwiseError("model has no parameters")
        for name, values in self.parameters.items():
            if not values:
                raise PairwiseError(f"parameter {name!r} has no values")
            if len(set(map(_key, values))) != len(values):
                raise PairwiseError(f"parameter {name!r} has duplicate values: {values}")
        known = set(self.parameters)
        for c in self.constraints:
            unknown = c.params - known
            if unknown:
                raise PairwiseError(
                    f"constraint {c.id} references unknown parameter(s) "
                    f"{sorted(unknown)}; known parameters are {sorted(known)}"
                )


@dataclass
class CoveringArray:
    rows: list[dict[str, Any]]
    strength: int
    model: Model
    covered: set[tuple] = field(default_factory=set)
    prevented: dict[tuple, str] = field(default_factory=dict)

    @property
    def full_cross_product(self) -> int:
        total = 1
        for values in self.model.parameters.values():
            total *= len(values)
        return total

    def stats(self) -> dict[str, Any]:
        return {
            "rows": len(self.rows),
            "strength": self.strength,
            "parameters": len(self.model.parameters),
            "constraints": len(self.model.constraints),
            "full_cross_product": self.full_cross_product,
            "combinations_covered": len(self.covered),
            "combinations_prevented": len(self.prevented),
        }


def _key(value: Any) -> str:
    """Stable, hashable, human-readable key for a parameter value."""
    return f"{type(value).__name__}:{value!r}"


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_model(text: str) -> Model:
    """Parse a model from raw YAML, or from the first ```yaml block in Markdown."""
    try:
        import yaml  # noqa: PLC0415 - optional dependency, error message below is the point
    except ImportError as exc:  # pragma: no cover
        raise PairwiseError(
            "PyYAML is required to parse a model. Install it with `pip install PyYAML`."
        ) from exc

    fenced = _YAML_FENCE.search(text)
    candidates = [fenced.group(1)] if fenced else []
    candidates.append(text)

    data = None
    for candidate in candidates:
        try:
            loaded = yaml.safe_load(candidate)
        except yaml.YAMLError:
            continue
        if isinstance(loaded, dict) and "parameters" in loaded:
            data = loaded
            break
    if data is None:
        raise PairwiseError(
            "no `parameters:` mapping found. Provide a YAML file, or a Markdown file "
            "containing a ```yaml block with a `parameters:` key."
        )

    raw_params = data.get("parameters") or {}
    if not isinstance(raw_params, dict):
        raise PairwiseError("`parameters` must be a mapping of name -> list of values")
    parameters = {str(k): list(v) for k, v in raw_params.items()}

    constraints: list[Constraint] = []
    for i, raw in enumerate(data.get("constraints") or [], start=1):
        if not isinstance(raw, dict):
            raise PairwiseError(f"constraint #{i} is not a mapping")
        expr = raw.get("expr")
        if not expr:
            raise PairwiseError(
                f"constraint {raw.get('id', f'#{i}')} has no `expr`. A human-readable "
                f"`rule` alone cannot be enforced — every rule needs a machine form."
            )
        referenced = frozenset(_referenced_identifiers(str(expr)))
        constraints.append(
            Constraint(
                id=str(raw.get("id", f"C{i}")),
                rule=str(raw.get("rule", "")),
                expr=str(expr),
                params=referenced,
            )
        )

    model = Model(parameters=parameters, constraints=constraints)
    model.validate()
    return model


# ---------------------------------------------------------------------------
# Constraint satisfaction
# ---------------------------------------------------------------------------


def _violates(model: Model, assignment: dict[str, Any]) -> str | None:
    """Return the id of the first decidable constraint this assignment breaks."""
    for c in model.constraints:
        if c.decidable(assignment) and not c.holds(assignment):
            return c.id
    return None


def _complete(
    model: Model, order: Sequence[str], fixed: dict[str, Any]
) -> dict[str, Any] | None:
    """Backtracking search for a full assignment extending `fixed`.

    This is what separates PREVENTED from UNCOVERED. Rather than assuming a
    combination is impossible because the greedy pass never produced it, we ask
    directly: does *any* valid complete assignment contain it?
    """
    assignment = dict(fixed)
    if _violates(model, assignment):
        return None
    remaining = [p for p in order if p not in assignment]

    def recurse(idx: int) -> bool:
        if idx == len(remaining):
            return _violates(model, assignment) is None
        param = remaining[idx]
        for value in model.parameters[param]:
            assignment[param] = value
            if _violates(model, assignment) is None and recurse(idx + 1):
                return True
            del assignment[param]
        return False

    return dict(assignment) if recurse(0) else None


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _combination_key(items: Sequence[tuple[str, Any]]) -> tuple:
    return tuple(sorted((name, _key(value)) for name, value in items))


def _all_target_combinations(
    model: Model, strength: int
) -> list[tuple[tuple[str, ...], tuple[Any, ...]]]:
    names = list(model.parameters)
    targets: list[tuple[tuple[str, ...], tuple[Any, ...]]] = []
    for combo_names in itertools.combinations(names, strength):
        value_lists = [model.parameters[n] for n in combo_names]
        for values in itertools.product(*value_lists):
            targets.append((combo_names, values))
    return targets


def build(model: Model, strength: int = 2) -> CoveringArray:
    """Greedy constrained covering-array construction.

    Deterministic by construction: candidate values are tried in declaration order and
    ties are broken by the first-best rather than at random. Two runs over the same
    model produce byte-identical output, which is what makes generated case ids stable
    (`filter-inventory.md`: "Keep keys stable — generated case IDs are derived from
    them.").
    """
    model.validate()
    if strength < 1:
        raise PairwiseError("strength must be >= 1")
    names = list(model.parameters)
    if strength > len(names):
        raise PairwiseError(
            f"strength {strength} exceeds the {len(names)} parameters in the model"
        )

    # Order parameters most-constrained-first: it shortens the backtracking search and
    # produces smaller arrays, without affecting correctness.
    constrained_hits = {n: 0 for n in names}
    for c in model.constraints:
        for p in c.params:
            constrained_hits[p] += 1
    order = sorted(
        names, key=lambda n: (-constrained_hits[n], -len(model.parameters[n]), n)
    )

    prevented: dict[tuple, str] = {}
    pending: list[tuple[tuple[str, ...], tuple[Any, ...]]] = []
    for combo_names, values in _all_target_combinations(model, strength):
        fixed = dict(zip(combo_names, values))
        key = _combination_key(list(fixed.items()))
        witness = _complete(model, order, fixed)
        if witness is None:
            # Attribute the impossibility to a specific constraint where we can, so a
            # human can check whether that constraint is right rather than just seeing
            # a count.
            blame = _violates(model, fixed) or _blame_scan(model, order, fixed)
            prevented[key] = blame or "unsatisfiable in combination"
        else:
            pending.append((combo_names, values))

    rows: list[dict[str, Any]] = []
    covered: set[tuple] = set()

    def row_covers(row: dict[str, Any]) -> set[tuple]:
        keys: set[tuple] = set()
        for combo_names in itertools.combinations(order, strength):
            keys.add(_combination_key([(n, row[n]) for n in combo_names]))
        return keys

    for combo_names, values in pending:
        seed = dict(zip(combo_names, values))
        key = _combination_key(list(seed.items()))
        if key in covered:
            continue
        row = _greedy_row(model, order, seed, covered, strength)
        if row is None:
            # _complete() already proved this combination reachable, so failing to
            # place it in a row is a generator defect, never a data problem.
            raise PairwiseError(
                f"internal: combination {seed} was proven satisfiable but no row could "
                f"be built for it. This is a bug in pairwise.py, not in the model."
            )
        rows.append(row)
        covered |= row_covers(row)

    missing = [
        (combo_names, values)
        for combo_names, values in pending
        if _combination_key(list(zip(combo_names, values))) not in covered
    ]
    if missing:
        raise PairwiseError(
            f"internal: {len(missing)} reachable combination(s) left uncovered, e.g. "
            f"{dict(zip(missing[0][0], missing[0][1]))}. This is a bug in pairwise.py."
        )

    return CoveringArray(
        rows=rows, strength=strength, model=model, covered=covered, prevented=prevented
    )


def _blame_scan(model: Model, order: Sequence[str], fixed: dict[str, Any]) -> str | None:
    """Find which single constraint, if dropped, would make `fixed` satisfiable."""
    for c in model.constraints:
        reduced = Model(
            parameters=model.parameters,
            constraints=[o for o in model.constraints if o.id != c.id],
        )
        if _complete(reduced, order, fixed) is not None:
            return c.id
    return None


def _greedy_row(
    model: Model,
    order: Sequence[str],
    seed: dict[str, Any],
    covered: set[tuple],
    strength: int,
) -> dict[str, Any] | None:
    """Extend `seed` into a full valid row, preferring values that cover new ground."""
    assignment = dict(seed)
    if _violates(model, assignment):
        return None
    remaining = [p for p in order if p not in assignment]

    for param in remaining:
        best_value = None
        best_gain = -1
        for value in model.parameters[param]:
            assignment[param] = value
            if _violates(model, assignment) is not None:
                del assignment[param]
                continue
            # Only count gain against already-assigned parameters; the rest of the row
            # is still unknown, so any gain attributed to it would be imaginary.
            assigned = [p for p in assignment if p != param]
            gain = 0
            for others in itertools.combinations(assigned, strength - 1):
                items = [(param, value)] + [(o, assignment[o]) for o in others]
                if _combination_key(items) not in covered:
                    gain += 1
            del assignment[param]
            if gain > best_gain:
                best_gain, best_value = gain, value

        if best_value is None:
            return None
        assignment[param] = best_value

        # Committing greedily can paint the row into a corner. Verify the partial row
        # is still completable; if not, fall back to any value that is.
        if _complete(model, order, assignment) is None:
            del assignment[param]
            for value in model.parameters[param]:
                assignment[param] = value
                if _complete(model, order, assignment) is not None:
                    break
                del assignment[param]
            if param not in assignment:
                return None

    return {name: assignment[name] for name in model.parameters}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_markdown(array: CoveringArray, case_prefix: str = "PW") -> str:
    names = list(array.model.parameters)
    stats = array.stats()
    out: list[str] = []
    out.append(f"| # | {' | '.join(names)} |")
    out.append(f"|---|{'---|' * len(names)}")
    for i, row in enumerate(array.rows, start=1):
        cells = " | ".join(str(row[n]) for n in names)
        out.append(f"| {case_prefix}-{i:03d} | {cells} |")
    out.append("")
    out.append(
        f"{stats['rows']} rows cover all {stats['combinations_covered']} reachable "
        f"{array.strength}-wise combinations "
        f"(full cross product: {stats['full_cross_product']:,})."
    )
    if array.prevented:
        by_rule: dict[str, int] = {}
        for rule_id in array.prevented.values():
            by_rule[rule_id] = by_rule.get(rule_id, 0) + 1
        detail = ", ".join(f"{k}: {v}" for k, v in sorted(by_rule.items()))
        out.append(
            f"{stats['combinations_prevented']} combinations are PREVENTED by "
            f"constraints and are correctly absent ({detail})."
        )
    return "\n".join(out)


def render_json(array: CoveringArray) -> str:
    return json.dumps(
        {
            "stats": array.stats(),
            "rows": array.rows,
            "prevented": [
                {"combination": dict(k), "blamed_constraint": v}
                for k, v in (
                    (dict((n, val) for n, val in combo), rule)
                    for combo, rule in array.prevented.items()
                )
            ],
        },
        indent=2,
        default=str,
    )


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------


def _selftest() -> int:
    checks = 0
    failures: list[str] = []

    def check(condition: bool, label: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            failures.append(label)

    # 1. Unconstrained 2-wise over 3 binary parameters. Known answer: all 12 pairs are
    #    coverable, and 2-wise over binaries needs at least 4 rows.
    m = Model({"a": [0, 1], "b": [0, 1], "c": [0, 1]})
    arr = build(m, strength=2)
    check(len(arr.prevented) == 0, "3x binary: nothing should be prevented")
    check(len(arr.covered) == 12, f"3x binary: expected 12 pairs, got {len(arr.covered)}")
    check(len(arr.rows) >= 4, f"3x binary: expected >=4 rows, got {len(arr.rows)}")

    # 2. Every row satisfies every constraint, and every reachable pair really appears.
    #    This is the property that matters: a covering array that quietly drops a pair
    #    is the exact failure this module exists to prevent.
    m2 = parse_model(
        """
parameters:
  purpose:        [Buy, Rent]
  frequency:      [Yearly, Monthly, "N/A"]
  beds:           [Studio, "1", "3"]
constraints:
  - id: C1
    rule: "frequency only applies to Rent"
    expr: "purpose == 'Rent' or frequency == 'N/A'"
  - id: C2
    rule: "Rent must have a real frequency"
    expr: "purpose != 'Rent' or frequency != 'N/A'"
"""
    )
    arr2 = build(m2, strength=2)
    for row in arr2.rows:
        check(_violates(m2, row) is None, f"constrained: row violates a constraint: {row}")
    # Buy+Yearly, Buy+Monthly, Rent+N/A are impossible: 3 prevented pairs.
    check(
        len(arr2.prevented) == 3,
        f"constrained: expected 3 prevented pairs, got {len(arr2.prevented)} "
        f"({sorted(str(k) for k in arr2.prevented)})",
    )
    check(
        all(v in {"C1", "C2"} for v in arr2.prevented.values()),
        f"constrained: prevented pairs should be blamed on C1/C2, got {arr2.prevented}",
    )
    # Independently verify coverage by brute force rather than trusting `covered`.
    reachable = set()
    for combo_names in itertools.combinations(m2.parameters, 2):
        for values in itertools.product(*(m2.parameters[n] for n in combo_names)):
            fixed = dict(zip(combo_names, values))
            if _complete(m2, list(m2.parameters), fixed) is not None:
                reachable.add(_combination_key(list(fixed.items())))
    actually_covered = set()
    for row in arr2.rows:
        for combo_names in itertools.combinations(m2.parameters, 2):
            actually_covered.add(_combination_key([(n, row[n]) for n in combo_names]))
    check(
        reachable <= actually_covered,
        f"constrained: {len(reachable - actually_covered)} reachable pair(s) missing "
        f"from the array",
    )

    # 3. Determinism — same model in, byte-identical array out (D-003: reproducible).
    check(
        render_markdown(build(m2, 2)) == render_markdown(build(m2, 2)),
        "determinism: two runs produced different arrays",
    )

    # 4. A contradictory model prevents everything rather than silently emitting rows.
    m3 = parse_model(
        """
parameters:
  x: [1, 2]
constraints:
  - id: X1
    rule: "impossible"
    expr: "x == 1 and x == 2"
"""
    )
    arr3 = build(m3, strength=1)
    check(len(arr3.rows) == 0, "contradiction: expected no rows")
    check(len(arr3.prevented) == 2, "contradiction: expected both values prevented")

    # 5. Malformed models fail loudly, never silently.
    for bad, label in [
        ("parameters: {}", "empty parameters"),
        ("parameters:\n  a: []", "parameter with no values"),
        (
            "parameters:\n  a: [1]\nconstraints:\n  - id: C1\n    rule: r\n"
            "    expr: \"zzz == 1\"",
            "constraint on unknown parameter",
        ),
        ("parameters:\n  a: [1]\nconstraints:\n  - id: C1\n    rule: r", "constraint with no expr"),
    ]:
        try:
            parse_model(bad)
        except PairwiseError:
            checks += 1
        else:
            checks += 1
            failures.append(f"malformed model accepted: {label}")

    # 6. The real repo model parses and produces a sane array. filter-inventory.md's own
    #    sanity note: "If pairwise.py returns fewer than ~25 rows, a constraint is
    #    over-broad". Assert the tool agrees with the file's stated expectation.
    inventory = Path(__file__).resolve().parent.parent / "context" / "filter-inventory.md"
    if inventory.exists():
        real = parse_model(inventory.read_text(encoding="utf-8"))
        real_arr = build(real, strength=2)
        check(
            len(real_arr.rows) >= 25,
            f"filter-inventory.md: {len(real_arr.rows)} rows is below the file's own "
            f"stated sanity floor of ~25 — a constraint is likely over-broad",
        )
        for row in real_arr.rows:
            if _violates(real, row) is not None:
                failures.append(f"filter-inventory.md: row violates a constraint: {row}")
                break
        checks += 1

    print(f"selftest: {checks - len(failures)}/{checks} assertions passed")
    for f in failures:
        print(f"  FAIL: {f}")
    if failures:
        print("Covering-array generation is NOT trustworthy. Do not use the output.")
        return 1
    print("Covering arrays are complete, constraint-clean and deterministic.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_generate(args: argparse.Namespace) -> int:
    path = Path(args.input)
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    model = parse_model(path.read_text(encoding="utf-8"))
    array = build(model, strength=args.strength)

    if args.json:
        Path(args.json).write_text(render_json(array), encoding="utf-8")
        print(f"wrote {args.json}")
    if args.format == "markdown":
        print(render_markdown(array, case_prefix=args.case_prefix))
    else:
        print(render_json(array))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Constrained t-wise covering arrays. Combinatorics live here, "
                    "never in a prompt (docs/DECISIONS.md D-003).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="build a covering array from a model")
    g.add_argument("--input", required=True,
                   help="YAML file, or Markdown containing a ```yaml parameter block "
                        "(e.g. context/filter-inventory.md)")
    g.add_argument("--strength", type=int, default=2,
                   help="t in t-wise; 2 = pairwise (default)")
    g.add_argument("--format", choices=["markdown", "json"], default="markdown")
    g.add_argument("--json", default=None, help="also write raw JSON to this path")
    g.add_argument("--case-prefix", default="PW",
                   help="prefix for generated row ids (default: PW)")
    g.set_defaults(func=_cmd_generate)

    s = sub.add_parser("selftest", help="verify the generator against known answers")
    s.set_defaults(func=lambda _a: _selftest())

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except PairwiseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
