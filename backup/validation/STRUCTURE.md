# Validation Agent - Directory Structure

```
agents/validation/
│
├── README.md                    # Complete documentation (architecture, usage, design)
├── QUICKSTART.md               # 5-minute getting started guide
├── CHANGES.md                  # Changelog of all fixes and improvements
├── STRUCTURE.md                # This file - directory overview
├── .env.example                # Environment variable template
│
├── __init__.py                 # Package initialization
├── main.py                     # Main entry point (CLI interface)
├── validation_agent.py         # Core validation logic and ADK agent
│
├── infrastructure/
│   ├── __init__.py            # Infrastructure module initialization
│   └── load_staging.py        # Load CSV files into BigQuery staging tables
│
├── mock/
│   └── mock_schema.json       # Schema mappings & validation rules (8 tables)
│
└── tests/
    └── test_validation_agent.py  # Unit tests (8 test cases)
```

## File Purposes

### Entry Points

#### `main.py`
- **Purpose:** Main CLI entry point
- **Usage:** `python agents/validation/main.py --mode REPORT`
- **Features:**
  - Command-line argument parsing
  - Environment validation
  - Orchestrates 3-step workflow: Load → Configure → Validate
  - Beautiful formatted output with progress indicators
  - Comprehensive error handling
- **Exit Codes:**
  - `0` = Success
  - `1` = Error occurred

### Core Logic

#### `validation_agent.py`
- **Purpose:** Core validation engine using Google ADK
- **Key Components:**
  - `validate_data()` function - Main validation tool
  - `validation_agent` - ADK Agent instance using Gemini 2.5 Flash
- **Capabilities:**
  - Generate SQL validation queries from rules
  - REPORT mode: Find and log errors to staging.staging_errors
  - FIX mode: Auto-correct safe errors (NOT_NULL, NUMERIC)
  - Skip dangerous fixes (RANGE violations)
- **Returns:** JSON results: `{"status": "success", "errors_found": 15}`

### Infrastructure

#### `infrastructure/load_staging.py`
- **Purpose:** Load CSV files into BigQuery staging tables
- **Features:**
  - Reads schema from mock_schema.json
  - Creates BigQuery tables with proper schemas
  - Loads CSV data using BigQuery load jobs
  - Idempotent (WRITE_TRUNCATE mode)
- **Usage:** Can be run standalone:
  ```bash
  python agents/validation/infrastructure/load_staging.py
  ```

### Configuration

#### `mock/mock_schema.json`
- **Purpose:** Define table mappings and validation rules
- **Structure:**
  ```json
  {
    "mappings": [
      {
        "source_file": "source_countries.csv",
        "target_table": "staging.countries",
        "schema": [...],
        "rules": [...]
      }
    ]
  }
  ```
- **Defines:** 8 table mappings for World Bank dataset

### Testing

#### `tests/test_validation_agent.py`
- **Purpose:** Unit tests for validation logic
- **Test Cases:**
  1. `test_validate_data_report_mode` - REPORT mode validation
  2. `test_validate_data_fix_mode` - FIX mode with NOT_NULL
  3. `test_agent_structure` - Agent configuration
  4. `test_validate_data_range_check` - RANGE validation
  5. `test_validate_data_range_fix_skipped` - RANGE fixes skipped
  6. `test_validate_data_invalid_json` - Error handling
  7. `test_validate_data_string_column_fix` - String column fixes
- **Coverage:** ~80%
- **Run:** `python -m unittest agents/validation/tests/test_validation_agent.py`

### Documentation

#### `README.md`
- Architecture overview
- All validation rule types
- Usage examples
- Configuration guide
- Design decisions
- Limitations & future work

#### `QUICKSTART.md`
- Prerequisites checklist
- 5-minute setup steps
- Usage examples with output
- SQL queries for results
- Troubleshooting common errors
- Advanced usage

#### `CHANGES.md`
- Complete changelog
- Issues fixed
- Improvements made
- Testing recommendations
- Migration notes

#### `.env.example`
- Environment variable template
- Copy to `.env` and customize
- Required: GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS

## Workflow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                      main.py                            │
│  Command Line Interface & Orchestration                 │
└──────────┬──────────────────────────────────┬──────────┘
           │                                    │
           ▼                                    ▼
  ┌────────────────────┐              ┌────────────────────┐
  │  load_staging.py   │              │ validation_agent.py│
  │                    │              │                    │
  │  - Read CSVs       │              │  - ADK Agent       │
  │  - Create tables   │              │  - SQL generation  │
  │  - Load data       │              │  - Validation      │
  └────────┬───────────┘              └─────────┬──────────┘
           │                                     │
           ▼                                     ▼
  ┌────────────────────┐              ┌────────────────────┐
  │ mock_schema.json   │              │   BigQuery         │
  │                    │◄─────────────┤                    │
  │  - Table mappings  │              │  - staging.*       │
  │  - Validation rules│              │  - staging_errors  │
  └────────────────────┘              └────────────────────┘
```

## Data Flow

### 1. REPORT Mode
```
CSV Files → load_staging.py → BigQuery staging.* tables
                                        ↓
            mock_schema.json → validation_agent.py
                                        ↓
                              SQL Validation Queries
                                        ↓
                              staging.staging_errors ← Error Records
                                        ↓
                              Summary Report (stdout)
```

### 2. FIX Mode
```
CSV Files → load_staging.py → BigQuery staging.* tables
                                        ↓
            mock_schema.json → validation_agent.py
                                        ↓
                         SQL Validation + UPDATE Queries
                                        ↓
                    staging.* tables (updated with fixes)
                                        ↓
                              Summary Report (stdout)
```

## BigQuery Tables Created

### Staging Tables (8)
1. `staging.countries` - Country metadata
2. `staging.indicators_meta` - Indicator definitions
3. `staging.gdp` - GDP time series
4. `staging.population` - Population time series
5. `staging.life_expectancy` - Life expectancy data
6. `staging.co2_emissions` - CO2 emissions data
7. `staging.primary_enrollment` - School enrollment data
8. `staging.poverty_headcount` - Poverty statistics

### Error Table (1)
- `staging.staging_errors` - Validation error log

## Dependencies

### Python Packages
- `google-cloud-bigquery` - BigQuery client
- `google-adk` - Agent Development Kit
- `vertexai` - Vertex AI SDK
- `python-dotenv` - Environment variable loading

### External Services
- Google Cloud BigQuery
- Google Vertex AI (Gemini 2.5 Flash)

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `GCP_PROJECT_ID` | Yes | - | Google Cloud Project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | - | Path to service account key |
| `GOOGLE_CLOUD_LOCATION` | No | us-central1 | GCP region for Vertex AI |
| `GOOGLE_CLOUD_PROJECT` | No | - | Alias for GCP_PROJECT_ID |

## Quick Commands

```bash
# Run validation in REPORT mode
python agents/validation/main.py --mode REPORT

# Run validation in FIX mode
python agents/validation/main.py --mode FIX

# Skip data loading (use existing tables)
python agents/validation/main.py --mode REPORT --skip-load

# Load data only (no validation)
python agents/validation/infrastructure/load_staging.py

# Run tests
python -m unittest agents/validation/tests/test_validation_agent.py

# Get help
python agents/validation/main.py --help
```

## File Sizes (Approximate)

```
README.md                      ~12 KB  (comprehensive docs)
QUICKSTART.md                  ~8 KB   (getting started)
CHANGES.md                     ~11 KB  (changelog)
main.py                        ~7 KB   (CLI interface)
validation_agent.py            ~5 KB   (core logic)
load_staging.py                ~3 KB   (data loading)
mock_schema.json               ~4 KB   (8 table configs)
test_validation_agent.py       ~6 KB   (8 test cases)
```

## Next Steps

1. **Setup:** Follow [QUICKSTART.md](QUICKSTART.md)
2. **Understand:** Read [README.md](README.md) for architecture
3. **Run:** Execute `main.py --mode REPORT`
4. **Customize:** Edit `mock/mock_schema.json` for your rules
5. **Extend:** Add new tables and validation rules

## Support

- **Documentation:** See README.md for detailed docs
- **Quick Start:** See QUICKSTART.md for setup
- **Changes:** See CHANGES.md for what's new
- **Issues:** Check GCP logs in Cloud Console
