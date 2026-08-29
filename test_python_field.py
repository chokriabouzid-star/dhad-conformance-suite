#!/usr/bin/env python3
"""
Field tests for Dhad Python Reference Implementation (dhad_ref.py)
Mirrors the exact 12 test scenarios from run_dhad_tests.sh
"""
import sys
from pathlib import Path

# إضافة مسار python_ref
sys.path.insert(0, str(Path(__file__).parent / "python_ref"))
from dhad_ref import process_mode_a_ref, RefOk, RefError

def run_test(input_bytes: bytes, label: str):
    res = process_mode_a_ref(input_bytes)
    print(f"--- {label} ---")
    if isinstance(res, RefOk):
        # حساب عدد الذرات (كل ذرة 8 بايت)
        atom_count = len(res.stream_bytes) // 8
        print(f"atoms:    {atom_count}")
        print(f"core:     {res.core_hash.hex()}")
        print(f"phonetic: {res.phonetic_hash.hex()}")
    elif isinstance(res, RefError):
        fields = ", ".join(f"{k}={v}" for k, v in res.fields.items())
        print(f"dhad_ref: error: {res.kind} ({fields})")
    print()

def hdr(title: str):
    print("═" * 62)
    print(f"  {title}")
    print("═" * 62)

# ──────────────────────────────────────────────────────────────
# المحور 1: FAPS — Presentation Forms & Ligatures
# ──────────────────────────────────────────────────────────────
hdr("اختبار 1A: Presentation Forms مقابل الحروف الأصلية")
pf_bytes = b"\xEF\xBB\x9B\xEF\xBA\x98\xEF\xBA\x8E\xEF\xBA\x90"  # كتاب بـ presentation forms
run_test(pf_bytes, "Presentation Forms")
run_test("كتاب".encode("utf-8"), "Normal Arabic")

hdr("اختبار 1B: لام-ألف Ligatures (أخطر FAPS)")
lamalef_lig = b"\xEF\xBB\xBB"  # U+FEFB
run_test(lamalef_lig, "Lam-Alef Ligature U+FEFB")
run_test("لا".encode("utf-8"), "Lam + Alef Normal")

hdr("اختبار 1C: لام-ألف مع مدّة وهمزة (Ligatures المركبة)")
lam_madda_lig = b"\xEF\xBB\xB5"  # U+FEF5
run_test(lam_madda_lig, "Lam-Alef-Madda Ligature U+FEF5")
run_test("لآ".encode("utf-8"), "Lam + Alef-Madda Normal")

# ──────────────────────────────────────────────────────────────
# المحور 2: مقاعد الهمزة
# ──────────────────────────────────────────────────────────────
hdr("اختبار 2A: مقاعد الهمزة المختلفة")
for ch, name in [("أ", "همزة على ألف: أ (U+0623)"),
                 ("إ", "همزة تحت ألف: إ (U+0625)"),
                 ("ؤ", "همزة على واو: ؤ (U+0624)"),
                 ("ئ", "همزة على ياء (نبرة): ئ (U+0626)"),
                 ("ء", "همزة مفردة على السطر: ء (U+0621)"),
                 ("آ", "ألف مدّة: آ (U+0622)")]:
    run_test(ch.encode("utf-8"), name)

hdr("اختبار 2B: سياق الهمزات — نفس الكلمة بتمثيلات مختلفة")
run_test("مسؤول".encode("utf-8"), '"مسؤول" بهمزة على واو')
run_test("مسئول".encode("utf-8"), '"مسئول" بهمزة على نبرة')

# ──────────────────────────────────────────────────────────────
# المحور 3: رفض التشكيل الفاسد
# ──────────────────────────────────────────────────────────────
hdr("اختبار 3A: تشكيل مكرّر (فتحة مرتين على نفس الحرف)")
run_test("ب\u064E".encode("utf-8"), "باء + فتحة واحدة (عادي)")
run_test("ب\u064E\u064E".encode("utf-8"), "باء + فتحتين متتاليتين (يجب أن يُرفض)")

hdr("اختبار 3B: تشكيل متناقض (فتحة + كسرة على نفس الحرف)")
run_test("ب\u064E\u0650".encode("utf-8"), "باء + فتحة + كسرة (تناقض — يجب أن يُرفض)")

hdr("اختبار 3C: شدة + تنوين (صالحة) مقابل تنوينان (غير صالح)")
run_test("ب\u0651\u064C".encode("utf-8"), "باء + شدة + تنوين ضم (صالح)")
run_test("ب\u064C\u064B".encode("utf-8"), "باء + تنوين ضم + تنوين فتح (تناقض — يجب أن يُرفض)")

# ──────────────────────────────────────────────────────────────
# المحور 4: الضجيج الخفي (Noise Stripping)
# ──────────────────────────────────────────────────────────────
hdr("اختبار 4A: ZWJ/ZWNJ + BiDi controls (ضجيج خفي)")
zwj_bytes = b"\xE2\x80\x8F\xD9\x83\xE2\x80\x8D\xD8\xAA\xE2\x80\x8C\xD8\xA7\xD8\xA8"
run_test(zwj_bytes, "كتاب مع ZWJ+ZWNJ+RLM مخبأة")
run_test("كتاب".encode("utf-8"), "كتاب نظيفة")

hdr("اختبار 4B: BOM في منتصف النص")
bom_mid = b"\xD9\x83\xD8\xAA\xEF\xBB\xBF\xD8\xA7\xD8\xA8"
run_test(bom_mid, "كتاب مع BOM مخبأ في المنتصف")
run_test("كتاب".encode("utf-8"), "كتاب نظيفة")

hdr("اختبار 4C: Variation Selectors (VS1-VS16)")
vs_bytes = b"\xD8\xA8\xEF\xB8\x80\xD8\xA7\xD8\xA8"
run_test(vs_bytes, "باب مع Variation Selector مخبأ")
run_test("باب".encode("utf-8"), "باب نظيفة")

# ──────────────────────────────────────────────────────────────
# المحور 5: NFC مقابل NFD — أخطر اختبار سيادة
# ──────────────────────────────────────────────────────────────
hdr("اختبار 5: NFC مقابل NFD — أخطر اختبار سيادة")
run_test("آ".encode("utf-8"), "آ precomposed U+0622 (NFC — يجب أن يُقبل)")
run_test("ا\u0653".encode("utf-8"), "ألف + مدة U+0627+U+0653 (NFD — يجب أن يُرفض)")
run_test("أ".encode("utf-8"), "أ precomposed U+0623 (NFC — يجب أن يُقبل)")
run_test("ا\u0654".encode("utf-8"), "ألف + همزة فوق U+0627+U+0654 (NFD — يجب أن يُرفض)")

print("═" * 62)
print("  انتهت جميع الاختبارات الميدانية على مرجع Python!")
print("═" * 62)
