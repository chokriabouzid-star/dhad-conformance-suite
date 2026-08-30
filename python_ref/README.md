# Dhad Python Reference

Independent Python reference implementation for Dhad conformance.

## Status

| Mode | Vectors | Result |
|------|---------|--------|
| Mode A (golden.json) | 116 | 116/116 |
| Mode A (adversarial.json) | 40 | 40/40 |
| Mode B (tagged.json) | 36 | 36/36 |
| **Total** | **195** | **195/195** |

Full parity achieved:

- success vectors: exact stream, CoreHash, PhoneticHash
- error vectors: exact error object including all fields and reason strings

## Files

- `dhad_ref.py` — Python reference implementation (Mode A + Mode B)
- `verify_tagged_ref.py` — verifies Mode B against `vectors/tagged.json`
- `verify_golden_ref.py` — verifies Mode A against `vectors/golden.json` and `vectors/adversarial.json`

## Run

```bash
python3 python_ref/verify_tagged_ref.py
python3 python_ref/verify_golden_ref.py
Expected:

text

tagged.json: 36/36 vectors matched in Phase 2
ALL TAGGED VECTORS MATCH (Phase 2: exact ok outputs + full error object parity)

golden.json: 116/116
adversarial.json: 40/40
ALL MODE A VECTORS MATCH
Dependencies
Python 3.10+ standard library only. No external packages.
