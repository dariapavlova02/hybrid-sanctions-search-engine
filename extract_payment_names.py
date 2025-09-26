#!/usr/bin/env python3
"""
Extract real names and their diminutives from payment data
"""

import csv
import json
import re
from collections import defaultdict

def load_existing_diminutives():
    """Load existing diminutive mappings"""

    existing_ru = {}
    existing_uk = {}

    try:
        with open('/Users/dariapavlova/Desktop/ai-service/data/diminutives_ru.json', 'r', encoding='utf-8') as f:
            existing_ru = json.load(f)
        print(f"✅ Loaded {len(existing_ru)} Russian diminutives")
    except Exception as e:
        print(f"❌ Failed to load Russian diminutives: {e}")

    try:
        with open('/Users/dariapavlova/Desktop/ai-service/data/diminutives_uk.json', 'r', encoding='utf-8') as f:
            existing_uk = json.load(f)
        print(f"✅ Loaded {len(existing_uk)} Ukrainian diminutives")
    except Exception as e:
        print(f"❌ Failed to load Ukrainian diminutives: {e}")

    return existing_ru, existing_uk

def extract_real_names_from_payments(filename, top_n=5000):
    """Extract real names that appear in payment descriptions"""

    # Focus on names that actually appear in payments with decent frequency
    confirmed_names = set()
    potential_diminutives = defaultdict(set)

    # Known diminutive patterns for quick recognition
    common_diminutives = {
        # Russian
        'саша': 'александр', 'сережа': 'сергей', 'володя': 'владимир', 'дима': 'дмитрий',
        'коля': 'николай', 'леша': 'алексей', 'витя': 'виктор', 'петя': 'петр', 'рома': 'роман',
        'юра': 'юрий', 'миша': 'михаил', 'женя': 'евгений', 'вася': 'василий', 'толя': 'анатолий',
        'костя': 'константин', 'паша': 'павел', 'ваня': 'иван', 'стас': 'станислав',
        'аня': 'анна', 'маша': 'мария', 'лена': 'елена', 'оля': 'ольга', 'таня': 'татьяна',
        'наташа': 'наталья', 'света': 'светлана', 'люда': 'людмила', 'ира': 'ирина',
        'валя': 'валентина', 'галя': 'галина', 'люба': 'любовь', 'катя': 'екатерина',

        # Ukrainian
        'олександр': 'олександр', 'сергій': 'сергій', 'володимир': 'володимир', 'дмитро': 'дмитро',
        'микола': 'микола', 'олексій': 'олексій', 'віктор': 'віктор', 'петро': 'петро',
        'юрій': 'юрій', 'михайло': 'михайло', 'євген': 'євген', 'василь': 'василь',
        'анатолій': 'анатолій', 'костянтин': 'костянтин', 'павло': 'павло', 'іван': 'іван',
        'анна': 'анна', 'марія': 'марія', 'олена': 'олена', 'ольга': 'ольга', 'тетяна': 'тетяна',
        'наталія': 'наталія', 'світлана': 'світлана', 'людмила': 'людмила', 'ірина': 'ірина',
        'валентина': 'валентина', 'галина': 'галина', 'катерина': 'катерина', 'юлія': 'юлія'
    }

    print(f"🔍 Extracting real names from top {top_n} payment tokens...")

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Skip very short tokens or numbers
            if len(token) < 3 or any(char.isdigit() for char in token):
                continue

            # Skip obvious business/service words
            business_keywords = [
                'оплат', 'плат', 'послуг', 'сервіс', 'договор', 'баланс', 'рахунок', 'тариф',
                'комісі', 'заборг', 'абонент', 'клієнт', 'картк', 'банк', 'компан', 'доставк',
                'замовл', 'товар', 'услуг', 'страхов', 'енергі', 'води', 'газу', 'електр',
                'транспорт', 'квиток', 'проїзд', 'поїздк', 'метро', 'автобус'
            ]

            if any(keyword in token for keyword in business_keywords):
                continue

            # Check if it's a known name or diminutive
            if token in common_diminutives:
                full_name = common_diminutives[token]
                confirmed_names.add(full_name)
                potential_diminutives[full_name].add(token)
                print(f"📋 Found name: {token} → {full_name} (freq: {frequency})")

            # Check for patronymic patterns (high confidence for names)
            elif (token.endswith('ович') or token.endswith('евич') or token.endswith('івич') or
                  token.endswith('овна') or token.endswith('евна') or token.endswith('івна')):
                # This is likely a patronymic - the root might be a name
                root = token.replace('ович', '').replace('евич', '').replace('івич', '')
                root = root.replace('овна', '').replace('евна', '').replace('івна', '')
                if len(root) >= 3 and frequency >= 50:
                    confirmed_names.add(root + 'ій' if token.endswith(('ович', 'евич', 'івич')) else root + 'ій')
                    print(f"📋 Found patronymic: {token} → implies name {root}")

            # Check for surname patterns (might indicate real person names nearby)
            elif (token.endswith('енко') or token.endswith('ук') or token.endswith('юк') or
                  token.endswith('ський') or token.endswith('ська') or token.endswith('ич')):
                if frequency >= 100:  # Reasonable frequency for a surname
                    print(f"📋 Found surname pattern: {token} (freq: {frequency})")

            # Check for name-like tokens with good frequency
            elif (frequency >= 200 and len(token) >= 4 and len(token) <= 12 and
                  re.match(r'^[а-яїієґёa-z]+$', token, re.IGNORECASE) and
                  not token.startswith(('www', 'http', 'com')) and
                  token.count('і') <= 2 and  # Not too many 'і'
                  not any(substring in token for substring in ['нет', 'без', 'для', 'при', 'про'])):

                # This might be a name - let's be more selective
                vowel_count = sum(1 for c in token if c in 'аеиоуяюёіїєыэ')
                consonant_count = len(token) - vowel_count

                # Names usually have a good vowel/consonant ratio
                if 0.2 <= vowel_count / len(token) <= 0.6 and consonant_count >= 2:
                    confirmed_names.add(token)
                    print(f"📋 Potential name: {token} (freq: {frequency}, {percent:.3f}%)")

    return confirmed_names, potential_diminutives

def compare_with_existing(confirmed_names, potential_diminutives, existing_ru, existing_uk):
    """Compare found names with existing diminutives"""

    print(f"\n🔍 Comparing with existing diminutives...")

    new_mappings = {}
    already_covered = set()

    # Check what's already covered
    all_existing = set()
    all_existing.update(existing_ru.keys())
    all_existing.update(existing_ru.values())
    all_existing.update(existing_uk.keys())
    all_existing.update(existing_uk.values())

    for name in confirmed_names:
        if name in all_existing:
            already_covered.add(name)
        else:
            # This is a new name not in existing data
            if name in potential_diminutives:
                new_mappings[name] = list(potential_diminutives[name])

    print(f"✅ Already covered names: {len(already_covered)}")
    print(f"🆕 New names found: {len(new_mappings)}")

    return new_mappings, already_covered

def generate_additions_report(confirmed_names, potential_diminutives, new_mappings, already_covered):
    """Generate a comprehensive report"""

    print(f"\n" + "="*70)
    print(f"📊 PAYMENT NAMES ANALYSIS REPORT")
    print(f"="*70)

    print(f"\n📈 STATISTICS:")
    print(f"  • Total confirmed names: {len(confirmed_names)}")
    print(f"  • Names with diminutives: {len(potential_diminutives)}")
    print(f"  • Already in existing data: {len(already_covered)}")
    print(f"  • New names to add: {len(new_mappings)}")

    if new_mappings:
        print(f"\n🆕 NEW DIMINUTIVE MAPPINGS TO ADD:")
        for full_name, diminutives in sorted(new_mappings.items()):
            print(f"  {full_name}: {', '.join(diminutives)}")

    # Show some examples of already covered names
    if already_covered:
        covered_sample = sorted(list(already_covered))[:20]
        print(f"\n✅ EXAMPLES OF ALREADY COVERED NAMES:")
        print(f"  {', '.join(covered_sample)}")
        if len(already_covered) > 20:
            print(f"  ... and {len(already_covered) - 20} more")

    print(f"\n💡 RECOMMENDATIONS:")
    if new_mappings:
        print(f"  1. Add {len(new_mappings)} new diminutive mappings to appropriate files")
        print(f"  2. Verify the new names are actually person names, not places/organizations")
        print(f"  3. Determine if they should go to Russian or Ukrainian diminutives file")
    else:
        print(f"  1. Existing diminutive files appear to be comprehensive")
        print(f"  2. No significant new diminutives found in payment data")

    print(f"  4. Consider the high frequency of names in payments for quality assessment")

    print(f"\n" + "="*70)

if __name__ == "__main__":
    # Load existing diminutives
    existing_ru, existing_uk = load_existing_diminutives()

    # Extract names from payment data
    confirmed_names, potential_diminutives = extract_real_names_from_payments("all_tokens_by_frequency.csv", top_n=3000)

    # Compare with existing data
    new_mappings, already_covered = compare_with_existing(confirmed_names, potential_diminutives, existing_ru, existing_uk)

    # Generate report
    generate_additions_report(confirmed_names, potential_diminutives, new_mappings, already_covered)