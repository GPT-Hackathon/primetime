# Quick Start Guide - Schema Mapping Agent

## 5-Minute Setup

### 1. Install Dependencies

```bash
cd /Users/nkaravadi/Dev/GPTHackathon/primetime

# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

### 3. Run Your First Mapping

```bash
# Interactive mode
python schema_mapping/test_local.py

# At the prompt, type:
demo
```

That's it! The agent will:
- Connect to your BigQuery tables
- Analyze schemas
- Generate SQL, reports, and visualizations
- Save everything to `schema_mapping/output/`

## Example Output

After running, you'll get:

```
✅ Mapped 12/12 columns (100% coverage)
🎯 12 high confidence mappings
✓ 2 type conversions needed

📄 Generated Files:
- SQL: schema_mapping/output/mapping_dim_borrower.sql
- Report: schema_mapping/output/mapping_report_dim_borrower.md  
- Visualization: schema_mapping/output/mapping_viz_dim_borrower.html
```

## View Your Results

```bash
# View the markdown report
cat schema_mapping/output/mapping_report_dim_borrower.md

# Open HTML visualization in browser
open schema_mapping/output/mapping_viz_dim_borrower.html

# View the SQL
cat schema_mapping/output/mapping_dim_borrower.sql
```

## Interactive Commands

Try these commands in the interactive session:

```
# Single table mapping
Create a schema mapping from PROJECT.DATASET.SOURCE to PROJECT.DATASET.TARGET

# List all tables in dataset
List all tables in PROJECT.DATASET

# Discover matching pairs
Discover table pairs between PROJECT.staging_dataset and PROJECT.target_dataset

# Batch process all tables
Map all tables from PROJECT.staging_dataset to PROJECT.target_dataset

# Get table info
Show me details about PROJECT.DATASET.TABLE

# Analyze specific column
Analyze the borrower_id column in the source table

# Get sample data
Show me sample data from the target table

# Generate MERGE instead
Generate a MERGE statement using borrower_id as the key

# Generate DBT model
Generate a DBT model for these tables

# Request changes
Change annual_revenue to use regular CAST instead of SAFE_CAST

# Approve
This looks good, I approve this mapping
```

## Your Tables

For the hackathon, use these tables:

**Source (Staging):**
```
ccibt-hack25ww7-750.test_staging_dataset.borrower
```

**Target (Analytics):**
```
ccibt-hack25ww7-750.test_dataset.dim_borrower
```

## Programmatic Usage

```python
from schema_mapping.agent import map_schemas

result = map_schemas(
    source_table="ccibt-hack25ww7-750.test_staging_dataset.borrower",
    target_table="ccibt-hack25ww7-750.test_dataset.dim_borrower"
)
print(result)
```

See `example_usage.py` for more examples.

## Troubleshooting

**"Authentication error"**
- Run: `gcloud auth application-default login`

**"Table not found"**
- Verify table names: `bq ls PROJECT:DATASET`
- Check format: `project.dataset.table`

**"No module named 'schema_mapping'"**
- Run from project root: `/Users/nkaravadi/Dev/GPTHackathon/primetime`
- Or: `pip install -e .`

## Next Steps

1. ✅ Run the demo with test tables
2. 📊 Open the HTML visualization
3. 📝 Review the markdown report
4. 💻 Execute the generated SQL (in a test environment first!)
5. 🔄 Try refining mappings with different prompts
6. 🚀 Deploy to Vertex AI: `python schema_mapping/deploy_vertex.py`

## Demo Script for Hackathon

Perfect for presenting:

1. **Show the problem**: Display source CSV and target SQL schema
2. **Run the agent**: `python schema_mapping/test_local.py` → type `demo`
3. **Show the outputs**: Open HTML visualization in browser
4. **Demonstrate intelligence**: Ask agent about specific columns
5. **Show refinement**: Request a change, agent regenerates mapping
6. **Show the SQL**: Display the generated transformation code
7. **Explain value**: Saves hours of manual mapping work!

---

**Time to first mapping: < 5 minutes** ⚡

