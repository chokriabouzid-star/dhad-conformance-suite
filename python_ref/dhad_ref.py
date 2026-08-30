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
    if atom.base not in VALID_BASE_IDS:
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

    if prosody & 0xC0:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="prosody bits 6-7 (0xC0) are reserved and must be zero",
        )

        # I24: SUKUN and TANWEEN exclusion
    if (atom.marks & 0x0008) and (prosody & (TW_FATH | TW_DAMM | TW_KASR)):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="SUKUN and TANWEEN are mutually exclusive on the same atom",
        )

    tanween_mask = TW_FATH | TW_DAMM | TW_KASR
    madd_mask = MADD_NORMAL | MADD_EXTENDED

    tanween_bits = prosody & tanween_mask
    madd_bits = prosody & madd_mask

    if tanween_bits in {0x03, 0x05, 0x06, 0x07}:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="TANWEEN_FATH and TANWEEN_DAMM are mutually exclusive",
        )

    if madd_bits == (MADD_NORMAL | MADD_EXTENDED):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="MADD_NORMAL and MADD_EXTENDED are mutually exclusive",
        )

    if madd_bits and atom.base not in LONG_VOWEL_CLASS:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="MADD bits only permitted on LONG_VOWEL_CLASS atoms",
        )

    # I13: MADD bits are mutually exclusive with TANWEEN bits
    if madd_bits and tanween_bits:
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="MADD bits are mutually exclusive with TANWEEN bits",
        )

    # I18: TANWEEN_FATH and FATHA are contradictory
    if (prosody & TW_FATH) and (atom.marks & 0x01):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="TANWEEN_FATH and FATHA are contradictory",
        )

    # I19: TANWEEN_DAMM and DAMMA are contradictory
    if (prosody & TW_DAMM) and (atom.marks & 0x02):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="TANWEEN_DAMM and DAMMA are contradictory",
        )

    # I20: TANWEEN_KASR and KASRA are contradictory
    if (prosody & TW_KASR) and (atom.marks & 0x04):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="TANWEEN_KASR and KASRA are contradictory",
        )

    # I21: SUPERSCRIPT_ALEF and TANWEEN bits are contradictory
    if (prosody & 0x20) and (prosody & 0x07):
        return err(
            "InvalidProsody",
            prosody=prosody,
            atom_index=atom_index,
            reason="SUPERSCRIPT_ALEF and TANWEEN bits are contradictory",
        )

    return None


def validate_marks(atom: Atom, atom_index: int) -> RefError | None:
    """I03/I17/I23: validate mark combinations and base-mark compatibility."""
    if atom.marks not in VALID_MARK_COMBOS:
        return err(
            "InvalidMarkCombo",
            marks=atom.marks,
            atom_index=atom_index,
        )
    if atom.base in PROSODY_INERT_BASES and atom.marks != 0:
        return err(
            "InvalidMarkCombo",
            marks=atom.marks,
            atom_index=atom_index,
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

    failure = validate_marks(atom, atom_index)
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
        return err("MalformedUtf8", byte_offset=0)

    if frame[0:4] != MAGIC:
        return err("MalformedUtf8", byte_offset=0)

    if frame[4] != VERSION:
        return err("MalformedUtf8", byte_offset=4)

    if frame[5] != MODE_B:
        return err("MalformedUtf8", byte_offset=5)

    n_atoms = struct.unpack("<I", frame[6:10])[0]

    # Guard against overflow: if n_atoms * 8 would exceed frame length,
    # report at byte_offset=6 (location of n_atoms field), matching Rust.
    try:
        atom_bytes = n_atoms * 8
    except OverflowError:
        return err("MalformedUtf8", byte_offset=6)

    expected_size = 10 + atom_bytes + 4

    if expected_size != len(frame):
        return err("MalformedUtf8", byte_offset=6)

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


# ===========================================================================
# Mode A reference (Phase 3)
# ===========================================================================

# ---------------------------------------------------------------------------
# Codepoint tables
# ---------------------------------------------------------------------------

# Base letters: codepoint -> (base_id, flags)
BASE_LETTERS: dict[int, tuple[int, int]] = {
    0x0627: (0x01, 0x00),  # ALEF
    0x0628: (0x02, 0x00),  # BEH
    0x062A: (0x03, 0x00),  # TEH
    0x062B: (0x04, 0x00),  # THEH
    0x062C: (0x05, 0x00),  # JEEM
    0x062D: (0x06, 0x00),  # HAH
    0x062E: (0x07, 0x00),  # KHAH
    0x062F: (0x08, 0x00),  # DAL
    0x0630: (0x09, 0x00),  # THAL
    0x0631: (0x0A, 0x00),  # REH
    0x0632: (0x0B, 0x00),  # ZAIN
    0x0633: (0x0C, 0x00),  # SEEN
    0x0634: (0x0D, 0x00),  # SHEEN
    0x0635: (0x0E, 0x00),  # SAD
    0x0636: (0x0F, 0x00),  # DAD
    0x0637: (0x10, 0x00),  # TAH
    0x0638: (0x11, 0x00),  # ZAH
    0x0639: (0x12, 0x00),  # AIN
    0x063A: (0x13, 0x00),  # GHAIN
    0x0641: (0x14, 0x00),  # FEH
    0x0642: (0x15, 0x00),  # QAF
    0x0643: (0x16, 0x00),  # KAF
    0x0644: (0x17, 0x00),  # LAM
    0x0645: (0x18, 0x00),  # MEEM
    0x0646: (0x19, 0x00),  # NOON
    0x0647: (0x1A, 0x00),  # HEH
    0x0648: (0x1B, 0x00),  # WAW
    0x064A: (0x1C, 0x00),  # YEH
    0x0621: (0x20, 0x00),  # HAMZA standalone
    0x0629: (0x21, 0x00),  # TEH MARBUTA
    0x0649: (0x22, 0x00),  # ALEF MAQSURA
    0x0671: (0x23, 0x00),  # ALEF WASLA
    # Precomposed hamza/madda forms
    0x0622: (0x01, 0x04),  # ALEF + MADDA
    0x0623: (0x01, 0x01),  # ALEF + HAMZA ABOVE
    0x0624: (0x1B, 0x01),  # WAW + HAMZA ABOVE
    0x0625: (0x01, 0x02),  # ALEF + HAMZA BELOW
    0x0626: (0x1C, 0x01),  # YEH + HAMZA ABOVE
}

# Punctuation/space: codepoint -> base_id
PUNCTUATION: dict[int, int] = {
    0x0020: 0x40,  # SPACE
    0x060C: 0x41,  # ARABIC COMMA
    0x061B: 0x42,  # ARABIC SEMICOLON
    0x061F: 0x43,  # ARABIC QUESTION MARK
    0x002E: 0x44,  # FULL STOP
    0x003A: 0x45,  # COLON
}

# Digits: codepoint -> base_id
DIGITS: dict[int, int] = {}
for d in range(10):
    base_id = d | 0x0100
    DIGITS[0x0030 + d] = base_id  # ASCII
    DIGITS[0x0660 + d] = base_id  # Arabic-Indic
    DIGITS[0x06F0 + d] = base_id  # Extended Arabic-Indic

# Positional forms -> canonical codepoint
POSITIONAL_FORMS: dict[int, int] = {
    0xFE8F: 0x0628,  # BEH isolated
    0xFE90: 0x0628,  # BEH final
    0xFE91: 0x0628,  # BEH initial
    0xFE92: 0x0628,  # BEH medial
    0xFEF1: 0x064A,  # YEH isolated
    0xFEEF: 0x0649,  # ALEF MAQSURA isolated
}

# Lam-Alef ligatures -> list of (base_id, flags) pairs
LAM_ALEF_LIGATURES: dict[int, list[tuple[int, int]]] = {
    0xFEFB: [(0x17, 0x00), (0x01, 0x00)],  # LAM + ALEF isolated
    0xFEFC: [(0x17, 0x00), (0x01, 0x00)],  # LAM + ALEF final
    0xFEF5: [(0x17, 0x00), (0x01, 0x04)],  # LAM + ALEF MADDA isolated
    0xFEF6: [(0x17, 0x00), (0x01, 0x04)],  # LAM + ALEF MADDA final
    0xFEF7: [(0x17, 0x00), (0x01, 0x01)],  # LAM + ALEF HAMZA ABOVE isolated
    0xFEF8: [(0x17, 0x00), (0x01, 0x01)],  # LAM + ALEF HAMZA ABOVE final
    0xFEF9: [(0x17, 0x00), (0x01, 0x02)],  # LAM + ALEF HAMZA BELOW isolated
    0xFEFA: [(0x17, 0x00), (0x01, 0x02)],  # LAM + ALEF HAMZA BELOW final
}

# Diacritics: codepoint -> mark bit
DIACRITICS: dict[int, int] = {
    0x064E: 0x01,  # FATHA
    0x064F: 0x02,  # DAMMA
    0x0650: 0x04,  # KASRA
    0x0651: 0x10,  # SHADDA
    0x0652: 0x08,  # SUKUN
}

# Prosody diacritics: codepoint -> prosody bit
PROSODY_MARKS: dict[int, int] = {
    0x064B: 0x01,  # TANWEEN_FATH
    0x064C: 0x02,  # TANWEEN_DAMM
    0x064D: 0x04,  # TANWEEN_KASR
    0x0670: 0x20,  # SUPERSCRIPT_ALEF
}

# Filter characters (silently removed) — Complete 32 Noise Codepoints matching Dhad Spec §5.1
FILTER_CHARS: set[int] = (
    {0x0640, 0x034F, 0xFEFF}
    | set(range(0x200C, 0x2010))  # ZWNJ, ZWJ, LRM, RLM (0x200C..=0x200F)
    | set(range(0x202A, 0x202F))  # LRE, RLE, PDF, LRO, RLO (0x202A..=0x202E)
    | set(range(0x2066, 0x206A))  # LRI, RLI, FSI, PDI (0x2066..=0x2069)
    | set(range(0xFE00, 0xFE10))  # VS01..VS16 (0xFE00..=0xFE0F)
)

# Valid mark combinations (bitmask values)
VALID_MARK_COMBOS: set[int] = {
    0x00,  # bare
    0x01,  # FATHA
    0x02,  # DAMMA
    0x04,  # KASRA
    0x08,  # SUKUN
    0x10,  # SHADDA
    0x11,  # SHADDA + FATHA
    0x12,  # SHADDA + DAMMA
    0x14,  # SHADDA + KASRA
}

# Prosody-inert base class (punctuation + digits)
PROSODY_INERT_BASES: set[int] = set()
for v in PUNCTUATION.values():
    PROSODY_INERT_BASES.add(v)
for v in DIGITS.values():
    PROSODY_INERT_BASES.add(v)

# All valid base IDs for Mode B atom validation (I01)
VALID_BASE_IDS: frozenset[int] = frozenset(
    {bid for bid, _ in BASE_LETTERS.values()}
    | PROSODY_INERT_BASES
) - RESERVED_BASES


# ---------------------------------------------------------------------------
# Mode A pipeline
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Stage 3: Complete 141-entry FAPS Decomposition (matching src/faps.rs)
# ---------------------------------------------------------------------------

def faps_decompose(cp: int) -> tuple[int, ...] | None:
    """
    Decomposes Arabic Presentation Forms (FB50..FDFF, FE70..FEFC) to canonical codepoints.
    Returns:
      - tuple of 1 or 2 canonical codepoints if mapped
      - None if unmapped presentation form (ERR_UNMAPPED_CODEPOINT)
      - (cp,) if pass-through (outside presentation form ranges, e.g. U+FEFF)
    """
    # Harakat (FE70..FE7F)
    if cp == 0xFE70: return (0x064B,)
    if cp == 0xFE71: return (0x0640, 0x064B)
    if cp == 0xFE72: return (0x064C,)
    if cp == 0xFE73: return None
    if cp == 0xFE74: return (0x064D,)
    if cp == 0xFE75: return None
    if cp == 0xFE76: return (0x064E,)
    if cp == 0xFE77: return (0x0640, 0x064E)
    if cp == 0xFE78: return (0x064F,)
    if cp == 0xFE79: return (0x0640, 0x064F)
    if cp == 0xFE7A: return (0x0650,)
    if cp == 0xFE7B: return (0x0640, 0x0650)
    if cp == 0xFE7C: return (0x0651,)
    if cp == 0xFE7D: return (0x0640, 0x0651)
    if cp == 0xFE7E: return (0x0652,)
    if cp == 0xFE7F: return (0x0640, 0x0652)

    # Hamza / Alef variants (FE80..FE8C)
    if cp == 0xFE80: return (0x0621,)
    if cp in (0xFE81, 0xFE82): return (0x0622,)
    if cp in (0xFE83, 0xFE84): return (0x0623,)
    if cp in (0xFE85, 0xFE86): return (0x0624,)
    if cp in (0xFE87, 0xFE88): return (0x0625,)
    if 0xFE89 <= cp <= 0xFE8C: return (0x0626,)

    # Core 28 letters (FE8D..FEF4)
    if cp in (0xFE8D, 0xFE8E): return (0x0627,)
    if 0xFE8F <= cp <= 0xFE92: return (0x0628,)
    if cp in (0xFE93, 0xFE94): return (0x0629,)
    if 0xFE95 <= cp <= 0xFE98: return (0x062A,)
    if 0xFE99 <= cp <= 0xFE9C: return (0x062B,)
    if 0xFE9D <= cp <= 0xFEA0: return (0x062C,)
    if 0xFEA1 <= cp <= 0xFEA4: return (0x062D,)
    if 0xFEA5 <= cp <= 0xFEA8: return (0x062E,)
    if cp in (0xFEA9, 0xFEAA): return (0x062F,)
    if cp in (0xFEAB, 0xFEAC): return (0x0630,)
    if cp in (0xFEAD, 0xFEAE): return (0x0631,)
    if cp in (0xFEAF, 0xFEB0): return (0x0632,)
    if 0xFEB1 <= cp <= 0xFEB4: return (0x0633,)
    if 0xFEB5 <= cp <= 0xFEB8: return (0x0634,)
    if 0xFEB9 <= cp <= 0xFEBC: return (0x0635,)
    if 0xFEBD <= cp <= 0xFEC0: return (0x0636,)
    if 0xFEC1 <= cp <= 0xFEC4: return (0x0637,)
    if 0xFEC5 <= cp <= 0xFEC8: return (0x0638,)
    if 0xFEC9 <= cp <= 0xFECC: return (0x0639,)
    if 0xFECD <= cp <= 0xFED0: return (0x063A,)
    if 0xFED1 <= cp <= 0xFED4: return (0x0641,)
    if 0xFED5 <= cp <= 0xFED8: return (0x0642,)
    if 0xFED9 <= cp <= 0xFEDC: return (0x0643,)
    if 0xFEDD <= cp <= 0xFEE0: return (0x0644,)
    if 0xFEE1 <= cp <= 0xFEE4: return (0x0645,)
    if 0xFEE5 <= cp <= 0xFEE8: return (0x0646,)
    if 0xFEE9 <= cp <= 0xFEEC: return (0x0647,)
    if cp in (0xFEED, 0xFEEE): return (0x0648,)
    if cp in (0xFEEF, 0xFEF0): return (0x0649,)
    if 0xFEF1 <= cp <= 0xFEF4: return (0x064A,)

    # Lam-Alef ligatures (FEF5..FEFC)
    if cp in (0xFEF5, 0xFEF6): return (0x0644, 0x0622)
    if cp in (0xFEF7, 0xFEF8): return (0x0644, 0x0623)
    if cp in (0xFEF9, 0xFEFA): return (0x0644, 0x0625)
    if cp in (0xFEFB, 0xFEFC): return (0x0644, 0x0627)

    # FE range remainders
    if cp in (0xFEFD, 0xFEFE): return None

    # Forms-A
    if cp in (0xFB50, 0xFB51): return (0x0671,)
    if 0xFB52 <= cp <= 0xFDFF: return None

    # Pass-through for non-presentation forms
    return (cp,)


def process_mode_a_ref(input_bytes: bytes) -> RefResult:
    if len(input_bytes) > MAX_INPUT_BYTES:
        return err("InputTooLarge")

    # Stage 1: UTF-8 decode
    try:
        text = input_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        return err("MalformedUtf8", byte_offset=e.start)

    # Stage 2-9: classify, attach marks, build atoms
    atoms: list[Atom] = []
    current_base: int | None = None
    current_flags: int = 0
    current_marks: int = 0
    current_prosody: int = 0
    position: int = 0

    def flush_atom() -> None:
        nonlocal current_base, current_flags, current_marks, current_prosody
        if current_base is not None:
            atoms.append(Atom(
                base=current_base,
                marks=current_marks,
                flags=current_flags,
                prosody=current_prosody,
                reserved=0,
            ))
            current_base = None
            current_flags = 0
            current_marks = 0
            current_prosody = 0

    # Pre-process via FAPS decomposition (Stage 3)
    decomposed_cps: list[tuple[int, int, int]] = []  # (canonical_cp, original_char_idx, filtered_input_idx)
    filtered_input_count = 0
    for i, ch in enumerate(text):
        raw_cp = ord(ch)
        if raw_cp in FILTER_CHARS:
            continue
        decomp = faps_decompose(raw_cp)
        if decomp is None:
            # Unmapped presentation form — position is the 0-based index in the original input stream
            return err("UnmappedCodepoint", codepoint=raw_cp, position=filtered_input_count)
        for d_cp in decomp:
            decomposed_cps.append((d_cp, i, filtered_input_count))
        filtered_input_count += 1

    for d_idx, (cp, orig_i, f_idx) in enumerate(decomposed_cps):
        if cp in FILTER_CHARS:
            continue

        # Diacritics (marks)
        if cp in DIACRITICS:
            if current_base is None:
                return err("OrphanDiacritic", codepoint=cp, position=f_idx)

            if current_base in PROSODY_INERT_BASES:
                return err("InvalidMarkCombo", marks=current_marks | DIACRITICS[cp], atom_index=len(atoms))

            mark_bit = DIACRITICS[cp]
                        # I24 check: SUKUN arriving after TANWEEN
            if mark_bit == 0x0008 and (current_prosody & (TW_FATH | TW_DAMM | TW_KASR)):
                return err("InvalidProsody", prosody=current_prosody, atom_index=len(atoms), reason="SUKUN and TANWEEN are mutually exclusive on the same atom")
            new_marks = current_marks | mark_bit

            if new_marks == current_marks:
                return err("InvalidMarkCombo", marks=new_marks, atom_index=len(atoms))

            if new_marks not in VALID_MARK_COMBOS:
                return err("InvalidMarkCombo", marks=new_marks, atom_index=len(atoms))

            current_marks = new_marks
            continue

        # Prosody marks
        if cp in PROSODY_MARKS:
            if current_base is None:
                return err("OrphanDiacritic", codepoint=cp, position=f_idx)

            if current_base in PROSODY_INERT_BASES:
                if cp == 0x0670:
                    return err("InvalidProsody", prosody=current_prosody | PROSODY_MARKS[cp], atom_index=len(atoms), reason="U+0670 SUPERSCRIPT_ALEF cannot attach to a structural or digit atom")
                else:
                    return err("InvalidProsody", prosody=current_prosody | PROSODY_MARKS[cp], atom_index=len(atoms), reason="Prosody cannot attach to PROSODY_INERT_CLASS")

            prosody_bit = PROSODY_MARKS[cp]
            new_prosody = current_prosody | prosody_bit

                        # I24: Sukun + Tanween check
            if prosody_bit in (TW_FATH, TW_DAMM, TW_KASR) and (current_marks & 0x0008):
                return err("InvalidProsody", prosody=new_prosody, atom_index=len(atoms), reason="SUKUN and TANWEEN are mutually exclusive on the same atom")
            if new_prosody == current_prosody:
                return err("InvalidProsody", prosody=new_prosody, atom_index=len(atoms), reason="duplicate prosody mark on same atom")

            # Tanween + corresponding vowel check
            if prosody_bit == TW_FATH and (current_marks & 0x01):
                return err("InvalidProsody", prosody=new_prosody, atom_index=len(atoms), reason="TANWEEN_FATH and FATHA are contradictory")

            current_prosody = new_prosody
            continue

        # If we get here, it is a base-class character. Flush previous atom.
        flush_atom()
        if atoms:
            _ve = validate_atom(atoms[-1], len(atoms) - 1)
            if _ve is not None:
                return _ve
        position = i

        # Positional form
        if cp in POSITIONAL_FORMS:
            canonical = POSITIONAL_FORMS[cp]
            base_id, flags = BASE_LETTERS[canonical]
            current_base = base_id
            current_flags = flags
            continue

        # Lam-Alef ligature
        if cp in LAM_ALEF_LIGATURES:
            pairs = LAM_ALEF_LIGATURES[cp]
            for j, (base_id, flags) in enumerate(pairs):
                if j < len(pairs) - 1:
                    atoms.append(Atom(base=base_id, marks=0, flags=flags, prosody=0, reserved=0))
                else:
                    current_base = base_id
                    current_flags = flags
            continue

        # Base letter
        if cp in BASE_LETTERS:
            base_id, flags = BASE_LETTERS[cp]
            current_base = base_id
            current_flags = flags
            continue

        # Punctuation
        if cp in PUNCTUATION:
            current_base = PUNCTUATION[cp]
            current_flags = 0
            continue

        # Digit
        if cp in DIGITS:
            current_base = DIGITS[cp]
            current_flags = 0
            continue

        # Unknown codepoint
        return err("UnmappedCodepoint", codepoint=cp, position=f_idx)

    flush_atom()

    # Post-build invariant check on last atom
    if atoms:
        _ve = validate_atom(atoms[-1], len(atoms) - 1)
        if _ve is not None:
            return _ve

    # Compute hashes
    stream_bytes = b"".join(atom.to_bytes() for atom in atoms)
    core = core_hash_from_atoms(atoms)
    phonetic = phonetic_hash_from_atoms(core, atoms)

    return RefOk(
        stream_bytes=stream_bytes,
        core_hash=core,
        phonetic_hash=phonetic,
    )
