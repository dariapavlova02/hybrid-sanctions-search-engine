"""
Тест для улучшенной логики связывания ID с персонами через proximity matching.

Проверяет, что ID правильно привязываются к ближайшим персонам в тексте,
а не ко всем персонам одинаково.
"""

import pytest
from unittest.mock import Mock, patch

from ai_service.layers.signals.signals_service import SignalsService, PersonSignal


class TestIDPersonProximityMatching:
    """Тесты для proximity matching между ID и персонами"""

    @pytest.fixture
    def signals_service(self):
        """Создание экземпляра SignalsService для тестов"""
        return SignalsService()

    @pytest.fixture
    def mock_person_ids_with_positions(self):
        """Мок данных ID с позициями"""
        return [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (25, 40),  # Позиция в тексте
            },
            {
                "type": "inn_ru",
                "value": "9876543210",
                "raw": "ИНН 9876543210",
                "confidence": 0.8,
                "valid": True,
                "position": (80, 95),  # Позиция в тексте
            }
        ]

    def test_proximity_matching_single_person_single_id(self, signals_service):
        """Тест: один ID рядом с одной персоной"""

        # Создаем персону
        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        persons = [person]

        # Создаем ID рядом с персоной
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (25, 40),  # ID рядом с именем
            }
        ]

        # Текст где персона находится в позиции 10-24, ID в позиции 25-40
        text = "Громадянин Іван Петренко ІНН 1234567890"

        # Вызываем proximity matching
        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # Проверяем, что ID привязан к персоне
        assert len(person.ids) == 1
        assert person.ids[0]["type"] == "inn_ua"
        assert person.ids[0]["value"] == "1234567890"
        assert "valid_inn_ua" in person.evidence

    def test_proximity_matching_multiple_persons_multiple_ids(self, signals_service):
        """Тест: несколько персон и ID - каждый ID к ближайшей персоне"""

        # Создаем двух персон
        person1 = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        person2 = PersonSignal(core=["Марія", "Сидоренко"], full_name="Марія Сидоренко")
        persons = [person1, person2]

        # Создаем два ID в разных частях текста
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1111111111",
                "raw": "ІНН 1111111111",
                "confidence": 0.9,
                "valid": True,
                "position": (25, 40),  # Рядом с первой персоной
            },
            {
                "type": "inn_ua",
                "value": "2222222222",
                "raw": "ІНН 2222222222",
                "confidence": 0.8,
                "valid": True,
                "position": (80, 95),  # Рядом со второй персоной
            }
        ]

        # Текст: первая персона в начале, вторая в конце
        text = "Громадянин Іван Петренко ІНН 1111111111 та Марія Сидоренко ІНН 2222222222"

        # Вызываем proximity matching
        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # Проверяем правильное распределение ID
        assert len(person1.ids) == 1
        assert person1.ids[0]["value"] == "1111111111"

        assert len(person2.ids) == 1
        assert person2.ids[0]["value"] == "2222222222"

    def test_proximity_matching_distance_limits(self, signals_service):
        """Тест: ID слишком далеко от персоны не связывается"""

        # Персона в начале текста
        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        persons = [person]

        # ID очень далеко от персоны (>500 символов)
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (600, 615),  # Очень далеко от персоны
            }
        ]

        # Создаем длинный текст где ID очень далеко от имени
        text = "Іван Петренко" + " " * 600 + "ІНН 1234567890"

        # Вызываем proximity matching
        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # ID не должен быть привязан из-за большого расстояния
        assert len(person.ids) == 0

    def test_fallback_for_ids_without_position(self, signals_service):
        """Тест: fallback логика для ID без позиции"""

        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        persons = [person]

        # ID без позиции (старый формат)
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                # Нет поля "position"
            }
        ]

        text = "Іван Петренко ІНН 1234567890"

        # Мокаем метод _assign_id_to_all_persons
        with patch.object(signals_service, '_assign_id_to_all_persons') as mock_assign_all:
            signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

            # Должен быть вызван fallback метод
            mock_assign_all.assert_called_once_with(persons, person_ids[0])

    def test_fallback_logic_single_person_single_id(self, signals_service):
        """Тест: fallback логика для одной персоны и одного неприсвоенного ID"""

        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        persons = [person]

        # ID далеко от персоны, но это единственные сущности
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (400, 415),  # Слишком далеко для proximity
            }
        ]

        text = "Іван Петренко" + " " * 400 + "ІНН 1234567890"

        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # ID должен быть присвоен по fallback логике
        assert len(person.ids) == 1
        assert person.ids[0]["value"] == "1234567890"

    def test_no_duplicate_id_assignment(self, signals_service):
        """Тест: ID не назначается дважды"""

        person1 = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")
        person2 = PersonSignal(core=["Марія", "Сидоренко"], full_name="Марія Сидоренко")
        persons = [person1, person2]

        # Один ID между двумя персонами
        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (30, 45),  # Между персонами
            }
        ]

        text = "Іван Петренко та ІНН 1234567890 Марія Сидоренко"

        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # ID должен быть привязан только к одной персоне (ближайшей)
        total_ids = len(person1.ids) + len(person2.ids)
        assert total_ids == 1

        # Проверяем, что ID привязан к ближайшей персоне
        if person1.ids:
            assert person1.ids[0]["value"] == "1234567890"
            assert len(person2.ids) == 0
        else:
            assert person2.ids[0]["value"] == "1234567890"
            assert len(person1.ids) == 0

    def test_assign_id_to_person_method(self, signals_service):
        """Тест вспомогательного метода _assign_id_to_person"""

        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")

        id_info = {
            "type": "inn_ua",
            "value": "1234567890",
            "raw": "ІНН 1234567890",
            "confidence": 0.9,
            "valid": True,
        }

        signals_service._assign_id_to_person(person, id_info)

        # Проверяем корректное присвоение
        assert len(person.ids) == 1
        assert person.ids[0]["type"] == "inn_ua"
        assert person.ids[0]["value"] == "1234567890"
        assert person.ids[0]["confidence"] == 0.9
        assert person.ids[0]["valid"] is True
        assert "valid_inn_ua" in person.evidence

    def test_assign_invalid_id_evidence(self, signals_service):
        """Тест evidence для невалидного ID"""

        person = PersonSignal(core=["Іван", "Петренко"], full_name="Іван Петренко")

        id_info = {
            "type": "inn_ua",
            "value": "invalid_id",
            "raw": "ІНН invalid_id",
            "confidence": 0.5,
            "valid": False,  # Невалидный ID
        }

        signals_service._assign_id_to_person(person, id_info)

        # Проверяем evidence для невалидного ID
        assert "invalid_inn_ua" in person.evidence
        assert "valid_inn_ua" not in person.evidence

    def test_persons_without_names_in_text(self, signals_service):
        """Тест: персоны, имена которых не найдены в тексте"""

        # Персона с именем, которого нет в тексте
        person = PersonSignal(core=["Невідомий", "Персон"], full_name="Невідомий Персон")
        persons = [person]

        person_ids = [
            {
                "type": "inn_ua",
                "value": "1234567890",
                "raw": "ІНН 1234567890",
                "confidence": 0.9,
                "valid": True,
                "position": (10, 25),
            }
        ]

        # Текст не содержит имени персоны
        text = "Якийсь текст з ІНН 1234567890"

        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # ID должен быть присвоен по fallback логике
        assert len(person.ids) == 1
        assert person.ids[0]["value"] == "1234567890"

    def test_distance_calculation_accuracy(self, signals_service):
        """Тест точности вычисления расстояний"""

        # Персона ближе к первому ID
        person = PersonSignal(core=["Тест"], full_name="Тест")
        persons = [person]

        person_ids = [
            {
                "type": "inn_ua",
                "value": "1111111111",
                "raw": "ІНН 1111111111",
                "confidence": 0.9,
                "valid": True,
                "position": (10, 25),  # Ближе к персоне (расстояние ~5)
            },
            {
                "type": "inn_ua",
                "value": "2222222222",
                "raw": "ІНН 2222222222",
                "confidence": 0.9,
                "valid": True,
                "position": (50, 65),  # Дальше от персоны (расстояние ~45)
            }
        ]

        # Персона в позиции 0-4, первый ID в 10-25, второй в 50-65
        text = "Тест та ІНН 1111111111 та інший текст ІНН 2222222222"

        signals_service._link_ids_to_persons_by_proximity(persons, person_ids, text)

        # Должен быть привязан ближайший ID
        assert len(person.ids) == 1
        assert person.ids[0]["value"] == "1111111111"  # Ближайший ID


class TestIDPersonProximityIntegration:
    """Интеграционные тесты proximity matching в контексте полного сервиса"""

    def test_full_signals_extraction_with_proximity(self):
        """Тест полного извлечения сигналов с proximity matching"""

        signals_service = SignalsService()

        # Реальный текст с несколькими персонами и ID
        text = "Договір з Іван Петренко ІНН 1234567890 та Марія Коваленко ІНН 9876543210"

        # Мокаем нормализацию персон
        normalization_result = {
            "persons_core": [["Іван", "Петренко"], ["Марія", "Коваленко"]]
        }

        # Мокаем извлечение ID с позициями
        with patch.object(signals_service.identifier_extractor, 'extract_person_ids') as mock_extract:
            mock_extract.return_value = [
                {
                    "type": "inn_ua",
                    "value": "1234567890",
                    "raw": "ІНН 1234567890",
                    "confidence": 0.9,
                    "valid": True,
                    "position": (22, 37),  # Позиция рядом с первой персоной
                },
                {
                    "type": "inn_ua",
                    "value": "9876543210",
                    "raw": "ІНН 9876543210",
                    "confidence": 0.9,
                    "valid": True,
                    "position": (58, 73),  # Позиция рядом со второй персоной
                }
            ]

            result = signals_service.extract(text, normalization_result)

            # Проверяем, что ID правильно распределены
            assert len(result["persons"]) == 2

            # Находим персон по именам
            ivan = next(p for p in result["persons"] if "Іван" in p["core"])
            maria = next(p for p in result["persons"] if "Марія" in p["core"])

            # Проверяем правильное присвоение ID
            assert len(ivan["ids"]) == 1
            assert ivan["ids"][0]["value"] == "1234567890"

            assert len(maria["ids"]) == 1
            assert maria["ids"][0]["value"] == "9876543210"