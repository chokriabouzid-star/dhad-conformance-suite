#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from python_ref.dhad_ref import RefError, RefOk, process_mode_a_ref


def decode_input(input_obj: dict) -> bytes:
    enc = input_obj["encoding"]
    if enc == "hex":
        return bytes.fromhex(input_obj["hex"])
    if enc == "repeat_byte":
        b = int(input_obj["byte_hex"], 16)
        count = int(input_obj["count"])
        return bytes([b]) * count
    raise AssertionError(f"unsupported input encoding: {enc}")


def error_to_object(e: RefError) -> dict:
    obj = {"kind": e.kind}
    obj.update(e.fields)
    return obj


def verify_file(path: Path, label: str) -> tuple[int, int, list[tuple[str, str]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    vectors = data["vectors"]

    passed = 0
    failed: list[tuple[str, str]] = []

    for v in vectors:
        raw_input = decode_input(v["input"])
        result = process_mode_a_ref(raw_input)

        if v["expected_result"] == "ok":
            if not isinstance(result, RefOk):
                failed.append((v["name"], f"expected ok, got error {result.kind}"))
                continue
            if result.stream_bytes.hex() != v["stream_hex"]:
                failed.append((v["name"], f"stream mismatch"))
                continue
            if result.core_hash.hex() != v["core_hash_hex"]:
                failed.append((v["name"], f"core_hash mismatch"))
                continue
            if result.phonetic_hash.hex() != v["phonetic_hash_hex"]:
                failed.append((v["name"], f"phonetic_hash mismatch"))
                continue
            passed += 1
        else:
            if not isinstance(result, RefError):
                failed.append((v["name"], "expected err, got ok"))
                continue
            got = error_to_object(result)
            expected = v["error"]
            if got != expected:
                failed.append((
                    v["name"],
                    f"error mismatch:\n    expected: {json.dumps(expected, sort_keys=True)}\n    got:      {json.dumps(got, sort_keys=True)}"
                ))
                continue
            passed += 1

    return len(vectors), passed, failed


def main() -> int:
    vectors_dir = ROOT / "vectors"
    files = [
        (vectors_dir / "golden.json", "golden"),
        (vectors_dir / "adversarial.json", "adversarial"),
    ]

    all_ok = True
    for path, label in files:
        total, passed, failed = verify_file(path, label)
        print(f"{label}.json: {passed}/{total}")
        if failed:
            all_ok = False
            for name, msg in failed[:15]:
                print(f"  FAIL {name}: {msg}")
            if len(failed) > 15:
                print(f"  ... and {len(failed) - 15} more")

    if all_ok:
        print("\nALL MODE A VECTORS MATCH")
        return 0
    else:
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
