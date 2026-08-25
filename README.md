# rightsflow

[![tests](https://github.com/teouidoo/Music-Project/actions/workflows/tests.yml/badge.svg)](https://github.com/teouidoo/Music-Project/actions/workflows/tests.yml)

**Rights-holder economics for AI-generated music — built on the [Eleven Music API](https://elevenlabs.io/music).**

I run strategy and licensing economics across a group of music companies — labels, distribution,
artist management — which means when an AI platform asks a rights holder to license a catalog,
I'm the side of the table that has to decide. This prototype combines an Eleven Music generation
demo with an explicit, scenario-driven royalty model for testing what a licensing "yes" could be
worth — to the platform and modeled recorded/publishing rights holders. The API does not provide rights-holder attribution;
usage weights are declared inputs and are labeled as such throughout the project.

Most AI-music commentary argues about vibes. This argues about waterfalls.

## What it does

1. **Generates music** via the Eleven Music API, or through an explicitly selected and clearly
   labeled mock mode. Real mode fails closed when credentials are unavailable.
2. **Runs the royalty waterfall** of an opt-in license: gross revenue → platform share →
   rights-holder pool → a configurable recorded/publishing split → per-rights-holder
   allocation, proportional to declared catalog-inclusion and usage assumptions. Distributed
   amounts and explicitly undistributed pools reconcile **to the cent**
   (largest-remainder allocation; conservation is enforced by tests, because a royalty statement
   that doesn't tie out is how trust dies in this industry).
3. **Answers the rights holder's real question** — license or abstain — as an explicit NPV frame:
   royalties gained, substitution loss avoided (staying out doesn't preserve the status quo; it
   concedes AI-shifted spend to catalogs that did opt in), cannibalization risked. Plus the
   breakeven: how bad would cannibalization have to be to flip the answer?

## Quickstart

```bash
git clone https://github.com/teouidoo/Music-Project.git
cd Music-Project
pip install -e ".[dev]"        # no hard dependencies; pytest for tests
pytest                          # conservation, validation, API-wrapper and breakeven tests

python -m rightsflow.cli demo --mock   # explicit offline demonstration

# real generation:
pip install "rightsflow[eleven]"   # pulls the official elevenlabs SDK
export ELEVENLABS_API_KEY=...   # env only - this repo never stores or logs keys
python -m rightsflow.cli demo          # fails closed if the key is unavailable
```

### The waterfall, on $1,000,000 of AI-music revenue (baseline scenario)

```
  Gross revenue                   $1,000,000.00
  Platform retained (55%)           $550,000.00
  Rights-holder royalty pool        $450,000.00
    Recorded pool (50%)             $225,000.00
    Publishing pool (50%)           $225,000.00

  RIGHTS HOLDER               SIDE          WEIGHT          PAYOUT
  Indie Label A               recorded           5     $112,500.00
  Indie Label B               recorded           3      $67,500.00
  Indie Label C               recorded           2      $45,000.00
  Publisher X                 publishing         6     $135,000.00
  Publisher Y                 publishing         4      $90,000.00
  TOTAL PAID (ties to pool)                            $450,000.00
```

### The decision lens

```bash
python -m rightsflow.cli decide --scenario scenarios/baseline_indie_pool.json \
    --revenue 1000000 --holder "Indie Label A" \
    --growth 0.5 --substitution 0.10 --cannibalization 0.03 --sensitivity
```

For a label holding half the recorded-side weight and $2M of sync/production income exposed
to AI substitution, licensing typically wins — and the tool tells you exactly how much displacement
of your own catalog it would take to flip that verdict. Argue with the inputs, not the
arithmetic; that's the point.

Scenarios are plain JSON (`scenarios/`). `enterprise_sync.json` models the deal shape I find
most interesting commercially: a synthetic enterprise/sync-scoped licensing thesis with a larger
rights-holder share. The current scenario does not model minimum guarantees, per-use sync pricing,
indemnity reserves, sales costs, or confidential deal terms.

## What the Eleven Music licensing architecture gets right

Having sat on the licensor side of distribution and DSP negotiations, three design choices
stand out:

- **Opt-in, not opt-out.** Consent as the foundation rather than the concession. It is slower
  and smaller than scraping — and it is why this platform is building deals while its
  competitors were building legal defenses.
- **Royalty parity between recordings and songs.** The included 50/50 scenario illustrates a
  more composition-friendly alternative to recorded-heavy streaming economics; it is a synthetic
  assumption, not a representation of confidential ElevenLabs terms.
- **Usage-proportional payout.** The engine allocates against explicit weights and now supports
  track-linked, operator-declared usage events. Those events are traceable inputs, not attribution
  supplied by ElevenLabs.

**What I'd add:** a per-output provenance surface — an auditable statement of which opted-in
catalogs influenced a given generated track, exposed at the API level. Enterprises buying
indemnified music will increasingly need it, EU AI Act training-transparency obligations are
pulling the whole industry toward it, and the first platform to make provenance a *product*
rather than a compliance artifact turns clean licensing from a cost into a moat.

## Honest limitations

- The waterfall is a faithful *shape*, not any platform's actual confidential terms; all
  scenario names and numbers are synthetic.
- The decision lens is a frame for arguing about assumptions, not a market forecast.
- Weights collapse "training inclusion × output popularity" into one declared number. The
  `rightsflow.usage` module links those declarations to track IDs and enforces conservation, but
  real model-derived attribution remains an open technical problem (see: what I'd add).
- The license-versus-abstain model is an assumption-driven comparison, not a recommendation.
  `--avoidance` explicitly controls what fraction of modeled abstention substitution loss licensing
  is assumed to prevent; the demo uses 50% rather than silently assuming complete avoidance.
- Track-linked allocations round at the individual usage-event level. Splitting or aggregating
  micro-events can therefore change results by cents; this is an explicit statement-policy choice,
  not a claim of granularity invariance.

## Audit trail and provenance

Generation manifests use the versioned `rightsflow.manifest/1` schema and record local track ID,
UTC timestamp, requested model, prompt, duration, byte count, SHA-256 digest, rightsflow version,
and installed SDK version. Audio and manifests are written atomically. This is an operational
audit trail, not proof of catalog influence: every manifest says explicitly that the integration
does not receive per-output rights-holder attribution from Eleven Music.

## About

Personal project by Thomas Kim ([thomas.wj.kim@gmail.com](mailto:thomas.wj.kim@gmail.com)) — music
executive and investor; Stanford MBA '26. Not affiliated with ElevenLabs. MIT licensed.
