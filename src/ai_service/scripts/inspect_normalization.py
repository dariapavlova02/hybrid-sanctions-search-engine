#!/usr/bin/env python3
"""
Utility script to run a step-by-step normalization pipeline inspection.

Shows intermediate results: basic cleanup, unicode normalization, tokenization,
lemmatization, and final normalized text.
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure project root on path for direct execution
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from ai_service.layers.normalization.normalization_service import NormalizationService


def _strip_domain_context(text: str, language: str) -> str:
    """Mimic orchestrator's domain-specific cleanup to drop leading/trailing stop words
    like 'платеж', 'оплата', 'перевод', 'от', 'для' and long legal phrases.
    Only trims from the boundaries to preserve internal name parts.
    """
    import re

    # Base stop words (fallbacks similar to orchestrator heuristics)
    sw = set()
    if language in ("ru", "uk"):
        sw.update({"платеж", "оплата", "перевод", "переказ", "від", "от", "для"})

    # Load long phrases and legal entities if available
    long_phrases = []
    try:
        from ai_service.data.dicts.company_triggers import COMPANY_TRIGGERS

        for lang in ("ru", "uk", "en"):
            data = COMPANY_TRIGGERS.get(lang, {})
            long_phrases.extend([x.lower() for x in data.get("long_phrases", [])])
            sw.update([x.lower() for x in data.get("legal_entities", [])])
    except Exception:
        pass

    s = text or ""
    # Cache lower() result to avoid repeated calls
    low = s.lower()
    for phrase in long_phrases:
        low = low.replace(phrase, " ")
    # Tokenize words (keep apostrophes and hyphens)
    tokens = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ\'-]+", low)
    # Use list slicing instead of pop() for better performance
    while tokens and tokens[0] in sw:
        tokens = tokens[1:]
    while tokens and tokens[-1] in sw:
        tokens = tokens[:-1]
    return " ".join(tokens)


def _extract_company_core(text: str, language: str) -> str:
    """Heuristic company core extraction mirroring orchestrator behavior.

    - Drop contract/date tails (по договору, №, от/від <num>)
    - Remove enclosing quotes
    - Remove leading legal entity markers (e.g., ТОВ, ООО, LLC)
    - Trim boundary stop words (від/от) and numbers
    """
    import re

    s = text or ""
    # Remove trailing contract/date/number tails
    s = re.split(
        r"\b(по\s+договор[ау]|догов[оі]р[ау]?|контракт[ау]?|№|#|от\s+\d|від\s+\d)",
        s,
        maxsplit=1,
    )[0]
    s = re.sub(r"\s+", " ", s).strip()
    # Remove enclosing quotes
    s = re.sub(r'^["«»\']\s*|\s*["«»\']$', "", s)

    # Load legal entity markers
    legal = set()
    try:
        from ai_service.data.dicts.company_triggers import COMPANY_TRIGGERS

        for lang in ("ru", "uk", "en"):
            data = COMPANY_TRIGGERS.get(lang, {})
            legal.update([x.lower() for x in data.get("legal_entities", [])])
    except Exception:
        # Basic defaults
        legal.update({"тов", "ооо", "ооошка", "llc", "ltd", "inc"})

    toks = re.findall(r"[A-Za-zА-Яа-яІіЇїЄєҐґ0-9\'-]+", s)
    # Remove boundary garbage and prefixes
    while toks and (toks[0].lower() in ("від", "от") or toks[0].isdigit()):
        toks.pop(0)
    # Remove legal entity prefixes
    while toks and toks[0].lower().strip('."«»”') in legal:
        toks.pop(0)
    # Remove trailing stop words/numbers
    while toks and (toks[-1].lower() in ("від", "от") or toks[-1].isdigit()):
        toks.pop()

    # If multiple tokens remain, prefer last token(s)
    if len(toks) >= 2:
        return " ".join(toks[-2:]) if len(toks[-1]) < 4 else toks[-1]
    return toks[0] if toks else ""


def inspect(
    text: str, language: str = "auto", apply_lemmatization: bool = True
) -> None:
    svc = NormalizationService()

    # Detect language (if auto)
    lang = language
    if language == "auto":
        try:
            lang = svc.detect_language(text)
        except Exception:
            lang = "en"

    print("=== Normalization Pipeline Inspection ===")
    print(f"Input: {text}")
    print(f"Language: {lang}")

    # 1) Basic cleanup (preserve names)
    step1 = svc.basic_cleanup(text, preserve_names=True)
    print("[1] Basic cleanup:", step1)

    # 2) Unicode normalization (lightweight)
    step2 = svc.normalize_unicode(step1)
    print("[2] Unicode normalized:", step2)

    # 2.5) Domain context cleanup (payment/company phrases)
    step25 = _strip_domain_context(step2, lang)
    print("[2.5] Context-trimmed:", step25)

    # 2.6) Company core (heuristic)
    company_core = _extract_company_core(step2, lang)
    if company_core:
        print("[2.6] Company-core:", company_core)

    # 3) Tokenization (on context-trimmed)
    tokens = svc.tokenize_text(step25 or step2, lang)
    print("[3] Tokens:", tokens)

    # 4) Lemmatization (optional)
    lemmas = svc.apply_lemmatization(tokens, lang) if apply_lemmatization else tokens
    print("[4] Lemmas:", lemmas)

    # 5) Final normalized string
    final_text = " ".join(lemmas)
    print("[5] Final normalized:", final_text)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Inspect normalization pipeline")
    parser.add_argument("text", type=str, help="Text to normalize")
    parser.add_argument("--lang", default="auto", help="Language code or 'auto'")
    parser.add_argument("--no-lemma", action="store_true", help="Disable lemmatization")
    args = parser.parse_args()

    inspect(args.text, language=args.lang, apply_lemmatization=not args.no_lemma)


if __name__ == "__main__":
    main()
