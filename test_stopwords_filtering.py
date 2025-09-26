#!/usr/bin/env python3
"""
Test how our enhanced stopwords filter the payment description
"""

# Load our enhanced stopwords
import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.data.dicts.stopwords import STOP_ALL

def analyze_payment_text():
    """Analyze the payment text with our stopwords"""

    text = """оплата опалення ор 533481 тернопіль вулблажкевич 6 кв 190 сума 22684 грн поповнення рахунку 533481 оплата вода ор 306176 тернопіль вулблажкевич 6 кв 190 сума 12686 грн поповнення рахунку 306176 оплата квартал л ор 206917 тернопіль вулблажкевич 6 кв 190 сума 6579 грн поповнення рахунку 206917 оплата управбуд ор 206917 тернопіль вулблажкевич 6 кв 190 сума 51346 грн поповнення рахунку 206917 оплата система гарячого водопостачання ор 533481 тернопіль вулблажкевич 6 кв 190 сума 6578 грн поповнення рахунку 533481 оплата газ розподіл ор 704254 тернопіль вулблажкевич 6 кв 190 сума 2128 грн поповнення рахунку 704254 оплата нафтогаз ор 320117936 тернопіль вулблажкевич 6 кв 190 сума 1989 грн поповнення рахунку 320117936 семенчук вікторія юріївна"""

    print("🔍 TESTING STOPWORDS FILTERING")
    print("=" * 70)
    print("📄 Original text:")
    print(text)
    print("\n" + "=" * 70)

    # Tokenize the text (simple split for testing)
    tokens = text.lower().split()

    print(f"📊 Total tokens: {len(tokens)}")
    print(f"📚 Stopwords loaded: {len(STOP_ALL)}")

    # Filter tokens
    filtered_tokens = []
    stopword_hits = []

    for token in tokens:
        # Clean token of punctuation for better matching
        clean_token = token.strip('.,!?;:()[]{}/"\'')

        if clean_token in STOP_ALL:
            stopword_hits.append(clean_token)
        elif clean_token.isdigit():
            # Numbers should be filtered out too
            stopword_hits.append(clean_token)
        elif len(clean_token) < 3:
            # Very short tokens
            stopword_hits.append(clean_token)
        else:
            filtered_tokens.append(clean_token)

    print(f"\n🎯 FILTERING RESULTS:")
    print(f"✅ Remaining tokens after filtering: {len(filtered_tokens)}")
    print(f"🚫 Filtered out (stopwords): {len(stopword_hits)}")

    print(f"\n📝 REMAINING TOKENS (potential names):")
    for i, token in enumerate(filtered_tokens, 1):
        print(f"  {i:2}. {token}")

    print(f"\n🚫 FILTERED OUT (sample of stopwords that were caught):")
    unique_stopwords = list(set(stopword_hits))[:20]  # First 20 unique
    for i, token in enumerate(unique_stopwords, 1):
        print(f"  {i:2}. {token}")
    if len(unique_stopwords) > 20:
        print(f"     ... and {len(set(stopword_hits)) - 20} more")

    print(f"\n🎯 EXPECTED RESULT:")
    print("Only names should remain: семенчук, вікторія, юріївна")

    # Check if our expected names are in the results
    expected_names = ['семенчук', 'вікторія', 'юріївна']
    found_names = [name for name in expected_names if name in filtered_tokens]

    print(f"\n✅ FOUND EXPECTED NAMES: {found_names}")

    # Check for any unexpected remaining tokens
    unexpected = [token for token in filtered_tokens if token not in expected_names]
    if unexpected:
        print(f"⚠️  UNEXPECTED REMAINING TOKENS: {unexpected}")
        print("   (These might need to be added to stopwords)")
    else:
        print("🎉 PERFECT! Only expected names remain.")

    return filtered_tokens, stopword_hits

if __name__ == "__main__":
    analyze_payment_text()