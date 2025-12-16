"""Example usage of the Schema Mapping Agent."""

import os
from pathlib import Path

# Example 1: Direct function calls (non-interactive)
def example_direct_mapping():
    """Example of using the mapping functions directly."""
    print("=" * 80)
    print("Example 1: Direct Schema Mapping")
    print("=" * 80)
    
    from schema_mapping.agent import map_schemas
    
    # Define your tables
    source_table = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    target_table = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    
    print(f"\nMapping from:")
    print(f"  Source: {source_table}")
    print(f"  Target: {target_table}\n")
    
    # Generate mapping
    result = map_schemas(source_table, target_table)
    print(result)
    
    print("\n✅ Check the schema_mapping/output/ directory for generated files!")


# Example 2: Using individual tools
def example_individual_tools():
    """Example of using individual tools for more control."""
    print("\n" + "=" * 80)
    print("Example 2: Using Individual Tools")
    print("=" * 80)
    
    from schema_mapping import bigquery_tools, schema_analyzer, sql_generator
    
    source_table = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    target_table = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    
    # Step 1: Get schemas
    print("\n1. Getting table schemas...")
    source_schema = bigquery_tools.get_table_schema(source_table)
    target_schema = bigquery_tools.get_table_schema(target_table)
    print(f"   Source: {source_schema['num_columns']} columns")
    print(f"   Target: {target_schema['num_columns']} columns")
    
    # Step 2: Analyze mappings
    print("\n2. Analyzing mappings...")
    mapping_analysis = schema_analyzer.analyze_mapping(source_schema, target_schema)
    print(f"   Mapped: {mapping_analysis['mapping_stats']['mapped_columns']} columns")
    print(f"   High confidence: {mapping_analysis['mapping_stats']['high_confidence']}")
    
    # Step 3: Generate SQL
    print("\n3. Generating SQL...")
    sql_content = sql_generator.generate_insert_sql(mapping_analysis)
    print(f"   Generated {len(sql_content)} characters of SQL")
    
    # Step 4: Save to file
    output_file = Path("schema_mapping/output/example_mapping.sql")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(sql_content)
    print(f"   Saved to: {output_file}")
    
    print("\n✅ Done!")


# Example 3: Interactive agent conversation
def example_interactive_agent():
    """Example of chatting with the agent."""
    print("\n" + "=" * 80)
    print("Example 3: Interactive Agent")
    print("=" * 80)
    
    from schema_mapping.agent import root_agent
    
    # Example conversation
    messages = [
        "Create a schema mapping from ccibt-hack25ww7-750.test_staging_dataset.borrower to ccibt-hack25ww7-750.test_dataset.dim_borrower",
        "Show me details about the borrower_id mapping",
        "What's the confidence level for all mappings?"
    ]
    
    conversation_history = []
    
    for user_message in messages:
        print(f"\n🧑 User: {user_message}")
        
        response = root_agent.generate_response(
            message=user_message,
            conversation_history=conversation_history
        )
        
        print(f"\n🤖 Agent: {response}")
        
        # Update history
        conversation_history.append({"role": "user", "content": user_message})
        conversation_history.append({"role": "agent", "content": response})
        
        print("\n" + "-" * 80)


# Example 4: Generate MERGE SQL
def example_merge_sql():
    """Example of generating MERGE SQL for incremental updates."""
    print("\n" + "=" * 80)
    print("Example 4: Generate MERGE SQL")
    print("=" * 80)
    
    from schema_mapping.agent import generate_merge_sql_for_tables
    
    source_table = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    target_table = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    key_columns = "borrower_id"
    
    print(f"\nGenerating MERGE SQL...")
    print(f"  Key columns: {key_columns}\n")
    
    result = generate_merge_sql_for_tables(source_table, target_table, key_columns)
    print(result)


# Example 4b: Generate DBT Model
def example_dbt_model():
    """Example of generating DBT model for schema mapping."""
    print("\n" + "=" * 80)
    print("Example 4b: Generate DBT Model")
    print("=" * 80)
    
    from schema_mapping.agent import generate_dbt_model_sql
    
    source_table = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    target_table = "ccibt-hack25ww7-750.test_dataset.dim_borrower"
    
    print(f"\nGenerating DBT model...\n")
    
    result = generate_dbt_model_sql(source_table, target_table)
    print(result)


# Example 5: Analyze specific columns
def example_column_analysis():
    """Example of analyzing specific columns."""
    print("\n" + "=" * 80)
    print("Example 5: Column Analysis")
    print("=" * 80)
    
    from schema_mapping.agent import analyze_column_in_table
    
    table_name = "ccibt-hack25ww7-750.test_staging_dataset.borrower"
    column_name = "annual_revenue"
    
    print(f"\nAnalyzing column: {column_name}\n")
    
    result = analyze_column_in_table(table_name, column_name)
    print(result)


# Example 6: Batch processing multiple tables
def example_batch_processing():
    """Example of processing multiple table pairs."""
    print("\n" + "=" * 80)
    print("Example 6: Batch Processing")
    print("=" * 80)
    
    from schema_mapping.agent import map_schemas
    
    # Define multiple table pairs
    table_pairs = [
        ("ccibt-hack25ww7-750.test_staging_dataset.borrower", 
         "ccibt-hack25ww7-750.test_dataset.dim_borrower"),
        # Add more pairs as needed
        # ("source.loan", "target.dim_loan"),
        # ("source.payment", "target.fact_payment"),
    ]
    
    print(f"\nProcessing {len(table_pairs)} table pairs...\n")
    
    for i, (source, target) in enumerate(table_pairs, 1):
        print(f"\n{'='*60}")
        print(f"Pair {i}/{len(table_pairs)}: {source.split('.')[-1]} → {target.split('.')[-1]}")
        print('='*60)
        
        try:
            result = map_schemas(source, target)
            print(f"\n✅ Success!\n")
            # Print just the summary, not full output
            lines = result.split('\n')
            print('\n'.join(lines[:10]))  # First 10 lines
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
    
    print("\n✅ Batch processing complete!")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Schema Mapping Agent Examples" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Check authentication
    if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
        print("\n⚠️  Warning: GOOGLE_APPLICATION_CREDENTIALS not set")
        print("   Run: gcloud auth application-default login\n")
    
    # Run examples
    try:
        # Uncomment the examples you want to run:
        
        example_direct_mapping()
        # example_individual_tools()
        # example_interactive_agent()
        # example_merge_sql()
        # example_dbt_model()
        # example_column_analysis()
        # example_batch_processing()
        
    except Exception as e:
        print(f"\n❌ Error running examples: {str(e)}")
        print("\nMake sure:")
        print("1. You're authenticated with Google Cloud")
        print("2. The tables exist in BigQuery")
        print("3. You have necessary permissions")
    
    print("\n" + "=" * 80)
    print("Examples completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

