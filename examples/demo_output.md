# Demo output

## 1. Generated tracks (real run, 2026-08-10)

Tracks below were generated live via the Eleven Music API (audio files are gitignored;
regenerate with `python -m rightsflow.cli demo`, or `--mock` for an explicit offline run).
```
[eleven-1786389510-001] (30000ms, mock=False)  warm analog synthwave, 100 bpm, nostalgic but forward-looking
[eleven-1786389521-002] (30000ms, mock=False)  female k-pop vocal over bright future-bass, bilingual hook
[eleven-1786389532-003] (30000ms, mock=False)  cinematic strings building to a hopeful resolution, sync-ready
```

Sections 2-4 below are regenerated from rightsflow 0.2.0 (`python -m rightsflow.cli demo --mock`).
The economics do not depend on the generated audio; the decision lens now applies an explicit
`--avoidance` assumption (default 50%) rather than assuming licensing prevents all substitution loss.

## 2. Waterfall ($1M gross, baseline scenario)
```
  Illustrative opt-in pool: platform retains 55%, the royalty pool is split 50/50 between recorded music and publishing, and synthetic weights are normalized within each side. These are configurable modeling assumptions, not reported terms of ElevenLabs or any partner. All names and numbers are synthetic.

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
  TOTAL PAID                                           $450,000.00
  TOTAL PAID (ties to pool)                            $450,000.00
```

## 3. Decision lens
```
DECISION LENS: Indie Label A
  (5yr horizon, 12% discount, pool growth 50%, addressable income $2,000,000.00/yr)

  + Royalty stream NPV                          $979,607.87
  + Substitution loss avoided NPV               $200,035.84
    (50% of modeled abstention loss avoided; 10% terminal exposure)
  - Cannibalization cost NPV                    $120,021.51
    (licensed outputs displacing own income at 3% terminal)
                                           ----------------
  = License advantage NPV                     $1,059,622.20

  VERDICT: LICENSE
  Breakeven cannibalization: 29.5% terminal - licensing pays unless AI outputs displace more than 29.5% of this holder's addressable income by year 5.
```

## 4. Sensitivity
```
SENSITIVITY: license advantage NPV  (rows: pool growth / cols: terminal substitution)
                      0%            5%           10%           20%
        0%   $285,515.81   $385,533.73   $485,551.65   $685,587.50
       25%   $513,136.57   $613,154.49   $713,172.41   $913,208.26
       50%   $859,586.36   $959,604.28 $1,059,622.20 $1,259,658.05
      100% $2,073,429.26 $2,173,447.18 $2,273,465.10 $2,473,500.95
```
