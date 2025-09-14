# -*- coding: utf-8 -*-

"""
Словник індійських імен та їх варіантів
Містить імена з різних регіонів Індії (Північна, Південна, Східна, Західна)
"""

INDIAN_NAMES = {
    # North Indian names (Hindi)
    "Арджун": {
        "gender": "masc",
        "variants": ["Arjun", "Arjuna"],
        "diminutives": ["Арджун", "Arjun"],
        "transliterations": ["Arjun", "Arjuna"],
        "declensions": ["Арджуна", "Арджуну", "Арджуна", "Арджуном", "Арджуні"],
    },
    "Прия": {
        "gender": "femn",
        "variants": ["Priya", "Priyanka"],
        "diminutives": ["Прия", "Priya"],
        "transliterations": ["Priya", "Priyanka"],
        "declensions": ["Приї", "Приї", "Прию", "Приєю", "Приї"],
    },
    "Раджеш": {
        "gender": "masc",
        "variants": ["Rajesh", "Raj"],
        "diminutives": ["Раджеш", "Rajesh"],
        "transliterations": ["Rajesh", "Raj"],
        "declensions": ["Раджеша", "Раджешу", "Раджеша", "Раджешем", "Раджеші"],
    },
    "Суніта": {
        "gender": "femn",
        "variants": ["Sunita", "Suneeta"],
        "diminutives": ["Суніта", "Sunita"],
        "transliterations": ["Sunita", "Suneeta"],
        "declensions": ["Суніти", "Суніті", "Суніту", "Сунітою", "Суніті"],
    },
    "Вікас": {
        "gender": "masc",
        "variants": ["Vikas", "Vikash"],
        "diminutives": ["Вікас", "Vikas"],
        "transliterations": ["Vikas", "Vikash"],
        "declensions": ["Вікаса", "Вікасу", "Вікаса", "Вікасом", "Вікасі"],
    },
    # South Indian names (Tamil, Telugu, Malayalam)
    "Ар'я": {
        "gender": "masc",
        "variants": ["Arya", "Aryan"],
        "diminutives": ["Ар'я", "Arya"],
        "transliterations": ["Arya", "Aryan"],
        "declensions": ["Ар'ї", "Ар'ї", "Ар'ю", "Ар'єю", "Ар'ї"],
    },
    "Діва": {
        "gender": "femn",
        "variants": ["Devi", "Divya"],
        "diminutives": ["Діва", "Devi"],
        "transliterations": ["Devi", "Divya"],
        "declensions": ["Діви", "Діві", "Діву", "Дівою", "Діві"],
    },
    "Крішна": {
        "gender": "masc",
        "variants": ["Krishna", "Krish"],
        "diminutives": ["Крішна", "Krishna"],
        "transliterations": ["Krishna", "Krish"],
        "declensions": ["Крішни", "Крішні", "Крішну", "Крішною", "Крішні"],
    },
    "Лакшмі": {
        "gender": "femn",
        "variants": ["Lakshmi", "Lakshmi"],
        "diminutives": ["Лакшмі", "Lakshmi"],
        "transliterations": ["Lakshmi", "Lakshmi"],
        "declensions": ["Лакшмі", "Лакшмі", "Лакшмі", "Лакшмі", "Лакшмі"],
    },
    "Рама": {
        "gender": "masc",
        "variants": ["Rama", "Ram"],
        "diminutives": ["Рама", "Rama"],
        "transliterations": ["Rama", "Ram"],
        "declensions": ["Рами", "Рамі", "Раму", "Рамою", "Рамі"],
    },
    # East Indian names (Bengali, Odia)
    "Абхішек": {
        "gender": "masc",
        "variants": ["Abhishek", "Abhi"],
        "diminutives": ["Абхішек", "Abhishek"],
        "transliterations": ["Abhishek", "Abhi"],
        "declensions": ["Абхішека", "Абхішеку", "Абхішека", "Абхішеком", "Абхішеці"],
    },
    "Аннапурна": {
        "gender": "femn",
        "variants": ["Annapurna", "Anna"],
        "diminutives": ["Аннапурна", "Annapurna"],
        "transliterations": ["Annapurna", "Anna"],
        "declensions": [
            "Аннапурни",
            "Аннапурні",
            "Аннапурну",
            "Аннапурною",
            "Аннапурні",
        ],
    },
    "Діпак": {
        "gender": "masc",
        "variants": ["Deepak", "Deep"],
        "diminutives": ["Діпак", "Deepak"],
        "transliterations": ["Deepak", "Deep"],
        "declensions": ["Діпака", "Діпаку", "Діпака", "Діпаком", "Діпаці"],
    },
    "Міра": {
        "gender": "femn",
        "variants": ["Meera", "Mira"],
        "diminutives": ["Міра", "Meera"],
        "transliterations": ["Meera", "Mira"],
        "declensions": ["Міри", "Мірі", "Міру", "Мірою", "Мірі"],
    },
    "Сантош": {
        "gender": "masc",
        "variants": ["Santosh", "Santo"],
        "diminutives": ["Сантош", "Santosh"],
        "transliterations": ["Santosh", "Santo"],
        "declensions": ["Сантоша", "Сантошу", "Сантоша", "Сантошем", "Сантоші"],
    },
    # West Indian names (Gujarati, Marathi)
    "Аміт": {
        "gender": "masc",
        "variants": ["Amit", "Amitabh"],
        "diminutives": ["Аміт", "Amit"],
        "transliterations": ["Amit", "Amitabh"],
        "declensions": ["Аміта", "Аміту", "Аміта", "Амітом", "Аміті"],
    },
    "Ашвіні": {
        "gender": "femn",
        "variants": ["Ashwini", "Ash"],
        "diminutives": ["Ашвіні", "Ashwini"],
        "transliterations": ["Ashwini", "Ash"],
        "declensions": ["Ашвіні", "Ашвіні", "Ашвіні", "Ашвіні", "Ашвіні"],
    },
    "Діпа": {
        "gender": "femn",
        "variants": ["Deepa", "Deep"],
        "diminutives": ["Діпа", "Deepa"],
        "transliterations": ["Deepa", "Deep"],
        "declensions": ["Діпи", "Діпі", "Діпу", "Діпою", "Діпі"],
    },
    "Маніш": {
        "gender": "masc",
        "variants": ["Manish", "Mani"],
        "diminutives": ["Маніш", "Manish"],
        "transliterations": ["Manish", "Mani"],
        "declensions": ["Маніша", "Манішу", "Маніша", "Манішем", "Маніші"],
    },
    "Ніта": {
        "gender": "femn",
        "variants": ["Neeta", "Nita"],
        "diminutives": ["Ніта", "Neeta"],
        "transliterations": ["Neeta", "Nita"],
        "declensions": ["Ніти", "Ніті", "Ніту", "Нітою", "Ніті"],
    },
}

# All Indian names
ALL_INDIAN_NAMES = list(INDIAN_NAMES.keys())

# Example output of name count in dictionary
# Total Indian names count: {len(ALL_INDIAN_NAMES)}
