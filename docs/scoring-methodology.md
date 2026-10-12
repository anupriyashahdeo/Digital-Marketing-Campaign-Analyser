# Scoring methodology

Views, likes, comments and publish date alone cannot prove an ad is a winner.

| Signal | Source |
|---|---|
| Longevity | Ad feed first/last date shown, variants, re-runs |
| Relative engagement | z-score of views/day and engagement rate vs the SAME channel's recent videos |
| Creative quality | Jev/Claude answers (describes the ad, not results) |
| Evidence level | organic_only / paid_confirmed / own_account_verified |

Labels: Winner (paid + long run + 2+ variants + above baseline), Promising, Watch,
Dog (short run, not re-run, below baseline), Unrated (organic only).
Never label Winner/Dog from views alone. Calibrate thresholds against own-account data
and the 200-ad hand-labelled set (`eval/labels`). Code: `apps/api/src/ada/domain/scoring`.
