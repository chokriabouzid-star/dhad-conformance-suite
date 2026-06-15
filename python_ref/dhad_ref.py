from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import zlib
from typing import Dict, Union


# ---------------------------------------------------------------------------
# Protocol constants (Phase 1: Mode B subset)
# ---------------------------------------------------------------------------

MAX_INPUT_BYTES = 4_194_304

MAGIC = b"DHAD"
VERSION = 0x01
MODE_B = 0x42

# Base IDs needed by the current tagged corpus
ALEF = 0x0001
BEH = 0x0002
MEEM = 0x0018
NOON = 0x0019
WAW = 0x001B
YEH = 0x001C
ALEF_MAQSURA = 0x0022

LONG_VOWEL_CLASS = {ALEF, WAW, YEH, ALEF_MAQSURA}
RESERVED_BASES = {0x001D, 0x001E, 0x001F}

HAMZA_ABOVE = 0x01
HAMZA_BELOW = 0x02
MADDA = 0x04

TW_FATH = 0x01
TW_DAMM = 0x02
TW_KASR = 0x04
MADD_NORMAL = 0x08
MADD_EXTENDED = 0x10

VALID_SINGLE_FLAGS = {0x00, HAMZA_ABOVE, HAMZA_BELOW, MADDA}


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RefOk:
    stream_bytes: bytes
    core_hash: bytes
    phonetic_hash: bytes


@dataclass(frozen=True)
class RefError:
    kind: str
    fields: Dict[str, object]


RefResult = Union[RefOk, RefError]


@dataclass(frozen=True)
class Atom:
    base: int
    marks: int
    flags: int
    prosody: int
    reserved: int

    def to_bytes(self) -> bytes:
        return (
            struct.pack("<H", self.base)
            + struct.pack("<H", self.marks)
            + bytes([self.flags, self.prosody])
            + struct.pack("<H", self.reserved)
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def err(kind: str, **fields: object) -> RefError:
    return RefError(kind=kind, fields=fields)


def core_hash_from_atoms(atoms: list[Atom]) -> bytes:
    h = hashlib.sha256()
    h.update(b"DHAD-CORE-V1")
    h.update(struct.pack("<I", len(atoms)))
    for atom in atoms:
        h.update(struct.pack("<H", atom.base))
        h.update(struct.pack("<H", atom.marks))
        h.update(bytes([atom.flags]))
    return h.digest()


def phonetic_hash_from_atoms(core_hash: bytes, atoms: list[Atom]) -> bytes:
    h = hashlib.sha256()
    h.update(b"DHAD-PROSODY-V1")
    h.update(core_hash)
    h.update(struct.pack("<I", len(atoms)))
    for atom in atoms:
        h.update(bytes([atom.prosody]))
    return h.digest()


# ---------------------------------------------------------------------------
# Invariant subset required by tagged.json
# ---------------------------------------------------------------------------

def validate_base(atom: Atom, atom_index: int) -> RefError | None:
    if atom.base in RESERVED_BASES:
        return err(
            "UnmappedCodepoint",
            codepoint=atom.base,
            position=atom_index,
        )
    return None


def validate_flags(atom: Atom, atom_index: int) -> RefError | None:
    flags = atom.flags

    if flags not in VALID_SINGLE_FLAGS:
        return err("InvalidFlagCombo", flags=flags, atom_index=atom_index)

    if flags == HAMZA_ABOVE and atom.base not in {ALEF, WAW, YEH}:
        return err("InvalidFlagCombo", flags=flags, atom_index=atom_index)

    if flags == HAMZA_BELOW and atom.base != ALEF:
        return err("InvalidFlagCombo", flags=flags, atom_index=atom_index)

    if flags == MADDA and atom.base != ALEF:
        return err("InvalidFlagCombo", flags=flags, atom_index=atom_index)

    return None


def validate_prosody(atom: Atom, atom_index: int) -> RefError | None:
    prosody = atom.prosody

    tanween_mask = TW_FATH | TW_DAMM | TW_KASR
    madd_mask = MADD_NORMAL | MADD_EXTENDED

    tanween_bits = prosody & tanween_mask
    madd_bits = prosody & madd_mask

    if tanween_bits in {0x03, 0x05, 0x06, 0x07}:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="Conflicting TANWEEN bits cannot coexist",
        )

    if madd_bits == (MADD_NORMAL | MADD_EXTENDED):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="MADD_NORMAL and MADD_EXTENDED cannot coexist",
        )

    if madd_bits and atom.base not in LONG_VOWEL_CLASS:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="MADD bits only permitted on LONG_VOWEL_CLASS atoms",
        )

    return None


def validate_atom(atom: Atom, atom_index: int) -> RefError | None:
    if atom.reserved != 0:
        return err(
            "ReservedFieldNonZero",
            atom_index=atom_index,
            reserved=atom.reserved,
        )

    failure = validate_base(atom, atom_index)
    if failure is not None:
        return failure

    failure = validate_flags(atom, atom_index)
    if failure is not None:
        return failure

    failure = validate_prosody(atom, atom_index)
    if failure is not None:
        return failure

    return None


# ---------------------------------------------------------------------------
# Mode B reference
# ---------------------------------------------------------------------------

def process_mode_b_ref(frame: bytes) -> RefResult:
    if len(frame) > MAX_INPUT_BYTES:
        return err("InputTooLarge")

    if len(frame) < 14:
        return err("MalformedUtf8", byte_offset=len(frame))

    if frame[0:4] != MAGIC:
        return err("MalformedUtf8", byte_offset=0)

    if frame[4] != VERSION:
        return err("MalformedUtf8", byte_offset=4)

    if frame[5] != MODE_B:
        return err("MalformedUtf8", byte_offset=5)

    n_atoms = struct.unpack("<I", frame[6:10])[0]
    expected_size = 10 + (n_atoms * 8) + 4

    if expected_size != len(frame):
        return err("MalformedUtf8", byte_offset=10)

    data = frame[:-4]
    crc_expected = struct.unpack("<I", frame[-4:])[0]
    crc_actual = zlib.crc32(data) & 0xFFFFFFFF

    if crc_actual != crc_expected:
        return err("MalformedUtf8", byte_offset=len(frame) - 4)

    atoms: list[Atom] = []
    off = 10

    for atom_index in range(n_atoms):
        chunk = frame[off : off + 8]
        atom = Atom(
            base=struct.unpack("<H", chunk[0:2])[0],
            marks=struct.unpack("<H", chunk[2:4])[0],
            flags=chunk[4],
            prosody=chunk[5],
            reserved=struct.unpack("<H", chunk[6:8])[0],
        )

        failure = validate_atom(atom, atom_index)
        if failure is not None:
            return failure

        atoms.append(atom)
        off += 8

    stream_bytes = b"".join(atom.to_bytes() for atom in atoms)
    core_hash = core_hash_from_atoms(atoms)
    phonetic_hash = phonetic_hash_from_atoms(core_hash, atoms)

    return RefOk(
        stream_bytes=stream_bytes,
        core_hash=core_hash,
        phonetic_hash=phonetic_hash,
    )
