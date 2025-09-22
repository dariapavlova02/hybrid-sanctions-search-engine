#!/usr/bin/env python3
"""Test _to_title logic"""

def _to_title_fixed(word: str) -> str:
    """
    Convert word to title case while preserving apostrophes and hyphens.
    """
    if not word:
        return word

    # Handle hyphenated words - apply titlecase to each segment
    if '-' in word:
        segments = word.split('-')
        return '-'.join(_to_title_fixed(segment) for segment in segments)

    # Handle single word - first letter uppercase, rest lowercase
    if len(word) == 1:
        return word.upper()

    # Handle apostrophes - capitalize letter after apostrophe
    # Support both ASCII apostrophe (') and typographic apostrophe (')
    result = word[0].upper()
    i = 1
    while i < len(word):
        if word[i] in ["'", "'"] and i + 1 < len(word):
            result += word[i] + word[i + 1].upper()
            i += 2
        else:
            result += word[i].lower()
            i += 1

    return result


def main():
    # Test cases
    test_cases = [
        "O'Connor",
        "O'Connor",
        "jean-claude",
        "O'CONNOR",
        "smith"
    ]

    for test_word in test_cases:
        result = _to_title_fixed(test_word)
        print(f"'{test_word}' -> '{result}'")

        # Show character details for apostrophe cases
        if "'" in test_word or "'" in test_word:
            print(f"  Input chars: {[f'{c}(U+{ord(c):04X})' for c in test_word]}")
            print(f"  Result chars: {[f'{c}(U+{ord(c):04X})' for c in result]}")


if __name__ == "__main__":
    main()