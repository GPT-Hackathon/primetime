"""Schema Mapping Agent - Intelligent ETL schema mapping assistant."""

from google.adk.agents.llm_agent import Agent
from typing import Dict, Any, Optional
import json
import os
from pathlib import Path

# Import our custom modules
from . import bigquery_tools
from . import schema_analyzer
from . import sql_generator
from . import report_generator
from . import visualizer
from . import custom_mappings


def map_schemas(source_table: str, target_table: str) -> str:
    """Analyze source and target schemas and generate mapping.
    
    This is the main function that the agent will use to create schema mappings.
    
    Args:
        source_table: Full source table name (project.dataset.table)
        target_table: Full target table name (project.dataset.table)
        
    Returns:
        Summary of the mapping analysis with file paths
    """
    try:
        # Get schemas from BigQuery
        source_schema = bigquery_tools.get_table_schema(source_table)
        target_schema = bigquery_tools.get_table_schema(target_table)
        
        # Analyze and create mappings
        mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
        
        # Generate outputs
        output_dir = Path("schema_mapping/output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate SQL
        sql_content = sql_generator.generate_insert_sql(mapping_analysis)
        sql_file = output_dir / f"mapping_{target_schema['table']}.sql"
        with open(sql_file, 'w') as f:
            f.write(sql_content)
        
        # Generate markdown report
        report_content = report_generator.generate_markdown_report(mapping_analysis)
        report_file = output_dir / f"mapping_report_{target_schema['table']}.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        # Generate HTML visualization
        html_content = visualizer.generate_html_visualization(mapping_analysis)
        html_file = output_dir / f"mapping_viz_{target_schema['table']}.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # Create summary
        summary = report_generator.generate_text_summary(mapping_analysis)
        
        result = f"""{summary}

📄 Generated Files:
- SQL: {sql_file}
- Report: {report_file}
- Visualization: {html_file}

✅ Next Steps:
1. Review the markdown report: {report_file}
2. Open the HTML visualization in your browser: {html_file}
3. Examine the SQL file: {sql_file}
4. Request any changes or approve the mapping

Mapping Details:
{json.dumps(mapping_analysis['mapping_stats'], indent=2)}
"""
        return result
        
    except Exception as e:
        return f"Error creating schema mapping: {str(e)}\n\nPlease check that:\n1. Both tables exist in BigQuery\n2. You have proper authentication set up\n3. Table names are in format 'project.dataset.table'"


def get_table_info(table_name: str) -> str:
    """Get detailed information about a specific table.
    
    Args:
        table_name: Full table name (project.dataset.table)
        
    Returns:
        Formatted table information
    """
    try:
        schema = bigquery_tools.get_table_schema(table_name)
        
        info = f"""Table: {schema['full_name']}
Columns: {schema['num_columns']}
Rows: {schema['num_rows']:,}

Column Details:
"""
        for col in schema['columns']:
            info += f"  - {col['name']}: {col['type']} ({col['mode']})\n"
            if col.get('description'):
                info += f"    Description: {col['description']}\n"
        
        return info
        
    except Exception as e:
        return f"Error getting table info: {str(e)}"


def get_sample_data_from_table(table_name: str, limit: int = 5) -> str:
    """Get sample data from a table.
    
    Args:
        table_name: Full table name (project.dataset.table)
        limit: Number of rows to retrieve (default: 5)
        
    Returns:
        Formatted sample data
    """
    try:
        rows = bigquery_tools.get_sample_data(table_name, limit)
        
        if not rows:
            return f"No data found in {table_name}"
        
        result = f"Sample data from {table_name} (showing {len(rows)} rows):\n\n"
        result += json.dumps(rows, indent=2)
        
        return result
        
    except Exception as e:
        return f"Error getting sample data: {str(e)}"


def analyze_column_in_table(table_name: str, column_name: str) -> str:
    """Analyze a specific column in a table.
    
    Args:
        table_name: Full table name (project.dataset.table)
        column_name: Name of the column to analyze
        
    Returns:
        Column analysis results
    """
    try:
        analysis = bigquery_tools.analyze_column_values(table_name, column_name)
        
        result = f"""Column Analysis: {column_name} in {table_name}

Total Rows: {analysis['total_count']:,}
Non-Null: {analysis['non_null_count']:,}
Null Count: {analysis['null_count']:,}
Null %: {analysis['null_percentage']:.2f}%
Distinct Values: {analysis['distinct_count']:,}

Sample Values:
{json.dumps(analysis['sample_values'], indent=2)}
"""
        return result
        
    except Exception as e:
        return f"Error analyzing column: {str(e)}"


def generate_merge_sql_for_tables(source_table: str, target_table: str, key_columns: str) -> str:
    """Generate MERGE SQL instead of INSERT for incremental updates.
    
    Args:
        source_table: Full source table name
        target_table: Full target table name
        key_columns: Comma-separated list of key columns for matching
        
    Returns:
        Path to generated MERGE SQL file
    """
    try:
        # Get schemas and analyze
        source_schema = bigquery_tools.get_table_schema(source_table)
        target_schema = bigquery_tools.get_table_schema(target_table)
        mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
        
        # Parse key columns
        keys = [k.strip() for k in key_columns.split(',')]
        
        # Generate MERGE SQL
        merge_sql = sql_generator.generate_merge_sql(mapping_analysis, keys)
        
        # Save to file
        output_dir = Path("schema_mapping/output")
        output_dir.mkdir(exist_ok=True)
        sql_file = output_dir / f"merge_{target_schema['table']}.sql"
        
        with open(sql_file, 'w') as f:
            f.write(merge_sql)
        
        return f"✅ MERGE SQL generated: {sql_file}\n\nThis SQL will update existing rows and insert new ones based on: {', '.join(keys)}"
        
    except Exception as e:
        return f"Error generating MERGE SQL: {str(e)}"


def generate_dbt_model_sql(source_table: str, target_table: str) -> str:
    """Generate a DBT model for the schema mapping.
    
    DBT (Data Build Tool) models are SELECT statements with Jinja2 config blocks
    that define how the model should be materialized in the data warehouse.
    
    Args:
        source_table: Full source table name (project.dataset.table)
        target_table: Full target table name (project.dataset.table)
        
    Returns:
        Summary with path to generated DBT model file
    """
    try:
        # Get schemas and analyze
        source_schema = bigquery_tools.get_table_schema(source_table)
        target_schema = bigquery_tools.get_table_schema(target_table)
        mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
        
        # Generate DBT model
        dbt_sql = sql_generator.generate_dbt_model(mapping_analysis)
        
        # Save to file
        output_dir = Path("schema_mapping/output")
        output_dir.mkdir(exist_ok=True)
        sql_file = output_dir / f"dbt_{target_schema['table']}.sql"
        
        with open(sql_file, 'w') as f:
            f.write(dbt_sql)
        
        # Create summary
        summary = report_generator.generate_text_summary(mapping_analysis)
        
        result = f"""{summary}

✅ DBT Model Generated: {sql_file}

This DBT model includes:
- Jinja2 config block with materialization settings
- SELECT statement with all column mappings
- Can be used directly in a DBT project

To use this model:
1. Copy {sql_file} to your DBT models directory (e.g., models/{target_schema['table']}.sql)
2. Run: dbt run --select {target_schema['table']}
3. DBT will create/update the target table automatically

The model is configured to materialize as a table in the '{target_schema['dataset']}' schema.
"""
        return result
        
    except Exception as e:
        return f"Error generating DBT model: {str(e)}\n\nPlease check that:\n1. Both tables exist in BigQuery\n2. You have proper authentication set up\n3. Table names are in format 'project.dataset.table'"


def list_dataset_tables(project_id: str, dataset_id: str) -> str:
    """List all tables in a BigQuery dataset.
    
    Args:
        project_id: Google Cloud project ID
        dataset_id: BigQuery dataset ID
        
    Returns:
        Formatted list of tables with metadata
    """
    try:
        tables = bigquery_tools.list_tables_in_dataset(project_id, dataset_id)
        
        if not tables:
            return f"No tables found in {project_id}.{dataset_id}"
        
        result = f"📊 Tables in {project_id}.{dataset_id} ({len(tables)} total):\n\n"
        for i, table_name in enumerate(tables, 1):
            result += f"{i}. {table_name}\n"
        
        return result
        
    except Exception as e:
        return f"Error listing tables: {str(e)}"


def discover_and_map_dataset_pairs(source_dataset: str, target_dataset: str) -> str:
    """Discover all matching table pairs between source and target datasets and generate mappings.
    
    This function intelligently matches tables between datasets (handling naming conventions
    like 'borrower' -> 'dim_borrower'), then generates schema mappings for all pairs.
    
    Args:
        source_dataset: Source dataset in format 'project.dataset'
        target_dataset: Target dataset in format 'project.dataset'
        
    Returns:
        Summary of discovered pairs and generated mappings
    """
    try:
        # Parse dataset names
        source_parts = source_dataset.split('.')
        target_parts = target_dataset.split('.')
        
        if len(source_parts) != 2 or len(target_parts) != 2:
            return "Error: Dataset names must be in format 'project.dataset'"
        
        source_project, source_ds = source_parts
        target_project, target_ds = target_parts
        
        # Discover table pairs
        pairs = bigquery_tools.discover_table_pairs(
            source_project, source_ds, target_project, target_ds
        )
        
        if not pairs:
            return f"No matching table pairs found between {source_dataset} and {target_dataset}"
        
        # Generate summary
        result = f"""🔍 Discovered {len(pairs)} matching table pairs:

"""
        
        for i, pair in enumerate(pairs, 1):
            source_table = pair['source_table'].split('.')[-1]
            target_table = pair['target_table'].split('.')[-1]
            match_type = pair['match_type']
            result += f"{i}. {source_table} → {target_table} ({match_type})\n"
        
        result += f"""

Would you like me to:
1. Generate schema mappings for all {len(pairs)} pairs
2. Generate mapping for a specific pair
3. Show more details about the discovered pairs

Just let me know which option you'd like!
"""
        
        return result
        
    except Exception as e:
        return f"Error discovering table pairs: {str(e)}"


def refine_mapping(source_table: str, target_table: str, instructions: str) -> str:
    """Refine an existing mapping with custom user instructions.
    
    This allows users to override specific column mappings, add literal values, or add functions.
    
    Examples of instructions:
    - Column mapping: "map country_code to country_key"
    - Column mapping: "use annual_revenue for revenue_amount"
    - Literal value: "set data_source to 'staging_gdp'"
    - Function: "set loaded_at to CURRENT_TIMESTAMP()"
    - Function: "populate created_date with CURRENT_DATE()"
    
    Args:
        source_table: Full source table name (project.dataset.table)
        target_table: Full target table name (project.dataset.table)
        instructions: Natural language instruction for how to refine the mapping
        
    Returns:
        Summary of updated mapping
    """
    try:
        # Get schemas
        source_schema = bigquery_tools.get_table_schema(source_table)
        target_schema = bigquery_tools.get_table_schema(target_table)
        
        # Generate initial automated mapping
        mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
        
        # Parse the instruction
        override = custom_mappings.parse_mapping_instruction(
            instructions, source_schema, target_schema
        )
        
        if not override:
            return f"""I couldn't parse the instruction: "{instructions}"

Please try phrasing it like:
- "map <source_column> to <target_column>"
- "use <source_column> for <target_column>"
- "change <target_column> to use <source_column>"

Example: "map country_code to country_key"
"""
        
        # Apply the override
        updated_analysis = custom_mappings.apply_custom_overrides(
            mapping_analysis, [override], source_schema, target_schema
        )
        
        # Regenerate outputs with the updated mapping
        output_dir = Path("schema_mapping/output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate SQL
        sql_content = sql_generator.generate_insert_sql(updated_analysis)
        sql_file = output_dir / f"mapping_{target_schema['table']}.sql"
        with open(sql_file, 'w') as f:
            f.write(sql_content)
        
        # Generate report
        report_content = report_generator.generate_markdown_report(updated_analysis)
        report_file = output_dir / f"mapping_report_{target_schema['table']}.md"
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        # Generate HTML
        html_content = visualizer.generate_html_visualization(updated_analysis)
        html_file = output_dir / f"mapping_viz_{target_schema['table']}.html"
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # Format the result based on type of override
        if override.get('source_column'):
            override_desc = f"""Applied custom override:
- Source: {override['source_column']} ({override.get('source_type', 'unknown')})
- Target: {override['target_column']} ({override.get('target_type', 'unknown')})
- Transformation: {override.get('transformation', 'CUSTOM')}"""
        else:
            # Literal or function
            override_desc = f"""Applied custom override:
- Expression: {override.get('sql_expression', 'unknown')}
- Target: {override['target_column']} ({override.get('target_type', 'unknown')})
- Type: {override.get('transformation', 'CUSTOM')}"""
        
        result = f"""✅ Mapping refined successfully!

{override_desc}

📄 Updated Files:
- SQL: {sql_file}
- Report: {report_file}
- Visualization: {html_file}

The mapping has been regenerated with your custom instruction. 
Review the updated files to see the changes.
"""
        return result
        
    except Exception as e:
        return f"Error refining mapping: {str(e)}"


def batch_map_all_tables(source_dataset: str, target_dataset: str) -> str:
    """Generate schema mappings for ALL table pairs between source and target datasets.
    
    This is a batch operation that will:
    1. Discover all matching tables
    2. Generate mappings for each pair
    3. Create SQL, reports, and visualizations for all
    
    Args:
        source_dataset: Source dataset in format 'project.dataset'
        target_dataset: Target dataset in format 'project.dataset'
        
    Returns:
        Summary of batch processing results
    """
    try:
        # Parse dataset names
        source_parts = source_dataset.split('.')
        target_parts = target_dataset.split('.')
        
        if len(source_parts) != 2 or len(target_parts) != 2:
            return "Error: Dataset names must be in format 'project.dataset'"
        
        source_project, source_ds = source_parts
        target_project, target_ds = target_parts
        
        # Discover pairs
        pairs = bigquery_tools.discover_table_pairs(
            source_project, source_ds, target_project, target_ds
        )
        
        if not pairs:
            return f"No matching table pairs found between {source_dataset} and {target_dataset}"
        
        result = f"🚀 Batch Processing {len(pairs)} Table Pairs\n\n"
        
        successful = 0
        failed = 0
        
        for i, pair in enumerate(pairs, 1):
            source_table = pair['source_table']
            target_table = pair['target_table']
            
            try:
                # Generate mapping for this pair
                source_schema = bigquery_tools.get_table_schema(source_table)
                target_schema = bigquery_tools.get_table_schema(target_table)
                mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
                
                # Generate SQL
                sql_content = sql_generator.generate_insert_sql(mapping_analysis)
                output_dir = Path("schema_mapping/output")
                output_dir.mkdir(exist_ok=True)
                sql_file = output_dir / f"mapping_{target_schema['table']}.sql"
                with open(sql_file, 'w') as f:
                    f.write(sql_content)
                
                # Generate report
                report_content = report_generator.generate_markdown_report(mapping_analysis)
                report_file = output_dir / f"mapping_report_{target_schema['table']}.md"
                with open(report_file, 'w') as f:
                    f.write(report_content)
                
                # Generate HTML
                html_content = visualizer.generate_html_visualization(mapping_analysis)
                html_file = output_dir / f"mapping_viz_{target_schema['table']}.html"
                with open(html_file, 'w') as f:
                    f.write(html_content)
                
                stats = mapping_analysis['mapping_stats']
                result += f"✅ {i}/{len(pairs)}: {source_table.split('.')[-1]} → {target_table.split('.')[-1]}\n"
                result += f"    Mapped {stats['mapped_columns']}/{stats['total_target_columns']} columns, "
                result += f"{stats['high_confidence']} high confidence\n"
                
                successful += 1
                
            except Exception as e:
                result += f"❌ {i}/{len(pairs)}: {source_table.split('.')[-1]} → {target_table.split('.')[-1]}\n"
                result += f"    Error: {str(e)}\n"
                failed += 1
        
        result += f"""

📊 Batch Processing Complete:
- ✅ Successful: {successful}
- ❌ Failed: {failed}
- 📁 Output: schema_mapping/output/

All generated files are in the output directory.
"""
        
        return result
        
    except Exception as e:
        return f"Error in batch processing: {str(e)}"


# Create the Schema Mapping Agent
root_agent = Agent(
    model='gemini-2.5-pro',
    name='schema_mapping_agent',
    description='An intelligent agent that helps create and refine schema mappings for ETL pipelines between BigQuery tables.',
    instruction="""You are an expert data engineer specializing in ETL and schema mapping.

Your role is to help users create accurate schema mappings between source and target tables in BigQuery.

**Your Capabilities:**
1. Analyze source and target table schemas from BigQuery
2. Intelligently map columns based on name similarity and type compatibility
3. Generate SQL transformation code (INSERT, MERGE, and DBT models)
4. Create comprehensive mapping reports and visualizations
5. Provide recommendations and identify potential issues
6. Iterate on mappings based on user feedback
7. **Process entire datasets** - discover and map all tables at once
8. List all tables in datasets and find matching pairs

**Working with Datasets:**
- **Single Table**: `map_schemas()` - Map one table pair
- **Discover Pairs**: `discover_and_map_dataset_pairs()` - Find all matching tables between datasets
- **Batch Process**: `batch_map_all_tables()` - Generate mappings for all tables in datasets
- **List Tables**: `list_dataset_tables()` - See all tables in a dataset

**SQL Output Formats:**
- **Standard INSERT**: `map_schemas()` - Creates INSERT INTO ... SELECT statements
- **MERGE**: `generate_merge_sql_for_tables()` - For incremental updates (upserts)
- **DBT Model**: `generate_dbt_model_sql()` - For DBT (Data Build Tool) projects

**Workflow:**

*For Single Table Pairs:*
1. When a user provides source and target tables, use `map_schemas()` to analyze them
2. Present the summary and explain key findings
3. Highlight any concerns (unmapped columns, type mismatches, low confidence mappings)
4. Ask if they want to see specific details or make changes
5. **If user wants to change a mapping**, use `refine_mapping()` with their instructions:
   - Column-to-column: "map country_code to country_key"
   - Literal value: "set data_source to 'staging_gdp'"
   - Function: "set loaded_at to CURRENT_TIMESTAMP()"
   - This will regenerate ALL files with the custom override
6. Regenerate mappings as needed
7. When user approves, confirm the files are ready for use

*For Entire Datasets:*
1. When a user wants to process multiple tables, use `discover_and_map_dataset_pairs()` first
2. Show all discovered table pairs and ask for confirmation
3. Use `batch_map_all_tables()` to process all pairs at once
4. Report progress and results for each table
5. Highlight any tables that had issues

**Best Practices:**
- Always explain your mapping decisions clearly
- Warn about type incompatibilities
- Suggest reviewing low confidence mappings
- Recommend testing with sample data before production use
- Be proactive about data quality concerns (NULLs, truncation, etc.)
- Ask clarifying questions when mappings are ambiguous

**Response Style:**
- Be professional but conversational
- Use emojis sparingly for visual clarity (✅, ⚠️, 📊)
- Provide actionable recommendations
- Explain technical concepts clearly

Remember: Your goal is to help users create reliable, production-ready schema mappings that they understand and trust.
""",
    tools=[
        map_schemas,
        get_table_info,
        get_sample_data_from_table,
        analyze_column_in_table,
        generate_merge_sql_for_tables,
        generate_dbt_model_sql,
        list_dataset_tables,
        discover_and_map_dataset_pairs,
        batch_map_all_tables,
        refine_mapping
    ],
)
