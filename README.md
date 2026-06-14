# Dhad Conformance Suite

Language-agnostic conformance vectors for the Dhad protocol.

## Purpose

This repository exists to make Dhad test vectors independent of the Rust
implementation repository.

Its role is to provide a stable, byte-exact, implementation-neutral set of:

- acceptance vectors
- rejection vectors
- tagged Mode B vectors

for any future implementation in Rust, Python, or other languages.

## Governing principles

1. **Spec before code**
   - Vector format is defined explicitly before generators or readers are written.

2. **Anchors are normative**
   - The four initial anchors are immutable conformance seeds.
   - Any implementation that disagrees with them is wrong.

3. **Independence by design**
   - Files in this repository must be understandable without reading Rust code.

## Repository layout

- `schema/vector-schema-1.0.md`
  - Human-readable schema definition for vector JSON files

- `vectors/golden.json`
  - Normative successful Mode A vectors

- `vectors/adversarial.json`
  - Normative error / rejection vectors

- `vectors/tagged.json`
  - Normative Mode B tagged-frame vectors

## Current status

This repository is bootstrapped in Step 2 of the v1.2.0 plan.

At this stage:

- schema is defined
- vector files exist
- vector files are intentionally empty placeholders

Population of the vector files happens in Step 3 from the Dhad Rust exporter.

## Generation policy

The JSON vector files are canonical artifacts.

They may be initialized manually as empty placeholders, but once exporter-driven
generation begins, populated vectors should not be edited by hand unless the
schema itself changes intentionally.

## Relationship to the Rust repository

Primary implementation repository:

- https://github.com/chokriabouzid-star/dhad

Published crate:

- https://crates.io/crates/dhad

This repository does not replace the Dhad specification.
It carries conformance artifacts for independent implementations.

## License

MIT.
