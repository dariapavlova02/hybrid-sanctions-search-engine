"""
Signals Service - структурирование и обогащение сущностей.

Отвечает за:
- Выделение юридических форм и полных названий организаций
- Парсинг идентификаторов (ИНН/ЄДРПОУ/ОГРН/VAT)
- Извлечение дат рождения
- Скоринг сущностей и формирование evidence
- Реконструкцию полных данных персон и организаций

НЕ отвечает за:
- Нормализацию текста (это делает NormalizationService)
- Решение "пропускать/не пропускать" (это делает SmartFilter)
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ...utils.logging_config import get_logger
from .extractors import PersonExtractor, OrganizationExtractor, IdentifierExtractor, BirthdateExtractor

# Confidence scoring constants
class ConfidenceScoring:
    """Constants for confidence scoring algorithm."""
    
    BASE_CONFIDENCE = 0.5
    
    # Person scoring bonuses
    BIRTHDATE_BONUS = 0.15
    VALID_ID_BONUS = 0.2
    INVALID_ID_BONUS = 0.1
    NAME_PATTERN_BONUS = 0.1
    
    # Organization scoring bonuses
    LEGAL_FORM_BONUS = 0.3
    QUOTED_CORE_BONUS = 0.2
    NORM_MATCH_BONUS = 0.2
    ADJACENT_NAME_BONUS = 0.1
    ORG_CORE_BONUS = 0.1
    
    # Multi-evidence bonuses
    PERSON_MAX_MULTI_BONUS = 0.2
    ORG_MAX_MULTI_BONUS = 0.25
    MULTI_EVIDENCE_INCREMENT = 0.05
    
    MAX_CONFIDENCE = 1.0


@dataclass
class PersonSignal:
    """Сигнал о персоне"""

    core: List[str]  # Токены имени из normalization
    full_name: str
    dob: Optional[str] = None  # ISO YYYY-MM-DD
    dob_raw: Optional[str] = None
    ids: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class OrganizationSignal:
    """Сигнал об организации"""

    core: str  # Ядро названия из normalization
    legal_form: Optional[str] = None
    full: Optional[str] = None  # Реконструированное полное название
    ids: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class ExtraSignal:
    """Дополнительные сигналы"""

    type: str
    value: str
    raw: str
    confidence: float = 0.0


class SignalsService:
    """
    Сервис сигналов для структурирования сущностей.

    Принимает исходный текст + результат нормализации,
    возвращает структурированные персоны и организации
    с метаданными (юр. формы, ID, даты рождения).
    """

    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize specialized extractors
        self.person_extractor = PersonExtractor()
        self.organization_extractor = OrganizationExtractor()
        self.identifier_extractor = IdentifierExtractor()
        self.birthdate_extractor = BirthdateExtractor()
        
        self.logger.info("SignalsService initialized with extractors")

    def extract(
        self,
        text: str,
        normalization_result: Optional[Dict[str, Any]] = None,
        language: str = "uk",
    ) -> Dict[str, Any]:
        """
        Извлечение и структурирование сигналов из текста.

        Args:
            text: Исходный текст
            normalization_result: Результат работы NormalizationService (опциональный)
            language: Язык текста

        Returns:
            Dict с ключами:
            - persons: List[PersonSignal]
            - organizations: List[OrganizationSignal]
            - extras: Dict с дополнительными сигналы
        """
        if not text or not text.strip():
            return self._empty_result()

        try:
            # 1. Извлекаем базовые токены сущностей
            persons_core, organizations_core = self._get_entity_cores(
                text, normalization_result, language
            )

            # 2. Создаем персоны из токенов
            persons = self._create_person_signals(persons_core)

            # 3. Создаем организации из токенов
            organizations = self._create_organization_signals(text, organizations_core)

            # 4. Обогащаем сущности идентификаторами
            self._enrich_with_identifiers(text, persons, organizations)

            # 5. Обогащаем персоны датами рождения
            self._enrich_with_birthdates(text, persons)

            # 6. Финальный скоринг сущностей
            self._score_entities(persons, organizations)

            # 7. Формируем результат
            result = self._build_result(persons, organizations)

            self.logger.debug(
                f"Extracted {len(persons)} persons, {len(organizations)} organizations"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error extracting signals: {e}")
            return self._empty_result()

    def _get_entity_cores(
        self,
        text: str,
        normalization_result: Optional[Dict[str, Any]],
        language: str,
    ) -> tuple[List[List[str]], List[str]]:
        """Извлекает базовые токены персон и организаций."""
        # Извлекаем персоны
        if normalization_result and "persons_core" in normalization_result:
            persons_core = normalization_result["persons_core"]
        else:
            persons_core = self.person_extractor.extract(text, language)

        # Извлекаем организации
        if normalization_result and "organizations_core" in normalization_result:
            organizations_core = normalization_result["organizations_core"]
        else:
            organizations_core = self.organization_extractor.extract(text, language)

        return persons_core, organizations_core

    def _create_person_signals(self, persons_core: List[List[str]]) -> List[PersonSignal]:
        """Создает PersonSignal объекты из токенов."""
        persons = []
        for person_tokens in persons_core:
            person = PersonSignal(
                core=person_tokens,
                full_name=" ".join(person_tokens),
                confidence=ConfidenceScoring.BASE_CONFIDENCE,
                evidence=["name_pattern"],
            )
            persons.append(person)
        return persons

    def _create_organization_signals(
        self, text: str, organizations_core: List[str]
    ) -> List[OrganizationSignal]:
        """Создает OrganizationSignal объекты из токенов и юридических форм."""
        # Извлекаем юридические формы и создаем организации
        legal_forms_found = self._extract_legal_forms(text, organizations_core)

        # Объединяем организации из нормализации с найденными юридическими формами
        org_dict = {}

        # Сначала добавляем базовые организации из нормализации
        for org_core in organizations_core:
            org_dict[org_core.upper()] = OrganizationSignal(
                core=org_core.upper(), 
                confidence=ConfidenceScoring.BASE_CONFIDENCE, 
                evidence=["org_core"]
            )

        # Обновляем информацией о юридических формах
        for legal_org in legal_forms_found:
            core_key = legal_org["core"]
            if core_key in org_dict:
                # Обновляем существующую организацию
                org_dict[core_key].legal_form = legal_org["legal_form"]
                org_dict[core_key].full = legal_org["full"]
                org_dict[core_key].evidence.extend(legal_org["evidence"])
            else:
                # Добавляем новую организацию
                org_dict[core_key] = OrganizationSignal(
                    core=core_key,
                    legal_form=legal_org["legal_form"],
                    full=legal_org["full"],
                    confidence=ConfidenceScoring.BASE_CONFIDENCE,
                    evidence=legal_org["evidence"],
                )

        return list(org_dict.values())

    def _enrich_with_identifiers(
        self, text: str, persons: List[PersonSignal], organizations: List[OrganizationSignal]
    ):
        """Обогащает сущности найденными идентификаторами."""
        org_ids = self.identifier_extractor.extract_organization_ids(text)
        person_ids = self.identifier_extractor.extract_person_ids(text)

        self._enrich_organizations_with_ids(organizations, org_ids)
        self._enrich_persons_with_ids(persons, person_ids)

    def _enrich_with_birthdates(self, text: str, persons: List[PersonSignal]):
        """Обогащает персоны найденными датами рождения."""
        birthdates = self.birthdate_extractor.extract(text)
        self._enrich_persons_with_birthdates(persons, birthdates, text)

    def _build_result(
        self, persons: List[PersonSignal], organizations: List[OrganizationSignal]
    ) -> Dict[str, Any]:
        """Формирует финальный результат."""
        return {
            "persons": [self._person_to_dict(p) for p in persons],
            "organizations": [self._org_to_dict(o) for o in organizations],
            "extras": {"dates": [], "amounts": []},
        }

    def _extract_legal_forms(
        self, text: str, organizations_core: List[str]
    ) -> List[Dict]:
        """
        Детектор юридических форм и реконструкция полных названий.

        Args:
            text: Исходный текст
            organizations_core: Ядра организаций из нормализации

        Returns:
            List[Dict]: Список найденных организаций с legal_form и full
        """
        from ...data.patterns.legal_forms import (
            LEGAL_FORM_REGEX,
            ORGANIZATION_NAME_REGEX,
            QUOTED_CORE_REGEX,
            normalize_legal_form,
        )

        organizations = []

        # Ищем юридические формы в тексте
        for legal_match in LEGAL_FORM_REGEX.finditer(text):
            legal_form_raw = legal_match.group("legal_form")
            legal_form_normalized = normalize_legal_form(legal_form_raw)

            # Позиция юридической формы
            form_start = legal_match.start()
            form_end = legal_match.end()

            # Ищем quoted core рядом с формой (±100 символов)
            search_start = max(0, form_start - 100)
            search_end = min(len(text), form_end + 100)
            search_region = text[search_start:search_end]

            core = None
            full = None
            evidence = ["legal_form_hit"]

            # Сначала пытаемся найти quoted название
            quoted_matches = list(QUOTED_CORE_REGEX.finditer(search_region))

            # Сортируем quoted matches по расстоянию до юридической формы
            def distance_to_legal_form(quoted_match):
                # Расстояние от quoted match до legal form в search_region
                quoted_start_in_search = quoted_match.start()
                quoted_end_in_search = quoted_match.end()

                # Позиция legal form в search_region
                legal_start_in_search = form_start - search_start
                legal_end_in_search = form_end - search_start

                # Расстояние между центрами
                quoted_center = (quoted_start_in_search + quoted_end_in_search) / 2
                legal_center = (legal_start_in_search + legal_end_in_search) / 2
                return abs(quoted_center - legal_center)

            quoted_matches.sort(key=distance_to_legal_form)

            for quoted_match in quoted_matches:
                quoted_core = quoted_match.group("quoted_core").strip()

                # Проверяем, есть ли это ядро в результатах нормализации
                if quoted_core.upper() in [org.upper() for org in organizations_core]:
                    core = quoted_core.upper()
                    # Используем нормализованное название для консистентности
                    normalized_core = next(
                        org
                        for org in organizations_core
                        if org.upper() == quoted_core.upper()
                    )
                    full = f'{legal_form_normalized} "{normalized_core}"'
                    evidence.append("quoted_core")
                    evidence.append("norm_match")
                    break
                elif len(quoted_core) >= 3:  # Минимум 3 символа для валидного названия
                    core = quoted_core.upper()
                    full = (
                        f'{legal_form_normalized} "{core}"'  # Используем uppercase core
                    )
                    evidence.append("quoted_core")
                    break

            # Если не нашли в кавычках, ищем рядом с формой
            if not core:
                # Ищем название слева от формы (более точно)
                left_region = text[max(0, form_start - 30) : form_start].strip()
                if left_region:
                    # Берем только последнее слово или два слова перед формой
                    words = left_region.split()
                    if words:
                        # Ищем только название, которое совпадает с нормализацией
                        for i in range(min(3, len(words)), 0, -1):
                            candidate = " ".join(words[-i:]).strip()
                            if (
                                len(candidate) >= 3
                                and any(c.isalpha() for c in candidate)
                                and len(candidate) <= 30
                            ):  # Разумная длина названия

                                # Приоритет - соответствие с нормализацией
                                if candidate.upper() in [
                                    org.upper() for org in organizations_core
                                ]:
                                    core = candidate.upper()
                                    # Используем нормализованное название
                                    normalized_core = next(
                                        org
                                        for org in organizations_core
                                        if org.upper() == candidate.upper()
                                    )
                                    full = f"{legal_form_normalized} {normalized_core}"
                                    evidence.extend(["adjacent_name", "norm_match"])
                                    break

                # Если не нашли слева, ищем справа от формы
                if not core:
                    right_region = text[
                        form_end : min(len(text), form_end + 30)
                    ].strip()
                    if right_region:
                        # Берем первые 1-3 слова после формы
                        words = right_region.split()
                        if words:
                            for i in range(1, min(4, len(words) + 1)):
                                candidate = " ".join(words[:i]).strip()
                                if (
                                    len(candidate) >= 3
                                    and any(c.isalpha() for c in candidate)
                                    and len(candidate) <= 30
                                ):

                                    # Приоритет - соответствие с нормализацией
                                    if candidate.upper() in [
                                        org.upper() for org in organizations_core
                                    ]:
                                        core = candidate.upper()
                                        # Используем нормализованное название
                                        normalized_core = next(
                                            org
                                            for org in organizations_core
                                            if org.upper() == candidate.upper()
                                        )
                                        full = (
                                            f"{legal_form_normalized} {normalized_core}"
                                        )
                                        evidence.extend(["adjacent_name", "norm_match"])
                                        break

            # Если нашли core, добавляем организацию
            if core:
                org_info = {
                    "core": core,
                    "legal_form": legal_form_normalized,
                    "full": full,
                    "evidence": evidence,
                    "legal_form_raw": legal_form_raw,
                }
                organizations.append(org_info)

        # Удаляем дубликаты по core
        seen_cores = set()
        unique_orgs = []
        for org in organizations:
            if org["core"] not in seen_cores:
                seen_cores.add(org["core"])
                unique_orgs.append(org)

        return unique_orgs

    def _extract_org_ids(self, text: str) -> List[Dict]:
        """Детектор организационных ID"""
        from ...data.patterns.identifiers import (
            get_compiled_patterns_cached,
            get_validation_function,
            normalize_identifier,
        )

        org_id_types = {
            "edrpou",
            "inn_ru",
            "ogrn",
            "ogrnip",
            "kpp",
            "vat_eu",
            "lei",
            "ein",
        }

        found_ids = []

        for pattern, compiled_regex in get_compiled_patterns_cached():
            if pattern.type not in org_id_types:
                continue

            for match in compiled_regex.finditer(text):
                raw_value = match.group(1)
                normalized_value = normalize_identifier(raw_value, pattern.type)

                # Дополнительная валидация если есть
                validator = get_validation_function(pattern.type)
                is_valid = True
                if validator:
                    is_valid = validator(normalized_value)

                confidence = 0.9 if is_valid else 0.6

                id_info = {
                    "type": pattern.type,
                    "value": normalized_value,
                    "raw": match.group(0),  # Полное совпадение
                    "name": pattern.name,
                    "confidence": confidence,
                    "position": match.span(),
                    "valid": is_valid,
                }
                found_ids.append(id_info)

        # Удаляем дубликаты по value
        seen_values = set()
        unique_ids = []
        for id_info in found_ids:
            if id_info["value"] not in seen_values:
                seen_values.add(id_info["value"])
                unique_ids.append(id_info)

        return unique_ids

    def _extract_person_ids(self, text: str) -> List[Dict]:
        """Детектор личных ID"""
        from ...data.patterns.identifiers import (
            get_compiled_patterns_cached,
            get_validation_function,
            normalize_identifier,
        )

        person_id_types = {"inn_ua", "inn_ru", "snils", "ssn", "passport_ua"}

        found_ids = []

        for pattern, compiled_regex in get_compiled_patterns_cached():
            if pattern.type not in person_id_types:
                continue

            for match in compiled_regex.finditer(text):
                raw_value = match.group(1)
                normalized_value = normalize_identifier(raw_value, pattern.type)

                # Дополнительная валидация если есть
                validator = get_validation_function(pattern.type)
                is_valid = True
                if validator:
                    is_valid = validator(normalized_value)

                confidence = 0.9 if is_valid else 0.6

                id_info = {
                    "type": pattern.type,
                    "value": normalized_value,
                    "raw": match.group(0),  # Полное совпадение
                    "name": pattern.name,
                    "confidence": confidence,
                    "position": match.span(),
                    "valid": is_valid,
                }
                found_ids.append(id_info)

        # Удаляем дубликаты по value
        seen_values = set()
        unique_ids = []
        for id_info in found_ids:
            if id_info["value"] not in seen_values:
                seen_values.add(id_info["value"])
                unique_ids.append(id_info)

        return unique_ids

    def _extract_birthdates(self, text: str) -> List[Dict]:
        """Детектор дат рождения"""
        from ...data.patterns.dates import extract_birthdates_from_text

        return extract_birthdates_from_text(text)

    def _enrich_organizations_with_ids(
        self, organizations: List[OrganizationSignal], org_ids: List[Dict]
    ):
        """Обогащение организаций найденными ID"""
        if not org_ids:
            return

        for org in organizations:
            # Ищем релевантные ID для этой организации
            for id_info in org_ids:
                # Простая эвристика: добавляем все найденные организационные ID
                # В будущем можно добавить более сложную логику связывания
                org.ids.append(
                    {
                        "type": id_info["type"],
                        "value": id_info["value"],
                        "raw": id_info["raw"],
                        "confidence": id_info["confidence"],
                        "valid": id_info["valid"],
                    }
                )

                # Добавляем evidence (скоринг будет в _score_entities)
                if id_info["valid"]:
                    org.evidence.append(f"valid_{id_info['type']}")
                else:
                    org.evidence.append(f"invalid_{id_info['type']}")

    def _enrich_persons_with_ids(
        self, persons: List[PersonSignal], person_ids: List[Dict]
    ):
        """Обогащение персон найденными ID"""
        if not person_ids:
            return

        for person in persons:
            # Ищем релевантные ID для этой персоны
            for id_info in person_ids:
                # Простая эвристика: добавляем все найденные персональные ID
                # В будущем можно добавить более сложную логику связывания
                person.ids.append(
                    {
                        "type": id_info["type"],
                        "value": id_info["value"],
                        "raw": id_info["raw"],
                        "confidence": id_info["confidence"],
                        "valid": id_info["valid"],
                    }
                )

                # Добавляем evidence (скоринг будет в _score_entities)
                if id_info["valid"]:
                    person.evidence.append(f"valid_{id_info['type']}")
                else:
                    person.evidence.append(f"invalid_{id_info['type']}")

    def _enrich_persons_with_birthdates(
        self, persons: List[PersonSignal], birthdates: List[Dict], text: str
    ):
        """Обогащение персон найденными датами рождения на основе близости в тексте"""
        if not birthdates or not persons:
            return

        # Найдем позиции всех персон в тексте для proximity matching
        person_positions = []
        for person in persons:
            # Составляем полное имя для поиска
            full_name = " ".join(person.core)

            # Ищем все вхождения имени в тексте
            import re

            name_pattern = re.escape(full_name)
            matches = list(re.finditer(name_pattern, text, re.IGNORECASE))

            if matches:
                # Берем первое вхождение как основную позицию
                start_pos = matches[0].start()
                end_pos = matches[0].end()
                person_positions.append(
                    {
                        "person": person,
                        "start": start_pos,
                        "end": end_pos,
                        "center": (start_pos + end_pos) // 2,
                    }
                )

        # Ассоциируем каждую дату рождения с ближайшей персоной
        used_birthdates = set()

        for date_info in birthdates:
            date_start = date_info["position"][0]
            date_end = date_info["position"][1]
            date_center = (date_start + date_end) // 2

            # Находим ближайшую персону
            closest_person = None
            min_distance = float("inf")

            for person_pos in person_positions:
                # Проверяем, что дата не была использована
                if date_info["raw"] in used_birthdates:
                    continue

                person_center = person_pos["center"]

                # Вычисляем расстояние между центрами
                distance = abs(date_center - person_center)

                # Дополнительно учитываем, находится ли дата в "разумном" диапазоне от персоны
                # Ограничиваем максимальным расстоянием в 200 символов
                if distance < 200 and distance < min_distance:
                    min_distance = distance
                    closest_person = person_pos["person"]

            # Назначаем дату ближайшей персоне
            if closest_person and date_info["raw"] not in used_birthdates:
                closest_person.dob = date_info["date"]  # ISO формат YYYY-MM-DD
                closest_person.dob_raw = date_info["raw"]  # Исходный текст
                closest_person.evidence.append("birthdate_found")
                used_birthdates.add(date_info["raw"])

        # Если остались персоны без дат, но есть неиспользованные даты,
        # назначаем их в порядке появления в тексте
        remaining_dates = [d for d in birthdates if d["raw"] not in used_birthdates]
        persons_without_dates = [p for p in persons if not p.dob]

        for i, person in enumerate(persons_without_dates):
            if i < len(remaining_dates):
                date_info = remaining_dates[i]
                person.dob = date_info["date"]
                person.dob_raw = date_info["raw"]
                person.evidence.append("birthdate_found")

    def _score_entities(
        self, persons: List[PersonSignal], organizations: List[OrganizationSignal]
    ):
        """
        Финальный скоринг сущностей на основе собранных evidence.

        Алгоритм скоринга:
        - Базовая уверенность от нормализации: 0.5
        - Юридическая форма с валидным core: +0.3
        - Валидный ID: +0.2
        - Невалидный ID: +0.1
        - Дата рождения: +0.15
        - Множественные evidence: бонус +0.05 за каждый дополнительный
        """

        # Скоринг персон
        for person in persons:
            base_confidence = ConfidenceScoring.BASE_CONFIDENCE
            bonus = 0.0
            evidence_count = len(person.evidence)

            # Анализируем evidence для бонусов
            for ev in person.evidence:
                if ev == "birthdate_found":
                    bonus += ConfidenceScoring.BIRTHDATE_BONUS
                elif ev.startswith("valid_"):
                    bonus += ConfidenceScoring.VALID_ID_BONUS
                elif ev.startswith("invalid_"):
                    bonus += ConfidenceScoring.INVALID_ID_BONUS
                elif ev == "name_pattern":
                    bonus += ConfidenceScoring.NAME_PATTERN_BONUS

            # Бонус за множественные evidence
            if evidence_count > 1:
                multi_bonus = min(
                    ConfidenceScoring.PERSON_MAX_MULTI_BONUS,
                    (evidence_count - 1) * ConfidenceScoring.MULTI_EVIDENCE_INCREMENT
                )
                bonus += multi_bonus

            # Обновляем уверенность с учетом максимума
            person.confidence = min(ConfidenceScoring.MAX_CONFIDENCE, base_confidence + bonus)

        # Скоринг организаций
        for org in organizations:
            base_confidence = ConfidenceScoring.BASE_CONFIDENCE
            bonus = 0.0
            evidence_count = len(org.evidence)

            # Анализируем evidence для бонусов
            for ev in org.evidence:
                if ev == "legal_form_hit":
                    bonus += ConfidenceScoring.LEGAL_FORM_BONUS
                elif ev == "quoted_core":
                    bonus += ConfidenceScoring.QUOTED_CORE_BONUS
                elif ev == "norm_match":
                    bonus += ConfidenceScoring.NORM_MATCH_BONUS
                elif ev == "adjacent_name":
                    bonus += ConfidenceScoring.ADJACENT_NAME_BONUS
                elif ev.startswith("valid_"):
                    bonus += ConfidenceScoring.VALID_ID_BONUS
                elif ev.startswith("invalid_"):
                    bonus += ConfidenceScoring.INVALID_ID_BONUS
                elif ev == "org_core":
                    bonus += ConfidenceScoring.ORG_CORE_BONUS

            # Бонус за множественные evidence
            if evidence_count > 1:
                multi_bonus = min(
                    ConfidenceScoring.ORG_MAX_MULTI_BONUS,
                    (evidence_count - 1) * ConfidenceScoring.MULTI_EVIDENCE_INCREMENT
                )
                bonus += multi_bonus

            # Обновляем уверенность с учетом максимума
            org.confidence = min(ConfidenceScoring.MAX_CONFIDENCE, base_confidence + bonus)

    def _person_to_dict(self, person: PersonSignal) -> Dict[str, Any]:
        """Конвертация PersonSignal в словарь"""
        return {
            "core": person.core,
            "full_name": person.full_name,
            "dob": person.dob,
            "dob_raw": person.dob_raw,
            "ids": person.ids,
            "confidence": person.confidence,
            "evidence": person.evidence,
        }

    def _org_to_dict(self, org: OrganizationSignal) -> Dict[str, Any]:
        """Конвертация OrganizationSignal в словарь"""
        return {
            "core": org.core,
            "legal_form": org.legal_form,
            "full": org.full,
            "ids": org.ids,
            "confidence": org.confidence,
            "evidence": org.evidence,
        }

    def _empty_result(self) -> Dict[str, Any]:
        """Пустой результат при ошибке или пустом вводе"""
        return {
            "persons": [],
            "organizations": [],
            "extras": {"dates": [], "amounts": []},
        }

    def _extract_person_tokens(self, text: str, language: str) -> List[List[str]]:
        """
        Извлечение токенов персон из текста.

        Использует простую эвристику для поиска имен:
        - Слова с заглавной буквы, не являющиеся юридическими формами
        - Последовательности из 2-3 капитализированных слов
        """
        # Простая эвристика: ищем последовательности капитализированных слов
        import re

        # Паттерн для поиска имен (2-3 капитализированных слова подряд)
        # Поддерживаем украинский и русский алфавиты (только заглавные в начале)
        name_pattern = r"\b[А-ЯЁЇІЄҐ][а-яёїієґ]+(?:\s+[А-ЯЁЇІЄҐ][а-яёїієґ]+){1,2}\b"

        # Также ищем латинские имена
        latin_name_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b"

        found_names = []

        # Украинские/русские имена
        for match in re.finditer(name_pattern, text):
            name_tokens = match.group(0).split()
            # Фильтруем юридические формы
            if not self._contains_legal_form(name_tokens):
                found_names.append(name_tokens)

        # Латинские имена
        for match in re.finditer(latin_name_pattern, text):
            name_tokens = match.group(0).split()
            if not self._contains_legal_form(name_tokens):
                found_names.append(name_tokens)

        return found_names

    def _extract_organization_tokens(self, text: str, language: str) -> List[str]:
        """
        Извлечение токенов организаций из текста.

        Использует детекцию юридических форм для поиска организаций.
        """
        from ...data.patterns.legal_forms import get_legal_forms_regex

        # Ищем юридические формы в тексте
        legal_forms_regex = get_legal_forms_regex()
        organizations = []

        for match in re.finditer(legal_forms_regex, text, re.IGNORECASE):
            # Найдена юридическая форма, теперь ищем название организации
            org_text = self._extract_org_name_near_legal_form(text, match)
            if org_text:
                organizations.append(org_text.strip().upper())

        return list(set(organizations))  # Убираем дубликаты

    def _contains_legal_form(self, tokens: List[str]) -> bool:
        """Проверяет, содержат ли токены юридическую форму"""
        from ...data.patterns.legal_forms import get_legal_forms_set

        legal_forms = get_legal_forms_set()
        for token in tokens:
            if token.upper() in legal_forms:
                return True
        return False

    def _extract_org_name_near_legal_form(self, text: str, legal_form_match) -> str:
        """
        Извлекает название организации рядом с найденной юридической формой.

        Это упрощенная версия логики из _extract_legal_forms.
        """
        legal_form = legal_form_match.group(0)
        start = legal_form_match.start()
        end = legal_form_match.end()

        # Ищем кавычки рядом с юридической формой
        quoted_pattern = r'["\u201c\u201d\u00ab\u00bb]([^"\u201c\u201d\u00ab\u00bb]+)["\u201c\u201d\u00ab\u00bb]'

        # Ищем в окрестности юридической формы (±100 символов)
        search_start = max(0, start - 100)
        search_end = min(len(text), end + 100)
        search_area = text[search_start:search_end]

        quoted_matches = list(re.finditer(quoted_pattern, search_area))

        if quoted_matches:
            # Берем ближайшее кавычки к юридической форме
            legal_form_pos_in_area = start - search_start
            closest_match = min(
                quoted_matches, key=lambda m: abs(m.start() - legal_form_pos_in_area)
            )
            return closest_match.group(1)

        # Если кавычек нет, возвращаем заглушку
        return "UNNAMED_ORG"
