# Dhad Vector Schema v1.0

**Status:** Normative  
**Applies to:** Dhad conformance vector JSON files  
**Schema version:** `1.0`

---

## 1. Purpose

This document defines the JSON schema used for Dhad conformance vectors.

The schema is designed to be:

- language-agnostic
- byte-exact
- independent of Rust internals
- usable for both Mode A (UTF-8 input bytes) and Mode B (tagged binary frame bytes)

The schema represents protocol-level test vectors only.

It does not expose internal implementation stages, helper functions,
or language-specific runtime types.

---

## 2. Design principles

### 2.1 Spec before implementation
The vector schema is defined independently of any one implementation language.

### 2.2 Exact input preservation
Inputs are represented as exact bytes, not as host-language strings.

This is required because:

- Mode A may contain malformed UTF-8
- Mode B is binary by definition
- some vectors intentionally exceed normal text expectations

### 2.3 Output-level conformance
Vectors test protocol entrypoints and protocol outputs:

- success:
  - atom stream bytes
  - CoreHash
  - PhoneticHash
- failure:
  - typed error object

The schema does not require implementations to expose internal stages.

### 2.4 Anchor immutability
The four foundational anchors are immutable conformance anchors.
Any conforming implementation must match them exactly.

---

## 3. File structure

Each JSON file contains one top-level object with these fields:

- `schema_version`
- `dhad_spec`
- `generated_by`
- `suite`
- `mode`
- `source_suite`
- `vector_count`
- `vectors`

Example shape:

    {
      "schema_version": "1.0",
      "dhad_spec": "v1.3",
      "generated_by": "dhad-rust-1.2.x",
      "suite": "golden",
      "mode": "A",
      "source_suite": "tests/suite1_golden.rs",
      "vector_count": 116,
      "vectors": []
    }

---

## 4. Top-level fields

- `schema_version`
  - string
  - required
  - version of this JSON schema

- `dhad_spec`
  - string
  - required
  - Dhad specification revision described by the vectors

- `generated_by`
  - string
  - required
  - generator identifier; informational

- `suite`
  - string
  - required
  - logical vector suite name

- `mode`
  - string
  - required
  - either `"A"` or `"B"`

- `source_suite`
  - string
  - required
  - source test file from which the vectors were derived

- `vector_count`
  - integer
  - required
  - must equal the number of entries in `vectors`

- `vectors`
  - array
  - required
  - array of vector objects

Notes:

- `generated_by` is informational metadata and is not part of hash computation.
- `vector_count` is redundant by design and must match the actual array length.
- Official v1.3.x corpus files use `schema_version = "1.0"`.

---

## 5. Vector object

Each element in `vectors` is one protocol-level test vector.

### 5.1 Common fields

- `name`
  - string
  - required
  - stable vector identifier

- `mode`
  - string
  - required
  - `"A"` or `"B"`; must match file-level `mode`

- `input`
  - object
  - required
  - exact input bytes

- `expected_result`
  - string
  - required
  - either `"ok"` or `"err"`

### 5.2 Optional informational field

- `input_utf8_preview`
  - string
  - optional
  - human-readable preview for small valid UTF-8 Mode A inputs

`input_utf8_preview` is informational only.
The canonical input is always the `input` object.

---

## 6. Input encoding object

The `input` field is an object with an explicit encoding.

Two encodings are defined in schema v1.0.

### 6.1 `hex`

Used for ordinary byte-exact inputs.

Shape:

    {
      "encoding": "hex",
      "hex": "d8a8d990d8b3"
    }

Rules:

- `hex` is a lowercase hexadecimal string
- it encodes the exact byte sequence passed to the protocol entrypoint
- length must be even
- no separators
- no `0x` prefixes

### 6.2 `repeat_byte`

Used for exact but very large repeated-byte inputs, mainly to avoid bloating JSON.

Shape:

    {
      "encoding": "repeat_byte",
      "byte_hex": "d8",
      "count": 4194305
    }

This means:

    input bytes = count repetitions of the single byte byte_hex

Rules:

- `byte_hex` is exactly 2 lowercase hex characters
- `count` is a non-negative integer
- decoded input must be exactly reproducible from these two fields

Rationale:

This encoding exists to represent oversized adversarial inputs compactly,
without changing their exact byte identity.

---

## 7. Success vectors

If `expected_result == "ok"`, the vector must contain:

- `stream_hex`
- `core_hash_hex`
- `phonetic_hash_hex`

and must not contain `error`.

`stream_hex` is the exact atom stream wire format:

- concatenation of `n` atoms
- each atom is 8 bytes
- little-endian
- exactly the canonical atom-stream wire format

Per-atom byte layout:

- bytes 0..1: `base` (`u16`, little-endian)
- bytes 2..3: `marks` (`u16`, little-endian)
- byte 4: `flags` (`u8`)
- byte 5: `prosody` (`u8`)
- bytes 6..7: `reserved` (`u16`, little-endian)

For v1.x success vectors, `reserved` must be `0x0000` in every atom.

---

## 8. Error vectors

If `expected_result == "err"`, the vector must contain:

- `error`

and must not contain:

- `stream_hex`
- `core_hash_hex`
- `phonetic_hash_hex`

---

## 9. Error object schema

Every error object contains a required `kind` field.
Additional fields depend on the error kind.

`InputTooLarge`
- fields: `kind`

`MalformedUtf8`
- fields: `kind`, `byte_offset`

`UnmappedCodepoint`
- fields: `kind`, `codepoint`, `position`

`OrphanDiacritic`
- fields: `kind`, `codepoint`, `position`

`InvalidMarkCombo`
- fields: `kind`, `marks`, `atom_index`

`InvalidFlagCombo`
- fields: `kind`, `flags`, `atom_index`

`InvalidProsody`
- fields: `kind`, `prosody`, `atom_index`, `reason`

`ReservedFieldNonZero`
- fields: `kind`, `atom_index`, `reserved`

---

## 10. Field semantics

### 10.1 `byte_offset`
Zero-based byte offset into the raw input byte sequence.

In Mode B v1.x compatibility cases, this refers to frame byte position,
even though the error kind remains `MalformedUtf8`.

### 10.2 `position`
Logical source position as emitted by the conformance-generating implementation.

### 10.3 `atom_index`
Zero-based index into the atom stream or parsed atom sequence.

### 10.4 `marks`, `flags`, `prosody`, `reserved`
Raw integer values from the Dhad protocol model.

### 10.5 `reason`
Human-readable explanatory text for certain prosody violations.

---

## 11. Hash verification rules

For every success vector, conforming implementations must recompute the hashes
from `stream_hex` exactly as defined in the Dhad specification.

### 11.1 CoreHash

    SHA-256("DHAD-CORE-V1" || LE_u32(n) || foreach atom: LE_u16(base) || LE_u16(marks) || flags)

### 11.2 PhoneticHash

    SHA-256("DHAD-PROSODY-V1" || CoreHash || LE_u32(n) || foreach atom: prosody)

---

## 12. Mandatory anchors

Official Dhad conformance corpora must contain vectors exposing these four anchors:

- ANCHOR-001: `""`
- ANCHOR-002: `0100000000000000`
- ANCHOR-003: `0200000000000000`
- ANCHOR-004: `0200010000000000`

Meanings:

- ANCHOR-001: empty stream
- ANCHOR-002: ALEF bare
- ANCHOR-003: BEH bare
- ANCHOR-004: BEH + FATHA

If an implementation disagrees with an anchor, the implementation is wrong.

---

## 13. Current official corpus layout

The current published corpus contains:

- `vectors/golden.json` — Mode A success vectors
- `vectors/adversarial.json` — Mode A success and error vectors
- `vectors/tagged.json` — Mode B success and error vectors

Current counts:

- `golden.json` = 116
- `adversarial.json` = 43
- `tagged.json` = 36
- total = 195

These counts are corpus facts, not schema requirements.

---

## 14. Non-goals

Schema v1.0 does not define:

- internal normalization stage dumps
- Rust-specific helper types
- Python-specific helper types
- implementation-specific debug traces
- future v2.0 error expansions

Those may appear only in a future schema revision.

---

## 15. Compatibility policy

### Minor-compatible changes

The following may evolve without changing `schema_version` if existing consumers remain valid:

- additional files using the same schema
- additional vectors
- updated `generated_by`
- updated `source_suite`

### Breaking changes

The following require a new schema version:

- changing field names
- changing input encoding semantics
- changing success/error object layout
- changing hash field names
- changing mandatory typing of existing fields

---

## 16. Reference status

The current corpus provides:

- a canonical published vector set
- a dependency-free Python verifier
- cross-language hash verification from `stream_hex`
- mandatory anchor verification

A full second implementation that reproduces protocol outputs directly from raw
inputs is the next conformance milestone.
