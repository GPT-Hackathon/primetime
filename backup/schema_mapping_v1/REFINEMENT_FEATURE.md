# Mapping Refinement Feature - User Override Capability

## Problem Fixed

**Before:** When users asked to fix a specific mapping (e.g., "map country_code to country_key"), the agent would apologize and say it couldn't directly modify mappings. Users had to manually edit the generated SQL files.

**After:** The agent can now accept natural language instructions and **automatically regenerate** all files with the custom mappings applied.

## What Was Added

### 1. New Module: `custom_mappings.py`

Provides two key functions:

- **`parse_mapping_instruction()`** - Parses natural language into structured overrides
  - "map country_code to country_key"
  - "use annual_revenue for revenue_amount"
  - "change borrower_id to use borrower_number"

- **`apply_custom_overrides()`** - Applies user overrides to automated mappings
  - Replaces existing mappings
  - Intelligently determines transformations based on types
  - Recalculates confidence scores

### 2. New Agent Tool: `refine_mapping()`

Accepts three parameters:
- `source_table`: Full source table name
- `target_table`: Full target table name
- `instructions`: Natural language instruction

**Flow:**
1. Gets schemas from BigQuery
2. Generates automated mapping
3. Parses user instruction
4. Applies custom override
5. Regenerates SQL, report, and visualization
6. Returns summary of changes

## Usage Examples

### Example 1: Change Column Mapping

```
You: Create a schema mapping from staging_countries to dim_country

Agent: Generated mapping with 5 columns...
       - country_name → country_name
       - country_iso → country_key  (auto-mapped)
       ...

You: Map country_code to country_key instead

Agent: ✅ Mapping refined successfully!
       
       Applied custom override:
       - Source: country_code (STRING)
       - Target: country_key (STRING)
       
       📄 Updated Files:
       - SQL: schema_mapping/output/mapping_dim_country.sql
       - Report: schema_mapping/output/mapping_report_dim_country.md
       - Visualization: schema_mapping/output/mapping_viz_dim_country.html
```

### Example 2: Add Literal Values

```
You: Set data_source to 'staging_gdp'

Agent: ✅ Mapping refined successfully!
       
       Applied custom override:
       - Expression: CAST('staging_gdp' AS STRING)
       - Target: data_source (STRING)
       - Type: LITERAL_VALUE
       
       📄 Updated Files:
       - SQL: schema_mapping/output/mapping_fact_indicator_values.sql
       ...
```

The generated SQL will now include:
```sql
SELECT
  ...,
  CAST('staging_gdp' AS STRING) AS data_source,
  ...
FROM source_table;
```

### Example 3: Add Functions

```
You: Set loaded_at to CURRENT_TIMESTAMP()

Agent: ✅ Mapping refined successfully!
       
       Applied custom override:
       - Expression: CURRENT_TIMESTAMP()
       - Target: loaded_at (TIMESTAMP)
       - Type: FUNCTION
       
       📄 Updated Files regenerated.
```

The generated SQL will now include:
```sql
SELECT
  ...,
  CURRENT_TIMESTAMP() AS loaded_at,
  ...
FROM source_table;
```

### Example 4: Multiple Refinements

```
You: Map borrower_number to borrower_id

Agent: ✅ Mapping refined successfully! ...

You: Now set data_source to 'staging_borrower'

Agent: ✅ Mapping refined successfully! ...

You: And set loaded_at to CURRENT_TIMESTAMP()

Agent: ✅ Mapping refined successfully! ...
```

### Supported Instruction Patterns

The parser recognizes these natural language patterns:

**Column-to-Column Mappings:**

1. **"map X to Y"**
   - "map country_code to country_key"
   - "map borrower_id to customer_id"

2. **"use X for Y"**
   - "use country_code for country_key"
   - "use annual_revenue for revenue_amount"

3. **"change Y to use X"**
   - "change country_key to use country_code"
   - "change borrower_id to use customer_number"

**Literal Values (NEW!):**

4. **"set Y to 'literal'"**
   - "set data_source to 'staging_gdp'"
   - "set status to 'active'"
   - "set version to '1.0'"

**Functions (NEW!):**

5. **"set Y to FUNCTION()"**
   - "set loaded_at to CURRENT_TIMESTAMP()"
   - "set created_date to CURRENT_DATE()"
   - "populate updated_at with CURRENT_TIMESTAMP()"

6. **"add Y as 'literal' or FUNCTION()"**
   - "add data_source as 'staging'"
   - "add inserted_at as CURRENT_TIMESTAMP()"

## How It Works

### Step 1: Parse Instruction

```python
instruction = "map country_code to country_key"

# Extracts:
override = {
    'source_column': 'country_code',
    'target_column': 'country_key',
    'source_type': 'STRING',
    'target_type': 'STRING'
}
```

### Step 2: Apply Override

```python
# Original automated mapping
mappings = [
    {'source_column': 'country_iso', 'target_column': 'country_key', ...},
    ...
]

# After override
mappings = [
    {'source_column': 'country_code', 'target_column': 'country_key', ...},  # Updated!
    ...
]
```

### Step 3: Regenerate Files

- **SQL**: Column mapping updated in SELECT clause
- **Report**: Shows new mapping with 100% confidence (user override)
- **Visualization**: HTML updated with new mappings

## Intelligent Type Handling

The override system automatically determines transformations:

**Same Types:**
```sql
-- STRING → STRING
`country_code` AS `country_key`
```

**Type Conversion Needed:**
```sql
-- STRING → INT64
SAFE_CAST(`borrower_number` AS INT64) AS `borrower_id`

-- STRING → DATE
SAFE.PARSE_DATE('%Y-%m-%d', `date_string`) AS `date_column`
```

## Agent Now Has 10 Tools

1. `map_schemas()` - Initial automated mapping
2. `get_table_info()` - Table details
3. `get_sample_data_from_table()` - Data preview
4. `analyze_column_in_table()` - Column analysis
5. `generate_merge_sql_for_tables()` - MERGE statements
6. `generate_dbt_model_sql()` - DBT models
7. `list_dataset_tables()` - List tables
8. `discover_and_map_dataset_pairs()` - Find pairs
9. `batch_map_all_tables()` - Batch process
10. **`refine_mapping()`** - **NEW!** Custom overrides

## Workflow with Refinement

### Complete User Journey

```
1. User: "Create mapping from staging_borrower to dim_borrower"
   Agent: Generates automated mapping

2. User reviews HTML visualization

3. User: "Map borrower_number to borrower_id instead"
   Agent: Applies override, regenerates files

4. User reviews updated files

5. User: "This looks good"
   Agent: Confirms files are ready

6. User executes SQL or integrates into pipeline
```

## Comparison: Before vs After

### Before (The Problem)

```
You: Map country_code to country_key instead

Agent: I apologize, but I cannot directly modify the mapping. 
       You will need to manually edit the SQL file:
       schema_mapping/output/mapping_dim_country.sql
       
       Please change the line to map country_code instead of country_iso.
```

❌ **User has to manually edit SQL**
❌ **Reports and HTML don't match updated SQL**
❌ **Not a true "refinement workflow"**

### After (The Solution)

```
You: Map country_code to country_key instead

Agent: ✅ Mapping refined successfully!
       
       Applied custom override:
       - Source: country_code (STRING)
       - Target: country_key (STRING)
       
       All files regenerated with your custom mapping.
```

✅ **Agent automatically updates files**
✅ **All outputs stay in sync**
✅ **True interactive refinement**

## For Your Hackathon

This feature completes the **review and approval workflow** you promised:

1. ✅ Agent generates intelligent mappings
2. ✅ User reviews (reports + visualization)
3. ✅ **User can refine mappings** (NEW!)
4. ✅ Agent regenerates everything
5. ✅ User approves final mapping

**Demo Script:**

1. Show automated mapping
2. Point out one "wrong" mapping in HTML
3. Tell agent: "Map X to Y instead"
4. Show updated visualization
5. Explain: "The agent learns from your corrections"

---

**Bottom Line:** Your agent now truly supports the interactive refinement workflow, making it much more practical for real-world use!

