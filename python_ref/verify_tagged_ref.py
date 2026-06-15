#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python_ref.dhad_ref import RefError, RefOk, process_mode_b_ref


VECTORS_PATH = ROOT / "vectors" / "tagged.json"


def decode_input(input_obj: dict) -> bytes:
    enc = input_obj["encoding"]
    if enc == "hex":
        return bytes.fromhex(input_obj["hex"])
    if enc == "repeat_byte":
        b = int(input_obj["byte_hex"], 16)
        count = int(input_obj["count"])
        return bytes([b]) * count
    raise AssertionError(f"unsupported input encoding: {enc}")


def error_to_object(err: RefError) -> dict:
    obj = {"kind": err.kind}
    obj.update(err.fields)
    return obj


def main() -> int:
    data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    vectors = data["vectors"]

    total = len(vectors)
    passed = 0
    failed: list[tuple[str, str]] = []

    for v in vectors:
        raw_input = decode_input(v["input"])
        result = process_mode_b_ref(raw_input)

        if v["expected_result"] == "ok":
            if not isinstance(result, RefOk):
                failed.append(
                    (
                        v["name"],
                        f"expected ok, got error {getattr(result, 'kind', type(result).__name__)}",
                    )
                )
                continue

            got_stream_hex = result.stream_bytes.hex()
            got_core_hash_hex = result.core_hash.hex()
            got_phonetic_hash_hex = result.phonetic_hash.hex()

            if got_stream_hex != v["stream_hex"]:
                failed.append((v["name"], "stream_hex mismatch"))
                continue
            if got_core_hash_hex != v["core_hash_hex"]:
                failed.append((v["name"], "core_hash_hex mismatch"))
                continue
            if got_phonetic_hash_hex != v["phonetic_hash_hex"]:
                failed.append((v["name"], "phonetic_hash_hex mismatch"))
                continue

            passed += 1
            continue

        if not isinstance(result, RefError):
            failed.append((v["name"], "expected err, got ok"))
            continue

        got_error = error_to_object(result)
        expected_error = v["error"]

        if got_error != expected_error:
            failed.append(
                (
                    v["name"],
                    "error object mismatch:\n"
                    f"    expected: {json.dumps(expected_error, ensure_ascii=False, sort_keys=True)}\n"
                    f"    got:      {json.dumps(got_error, ensure_ascii=False, sort_keys=True)}",
                )
            )
            continue

        passed += 1

    print(f"tagged.json: {passed}/{total} vectors matched in Phase 2")

    if failed:
        print("\nFAILURES:")
        for name, msg in failed[:20]:
            print(f"  {name}: {msg}")
        print(f"\nTotal failures: {len(failed)}")
        return 1

    print("ALL TAGGED VECTORS MATCH (Phase 2: exact ok outputs + full error object parity)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
