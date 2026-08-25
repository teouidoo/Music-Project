"""rightsflow CLI.

  rightsflow demo                          end-to-end: generate (mock) -> waterfall -> decision
  rightsflow simulate --scenario F --revenue N
  rightsflow decide   --scenario F --revenue N --holder NAME [economics flags]
  rightsflow generate --prompt "..." [--length-ms N] [--mock]
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path

from .decision import DecisionInputs, evaluate, sensitivity_grid
from .generate import MissingCredentialsError, generate_track, save_manifest
from .report import render_decision, render_sensitivity, render_waterfall
from .waterfall import RightsHolder, Scenario, run_waterfall


def load_scenario(path: str) -> Scenario:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return Scenario(
        name=raw["name"],
        description=raw["description"],
        platform_share=Decimal(str(raw["platform_share"])),
        recorded_share=Decimal(str(raw["recorded_share"])),
        publishing_share=Decimal(str(raw["publishing_share"])),
        rightsholders=tuple(
            RightsHolder(name=h["name"], side=h["side"], weight=Decimal(str(h["weight"])), id=h.get("id", ""))
            for h in raw["rightsholders"]
        ),
    )


def _decision_inputs(args, scenario: Scenario) -> DecisionInputs:
    return DecisionInputs(
        scenario=scenario,
        holder_name=args.holder,
        pool_gross_revenue=Decimal(str(args.revenue)),
        pool_growth=args.growth,
        discount_rate=args.discount,
        years=args.years,
        addressable_income=Decimal(str(args.addressable_income)),
        terminal_substitution=args.substitution,
        cannibalization_rate=args.cannibalization,
        substitution_avoidance_fraction=args.avoidance,
    )


def cmd_simulate(args):
    scenario = load_scenario(args.scenario)
    print(render_waterfall(run_waterfall(scenario, Decimal(str(args.revenue)))))


def cmd_decide(args):
    scenario = load_scenario(args.scenario)
    inputs = _decision_inputs(args, scenario)
    print(render_decision(inputs, evaluate(inputs)))
    if args.sensitivity:
        growth_axis = [0.0, 0.25, 0.5, 1.0]
        sub_axis = [0.0, 0.05, 0.10, 0.20]
        print()
        print(render_sensitivity(growth_axis, sub_axis, sensitivity_grid(inputs, growth_axis, sub_axis)))


def cmd_generate(args):
    track = generate_track(args.prompt, length_ms=args.length_ms, mock=args.mock)
    print(json.dumps(track.__dict__, indent=2))


def cmd_demo(args):
    root = Path(__file__).resolve().parent.parent
    scenario = load_scenario(str(root / "scenarios" / "baseline_indie_pool.json"))

    print("=" * 76)
    print("rightsflow demo - the money behind an opt-in AI music license")
    print("=" * 76)
    print()

    prompts = [
        "warm analog synthwave, 100 bpm, nostalgic but forward-looking",
        "female k-pop vocal over bright future-bass, bilingual hook",
        "cinematic strings building to a hopeful resolution, sync-ready",
    ]
    tracks = []
    manifest_path = str(root / "examples" / "generated" / "manifest.json")
    for i, prompt in enumerate(prompts):
        tracks.append(generate_track(prompt, mock=args.mock, index=i + 1))
        save_manifest(tracks, manifest_path)  # journal each successful paid generation
    manifest = manifest_path
    print(f"1) GENERATED {len(tracks)} tracks ({'mock' if tracks[0].mock else 'Eleven Music API'}) -> {manifest}")
    for t in tracks:
        print(f"   - [{t.track_id}] {t.prompt}")
    print()

    revenue = Decimal("1000000")
    print(f"2) WATERFALL - {render_waterfall(run_waterfall(scenario, revenue)).lstrip()}")
    print()

    args2 = argparse.Namespace(
        holder="Indie Label A",
        revenue=revenue,
        growth=0.5,
        discount=0.12,
        years=5,
        addressable_income=Decimal("2000000"),
        substitution=0.10,
        cannibalization=0.03,
        avoidance=0.5,
    )
    inputs = _decision_inputs(args2, scenario)
    print("3) " + render_decision(inputs, evaluate(inputs)))
    print()
    growth_axis = [0.0, 0.25, 0.5, 1.0]
    sub_axis = [0.0, 0.05, 0.10, 0.20]
    print("4) " + render_sensitivity(growth_axis, sub_axis, sensitivity_grid(inputs, growth_axis, sub_axis)))


def main(argv=None):
    p = argparse.ArgumentParser(prog="rightsflow", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("simulate", help="run a royalty waterfall for a scenario")
    sp.add_argument("--scenario", required=True)
    sp.add_argument("--revenue", required=True, type=Decimal)
    sp.set_defaults(func=cmd_simulate)

    dp = sub.add_parser("decide", help="license-vs-abstain lens for one rights holder")
    dp.add_argument("--scenario", required=True)
    dp.add_argument("--revenue", required=True, type=Decimal)
    dp.add_argument("--holder", required=True)
    dp.add_argument("--growth", type=float, default=0.5)
    dp.add_argument("--discount", type=float, default=0.12)
    dp.add_argument("--years", type=int, default=5)
    dp.add_argument("--addressable-income", type=Decimal, default=Decimal("2000000"))
    dp.add_argument("--substitution", type=float, default=0.10)
    dp.add_argument("--cannibalization", type=float, default=0.03)
    dp.add_argument("--avoidance", type=float, default=0.5,
                    help="fraction of abstention substitution loss avoided by licensing")
    dp.add_argument("--sensitivity", action="store_true")
    dp.set_defaults(func=cmd_decide)

    gp = sub.add_parser("generate", help="generate a track via the Eleven Music API (or mock)")
    gp.add_argument("--prompt", required=True)
    gp.add_argument("--length-ms", type=int, default=30_000)
    gp.add_argument("--mock", action="store_true", help="explicitly use offline mock generation")
    gp.set_defaults(func=cmd_generate)

    dm = sub.add_parser("demo", help="end-to-end demo: generate -> waterfall -> decision")
    dm.add_argument("--mock", action="store_true", help="explicitly use offline mock generation")
    dm.set_defaults(func=cmd_demo)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except MissingCredentialsError as exc:
        p.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
