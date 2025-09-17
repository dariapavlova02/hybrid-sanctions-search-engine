"""Smoke tests covering regression cases for RU/UK diminutive resolution."""

import os

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestDiminutiveRegression:
    """Ensure canonical names are produced from diminutives in key scenarios."""

    def setup_method(self):
        os.environ["USE_DIMINUTIVES_DICTIONARY_ONLY"] = "true"
        os.environ["DIMINUTIVES_ALLOW_CROSS_LANG"] = "false"

        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

        self.service = NormalizationService()

    def teardown_method(self):
        os.environ.pop("USE_DIMINUTIVES_DICTIONARY_ONLY", None)
        os.environ.pop("DIMINUTIVES_ALLOW_CROSS_LANG", None)

        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

    def test_russian_vova_petrov(self):
        result = self.service.normalize_sync("Вова Петров", language="ru")

        assert result.normalized == "Владимир Петров"
        vova_trace = next(trace for trace in result.trace if trace.token.lower() == "вова")
        assert "diminutive_resolved" in (vova_trace.notes or "")

    def test_ukrainian_sashko_koval(self):
        result = self.service.normalize_sync("Сашко Коваль", language="uk")

        assert result.normalized == "Олександр Коваль"
        sashko_trace = next(trace for trace in result.trace if trace.token.lower() == "сашко")
        assert "diminutive_resolved" in (sashko_trace.notes or "")

    def test_cross_language_ambiguity_prevents_volodymyr(self):
        result = self.service.normalize_sync("Вова", language="ru")

        assert result.normalized == "Владимир"
        assert "Володимир" not in result.normalized
