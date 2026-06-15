# Dhad Python Reference

This directory contains the independent Python reference implementation work for
Dhad conformance.

## Current status

### Mode B
Mode B is currently implemented and verified against the published corpus.

Implemented:

- tagged binary frame parsing
- frame structure validation
- CRC validation
- atom parsing
- invariant subset required by `vectors/tagged.json`
- CoreHash recomputation
- PhoneticHash recomputation

Verification status:

- `tagged.json`: **30/30 vectors match**
- success vectors: exact stream/hash parity
- error vectors: exact full error object parity

### Mode A
Mode A independent reimplementation has **not started yet**.

Planned next steps:

1. corpus inventory for `golden.json` and `adversarial.json`
2. minimal successful Mode A path
3. full Mode A error parity

## Files

- `dhad_ref.py`
  - Python reference implementation logic (currently Mode B)
- `verify_tagged_ref.py`
  - Verifies the Python reference against `vectors/tagged.json`

## Run

```bash
python3 python_ref/verify_tagged_ref.py
Expected result:

text

tagged.json: 30/30 vectors matched in Phase 2
ALL TAGGED VECTORS MATCH (Phase 2: exact ok outputs + full error object parity)
