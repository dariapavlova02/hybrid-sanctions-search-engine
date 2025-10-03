# Sanctions Pipeline Gap Analysis

**Дата:** 03.10.2025
**Проблема:** Проверка полноты автоматизации sanctions workflow

---

## 📋 Полный Workflow (из документации)

Согласно `docs/SANCTIONS_UPDATE_WORKFLOW.md` и `docs/DATA_PIPELINE.md`:

### ✅ Должно быть (5 шагов):

```bash
# Шаг 1: Замена исходных файлов
- Бэкап текущих sanctions JSON
- Копирование новых файлов

# Шаг 2: Генерация AC patterns
- export_high_recall_ac_patterns.py
- 4 tier'а (Tier 0-3)
- tier_limits поддержка
- Статистика и summary

# Шаг 3: Генерация векторов
- generate_vectors.py для persons
- generate_vectors.py для companies
- generate_vectors.py для terrorism
- Модель: paraphrase-multilingual-MiniLM-L12-v2 (384-dim)

# Шаг 4: Загрузка в Elasticsearch
- load_ac_patterns.py (AC patterns index)
- Bulk load векторов в vector indices
- Health checks
- Warmup queries

# Шаг 5: Templates (опционально)
- build_templates.py
- Генерация templates для дополнительной обработки
```

---

## 🔍 Что реально делает sanctions_pipeline.py

### Структура:

```python
sanctions_pipeline.py
├── Step 1: Prepare Data
│   └── prepare_sanctions_data.py
│       ├── Валидация входных файлов ✅
│       ├── Генерация AC patterns ⚠️ (неправильный метод)
│       ├── Генерация vectors ⚠️ (неправильный формат)
│       └── Deployment manifest ✅
│
└── Step 2: Deploy to ES
    └── deploy_to_elasticsearch.py
        ├── ES health checks ✅
        ├── Create AC patterns index ✅
        ├── Bulk load AC patterns ✅
        ├── Create vector indices ⚠️ (опционально)
        └── Warmup queries ✅
```

---

## ❌ Критические пробелы

### 1. **Отсутствует Шаг 1: Backup & Replace**

**Проблема:**
```bash
# Из документации (ДОЛЖНО БЫТЬ):
cp src/ai_service/data/sanctioned_persons.json src/ai_service/data/sanctioned_persons.json.backup
cp /path/to/new/sanctioned_persons.json src/ai_service/data/

# sanctions_pipeline.py:
❌ НЕТ - пользователь должен делать вручную
```

**Последствия:**
- Если генерация упадёт с ошибкой, откат данных невозможен
- Нет автоматизации замены файлов

**Решение:**
Добавить в `sanctions_pipeline.py` или `prepare_sanctions_data.py`:
```python
def backup_current_data(data_dir: Path, backup_dir: Path):
    """Backup current sanctions files"""
    files = [
        "sanctioned_persons.json",
        "sanctioned_companies.json",
        "terrorism_black_list.json"
    ]
    for filename in files:
        src = data_dir / filename
        dst = backup_dir / f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy(src, dst)
```

---

### 2. **Неправильная генерация AC patterns**

**Текущий код (`prepare_sanctions_data.py:129-142`):**
```python
for person in persons:
    try:
        patterns = generator.generate_patterns(  # ❌ НЕПРАВИЛЬНЫЙ метод
            person,
            entity_type="person",
            max_patterns_per_entity=max_patterns
        )
        all_patterns.extend(patterns)
```

**Правильный код (из `export_high_recall_ac_patterns.py:168`):**
```python
corpus = generator.generate_full_corpus(  # ✅ ПРАВИЛЬНО
    persons_file=args.persons_file,
    companies_file=args.companies_file,
    terrorism_file=args.terrorism_file
)
```

**Проблемы:**
- `generate_patterns()` - низкоуровневый метод, не генерирует полную статистику
- Нет tier distribution
- Нет правильной структуры метаданных
- Не используются `tier_limits`

**Доказательство:**
```python
# high_recall_ac_generator.py:2074-2089
def generate_full_corpus(self,
                       persons_file: str = None,
                       companies_file: str = None,
                       terrorism_file: str = None) -> Dict[str, Any]:
    """Generate full pattern corpus from sanctions data"""
    start_time = time.time()

    all_patterns = []
    stats = {
        "persons_processed": 0,
        "companies_processed": 0,
        "terrorism_processed": 0,
        "patterns_generated": 0,
        "tier_distribution": defaultdict(int),  # ✅ Правильная структура
        "processing_time": 0
    }
```

---

### 3. **Неправильная генерация векторов**

**Проблема 1: Формат файла**

`prepare_sanctions_data.py:223`:
```python
output_file = output_dir / f"vectors_{entity_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.npy"
```

Но `generate_vectors.py` генерирует **JSON**, не `.npy`:
```python
# generate_vectors.py:115-117
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(vectors, f, ensure_ascii=False, indent=2)  # ✅ JSON
```

**Проблема 2: Неправильные аргументы**

`prepare_sanctions_data.py:228-233`:
```python
result = subprocess.run([
    sys.executable,
    str(project_root / "scripts" / "generate_vectors.py"),
    "--input", str(filepath),     # ✅ OK
    "--output", str(output_file)  # ❌ .npy расширение
], capture_output=True, text=True, timeout=300)
```

`generate_vectors.py` ожидает:
```python
# generate_vectors.py:191-197
parser.add_argument("--input", type=Path, help="Input AC patterns file")  # ❌ НЕ sanctions JSON!
parser.add_argument("--output", type=Path, help="Output vectors file")
parser.add_argument("--max-patterns", type=int, default=10000, help="Maximum patterns to process")
parser.add_argument("--sample", action="store_true", help="Generate sample vectors instead")
parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                   help="Model name for embeddings")
```

**КРИТИЧЕСКОЕ НЕСООТВЕТСТВИЕ:**
- `prepare_sanctions_data.py` передаёт `sanctioned_persons.json` (исходные данные)
- `generate_vectors.py` ожидает **AC patterns JSON** (результат шага 2)

**Правильная логика (из документации):**
```bash
# Шаг 2: Генерация AC patterns
python scripts/export_high_recall_ac_patterns.py \
  --output high_recall_ac_patterns.json

# Шаг 3: Генерация векторов ИЗ AC PATTERNS
python scripts/generate_vectors.py \
  --input high_recall_ac_patterns.json \     # ✅ AC patterns, не sanctions!
  --output vectors_persons.json
```

---

### 4. **Отсутствует загрузка векторов в ES**

**Проблема:**

`deploy_to_elasticsearch.py` создаёт vector indices:
```python
# deploy_to_elasticsearch.py:428-432
if args.create_vector_indices:
    for entity_type in ['persons', 'companies', 'terrorism']:
        vector_index = f"{args.index_prefix}_vectors_{entity_type}"
        if not await create_vectors_index(es_host, vector_index):
            print(f"⚠️  Failed to create vectors index for {entity_type}")
```

Но **НЕ загружает векторные данные**! Индексы создаются пустыми.

**Должно быть:**
```python
# После создания индексов - ЗАГРУЗИТЬ векторы
await bulk_load_vectors(es_host, vector_index, vectors_file)
```

---

### 5. **Отсутствует поддержка tier_limits**

**Из документации:**
```bash
python scripts/export_high_recall_ac_patterns.py \
  --tier-limits 0:5,1:10,2:15,3:50  # ✅ Поддерживается
```

**`prepare_sanctions_data.py`:**
```python
# ❌ tier_limits вообще не поддерживается
parser.add_argument("--max-patterns", ...)  # Есть
# НЕТ: parser.add_argument("--tier-limits", ...)
```

---

### 6. **Отсутствует генерация templates**

**Из документации (Шаг 5):**
```bash
python src/ai_service/scripts/build_templates.py
```

**`sanctions_pipeline.py`:**
- Есть опция `--skip-templates` в `prepare_sanctions_data.py`
- Но `generate_templates()` вызывает `TemplateBuilder`, а НЕ `build_templates.py`
- Неясно, это тот же функционал или нет

---

## 📊 Сравнительная таблица покрытия

| Шаг | Документация | sanctions_pipeline.py | Статус | Критичность |
|-----|-------------|----------------------|--------|-------------|
| **1. Backup & Replace** | ✅ Обязательно | ❌ Отсутствует | **КРИТИЧНО** | 🔴 HIGH |
| **2. AC Patterns** | `export_high_recall_ac_patterns.py` | `prepare_sanctions_data.py` | ⚠️ Неправильно | 🔴 HIGH |
| 2a. tier_limits | ✅ Поддержка | ❌ Нет | **ОТСУТСТВУЕТ** | 🟡 MEDIUM |
| 2b. Tier distribution | ✅ Полная статистика | ❌ Частичная | **НЕПОЛНО** | 🟡 MEDIUM |
| **3. Vectors** | `generate_vectors.py` из AC patterns | `generate_vectors.py` из sanctions | ⚠️ Неправильно | 🔴 HIGH |
| 3a. Input | AC patterns JSON | ❌ Sanctions JSON | **НЕПРАВИЛЬНО** | 🔴 HIGH |
| 3b. Output format | JSON | ❌ .npy (но фактически JSON) | **НЕСООТВЕТСТВИЕ** | 🟡 MEDIUM |
| 3c. Model | MiniLM-L12-v2 (384-dim) | mpnet-base-v2 (768-dim) | **ДРУГАЯ МОДЕЛЬ** | 🟡 MEDIUM |
| **4. ES Deploy** | AC + Vectors | Только AC patterns | ⚠️ Неполно | 🔴 HIGH |
| 4a. AC patterns | ✅ Загрузка | ✅ Есть | ✅ OK | - |
| 4b. Vector indices | ✅ Создание + загрузка | ⚠️ Только создание | **БЕЗ ДАННЫХ** | 🔴 HIGH |
| 4c. Warmup | ✅ Запросы | ✅ Есть | ✅ OK | - |
| **5. Templates** | `build_templates.py` | `TemplateBuilder` | ⚠️ Неясно | 🟢 LOW |

---

## ✅ Что работает правильно

1. **Интерактивное меню** - удобный UX
2. **ES health checks** - проверка перед deploy
3. **AC patterns index creation** - правильные mappings
4. **Bulk load AC patterns** - ndjson формат
5. **Warmup queries** - прогрев кэша
6. **Validation входных файлов** - проверка существования

---

## 🚨 Критические проблемы (MUST FIX)

### Приоритет 1: AC Patterns Generation

**Проблема:** `prepare_sanctions_data.py` использует неправильный метод

**Решение:**
```python
# prepare_sanctions_data.py:102-107
def generate_ac_patterns(
    files: Dict[str, Path],
    output_dir: Path,
    tier_limits: Optional[Dict] = None,
    max_patterns: int = 50
) -> Path:
    """Generate AC patterns from sanctions data"""

    # ЗАМЕНИТЬ:
    # for person in persons:
    #     patterns = generator.generate_patterns(person, ...)

    # НА:
    corpus = generator.generate_full_corpus(
        persons_file=str(files["persons"]),
        companies_file=str(files["companies"]),
        terrorism_file=str(files["terrorism"])
    )

    # Применить tier_limits если нужно
    if tier_limits:
        corpus = apply_tier_limits(corpus, tier_limits)

    # Сохранить в правильном формате
    save_corpus(output_dir, corpus)
```

---

### Приоритет 2: Vector Generation Pipeline

**Проблема:** Векторы генерируются из sanctions JSON, а не из AC patterns

**Правильная последовательность:**
```bash
# 1. Генерация AC patterns
ac_patterns_file = generate_ac_patterns(...)  # → high_recall_ac_patterns.json

# 2. Генерация векторов ИЗ AC PATTERNS
vectors = generate_vectors(
    input=ac_patterns_file,  # ✅ AC patterns
    output="vectors.json"
)
```

**Или альтернативный подход:**
Если нужны векторы из исходных sanctions:
```python
# generate_vectors.py должен поддерживать 2 режима:
# 1. From AC patterns (текущий)
# 2. From raw sanctions data (новый)

if args.from_sanctions:
    # Генерировать векторы из sanctions JSON напрямую
    vectors = generate_from_sanctions(args.input)
else:
    # Генерировать из AC patterns
    vectors = generate_from_patterns(args.input)
```

---

### Приоритет 3: Vector Loading to ES

**Проблема:** Векторные индексы создаются, но остаются пустыми

**Решение:**
```python
# deploy_to_elasticsearch.py
async def bulk_load_vectors(es_host: str, index_name: str, vectors_file: Path) -> bool:
    """Bulk load vectors into Elasticsearch"""
    print(f"\n📦 Loading vectors from: {vectors_file.name}")

    try:
        with open(vectors_file, 'r', encoding='utf-8') as f:
            vectors_data = json.load(f)

        # Build bulk request
        bulk_data = []
        for vector_entry in vectors_data:
            bulk_data.append(json.dumps({"index": {"_index": index_name}}))
            bulk_data.append(json.dumps({
                "entity_id": vector_entry["metadata"]["entity_id"],
                "entity_type": vector_entry["metadata"]["entity_type"],
                "name": vector_entry["name"],
                "vector": vector_entry["vector"]
            }))

        bulk_body = "\n".join(bulk_data) + "\n"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{es_host}/_bulk",
                data=bulk_body,
                headers={"Content-Type": "application/x-ndjson"}
            ) as response:
                if response.status == 200:
                    print(f"   ✅ Successfully loaded vectors")
                    return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
```

---

### Приоритет 4: Backup & Replace

**Решение: Добавить pre-step в pipeline**

```python
# sanctions_pipeline.py - добавить шаг 0

def backup_and_replace(
    new_files_dir: Optional[Path],
    data_dir: Path,
    backup_dir: Path
) -> bool:
    """Backup current data and optionally replace with new files"""

    print("\n" + "="*60)
    print("  💾 STEP 0: BACKUP & REPLACE")
    print("="*60 + "\n")

    # 1. Backup current files
    print("Creating backups...")
    backup_current_data(data_dir, backup_dir)

    # 2. Replace if new files provided
    if new_files_dir:
        print("Replacing with new files...")
        replace_sanctions_files(new_files_dir, data_dir)
    else:
        print("ℹ️  No new files to replace, using existing data")

    return True
```

---

## 📝 Рекомендуемый Workflow

### Вариант A: Исправить prepare_sanctions_data.py

```bash
# Сделать prepare_sanctions_data.py полностью совместимым с export_high_recall_ac_patterns.py
# 1. Использовать generate_full_corpus()
# 2. Поддержать tier_limits
# 3. Векторы генерировать из AC patterns
# 4. Загружать векторы в ES
```

### Вариант B: Использовать export_high_recall_ac_patterns.py напрямую

```python
# sanctions_pipeline.py → вызывать оригинальный скрипт

def run_prepare_data():
    # Вместо prepare_sanctions_data.py:
    subprocess.run([
        "python", "scripts/export_high_recall_ac_patterns.py",
        "--output", "output/ac_patterns.json",
        "--tier-limits", "0:5,1:10,2:15,3:50",
        "--verbose"
    ])

    subprocess.run([
        "python", "scripts/generate_vectors.py",
        "--input", "output/ac_patterns.json",  # ✅ Из AC patterns
        "--output", "output/vectors.json"
    ])
```

---

## ✅ Итоговые рекомендации

### Immediate Actions (HIGH Priority):

1. **Исправить AC generation** в `prepare_sanctions_data.py`
   - Заменить `generate_patterns()` → `generate_full_corpus()`
   - Добавить поддержку `tier_limits`

2. **Исправить vector generation**
   - Input: AC patterns (не sanctions JSON)
   - Output: .json (не .npy)
   - Или добавить режим `--from-sanctions`

3. **Добавить vector loading в ES**
   - Функция `bulk_load_vectors()`
   - Загрузка после создания индексов

4. **Добавить backup step**
   - Pre-step перед prepare
   - Автоматический бэкап текущих данных

### Medium Priority:

5. Поддержка tier_limits в prepare_sanctions_data.py
6. Унификация моделей векторизации (384 vs 768 dim)
7. Валидация deployment manifest

### Low Priority:

8. Templates generation (уже есть через TemplateBuilder)
9. Advanced статистика и reporting
10. Rollback механизм при ошибках

---

## 🎯 Выводы

**sanctions_pipeline.py покрывает ~60% полного workflow:**

✅ **Есть:**
- Интерактивное меню
- ES deployment (частично)
- Validation входных данных
- Health checks

❌ **Отсутствует:**
- Backup & replace (Шаг 1)
- Правильная генерация AC patterns
- Правильная генерация векторов
- Загрузка векторов в ES
- Поддержка tier_limits

⚠️ **Неправильно реализовано:**
- AC patterns generation (использует низкоуровневый метод)
- Vector generation (неправильный input)
- Vector indices (создаются пустыми)

**Рекомендация:** Исправить критические проблемы (Приоритет 1-3) перед использованием в production.
