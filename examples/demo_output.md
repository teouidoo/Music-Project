# Demo output (real run, 2026-08-10)

Tracks below were generated live via the Eleven Music API (audio files are
gitignored; regenerate with `python -m rightsflow.cli demo`).

## 1. Generated tracks
```
[eleven-1786389510-001] (30000ms, mock=False)  warm analog synthwave, 100 bpm, nostalgic but forward-looking
[eleven-1786389521-002] (30000ms, mock=False)  female k-pop vocal over bright future-bass, bilingual hook
[eleven-1786389532-003] (30000ms, mock=False)  cinematic strings building to a hopeful resolution, sync-ready
```

## 2. Waterfall ($1M gross, baseline scenario)
```
SCENARIO: Baseline opt-in indie pool
  Opt-in usage-proportional pool in the shape of the Aug-2025 Merlin/Kobalt architecture: platform retains 55%, royalty pool split 50/50 recorded/publishing (the Kobalt parity precedent, later the NMPA industry norm). Weights = training-inclusion x output-popularity, normalized per side. All names and numbers synthetic.

  Gross revenue                   $1,000,000.00
  Platform retained (55%)          $550,000.00
  Rights-holder royalty pool        $450,000.00
    Recorded pool (50%)            $225,000.00
    Publishing pool (50%)          $225,000.00

  RIGHTS HOLDER               SIDE          WEIGHT          PAYOUT
  Indie Label A               recorded           5     $112,500.00
  Indie Label B               recorded           3      $67,500.00
  Indie Label C               recorded           2      $45,000.00
  Publisher X                 publishing         6     $135,000.00
  Publisher Y                 publishing         4      $90,000.00
                                                  ----------------
  TOTAL PAID (ties to pool)                            $450,000.00
```

## 3. Decision lens + sensitivity
```
DECISION LENS: Indie Label A
  (5yr horizon, 12% discount, pool growth 50%, addressable income $2,000,000.00/yr)

  + Royalty stream NPV                          $979,607.87
  + Substitution loss avoided NPV               $400,071.69
    (staying out concedes AI-shifted spend at 10% terminal)
  - Cannibalization cost NPV                    $120,021.51
    (licensed outputs displacing own income at 3% terminal)
                                           ----------------
  = License advantage NPV                     $1,259,658.05

  VERDICT: LICENSE
  Breakeven cannibalization: 34.5% terminal - licensing pays unless AI outputs displace more than 34.5% of this holder's addressable income by year 5.

SENSITIVITY: license advantage NPV  (rows: pool growth / cols: terminal substitution)
                      0%            5%           10%           20%
        0%   $285,515.81   $485,551.65   $685,587.50 $1,085,659.19
       25%   $513,136.57   $713,172.41   $913,208.26 $1,313,279.95
       50%   $859,586.36 $1,059,622.20 $1,259,658.05 $1,659,729.74
      100% $2,073,429.26 $2,273,465.10 $2,473,500.95 $2,873,572.64
```
