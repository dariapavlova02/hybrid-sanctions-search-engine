# Golden Parity Summary

- Total cases: **31**
- Parity: **93.5%**
- Legacy p95/p99: **0.0032s / 0.0043s**
- Factory p95/p99: **0.0012s / 0.0014s**

## Failing cases

- `en_title_suffix` [en]:
  - input: `Dr. John A. Smith Jr.`
  - legacy: `John A. Smith`
  - factory: `John A. Smith Jr.`
  - expected: `John Smith`
  - traces: legacy=0b6bf0a1 factory=ee3aec24
- `en_apostrophe` [en]:
  - input: `O'Connor, Sean`
  - legacy: `Sean O connor`
  - factory: `Sean O Connor`
  - expected: `Sean O’Connor`
  - traces: legacy=113409e3 factory=56333880
