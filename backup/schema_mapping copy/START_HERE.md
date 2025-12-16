# 🚀 Schema Mapping Agent - START HERE

Welcome! This agent generates intelligent schema mappings between BigQuery datasets using AI.

## 🎯 What Does This Do?

Automatically creates mappings between source and target BigQuery datasets:
- ✅ Matches tables intelligently
- ✅ Maps columns with type conversions
- ✅ Generates validation rules
- ✅ Suggests defaults for missing columns
- ✅ Identifies primary keys

**NEW: State Management** 🎉
- ✅ Save mappings with memorable IDs
- ✅ Load them later in the session
- ✅ Extract validation rules for specific tables
- ✅ Work with multiple mappings at once
- ✅ Compare different versions

## ⚡ Quick Start (30 seconds)

### Option 1: Interactive Chat (Recommended)

```bash
adk run agents/schema_mapping
```

Then chat:
```
> Generate a mapping between worldbank_staging_dataset and worldbank_target_dataset in FIX mode
> Save it as "worldbank_prod"
> Extract validation rules from worldbank_prod
```

### Option 2: Command Line

```bash
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output mapping.json \
    --mode FIX
```

### Option 3: Test It First

```bash
cd agents/schema_mapping
python test_local.py
```

## 📚 Documentation Guide

**New to this agent?** Read in this order:

1. **This file** (START_HERE.md) - You are here! ✅
2. **[QUICKSTART_ADK.md](QUICKSTART_ADK.md)** - Get running in 5 minutes
3. **[STATE_MANAGEMENT_GUIDE.md](STATE_MANAGEMENT_GUIDE.md)** - Save and reuse mappings ⭐ NEW
4. **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Choose the right mode for you
5. **[README.md](README.md)** - Complete documentation

**Setting up?**

6. **[ADK_SETUP_CHECKLIST.md](ADK_SETUP_CHECKLIST.md)** - Verify everything works

**Going deeper?**

7. **[README_ADK.md](README_ADK.md)** - Detailed ADK integration guide
8. **[API_README.md](API_README.md)** - REST API documentation
9. **[ADK_CONVERSION_SUMMARY.md](ADK_CONVERSION_SUMMARY.md)** - Technical details

## 🎮 Three Ways to Use

### 1. 💬 Interactive (Best for Exploration)

```bash
adk run agents/schema_mapping
```

**When to use:**
- Learning how it works
- Exploring new datasets
- Need explanations
- Want to iterate

**Example:**
```
You: Show me tables in my dataset
Agent: [Lists tables]
You: Generate a mapping
Agent: [Creates mapping and explains results]
```

### 2. ⚙️ CLI Script (Best for Automation)

```bash
python run_schema_mapper.py --source X --target Y --mode FIX
```

**When to use:**
- Batch processing
- Scripts and automation
- CI/CD pipelines
- Direct file output

**Example:**
```bash
for dataset in staging_*; do
    python run_schema_mapper.py --source "$dataset" --target "${dataset/staging/target}"
done
```

### 3. 🌐 REST API (Best for Integration)

```bash
python api.py  # Start server
# POST to http://localhost:8080/generate-mapping
```

**When to use:**
- Web application integration
- Microservices
- Remote access
- Multiple clients

**Example:**
```bash
curl -X POST http://localhost:8080/generate-mapping \
  -H "Content-Type: application/json" \
  -d '{"source_dataset": "staging", "target_dataset": "target", "mode": "FIX"}'
```

## 🔧 Prerequisites

### Must Have

1. **Google Cloud Project** with BigQuery and Vertex AI enabled
2. **Authentication**: `gcloud auth application-default login`
3. **Environment Variables** (create `.env` file):
   ```bash
   GCP_PROJECT_ID=your-project-id
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1
   GOOGLE_GENAI_USE_VERTEXAI=1
   ```
4. **Dependencies**: `pip install -r requirements.txt`

### Verify Setup

```bash
# Quick verification
python -c "from agent import root_agent; print('✓ Agent ready:', root_agent.name)"
```

If this works, you're good to go! If not, see [ADK_SETUP_CHECKLIST.md](ADK_SETUP_CHECKLIST.md).

## 🎯 Common Use Cases

### Use Case 1: First Time Mapping

```bash
# Step 1: Explore
adk run agents/schema_mapping
> "Show me tables in worldbank_staging_dataset"

# Step 2: Generate
> "Generate mapping to worldbank_target_dataset in REPORT mode"

# Step 3: Review and refine
> "Now generate in FIX mode"
```

### Use Case 2: Automated Pipeline

```bash
# In your ETL script
python run_schema_mapper.py \
    --source staging \
    --target prod \
    --output mapping.json \
    --mode FIX

# Use the mapping for validation
python validate_with_mapping.py mapping.json
```

### Use Case 3: Web Application

```python
# In your Flask/FastAPI app
import requests

response = requests.post(
    "http://your-api.run.app/generate-mapping",
    json={"source_dataset": "staging", "target_dataset": "prod", "mode": "FIX"}
)

mapping = response.json()
```

## 🎨 Two Modes Explained

### REPORT Mode

**What it does:** Flags unmapped columns as errors

**Output example:**
```json
{
  "source_column": "UNMAPPED",
  "target_column": "loaded_at",
  "notes": "No source column found"
}
```

**Use when:** You want to see what's missing and fix manually

### FIX Mode

**What it does:** Suggests intelligent defaults

**Output example:**
```json
{
  "source_column": "GENERATED",
  "target_column": "loaded_at",
  "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
  "notes": "Auto-generated timestamp"
}
```

**Use when:** You want automatic suggestions for missing columns

## 🐛 Troubleshooting

### Quick Fixes

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"Permission denied"**
```bash
gcloud auth application-default login
```

**"Dataset not found"**
```bash
bq ls  # Check your datasets exist
```

**"Agent not responding"**
```bash
# Check environment
python test_local.py
```

### Still Stuck?

1. Run the setup checklist: [ADK_SETUP_CHECKLIST.md](ADK_SETUP_CHECKLIST.md)
2. Check detailed docs: [README_ADK.md](README_ADK.md)
3. Review error logs in terminal

## 📊 What You Get

The agent generates comprehensive JSON with:

```json
{
  "status": "success",
  "mapping": {
    "metadata": {
      "source_dataset": "...",
      "target_dataset": "...",
      "mode": "FIX",
      "confidence": "high"
    },
    "mappings": [
      {
        "source_table": "staging.countries",
        "target_table": "target.dim_country",
        "column_mappings": [...],
        "validation_rules": [...],
        "primary_key": [...],
        "unmapped_columns": [...]
      }
    ]
  }
}
```

## 🎓 Learning Path

**Beginner:**
1. Read this file ✅
2. Run `python test_local.py`
3. Try `adk run agents/schema_mapping`
4. Read [QUICKSTART_ADK.md](QUICKSTART_ADK.md)

**Intermediate:**
1. Read [USAGE_GUIDE.md](USAGE_GUIDE.md)
2. Try all three modes
3. Experiment with your datasets
4. Read [README.md](README.md)

**Advanced:**
1. Read [README_ADK.md](README_ADK.md)
2. Deploy to Cloud Run
3. Integrate with your pipelines
4. Customize the agent

## 🚦 Next Steps

Choose your path:

**I want to try it now:**
```bash
adk run agents/schema_mapping
```

**I want to understand it first:**
→ Read [QUICKSTART_ADK.md](QUICKSTART_ADK.md)

**I want to set it up properly:**
→ Follow [ADK_SETUP_CHECKLIST.md](ADK_SETUP_CHECKLIST.md)

**I want to integrate it:**
→ Read [USAGE_GUIDE.md](USAGE_GUIDE.md)

## 💡 Tips

1. **Start with REPORT mode** to understand gaps
2. **Use FIX mode** for automation
3. **Test with small datasets** first
4. **Review generated mappings** before using in production
5. **Save mappings** for version control

## 🎉 Success Criteria

You'll know it's working when:

✅ Agent starts without errors
✅ Can fetch table schemas
✅ Generates complete mappings
✅ Returns valid JSON
✅ Explains results clearly

## 📞 Support

**Documentation:**
- [QUICKSTART_ADK.md](QUICKSTART_ADK.md) - Quick start guide
- [USAGE_GUIDE.md](USAGE_GUIDE.md) - Complete usage guide
- [README_ADK.md](README_ADK.md) - Technical details

**Troubleshooting:**
- [ADK_SETUP_CHECKLIST.md](ADK_SETUP_CHECKLIST.md) - Setup verification
- `python test_local.py` - Run diagnostics

**Examples:**
- See `test_local.py` for code examples
- Check `worldbank_mapping*.json` for output examples

---

## 🎯 TL;DR

**Want to try it RIGHT NOW?**

```bash
# 1. Set environment variables (create .env file)
echo "GCP_PROJECT_ID=your-project" > .env
echo "GOOGLE_CLOUD_PROJECT=your-project" >> .env
echo "GOOGLE_CLOUD_LOCATION=us-central1" >> .env
echo "GOOGLE_GENAI_USE_VERTEXAI=1" >> .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run it
adk run agents/schema_mapping

# 4. Chat
> "Generate a mapping between worldbank_staging_dataset and worldbank_target_dataset in FIX mode"
```

**That's it! 🎉**

---

**Version**: 1.0 (ADK Compatible)
**Last Updated**: December 16, 2025
**Model**: Gemini 2.5 Flash

