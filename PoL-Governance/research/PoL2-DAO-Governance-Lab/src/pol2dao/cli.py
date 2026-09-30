"""Command line: ``pol2dao {demo,simulate,published,replay,verify}``."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import replay, simulate
from .ledger import DecisionChain

ROOT = Path(__file__).resolve().parents[2]


def _have_matplotlib() -> bool:
    import importlib.util

    if importlib.util.find_spec("matplotlib") is None:
        print("matplotlib not installed; skipping figures (pip install -e .[plot])")
        return False
    return True


def _results(args) -> Path:
    p = Path(args.out)
    p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_demo(args) -> int:
    from .demo import run_demo

    decision, chain, path = run_demo(Path(args.out) / "demo_decision_chain.jsonl")
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
    ok, bad = chain.verify()
    print(f"\n{len(chain)} entries written to {path}; chain intact: {ok}")
    return 0


def cmd_simulate(args) -> int:
    out = _results(args)
    rows = simulate.run_grid(reps=args.reps, seed=args.seed)
    path = simulate.write_csv(rows, out / "tables" / "simulation_summary.csv")
    print(f"wrote {path} ({len(rows)} rows)")
    if not args.no_figures and _have_matplotlib():
        from .figures import simulation_figure

        for metric, label in (("minority_win", "P(minority's option wins)"),
                              ("regret", "equal-weight regret")):
            for p in simulation_figure(rows, metric, out / "figures" / f"simulation_{metric}", label):
                print(f"wrote {p}")
    return 0


def cmd_published(args) -> int:
    out = _results(args)
    rows = replay.from_published()
    path = replay.write_rows(rows, out / "tables" / "published_equal_budget_counterfactual.csv")
    for r in rows:
        print(r)
    print(f"wrote {path}")
    if not args.no_figures and _have_matplotlib():
        from .figures import published_counterfactual_figure

        for p in published_counterfactual_figure(ROOT / "data" / "sharma2026_token_totals.csv",
                                                 ROOT / "data" / "sharma2026_table1_means.csv",
                                                 out / "figures" / "published_equal_budget_counterfactual"):
            print(f"wrote {p}")
    return 0


def cmd_replay(args) -> int:
    rows = replay.replay_osf(replay.read_osf_votes(args.data_dir), boot=args.boot,
                             include_pilots=not args.exclude_pilots)
    path = replay.write_rows(rows, _results(args) / "tables" / "osf_equal_budget_replay.csv")
    for r in rows:
        print(r)
    print(f"wrote {path}")
    return 0


def cmd_experiments(args) -> int:
    if not _have_matplotlib():
        return 1
    from . import experiments

    only = [x.strip().upper() for x in args.only.split(",")] if args.only else None
    res = experiments.run(_results(args), args.reps, only)
    for eid, paths in res.items():
        for p in paths:
            print(f"{eid}: wrote {p}")
    return 0


def cmd_verify(args) -> int:
    chain = DecisionChain.from_jsonl(args.path)
    ok, bad = chain.verify()
    print(f"{len(chain)} entries, head {chain.head[:16]}…: " + ("intact" if ok else f"BROKEN at entry {bad}"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pol2dao", description="PoL2 x DAO governance lab")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("demo", help="run one PoL2 governance session and write its decision chain")
    p.add_argument("--out", default="results")
    p.set_defaults(fn=cmd_demo)

    p = sub.add_parser("simulate", help="agent-based comparison of DAO conditions")
    p.add_argument("--reps", type=int, default=1000)
    p.add_argument("--seed", type=int, default=20260929)
    p.add_argument("--out", default="results")
    p.add_argument("--no-figures", action="store_true")
    p.set_defaults(fn=cmd_simulate)

    p = sub.add_parser("published", help="equal-budget counterfactual from published numbers")
    p.add_argument("--out", default="results")
    p.add_argument("--no-figures", action="store_true")
    p.set_defaults(fn=cmd_published)

    p = sub.add_parser("replay", help="equal-budget replay of the OSF ballots (data not included)")
    p.add_argument("--data-dir", required=True)
    p.add_argument("--boot", type=int, default=2000)
    p.add_argument("--exclude-pilots", action="store_true")
    p.add_argument("--out", default="results")
    p.set_defaults(fn=cmd_replay)

    p = sub.add_parser("experiments", help="run the E0-E13 experiment suite (needs matplotlib)")
    p.add_argument("--only", default="", help="comma-separated ids, e.g. E1,E4")
    p.add_argument("--reps", type=int, default=1000)
    p.add_argument("--out", default="results")
    p.set_defaults(fn=cmd_experiments)

    p = sub.add_parser("verify", help="check a decision chain JSONL file")
    p.add_argument("path")
    p.set_defaults(fn=cmd_verify)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
