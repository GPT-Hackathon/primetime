# Schema Mapping Agent - Complete Usage Guide

## Overview

The Schema Mapping Agent is now available in **three modes** to fit your workflow:

```
┌─────────────────────────────────────────────────────────────┐
│                  Schema Mapping Agent                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. ADK Interactive    2. CLI Script      3. REST API       │
│     (Conversational)      (Batch)           (Service)       │
│                                                              │
│     adk run .          python run_*.py     python api.py    │
│     > chat...          --source X          POST /generate   │
│                        --target Y                            │
└─────────────────────────────────────────────────────────────┘
```

## Mode Comparison

| Feature | ADK Interactive | CLI Script | REST API |
|---------|----------------|------------|----------|
| **Interface** | Chat | Command line | HTTP |
| **Best For** | Exploration | Automation | Integration |
| **Learning Curve** | Easy | Medium | Medium |
| **Flexibility** | High | Medium | High |
| **Deployment** | Local/Cloud | Local | Cloud Run |
| **Output** | Conversation | JSON file | JSON response |

## Mode 1: ADK Interactive (Recommended for Exploration)

### When to Use
- ✅ Exploring datasets for the first time
- ✅ Learning how schema mapping works
- ✅ Need explanations of results
- ✅ Want to refine mappings iteratively
- ✅ Prefer natural language over commands

### How to Use

**Start the agent:**
```bash
adk run agents/schema_mapping
```

**Example conversation:**
```
You: Hello! What can you do?

Agent: I'm a Schema Mapping Agent that helps you generate intelligent 
mappings between BigQuery datasets. I can:

1. Fetch schema information from BigQuery tables
2. Analyze entire datasets
3. Generate comprehensive mappings with validation rules

What would you like to do?

You: I need to map worldbank_staging_dataset to worldbank_target_dataset

Agent: I can help with that! Would you like me to generate the mapping in:
- REPORT mode (flags unmapped columns for review)
- FIX mode (suggests default values for unmapped columns)

Which mode would you prefer?

You: Use FIX mode

Agent: [Calls generate_schema_mapping tool]
Great! I've generated a comprehensive mapping. Here's what I found:

- 5 table mappings created
- 42 column mappings with 8 generated defaults
- 15 validation rules
- Confidence: HIGH

The mapping includes intelligent defaults for:
- loaded_at → CURRENT_TIMESTAMP()
- data_source → 'staging_table_name'
- gdp_per_capita → gdp / population

Would you like me to explain any specific part of the mapping?
```

### Advantages
- 🎯 Natural language - no need to remember flags
- 💡 Explanations included
- 🔄 Interactive refinement
- 📊 Contextual help

## Mode 2: CLI Script (Best for Automation)

### When to Use
- ✅ Batch processing multiple datasets
- ✅ Scripting and automation
- ✅ CI/CD pipelines
- ✅ Scheduled jobs
- ✅ Direct file output needed

### How to Use

**Basic command:**
```bash
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output worldbank_mapping.json \
    --mode FIX
```

**In a script:**
```bash
#!/bin/bash
# map_all_datasets.sh

DATASETS=(
    "worldbank:worldbank_staging_dataset:worldbank_target_dataset"
    "lending:lending_staging_dataset:lending_target_dataset"
)

for dataset in "${DATASETS[@]}"; do
    IFS=':' read -r name source target <<< "$dataset"
    
    echo "Mapping $name..."
    python run_schema_mapper.py \
        --source "$source" \
        --target "$target" \
        --output "${name}_mapping.json" \
        --mode FIX
done
```

**In Python:**
```python
from agents.schema_mapping import generate_schema_mapping

result = generate_schema_mapping(
    source_dataset="worldbank_staging_dataset",
    target_dataset="worldbank_target_dataset",
    output_file="mapping.json",
    mode="FIX"
)

if result["status"] == "success":
    print(f"✓ Generated {len(result['mapping']['mappings'])} mappings")
else:
    print(f"✗ Error: {result['message']}")
```

### Advantages
- ⚡ Fast execution
- 🤖 Scriptable
- 📁 Direct file output
- 🔁 Repeatable

## Mode 3: REST API (Best for Integration)

### When to Use
- ✅ Microservices architecture
- ✅ Web application integration
- ✅ Remote access needed
- ✅ Multiple clients
- ✅ Cloud deployment

### How to Use

**Start the server:**
```bash
python api.py
# Server runs on http://localhost:8080
```

**Call from cURL:**
```bash
curl -X POST http://localhost:8080/generate-mapping \
  -H "Content-Type: application/json" \
  -d '{
    "source_dataset": "worldbank_staging_dataset",
    "target_dataset": "worldbank_target_dataset",
    "mode": "FIX"
  }'
```

**Call from Python:**
```python
import requests

response = requests.post(
    "http://localhost:8080/generate-mapping",
    json={
        "source_dataset": "worldbank_staging_dataset",
        "target_dataset": "worldbank_target_dataset",
        "mode": "FIX"
    }
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Mappings: {result['metadata']['num_mappings']}")
```

**Call from JavaScript:**
```javascript
const response = await fetch('http://localhost:8080/generate-mapping', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    source_dataset: 'worldbank_staging_dataset',
    target_dataset: 'worldbank_target_dataset',
    mode: 'FIX'
  })
});

const result = await response.json();
console.log(`Generated ${result.metadata.num_mappings} mappings`);
```

**Deploy to Cloud Run:**
```bash
gcloud run deploy schema-mapping-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### Advantages
- 🌐 Remote access
- 🔌 Easy integration
- 📈 Scalable
- 🔒 Can add authentication

## Choosing the Right Mode

### Decision Tree

```
Are you exploring/learning?
├─ YES → Use ADK Interactive (adk run)
└─ NO → Do you need automation?
    ├─ YES → Use CLI Script (run_schema_mapper.py)
    └─ NO → Do you need remote access?
        ├─ YES → Use REST API (api.py)
        └─ NO → Use CLI Script
```

### By Use Case

**Data Analyst/Scientist** → ADK Interactive
- Natural language queries
- Explanations of results
- Iterative exploration

**Data Engineer** → CLI Script
- Batch processing
- Pipeline integration
- Scheduled jobs

**Application Developer** → REST API
- Web app integration
- Microservices
- Remote access

**DevOps/SRE** → CLI Script or REST API
- Automation scripts
- CI/CD pipelines
- Monitoring integration

## Common Workflows

### Workflow 1: Initial Exploration → Production

```bash
# Step 1: Explore with ADK
adk run agents/schema_mapping
> "Show me tables in worldbank_staging_dataset"
> "Generate mapping to worldbank_target_dataset in REPORT mode"
> "What are the unmapped columns?"

# Step 2: Refine and save
> "Generate mapping in FIX mode"
# [Review the results]

# Step 3: Automate with CLI
python run_schema_mapper.py \
    --source worldbank_staging_dataset \
    --target worldbank_target_dataset \
    --output prod_mapping.json \
    --mode FIX

# Step 4: Deploy API for team access
gcloud run deploy schema-mapping-api --source .
```

### Workflow 2: Batch Processing

```bash
# Create mapping script
cat > map_all.sh << 'EOF'
#!/bin/bash
for source in staging_*; do
    target="${source/staging_/target_}"
    python run_schema_mapper.py \
        --source "$source" \
        --target "$target" \
        --output "mappings/${source}_mapping.json" \
        --mode FIX
done
EOF

chmod +x map_all.sh
./map_all.sh
```

### Workflow 3: Web Application Integration

```python
# Flask app example
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
MAPPING_API = "https://your-api.run.app/generate-mapping"

@app.route('/api/generate-mapping', methods=['POST'])
def generate_mapping():
    data = request.json
    
    # Call schema mapping API
    response = requests.post(MAPPING_API, json={
        "source_dataset": data['source'],
        "target_dataset": data['target'],
        "mode": data.get('mode', 'FIX')
    })
    
    return jsonify(response.json())
```

## Tips and Best Practices

### For ADK Interactive

1. **Start broad, then narrow**: Ask general questions first
2. **Use REPORT before FIX**: Understand gaps before applying defaults
3. **Ask for explanations**: Agent can explain any part of the mapping
4. **Iterate**: Refine based on results

### For CLI Script

1. **Use FIX mode for automation**: Generates complete mappings
2. **Save outputs with timestamps**: `mapping_$(date +%Y%m%d).json`
3. **Check exit codes**: `if [ $? -eq 0 ]; then ...`
4. **Log outputs**: Redirect to log files for debugging

### For REST API

1. **Add authentication**: Don't expose publicly without auth
2. **Set timeouts**: Large datasets can take time
3. **Cache results**: Same mapping request can be cached
4. **Monitor usage**: Track API calls and errors

## Troubleshooting

### All Modes

**Issue**: "Permission denied"
```bash
gcloud auth application-default login
```

**Issue**: "Dataset not found"
```bash
bq ls  # Verify dataset exists
```

### ADK Interactive

**Issue**: "Agent not responding"
- Check Vertex AI is enabled
- Verify environment variables
- Try `test_local.py` for diagnostics

### CLI Script

**Issue**: "Import error"
```bash
pip install -r requirements.txt
```

### REST API

**Issue**: "Connection refused"
- Verify server is running: `ps aux | grep api.py`
- Check port: `lsof -i :8080`

## Next Steps

1. **Try all three modes** to find your preference
2. **Read mode-specific docs**:
   - ADK: `README_ADK.md`, `QUICKSTART_ADK.md`
   - CLI: `README.md`
   - API: `API_README.md`
3. **Integrate with your workflow**
4. **Share with your team**

---

**Need Help?**
- 📖 Check the README files
- 🧪 Run `test_local.py`
- 🔍 Review logs for errors
- ✅ Verify environment setup

