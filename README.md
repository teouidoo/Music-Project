# rightsflow

**Rights-holder economics for AI-generated music — built on the [Eleven Music API](https://elevenlabs.io/music).**

I run strategy and licensing economics across a group of music companies — labels, distribution,
artist management — which means when an AI platform asks a rights holder to license a catalog,
I'm the side of the table that has to decide. This tool is the analysis I would actually run
before signing: generate real tracks with the Eleven Music API, then follow the money through
an opt-in, usage-proportional license to see what a "yes" is worth — to the platform, to the
label, and to the songwriter.

Most AI-music commentary argues about vibes. This argues about waterfalls.

## What it does

1. **Generates music** via the Eleven Music API (or a labeled mock mode, so the economics run
   without credentials).
2. **Runs the royalty waterfall** of an opt-in license: gross revenue → platform share →
   rights-holder pool → recorded/publishing split (the 50/50 parity precedent the
   ElevenLabs–Kobalt deal set in 2025, later the NMPA industry norm) → per-rights-holder
   allocation, proportional to catalog inclusion and usage. Every level ties out **to the cent**
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
pytest                          # 13 tests: conservation, known values, breakevens

python -m rightsflow.cli demo   # end-to-end, mock generation if no key is set

# real generation:
pip install elevenlabs
export ELEVENLABS_API_KEY=...   # env only - this repo never stores or logs keys
python -m rightsflow.cli demo
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

For a label with a 2%-weight catalog and $2M of sync/production income exposed to AI
substitution, licensing typically wins — and the tool tells you exactly how much displacement
of your own catalog it would take to flip that verdict. Argue with the inputs, not the
arithmetic; that's the point.

Scenarios are plain JSON (`scenarios/`). `enterprise_sync.json` models the deal shape I find
most interesting commercially: enterprise/sync-scoped licensing at a premium, where
indemnified-and-cleared is what buyers are actually paying for — and the contained, non-consumer
scope is the shape that could plausibly bring a major label into a licensed pool.

## What the Eleven Music licensing architecture gets right

Having sat on the licensor side of distribution and DSP negotiations, three design choices
stand out:

- **Opt-in, not opt-out.** Consent as the foundation rather than the concession. It is slower
  and smaller than scraping — and it is why this platform is building deals while its
  competitors were building legal defenses.
- **Royalty parity between recordings and songs.** The 50/50 split broke with streaming's
  recorded-heavy economics and became the industry's reference point within a year. Songwriters
  noticed.
- **Usage-proportional payout.** Royalties that follow actual influence on outputs are auditable
  in principle — which is what makes the next item possible.

**What I'd add:** a per-output provenance surface — an auditable statement of which opted-in
catalogs influenced a given generated track, exposed at the API level. Enterprises buying
indemnified music will increasingly need it, EU AI Act training-transparency obligations are
pulling the whole industry toward it, and the first platform to make provenance a *product*
rather than a compliance artifact turns clean licensing from a cost into a moat.

## Honest limitations

- The waterfall is a faithful *shape*, not any platform's actual confidential terms; all
  scenario names and numbers are synthetic.
- The decision lens is a frame for arguing about assumptions, not a market forecast.
- Weights collapse "training inclusion × output popularity" into one number; real attribution
  is an open technical problem (see: what I'd add).

## About

Personal project by Thomas Kim ([tkim1993@gmail.com](mailto:tkim1993@gmail.com)) — music
executive and investor; Stanford MBA '26. Not affiliated with ElevenLabs. MIT licensed.
