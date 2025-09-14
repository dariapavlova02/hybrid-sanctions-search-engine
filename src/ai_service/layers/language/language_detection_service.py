"""
Language detection service with fallback mechanisms
"""

import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

try:
    from langdetect import LangDetectException, detect
except ImportError:
    detect = None
    LangDetectException = Exception

from ...config import SERVICE_CONFIG, LANGUAGE_CONFIG
from ...exceptions import LanguageDetectionError
from ...utils.logging_config import get_logger
from ...utils.types import LanguageDetectionResult


# Import name dictionaries for verification
class LanguageDetectionService:
    """Service for language detection with focus on speed and accuracy"""

    def __init__(self):
        """Initialize language detection service"""
        self.logger = get_logger(__name__)
        # Controls: make Cyrillic heuristics override more aggressively if enabled
        self.aggressive_cyr_override = os.getenv(
            "AI_SERVICE_AGGRESSIVE_CYR_FALLBACK", "true"
        ).lower() in ("1", "true", "yes", "on")

        # Supported languages
        self.supported_languages = {"en": "English", "ru": "Russian", "uk": "Ukrainian"}

        # Language mapping (extended)
        self.language_mapping = {
            # English and similar
            "en": "en",
            "en-US": "en",
            "en-GB": "en",
            # Russian and similar
            "ru": "ru",
            "be": "ru",  # Belarusian -> Russian
            "kk": "ru",  # Kazakh -> Russian
            "ky": "ru",  # Kyrgyz -> Russian
            # Ukrainian
            "uk": "uk",
            # Other Slavic languages -> Russian
            "bg": "ru",  # Bulgarian
            "sr": "ru",  # Serbian
            "hr": "ru",  # Croatian
            "sl": "ru",  # Slovenian
            "pl": "ru",  # Polish
        }

        # Patterns for fast detection
        self.language_patterns = {
            "en": [
                r"\b[aeiou]{2,}",  # Long vowels
                r"\b(the|and|or|but|in|on|at|to|for|of|with|by)\b",
                r"\b(is|are|was|were|be|been|being|have|has|had|do|does|did)\b",
            ],
            "ru": [
                r"\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто|деньги|средства|перевод|платеж|оплата)\b",
                r"\b(был|была|были|быть|есть|нет|это|тот|эта|эти)\b",
                r"[аеёиоуыэюя]{2,}",  # Long vowels
                r"[йцкнгшщзхфвпрлджчсмтб]{3,}",  # Long consonants
            ],
            "uk": [
                r"\b(і|в|на|з|по|за|від|до|з|у|о|а|але|або|якщо|коли|де|як|що|хто|кошти|гроші|платіж|переказ|одержувач|отримувач)\b",
                r"\b(був|була|були|бути|є|немає|це|той|ця|ці|усього|загалом)\b",
                r"[аеєиіїоущюя]{2,}",  # Long vowels
                r"[йцкнгшщзхфвпрлджчсмтб]{3,}",  # Long consonants
            ],
        }

        # Heuristics: Ukrainian surname suffixes
        self.uk_surname_suffixes = (
            "енко",
            "енка",
            "чук",
            "чука",
            "юк",
            "юка",
            "ук",
            "ука",
            "ський",
            "ського",
            "цький",
            "цького",
            "зький",
            "зького",
            "ко",
            "ка",
        )

        # Detection statistics
        self.detection_stats = {
            "total_detections": 0,
            "successful_detections": 0,
            "fallback_detections": 0,
            "average_confidence": 0.0,
            "method_usage": {
                "dictionary": 0,
                "cyrillic_priority": 0,
                "pattern": 0,
                "langdetect": 0,
                "fallback": 0,
            },
            "recent_scores": [],  # Last 1000 confidence scores
        }

        self.logger.info("LanguageDetectionService initialized")

    def detect_language(self, text: str, use_fallback: bool = True) -> Dict[str, Any]:
        """
        Language detection with fallback mechanisms

        Args:
            text: Input text
            use_fallback: Use fallback methods

        Returns:
            Dict with detection result
        """
        if not text or not text.strip():
            return self._create_detection_result("en", 0.0, "empty_text")

        # 1. SECONDARY check for Cyrillic characters with ABSOLUTE PRIORITY
        cyrillic_result = self._detect_cyrillic_priority(text)
        if cyrillic_result["confidence"] >= 0.8:  # High priority for Cyrillic
            self._update_stats(cyrillic_result["confidence"], "cyrillic_priority")
            return cyrillic_result

        # 2. Fast detection by patterns
        pattern_result = self._fast_pattern_detection(text)
        if pattern_result["confidence"] >= 0.6:
            self._update_stats(pattern_result["confidence"], "pattern")
            return pattern_result

        # 3. Main detection (langdetect)
        if detect is not None:
            try:
                detected_lang = detect(text)

                if detected_lang in self.language_mapping:
                    mapped_lang = self.language_mapping[detected_lang]
                    confidence = 0.7  # Medium confidence for langdetect

                    result = self._create_detection_result(
                        mapped_lang, confidence, "langdetect"
                    )
                    self._update_stats(confidence, "langdetect")
                    # Optional aggressive override: if langdetect says 'en' but Cyrillic exists, prefer Cyrillic logic
                    if (
                        self.aggressive_cyr_override
                        and result["language"] == "en"
                        and re.search(r"[а-яёіїєґА-ЯЁІЇЄҐ]", text)
                    ):
                        cyr = self._detect_cyrillic_priority(text)
                        if cyr and cyr.get("language") in ("ru", "uk"):
                            return cyr
                    return result

            except LangDetectException as e:
                self.logger.debug(f"LangDetect failed: {e}")
                # Don't return result with method 'langdetect' on error

        # 4. Fallback detection
        if use_fallback:
            fallback_result = self._fallback_detection(text)
            self._update_stats(fallback_result["confidence"], "fallback")
            return fallback_result

        # 5. Default
        default_result = self._create_detection_result("en", 0.5, "default")
        self._update_stats(0.5, "default")
        return default_result

    def detect_language_config_driven(self, text: str, config: Optional[Any] = None) -> LanguageDetectionResult:
        """
        Config-driven language detection with detailed analysis
        
        Args:
            text: Input text to analyze
            config: LanguageConfig instance (uses LANGUAGE_CONFIG if None)
            
        Returns:
            LanguageDetectionResult with detailed analysis
        """
        if config is None:
            config = LANGUAGE_CONFIG
            
        if not text or not text.strip():
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                details={
                    "method": "empty_text",
                    "cyr_ratio": 0.0,
                    "lat_ratio": 0.0,
                    "uk_chars": 0,
                    "ru_chars": 0,
                    "total_letters": 0,
                    "bonuses": {},
                    "reason": "empty_text"
                }
            )
        
        # Extract alphabetic characters for analysis
        text_alpha = re.sub(r'[^a-zA-Zа-яёіїєґА-ЯЁІЇЄҐ]', '', text)
        
        # Edge case 2: Check for numeric/punctuation dominance (>70%) - check this first
        total_chars = len(text)
        non_alpha_chars = len(re.findall(r'[^a-zA-Zа-яёіїєґА-ЯЁІЇЄҐ\s]', text))
        if total_chars > 0 and (non_alpha_chars / total_chars) >= 0.7:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.2,
                details={
                    "method": "noisy_text",
                    "cyr_ratio": 0.0,
                    "lat_ratio": 0.0,
                    "uk_chars": 0,
                    "ru_chars": 0,
                    "total_letters": len(text_alpha),
                    "bonuses": {},
                    "reason": "excessive_non_alphabetic_chars"
                }
            )
        
        # Edge case 1: Check for short text (less than 3 alphabetic characters)
        if len(text_alpha) < 3:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.3,
                details={
                    "method": "short_text",
                    "cyr_ratio": 0.0,
                    "lat_ratio": 0.0,
                    "uk_chars": 0,
                    "ru_chars": 0,
                    "total_letters": len(text_alpha),
                    "bonuses": {},
                    "reason": "insufficient_alphabetic_chars"
                }
            )
        
        # Calculate character ratios
        details = self._calculate_character_ratios(text)
        
        # Edge case 3: Check for uppercase/acronym dominance
        uppercase_ratio = len(re.findall(r'[A-ZА-ЯЁІЇЄҐ]', text)) / len(text_alpha) if len(text_alpha) > 0 else 0
        is_likely_acronym = (uppercase_ratio > 0.9 and 
                           len(text_alpha) <= 10 and 
                           re.match(r'^[A-ZА-ЯЁІЇЄҐ]+$', text.strip()))
        
        # Determine primary language based on config thresholds
        language, confidence, reason = self._determine_language_from_ratios(
            details, config, text
        )
        
        # Apply bonuses for specific characters
        confidence = self._apply_character_bonuses(
            details, confidence, config
        )
        
        # Apply uppercase/acronym confidence penalty (after bonuses)
        if is_likely_acronym:
            confidence = max(0.1, confidence - 0.4)  # Increased penalty for acronyms
            details["uppercase_penalty"] = 0.4
            details["is_likely_acronym"] = True
        
        # Check for mixed language
        if self._is_mixed_language(details, config):
            language = "mixed"
            confidence = min(max(details["cyr_ratio"], details["lat_ratio"]) + 0.05, 0.95)
            reason = "mixed_language"
        
        # Apply minimum confidence threshold
        if confidence < config.min_confidence:
            language = "unknown"
            reason = "low_confidence"
        
        # Clamp confidence to [0, 1]
        confidence = max(0.0, min(1.0, confidence))
        
        # Update details with final results
        details.update({
            "method": "config_driven",
            "reason": reason,
            "final_confidence": confidence,
            "final_language": language,
            "config_used": config.to_dict()
        })
        
        return LanguageDetectionResult(
            language=language,
            confidence=confidence,
            details=details
        )
    
    def _calculate_character_ratios(self, text: str) -> Dict[str, Any]:
        """Calculate character ratios and counts"""
        # Count different character types
        cyr_chars = len(re.findall(r"[а-яёіїєґА-ЯЁІЇЄҐ]", text))
        lat_chars = len(re.findall(r"[a-zA-Z]", text))
        digits = len(re.findall(r"[0-9]", text))
        punct = len(re.findall(r"[^\w\s]", text))
        
        # Count specific characters for bonuses
        uk_chars = len(re.findall(r"[іїєґІЇЄҐ]", text))
        ru_chars = len(re.findall(r"[ёъыэЁЪЫЭ]", text))
        
        # Calculate total letters (excluding digits and punctuation)
        total_letters = cyr_chars + lat_chars
        
        # Calculate ratios
        cyr_ratio = cyr_chars / total_letters if total_letters > 0 else 0.0
        lat_ratio = lat_chars / total_letters if total_letters > 0 else 0.0
        
        return {
            "cyr_chars": cyr_chars,
            "lat_chars": lat_chars,
            "cyr_ratio": cyr_ratio,
            "lat_ratio": lat_ratio,
            "uk_chars": uk_chars,
            "ru_chars": ru_chars,
            "total_letters": total_letters,
            "digits": digits,
            "punct": punct,
            "bonuses": {}
        }
    
    def _determine_language_from_ratios(self, details: Dict[str, Any], config: Any, text: str) -> tuple[str, float, str]:
        """Determine primary language from character ratios"""
        cyr_ratio = details["cyr_ratio"]
        lat_ratio = details["lat_ratio"]
        
        # Check if both ratios are below minimum thresholds
        if cyr_ratio < config.min_cyr_ratio and lat_ratio < config.min_lat_ratio:
            return "unknown", 0.0, "below_thresholds"
        
        # Check for mixed language (both ratios above thresholds and close)
        if (cyr_ratio >= config.min_cyr_ratio and 
            lat_ratio >= config.min_lat_ratio and 
            abs(cyr_ratio - lat_ratio) < config.mixed_gap):
            return "mixed", min(cyr_ratio, lat_ratio), "mixed_candidate"
        
        # Determine primary language based on higher ratio
        if cyr_ratio > lat_ratio:
            # Determine if Ukrainian or Russian based on specific characters
            if details["uk_chars"] > details["ru_chars"]:
                return "uk", cyr_ratio, "cyrillic_ukrainian"
            elif details["ru_chars"] > details["uk_chars"]:
                return "ru", cyr_ratio, "cyrillic_russian"
            else:
                # Use pattern-based detection for ambiguous Cyrillic text
                lang, confidence, reason = self._detect_cyrillic_language_patterns(text)
                return lang, confidence, reason
        else:
            return "en", lat_ratio, "latin"
    
    def _apply_character_bonuses(self, details: Dict[str, Any], confidence: float, config: Any) -> float:
        """Apply bonuses for specific characters"""
        bonuses = {}
        
        # Ukrainian character bonus
        if details["uk_chars"] > 0:
            uk_bonus = min(details["uk_chars"] * config.prefer_uk_chars_bonus, 0.2)
            confidence += uk_bonus
            bonuses["uk_chars"] = uk_bonus
        
        # Russian character bonus
        if details["ru_chars"] > 0:
            ru_bonus = min(details["ru_chars"] * config.prefer_ru_chars_bonus, 0.2)
            confidence += ru_bonus
            bonuses["ru_chars"] = ru_bonus
        
        details["bonuses"] = bonuses
        return confidence
    
    def _is_mixed_language(self, details: Dict[str, Any], config: Any) -> bool:
        """Check if the language should be classified as mixed"""
        cyr_ratio = details["cyr_ratio"]
        lat_ratio = details["lat_ratio"]
        
        return (cyr_ratio >= config.min_cyr_ratio and 
                lat_ratio >= config.min_lat_ratio and 
                abs(cyr_ratio - lat_ratio) < config.mixed_gap)
    
    def _detect_cyrillic_language_patterns(self, text: str) -> tuple[str, float, str]:
        """Detect Ukrainian vs Russian using pattern matching for ambiguous Cyrillic text"""
        # Ukrainian patterns
        uk_patterns = [
            r"\b(і|в|на|з|по|за|від|до|у|о|а|але|або|якщо|коли|де|як|що|хто|кошти|гроші|платіж|переказ|одержувач|отримувач)\b",
            r"\b(був|була|були|бути|є|немає|це|той|ця|ці|усього|загалом)\b",
        ]
        
        # Russian patterns
        ru_patterns = [
            r"\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто|деньги|средства|перевод|платеж|оплата)\b",
            r"\b(был|была|были|быть|есть|нет|это|тот|эта|эти)\b",
        ]
        
        # Count pattern matches
        uk_matches = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in uk_patterns)
        ru_matches = sum(len(re.findall(pattern, text, re.IGNORECASE)) for pattern in ru_patterns)
        
        # Check for Ukrainian surname suffixes
        words = re.findall(r"\b[А-ЯІЇЄҐ][а-яіїєґА-ЯІЇЄҐ\'-]+\b", text)
        uk_surname_count = sum(1 for w in words if any(w.lower().endswith(suf) for suf in self.uk_surname_suffixes))
        
        # Determine language based on patterns
        if uk_matches > ru_matches or uk_surname_count > 0:
            confidence = min(0.9, 0.7 + uk_matches * 0.05 + uk_surname_count * 0.1)
            return "uk", confidence, "cyrillic_patterns_ukrainian"
        elif ru_matches > uk_matches:
            confidence = min(0.9, 0.7 + ru_matches * 0.05)
            return "ru", confidence, "cyrillic_patterns_russian"
        else:
            # Default to Russian for ambiguous cases (more conservative)
            confidence = 0.6
            return "ru", confidence, "cyrillic_default_russian"

    def _fast_pattern_detection(self, text: str) -> Dict[str, Any]:
        """Fast detection by patterns"""
        scores = {}

        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches

            # Normalize score
            scores[lang] = score / len(patterns) if patterns else 0

        # Find language with highest score
        if scores:
            best_lang = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_lang]

            if best_score > 0.3:  # Threshold for fast detection
                confidence = min(0.8, 0.5 + best_score * 0.3)
                return self._create_detection_result(best_lang, confidence, "pattern")

        return self._create_detection_result("en", 0.3, "pattern_low_confidence")

    def _detect_cyrillic_priority(self, text: str) -> Dict[str, Any]:
        """ABSOLUTE PRIORITY of Cyrillic characters"""
        # Count Ukrainian unique characters
        ukrainian_chars = len(re.findall(r"[іїєґІЇЄҐ]", text))

        # Count Russian specific characters
        russian_chars = len(re.findall(r"[ёъыэЁЪЫЭ]", text))

        # Count total Cyrillic characters
        cyrillic_chars = len(re.findall(r"[а-яёА-ЯЁ]", text))

        # ABSOLUTE PRIORITY: even ONE Ukrainian character = Ukrainian language
        if ukrainian_chars > 0:
            confidence = min(0.98, 0.8 + ukrainian_chars * 0.1)  # Very high confidence
            return self._create_detection_result("uk", confidence, "cyrillic_ukrainian")

        # If there are Russian specific characters
        if russian_chars > 0:
            confidence = min(0.95, 0.8 + russian_chars * 0.1)
            return self._create_detection_result("ru", confidence, "cyrillic_russian")

        # If there is Cyrillic in general (without specific characters)
        if cyrillic_chars > 0:
            # Surname suffix heuristic (strongly favors Ukrainian)
            words = re.findall(r"\b[А-ЯІЇЄҐ][а-яіїєґА-ЯІЇЄҐ\'-]+\b", text)
            for w in words:
                lw = w.lower()
                if any(lw.endswith(suf) for suf in self.uk_surname_suffixes):
                    confidence = 0.92
                    return self._create_detection_result(
                        "uk", confidence, "cyrillic_surname_suffix"
                    )

            # Additional check for Ukrainian words
            uk_patterns = len(
                re.findall(
                    r"\b(і|в|на|з|по|за|від|до|у|о|а|але|або|якщо|коли|де|як|що|хто|це|той|ця|ці|був|була|були|бути|є|немає)\b",
                    text,
                    re.IGNORECASE,
                )
            )
            ru_patterns = len(
                re.findall(
                    r"\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто|это|тот|эта|эти|был|была|были|быть|есть|нет)\b",
                    text,
                    re.IGNORECASE,
                )
            )

            if uk_patterns > ru_patterns:
                confidence = min(0.9, 0.7 + uk_patterns * 0.05)
                return self._create_detection_result(
                    "uk", confidence, "cyrillic_patterns_ukrainian"
                )
            else:
                confidence = min(0.9, 0.7 + ru_patterns * 0.05)
                return self._create_detection_result(
                    "ru", confidence, "cyrillic_patterns_russian"
                )

        # No Cyrillic characters - low confidence
        return self._create_detection_result("en", 0.2, "cyrillic_none")

    def _fallback_detection(self, text: str) -> Dict[str, Any]:
        """Fallback detection based on character statistics with improved logic"""
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r"[а-яёіїє]", text, re.IGNORECASE))
        latin_count = len(re.findall(r"[a-z]", text, re.IGNORECASE))
        total_chars = len(re.findall(r"[а-яёіїєa-z]", text, re.IGNORECASE))

        if total_chars == 0:
            return self._create_detection_result("en", 0.1, "fallback_no_letters")

        # Improved logic: even a small number of Cyrillic characters outweighs Latin
        if cyrillic_count > 0:
            # Additional check for Ukrainian
            if cyrillic_count > latin_count:
                uk_specific = len(re.findall(r"[іїєґІЇЄҐ]", text))
                ru_specific = len(re.findall(r"[ёъыэЁЪЫЭ]", text))

                if uk_specific > 0:
                    # Check for typical Ukrainian/Russian patterns
                    uk_patterns = len(
                        re.findall(
                            r"\b(і|в|на|з|по|за|від|до|у|о|а|але|або|якщо|коли|де|як|що|хто)\b",
                            text,
                            re.IGNORECASE,
                        )
                    )
                    ru_patterns = len(
                        re.findall(
                            r"\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто)\b",
                            text,
                            re.IGNORECASE,
                        )
                    )

                    if uk_patterns >= ru_patterns:
                        confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                        return self._create_detection_result(
                            "uk", confidence, "fallback_cyrillic_ukrainian"
                        )
                    else:
                        confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                        return self._create_detection_result(
                            "ru", confidence, "fallback_cyrillic_russian"
                        )

            # If there are Cyrillic characters, determine as Russian (default Cyrillic)
            if cyrillic_count > 0:
                confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                return self._create_detection_result(
                    "ru", confidence, "fallback_cyrillic_default"
                )

            # Only if there are no Cyrillic characters at all, determine as English
            confidence = min(0.7, 0.5 + latin_count / total_chars)
            return self._create_detection_result("en", confidence, "fallback_latin")

        return self._create_detection_result("en", 0.5, "fallback_default")

    def _create_detection_result(
        self, language: str, confidence: float, method: str
    ) -> Dict[str, Any]:
        """Create detection result"""
        result = {
            "language": language,
            "confidence": confidence,
            "method": method,
            "timestamp": None,  # Can add timestamp
        }

        # Add additional fields
        result["supported"] = language in self.supported_languages
        result["language_name"] = self.supported_languages.get(language, language)

        # Update statistics
        self.detection_stats["total_detections"] += 1
        self.detection_stats["recent_scores"].append(confidence)

        # Keep only last 1000 scores
        if len(self.detection_stats["recent_scores"]) > 1000:
            self.detection_stats["recent_scores"] = self.detection_stats[
                "recent_scores"
            ][-1000:]

        return result

    def _update_stats(self, confidence: float, method: str):
        """Update detection statistics"""
        self.detection_stats["successful_detections"] += 1
        self.detection_stats["average_confidence"] = (
            self.detection_stats["average_confidence"]
            * (self.detection_stats["successful_detections"] - 1)
            + confidence
        ) / self.detection_stats["successful_detections"]

        if method in self.detection_stats["method_usage"]:
            self.detection_stats["method_usage"][method] += 1

    def detect_languages_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Batch language detection"""
        results = []
        for text in texts:
            result = self.detect_language(text)
            results.append(result)
        return results

    def detect_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Alias for detect_languages_batch"""
        return self.detect_languages_batch(texts)

    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        stats = self.detection_stats.copy()

        # Calculate additional metrics
        if stats["recent_scores"]:
            stats["recent_average_confidence"] = sum(stats["recent_scores"]) / len(
                stats["recent_scores"]
            )
            stats["recent_min_confidence"] = min(stats["recent_scores"])
            stats["recent_max_confidence"] = max(stats["recent_scores"])
        else:
            stats["recent_average_confidence"] = 0.0
            stats["recent_min_confidence"] = 0.0
            stats["recent_max_confidence"] = 0.0

        stats["success_rate"] = (
            stats["successful_detections"] / stats["total_detections"]
            if stats["total_detections"] > 0
            else 0.0
        )

        stats["method_distribution"] = {
            method: count / max(stats["total_detections"], 1)
            for method, count in stats["method_usage"].items()
        }

        # Add aliases for backward compatibility
        stats["avg_confidence"] = stats["average_confidence"]
        stats["confidence_scores"] = stats["recent_scores"]
        stats["fallback_usage"] = stats["fallback_detections"]

        return stats

    def reset_stats(self) -> None:
        """Reset detection statistics"""
        self.detection_stats = {
            "total_detections": 0,
            "successful_detections": 0,
            "fallback_detections": 0,
            "average_confidence": 0.0,
            "method_usage": {
                "dictionary": 0,
                "cyrillic_priority": 0,
                "pattern": 0,
                "langdetect": 0,
                "fallback": 0,
            },
            "recent_scores": [],
        }
        self.logger.info("Detection statistics reset")

    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.supported_languages

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.supported_languages.keys())

    def add_language_mapping(self, source_lang: str, target_lang: str) -> None:
        """Add new language mapping"""
        # Only add mapping if target language is supported
        if target_lang in self.supported_languages:
            self.language_mapping[source_lang] = target_lang
