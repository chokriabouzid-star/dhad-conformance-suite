# Dhad Vector Schema 1.0

## Scope

This document defines the JSON structure used by the Dhad conformance suite.

It is intentionally language-agnostic and does not depend on Rust data types.

## Root object

Each vector file is a single JSON object with the following fields:

- `schema_version` — string
- `dhad_spec` — string
- `generated_by` — string
- `vectors` — array of vector objects

Example:

```json
{
  "schema_version": "1.0",
  "dhad_spec": "v1.0+CR-07",
  "generated_by": "dhad-rust-1.1.2",
  "vectors": []
}

Vector object

Each entry in vectors is a JSON object with these common fields:

    name — string
    mode — "A" or "B"
    input_hex — uppercase or lowercase hex string representing exact input bytes
    input_utf8_preview — optional string, informational only
    expected — "ok" or "err"

Notes

    input_hex is always authoritative.
    input_utf8_preview is optional and must be omitted if:
        the input is invalid UTF-8, or
        the case is Mode B binary data with no useful text preview.
    Readers must not derive conformance from the preview field.

Successful vector (expected: "ok")

An OK vector contains:

    all common fields
    stream_hex — hex string of the serialized atom stream bytes
    core_hash — lowercase hex SHA-256
    phonetic_hash — lowercase hex SHA-256

Example:

JSON

{
  "name": "anchor_004_beh_fatha",
  "mode": "A",
  "input_hex": "D8A8D98E",
  "input_utf8_preview": "بَ",
  "expected": "ok",
  "stream_hex": "0200010000000000",
  "core_hash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "phonetic_hash": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
}

Error vector (expected: "err")

An ERR vector contains:

    all common fields
    error — an object with:
        mandatory field kind
        only the fields that belong to that error kind
        no null values
        no unrelated extra fields

This is a tagged union / discriminated union.
Error object variants
InputTooLarge

JSON

{ "kind": "InputTooLarge", "input_bytes": 4194305 }

MalformedUtf8

JSON

{ "kind": "MalformedUtf8", "byte_offset": 3 }

UnmappedCodepoint

JSON

{ "kind": "UnmappedCodepoint", "codepoint": 1620, "position": 2 }

OrphanDiacritic

JSON

{ "kind": "OrphanDiacritic", "codepoint": 1614, "position": 0 }

InvalidMarkCombo

JSON

{ "kind": "InvalidMarkCombo", "marks": 24, "atom_index": 1 }

InvalidFlagCombo

JSON

{ "kind": "InvalidFlagCombo", "flags": 3, "atom_index": 0 }

InvalidProsody

JSON

{ "kind": "InvalidProsody", "prosody": 24, "atom_index": 0, "reason": "MADD_N|MADD_X forbidden" }

ReservedFieldNonZero

JSON

{ "kind": "ReservedFieldNonZero", "reserved": 1, "atom_index": 0 }

Error field semantics

    input_bytes is the raw input length in bytes at the point of rejection.
    byte_offset is a byte position in the raw input or raw Mode B frame.
    position is the logical decoded-input position used by Dhad error reporting.
    atom_index is the zero-based index of the validated atom in the canonical stream.
    Error objects must include only the fields that belong to their kind.
    Error objects must not contain null values.

Additional conventions
stream_hex

    Represents the exact serialized atom stream
    Uses the Dhad wire format
    Each atom is 8 bytes
    Little-endian layout is already encoded in the byte stream itself

Hash fields

    core_hash and phonetic_hash are lowercase hexadecimal SHA-256 digests
    No 0x prefix
    Exactly 64 hex characters each

File categories

    golden.json — successful Mode A vectors
    adversarial.json — invalid / rejection vectors, plus edge cases
    tagged.json — Mode B vectors

Stability expectations

    schema_version changes only when JSON structure changes
    dhad_spec changes when the protocol/spec version changes
    generated_by identifies the implementation/tool that emitted the file

