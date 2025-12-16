# ADK Setup Checklist

Use this checklist to verify your Schema Mapping Agent is ready to run with ADK.

## ✅ Prerequisites

### Google Cloud Setup

- [ ] Google Cloud Project created
- [ ] Project ID noted: `_________________`
- [ ] Billing enabled on project
- [ ] BigQuery API enabled
  ```bash
  gcloud services enable bigquery.googleapis.com
  ```
- [ ] Vertex AI API enabled
  ```bash
  gcloud services enable aiplatform.googleapis.com
  ```

### Local Environment

- [ ] Python 3.9+ installed
  ```bash
  python --version  # Should be 3.9 or higher
  ```
- [ ] Google Cloud SDK installed
  ```bash
  gcloud --version
  ```
- [ ] Authenticated with Google Cloud
  ```bash
  gcloud auth application-default login
  ```
- [ ] Project set correctly
  ```bash
  gcloud config set project YOUR_PROJECT_ID
  ```

### Dependencies

- [ ] Dependencies installed
  ```bash
  cd agents/schema_mapping
  pip install -r requirements.txt
  ```
- [ ] Verify installations:
  ```bash
  python -c "import google.adk; print('ADK OK')"
  python -c "import vertexai; print('Vertex AI OK')"
  python -c "from google.cloud import bigquery; print('BigQuery OK')"
  ```

## ✅ Configuration

### Environment Variables

- [ ] `.env` file created in project root or agent directory
- [ ] Environment variables set:
  ```bash
  # Required
  GCP_PROJECT_ID=your-project-id
  GOOGLE_CLOUD_PROJECT=your-project-id
  GOOGLE_CLOUD_LOCATION=us-central1
  GOOGLE_GENAI_USE_VERTEXAI=1
  ```
- [ ] Verify environment variables:
  ```bash
  python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Project:', os.getenv('GCP_PROJECT_ID'))"
  ```

### BigQuery Datasets

- [ ] Source dataset exists
  ```bash
  bq ls YOUR_PROJECT:your_source_dataset
  ```
- [ ] Target dataset exists
  ```bash
  bq ls YOUR_PROJECT:your_target_dataset
  ```
- [ ] Permissions verified (you can read schemas)
  ```bash
  bq show YOUR_PROJECT:your_source_dataset.table_name
  ```

## ✅ File Verification

### New ADK Files

- [ ] `agent.py` exists and contains `root_agent`
- [ ] `test_local.py` exists
- [ ] `README_ADK.md` exists
- [ ] `QUICKSTART_ADK.md` exists

### Modified Files

- [ ] `__init__.py` exports `root_agent`
- [ ] `README.md` mentions ADK usage

### Original Files (Unchanged)

- [ ] `schema_mapper.py` exists
- [ ] `run_schema_mapper.py` exists
- [ ] `api.py` exists
- [ ] `requirements.txt` exists

## ✅ Testing

### Test 1: Import Check

```bash
cd agents/schema_mapping
python -c "from agent import root_agent; print('Agent imported:', root_agent.name)"
```

- [ ] No import errors
- [ ] Prints: `Agent imported: schema_mapping_agent`

### Test 2: Local Test Script

```bash
cd agents/schema_mapping
python test_local.py
```

- [ ] Script runs without errors
- [ ] Displays conversation
- [ ] Shows agent responses
- [ ] Completes successfully

### Test 3: ADK Run (Interactive)

```bash
adk run agents/schema_mapping
```

- [ ] Agent starts successfully
- [ ] Can send messages
- [ ] Agent responds appropriately
- [ ] Can exit cleanly (Ctrl+C or exit command)

### Test 4: Tool Functionality

In ADK interactive mode, test each tool:

**Test fetch_table_schema:**
```
> Get the schema for table PROJECT.DATASET.TABLE
```
- [ ] Returns table schema
- [ ] Shows columns and types

**Test fetch_dataset_schemas:**
```
> Show me all tables in DATASET_NAME
```
- [ ] Returns all table schemas
- [ ] Lists all tables

**Test generate_schema_mapping:**
```
> Generate a mapping between SOURCE_DATASET and TARGET_DATASET in FIX mode
```
- [ ] Fetches schemas
- [ ] Generates mapping
- [ ] Returns JSON result
- [ ] Includes validation rules

## ✅ Backward Compatibility

### Test Original CLI

```bash
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output test_mapping.json \
    --mode REPORT
```

- [ ] Runs successfully
- [ ] Creates output file
- [ ] JSON is valid

### Test Original API

```bash
# Terminal 1: Start API
python api.py

# Terminal 2: Test endpoint
curl http://localhost:8080/health
```

- [ ] API starts
- [ ] Health check returns `{"status": "healthy"}`
- [ ] Can stop cleanly (Ctrl+C)

## ✅ Documentation

- [ ] Read `README_ADK.md`
- [ ] Read `QUICKSTART_ADK.md`
- [ ] Understand three usage modes
- [ ] Know how to troubleshoot

## 🎯 Ready to Use!

If all items are checked, you're ready to use the Schema Mapping Agent with ADK!

### Quick Start Commands

**Interactive Mode:**
```bash
adk run agents/schema_mapping
```

**Local Testing:**
```bash
cd agents/schema_mapping
python test_local.py
```

**Original CLI:**
```bash
python run_schema_mapper.py --source X --target Y --mode FIX
```

## 🐛 Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'google.adk'`
```bash
pip install google-adk
```

**Issue**: `Permission denied` when accessing BigQuery
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

**Issue**: `Vertex AI not initialized`
- Check `.env` file exists
- Verify `GOOGLE_GENAI_USE_VERTEXAI=1`
- Ensure Vertex AI API is enabled

**Issue**: `Dataset not found`
```bash
# List all datasets
bq ls

# Check specific dataset
bq ls YOUR_PROJECT:dataset_name
```

**Issue**: Agent doesn't respond in ADK
- Check Vertex AI API is enabled
- Verify project has Gemini access
- Try `test_local.py` for detailed errors

### Getting Help

1. **Check logs**: Look for error messages in terminal
2. **Run test script**: `python test_local.py` for diagnostics
3. **Verify environment**: Check all environment variables
4. **Review docs**: Read relevant README files
5. **Test components**: Test BigQuery and Vertex AI separately

### Verification Commands

```bash
# Check Python version
python --version

# Check gcloud config
gcloud config list

# Check authentication
gcloud auth list

# Check BigQuery access
bq ls

# Check Vertex AI access
gcloud ai models list --region=us-central1

# Check environment variables
env | grep GOOGLE
env | grep GCP
```

## 📚 Next Steps

After completing this checklist:

1. **Explore**: Try different queries in ADK interactive mode
2. **Experiment**: Test with your own datasets
3. **Integrate**: Choose the mode that fits your workflow
4. **Share**: Share with your team
5. **Feedback**: Note what works and what doesn't

## 📝 Notes

Use this space for your own notes:

```
Project ID: _________________
Source Dataset: _________________
Target Dataset: _________________
Special Configuration: _________________
Issues Encountered: _________________
Solutions Found: _________________
```

---

**Checklist Version**: 1.0
**Last Updated**: December 16, 2025
**Agent Version**: ADK Compatible

