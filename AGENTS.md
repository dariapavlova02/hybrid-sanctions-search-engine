# AGENTS.md: Instructions for AI Agents

This document provides guidance for AI agents working on the `AI-Normalization-Service` codebase.

## NormalizationService Architecture

The `NormalizationService` is responsible for normalizing person names from free-form text. The service has been refactored to follow a simple, robust, and library-driven pipeline. Please adhere to this design to avoid re-introducing the complexity of the previous implementation.

The normalization pipeline consists of the following steps, executed in `NormalizationService.normalize_async`:

1.  **Language Detection**: The language of the input text is detected using `LanguageDetectionService`.
2.  **Text Cleaning**: The input text is cleaned to remove irrelevant characters using `basic_cleanup` and `normalize_unicode`.
3.  **Name Entity Recognition (NER)**: Person names are extracted from the cleaned text using `spacy`'s NER models (`_extract_name_tokens_with_ner`). This is the primary method for identifying names.
4.  **Fallback Name Detection**: If `spacy`'s NER does not find any person names, a simplified `NameDetector` is used as a fallback. This detector uses basic heuristics (capitalized words, dictionary lookups) to find potential names.
5.  **Token Normalization**: The extracted name tokens are normalized using `_normalize_tokens`. This method dispatches to language-specific helpers:
    *   `_normalize_slavic_tokens` for Ukrainian and Russian.
    *   `_normalize_english_tokens` for English.
6.  **Slavic Normalization (`_normalize_slavic_tokens`)**:
    *   It uses `pymorphy3` (via the language-specific `MorphologyAnalyzer`) to get the nominative case of each token.
    *   It then uses a flat dictionary of diminutives (`special_names`) to convert nicknames to their full forms (e.g., "петрик" -> "петро").
7.  **English Normalization (`_normalize_english_tokens`)**:
    *   It uses a flat dictionary of nicknames (`NICKNAMES`) to convert nicknames to their full forms (e.g., "bill" -> "william").
8.  **Reconstruction**: The normalized tokens are joined back into a string.

## Key Principles

*   **Rely on Libraries**: For core NLP tasks like NER and morphological analysis, rely on `spacy` and `pymorphy3`. Do not re-implement this logic with hand-crafted rules.
*   **Keep Dictionaries Flat**: The diminutive/nickname dictionaries should be simple, flat key-value stores (`{'nickname': 'full_name'}`). This makes the lookup logic simple and consistent across languages. Avoid complex, nested dictionary structures.
*   **Centralize Logic**: The main normalization logic is centralized in `NormalizationService`. The `NameDetector` and `MorphologyAnalyzer` classes are helpers that provide specific functionalities (fallback detection, morphology, dictionaries) but do not contain complex pipeline logic themselves.
*   **Write Strict Tests**: All new functionality should be accompanied by strict unit and integration tests that check for exact output, not just subsets.

By following these principles, we can keep the codebase clean, maintainable, and robust.
