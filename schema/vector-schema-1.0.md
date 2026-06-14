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

{ "kind": "InputTooLarge" }

MalformedUtf8

JSON

{ "kind": "MalformedUtf8", "byte_offset": 3 }

UnmappedCodepoint

JSON

{ "kind": "UnmappedCodepoint", "codepoint": 1620, "byte_offset": 2 }

OrphanDiacritic

JSON

{ "kind": "OrphanDiacritic", "byte_offset": 0 }

InvalidMarkCombo

JSON

{ "kind": "InvalidMarkCombo", "atom_index": 1 }

InvalidFlagCombo

JSON

{ "kind": "InvalidFlagCombo", "atom_index": 0 }

InvalidProsody

JSON

{ "kind": "InvalidProsody", "atom_index": 2 }

ReservedFieldNonZero

JSON

{ "kind": "ReservedFieldNonZero", "atom_index": 0 }

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

