#!/usr/bin/env python3
"""
Analyze payment tokens for diminutives and nicknames
"""

import csv
import re
from collections import defaultdict

def analyze_diminutives(filename, top_n=1000):
    """Analyze top N tokens for potential diminutives and nicknames"""

    # Known common Ukrainian/Russian/English diminutive patterns
    diminutive_patterns = {
        'ru': {
            # Russian diminutive endings
            'я_endings': ['ня', 'ся', 'ля', 'ка', 'ша', 'та', 'да'],  # Таня, Вася, Коля, Анька, Саша, Света, Люда
            'и_endings': ['ик', 'ич', 'ин'],  # Костик, Костич, Костин
            'а_endings': ['ша', 'ня', 'ка', 'ля', 'ся', 'та', 'да'],  # Маша, Соня, Валька, Оля, Вася, Света, Люда
        },
        'uk': {
            # Ukrainian similar patterns
            'я_endings': ['ня', 'ся', 'ля', 'ка'],  # Таня, Вася, Коля, Анька
            'і_endings': ['ік'],  # Костік
            'а_endings': ['ша', 'ня', 'ка', 'ля', 'ся'],  # Маша, Соня, Валька, Оля, Вася
        }
    }

    # Common full names that might have diminutives in payment data
    known_full_names = {
        # Male names
        'александр': ['саша', 'саня', 'шура', 'алекс', 'саха'],
        'владимир': ['володя', 'вова', 'владик', 'володька'],
        'сергей': ['сережа', 'серега', 'серж'],
        'андрей': ['андрій', 'андреїв', 'андрюша'],
        'дмитрий': ['дима', 'димка', 'димон', 'митя'],
        'николай': ['коля', 'колян', 'микола', 'ника'],
        'алексей': ['леша', 'алеша', 'лёша', 'олекс'],
        'виктор': ['витя', 'витька', 'віктор'],
        'петр': ['петя', 'петро', 'петруша'],
        'роман': ['рома', 'ромка', 'романчик'],
        'олег': ['олежка', 'олега'],
        'юрий': ['юра', 'юрка', 'юрій'],
        'михаил': ['миша', 'мишка', 'михайло', 'міша'],
        'евгений': ['женя', 'женька', 'євген'],
        'валентин': ['валя', 'валик', 'валентін'],
        'василий': ['вася', 'васька', 'василь'],
        'артем': ['тема', 'темка', 'артемка'],
        'максим': ['макс', 'максик', 'максимка'],
        'игорь': ['игорёк', 'ігор'],
        'павел': ['паша', 'пашка', 'павло'],
        'анатолий': ['толя', 'толик', 'анатолій'],
        'константин': ['костя', 'костик', 'костян'],
        'иван': ['ваня', 'ванька', 'іван'],
        'денис': ['дэн', 'денчик', 'деня'],
        'станислав': ['стас', 'стасик', 'станіслав'],
        'тарас': ['тарасик', 'тараска'],
        'богдан': ['богданчик', 'богдя'],
        'виталий': ['виталик', 'віталій', 'віталя'],

        # Female names
        'анна': ['аня', 'анька', 'нюша', 'анечка'],
        'мария': ['маша', 'машка', 'мара', 'мари', 'марія'],
        'елена': ['лена', 'ленка', 'алена', 'єлена', 'олена'],
        'ольга': ['оля', 'олька', 'ольгуша'],
        'татьяна': ['таня', 'танька', 'тата', 'татьяна'],
        'наталья': ['наталя', 'наталія', 'наташа', 'ната'],
        'светлана': ['света', 'светик', 'светлана'],
        'людмила': ['люда', 'людка', 'людмила', 'мила'],
        'ирина': ['ира', 'ирка', 'ириша', 'ірина'],
        'валентина': ['валя', 'валька', 'валентина'],
        'галина': ['галя', 'галька', 'галина'],
        'нина': ['нинка', 'ниночка'],
        'любовь': ['люба', 'любка', 'любовь'],
        'екатерина': ['катя', 'катька', 'катерина', 'катерін'],
        'лариса': ['лара', 'ларка'],
        'тамара': ['тома', 'томка', 'тамарка'],
        'раиса': ['рая', 'раечка'],
        'вера': ['верочка', 'верка'],
        'алла': ['аллочка', 'алка'],
        'инна': ['иннка', 'инночка'],
        'оксана': ['ксюша', 'ксения', 'окся'],
        'юлия': ['юля', 'юлька', 'юлия'],
        'дарья': ['даша', 'дашка', 'дарка', 'дарина'],
        'анастасия': ['настя', 'настька', 'анастасія', 'настасья'],
        'виктория': ['вика', 'викка', 'вікторія'],
    }

    potential_diminutives = {}
    potential_full_names = set()
    uncertain_names = set()

    print(f"🔍 Analyzing potential names and diminutives from top {top_n} tokens...")

    with open(filename, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        for i, row in enumerate(reader):
            if i >= top_n:
                break

            token = row['Токен'].lower().strip()
            frequency = int(row['Частота'])
            percent = float(row['Процент'].replace('%', ''))

            # Skip very short or very long tokens
            if len(token) < 3 or len(token) > 15:
                continue

            # Skip obvious non-names
            if token.isdigit() or any(char.isdigit() for char in token):
                continue

            # Skip business terms
            business_terms = ['оплата', 'платеж', 'договор', 'послуг', 'сервіс', 'тариф', 'комісі']
            if any(term in token for term in business_terms):
                continue

            # Check if it's a known full name
            if token in known_full_names:
                potential_full_names.add(token)
                continue

            # Check if it matches diminutive patterns
            is_potential_diminutive = False

            # Russian/Ukrainian diminutive patterns
            for lang, patterns in diminutive_patterns.items():
                for ending_type, endings in patterns.items():
                    if any(token.endswith(ending) for ending in endings):
                        # Additional checks to avoid false positives
                        if frequency >= 100:  # Reasonable frequency for a name
                            # Look for potential full form
                            for full_name, diminutives in known_full_names.items():
                                if token in diminutives:
                                    if full_name not in potential_diminutives:
                                        potential_diminutives[full_name] = set()
                                    potential_diminutives[full_name].add(token)
                                    is_potential_diminutive = True
                                    break

            # If it looks like a name but we can't map it, mark as uncertain
            if not is_potential_diminutive and frequency >= 500:
                # Name-like patterns
                if (len(token) >= 4 and
                    token[0] not in 'йъьы' and  # Unlikely first letters for names
                    not any(substring in token for substring in ['оплат', 'плат', 'сума', 'грн']) and
                    token.count('і') <= 1 and  # Not too many 'і' characters
                    re.match(r'^[а-яёїієґa-z]+$', token, re.IGNORECASE)):  # Only letters
                    uncertain_names.add(token)

    return potential_diminutives, potential_full_names, uncertain_names

def analyze_existing_diminutives():
    """Analyze existing diminutives files to understand the format"""

    print("\n📋 Analyzing existing diminutives files...")

    files_to_check = [
        "/Users/dariapavlova/Desktop/ai-service/data/diminutives_ru.json",
        "/Users/dariapavlova/Desktop/ai-service/data/diminutives_uk.json"
    ]

    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                print(f"\n📁 File: {file_path}")
                content = f.read()[:500]  # First 500 characters
                print(f"Format preview: {content}...")
        except FileNotFoundError:
            print(f"❌ File not found: {file_path}")
        except Exception as e:
            print(f"❌ Error reading {file_path}: {e}")

def generate_diminutives_additions(potential_diminutives, potential_full_names, uncertain_names):
    """Generate recommended additions to diminutives dictionaries"""

    print(f"\n🎯 DIMINUTIVES ANALYSIS RESULTS")
    print("=" * 70)

    if potential_diminutives:
        print(f"\n📝 FOUND DIMINUTIVE MAPPINGS ({len(potential_diminutives)} full names):")
        for full_name, diminutives in sorted(potential_diminutives.items()):
            print(f"  {full_name}: {', '.join(sorted(diminutives))}")

    if potential_full_names:
        print(f"\n👤 POTENTIAL FULL NAMES FOUND ({len(potential_full_names)}):")
        sorted_names = sorted(list(potential_full_names))
        for i in range(0, len(sorted_names), 8):
            batch = sorted_names[i:i+8]
            print("  " + ", ".join(batch))

    if uncertain_names:
        print(f"\n❓ UNCERTAIN NAME-LIKE TOKENS ({len(uncertain_names)}):")
        print("  (These might be names but need manual verification)")
        sorted_uncertain = sorted(list(uncertain_names))
        for i in range(0, len(sorted_uncertain), 10):
            batch = sorted_uncertain[i:i+10]
            print("  " + ", ".join(batch))

    print("\n" + "=" * 70)
    print("💡 RECOMMENDATIONS:")
    print("1. Add found diminutive mappings to existing diminutives files")
    print("2. Review uncertain tokens manually - some might be valid names")
    print("3. Consider regional name variations (Ukrainian vs Russian)")
    print("4. Check if existing diminutives files need the new mappings")

if __name__ == "__main__":
    # First analyze existing diminutives format
    analyze_existing_diminutives()

    # Then analyze payment tokens
    potential_diminutives, potential_full_names, uncertain_names = analyze_diminutives("all_tokens_by_frequency.csv", top_n=2000)

    # Generate recommendations
    generate_diminutives_additions(potential_diminutives, potential_full_names, uncertain_names)