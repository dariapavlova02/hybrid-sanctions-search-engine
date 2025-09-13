"""
Улучшенный Template Builder с оптимизированной генерацией AC паттернов
"""

import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from ..utils import get_logger
from .high_recall_ac_generator import HighRecallACGenerator, RecallOptimizedPattern
from .template_builder import EntityTemplate, TemplateBuilder


class EnhancedTemplateBuilder(TemplateBuilder):
    """Улучшенный Template Builder с оптимизированными паттернами"""

    def __init__(self):
        super().__init__()
        self.pattern_generator = HighRecallACGenerator()
        self.logger = get_logger(__name__)

        # Settings for different entity types
        self.entity_configs = {
            "person": {
                "require_context_for_surnames": True,
                "min_confidence": 0.6,
                "max_patterns_per_entity": 15,
            },
            "company": {
                "require_legal_form": False,  # Not always required
                "min_confidence": 0.7,
                "max_patterns_per_entity": 20,
            },
            "document": {
                "require_context": False,
                "min_confidence": 0.95,
                "max_patterns_per_entity": 5,
            },
        }

        self.logger.info(
            "EnhancedTemplateBuilder initialized with optimized AC patterns"
        )

    def create_optimized_entity_template(
        self,
        entity: Dict,
        normalized_text: str,
        language: str,
        language_confidence: float,
        variants: List[str],
        token_variants: Dict[str, List[str]] = None,
        embeddings: Optional[List[float]] = None,
        entity_metadata: Dict = None,
    ) -> EntityTemplate:
        """
        Создание оптимизированного шаблона с точными AC паттернами
        """
        try:
            entity_type = entity.get("type", "unknown").lower()
            entity_metadata = entity_metadata or {}

            # Generate patterns with maximum Recall (use original text)
            original_text = entity.get("text", normalized_text)
            optimized_patterns = self.pattern_generator.generate_high_recall_patterns(
                text=original_text, language=language, entity_metadata=entity_metadata
            )

            # Convert to string patterns for AC
            ac_patterns = self._convert_to_ac_patterns(optimized_patterns, entity_type)

            # Filter patterns by entity configuration
            filtered_patterns = self._filter_patterns_by_entity_config(
                ac_patterns, entity_type, language_confidence
            )

            # Create extended variants only for high-quality patterns
            enhanced_variants = self._create_enhanced_variants(
                filtered_patterns, variants, language
            )

            # Calculate new quality score
            template_confidence = self._calculate_enhanced_confidence(
                optimized_patterns, language_confidence, len(filtered_patterns)
            )

            # Create template with optimized data
            template = EntityTemplate(
                original_text=entity.get("text", ""),
                entity_type=entity_type,
                source=entity.get("source", "enhanced_builder"),
                normalized_text=normalized_text,
                language=language,
                language_confidence=language_confidence,
                search_patterns=filtered_patterns,
                variants=enhanced_variants,
                token_variants=token_variants or {},
                embeddings=embeddings,
                complexity_score=self._calculate_complexity_score(
                    language_confidence,
                    len(filtered_patterns),
                    len(enhanced_variants),
                    normalized_text,
                ),
                template_confidence=template_confidence,
            )

            # Add optimization metadata
            if hasattr(template, "metadata"):
                template.metadata = {}
            template.metadata = {
                "optimization_applied": True,
                "original_patterns_count": len(optimized_patterns),
                "filtered_patterns_count": len(filtered_patterns),
                "pattern_statistics": self._get_pattern_statistics(optimized_patterns),
                "entity_config": self.entity_configs.get(entity_type, {}),
            }

            self.logger.info(
                f"Created optimized template for {entity_type}: "
                f"{len(optimized_patterns)} -> {len(filtered_patterns)} patterns"
            )

            return template

        except Exception as e:
            self.logger.error(f"Failed to create optimized template: {e}")
            # Fallback to base method
            return super().create_entity_template(
                entity,
                normalized_text,
                language,
                language_confidence,
                variants,
                token_variants,
                embeddings,
            )

    def _convert_to_ac_patterns(
        self, optimized_patterns: List[RecallOptimizedPattern], entity_type: str
    ) -> List[str]:
        """Конвертация RecallOptimizedPattern в строки для AC"""
        ac_patterns = []

        for opt_pattern in optimized_patterns:
            # Add main pattern
            ac_patterns.append(opt_pattern.pattern)

            # Add all variants from pattern
            ac_patterns.extend(opt_pattern.variants)

            # For high-confidence patterns add case variations
            if (
                opt_pattern.pattern_type
                in [
                    "full_name_aggressive",
                    "structured_name_aggressive",
                    "company_with_legal_form",
                ]
                and opt_pattern.precision_hint >= 0.8
            ):

                # Add lowercase version for contextual searches
                ac_patterns.append(opt_pattern.pattern.lower())

                # Add UPPERCASE for document headers
                if len(opt_pattern.pattern.split()) >= 2:  # Only for full names
                    ac_patterns.append(opt_pattern.pattern.upper())

        return list(set(ac_patterns))  # Remove duplicates

    def _filter_patterns_by_entity_config(
        self, patterns: List[str], entity_type: str, language_confidence: float
    ) -> List[str]:
        """Фильтрация паттернов согласно конфигурации сущности"""
        if entity_type not in self.entity_configs:
            return patterns[:20]  # Basic limit

        config = self.entity_configs[entity_type]
        filtered = []

        # Check minimum confidence
        if language_confidence < config["min_confidence"]:
            # If low confidence, take only shortest and most accurate patterns
            filtered = [p for p in patterns if len(p.split()) <= 2 and len(p) >= 5][:5]
        else:
            filtered = patterns

        # Limit quantity
        max_patterns = config["max_patterns_per_entity"]
        if len(filtered) > max_patterns:
            # Sort by length (longer = more specific)
            filtered.sort(key=lambda x: (len(x.split()), len(x)), reverse=True)
            filtered = filtered[:max_patterns]

        # Fallback: if empty after filtering — take 3 most specific by length
        if not filtered and patterns:
            tmp = sorted(patterns, key=lambda x: (len(x.split()), len(x)), reverse=True)
            filtered = tmp[:3]

        return filtered

    def _create_enhanced_variants(
        self, filtered_patterns: List[str], original_variants: List[str], language: str
    ) -> List[str]:
        """Создание улучшенных вариантов на основе отфильтрованных паттернов"""
        enhanced_variants = set(original_variants)

        for pattern in filtered_patterns:
            # For each pattern create minimal high-quality variants

            if len(pattern.split()) >= 2:  # Compound names/titles
                # Add variants with initials
                words = pattern.split()
                if len(words) == 2:  # First Last -> F. Last
                    enhanced_variants.add(f"{words[0][0]}. {words[1]}")
                elif len(words) == 3:  # First Middle Last -> F.M. Last
                    enhanced_variants.add(f"{words[0][0]}. {words[1][0]}. {words[2]}")

            # Remove extra characters from source pattern
            clean_pattern = pattern.strip('.,;:!?"()[]{}')
            if clean_pattern != pattern and len(clean_pattern) >= 3:
                enhanced_variants.add(clean_pattern)

        # Filter variants: remove too short ones
        final_variants = [v for v in enhanced_variants if len(v) >= 3]

        return final_variants[:25]  # Limit number of variants

    def _calculate_enhanced_confidence(
        self,
        optimized_patterns: List[RecallOptimizedPattern],
        language_confidence: float,
        filtered_count: int,
    ) -> float:
        """Расчет улучшенной оценки уверенности шаблона"""
        if not optimized_patterns:
            return 0.1

        # Base score from language
        base_confidence = language_confidence * 0.4

        # Score from pattern quality (use precision_hint instead of confidence)
        if optimized_patterns:
            avg_precision = sum(p.precision_hint for p in optimized_patterns) / len(
                optimized_patterns
            )
            avg_source_confidence = sum(
                p.source_confidence for p in optimized_patterns
            ) / len(optimized_patterns)
            pattern_score = (avg_precision * avg_source_confidence) * 0.4
        else:
            pattern_score = 0.1

        # Score from number of filtered patterns
        if isinstance(filtered_count, (list, tuple)):
            filtered_count = len(filtered_count)

        if filtered_count > 0:
            # More quality patterns = higher confidence, but with diminishing returns
            filter_score = min(0.2, filtered_count * 0.02)
        else:
            filter_score = 0.0

        total_confidence = base_confidence + pattern_score + filter_score
        return min(1.0, max(0.1, total_confidence))

    def export_optimized_for_aho_corasick(
        self, templates: List[EntityTemplate]
    ) -> Dict[str, List[str]]:
        """
        Экспорт оптимизированных шаблонов для многоуровневого AC поиска
        Использует новую логику с HighRecallACGenerator
        """
        tier_patterns = {
            "tier_0_exact": [],  # Documents, exact IDs
            "tier_1_high_recall": [],  # Full names with context
            "tier_2_medium_recall": [],  # Structured names
            "tier_3_broad_recall": [],  # Simple patterns
        }

        for template in templates:
            # Classify patterns by confidence and type
            for pattern in template.search_patterns:
                pattern_length = len(pattern)
                word_count = len(pattern.split())

                # Documents and exact IDs (highest priority)
                if (
                    re.match(r"^\d+$", pattern)
                    and pattern_length >= 6
                    or re.match(r"^[A-Z]{2}\d+", pattern)
                ):
                    tier_patterns["tier_0_exact"].append(pattern)

                # High confidence: full names (2+ words) + high template confidence
                elif (
                    word_count >= 2
                    and template.template_confidence >= 0.85
                    and pattern_length >= 6
                ):
                    tier_patterns["tier_1_high_recall"].append(pattern)

                # Medium confidence: structured names or good single-syllable
                elif ("." in pattern and word_count >= 2) or (
                    word_count == 1
                    and template.template_confidence >= 0.8
                    and pattern_length >= 4
                ):
                    tier_patterns["tier_2_medium_recall"].append(pattern)

                # Low confidence: others
                else:
                    tier_patterns["tier_3_broad_recall"].append(pattern)

            # Add high-quality variants to appropriate levels
            for variant in template.variants:
                variant_length = len(variant)
                variant_words = len(variant.split())

                if variant_words >= 2 and template.template_confidence >= 0.8:
                    tier_patterns["tier_1_high_recall"].append(variant)
                elif variant_length >= 4:
                    tier_patterns["tier_2_medium_recall"].append(variant)

        # Remove duplicates in each level
        for tier in tier_patterns:
            tier_patterns[tier] = list(set(tier_patterns[tier]))

        # Statistics
        total_patterns = sum(len(patterns) for patterns in tier_patterns.values())
        self.logger.info(
            f"Exported {total_patterns} optimized AC patterns across 4 tiers"
        )

        return tier_patterns

    def get_optimization_report(
        self, templates: List[EntityTemplate]
    ) -> Dict[str, Any]:
        """Отчет по оптимизации паттернов"""
        if not templates:
            return {}

        optimized_templates = [
            t
            for t in templates
            if hasattr(t, "metadata") and t.metadata.get("optimization_applied")
        ]

        if not optimized_templates:
            return {"error": "No optimized templates found"}

        report = {
            "total_templates": len(templates),
            "optimized_templates": len(optimized_templates),
            "optimization_coverage": len(optimized_templates) / len(templates) * 100,
            "pattern_reduction": {
                "original_total": 0,
                "filtered_total": 0,
                "reduction_percentage": 0,
            },
            "confidence_improvement": {"optimized_avg": 0, "non_optimized_avg": 0},
            "tier_distribution": {},
        }

        # Count pattern reduction
        for template in optimized_templates:
            if template.metadata and "original_patterns_count" in template.metadata:
                report["pattern_reduction"]["original_total"] += template.metadata[
                    "original_patterns_count"
                ]
                report["pattern_reduction"]["filtered_total"] += template.metadata[
                    "filtered_patterns_count"
                ]

        if report["pattern_reduction"]["original_total"] > 0:
            report["pattern_reduction"]["reduction_percentage"] = (
                1
                - report["pattern_reduction"]["filtered_total"]
                / report["pattern_reduction"]["original_total"]
            ) * 100

        # Compare confidence
        optimized_confidences = [t.template_confidence for t in optimized_templates]
        non_optimized_templates = [
            t
            for t in templates
            if not (hasattr(t, "metadata") and t.metadata.get("optimization_applied"))
        ]
        non_optimized_confidences = [
            t.template_confidence for t in non_optimized_templates
        ]

        if optimized_confidences:
            report["confidence_improvement"]["optimized_avg"] = sum(
                optimized_confidences
            ) / len(optimized_confidences)

        if non_optimized_confidences:
            report["confidence_improvement"]["non_optimized_avg"] = sum(
                non_optimized_confidences
            ) / len(non_optimized_confidences)

        # Distribution by levels
        tier_export = self.export_optimized_for_aho_corasick(templates)
        report["tier_distribution"] = {
            tier: len(patterns) for tier, patterns in tier_export.items()
        }

        # Add information about new logic
        report["optimization_method"] = "high_recall_ac_generator"
        report["recall_focused"] = True

        return report

    async def create_batch_templates(
        self, entities: List[Dict], entity_type: str = None
    ) -> List[EntityTemplate]:
        """
        Create templates for a batch of entities using enhanced logic

        Args:
            entities: List of original entities
            entity_type: Type of entities (person, company, etc.)

        Returns:
            List of ready-made templates
        """
        templates = []
        
        # Create orchestrator once to avoid memory leaks
        from .orchestrator_service import OrchestratorService
        
        orchestrator = OrchestratorService()

        for i, entity in enumerate(entities):
            try:
                # Extract basic info - try different field names
                text = entity.get("name") or entity.get("text") or entity.get("name_en") or entity.get("name_ru") or ""
                if not text:
                    self.logger.debug(f"Entity {i} has no text/name field: {list(entity.keys())}")
                    continue
                
                self.logger.debug(f"Processing entity {i}: {text[:50]}...")

                # Process entity using async version
                result = await orchestrator.process_text(
                    text=text,
                    generate_variants=True,
                    generate_embeddings=False,
                    cache_result=False
                )

                if result.success:
                    # Create optimized template
                    template = self.create_optimized_entity_template(
                        entity=entity,
                        normalized_text=result.normalized_text,
                        language=result.language,
                        language_confidence=result.language_confidence,
                        variants=result.variants,
                        token_variants=result.token_variants,
                        embeddings=result.embeddings,
                        entity_metadata=entity,
                    )
                    
                    # Set original_text to the processed text
                    template.original_text = text
                    templates.append(template)
                else:
                    self.logger.warning(f"Failed to process entity: {text}")

            except Exception as e:
                self.logger.error(
                    f"Error processing entity {entity.get('text', '')}: {e}"
                )
                continue

        self.logger.info(
            f"Created {len(templates)} enhanced templates from {len(entities)} entities"
        )
        return templates

    def _get_pattern_statistics(
        self, patterns: List[RecallOptimizedPattern]
    ) -> Dict[str, Any]:
        """Получение статистики по паттернам"""
        if not patterns:
            return {}

        tier_distribution = {0: 0, 1: 0, 2: 0, 3: 0}
        precision_expectations = []
        total_variants = 0

        for pattern in patterns:
            tier_distribution[pattern.recall_tier] += 1
            precision_expectations.append(pattern.precision_hint)
            total_variants += len(pattern.variants)

        return {
            "total_patterns": len(patterns),
            "total_variants": total_variants,
            "tier_distribution": {
                "tier_0_exact": tier_distribution[0],
                "tier_1_high_recall": tier_distribution[1],
                "tier_2_medium_recall": tier_distribution[2],
                "tier_3_broad_recall": tier_distribution[3],
            },
            "avg_precision": (
                sum(precision_expectations) / len(precision_expectations)
                if precision_expectations
                else 0.0
            ),
        }


# Import regular expressions for checks
import re
