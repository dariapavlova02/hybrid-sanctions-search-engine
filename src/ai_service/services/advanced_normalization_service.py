#!/usr/bin/env python3
"""
Advanced normalization service with morphology and transliteration support:
- Reductive-diminutive forms
- Regional transliterations  
- Morphological cases
- Enhanced Ukrainian name processing
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set, Any
import spacy
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, SnowballStemmer
from nltk.tokenize import word_tokenize
import nltk
from langdetect import detect, LangDetectException
from unidecode import unidecode
from pymorphy3 import MorphAnalyzer

from .ukrainian_morphology import UkrainianMorphologyAnalyzer
from .russian_morphology import RussianMorphologyAnalyzer

logger = logging.getLogger(__name__)


class AdvancedNormalizationService:
    """Advanced normalization service with morphology and transliteration support"""
    
    def __init__(self):
        """Initialize advanced normalization service"""
        self.logger = logging.getLogger(__name__)
        
        # Download required NLTK resources
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK resources: {e}")
        
        # Initialize language-specific resources
        self._initialize_language_resources()
        
        # Initialize Ukrainian morphology analyzer
        self.uk_morphology = UkrainianMorphologyAnalyzer()
        
        # Initialize Russian morphology analyzer
        self.ru_morphology = RussianMorphologyAnalyzer()
        
        # Initialize pymorphy3 analyzers
        self._initialize_pymorphy3()
        
        # Regional transliteration patterns
        self._initialize_regional_patterns()
        
        # Import dictionaries from files
        self._import_dictionaries()
        
        # Initialize VariantGenerationService for additional variant generation
        try:
            from .variant_generation_service import VariantGenerationService
            self.variant_service = VariantGenerationService()
            logger.info("VariantGenerationService initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize VariantGenerationService: {e}")
            self.variant_service = None
        
        # Initialize enhanced LanguageDetectionService
        try:
            from .language_detection_service import LanguageDetectionService
            self.language_detection_service = LanguageDetectionService()
            logger.info("Enhanced LanguageDetectionService initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize LanguageDetectionService: {e}")
            self.language_detection_service = None
        
        logger.info("AdvancedNormalizationService initialized successfully")
    
    def _initialize_language_resources(self):
        """Initialize language-specific models and resources"""
        self.nlp_models = {}
        self.stemmers = {}
        self.stop_words = {}
        
        # English resources
        try:
            self.nlp_models['en'] = spacy.load("en_core_web_sm")
            self.stemmers['en'] = PorterStemmer()
            self.stop_words['en'] = set(stopwords.words('english'))
        except OSError:
            logger.warning("English SpaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp_models['en'] = None
        
        # Russian resources
        try:
            self.nlp_models['ru'] = spacy.load("ru_core_news_sm")
            self.stemmers['ru'] = SnowballStemmer('russian')
            self.stop_words['ru'] = set(stopwords.words('russian'))
        except OSError:
            logger.warning("Russian SpaCy model not found. Install with: python -m spacy download ru_core_news_sm")
            self.nlp_models['ru'] = None
        
        # Ukrainian resources (proper Ukrainian support)
        try:
            self.nlp_models['uk'] = spacy.load("uk_core_news_sm")
            # Use Ukrainian stemmer instead of Russian
            try:
                self.stemmers['uk'] = SnowballStemmer('ukrainian')
            except:
                # Fallback to Russian if Ukrainian is not available
                self.stemmers['uk'] = SnowballStemmer('russian')
                logger.warning("Ukrainian stemmer not available, using Russian as fallback")
            
            # Ukrainian stop words (first try Ukrainian, then Russian as fallback)
            try:
                self.stop_words['uk'] = set(stopwords.words('russian'))  # Use Russian as fallback
            except:
                self.stop_words['uk'] = set(stopwords.words('russian'))
                logger.warning("Ukrainian stopwords not available, using Russian as fallback")
                
        except OSError:
            logger.warning("Ukrainian SpaCy model not found. Using Russian as fallback")
            self.nlp_models['uk'] = self.nlp_models.get('ru')
            self.stemmers['uk'] = self.stemmers.get('ru')
            self.stop_words['uk'] = self.stop_words.get('ru', set())
    
    def _initialize_pymorphy3(self):
        """Initialize pymorphy3 morphological analyzers"""
        try:
            self.ru_morph = MorphAnalyzer(lang='ru')
            logger.info("Russian pymorphy3 analyzer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Russian pymorphy3: {e}")
            self.ru_morph = None
        
        try:
            # Try to create Ukrainian analyzer with Ukrainian dictionaries
            self.uk_morph = MorphAnalyzer(lang='uk')
            logger.info("Ukrainian pymorphy3 analyzer with Ukrainian dictionaries initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Ukrainian pymorphy3: {e}")
            # If Ukrainian is not available, use Russian as fallback
            # but with a warning about inaccuracies
            if self.ru_morph:
                self.uk_morph = self.ru_morph
                logger.warning("Using Russian pymorphy3 as fallback for Ukrainian. Install pymorphy3-dicts-uk for proper Ukrainian support.")
            else:
                self.uk_morph = None
    
    def _initialize_regional_patterns(self):
        """Initialize regional transliteration patterns"""
        # Regional transliteration patterns for different countries
        self.regional_patterns = {}
        
        # Phonetic similarity patterns
        self.phonetic_patterns = {}
    
    def _detect_language(self, text: str) -> str:
        """Automatic language detection for text"""
        try:
            detected_lang = detect(text)
            # Map detected language to supported languages
            lang_mapping = {
                'en': 'en',
                'ru': 'ru', 
                'uk': 'uk',
                'be': 'by',  # Belarusian -> Belarus
                'kk': 'kz',  # Kazakh -> Kazakhstan
                'ky': 'kg',  # Kyrgyz -> Kyrgyzstan
                'tg': 'tj',  # Tajik -> Tajikistan
                'uz': 'uz',  # Uzbek -> Uzbekistan
            }
            return lang_mapping.get(detected_lang, 'en')
        except LangDetectException:
            return 'en'
    
    def _clean_text(self, text: str, preserve_names: bool = True) -> str:
        """Basic text cleaning with name preservation"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        if preserve_names:
            # For names, preserve dots, hyphens, and apostrophes
            # Dots for initials (I.I. Ivanov)
            # Hyphens for compound names (Jean-Pierre)
            # Apostrophes for names (O'Connor, D'Artagnan)
            text = re.sub(r'[^\w\s\.\-\']', ' ', text)
        else:
            # Remove special characters but keep letters, numbers, spaces
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _normalize_unicode(self, text: str) -> str:
        """Unicode character normalization"""
        # Convert to ASCII where possible
        text = unidecode(text)
        
        # Handle specific characters for different languages
        text = text.replace('ё', 'е')  # Russian yo -> e
        text = text.replace('Ё', 'Е')
        
        return text
    
    def _analyze_names_with_morphology(self, tokens: List[str], language: str) -> List[Dict[str, Any]]:
        """Analyze names using morphology"""
        analyzed_names = []
        
        for token in tokens:
            if self._is_potential_name(token):
                analysis = self._analyze_single_name(token, language)
                if analysis:
                    analyzed_names.append(analysis)
        
        return analyzed_names
    
    def _is_potential_name(self, token: str) -> bool:
        """Check if token can be a name"""
        # Simple rules for determining potential names
        if len(token) < 2:
            return False
        
        # Check for capital letter (capitalization) - important for names
        if not token[0].isupper():
            return False
        
        # Check for presence of Ukrainian/Russian characters
        ukrainian_chars = set('іїєґІЇЄҐ')
        russian_chars = set('ёъыэЁЪЫЭ')
        
        if any(char in ukrainian_chars or char in russian_chars for char in token):
            return True
        
        # Check for presence of typical name endings
        name_endings = ['ов', 'ев', 'ин', 'ын', 'ко', 'енко', 'чук', 'юк', 'ак', 'ик', 'ич', 'ович', 'евич']
        if any(token.lower().endswith(ending) for ending in name_endings):
            return True
        
        # For Latin names, check for letters and capitalization
        if token[0].isupper() and any(char.isalpha() for char in token):
            return True
        
        return False
    
    def _analyze_single_name(self, name: str, language: str) -> Optional[Dict[str, Any]]:
        """Analyze individual name"""
        try:
            if language in ['uk', 'ru']:
                if language == 'uk':
                    # For Ukrainian language, use Ukrainian analyzer
                    uk_analysis = self.uk_morphology.analyze_name(name, language)
                    
                    # Check that analysis is successful
                    if not uk_analysis:
                        return self._basic_name_analysis(name, language)
                    
                    # Add total_forms if it doesn't exist
                    if 'total_forms' not in uk_analysis:
                        uk_analysis['total_forms'] = 0
                    
                    # Additionally analyze through pymorphy3 if available
                    if hasattr(self.uk_morphology, 'morph_analyzer'):
                        pymorphy_analysis = self._analyze_with_pymorphy(name, language)
                        if pymorphy_analysis:
                            # Combine results
                            uk_analysis['pymorphy_analysis'] = pymorphy_analysis
                            uk_analysis['total_forms'] += len(pymorphy_analysis.get('declensions', []))
                    
                    return uk_analysis
                elif language == 'ru':
                    # For Russian language, use Russian analyzer
                    ru_analysis = self.ru_morphology.analyze_name(name, language)
                    
                    # Check that analysis is successful
                    if not ru_analysis:
                        return self._basic_name_analysis(name, language)
                    
                    # Add total_forms if it doesn't exist
                    if 'total_forms' not in ru_analysis:
                        ru_analysis['total_forms'] = 0
                    
                    # Additionally analyze through pymorphy3 if available
                    if hasattr(self.ru_morphology, 'morph_analyzer'):
                        pymorphy_analysis = self._analyze_with_pymorphy(name, language)
                        if pymorphy_analysis:
                            # Combine results
                            ru_analysis['pymorphy_analysis'] = pymorphy_analysis
                            ru_analysis['total_forms'] += len(pymorphy_analysis.get('declensions', []))
                    
                    return ru_analysis
            else:
                # For other languages, use basic analysis
                return self._basic_name_analysis(name, language)
                
        except Exception as e:
            self.logger.warning(f"Failed to analyze name '{name}': {e}")
            return self._basic_name_analysis(name, language)
    
    def _analyze_with_pymorphy(self, name: str, language: str) -> Dict[str, Any]:
        """Analyze name through pymorphy3"""
        # Use proper morphological analyzers
        if language == 'ru' and hasattr(self, 'ru_morphology'):
            morph_analyzer = self.ru_morphology.morph_analyzer
        elif language == 'uk' and hasattr(self, 'uk_morphology'):
            morph_analyzer = self.uk_morphology.morph_analyzer
        else:
            return self._basic_name_analysis(name, language)
        
        if not morph_analyzer:
            return self._basic_name_analysis(name, language)
        
        try:
            parsed = morph_analyzer.parse(name)
            if not parsed:
                return self._basic_name_analysis(name, language)
            
            best_parse = parsed[0]
            tag = best_parse.tag
            
            # 🚨 CRITICAL FIX: Context-dependent lemmatization
            is_surname = 'Surn' in str(tag)
            
            if is_surname:
                # For surnames, do NOT use normal_form, which can be a name
                # Instead, take the form in nominative case
                nominative_form = best_parse.inflect({'nomn'})
                normal_form = nominative_form.word if nominative_form else name.lower()
            else:
                # For names, keep standard behavior
                normal_form = best_parse.normal_form
            
            gender = self._extract_gender_from_pymorphy(best_parse)
            
            # Generate declensions
            declensions = self._generate_pymorphy_declensions(best_parse)
            
            # Generate transliterations
            transliterations = self._generate_regional_transliterations(name, language)
            
            return {
                'name': name,
                'normal_form': normal_form,
                'gender': gender,
                'declensions': declensions,
                'transliterations': transliterations,
                'total_forms': len(declensions) + len(transliterations) + 1,
                'is_surname': is_surname  # Add flag for further logic
            }
            
        except Exception as e:
            self.logger.warning(f"pymorphy3 analysis failed for '{name}': {e}")
            return self._basic_name_analysis(name, language)
    
    def _extract_gender_from_pymorphy(self, parsed_word) -> str:
        """Extract gender from pymorphy3 result"""
        try:
            if 'masc' in parsed_word.tag:
                return 'masc'
            elif 'femn' in parsed_word.tag:
                return 'femn'
            elif 'neut' in parsed_word.tag:
                return 'neut'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def _generate_pymorphy_declensions(self, parsed_word) -> List[str]:
        """Generate declensions through pymorphy3"""
        declensions = []
        
        try:
            # Generate different forms for different cases
            cases = ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
            
            for case in cases:
                try:
                    form = parsed_word.inflect({case})
                    if form and form.word not in declensions:
                        declensions.append(form.word)
                except:
                    continue
                    
        except Exception as e:
            self.logger.warning(f"Failed to generate declensions: {e}")
        
        return declensions
    
    def _basic_name_analysis(self, name: str, language: str) -> Dict[str, Any]:
        """Basic name analysis without morphology"""
        return {
            'name': name,
            'normal_form': name,
            'gender': 'unknown',
            'declensions': [],
            'transliterations': self._generate_regional_transliterations(name, language),
            'total_forms': 1
        }
    
    def _generate_regional_transliterations(self, name: str, language: str) -> List[str]:
        """Generate regional transliterations"""
        if not name:
            return []
            
        transliterations = []
        
        # Basic transliteration
        base_translit = self._basic_transliterate(name)
        if base_translit != name:
            transliterations.append(base_translit)
        
        # Regional variants
        for region, char_map in self.regional_patterns.items():
            if region == 'standards':
                for std_name, std_map in char_map.items():
                    regional_translit = self._apply_regional_transliteration(name, std_map)
                    if regional_translit != name and regional_translit not in transliterations:
                        transliterations.append(regional_translit)
            else:
                regional_translit = self._apply_regional_transliteration(name, char_map)
                if regional_translit != name and regional_translit not in transliterations:
                    transliterations.append(regional_translit)
        
        # Phonetic variants
        phonetic_variants = self._generate_phonetic_variants(name)
        transliterations.extend(phonetic_variants)
        
        return list(set(transliterations))
    
    def _basic_transliterate(self, text: str) -> str:
        """Basic transliteration of Cyrillic to Latin"""
        if not text:
            return ''
            
        cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'y', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'і': 'i', 'ї': 'yi', 'є': 'ye', 'ґ': 'g'
        }
        
        result = ''
        for char in text:
            result += cyrillic_to_latin.get(char.lower(), char)
        
        return result
    
    def _apply_regional_transliteration(self, text: str, char_map: Dict[str, str]) -> str:
        """Apply regional transliteration"""
        result = text
        for cyr_char, lat_char in char_map.items():
            result = result.replace(cyr_char, lat_char)
            result = result.replace(cyr_char.upper(), lat_char.upper())
        return result
    
    def _generate_phonetic_variants(self, name: str) -> List[str]:
        """Generate phonetic variants"""
        variants = []
        
        # Replace similar sounds
        for pattern, alternatives in self.phonetic_patterns.items():
            if pattern in name.lower():
                for alt in alternatives:
                    if alt != pattern:
                        variant = name.lower().replace(pattern, alt)
                        variants.append(variant)
        
        return variants
    
    async def normalize_advanced(
        self,
        text: str,
        language: str = 'auto',
        enable_morphology: bool = True,
        enable_transliterations: bool = True,
        enable_phonetic_variants: bool = True,
        preserve_names: bool = True,
        clean_unicode: bool = True
    ) -> Dict[str, Any]:
        """
        Advanced text normalization with morphology and transliterations
        
        Args:
            text: Input text
            language: Text language ('en', 'ru', 'uk', 'auto')
            enable_morphology: Enable morphological analysis
            enable_transliterations: Enable transliterations
            enable_phonetic_variants: Enable phonetic variants
            preserve_names: Preserve names and surnames
            clean_unicode: Clean Unicode characters
            
        Returns:
            Dict with advanced normalization results
        """
        if not text or not text.strip():
            return {
                'original_text': text,
                'normalized': '',
                'tokens': [],
                'language': language,
                'names_analysis': [],
                'token_variants': {},
                'total_variants': 0,
                'processing_details': {},
                'errors': []
            }
        
        original_text = text
        
        # Automatic language detection through enhanced service
        if language == 'auto':
            if self.language_detection_service:
                try:
                    detection_result = self.language_detection_service.detect_language(text)
                    language = detection_result.get('language', 'en')
                    self.logger.info(f"Enhanced language detection: {language} (confidence: {detection_result.get('confidence', 0):.2f})")
                except Exception as e:
                    self.logger.warning(f"Enhanced language detection error: {e}")
                    language = self._detect_language(text)
            else:
                language = self._detect_language(text)
        
        # Basic cleaning
        errors = []
        try:
            cleaned_text = self._clean_text(text, preserve_names)
        except Exception as e:
            self.logger.warning(f"Text cleaning error: {e}")
            cleaned_text = text  # Use original text as fallback
            errors.append(f"Text cleaning error: {e}")
        
        # Unicode normalization
        if clean_unicode:
            try:
                cleaned_text = self._normalize_unicode(cleaned_text)
            except Exception as e:
                self.logger.warning(f"Unicode normalization error: {e}")
                errors.append(f"Unicode normalization error: {e}")
                # Continue with cleaned text
        else:
            # If clean_unicode=False, preserve original text
            # so VariantGenerationService can properly analyze Cyrillic names
            pass
        
        # Tokenization
        tokens = self._tokenize_with_spacy(cleaned_text, language)
        
        # Name analysis with morphology through VariantGenerationService (HEART OF THE SYSTEM)
        names_analysis = []
        
        if enable_morphology and self.variant_service:
            try:
                # Use powerful analysis from VariantGenerationService
                variant_analysis = self.variant_service.analyze_names(cleaned_text, language)
                if variant_analysis and variant_analysis.get('analyzed_names'):
                    names_analysis = variant_analysis['analyzed_names']
                    self.logger.info(f"Morphological analysis found {len(names_analysis)} names")
                else:
                    # Fallback to internal method
                    names_analysis = self._analyze_names_with_morphology(tokens, language)
                    self.logger.debug("Used fallback morphological analysis")
            except Exception as e:
                self.logger.warning(f"Error in morphological analysis: {e}")
                # Fallback to internal method
                names_analysis = self._analyze_names_with_morphology(tokens, language)
        elif enable_morphology and not self.variant_service:
            # Fallback to internal method if VariantGenerationService is not available
            names_analysis = self._analyze_names_with_morphology(tokens, language)
            self.logger.debug("VariantGenerationService not available, used fallback")
        else:
            # Morphology disabled - don't analyze names
            names_analysis = []
            self.logger.debug("Morphological analysis disabled")
        
        # Create variants dictionary for each token (ELIMINATING COMBINATORIAL EXPLOSION)
        token_variants = {}
        total_variants = 0
        
        # Add original tokens
        for token in tokens:
            if token not in token_variants:
                token_variants[token] = set()
            token_variants[token].add(token)
            total_variants += 1
        
        # Collect variants for each token separately
        for analysis in names_analysis:
            original_name = analysis.get('name', '')
            if not original_name:
                continue
                
            # Find matching token
            matching_token = None
            for token in tokens:
                if token.lower() in original_name.lower() or original_name.lower() in token.lower():
                    matching_token = token
                    break
            
            if not matching_token:
                continue
                
            # Add variants for this token
            if matching_token not in token_variants:
                token_variants[matching_token] = set()
            
            # Cases
            if enable_morphology:
                declensions = analysis.get('declensions', [])
                token_variants[matching_token].update(declensions)
                total_variants += len(declensions)
                
                # Diminutive forms
                diminutives = analysis.get('diminutives', [])
                token_variants[matching_token].update(diminutives)
                total_variants += len(diminutives)
                
                # All forms (if available)
                all_forms = analysis.get('all_forms', [])
                token_variants[matching_token].update(all_forms)
                total_variants += len(all_forms)
                
                # Normal form
                normal_form = analysis.get('normal_form', '')
                if normal_form:
                    token_variants[matching_token].add(normal_form)
                    total_variants += 1
                
                # Add original name
                token_variants[matching_token].add(original_name)
                total_variants += 1
            
            # Add transliterations
            if enable_transliterations:
                transliterations = analysis.get('transliterations', [])
                token_variants[matching_token].update(transliterations)
                total_variants += len(transliterations)
            
            # Add phonetic variants
            if enable_phonetic_variants:
                phonetic_variants = analysis.get('phonetic_variants', [])
                token_variants[matching_token].update(phonetic_variants)
                total_variants += len(phonetic_variants)
            
            # Add other variants
            variants = analysis.get('variants', [])
            token_variants[matching_token].update(variants)
            total_variants += len(variants)
        
        # Add variants from VariantGenerationService (COMPREHENSIVE GENERATION)
        if self.variant_service:
            try:
                # Comprehensive variant generation
                variant_result = self.variant_service.generate_comprehensive_variants(cleaned_text, language)
                if variant_result:
                    # Add variants to corresponding tokens
                    for token in tokens:
                        if token not in token_variants:
                            token_variants[token] = set()
                        
                        # Transliterations
                        translits = variant_result.get('transliterations', set())
                        for translit in translits:
                            if token.lower() in translit.lower() or translit.lower() in token.lower():
                                token_variants[token].add(translit)
                                total_variants += 1
                        
                        # Visual similarities
                        visual = variant_result.get('visual_similarities', set())
                        for visual_var in visual:
                            if token.lower() in visual_var.lower() or visual_var.lower() in token.lower():
                                token_variants[token].add(visual_var)
                                total_variants += 1
                        
                        # Typo errors
                        typos = variant_result.get('typo_variants', set())
                        for typo in typos:
                            if token.lower() in typo.lower() or typo.lower() in token.lower():
                                token_variants[token].add(typo)
                                total_variants += 1
                        
                        # Phonetic variants
                        phonetic = variant_result.get('phonetic_variants', set())
                        for phonetic_var in phonetic:
                            if token.lower() in phonetic_var.lower() or phonetic_var.lower() in token.lower():
                                token_variants[token].add(phonetic_var)
                                total_variants += 1
                        
                        # Morphological variants
                        morphological = variant_result.get('morphological_variants', set())
                        for morph_var in morphological:
                            if token.lower() in morph_var.lower() or morph_var.lower() in token.lower():
                                token_variants[token].add(morph_var)
                                total_variants += 1
                    
                    self.logger.debug(f"Comprehensive generation added variants for {len(tokens)} tokens")
                    
            except Exception as e:
                self.logger.warning(f"Error generating variants: {e}")
        
        # Final normalization
        normalized_text = ' '.join(tokens)
        
        # Convert set to list for JSON serialization
        token_variants_serializable = {}
        for token, variants in token_variants.items():
            # Structure variants by type
            structured_variants = {
                'transliterations': [],
                'visual_similarities': [],
                'typo_variants': [],
                'phonetic_variants': [],
                'morphological_variants': [],
                'all_variants': list(variants)
            }
            
            # Try to categorize variants by type
            for variant in variants:
                variant_lower = variant.lower()
                token_lower = token.lower()
                
                # Simple categorization logic
                if variant_lower != token_lower:
                    if '_' in variant_lower:
                        structured_variants['transliterations'].append(variant)
                    elif len(variant) == len(token):
                        structured_variants['visual_similarities'].append(variant)
                    else:
                        structured_variants['morphological_variants'].append(variant)
            
            token_variants_serializable[token] = structured_variants
        
        return {
            'original_text': original_text,
            'normalized': normalized_text,
            'tokens': tokens,
            'language': language,
            'names_analysis': names_analysis,
            'token_variants': token_variants_serializable,
            'total_variants': total_variants,
            'processing_details': {
                'morphology_enabled': enable_morphology,
                'transliterations_enabled': enable_transliterations,
                'phonetic_variants_enabled': enable_phonetic_variants,
                'names_found': len(names_analysis),
                'tokens_processed': len(tokens)
            },
            'errors': errors if errors else []
        }
    
    def _tokenize_with_spacy(self, text: str, language: str) -> List[str]:
        """Tokenization using SpaCy"""
        if not self.nlp_models.get(language):
            return word_tokenize(text)
        
        try:
            doc = self.nlp_models[language](text)
            tokens = []
            for token in doc:
                # Keep only meaningful tokens
                if not token.is_space and not token.is_punct:
                    tokens.append(token.text)  # Preserve original case
            return tokens
        except Exception as e:
            logger.warning(f"SpaCy tokenization failed for {language}: {e}")
            return word_tokenize(text)
    
    async def normalize_batch_advanced(
        self,
        texts: List[str],
        language: str = 'auto',
        enable_morphology: bool = True,
        enable_transliterations: bool = True,
        enable_phonetic_variants: bool = True
    ) -> List[Dict[str, Any]]:
        """Advanced normalization of text list"""
        results = []
        for text in texts:
            result = await self.normalize_advanced(
                text=text,
                language=language,
                enable_morphology=enable_morphology,
                enable_transliterations=enable_transliterations,
                enable_phonetic_variants=enable_phonetic_variants
            )
            results.append(result)
        return results
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.nlp_models.keys())
    
    def get_regional_patterns(self) -> Dict[str, Dict[str, str]]:
        """Get regional transliteration patterns"""
        return self.regional_patterns
    
    def get_phonetic_patterns(self) -> Dict[str, List[str]]:
        """Get phonetic patterns"""
        return self.phonetic_patterns
    
    def _import_dictionaries(self):
        """Import dictionaries from files"""
        try:
            # Import regional patterns
            from ..data.dicts.regional_patterns import REGIONAL_PATTERNS, ALL_BASE_PATTERNS
            self.regional_patterns = REGIONAL_PATTERNS
            self.base_transliteration = ALL_BASE_PATTERNS
            
            # Import phonetic patterns
            from ..data.dicts.phonetic_patterns import ALL_PHONETIC_PATTERNS
            self.phonetic_patterns = ALL_PHONETIC_PATTERNS
            
            logger.info("Dictionaries imported successfully from files")
            
        except ImportError as e:
            logger.warning(f"Failed to import dictionaries from files: {e}")
            logger.info("Using fallback dictionaries")
            
            # Fallback patterns
            self.regional_patterns = {
                'uk': {'і': 'i', 'ї': 'yi', 'є': 'ye', 'ґ': 'g'},
                'ru': {'ё': 'e', 'ъ': '', 'ь': ''},
                'en': {'ch': 'ch', 'sh': 'sh', 'zh': 'zh'}
            }
            
            self.phonetic_patterns = {
                'ch': ['ch', 'tch', 'cz', 'ч'],
                'sh': ['sh', 'sch', 'sz', 'ш'],
                'zh': ['zh', 'j', 'g', 'ж']
            }
            
            self.base_transliteration = {
                'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'д': 'd', 'е': 'e',
                'ж': 'zh', 'з': 'z', 'и': 'y', 'й': 'i', 'к': 'k', 'л': 'l'
            }
    
    def is_ukrainian_support_available(self) -> Dict[str, bool]:
        """Check availability of Ukrainian support"""
        return {
            'spacy_model': self.nlp_models.get('uk') is not None,
            'pymorphy3_uk': self.uk_morph is not None and self.uk_morph != self.ru_morph,
            'ukrainian_stemmer': hasattr(self.stemmers.get('uk'), '__class__') and 'ukrainian' in str(self.stemmers.get('uk').__class__),
            'ukrainian_stopwords': 'ukrainian' in str(self.stop_words.get('uk', set()))
        }
    
    def get_language_support_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about language support"""
        info = {}
        
        for lang in ['en', 'ru', 'uk']:
            info[lang] = {
                'spacy_model': self.nlp_models.get(lang) is not None,
                'stemmer': self.stemmers.get(lang) is not None,
                'stop_words': len(self.stop_words.get(lang, set())) > 0,
                'pymorphy3': self.ru_morph is not None if lang in ['ru', 'uk'] else False
            }
            
            # Special check for Ukrainian language
            if lang == 'uk':
                info[lang]['pymorphy3_uk'] = self.uk_morph is not None and self.uk_morph != self.ru_morph
                info[lang]['ukrainian_morphology'] = hasattr(self, 'uk_morphology')
        
        return info
