# Dhad Conformance Suite

Language-agnostic conformance vectors for the Dhad protocol.

## Purpose

This repository contains the canonical conformance corpus for Dhad.

It exists to keep protocol-level conformance artifacts independent from any
single implementation repository or programming language.

Its role is to provide a stable, byte-exact, implementation-neutral set of:

- Mode A success vectors
- Mode A rejection / adversarial vectors
- Mode B tagged binary vectors
- the normative vector schema used by all implementations

This repository is the public conformance artifact layer.

The Rust repository remains the primary implementation source:

- https://github.com/chokriabouzid-star/dhad

Published crate:

- https://crates.io/crates/dhad

---

## Governing principles

### 1. Spec before code
The vector format is defined explicitly before generators or readers are written.

### 2. Anchors are normative
The four foundational anchors are immutable conformance seeds.

Any implementation that disagrees with them is wrong.

### 3. Independence by design
Files in this repository must be understandable without reading Rust code.

---

## Repository layout

- `schema/vector-schema-1.0.md`
  - Normative schema definition for vector JSON files

- `vectors/golden.json`
  - Mode A success vectors

- `vectors/adversarial.json`
  - Mode A error and adversarial vectors

- `vectors/tagged.json`
  - Mode B tagged-frame vectors

- `tools/verify_vectors.py`
  - Dependency-free Python verifier for the published vector corpus

---

## Current corpus (v1.2.x bootstrap)

| File | Suite | Mode | Vectors | ok | err |
|------|-------|------|---------|----|-----|
| `vectors/golden.json` | golden | A | 116 | 116 | 0 |
| `vectors/adversarial.json` | adversarial | A | 39 | 3 | 36 |
| `vectors/tagged.json` | tagged | B | 32 | 9 | 21 |
| **Total** | | | **187** | **128** | **57** |

Schema version:

- `1.0`

Normative Dhad specification:

- https://github.com/chokriabouzid-star/dhad/blob/main/specification.md

---

## Verification

The corpus can be verified without Rust dependencies.

```bash
python3 tools/verify_vectors.py
Expected result:

text

golden.json: OK ...
adversarial.json: OK ...
tagged.json: OK ...
anchors: OK (4 found)
total vectors verified: 187
ALL VECTOR FILES VERIFIED
The verifier checks:

top-level schema structure
hex and repeat_byte input encodings
error object field contracts
recomputed CoreHash from stream_hex
recomputed PhoneticHash from stream_hex
presence of all four mandatory anchors
Mandatory anchors
The corpus must expose these four stream anchors:

Anchor	Stream hex	Meaning
ANCHOR-001	""	empty stream
ANCHOR-002	0100000000000000	ALEF bare
ANCHOR-003	0200000000000000	BEH bare
ANCHOR-004	0200010000000000	BEH + FATHA
These anchors are normative.

Generation policy
The JSON files in this repository are canonical published artifacts.

They are generated from the dhad implementation repository and then checked
into this repository as stable conformance corpus files.

They must not be edited casually by hand.

If vectors change, the change must be accompanied by:

an explicit reason
regenerated artifacts
verifier success
a documented contract update if schema semantics changed
Status
Current status:

schema defined
corpus populated
Python verifier present
cross-language hash verification complete
full Python protocol reimplementation complete (187/187 match)
This repository does not replace the Dhad specification.
It carries conformance artifacts for independent implementations.

License
MIT.
