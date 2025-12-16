"""Generate human-readable mapping reports."""

from typing import Dict, Any
from datetime import datetime


def generate_markdown_report(mapping_analysis: Dict[str, Any]) -> str:
    """Generate a markdown report for schema mapping.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        
    Returns:
        Markdown-formatted report string
    """
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    mappings = mapping_analysis["mappings"]
    stats = mapping_analysis["mapping_stats"]
    
    lines = []
    
    # Header
    lines.append("# Schema Mapping Report")
    lines.append("")
    lines.append(f"**Source Table:** `{source_table}`")
    lines.append(f"**Target Table:** `{target_table}`")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Summary statistics with emojis
    lines.append("## Mapping Summary")
    lines.append("")
    mapped_percentage = (stats["mapped_columns"] / stats["total_target_columns"] * 100) if stats["total_target_columns"] > 0 else 0
    lines.append(f"- ✅ **Mapped:** {stats['mapped_columns']}/{stats['total_target_columns']} columns ({mapped_percentage:.1f}%)")
    lines.append(f"- 🎯 **High Confidence:** {stats['high_confidence']} mappings")
    lines.append(f"- ⚠️ **Medium Confidence:** {stats['medium_confidence']} mappings")
    lines.append(f"- ❗ **Low Confidence:** {stats['low_confidence']} mappings")
    
    if stats["unmapped_target"] > 0:
        lines.append(f"- 🔍 **Unmapped Target Columns:** {stats['unmapped_target']}")
    
    if stats["unmapped_source"] > 0:
        lines.append(f"- ℹ️ **Unused Source Columns:** {stats['unmapped_source']}")
    
    lines.append("")
    
    # Column mappings table
    lines.append("## Column Mappings")
    lines.append("")
    lines.append("| Source Column | Source Type | → | Target Column | Target Type | Transformation | Confidence |")
    lines.append("|---------------|-------------|---|---------------|-------------|----------------|------------|")
    
    for mapping in mappings:
        source_col = mapping["source_column"]
        source_type = mapping["source_type"]
        target_col = mapping["target_column"]
        target_type = mapping["target_type"]
        transformation = mapping["transformation"]
        confidence = mapping["confidence"]
        similarity = mapping["similarity_score"]
        
        # Add emoji for confidence
        conf_emoji = "🟢" if confidence == "high" else "🟡" if confidence == "medium" else "🔴"
        conf_display = f"{conf_emoji} {confidence.title()} ({similarity}%)"
        
        lines.append(f"| `{source_col}` | {source_type} | → | `{target_col}` | {target_type} | {transformation} | {conf_display} |")
    
    lines.append("")
    
    # Detailed mapping notes
    lines.append("## Mapping Details")
    lines.append("")
    
    for i, mapping in enumerate(mappings, 1):
        lines.append(f"### {i}. `{mapping['source_column']}` → `{mapping['target_column']}`")
        lines.append("")
        lines.append(f"- **Transformation:** `{mapping['transformation']}`")
        lines.append(f"- **SQL Expression:** `{mapping['sql_expression']}`")
        lines.append(f"- **Type Compatibility:** {'✅ Compatible' if mapping['type_compatible'] else '❌ Incompatible'}")
        lines.append(f"- **Confidence:** {mapping['confidence'].title()} (similarity: {mapping['similarity_score']}%)")
        
        if not mapping['type_compatible']:
            lines.append("")
            lines.append("> ⚠️ **Warning:** Type mismatch detected. Please review this mapping carefully.")
        
        lines.append("")
    
    # Unmapped columns
    if mapping_analysis.get("unmapped_target_columns"):
        lines.append("## ⚠️ Unmapped Target Columns")
        lines.append("")
        lines.append("The following target columns were not mapped from the source:")
        lines.append("")
        for col in mapping_analysis["unmapped_target_columns"]:
            lines.append(f"- `{col}` - No matching source column found")
        lines.append("")
        lines.append("> **Action Required:** These columns will be NULL unless you manually add mappings or provide default values.")
        lines.append("")
    
    if mapping_analysis.get("unmapped_source_columns"):
        lines.append("## ℹ️ Unused Source Columns")
        lines.append("")
        lines.append("The following source columns are not mapped to any target column:")
        lines.append("")
        for col_info in mapping_analysis["unmapped_source_columns"]:
            best_match_info = f" (closest match: `{col_info['best_match']}` at {col_info['best_score']}%)" if col_info.get('best_match') else ""
            lines.append(f"- `{col_info['column']}` ({col_info['type']}){best_match_info}")
        lines.append("")
    
    # Recommendations
    lines.append("## 💡 Recommendations")
    lines.append("")
    
    if stats["low_confidence"] > 0:
        lines.append("1. **Review Low Confidence Mappings:** Carefully verify the mappings marked with low confidence.")
    
    if stats["unmapped_target"] > 0:
        lines.append("2. **Handle Unmapped Target Columns:** Decide whether to use NULL values, default values, or add explicit mappings.")
    
    type_mismatches = [m for m in mappings if not m["type_compatible"]]
    if type_mismatches:
        lines.append("3. **Verify Type Conversions:** Review type conversions, especially for incompatible types.")
    
    lines.append("4. **Test with Sample Data:** Run the generated SQL on a small data sample before full migration.")
    lines.append("5. **Validate Data Quality:** Check for NULL values, data truncation, and conversion errors.")
    lines.append("")
    
    # Next steps
    lines.append("## 📋 Next Steps")
    lines.append("")
    lines.append("1. Review this mapping report thoroughly")
    lines.append("2. Examine the generated SQL file")
    lines.append("3. Request any changes needed via the agent")
    lines.append("4. Once satisfied, approve the mapping")
    lines.append("5. Test the SQL with a small data sample")
    lines.append("6. Deploy to production ETL pipeline")
    lines.append("")
    
    return "\n".join(lines)


def generate_text_summary(mapping_analysis: Dict[str, Any]) -> str:
    """Generate a brief text summary of the mapping.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        
    Returns:
        Text summary string
    """
    stats = mapping_analysis["mapping_stats"]
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    
    mapped_percentage = (stats["mapped_columns"] / stats["total_target_columns"] * 100) if stats["total_target_columns"] > 0 else 0
    
    summary_parts = []
    summary_parts.append(f"Schema mapping: {source_table} → {target_table}")
    summary_parts.append(f"Mapped {stats['mapped_columns']}/{stats['total_target_columns']} columns ({mapped_percentage:.1f}%)")
    summary_parts.append(f"Confidence: {stats['high_confidence']} high, {stats['medium_confidence']} medium, {stats['low_confidence']} low")
    
    if stats["unmapped_target"] > 0:
        summary_parts.append(f"⚠️ {stats['unmapped_target']} target columns unmapped")
    
    if stats["low_confidence"] > 0:
        summary_parts.append(f"⚠️ {stats['low_confidence']} mappings need review")
    
    return "\n".join(summary_parts)

