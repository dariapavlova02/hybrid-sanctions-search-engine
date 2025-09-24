"""
Sanctions data loader for fuzzy search.
Loads and caches sanctions lists from various sources for fuzzy matching.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio
import hashlib

try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

from ...utils.logging_config import get_logger
from ...utils.profiling import profile_function


@dataclass
class SanctionEntry:
    """Single sanctions list entry."""
    name: str
    entity_type: str  # "person", "organization"
    source: str  # "ofac", "eu", "uk", etc.
    list_name: str  # "SDN", "EU Sanctions", etc.
    aliases: List[str] = None
    birth_date: Optional[str] = None
    nationality: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class SanctionsDataset:
    """Complete sanctions dataset for fuzzy matching."""
    persons: List[SanctionEntry]
    organizations: List[SanctionEntry]
    all_names: List[str]  # All names + aliases for fuzzy search
    name_to_entry: Dict[str, SanctionEntry]  # Quick lookup
    loaded_at: datetime
    sources: List[str]
    total_entries: int

    def get_person_names(self) -> List[str]:
        """Get all person names including aliases."""
        names = []
        for entry in self.persons:
            names.append(entry.name)
            names.extend(entry.aliases)
        return names

    def get_org_names(self) -> List[str]:
        """Get all organization names including aliases."""
        names = []
        for entry in self.organizations:
            names.append(entry.name)
            names.extend(entry.aliases)
        return names


class SanctionsDataLoader:
    """Loads and manages sanctions data for fuzzy search."""

    def __init__(self, data_dir: Optional[Path] = None, cache_ttl_hours: int = 24):
        self.logger = get_logger(__name__)

        # Data directory - default to project data folder
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent.parent / "data" / "sanctions"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self._cached_dataset: Optional[SanctionsDataset] = None
        self._cache_file = self.data_dir / "sanctions_cache.json"

        self.logger.info(f"SanctionsDataLoader initialized with data_dir: {self.data_dir}")

    @profile_function("sanctions.load_dataset")
    async def load_dataset(self, force_reload: bool = False) -> SanctionsDataset:
        """
        Load complete sanctions dataset.

        Args:
            force_reload: Force reload from source files

        Returns:
            Complete sanctions dataset
        """
        # Check cache first
        if not force_reload and self._cached_dataset:
            if datetime.now() - self._cached_dataset.loaded_at < self.cache_ttl:
                self.logger.debug("Using cached sanctions dataset")
                return self._cached_dataset

        # Try to load from cache file
        if not force_reload and await self._load_from_cache():
            return self._cached_dataset

        # Load from source files
        self.logger.info("Loading sanctions data from source files...")
        dataset = await self._load_from_sources()

        # Cache the dataset
        await self._save_to_cache(dataset)
        self._cached_dataset = dataset

        self.logger.info(f"Loaded {dataset.total_entries} sanctions entries from {len(dataset.sources)} sources")
        return dataset

    async def _load_from_cache(self) -> bool:
        """Try to load dataset from cache file."""
        try:
            if not self._cache_file.exists():
                return False

            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self._cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.loads(await f.read())
            else:
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

            # Check cache age
            loaded_at = datetime.fromisoformat(cache_data['loaded_at'])
            if datetime.now() - loaded_at > self.cache_ttl:
                self.logger.debug("Cache expired")
                return False

            # Reconstruct dataset
            persons = [SanctionEntry(**entry) for entry in cache_data['persons']]
            organizations = [SanctionEntry(**entry) for entry in cache_data['organizations']]

            self._cached_dataset = SanctionsDataset(
                persons=persons,
                organizations=organizations,
                all_names=cache_data['all_names'],
                name_to_entry=cache_data['name_to_entry'],
                loaded_at=loaded_at,
                sources=cache_data['sources'],
                total_entries=cache_data['total_entries']
            )

            # Rebuild name_to_entry mapping with actual objects
            name_to_entry = {}
            all_entries = persons + organizations
            for entry in all_entries:
                name_to_entry[entry.name] = entry
                for alias in entry.aliases:
                    name_to_entry[alias] = entry

            self._cached_dataset.name_to_entry = name_to_entry

            self.logger.debug("Successfully loaded from cache")
            return True

        except Exception as e:
            self.logger.warning(f"Failed to load from cache: {e}")
            return False

    async def _save_to_cache(self, dataset: SanctionsDataset):
        """Save dataset to cache file."""
        try:
            # Convert to JSON-serializable format
            cache_data = {
                'persons': [self._entry_to_dict(entry) for entry in dataset.persons],
                'organizations': [self._entry_to_dict(entry) for entry in dataset.organizations],
                'all_names': dataset.all_names,
                'name_to_entry': {name: self._entry_to_dict(entry) for name, entry in dataset.name_to_entry.items()},
                'loaded_at': dataset.loaded_at.isoformat(),
                'sources': dataset.sources,
                'total_entries': dataset.total_entries
            }

            if AIOFILES_AVAILABLE:
                async with aiofiles.open(self._cache_file, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(cache_data, indent=2, ensure_ascii=False))
            else:
                with open(self._cache_file, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f, indent=2, ensure_ascii=False)

            self.logger.debug("Successfully saved to cache")

        except Exception as e:
            self.logger.warning(f"Failed to save to cache: {e}")

    def _entry_to_dict(self, entry: SanctionEntry) -> Dict[str, Any]:
        """Convert SanctionEntry to dictionary."""
        return {
            'name': entry.name,
            'entity_type': entry.entity_type,
            'source': entry.source,
            'list_name': entry.list_name,
            'aliases': entry.aliases,
            'birth_date': entry.birth_date,
            'nationality': entry.nationality,
            'metadata': entry.metadata
        }

    async def _load_from_sources(self) -> SanctionsDataset:
        """Load sanctions data from various sources."""
        all_entries = []
        sources = []

        # Load from different file formats and sources
        loaders = [
            self._load_sanctioned_persons,   # Ukrainian sanctions persons
            self._load_sanctioned_companies, # Ukrainian sanctions companies
            self._load_terrorism_blacklist,  # Terrorism blacklist
            self._load_sample_data,          # Sample data for testing
            self._load_ofac_sdn,             # OFAC SDN list
            self._load_eu_sanctions,         # EU sanctions
            self._load_uk_sanctions,         # UK sanctions
            self._load_custom_lists,         # Custom sanctions lists
        ]

        for loader in loaders:
            try:
                entries, source_name = await loader()
                if entries:
                    all_entries.extend(entries)
                    sources.append(source_name)
                    self.logger.debug(f"Loaded {len(entries)} entries from {source_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load from {loader.__name__}: {e}")

        # Split by type
        persons = [e for e in all_entries if e.entity_type == "person"]
        organizations = [e for e in all_entries if e.entity_type == "organization"]

        # Build name indexes
        all_names = []
        name_to_entry = {}

        for entry in all_entries:
            all_names.append(entry.name)
            name_to_entry[entry.name] = entry

            for alias in entry.aliases:
                all_names.append(alias)
                name_to_entry[alias] = entry

        dataset = SanctionsDataset(
            persons=persons,
            organizations=organizations,
            all_names=list(set(all_names)),  # Remove duplicates
            name_to_entry=name_to_entry,
            loaded_at=datetime.now(),
            sources=sources,
            total_entries=len(all_entries)
        )

        return dataset

    async def _load_sample_data(self) -> Tuple[List[SanctionEntry], str]:
        """Load sample sanctions data for testing."""
        entries = [
            # Ukrainian/Russian politicians and oligarchs
            SanctionEntry(
                name="Петро Порошенко",
                entity_type="person",
                source="sample",
                list_name="Sample List",
                aliases=["Petro Poroshenko", "Порошенко Петро Олексійович"],
                nationality="Ukraine"
            ),
            SanctionEntry(
                name="Владимир Путин",
                entity_type="person",
                source="sample",
                list_name="Sample List",
                aliases=["Vladimir Putin", "Путин Владимир Владимирович"],
                birth_date="1952-10-07",
                nationality="Russia"
            ),
            SanctionEntry(
                name="Ігор Коломойський",
                entity_type="person",
                source="sample",
                list_name="Sample List",
                aliases=["Igor Kolomoisky", "Коломойський Ігор Валерійович"],
                nationality="Ukraine"
            ),
            SanctionEntry(
                name="Рінат Ахметов",
                entity_type="person",
                source="sample",
                list_name="Sample List",
                aliases=["Rinat Akhmetov", "Ахметов Рінат Леонідович"],
                nationality="Ukraine"
            ),
            SanctionEntry(
                name="Алексей Навальный",
                entity_type="person",
                source="sample",
                list_name="Sample List",
                aliases=["Alexei Navalny", "Навальный Алексей Анатольевич"],
                birth_date="1976-06-04",
                nationality="Russia"
            ),

            # Organizations
            SanctionEntry(
                name="Газпром",
                entity_type="organization",
                source="sample",
                list_name="Sample List",
                aliases=["Gazprom", "ПАО Газпром", "Gazprom PAO"]
            ),
            SanctionEntry(
                name="Роснефть",
                entity_type="organization",
                source="sample",
                list_name="Sample List",
                aliases=["Rosneft", "НК Роснефть", "Rosneft Oil Company"]
            ),
            SanctionEntry(
                name="Приватбанк",
                entity_type="organization",
                source="sample",
                list_name="Sample List",
                aliases=["PrivatBank", "АТ КБ ПриватБанк"]
            ),
        ]

        return entries, "Sample Data"

    async def _load_sanctioned_persons(self) -> Tuple[List[SanctionEntry], str]:
        """Load Ukrainian sanctioned persons data."""
        entries = []
        persons_file = self.data_dir / "sanctioned_persons.json"

        if not persons_file.exists():
            self.logger.debug("sanctioned_persons.json not found, skipping")
            return entries, "Ukrainian Persons"

        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(persons_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
            else:
                with open(persons_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            for item in data:
                # Extract aliases from different name fields
                aliases = []
                if item.get('name_ru') and item['name_ru'] != item['name']:
                    aliases.append(item['name_ru'])
                if item.get('name_en') and item['name_en'] != item['name']:
                    aliases.append(item['name_en'])

                # Create entry
                entry = SanctionEntry(
                    name=item.get('name', '').strip(),
                    entity_type="person",
                    source="ukrainian_sanctions",
                    list_name="Ukrainian Sanctioned Persons",
                    aliases=aliases,
                    birth_date=item.get('birthdate'),
                    nationality=None,  # Not provided in this format
                    metadata={
                        'person_id': item.get('person_id'),
                        'itn': item.get('itn'),
                        'status': item.get('status')
                    }
                )

                # Only add if we have a valid name
                if entry.name:
                    entries.append(entry)

            self.logger.info(f"Loaded {len(entries)} Ukrainian sanctioned persons")

        except Exception as e:
            self.logger.error(f"Error loading Ukrainian sanctioned persons: {e}")

        return entries, "Ukrainian Persons"

    async def _load_sanctioned_companies(self) -> Tuple[List[SanctionEntry], str]:
        """Load Ukrainian sanctioned companies data."""
        entries = []
        companies_file = self.data_dir / "sanctioned_companies.json"

        if not companies_file.exists():
            self.logger.debug("sanctioned_companies.json not found, skipping")
            return entries, "Ukrainian Companies"

        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(companies_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
            else:
                with open(companies_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            for item in data:
                # Create entry
                entry = SanctionEntry(
                    name=item.get('name', '').strip(),
                    entity_type="organization",
                    source="ukrainian_sanctions",
                    list_name="Ukrainian Sanctioned Companies",
                    aliases=[],  # No aliases in this format
                    birth_date=None,  # Not applicable for companies
                    nationality=None,  # Could extract from address
                    metadata={
                        'person_id': item.get('person_id'),
                        'tax_number': item.get('tax_number'),
                        'reg_number': item.get('reg_number'),
                        'address': item.get('address'),
                        'status': item.get('status')
                    }
                )

                # Only add if we have a valid name
                if entry.name:
                    entries.append(entry)

            self.logger.info(f"Loaded {len(entries)} Ukrainian sanctioned companies")

        except Exception as e:
            self.logger.error(f"Error loading Ukrainian sanctioned companies: {e}")

        return entries, "Ukrainian Companies"

    async def _load_terrorism_blacklist(self) -> Tuple[List[SanctionEntry], str]:
        """Load terrorism blacklist data."""
        entries = []
        blacklist_file = self.data_dir / "terrorism_black_list.json"

        if not blacklist_file.exists():
            self.logger.debug("terrorism_black_list.json not found, skipping")
            return entries, "Terrorism Blacklist"

        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
            else:
                with open(blacklist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            for item in data:
                # Extract name from aka_name
                name = item.get('aka_name', '').strip()
                if not name:
                    continue

                # Create entry
                entry = SanctionEntry(
                    name=name,
                    entity_type="person",  # Terrorism blacklist is typically persons
                    source="terrorism_blacklist",
                    list_name="Terrorism Blacklist",
                    metadata={
                        'date_entry': item.get('date_entry'),
                        'type_aka': item.get('type_aka'),
                        'quality_aka': item.get('quality_aka'),
                        'number_entry': item.get('number_entry')
                    }
                )

                entries.append(entry)

            self.logger.info(f"Loaded {len(entries)} terrorism blacklist entries")

        except Exception as e:
            self.logger.error(f"Error loading terrorism blacklist: {e}")

        return entries, "Terrorism Blacklist"

    async def _load_ofac_sdn(self) -> Tuple[List[SanctionEntry], str]:
        """Load OFAC SDN (Specially Designated Nationals) list."""
        entries = []
        sdn_file = self.data_dir / "ofac_sdn.json"

        if not sdn_file.exists():
            self.logger.debug("OFAC SDN file not found, skipping")
            return entries, "OFAC SDN"

        try:
            if AIOFILES_AVAILABLE:
                async with aiofiles.open(sdn_file, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
            else:
                with open(sdn_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

            for item in data.get('entries', []):
                entry = SanctionEntry(
                    name=item.get('name', ''),
                    entity_type=item.get('type', 'person').lower(),
                    source="ofac",
                    list_name="SDN",
                    aliases=item.get('aliases', []),
                    birth_date=item.get('birth_date'),
                    nationality=item.get('nationality'),
                    metadata=item.get('metadata')
                )
                entries.append(entry)

        except Exception as e:
            self.logger.error(f"Error loading OFAC SDN data: {e}")

        return entries, "OFAC SDN"

    async def _load_eu_sanctions(self) -> Tuple[List[SanctionEntry], str]:
        """Load EU sanctions list."""
        entries = []
        eu_file = self.data_dir / "eu_sanctions.json"

        if not eu_file.exists():
            self.logger.debug("EU sanctions file not found, skipping")
            return entries, "EU Sanctions"

        # Similar implementation to OFAC
        # TODO: Implement EU sanctions parsing

        return entries, "EU Sanctions"

    async def _load_uk_sanctions(self) -> Tuple[List[SanctionEntry], str]:
        """Load UK sanctions list."""
        entries = []
        uk_file = self.data_dir / "uk_sanctions.json"

        if not uk_file.exists():
            self.logger.debug("UK sanctions file not found, skipping")
            return entries, "UK Sanctions"

        # Similar implementation to OFAC
        # TODO: Implement UK sanctions parsing

        return entries, "UK Sanctions"

    async def _load_custom_lists(self) -> Tuple[List[SanctionEntry], str]:
        """Load custom sanctions lists."""
        entries = []

        # Look for custom JSON files in data directory
        custom_files = list(self.data_dir.glob("custom_*.json"))

        for custom_file in custom_files:
            try:
                if AIOFILES_AVAILABLE:
                    async with aiofiles.open(custom_file, 'r', encoding='utf-8') as f:
                        data = json.loads(await f.read())
                else:
                    with open(custom_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                for item in data.get('entries', []):
                    entry = SanctionEntry(
                        name=item.get('name', ''),
                        entity_type=item.get('type', 'person').lower(),
                        source="custom",
                        list_name=custom_file.stem,
                        aliases=item.get('aliases', []),
                        birth_date=item.get('birth_date'),
                        nationality=item.get('nationality'),
                        metadata=item.get('metadata')
                    )
                    entries.append(entry)

                self.logger.debug(f"Loaded {len(data.get('entries', []))} entries from {custom_file}")

            except Exception as e:
                self.logger.error(f"Error loading custom sanctions from {custom_file}: {e}")

        return entries, "Custom Lists"

    async def get_fuzzy_candidates(self, entity_type: Optional[str] = None) -> List[str]:
        """
        Get all names for fuzzy matching.

        Args:
            entity_type: Filter by 'person', 'organization', or None for all

        Returns:
            List of names for fuzzy matching
        """
        dataset = await self.load_dataset()

        if entity_type == "person":
            return dataset.get_person_names()
        elif entity_type == "organization":
            return dataset.get_org_names()
        else:
            return dataset.all_names

    async def find_entry(self, name: str) -> Optional[SanctionEntry]:
        """Find sanctions entry by exact name match."""
        dataset = await self.load_dataset()
        return dataset.name_to_entry.get(name)

    async def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics."""
        if not self._cached_dataset:
            dataset = await self.load_dataset()
        else:
            dataset = self._cached_dataset

        return {
            'total_entries': dataset.total_entries,
            'persons': len(dataset.persons),
            'organizations': len(dataset.organizations),
            'unique_names': len(dataset.all_names),
            'sources': dataset.sources,
            'loaded_at': dataset.loaded_at.isoformat(),
            'cache_age_hours': (datetime.now() - dataset.loaded_at).total_seconds() / 3600,
            'data_dir': str(self.data_dir)
        }

    async def clear_cache(self):
        """Clear cached data and force reload."""
        self._cached_dataset = None
        if self._cache_file.exists():
            self._cache_file.unlink()
        self.logger.info("Cache cleared")