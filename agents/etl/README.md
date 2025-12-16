Code Review & Design Philosophy
The request is for a generic script. This means the script should not be hardcoded for the specific World Bank data but should be intelligent enough to parse the structure of the provided JSON rules and generate SQL accordingly.

Here are the principles I've followed in crafting the script:

Dynamic Parsing: The script reads the JSON file and iterates through the mappings array. It doesn't assume fixed table or column names.
Transformation Logic: It correctly identifies and applies transformations specified in the transformation field for each column.
Handling Multiple Sources: The script detects when a source_table entry contains multiple tables (comma-separated). It then correctly constructs a UNION ALL or a PIVOT query based on the mapping patterns.
Default Value Injection: For unmapped_target_columns, the script intelligently injects sensible defaults (CURRENT_TIMESTAMP() for timestamp-like columns, 'Default' for others) and adds comments to highlight them.
Code Quality & Readability: The logic is broken down into smaller, single-purpose functions (generate_select_expression, generate_single_source_sql, generate_union_sql, etc.). This makes the code easier to understand, maintain, and extend.
Clarity and User Guidance: The script prints each generated SQL statement with a descriptive header. For tables that have no source mapping, it prints a clear warning and a placeholder SQL template.
The Generic Python Script
Here is the Python script. You can save it as generate_etl_sql.py and run it. It will read a file named mapping_rules.json (containing the JSON you provided) from the same directory.


The Generic Python Script
Here is the Python script. You can save it as generate_etl_sql.py and run it. It will read a file named mapping_rules.json (containing the JSON you provided) from the same directory.

How to Use
Save the Files:

Save the Python code above as generate_etl_sql.py.
Save the large JSON you provided in the prompt into a file named mapping_rules.json in the same directory.
Run from Terminal:
python generate_etl_sql.py

3. Output: The script will print the complete, ordered set of SQL INSERT statements to your console, ready to be executed in BigQuery. The output will be identical to the SQL I provided in the previous answer, but generated dynamically from the JSON rules.

This generic approach ensures that if your mapping rules change or if you get a new set of rules for a different project, you can simply update the JSON file and rerun the script to get the new SQL.
