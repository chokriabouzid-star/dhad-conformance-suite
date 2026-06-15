# Dhad Python Reference

This directory contains the independent Python reference implementation work for
Dhad conformance.

## Phase 1 scope

Current scope:

- Mode B only
- parse tagged binary frame input
- validate frame structure
- parse atoms
- enforce the invariant subset required by `vectors/tagged.json`
- recompute `CoreHash`
- recompute `PhoneticHash`
- verify all Mode B success vectors exactly
- verify Mode B error **kind** parity

## Not yet in Phase 1

- full Mode A reimplementation
- exact field parity for every Mode B error object
- full spec-wide invariant coverage outside current corpus needs

## Run

```bash
python3 python_ref/verify_tagged_ref.py
