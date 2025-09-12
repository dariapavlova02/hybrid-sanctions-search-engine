# -*- coding: utf-8 -*-

"""
Dictionary of European names and their variants
Contains German, French, Italian, Spanish and other European names
"""

NAMES = {
    # German names
    "Ганс": {
        "gender": "masc",
        "variants": ["Hans", "Johannes"],
        "diminutives": ["Ганс", "Hans"],
        "transliterations": ["Hans", "Johannes"],
        "declensions": ["Ганса", "Гансу", "Ганса", "Гансом", "Гансі"],
    },
    "Грета": {
        "gender": "femn",
        "variants": ["Greta", "Margarete"],
        "diminutives": ["Грета", "Greta"],
        "transliterations": ["Greta", "Margarete"],
        "declensions": ["Грети", "Греті", "Грету", "Гретою", "Греті"],
    },
    "Вольфганг": {
        "gender": "masc",
        "variants": ["Wolfgang", "Wolf"],
        "diminutives": ["Вольфганг", "Wolfgang"],
        "transliterations": ["Wolfgang", "Wolf"],
        "declensions": [
            "Вольфганга",
            "Вольфгангу",
            "Вольфганга",
            "Вольфгангом",
            "Вольфганзі",
        ],
    },
    "Інгеборг": {
        "gender": "femn",
        "variants": ["Ingeborg", "Inge"],
        "diminutives": ["Інгеборг", "Ingeborg"],
        "transliterations": ["Ingeborg", "Inge"],
        "declensions": ["Інгеборг", "Інгеборг", "Інгеборг", "Інгеборг", "Інгеборг"],
    },
    "Фрідріх": {
        "gender": "masc",
        "variants": ["Friedrich", "Fritz"],
        "diminutives": ["Фрідріх", "Friedrich"],
        "transliterations": ["Friedrich", "Fritz"],
        "declensions": ["Фрідріха", "Фрідріху", "Фрідріха", "Фрідріхом", "Фрідрісі"],
    },
    # French names
    "Жан": {
        "gender": "masc",
        "variants": ["Jean", "John"],
        "diminutives": ["Жан", "Jean"],
        "transliterations": ["Jean", "John"],
        "declensions": ["Жана", "Жану", "Жана", "Жаном", "Жані"],
    },
    "Марі": {
        "gender": "femn",
        "variants": ["Marie", "Maria"],
        "diminutives": ["Марі", "Marie"],
        "transliterations": ["Marie", "Maria"],
        "declensions": ["Марі", "Марі", "Марі", "Марі", "Марі"],
    },
    "П'єр": {
        "gender": "masc",
        "variants": ["Pierre", "Peter"],
        "diminutives": ["П'єр", "Pierre"],
        "transliterations": ["Pierre", "Peter"],
        "declensions": ["П'єра", "П'єру", "П'єра", "П'єром", "П'єрі"],
    },
    "Софі": {
        "gender": "femn",
        "variants": ["Sophie", "Sophia"],
        "diminutives": ["Софі", "Sophie"],
        "transliterations": ["Sophie", "Sophia"],
        "declensions": ["Софі", "Софі", "Софі", "Софі", "Софі"],
    },
    "Луї": {
        "gender": "masc",
        "variants": ["Louis", "Luis"],
        "diminutives": ["Луї", "Louis"],
        "transliterations": ["Louis", "Luis"],
        "declensions": ["Луї", "Луї", "Луї", "Луї", "Луї"],
    },
    # Italian names
    "Джузеппе": {
        "gender": "masc",
        "variants": ["Giuseppe", "Joe"],
        "diminutives": ["Джузеппе", "Giuseppe"],
        "transliterations": ["Giuseppe", "Joe"],
        "declensions": ["Джузеппе", "Джузеппе", "Джузеппе", "Джузеппе", "Джузеппе"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Maria", "Mary"],
        "diminutives": ["Марія", "Maria"],
        "transliterations": ["Maria", "Mary"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Антоніо": {
        "gender": "masc",
        "variants": ["Antonio", "Tony"],
        "diminutives": ["Антоніо", "Antonio"],
        "transliterations": ["Antonio", "Tony"],
        "declensions": ["Антоніо", "Антоніо", "Антоніо", "Антоніо", "Антоніо"],
    },
    "Лукреція": {
        "gender": "femn",
        "variants": ["Lucrezia", "Lucretia"],
        "diminutives": ["Лукреція", "Lucrezia"],
        "transliterations": ["Lucrezia", "Lucretia"],
        "declensions": ["Лукреції", "Лукреції", "Лукрецію", "Лукрецією", "Лукреції"],
    },
    "Марко": {
        "gender": "masc",
        "variants": ["Marco", "Mark"],
        "diminutives": ["Марко", "Marco"],
        "transliterations": ["Marco", "Mark"],
        "declensions": ["Марка", "Марку", "Марка", "Марком", "Марці"],
    },
    # Spanish names
    "Хуан": {
        "gender": "masc",
        "variants": ["Juan", "John"],
        "diminutives": ["Хуан", "Juan"],
        "transliterations": ["Juan", "John"],
        "declensions": ["Хуана", "Хуану", "Хуана", "Хуаном", "Хуані"],
    },
    "Ізабела": {
        "gender": "femn",
        "variants": ["Isabella", "Isabel"],
        "diminutives": ["Ізабела", "Isabella"],
        "transliterations": ["Isabella", "Isabel"],
        "declensions": ["Ізабели", "Ізабелі", "Ізабелу", "Ізабелою", "Ізабелі"],
    },
    "Карлос": {
        "gender": "masc",
        "variants": ["Carlos", "Charles"],
        "diminutives": ["Карлос", "Carlos"],
        "transliterations": ["Carlos", "Charles"],
        "declensions": ["Карлоса", "Карлосу", "Карлоса", "Карлосом", "Карлосі"],
    },
    "Кармен": {
        "gender": "femn",
        "variants": ["Carmen", "Carmela"],
        "diminutives": ["Кармен", "Carmen"],
        "transliterations": ["Carmen", "Carmela"],
        "declensions": ["Кармен", "Кармен", "Кармен", "Кармен", "Кармен"],
    },
    "Мігель": {
        "gender": "masc",
        "variants": ["Miguel", "Michael"],
        "diminutives": ["Мігель", "Miguel"],
        "transliterations": ["Miguel", "Michael"],
        "declensions": ["Мігеля", "Мігелю", "Мігеля", "Мігелем", "Мігелі"],
    },
    # Polish names
    "Ян": {
        "gender": "masc",
        "variants": ["Jan", "John"],
        "diminutives": ["Ян", "Jan"],
        "transliterations": ["Jan", "John"],
        "declensions": ["Яна", "Яну", "Яна", "Яном", "Яні"],
    },
    "Анна": {
        "gender": "femn",
        "variants": ["Anna", "Anne"],
        "diminutives": ["Анна", "Anna"],
        "transliterations": ["Anna", "Anne"],
        "declensions": ["Анни", "Анні", "Анну", "Анною", "Анні"],
    },
    "Пйотр": {
        "gender": "masc",
        "variants": ["Piotr", "Peter"],
        "diminutives": ["Пйотр", "Piotr"],
        "transliterations": ["Piotr", "Peter"],
        "declensions": ["Пйотра", "Пйотру", "Пйотра", "Пйотром", "Пйотрі"],
    },
    "Катажина": {
        "gender": "femn",
        "variants": ["Katarzyna", "Katherine"],
        "diminutives": ["Катажина", "Katarzyna"],
        "transliterations": ["Katarzyna", "Katherine"],
        "declensions": ["Катажини", "Катажині", "Катажину", "Катажиною", "Катажині"],
    },
    "Станіслав": {
        "gender": "masc",
        "variants": ["Stanislaw", "Stan"],
        "diminutives": ["Станіслав", "Stanislaw"],
        "transliterations": ["Stanislaw", "Stan"],
        "declensions": [
            "Станіслава",
            "Станіславу",
            "Станіслава",
            "Станіславом",
            "Станіславі",
        ],
    },
    # Additional Czech names
    "Ян": {
        "gender": "masc",
        "variants": ["Jan", "John"],
        "diminutives": ["Ян", "Jan"],
        "transliterations": ["Jan", "John"],
        "declensions": ["Яна", "Яну", "Яна", "Яном", "Яні"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Marie", "Mary"],
        "diminutives": ["Марія", "Marie"],
        "transliterations": ["Marie", "Mary"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Петр": {
        "gender": "masc",
        "variants": ["Petr", "Peter"],
        "diminutives": ["Петр", "Petr"],
        "transliterations": ["Petr", "Peter"],
        "declensions": ["Петра", "Петру", "Петра", "Петром", "Петрі"],
    },
    "Анна": {
        "gender": "femn",
        "variants": ["Anna", "Anne"],
        "diminutives": ["Анна", "Anna"],
        "transliterations": ["Anna", "Anne"],
        "declensions": ["Анни", "Анні", "Анну", "Анною", "Анні"],
    },
    "Томаш": {
        "gender": "masc",
        "variants": ["Tomas", "Thomas"],
        "diminutives": ["Томаш", "Tomas"],
        "transliterations": ["Tomas", "Thomas"],
        "declensions": ["Томаша", "Томашу", "Томаша", "Томашем", "Томаші"],
    },
    # Additional Hungarian names
    "Іштван": {
        "gender": "masc",
        "variants": ["Istvan", "Stephen"],
        "diminutives": ["Іштван", "Istvan"],
        "transliterations": ["Istvan", "Stephen"],
        "declensions": ["Іштвана", "Іштвану", "Іштвана", "Іштваном", "Іштвані"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Maria", "Mary"],
        "diminutives": ["Марія", "Maria"],
        "transliterations": ["Maria", "Mary"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Янош": {
        "gender": "masc",
        "variants": ["Janos", "John"],
        "diminutives": ["Янош", "Janos"],
        "transliterations": ["Janos", "John"],
        "declensions": ["Яноша", "Яношу", "Яноша", "Яношем", "Яноші"],
    },
    "Ержебет": {
        "gender": "femn",
        "variants": ["Erzsebet", "Elizabeth"],
        "diminutives": ["Ержебет", "Erzsebet"],
        "transliterations": ["Erzsebet", "Elizabeth"],
        "declensions": ["Ержебет", "Ержебет", "Ержебет", "Ержебет", "Ержебет"],
    },
    "Ласло": {
        "gender": "masc",
        "variants": ["Laszlo", "Ladislas"],
        "diminutives": ["Ласло", "Laszlo"],
        "transliterations": ["Laszlo", "Ladislas"],
        "declensions": ["Ласла", "Ласлу", "Ласла", "Ласлом", "Ласлі"],
    },
    # Additional Romanian names
    "Іон": {
        "gender": "masc",
        "variants": ["Ion", "John"],
        "diminutives": ["Іон", "Ion"],
        "transliterations": ["Ion", "John"],
        "declensions": ["Іона", "Іону", "Іона", "Іоном", "Іоні"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Maria", "Mary"],
        "diminutives": ["Марія", "Maria"],
        "transliterations": ["Maria", "Mary"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Георге": {
        "gender": "masc",
        "variants": ["Gheorghe", "George"],
        "diminutives": ["Георге", "Gheorghe"],
        "transliterations": ["Gheorghe", "George"],
        "declensions": ["Георге", "Георге", "Георге", "Георге", "Георге"],
    },
    "Анна": {
        "gender": "femn",
        "variants": ["Ana", "Anne"],
        "diminutives": ["Анна", "Ana"],
        "transliterations": ["Ana", "Anne"],
        "declensions": ["Анни", "Анні", "Анну", "Анною", "Анні"],
    },
    "Ніколае": {
        "gender": "masc",
        "variants": ["Nicolae", "Nicholas"],
        "diminutives": ["Ніколае", "Nicolae"],
        "transliterations": ["Nicolae", "Nicholas"],
        "declensions": ["Ніколае", "Ніколае", "Ніколае", "Ніколае", "Ніколае"],
    },
}

# All European names
# ALL_NAMES = list(NAMES.keys())

# Example output of names count in dictionary
# Total European names count: {len(ALL_EUROPEAN_NAMES)}
