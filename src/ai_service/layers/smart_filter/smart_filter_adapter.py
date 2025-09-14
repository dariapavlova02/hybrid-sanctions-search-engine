"""
SmartFilter Adapter - Layer 2 of the unified architecture.

Wraps the existing SmartFilterService to match the new interface and
implements the exact specification from CLAUDE.md.
"""

import time
from typing import Dict, Any

from ...contracts.base_contracts import SmartFilterInterface, SmartFilterResult
from ...utils import get_logger
from .smart_filter_service import SmartFilterService, FilterResult

logger = get_logger(__name__)


class SmartFilterAdapter(SmartFilterInterface):
    """
    Layer 2: Smart Filter adapter for pre-processing decisions.

    Wraps the existing SmartFilterService to provide:
    - NameDetector signals (capitals, initials, patronymics, nicknames)
    - CompanyDetector signals (legal forms, banking triggers, quoted cores)
    - Payment context detection
    - Classification: must_process | recommend | maybe | skip
    - Signal weighting and confidence scoring

    Per CLAUDE.md: Does NOT normalize or change text, only evaluates it.
    """

    def __init__(self):
        self._service = None

    async def initialize(self):
        """Initialize the smart filter service"""
        try:
            # Initialize existing service with all detectors
            self._service = SmartFilterService(
                enable_name_detector=True,
                enable_company_detector=True,
                enable_document_detector=True,
                enable_terrorism_detector=True,
                confidence_threshold=0.3
            )
            logger.info("SmartFilterAdapter initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SmartFilterAdapter: {e}")
            raise

    async def should_process(self, text: str) -> SmartFilterResult:
        """
        Determine if expensive processing is worthwhile.

        Implements the exact logic from CLAUDE.md:
        1. NameDetector: заглавные, инициалы, патронимные хвосты, никнеймы/уменьшительные
        2. CompanyDetector: юр. формы, банковские триггеры, кавычные ядра
        3. Payment context: платеж/оплата/в пользу/за услуги triggers
        4. Signal weighting → confidence + classification

        Args:
            text: Sanitized input text (original form, NOT normalized)

        Returns:
            SmartFilterResult with decision and signals
        """
        if self._service is None:
            raise RuntimeError("SmartFilterAdapter not initialized")

        start_time = time.time()

        try:
            # Use existing service for detection
            filter_result = await self._service.filter(text)

            # Map existing result to new contract
            classification = self._map_to_classification(
                filter_result.confidence,
                filter_result.should_process
            )

            # Extract detected signals for transparency
            detected_signals = self._extract_signal_names(filter_result.detected_signals)

            processing_time = time.time() - start_time

            return SmartFilterResult(
                should_process=filter_result.should_process,
                confidence=filter_result.confidence,
                classification=classification,
                detected_signals=detected_signals,
                details={
                    "signal_details": filter_result.signal_details,
                    "processing_recommendation": filter_result.processing_recommendation,
                    "estimated_complexity": filter_result.estimated_complexity,
                    "name_signals": self._extract_name_signals(filter_result.signal_details),
                    "company_signals": self._extract_company_signals(filter_result.signal_details),
                    "payment_signals": self._extract_payment_signals(filter_result.signal_details)
                },
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"SmartFilter processing failed for text: {text[:50]}... Error: {e}")
            # Safe fallback: recommend processing
            return SmartFilterResult(
                should_process=True,
                confidence=0.5,
                classification="recommend",
                detected_signals=["fallback"],
                details={"error": str(e)},
                processing_time=time.time() - start_time
            )

    def _map_to_classification(self, confidence: float, should_process: bool) -> str:
        """
        Map confidence to CLAUDE.md classification levels.

        Returns: must_process | recommend | maybe | skip
        """
        if not should_process:
            return "skip"
        elif confidence >= 0.8:
            return "must_process"
        elif confidence >= 0.5:
            return "recommend"
        else:
            return "maybe"

    def _extract_signal_names(self, detected_signals: list) -> list:
        """Extract human-readable signal names from detection results"""
        if not detected_signals:
            return []

        signal_names = []
        for signal in detected_signals:
            if isinstance(signal, str):
                signal_names.append(signal)
            elif isinstance(signal, dict) and "type" in signal:
                signal_names.append(signal["type"])

        return signal_names

    def _extract_name_signals(self, signal_details: dict) -> dict:
        """Extract name-specific signals per CLAUDE.md specification"""
        name_signals = {}

        if "name_detector" in signal_details:
            details = signal_details["name_detector"]
            name_signals.update({
                "has_capitals": details.get("has_proper_names", False),
                "has_initials": details.get("has_initials", False),
                "has_patronymic_endings": details.get("has_patronymic_patterns", False),
                "has_nicknames": details.get("has_diminutives", False),
                "confidence": details.get("confidence", 0.0)
            })

        return name_signals

    def _extract_company_signals(self, signal_details: dict) -> dict:
        """Extract company-specific signals per CLAUDE.md specification"""
        company_signals = {}

        if "company_detector" in signal_details:
            details = signal_details["company_detector"]
            company_signals.update({
                "has_legal_forms": details.get("has_legal_forms", False),
                "has_banking_triggers": details.get("has_banking_keywords", False),
                "has_quoted_cores": details.get("has_quoted_names", False),
                "has_org_patterns": details.get("has_organization_patterns", False),
                "confidence": details.get("confidence", 0.0)
            })

        return company_signals

    def _extract_payment_signals(self, signal_details: dict) -> dict:
        """Extract payment context signals per CLAUDE.md specification"""
        payment_signals = {}

        # Look for payment context in various detectors
        for detector_key, details in signal_details.items():
            if isinstance(details, dict):
                if details.get("has_payment_context", False):
                    payment_signals.update({
                        "has_payment_keywords": True,
                        "payment_triggers": details.get("payment_keywords", []),
                        "confidence": details.get("payment_confidence", 0.0)
                    })
                    break

        return payment_signals if payment_signals else {"has_payment_keywords": False}