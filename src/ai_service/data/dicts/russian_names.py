# -*- coding: utf-8 -*-

"""
Розширений словник російських імен та їх варіантів.
Словник містить початкові імена, імена з додаткового списку
та інші популярні імена для максимального охоплення.
"""

RUSSIAN_NAMES = {
    'Сергей': {
        'gender': 'masc',
        'variants': ['Сергій'],
        'diminutives': ['Серёжа', 'Серёжка', 'Серёженька', 'Серж'],
        'transliterations': ['Sergey', 'Serhii', 'Seryozha'],
        'declensions': ['Сергея', 'Сергею', 'Сергея', 'Сергеем', 'Сергее']
    },
    'Владимир': {
        'gender': 'masc',
        'variants': ['Володимир'],
        'diminutives': ['Вова', 'Вовка', 'Вовочка', 'Володя', 'Володи', 'Володе', 'Володю', 'Володей', 'Володе'],
        'transliterations': ['Vladimir', 'Volodymyr', 'Volodya'],
        'declensions': ['Владимира', 'Владимиру', 'Владимира', 'Владимиром', 'Владимире']
    },
    'Петр': {
        'gender': 'masc',
        'variants': ['Петро'],
        'diminutives': ['Петя', 'Петенька', 'Петруша'],
        'transliterations': ['Petr', 'Petro', 'Petya'],
        'declensions': ['Петра', 'Петру', 'Петра', 'Петром', 'Петре']
    },
    'Иван': {
        'gender': 'masc',
        'variants': ['Іван'],
        'diminutives': ['Ваня', 'Ванька', 'Ванюша', 'Иванушка'],
        'transliterations': ['Ivan', 'Vanya'],
        'declensions': ['Ивана', 'Ивану', 'Ивана', 'Иваном', 'Иване']
    },
    'Алексей': {
        'gender': 'masc',
        'variants': ['Олексій'],
        'diminutives': ['Алёша', 'Лёша', 'Алёшка', 'Лёха'],
        'transliterations': ['Alexey', 'Oleksii', 'Alyosha'],
        'declensions': ['Алексея', 'Алексею', 'Алексея', 'Алексеем', 'Алексее']
    },
    'Дарья': {
        'gender': 'femn',
        'variants': ['Дарія'],
        'diminutives': ['Даша', 'Дашенька', 'Дашуля', 'Дарьюшка'],
        'transliterations': ['Darya', 'Dariia', 'Dasha'],
        'declensions': ['Дарьи', 'Дарье', 'Дарью', 'Дарьей', 'Дарье']
    },
    'Анна': {
        'gender': 'femn',
        'variants': ['Ганна'],
        'diminutives': ['Аня', 'Анечка', 'Анюта', 'Нюра'],
        'transliterations': ['Anna', 'Hanna', 'Anya'],
        'declensions': ['Анны', 'Анне', 'Анну', 'Анной', 'Анне']
    },
    'Алла': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Алочка', 'Аллочка'],
        'transliterations': ['Alla'],
        'declensions': ['Аллы', 'Алле', 'Аллу', 'Аллой', 'Алле']
    },
    'Мария': {
        'gender': 'femn',
        'variants': ['Марія'],
        'diminutives': ['Маша', 'Машенька', 'Маруся', 'Маня'],
        'transliterations': ['Mariya', 'Mariia', 'Masha'],
        'declensions': ['Марии', 'Марии', 'Марию', 'Марией', 'Марии']
    },
    'Елена': {
        'gender': 'femn',
        'variants': ['Олена'],
        'diminutives': ['Лена', 'Леночка', 'Ленуся', 'Алёна'],
        'transliterations': ['Elena', 'Olena', 'Lena'],
        'declensions': ['Елены', 'Елене', 'Елену', 'Еленой', 'Елене']
    },
    'Наталия': {
        'gender': 'femn',
        'variants': ['Наталія'],
        'diminutives': ['Наташа', 'Наташенька', 'Ната', 'Таша'],
        'transliterations': ['Nataliya', 'Nataliia', 'Natasha'],
        'declensions': ['Наталии', 'Наталии', 'Наталию', 'Наталией', 'Наталии']
    },
    'Михаил': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Миша', 'Мишенька', 'Мишка', 'Михайло'],
        'transliterations': ['Mikhail', 'Mykhailo', 'Misha'],
        'declensions': ['Михаила', 'Михаилу', 'Михаила', 'Михаилом', 'Михаиле']
    },
    'Андрей': {
        'gender': 'masc',
        'variants': ['Андрій'],
        'diminutives': ['Андрюша', 'Андрюшка', 'Андрейка', 'Дрон'],
        'transliterations': ['Andrey', 'Andrii', 'Andryusha'],
        'declensions': ['Андрея', 'Андрею', 'Андрея', 'Андреем', 'Андрее']
    },
    'Василий': {
        'gender': 'masc',
        'variants': ['Василь'],
        'diminutives': ['Вася', 'Васенька', 'Василёк'],
        'transliterations': ['Vasily', 'Vasyl', 'Vasya'],
        'declensions': ['Василия', 'Василию', 'Василия', 'Василием', 'Василии']
    },
    'Ирина': {
        'gender': 'femn',
        'variants': ['Ірина'],
        'diminutives': ['Ира', 'Ирочка', 'Иришка', 'Ириша'],
        'transliterations': ['Irina', 'Iryna', 'Ira'],
        'declensions': ['Ирины', 'Ирине', 'Ирину', 'Ириной', 'Ирине']
    },
    'Татьяна': {
        'gender': 'femn',
        'variants': ['Тетяна'],
        'diminutives': ['Таня', 'Танечка', 'Танюша', 'Тата'],
        'transliterations': ['Tatyana', 'Tetiana', 'Tanya'],
        'declensions': ['Татьяны', 'Татьяне', 'Татьяну', 'Татьяной', 'Татьяне']
    },
    'Александр': {
        'gender': 'masc',
        'variants': ['Олександр'],
        'diminutives': ['Саша', 'Саши', 'Саше', 'Сашу', 'Сашей', 'Саше', 'Сашенька', 'Шура', 'Саня', 'Алекс'],
        'transliterations': ['Aleksandr', 'Oleksandr', 'Sasha'],
        'declensions': ['Александра', 'Александру', 'Александра', 'Александром', 'Александре']
    },
    'Дмитрий': {
        'gender': 'masc',
        'variants': ['Дмитро'],
        'diminutives': ['Дима', 'Димы', 'Диме', 'Диму', 'Димой', 'Диме', 'Димочка', 'Митя', 'Димон'],
        'transliterations': ['Dmitry', 'Dmytro', 'Dima'],
        'declensions': ['Дмитрия', 'Дмитрию', 'Дмитрия', 'Дмитрием', 'Дмитрии']
    },
    'Богдан': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Богданчик', 'Бодя', 'Дана'],
        'transliterations': ['Bogdan', 'Bohdan', 'Bodya'],
        'declensions': ['Богдана', 'Богдану', 'Богдана', 'Богданом', 'Богдане']
    },
    'Роман': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Рома', 'Ромочка', 'Ромка'],
        'transliterations': ['Roman', 'Roma'],
        'declensions': ['Романа', 'Роману', 'Романа', 'Романом', 'Романе']
    },
    'Тарас': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Тарасик', 'Тараска'],
        'transliterations': ['Taras', 'Tarasik'],
        'declensions': ['Тараса', 'Тарасу', 'Тараса', 'Тарасом', 'Тарасе']
    },
    'Юрий': {
        'gender': 'masc',
        'variants': ['Юрій'],
        'diminutives': ['Юра', 'Юрочка', 'Юрасик'],
        'transliterations': ['Yuriy', 'Yurii', 'Yura'],
        'declensions': ['Юрия', 'Юрию', 'Юрия', 'Юрием', 'Юрии']
    },
    'Виктор': {
        'gender': 'masc',
        'variants': ['Віктор'],
        'diminutives': ['Витя', 'Витенька', 'Витек'],
        'transliterations': ['Viktor', 'Vitya'],
        'declensions': ['Виктора', 'Виктору', 'Виктора', 'Виктором', 'Викторе']
    },
    'Виктория': {
        'gender': 'femn',
        'variants': ['Вікторія'],
        'diminutives': ['Вика', 'Викуля', 'Викуся'],
        'transliterations': ['Viktoriya', 'Viktoriia', 'Vika'],
        'declensions': ['Виктории', 'Виктории', 'Викторию', 'Викторией', 'Виктории']
    },
    'Юлия': {
        'gender': 'femn',
        'variants': ['Юлія'],
        'diminutives': ['Юля', 'Юленька', 'Юлечка'],
        'transliterations': ['Yuliya', 'Yuliia', 'Yulya'],
        'declensions': ['Юлии', 'Юлии', 'Юлию', 'Юлией', 'Юлии']
    },
    'Екатерина': {
        'gender': 'femn',
        'variants': ['Катерина'],
        'diminutives': ['Катя', 'Катенька', 'Катюша'],
        'transliterations': ['Ekaterina', 'Kateryna', 'Katya'],
        'declensions': ['Екатерины', 'Екатерине', 'Екатерину', 'Екатериной', 'Екатерине']
    },
    'Людмила': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Люда', 'Людочка', 'Мила'],
        'transliterations': ['Lyudmila', 'Liudmyla', 'Lyuda'],
        'declensions': ['Людмилы', 'Людмиле', 'Людмилу', 'Людмилой', 'Людмиле']
    },
    'Светлана': {
        'gender': 'femn',
        'variants': ['Світлана'],
        'diminutives': ['Света', 'Светочка', 'Лана'],
        'transliterations': ['Svetlana', 'Svitlana', 'Sveta'],
        'declensions': ['Светланы', 'Светлане', 'Светлану', 'Светланой', 'Светлане']
    },
    'Валентина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Валя', 'Валечка', 'Валюша'],
        'transliterations': ['Valentina', 'Valentyna', 'Valya'],
        'declensions': ['Валентины', 'Валентине', 'Валентину', 'Валентиной', 'Валентине']
    },
    'Николай': {
        'gender': 'masc',
        'variants': ['Микола'],
        'diminutives': ['Коля', 'Коленька', 'Николаша'],
        'transliterations': ['Nikolay', 'Mykola', 'Kolya'],
        'declensions': ['Николая', 'Николаю', 'Николая', 'Николаем', 'Николае']
    },
    'Павел': {
        'gender': 'masc',
        'variants': ['Павло'],
        'diminutives': ['Паша', 'Пашенька', 'Павлик', 'Павлуша'],
        'transliterations': ['Pavel', 'Pavlo', 'Pasha'],
        'declensions': ['Павла', 'Павлу', 'Павла', 'Павлом', 'Павле']
    },
    'Олег': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Олежка', 'Олежек', 'Олегушка'],
        'transliterations': ['Oleg', 'Oleh', 'Olezhka'],
        'declensions': ['Олега', 'Олегу', 'Олега', 'Олегом', 'Олеге']
    },
    'Игорь': {
        'gender': 'masc',
        'variants': ['Ігор'],
        'diminutives': ['Игорёк', 'Гоша', 'Игорюша'],
        'transliterations': ['Igor', 'Ihor', 'Igoryok'],
        'declensions': ['Игоря', 'Игорю', 'Игоря', 'Игорем', 'Игоре']
    },
    'Станислав': {
        'gender': 'masc',
        'variants': ['Станіслав'],
        'diminutives': ['Стас', 'Стасик', 'Слава'],
        'transliterations': ['Stanislav', 'Stas'],
        'declensions': ['Станислава', 'Станиславу', 'Станислава', 'Станиславом', 'Станиславе']
    },
    'Максим': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Макс', 'Максимка', 'Максик'],
        'transliterations': ['Maksim', 'Maksym', 'Max'],
        'declensions': ['Максима', 'Максиму', 'Максима', 'Максимом', 'Максиме']
    },
    'Артем': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Тёма', 'Артёмка', 'Тёмыч'],
        'transliterations': ['Artem', 'Tyoma'],
        'declensions': ['Артема', 'Артему', 'Артема', 'Артемом', 'Артеме']
    },
    'Никита': {
        'gender': 'masc',
        'variants': ['Микита'],
        'diminutives': ['Никитка', 'Никиша', 'Кеша'],
        'transliterations': ['Nikita', 'Mykyta', 'Nikitka'],
        'declensions': ['Никиты', 'Никите', 'Никиту', 'Никитой', 'Никите']
    },
    'Ольга': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Оля', 'Оленька', 'Олечка', 'Ольгуня'],
        'transliterations': ['Olga', 'Olha', 'Olya'],
        'declensions': ['Ольги', 'Ольге', 'Ольгу', 'Ольгой', 'Ольге']
    },
    'Анастасия': {
        'gender': 'femn',
        'variants': ['Анастасія'],
        'diminutives': ['Настя', 'Настенька', 'Ася', 'Стася'],
        'transliterations': ['Anastasiya', 'Anastasiia', 'Nastya'],
        'declensions': ['Анастасии', 'Анастасии', 'Анастасию', 'Анастасией', 'Анастасии']
    },
    'Ксения': {
        'gender': 'femn',
        'variants': ['Ксенія'],
        'diminutives': ['Ксюша', 'Ксеня', 'Ксюха'],
        'transliterations': ['Kseniya', 'Kseniia', 'Ksyusha'],
        'declensions': ['Ксении', 'Ксении', 'Ксению', 'Ксенией', 'Ксении']
    },
    'Александра': {
        'gender': 'femn',
        'variants': ['Олександра'],
        'diminutives': ['Саша', 'Сашенька', 'Шура', 'Алекса'],
        'transliterations': ['Aleksandra', 'Oleksandra', 'Sasha'],
        'declensions': ['Александры', 'Александре', 'Александру', 'Александрой', 'Александре']
    },
    'София': {
        'gender': 'femn',
        'variants': ['Софія'],
        'diminutives': ['Соня', 'Сонечка', 'Софа'],
        'transliterations': ['Sofiya', 'Sofiia', 'Sonya'],
        'declensions': ['Софии', 'Софии', 'Софию', 'Софией', 'Софии']
    },
    'Полина': {
        'gender': 'femn',
        'variants': ['Поліна'],
        'diminutives': ['Поля', 'Полиночка', 'Полюша'],
        'transliterations': ['Polina', 'Polya'],
        'declensions': ['Полины', 'Полине', 'Полину', 'Полиной', 'Полине']
    },
    'Вера': {
        'gender': 'femn',
        'variants': ['Віра'],
        'diminutives': ['Верочка', 'Веруня', 'Веруся'],
        'transliterations': ['Vera', 'Vira', 'Verochka'],
        'declensions': ['Веры', 'Вере', 'Веру', 'Верой', 'Вере']
    },
    'Надежда': {
        'gender': 'femn',
        'variants': ['Надія'],
        'diminutives': ['Надя', 'Наденька', 'Надюша'],
        'transliterations': ['Nadezhda', 'Nadiia', 'Nadya'],
        'declensions': ['Надежды', 'Надежде', 'Надежду', 'Надеждой', 'Надежде']
    },
    'Любовь': {
        'gender': 'femn',
        'variants': ['Любов'],
        'diminutives': ['Люба', 'Любочка', 'Любаша'],
        'transliterations': ['Lyubov', 'Liubov', 'Lyuba'],
        'declensions': ['Любови', 'Любови', 'Любовь', 'Любовью', 'Любови']
    },
    'Константин': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Костя', 'Костик', 'Константинчик'],
        'transliterations': ['Konstantin', 'Kostya'],
        'declensions': ['Константина', 'Константину', 'Константина', 'Константином', 'Константине']
    },
    'Евгений': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Женя', 'Евгенька', 'Женька'],
        'transliterations': ['Evgeniy', 'Yevgeniy', 'Zhenya'],
        'declensions': ['Евгения', 'Евгению', 'Евгения', 'Евгением', 'Евгении']
    },
    'Валерий': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Валера', 'Валерка', 'Лера'],
        'transliterations': ['Valeriy', 'Valera'],
        'declensions': ['Валерия', 'Валерию', 'Валерия', 'Валерием', 'Валерии']
    },
    'Кирилл': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Кирюша', 'Кирик', 'Киря'],
        'transliterations': ['Kirill', 'Kiryusha'],
        'declensions': ['Кирилла', 'Кириллу', 'Кирилла', 'Кириллом', 'Кирилле']
    },
    'Леонид': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Леня', 'Леонидик', 'Льоня'],
        'transliterations': ['Leonid', 'Lenya'],
        'declensions': ['Леонида', 'Леониду', 'Леонида', 'Леонидом', 'Леониде']
    },
    'Георгий': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Гоша', 'Жора', 'Георгик'],
        'transliterations': ['Georgiy', 'Gosha', 'Zhora'],
        'declensions': ['Георгия', 'Георгию', 'Георгия', 'Георгием', 'Георгии']
    },
    'Владислав': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Влад', 'Владик', 'Слава'],
        'transliterations': ['Vladislav', 'Vlad', 'Slava'],
        'declensions': ['Владислава', 'Владиславу', 'Владислава', 'Владиславом', 'Владиславе']
    },
    'Денис': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Дениска', 'Денисик', 'Ден'],
        'transliterations': ['Denis', 'Deniska'],
        'declensions': ['Дениса', 'Денису', 'Дениса', 'Денисом', 'Денисе']
    },
    'Федор': {
        'gender': 'masc',
        'variants': ['Фёдор'],
        'diminutives': ['Федя', 'Федик', 'Федюша'],
        'transliterations': ['Fedor', 'Fyodor', 'Fedya'],
        'declensions': ['Федора', 'Федору', 'Федора', 'Федором', 'Федоре']
    },
    'Глеб': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Глебик', 'Глебушка'],
        'transliterations': ['Gleb', 'Glebik'],
        'declensions': ['Глеба', 'Глебу', 'Глеба', 'Глебом', 'Глебе']
    },
    'Семен': {
        'gender': 'masc',
        'variants': ['Семён'],
        'diminutives': ['Сеня', 'Семка', 'Семочка'],
        'transliterations': ['Semen', 'Semyon', 'Senya'],
        'declensions': ['Семена', 'Семену', 'Семена', 'Семеном', 'Семене']
    },
    'Тимофей': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Тима', 'Тимоша', 'Тимофейка'],
        'transliterations': ['Timofey', 'Tima', 'Timosha'],
        'declensions': ['Тимофея', 'Тимофею', 'Тимофея', 'Тимофеем', 'Тимофее']
    },
    'Руслан': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Русик', 'Русланчик'],
        'transliterations': ['Ruslan', 'Rusik'],
        'declensions': ['Руслана', 'Руслану', 'Руслана', 'Русланом', 'Руслане']
    },
    'Данил': {
        'gender': 'masc',
        'variants': ['Данила'],
        'diminutives': ['Данилка', 'Данька', 'Данечка'],
        'transliterations': ['Danil', 'Danila', 'Danka'],
        'declensions': ['Данила', 'Данилу', 'Данила', 'Данилом', 'Даниле']
    },
    'Егор': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Егорка', 'Егорушка'],
        'transliterations': ['Egor', 'Yegor'],
        'declensions': ['Егора', 'Егору', 'Егора', 'Егором', 'Егоре']
    },
    'Матвей': {
        'gender': 'masc',
        'variants': [],
        'diminutives': ['Мотя', 'Матюша', 'Матвейка'],
        'transliterations': ['Matvey', 'Motya', 'Matyusha'],
        'declensions': ['Матвея', 'Матвею', 'Матвея', 'Матвеем', 'Матвее']
    },
    'Марина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Маринка', 'Мариша', 'Марочка'],
        'transliterations': ['Marina', 'Marinka', 'Marisha'],
        'declensions': ['Марины', 'Марине', 'Марину', 'Мариной', 'Марине']
    },
    'Оксана': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Ксюша', 'Оксанка', 'Ксеня'],
        'transliterations': ['Oksana', 'Ksyusha', 'Ksenya'],
        'declensions': ['Оксаны', 'Оксане', 'Оксану', 'Оксаной', 'Оксане']
    },
    'Лидия': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Лида', 'Лидочка', 'Лидуся'],
        'transliterations': ['Lidiya', 'Lida', 'Lidochka'],
        'declensions': ['Лидии', 'Лидии', 'Лидию', 'Лидией', 'Лидии']
    },
    'Зоя': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Зоечка', 'Зоюшка', 'Зойка'],
        'transliterations': ['Zoya', 'Zoechka', 'Zoyka'],
        'declensions': ['Зои', 'Зое', 'Зою', 'Зоей', 'Зое']
    },
    'Галина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Галя', 'Галочка', 'Галинка'],
        'transliterations': ['Galina', 'Galya', 'Galochka'],
        'declensions': ['Галины', 'Галине', 'Галину', 'Галиной', 'Галине']
    },
    'Кристина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Кристи', 'Кристинка', 'Тина'],
        'transliterations': ['Kristina', 'Kristi', 'Tina'],
        'declensions': ['Кристины', 'Кристине', 'Кристину', 'Кристиной', 'Кристине']
    },
    'Диана': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Дианка', 'Ди', 'Дианочка'],
        'transliterations': ['Diana', 'Dianka', 'Di'],
        'declensions': ['Дианы', 'Диане', 'Диану', 'Дианой', 'Диане']
    },
    'Карина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Каринка', 'Кара', 'Карочка'],
        'transliterations': ['Karina', 'Karinka', 'Kara'],
        'declensions': ['Карины', 'Карине', 'Карину', 'Кариной', 'Карине']
    },
    'Алина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Алинка', 'Аля', 'Алиночка'],
        'transliterations': ['Alina', 'Alinka', 'Alya'],
        'declensions': ['Алины', 'Алине', 'Алину', 'Алиной', 'Алине']
    },
    'Валерия': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Лера', 'Валерочка', 'Валя'],
        'transliterations': ['Valeriya', 'Lera', 'Valya'],
        'declensions': ['Валерии', 'Валерии', 'Валерию', 'Валерией', 'Валерии']
    },
    'Регина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Регинка', 'Ригина', 'Рина'],
        'transliterations': ['Regina', 'Reginka', 'Rina'],
        'declensions': ['Регины', 'Регине', 'Регину', 'Региной', 'Регине']
    },
    'Маргарита': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Рита', 'Маргаритка', 'Марго'],
        'transliterations': ['Margarita', 'Rita', 'Margo'],
        'declensions': ['Маргариты', 'Маргарите', 'Маргариту', 'Маргаритой', 'Маргарите']
    },
    'Лариса': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Лара', 'Ларочка', 'Лариска'],
        'transliterations': ['Larisa', 'Lara', 'Larochka'],
        'declensions': ['Ларисы', 'Ларисе', 'Ларису', 'Ларисой', 'Ларисе']
    },
    'Тамара': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Тома', 'Томочка', 'Тамарочка'],
        'transliterations': ['Tamara', 'Toma', 'Tomochka'],
        'declensions': ['Тамары', 'Тамаре', 'Тамару', 'Тамарой', 'Тамаре']
    },
    'Римма': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Риммочка', 'Римка'],
        'transliterations': ['Rimma', 'Rimmochka'],
        'declensions': ['Риммы', 'Римме', 'Римму', 'Риммой', 'Римме']
    },
    'Инна': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Инночка', 'Иннуся'],
        'transliterations': ['Inna', 'Innochka'],
        'declensions': ['Инны', 'Инне', 'Инну', 'Инной', 'Инне']
    },
    'Раиса': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Рая', 'Раечка', 'Раиска'],
        'transliterations': ['Raisa', 'Raya', 'Rayechka'],
        'declensions': ['Раисы', 'Раисе', 'Раису', 'Раисой', 'Раисе']
    },
    'Жанна': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Жанночка', 'Жанка'],
        'transliterations': ['Zhanna', 'Zhannochka'],
        'declensions': ['Жанны', 'Жанне', 'Жанну', 'Жанной', 'Жанне']
    },
    'Эмилия': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Эмма', 'Эмилька', 'Миля'],
        'transliterations': ['Emiliya', 'Emma', 'Milya'],
        'declensions': ['Эмилии', 'Эмилии', 'Эмилию', 'Эмилией', 'Эмилии']
    },
    'Стефания': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Стефа', 'Стеша', 'Фаня'],
        'transliterations': ['Stefaniya', 'Stefa', 'Stesha'],
        'declensions': ['Стефании', 'Стефании', 'Стефанию', 'Стефанией', 'Стефании']
    },
    'Милана': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Миланка', 'Мила', 'Лана'],
        'transliterations': ['Milana', 'Milanka', 'Mila'],
        'declensions': ['Миланы', 'Милане', 'Милану', 'Миланой', 'Милане']
    },
    'Камилла': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Камила', 'Кама', 'Милка'],
        'transliterations': ['Kamilla', 'Kamila', 'Kama'],
        'declensions': ['Камиллы', 'Камилле', 'Камиллу', 'Камиллой', 'Камилле']
    },
    'Арина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Аринка', 'Ариша', 'Аря'],
        'transliterations': ['Arina', 'Arinka', 'Arisha'],
        'declensions': ['Арины', 'Арине', 'Арину', 'Ариной', 'Арине']
    },
    'Злата': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Златка', 'Златочка'],
        'transliterations': ['Zlata', 'Zlatka'],
        'declensions': ['Златы', 'Злате', 'Злату', 'Златой', 'Злате']
    },
    'Вероника': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Ника', 'Вера', 'Веронька'],
        'transliterations': ['Veronika', 'Nika', 'Vera'],
        'declensions': ['Вероники', 'Веронике', 'Веронику', 'Вероникой', 'Веронике']
    },
    'Лилия': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Лиля', 'Лилька', 'Лилечка'],
        'transliterations': ['Liliya', 'Lilya', 'Lilka'],
        'declensions': ['Лилии', 'Лилии', 'Лилию', 'Лилией', 'Лилии']
    },
    'Яна': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Янка', 'Яночка', 'Януся'],
        'transliterations': ['Yana', 'Yanka', 'Yanochka'],
        'declensions': ['Яны', 'Яне', 'Яну', 'Яной', 'Яне']
    },
    'Ева': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Евочка', 'Евуся'],
        'transliterations': ['Eva', 'Evochka'],
        'declensions': ['Евы', 'Еве', 'Еву', 'Евой', 'Еве']
    },
    'Василиса': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Вася', 'Василисочка', 'Лиса'],
        'transliterations': ['Vasilisa', 'Vasya', 'Lisa'],
        'declensions': ['Василисы', 'Василисе', 'Василису', 'Василисой', 'Василисе']
    },
    
    # Additional male names
    'Дмитрий': {
        'gender': 'masc',
        'variants': ['Дмитрій'],
        'diminutives': ['Дима', 'Димы', 'Диме', 'Диму', 'Димой', 'Диме', 'Димочка', 'Димка'],
        'transliterations': ['Dmitry', 'Dmitriy', 'Dima'],
        'declensions': ['Дмитрия', 'Дмитрию', 'Дмитрия', 'Дмитрием', 'Дмитрии']
    },
    'Николай': {
        'gender': 'masc',
        'variants': ['Микола'],
        'diminutives': ['Коля', 'Коленька', 'Колька'],
        'transliterations': ['Nikolay', 'Nikolai', 'Kolya'],
        'declensions': ['Николая', 'Николаю', 'Николая', 'Николаем', 'Николае']
    },
    'Сергей': {
        'gender': 'masc',
        'variants': ['Сергій'],
        'diminutives': ['Серёжа', 'Серёжка', 'Серж'],
        'transliterations': ['Sergey', 'Serhii', 'Seryozha'],
        'declensions': ['Сергея', 'Сергею', 'Сергея', 'Сергеем', 'Сергее']
    },
    'Артём': {
        'gender': 'masc',
        'variants': ['Артем'],
        'diminutives': ['Тёма', 'Тёмка', 'Артёмка'],
        'transliterations': ['Artyom', 'Artem', 'Tyoma'],
        'declensions': ['Артёма', 'Артёму', 'Артёма', 'Артёмом', 'Артёме']
    },
    
    # Additional female names
    'Ангелина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Ангела', 'Геля', 'Лина'],
        'transliterations': ['Angelina', 'Angela', 'Gelya'],
        'declensions': ['Ангелины', 'Ангелине', 'Ангелину', 'Ангелиной', 'Ангелине']
    },
    'Полина': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Поля', 'Поленька', 'Полинка'],
        'transliterations': ['Polina', 'Polya', 'Polinka'],
        'declensions': ['Полины', 'Полине', 'Полину', 'Полиной', 'Полине']
    },
    'Ксения': {
        'gender': 'femn',
        'variants': ['Ксенія'],
        'diminutives': ['Ксюша', 'Ксюшенька', 'Ксю'],
        'transliterations': ['Kseniya', 'Ksenia', 'Ksyusha'],
        'declensions': ['Ксении', 'Ксении', 'Ксению', 'Ксенией', 'Ксении']
    },
    'Алиса': {
        'gender': 'femn',
        'variants': [],
        'diminutives': ['Алисочка', 'Алиска', 'Алис'],
        'transliterations': ['Alisa', 'Alice', 'Aliska'],
        'declensions': ['Алисы', 'Алисе', 'Алису', 'Алисой', 'Алисе']
    },
    'София': {
        'gender': 'femn',
        'variants': ['Софія'],
        'diminutives': ['Соня', 'Сонечка', 'Софійка'],
        'transliterations': ['Sofiya', 'Sofia', 'Sonya'],
        'declensions': ['Софии', 'Софии', 'Софию', 'Софией', 'Софии']
    },
    
    # Additional modern Russian names
    'Максим': {
        'gender': 'masc',
        'variants': ['Максим', 'Макс', 'Максим'],
        'diminutives': ['Максим', 'Макс', 'Максим'],
        'transliterations': ['Maksim', 'Max', 'Maksim'],
        'declensions': ['Максима', 'Максиму', 'Максима', 'Максимом', 'Максиме']
    },
    'Анна': {
        'gender': 'femn',
        'variants': ['Анна', 'Анна', 'Анна'],
        'diminutives': ['Анна', 'Анна', 'Анна'],
        'transliterations': ['Anna', 'Anna', 'Anna'],
        'declensions': ['Анны', 'Анне', 'Анну', 'Анной', 'Анне']
    },
    'Денис': {
        'gender': 'masc',
        'variants': ['Денис', 'Ден', 'Денис'],
        'diminutives': ['Денис', 'Ден', 'Денис'],
        'transliterations': ['Denis', 'Den', 'Denis'],
        'declensions': ['Дениса', 'Денису', 'Дениса', 'Денисом', 'Денисе']
    },
    'Мария': {
        'gender': 'femn',
        'variants': ['Мария', 'Мария', 'Мария'],
        'diminutives': ['Мария', 'Мария', 'Мария'],
        'transliterations': ['Mariya', 'Mariya', 'Mariya'],
        'declensions': ['Марии', 'Марии', 'Марию', 'Марией', 'Марии']
    },
    'Илья': {
        'gender': 'masc',
        'variants': ['Илья', 'Илья', 'Илья'],
        'diminutives': ['Илья', 'Илья', 'Илья'],
        'transliterations': ['Ilya', 'Ilya', 'Ilya'],
        'declensions': ['Ильи', 'Илье', 'Илью', 'Ильёй', 'Илье']
    },
    'Валерия': {
        'gender': 'femn',
        'variants': ['Валерия', 'Валерия', 'Валерия'],
        'diminutives': ['Валерия', 'Валерия', 'Валерия'],
        'transliterations': ['Valeriya', 'Valeriya', 'Valeriya'],
        'declensions': ['Валерии', 'Валерии', 'Валерию', 'Валерией', 'Валерии']
    },
    'Кирилл': {
        'gender': 'masc',
        'variants': ['Кирилл', 'Кирилл', 'Кирилл'],
        'diminutives': ['Кирилл', 'Кирилл', 'Кирилл'],
        'transliterations': ['Kirill', 'Kirill', 'Kirill'],
        'declensions': ['Кирилла', 'Кириллу', 'Кирилла', 'Кириллом', 'Кирилле']
    },
    'Алина': {
        'gender': 'femn',
        'variants': ['Алина', 'Алина', 'Алина'],
        'diminutives': ['Алина', 'Алина', 'Алина'],
        'transliterations': ['Alina', 'Alina', 'Alina'],
        'declensions': ['Алины', 'Алине', 'Алину', 'Алиной', 'Алине']
    },
    
    # Додаткові сучасні російські імена
    'Арсен': {
        'gender': 'masc',
        'variants': ['Арсен', 'Арсен', 'Арсен'],
        'diminutives': ['Арсен', 'Арсен', 'Арсен'],
        'transliterations': ['Arsen', 'Arsen', 'Arsen'],
        'declensions': ['Арсена', 'Арсену', 'Арсена', 'Арсеном', 'Арсене']
    },
    'Ангеліна': {
        'gender': 'femn',
        'variants': ['Ангеліна', 'Ангеліна', 'Ангеліна'],
        'diminutives': ['Ангеліна', 'Ангеліна', 'Ангеліна'],
        'transliterations': ['Angelina', 'Angelina', 'Angelina'],
        'declensions': ['Ангеліни', 'Ангеліні', 'Ангеліну', 'Ангеліною', 'Ангеліні']
    },
    'Богдан': {
        'gender': 'masc',
        'variants': ['Богдан', 'Богдан', 'Богдан'],
        'diminutives': ['Богдан', 'Богдан', 'Богдан'],
        'transliterations': ['Bohdan', 'Bogdan', 'Bohdan'],
        'declensions': ['Богдана', 'Богдану', 'Богдана', 'Богданом', 'Богдані']
    },
    'Валерія': {
        'gender': 'femn',
        'variants': ['Валерія', 'Валерія', 'Валерія'],
        'diminutives': ['Валерія', 'Валерія', 'Валерія'],
        'transliterations': ['Valeriya', 'Valeriya', 'Valeriya'],
        'declensions': ['Валерії', 'Валерії', 'Валерію', 'Валерією', 'Валерії']
    },
    'Гліб': {
        'gender': 'masc',
        'variants': ['Гліб', 'Гліб', 'Гліб'],
        'diminutives': ['Гліб', 'Гліб', 'Гліб'],
        'transliterations': ['Glib', 'Gleb', 'Glib'],
        'declensions': ['Гліба', 'Глібу', 'Гліба', 'Глібом', 'Глібі']
    },
    'Діана': {
        'gender': 'femn',
        'variants': ['Діана', 'Діана', 'Діана'],
        'diminutives': ['Діана', 'Діана', 'Діана'],
        'transliterations': ['Diana', 'Diana', 'Diana'],
        'declensions': ['Діани', 'Діані', 'Діану', 'Діаною', 'Діані']
    },
    'Єгор': {
        'gender': 'masc',
        'variants': ['Єгор', 'Єгор', 'Єгор'],
        'diminutives': ['Єгор', 'Єгор', 'Єгор'],
        'transliterations': ['Yegor', 'Egor', 'Yegor'],
        'declensions': ['Єгора', 'Єгору', 'Єгора', 'Єгором', 'Єгорі']
    },
    'Єлизавета': {
        'gender': 'femn',
        'variants': ['Єлизавета', 'Єлизавета', 'Єлизавета'],
        'diminutives': ['Єлизавета', 'Єлизавета', 'Єлизавета'],
        'transliterations': ['Yelizaveta', 'Elizaveta', 'Yelizaveta'],
        'declensions': ['Єлизавети', 'Єлизаветі', 'Єлизавету', 'Єлизаветою', 'Єлизаветі']
    },
    'Захар': {
        'gender': 'masc',
        'variants': ['Захар', 'Захар', 'Захар'],
        'diminutives': ['Захар', 'Захар', 'Захар'],
        'transliterations': ['Zakhar', 'Zakhar', 'Zakhar'],
        'declensions': ['Захара', 'Захару', 'Захара', 'Захаром', 'Захарі']
    },
    'Ірина': {
        'gender': 'femn',
        'variants': ['Ірина', 'Ірина', 'Ірина'],
        'diminutives': ['Ірина', 'Ірина', 'Ірина'],
        'transliterations': ['Irina', 'Irina', 'Irina'],
        'declensions': ['Ірини', 'Ірині', 'Ірину', 'Іриною', 'Ірині']
    }
}



ALL_RUSSIAN_NAMES = list(RUSSIAN_NAMES.keys())