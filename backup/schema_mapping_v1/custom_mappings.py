"""Custom mapping overrides for user-directed schema mappings."""

from typing import Dict, List, Any, Optional


def apply_custom_overrides(mapping_analysis: Dict[str, Any], 
                          overrides: List[Dict[str, str]],
                          source_schema: Dict[str, Any],
                          target_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Apply custom user overrides to an automated mapping analysis.
    
    This allows users to correct or customize specific column mappings.
    
    Args:
        mapping_analysis: Original mapping analysis from schema_analyzer
        overrides: List of override instructions, each with:
            - source_column: Source column name
            - target_column: Target column name  
            - transformation: Optional transformation type
            - sql_expression: Optional custom SQL expression
        source_schema: Source table schema
        target_schema: Target table schema
            
    Returns:
        Updated mapping analysis with overrides applied
    """
    # Create a deep copy to avoid modifying original
    import copy
    updated_analysis = copy.deepcopy(mapping_analysis)
    mappings = updated_analysis['mappings']
    
    # Create column lookup dictionaries
    source_cols = {col['name']: col for col in source_schema['columns']}
    target_cols = {col['name']: col for col in target_schema['columns']}
    
    for override in overrides:
        source_col = override.get('source_column')
        target_col = override.get('target_column')
        
        if not target_col:
            continue  # Must have at least a target column
        
        # Find existing mapping for this target column
        existing_idx = None
        for i, mapping in enumerate(mappings):
            if mapping['target_column'] == target_col:
                existing_idx = i
                break
        
        # Get target column info from schema
        target_info = target_cols.get(target_col, {'name': target_col, 'type': 'STRING'})
        
        # Handle literal values or functions (no source column)
        if source_col is None:
            transformation = override.get('transformation', 'CUSTOM')
            sql_expression = override.get('sql_expression', 'NULL')
            
            new_mapping = {
                'source_column': '<literal/function>',  # Placeholder for display
                'source_type': target_info.get('type', 'STRING'),
                'target_column': target_col,
                'target_type': target_info.get('type', 'STRING'),
                'similarity_score': 100,  # User override = 100% confidence
                'type_compatible': True,
                'transformation': transformation,
                'sql_expression': sql_expression,
                'confidence': 'high'
            }
        else:
            # Column-to-column mapping
            source_info = source_cols.get(source_col, {'name': source_col, 'type': 'STRING'})
            
            # Determine transformation if not specified
            transformation = override.get('transformation')
            sql_expression = override.get('sql_expression')
            
            if not transformation or not sql_expression:
                # Use intelligent transformation based on types
                source_type = source_info.get('type', 'STRING')
                target_type = target_info.get('type', 'STRING')
                
                if source_type == target_type:
                    transformation = 'DIRECT'
                    sql_expression = f"`{source_col}`"
                elif target_type in ['INT64', 'INTEGER']:
                    transformation = 'CAST_TO_INT64'
                    sql_expression = f"SAFE_CAST(`{source_col}` AS INT64)"
                elif target_type in ['NUMERIC', 'DECIMAL', 'FLOAT64']:
                    transformation = 'CAST_TO_NUMERIC'
                    sql_expression = f"SAFE_CAST(`{source_col}` AS NUMERIC)"
                elif target_type == 'DATE':
                    transformation = 'PARSE_DATE'
                    sql_expression = f"SAFE.PARSE_DATE('%Y-%m-%d', `{source_col}`)"
                else:
                    transformation = 'CUSTOM_OVERRIDE'
                    sql_expression = f"CAST(`{source_col}` AS {target_type})"
            
            # Create new mapping
            new_mapping = {
                'source_column': source_col,
                'source_type': source_info.get('type', 'STRING'),
                'target_column': target_col,
                'target_type': target_info.get('type', 'STRING'),
                'similarity_score': 100,  # User override = 100% confidence
                'type_compatible': True,
                'transformation': transformation,
                'sql_expression': sql_expression,
                'confidence': 'high'
            }
        
        # Update or add the mapping
        if existing_idx is not None:
            mappings[existing_idx] = new_mapping
        else:
            mappings.append(new_mapping)
    
    # Recalculate stats
    updated_analysis['mapping_stats']['mapped_columns'] = len(mappings)
    updated_analysis['mapping_stats']['high_confidence'] = sum(
        1 for m in mappings if m['confidence'] == 'high'
    )
    updated_analysis['mapping_stats']['medium_confidence'] = sum(
        1 for m in mappings if m['confidence'] == 'medium'
    )
    updated_analysis['mapping_stats']['low_confidence'] = sum(
        1 for m in mappings if m['confidence'] == 'low'
    )
    
    return updated_analysis


def parse_mapping_instruction(instruction: str, 
                              source_schema: Dict[str, Any],
                              target_schema: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """Parse a natural language mapping instruction into an override.
    
    Examples:
        "map country_code to country_key"
        "use country_code for country_key"
        "set data_source to 'staging_gdp'"
        "set loaded_at to CURRENT_TIMESTAMP()"
        
    Args:
        instruction: Natural language instruction
        source_schema: Source table schema
        target_schema: Target table schema
        
    Returns:
        Override dictionary or None if can't parse
    """
    instruction_lower = instruction.lower()
    
    # Get all column names
    source_cols = [col['name'] for col in source_schema['columns']]
    target_cols = [col['name'] for col in target_schema['columns']]
    
    # Check for literal/function patterns first (no source column)
    # Pattern: "set X to 'literal'" or "set X to FUNCTION()"
    literal_patterns = [
        ('set', 'to'),
        ('add', 'as'),
        ('populate', 'with'),
    ]
    
    for pattern_start, pattern_end in literal_patterns:
        if pattern_start in instruction_lower and pattern_end in instruction_lower:
            parts = instruction_lower.split(pattern_start)[1].split(pattern_end)
            if len(parts) == 2:
                potential_target = parts[0].strip()
                potential_value = parts[1].strip()
                
                # Find target column
                target_match = None
                for col in target_cols:
                    if col.lower() in potential_target or potential_target in col.lower():
                        target_match = col
                        break
                
                if target_match:
                    # Check if it's a literal string (in quotes)
                    if "'" in potential_value or '"' in potential_value:
                        # Extract the literal value
                        literal_value = potential_value.strip("'\"")
                        target_type = next(
                            (c['type'] for c in target_schema['columns'] if c['name'] == target_match),
                            'STRING'
                        )
                        
                        return {
                            'source_column': None,  # No source column
                            'target_column': target_match,
                            'source_type': target_type,
                            'target_type': target_type,
                            'sql_expression': f"CAST('{literal_value}' AS {target_type})",
                            'transformation': 'LITERAL_VALUE',
                            'is_literal': True
                        }
                    
                    # Check if it's a function (contains parentheses)
                    elif '(' in potential_value and ')' in potential_value:
                        # It's a function call
                        function_name = potential_value.upper()
                        target_type = next(
                            (c['type'] for c in target_schema['columns'] if c['name'] == target_match),
                            'TIMESTAMP'
                        )
                        
                        return {
                            'source_column': None,  # No source column
                            'target_column': target_match,
                            'source_type': target_type,
                            'target_type': target_type,
                            'sql_expression': function_name,
                            'transformation': 'FUNCTION',
                            'is_function': True
                        }
    
    # Pattern 2: Column-to-column mapping "map X to Y" or "use X for Y"
    column_patterns = [
        ('map', 'to'),
        ('use', 'for'),
        ('change', 'to use'),
    ]
    
    for pattern_start, pattern_end in column_patterns:
        if pattern_start in instruction_lower and pattern_end in instruction_lower:
            parts = instruction_lower.split(pattern_start)[1].split(pattern_end)
            if len(parts) == 2:
                potential_source = parts[0].strip()
                potential_target = parts[1].strip()
                
                # Find matching columns
                source_match = None
                target_match = None
                
                for col in source_cols:
                    if col.lower() in potential_source or potential_source in col.lower():
                        source_match = col
                        break
                
                for col in target_cols:
                    if col.lower() in potential_target or potential_target in col.lower():
                        target_match = col
                        break
                
                if source_match and target_match:
                    # Get column types
                    source_type = next(
                        (c['type'] for c in source_schema['columns'] if c['name'] == source_match),
                        'STRING'
                    )
                    target_type = next(
                        (c['type'] for c in target_schema['columns'] if c['name'] == target_match),
                        'STRING'
                    )
                    
                    return {
                        'source_column': source_match,
                        'target_column': target_match,
                        'source_type': source_type,
                        'target_type': target_type,
                        'sql_expression': f"`{source_match}`"
                    }
    
    return None

