#!/usr/bin/env python3
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "vectors"

EXPECTED_FILES = {
    "golden.json": {"suite": "golden", "mode": "A", "count": 116},
    "adversarial.json": {"suite": "adversarial", "mode": "A", "count": 39},
    "tagged.json": {"suite": "tagged", "mode": "B", "count": 30},
}

EXPECTED_ERROR_FIELDS = {
    "InputTooLarge": {"kind"},
    "MalformedUtf8": {"kind", "byte_offset"},
    "UnmappedCodepoint": {"kind", "codepoint", "position"},
    "OrphanDiacritic": {"kind", "codepoint", "position"},
    "InvalidMarkCombo": {"kind", "marks", "atom_index"},
    "InvalidFlagCombo": {"kind", "flags", "atom_index"},
    "InvalidProsody": {"kind", "prosody", "atom_index", "reason"},
    "ReservedFieldNonZero": {"kind", "atom_index", "reserved"},
}

ANCHOR_STREAMS = {
    "": "ANCHOR-001 empty stream",
    "0100000000000000": "ANCHOR-002 ALEF bare",
    "0200000000000000": "ANCHOR-003 BEH bare",
    "0200010000000000": "ANCHOR-004 BEH + FATHA",
}


def core_hash(atoms):
    h = hashlib.sha256()
    h.update(b"DHAD-CORE-V1")
    h.update(struct.pack("<I", len(atoms)))
    for atom in atoms:
        h.update(struct.pack("<H", atom["base"]))
        h.update(struct.pack("<H", atom["marks"]))
        h.update(bytes([atom["flags"]]))
    return h.digest()


def phonetic_hash(core_digest, atoms):
    h = hashlib.sha256()
    h.update(b"DHAD-PROSODY-V1")
    h.update(core_digest)
    h.update(struct.pack("<I", len(atoms)))
    for atom in atoms:
        h.update(bytes([atom["prosody"]]))
    return h.digest()


def parse_stream_hex(stream_hex):
    raw = bytes.fromhex(stream_hex)
    if len(raw) % 8 != 0:
        raise AssertionError(f"stream_hex length not divisible by 8 bytes: {len(raw)}")

    atoms = []
    for i in range(0, len(raw), 8):
        atom = raw[i : i + 8]
        atoms.append(
            {
                "base": int.from_bytes(atom[0:2], "little"),
                "marks": int.from_bytes(atom[2:4], "little"),
                "flags": atom[4],
                "prosody": atom[5],
                "reserved": int.from_bytes(atom[6:8], "little"),
            }
        )
    return atoms


def decode_input(input_obj):
    enc = input_obj["encoding"]
    if enc == "hex":
        return bytes.fromhex(input_obj["hex"])
    if enc == "repeat_byte":
        b = int(input_obj["byte_hex"], 16)
        count = int(input_obj["count"])
        return bytes([b]) * count
    raise AssertionError(f"unknown input encoding: {enc}")


def validate_input_object(input_obj):
    enc = input_obj.get("encoding")
    if enc == "hex":
        keys = set(input_obj.keys())
        assert keys == {"encoding", "hex"}, f"hex input keys mismatch: {keys}"
        bytes.fromhex(input_obj["hex"])
        return
    if enc == "repeat_byte":
        keys = set(input_obj.keys())
        assert keys == {"encoding", "byte_hex", "count"}, f"repeat_byte input keys mismatch: {keys}"
        assert len(input_obj["byte_hex"]) == 2, "byte_hex must be exactly 2 hex chars"
        int(input_obj["byte_hex"], 16)
        assert isinstance(input_obj["count"], int) and input_obj["count"] >= 0, "count must be non-negative int"
        return
    raise AssertionError(f"unsupported input encoding: {enc}")


def validate_error_object(err):
    assert isinstance(err, dict), "error must be an object"
    kind = err.get("kind")
    assert kind in EXPECTED_ERROR_FIELDS, f"unknown error kind: {kind}"
    actual = set(err.keys())
    expected = EXPECTED_ERROR_FIELDS[kind]
    assert actual == expected, f"{kind}: fields mismatch; expected {expected}, got {actual}"


def verify_ok_vector(v, found_anchors):
    stream_hex = v["stream_hex"]
    core_hash_hex = v["core_hash_hex"]
    phonetic_hash_hex = v["phonetic_hash_hex"]

    atoms = parse_stream_hex(stream_hex)
    for idx, atom in enumerate(atoms):
        assert atom["reserved"] == 0, f"{v['name']}: atom {idx} reserved != 0 in stream"

    core = core_hash(atoms)
    phon = phonetic_hash(core, atoms)

    assert core.hex() == core_hash_hex, f"{v['name']}: CoreHash mismatch"
    assert phon.hex() == phonetic_hash_hex, f"{v['name']}: PhoneticHash mismatch"

    if stream_hex in ANCHOR_STREAMS:
        found_anchors.add(stream_hex)


def verify_err_vector(v):
    validate_error_object(v["error"])


def verify_file(path: Path, expected_meta, found_anchors):
    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == "1.0", f"{path.name}: schema_version mismatch"
    assert data["dhad_spec"] == "v1.0+CR-01..CR-07", f"{path.name}: dhad_spec mismatch"
    assert isinstance(data["generated_by"], str) and data["generated_by"].startswith("dhad-rust-"), \
        f"{path.name}: generated_by invalid"
    assert data["suite"] == expected_meta["suite"], f"{path.name}: suite mismatch"
    assert data["mode"] == expected_meta["mode"], f"{path.name}: mode mismatch"
    assert data["vector_count"] == expected_meta["count"], f"{path.name}: vector_count mismatch"

    vectors = data["vectors"]
    assert isinstance(vectors, list), f"{path.name}: vectors must be a list"
    assert len(vectors) == expected_meta["count"], f"{path.name}: actual vector list length mismatch"

    ok_count = 0
    err_count = 0

    for v in vectors:
        assert v["mode"] == data["mode"], f"{path.name}:{v['name']}: vector mode mismatch"
        validate_input_object(v["input"])

        decoded = decode_input(v["input"])
        if data["mode"] == "A" and "input_utf8_preview" in v:
            preview = decoded.decode("utf-8")
            assert v["input_utf8_preview"] == preview, f"{path.name}:{v['name']}: utf8 preview mismatch"

        result = v["expected_result"]
        if result == "ok":
            assert "error" not in v, f"{path.name}:{v['name']}: ok vector must not contain error"
            verify_ok_vector(v, found_anchors)
            ok_count += 1
        elif result == "err":
            assert "stream_hex" not in v, f"{path.name}:{v['name']}: err vector must not contain stream_hex"
            assert "core_hash_hex" not in v, f"{path.name}:{v['name']}: err vector must not contain core_hash_hex"
            assert "phonetic_hash_hex" not in v, f"{path.name}:{v['name']}: err vector must not contain phonetic_hash_hex"
            verify_err_vector(v)
            err_count += 1
        else:
            raise AssertionError(f"{path.name}:{v['name']}: unknown expected_result {result}")

    print(f"{path.name}: OK ({ok_count} ok / {err_count} err)")


def main():
    assert ROOT.is_dir(), f"missing vector directory: {ROOT}"

    found_anchors = set()

    total = 0
    for file_name, meta in EXPECTED_FILES.items():
        verify_file(ROOT / file_name, meta, found_anchors)
        total += meta["count"]

    missing = [name for stream, name in ANCHOR_STREAMS.items() if stream not in found_anchors]
    assert not missing, f"missing anchors: {missing}"

    print(f"anchors: OK ({len(found_anchors)} found)")
    print(f"total vectors verified: {total}")
    print("ALL VECTOR FILES VERIFIED")


if __name__ == "__main__":
    main()
