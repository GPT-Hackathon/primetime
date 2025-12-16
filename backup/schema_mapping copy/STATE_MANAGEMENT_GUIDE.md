# State Management Guide

The Schema Mapping Agent now includes **session state management** to save, load, and manipulate mappings within a conversation.

## Overview

With state management, you can:
- ✅ Save generated mappings with memorable IDs
- ✅ Load them later in the same session
- ✅ List all saved mappings
- ✅ Extract specific parts (validation rules, column mappings)
- ✅ Work with multiple mappings simultaneously
- ✅ Pass data between steps in your workflow

## New Tools

### 1. `save_mapping(mapping_json, mapping_id)`

Save a mapping to memory with a unique identifier.

**Example:**
```
User: Generate a mapping between worldbank_staging_dataset and worldbank_target_dataset in FIX mode

Agent: [Generates mapping]
       "I've created the mapping! Would you like me to save it?"

User: Yes, save it as "worldbank_prod"

Agent: [Calls save_mapping]
       "Saved as 'worldbank_prod'! You now have 1 saved mapping."
```

### 2. `load_mapping(mapping_id)`

Retrieve a previously saved mapping.

**Example:**
```
User: Load the worldbank_prod mapping

Agent: [Calls load_mapping]
       "Here's the worldbank_prod mapping: {...}"
```

### 3. `list_mappings()`

See all saved mappings in the current session.

**Example:**
```
User: What mappings do I have saved?

Agent: [Calls list_mappings]
       "You have 2 saved mappings:
       1. worldbank_prod (worldbank_staging → worldbank_target, FIX mode, 5 tables)
       2. test_mapping (test_staging → test_target, REPORT mode, 3 tables)"
```

### 4. `extract_validation_rules(mapping_id, table_name)`

Extract validation rules for a specific table or all tables.

**Example:**
```
User: Get validation rules from worldbank_prod for dim_country

Agent: [Calls extract_validation_rules]
       "Found 3 validation rules for dim_country:
       - country_key: NOT_NULL (Target column is REQUIRED)
       - country_code: UNIQUENESS
       - year: RANGE (1900-2100)"
```

### 5. `delete_mapping(mapping_id)`

Remove a saved mapping from memory.

**Example:**
```
User: Delete the test_mapping

Agent: [Calls delete_mapping]
       "Deleted test_mapping. You have 1 mapping remaining."
```

## Common Workflows

### Workflow 1: Generate, Save, and Extract

```
User: Generate a mapping between worldbank_staging_dataset and worldbank_target_dataset in FIX mode

Agent: [Generates comprehensive mapping]
       ✓ Created 5 table mappings
       ✓ 42 column mappings with 8 generated defaults
       ✓ 15 validation rules
       Would you like me to save this?

User: Save it as "worldbank_v1"

Agent: ✓ Saved as 'worldbank_v1'

User: Extract validation rules from worldbank_v1

Agent: Found validation rules for 5 tables:
       - dim_country: 3 rules
       - dim_indicator: 2 rules
       - dim_time: 1 rule
       - fact_indicator_values: 7 rules
       - agg_country_year: 2 rules

User: Get the rules for dim_country specifically

Agent: [Shows detailed rules for dim_country]
```

### Workflow 2: Compare Multiple Mappings

```
User: Generate mapping for worldbank datasets in REPORT mode

Agent: [Generates] Would you like to save it?

User: Save as "worldbank_report"

Agent: ✓ Saved

User: Now generate the same mapping in FIX mode

Agent: [Generates with defaults]

User: Save as "worldbank_fix"

Agent: ✓ Saved. You now have 2 mappings.

User: List my mappings

Agent: 1. worldbank_report (REPORT mode, 5 tables, 12 errors)
       2. worldbank_fix (FIX mode, 5 tables, 0 errors)

User: What's the difference in unmapped columns?

Agent: [Loads both and compares]
       In REPORT mode: 12 unmapped columns flagged as errors
       In FIX mode: Same 12 columns now have generated defaults
```

### Workflow 3: Multi-Step Processing

```
User: Generate mapping for worldbank_staging to worldbank_target in FIX mode

Agent: [Generates]

User: Save it as "prod_mapping"

Agent: ✓ Saved

User: Extract validation rules for all tables

Agent: [Shows all rules]
       Total: 15 rules across 5 tables

User: Now extract just the rules for fact_indicator_values

Agent: [Shows 7 rules for fact table]
       These rules should be used for validation

User: Great! I'll use those in my validation pipeline

Agent: Perfect! The rules are ready to use. Need anything else?
```

### Workflow 4: Iterative Refinement

```
User: Generate mapping for datasets X to Y

Agent: [Generates] Save it?

User: Save as "v1"

Agent: ✓ Saved

User: The defaults look wrong. Generate a new mapping but use CURRENT_DATE() instead of CURRENT_TIMESTAMP() for timestamps

Agent: [Generates new mapping with adjusted requirements]

User: Save as "v2"

Agent: ✓ Saved

User: List mappings

Agent: 1. v1 (uses CURRENT_TIMESTAMP)
       2. v2 (uses CURRENT_DATE)

User: Load v2 and show me the column mappings for the audit columns

Agent: [Loads v2 and extracts audit column mappings]
```

## Usage Patterns

### Pattern 1: Generate-Save-Extract

```
1. Generate mapping
2. Save with ID
3. Extract specific parts (validation rules, column mappings)
4. Use in downstream processes
```

### Pattern 2: Compare Modes

```
1. Generate in REPORT mode → Save as "report"
2. Generate in FIX mode → Save as "fix"
3. List and compare differences
4. Choose the best approach
```

### Pattern 3: Versioning

```
1. Generate mapping → Save as "v1"
2. Refine requirements
3. Generate new mapping → Save as "v2"
4. Compare v1 and v2
5. Delete old version if not needed
```

### Pattern 4: Batch Processing

```
1. Generate mapping for dataset A → Save as "mapping_a"
2. Generate mapping for dataset B → Save as "mapping_b"
3. Generate mapping for dataset C → Save as "mapping_c"
4. List all mappings
5. Extract validation rules from each
```

## Best Practices

### Naming Conventions

Use descriptive IDs that include:
- **Dataset names**: `worldbank_mapping`, `lending_mapping`
- **Versions**: `prod_v1`, `prod_v2`, `dev_v1`
- **Modes**: `worldbank_report`, `worldbank_fix`
- **Purpose**: `prod_final`, `test_draft`, `review_needed`

**Good examples:**
- ✅ `worldbank_prod_v1`
- ✅ `lending_fix_mode`
- ✅ `test_mapping_20251216`
- ✅ `final_approved`

**Avoid:**
- ❌ `mapping1`, `m1`, `test`
- ❌ Non-descriptive single letters
- ❌ Numbers without context

### Save Early and Often

```
# Good: Save immediately after generation
User: Generate mapping...
Agent: [Generates]
User: Save as "prod_v1"    ← Do this right away

# Not ideal: Generate multiple times and lose track
User: Generate mapping...
Agent: [Generates]
User: Generate another one...
Agent: [Generates - first one lost]
```

### Use Extract for Large JSONs

```
# Good: Extract specific parts
User: Extract validation rules from prod_v1

# Less efficient: Load entire JSON
User: Load prod_v1    ← Returns entire large JSON
```

### Clean Up When Done

```
User: Delete old_draft
User: Delete test_v1
Agent: Cleaned up! 2 mappings remaining.
```

## Session Limitations

### What Persists

✅ **Within the same session:**
- All saved mappings remain in memory
- Can be loaded/extracted anytime
- Listing shows all saved mappings

### What Doesn't Persist

❌ **Across different sessions:**
- Mappings are NOT saved between sessions
- Starting a new ADK session = fresh start
- Need to regenerate or save to files for persistence

### Working Around Session Limits

If you need persistence across sessions, use the CLI to save to files:

```bash
# Save to file
python run_schema_mapper.py \
    --source worldbank_staging \
    --target worldbank_target \
    --output worldbank_mapping.json \
    --mode FIX

# Later, you can reference this file
```

Or add file-based persistence tools (future enhancement).

## Advanced Usage

### Conditional Logic

```
User: Generate mapping for dataset X to Y in REPORT mode

Agent: [Generates]

User: Save as "report_mode"

Agent: ✓ Saved

User: How many unmapped columns are there?

Agent: [Analyzes] 8 unmapped columns

User: That's too many. Generate in FIX mode instead

Agent: [Generates with defaults]

User: Save as "fix_mode"

Agent: ✓ Saved. You now have both versions.
```

### Data Extraction Pipeline

```
User: Generate mapping for worldbank datasets in FIX mode

Agent: [Generates]

User: Save as "worldbank"

Agent: ✓ Saved

User: Extract validation rules for dim_country

Agent: [Extracts 3 rules]

User: Extract validation rules for dim_indicator

Agent: [Extracts 2 rules]

User: Extract validation rules for fact_indicator_values

Agent: [Extracts 7 rules]

# Now you have all rules extracted and ready to use
```

## Examples

### Example 1: Quick Generation and Save

```
User: Map worldbank_staging_dataset to worldbank_target_dataset in FIX mode

Agent: [Generates mapping]
       Generated comprehensive mapping with 5 tables, 42 columns, 15 validation rules.
       Would you like me to save this?

User: Yes, save it as "worldbank_prod"

Agent: ✓ Saved as 'worldbank_prod'!
       You can now:
       - Load it anytime: "load worldbank_prod"
       - Extract validation rules: "extract validation rules from worldbank_prod"
       - See all mappings: "list my mappings"
```

### Example 2: Working with Multiple Mappings

```
User: I need to compare REPORT and FIX modes for worldbank datasets

Agent: I can help! Let me generate both.
       First, generating REPORT mode...
       [Generates]
       Would you like me to save this as "worldbank_report"?

User: Yes

Agent: ✓ Saved. Now generating FIX mode...
       [Generates]
       Shall I save this as "worldbank_fix"?

User: Yes

Agent: ✓ Saved both! 
       worldbank_report: 12 unmapped columns (errors flagged)
       worldbank_fix: Same 12 columns with generated defaults
       
       Which would you like to review first?
```

### Example 3: Extracting for Downstream Use

```
User: Generate mapping between staging and target in FIX mode, save it as "prod_v1"

Agent: [Generates and saves]
       ✓ Mapping generated and saved as 'prod_v1'

User: Extract validation rules for all tables

Agent: [Extracts]
       Found 15 validation rules across 5 tables:
       - dim_country: 3 rules (NOT_NULL, UNIQUENESS)
       - dim_indicator: 2 rules (NOT_NULL)
       - dim_time: 1 rule (RANGE check for years)
       - fact_indicator_values: 7 rules
       - agg_country_year: 2 rules
       
       Would you like the detailed rules for any specific table?

User: Yes, show me fact_indicator_values rules

Agent: [Shows detailed rules with reasoning]
```

## Tips

1. **Always save after generating** - Don't lose your work!
2. **Use descriptive IDs** - Makes it easier to find later
3. **List before loading** - See what's available
4. **Extract instead of load** - For large JSONs, extract just what you need
5. **Clean up** - Delete mappings you don't need anymore
6. **Version your mappings** - Use v1, v2, etc. for iterations

## Summary

State management transforms the agent from a one-shot tool to a **stateful assistant** that can:
- Remember your work
- Help you compare options
- Extract exactly what you need
- Support multi-step workflows
- Work with multiple mappings simultaneously

**Start using it:**
```
adk run agents/schema_mapping

> Generate mapping for X to Y in FIX mode
> Save it as "my_first_mapping"
> List mappings
> Extract validation rules from my_first_mapping
```

Enjoy! 🚀

