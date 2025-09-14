# -*- coding: utf-8 -*-

"""
Словник скандинавських імен та їх варіантів
Містить данські, норвезькі, шведські та фінські імена
"""

SCANDINAVIAN_NAMES = {
    # Danish names
    "Ларс": {
        "gender": "masc",
        "variants": ["Lars", "Lasse"],
        "diminutives": ["Ларс", "Lars"],
        "transliterations": ["Lars", "Lasse"],
        "declensions": ["Ларса", "Ларсу", "Ларса", "Ларсом", "Ларсі"],
    },
    "Анна": {
        "gender": "femn",
        "variants": ["Anna", "Anne"],
        "diminutives": ["Анна", "Anna"],
        "transliterations": ["Anna", "Anne"],
        "declensions": ["Анни", "Анні", "Анну", "Анною", "Анні"],
    },
    "Петер": {
        "gender": "masc",
        "variants": ["Peter", "Pete"],
        "diminutives": ["Петер", "Peter"],
        "transliterations": ["Peter", "Pete"],
        "declensions": ["Петера", "Петеру", "Петера", "Петером", "Петері"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Maria", "Mary"],
        "diminutives": ["Марія", "Maria"],
        "transliterations": ["Maria", "Mary"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Хенрік": {
        "gender": "masc",
        "variants": ["Henrik", "Henrik"],
        "diminutives": ["Хенрік", "Henrik"],
        "transliterations": ["Henrik", "Henrik"],
        "declensions": ["Хенріка", "Хенріку", "Хенріка", "Хенріком", "Хенріці"],
    },
    # Norwegian names
    "Оле": {
        "gender": "masc",
        "variants": ["Ole", "Ola"],
        "diminutives": ["Оле", "Ole"],
        "transliterations": ["Ole", "Ola"],
        "declensions": ["Оле", "Оле", "Оле", "Оле", "Оле"],
    },
    "Інгрід": {
        "gender": "femn",
        "variants": ["Ingrid", "Inger"],
        "diminutives": ["Інгрід", "Ingrid"],
        "transliterations": ["Ingrid", "Inger"],
        "declensions": ["Інгрід", "Інгрід", "Інгрід", "Інгрід", "Інгрід"],
    },
    "Ерік": {
        "gender": "masc",
        "variants": ["Erik", "Eirik"],
        "diminutives": ["Ерік", "Erik"],
        "transliterations": ["Erik", "Eirik"],
        "declensions": ["Еріка", "Еріку", "Еріка", "Еріком", "Еріці"],
    },
    "Сігрід": {
        "gender": "femn",
        "variants": ["Sigrid", "Siri"],
        "diminutives": ["Сігрід", "Sigrid"],
        "transliterations": ["Sigrid", "Siri"],
        "declensions": ["Сігрід", "Сігрід", "Сігрід", "Сігрід", "Сігрід"],
    },
    "Тор": {
        "gender": "masc",
        "variants": ["Thor", "Tor"],
        "diminutives": ["Тор", "Thor"],
        "transliterations": ["Thor", "Tor"],
        "declensions": ["Тора", "Тору", "Тора", "Тором", "Торі"],
    },
    # Swedish names
    "Карл": {
        "gender": "masc",
        "variants": ["Karl", "Carl"],
        "diminutives": ["Карл", "Karl"],
        "transliterations": ["Karl", "Carl"],
        "declensions": ["Карла", "Карлу", "Карла", "Карлом", "Карлі"],
    },
    "Інгеборг": {
        "gender": "femn",
        "variants": ["Ingeborg", "Inge"],
        "diminutives": ["Інгеборг", "Ingeborg"],
        "transliterations": ["Ingeborg", "Inge"],
        "declensions": ["Інгеборг", "Інгеборг", "Інгеборг", "Інгеборг", "Інгеборг"],
    },
    "Густав": {
        "gender": "masc",
        "variants": ["Gustav", "Gösta"],
        "diminutives": ["Густав", "Gustav"],
        "transliterations": ["Gustav", "Gösta"],
        "declensions": ["Густава", "Густаву", "Густава", "Густавом", "Густаві"],
    },
    "Астрід": {
        "gender": "femn",
        "variants": ["Astrid", "Astrid"],
        "diminutives": ["Астрід", "Astrid"],
        "transliterations": ["Astrid", "Astrid"],
        "declensions": ["Астрід", "Астрід", "Астрід", "Астрід", "Астрід"],
    },
    "Свен": {
        "gender": "masc",
        "variants": ["Sven", "Sven"],
        "diminutives": ["Свен", "Sven"],
        "transliterations": ["Sven", "Sven"],
        "declensions": ["Свена", "Свену", "Свена", "Свеном", "Свені"],
    },
    # Finnish names
    "Матті": {
        "gender": "masc",
        "variants": ["Matti", "Matti"],
        "diminutives": ["Матті", "Matti"],
        "transliterations": ["Matti", "Matti"],
        "declensions": ["Матті", "Матті", "Матті", "Матті", "Матті"],
    },
    "Марія": {
        "gender": "femn",
        "variants": ["Maria", "Maija"],
        "diminutives": ["Марія", "Maria"],
        "transliterations": ["Maria", "Maija"],
        "declensions": ["Марії", "Марії", "Марію", "Марією", "Марії"],
    },
    "Юха": {
        "gender": "masc",
        "variants": ["Juha", "Juhani"],
        "diminutives": ["Юха", "Juha"],
        "transliterations": ["Juha", "Juhani"],
        "declensions": ["Юхи", "Юсі", "Юху", "Юхою", "Юсі"],
    },
    "Аннелі": {
        "gender": "femn",
        "variants": ["Anneli", "Anneli"],
        "diminutives": ["Аннелі", "Anneli"],
        "transliterations": ["Anneli", "Anneli"],
        "declensions": ["Аннелі", "Аннелі", "Аннелі", "Аннелі", "Аннелі"],
    },
    "Пекка": {
        "gender": "masc",
        "variants": ["Pekka", "Pekka"],
        "diminutives": ["Пекка", "Pekka"],
        "transliterations": ["Pekka", "Pekka"],
        "declensions": ["Пекки", "Пекці", "Пекку", "Пеккою", "Пекці"],
    },
    # Icelandic names
    "Йон": {
        "gender": "masc",
        "variants": ["Jón", "Jon"],
        "diminutives": ["Йон", "Jón"],
        "transliterations": ["Jón", "Jon"],
        "declensions": ["Йона", "Йону", "Йона", "Йоном", "Йоні"],
    },
    "Гудрун": {
        "gender": "femn",
        "variants": ["Guðrún", "Gudrun"],
        "diminutives": ["Гудрун", "Guðrún"],
        "transliterations": ["Guðrún", "Gudrun"],
        "declensions": ["Гудрун", "Гудрун", "Гудрун", "Гудрун", "Гудрун"],
    },
    "Сігурдур": {
        "gender": "masc",
        "variants": ["Sigurður", "Sigurdur"],
        "diminutives": ["Сігурдур", "Sigurður"],
        "transliterations": ["Sigurður", "Sigurdur"],
        "declensions": [
            "Сігурдура",
            "Сігурдуру",
            "Сігурдура",
            "Сігурдуром",
            "Сігурдурі",
        ],
    },
    "Хельга": {
        "gender": "femn",
        "variants": ["Helga", "Helga"],
        "diminutives": ["Хельга", "Helga"],
        "transliterations": ["Helga", "Helga"],
        "declensions": ["Хельги", "Хельзі", "Хельгу", "Хельгою", "Хельзі"],
    },
    "Олафур": {
        "gender": "masc",
        "variants": ["Ólafur", "Olafur"],
        "diminutives": ["Олафур", "Ólafur"],
        "transliterations": ["Ólafur", "Olafur"],
        "declensions": ["Олафура", "Олафуру", "Олафура", "Олафуром", "Олафурі"],
    },
}

# All Scandinavian names
ALL_SCANDINAVIAN_NAMES = list(SCANDINAVIAN_NAMES.keys())

# Example output of name count in dictionary
# Total Scandinavian names count: {len(ALL_SCANDINAVIAN_NAMES)}
