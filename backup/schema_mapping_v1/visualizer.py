"""Generate HTML visualization for schema mappings."""

from typing import Dict, Any
from datetime import datetime
import html


def generate_html_visualization(mapping_analysis: Dict[str, Any]) -> str:
    """Generate an interactive HTML visualization of the schema mapping.
    
    Args:
        mapping_analysis: Mapping analysis from schema_analyzer
        
    Returns:
        HTML string with visualization
    """
    source_table = mapping_analysis["source_table"]
    target_table = mapping_analysis["target_table"]
    mappings = mapping_analysis["mappings"]
    stats = mapping_analysis["mapping_stats"]
    
    html_parts = []
    
    # HTML header
    html_parts.append("<!DOCTYPE html>")
    html_parts.append("<html lang='en'>")
    html_parts.append("<head>")
    html_parts.append("  <meta charset='UTF-8'>")
    html_parts.append("  <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html_parts.append("  <title>Schema Mapping Visualization</title>")
    html_parts.append("  <style>")
    html_parts.append(get_css_styles())
    html_parts.append("  </style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    
    # Header
    html_parts.append("  <div class='container'>")
    html_parts.append("    <header>")
    html_parts.append("      <h1>📊 Schema Mapping Visualization</h1>")
    html_parts.append(f"      <p class='timestamp'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    html_parts.append("    </header>")
    
    # Summary cards
    html_parts.append("    <div class='summary-cards'>")
    html_parts.append("      <div class='card'>")
    html_parts.append(f"        <div class='card-title'>Source Table</div>")
    html_parts.append(f"        <div class='card-value'>{html.escape(source_table.split('.')[-1])}</div>")
    html_parts.append(f"        <div class='card-subtitle'>{stats['total_source_columns']} columns</div>")
    html_parts.append("      </div>")
    html_parts.append("      <div class='card'>")
    html_parts.append(f"        <div class='card-title'>Target Table</div>")
    html_parts.append(f"        <div class='card-value'>{html.escape(target_table.split('.')[-1])}</div>")
    html_parts.append(f"        <div class='card-subtitle'>{stats['total_target_columns']} columns</div>")
    html_parts.append("      </div>")
    html_parts.append("      <div class='card'>")
    html_parts.append(f"        <div class='card-title'>Mapped Columns</div>")
    mapped_pct = (stats['mapped_columns'] / stats['total_target_columns'] * 100) if stats['total_target_columns'] > 0 else 0
    html_parts.append(f"        <div class='card-value'>{stats['mapped_columns']}/{stats['total_target_columns']}</div>")
    html_parts.append(f"        <div class='card-subtitle'>{mapped_pct:.1f}% coverage</div>")
    html_parts.append("      </div>")
    html_parts.append("      <div class='card'>")
    html_parts.append(f"        <div class='card-title'>Confidence</div>")
    html_parts.append(f"        <div class='card-value'>")
    html_parts.append(f"          <span class='badge high'>{stats['high_confidence']}</span>")
    html_parts.append(f"          <span class='badge medium'>{stats['medium_confidence']}</span>")
    html_parts.append(f"          <span class='badge low'>{stats['low_confidence']}</span>")
    html_parts.append(f"        </div>")
    html_parts.append(f"        <div class='card-subtitle'>High / Medium / Low</div>")
    html_parts.append("      </div>")
    html_parts.append("    </div>")
    
    # Mapping visualization
    html_parts.append("    <div class='mapping-section'>")
    html_parts.append("      <h2>Column Mappings</h2>")
    html_parts.append("      <div class='mappings-container'>")
    
    for i, mapping in enumerate(mappings):
        confidence_class = mapping['confidence']
        compatible = mapping['type_compatible']
        
        html_parts.append(f"        <div class='mapping-item {confidence_class}' onclick='toggleDetails({i})'>")
        html_parts.append("          <div class='mapping-header'>")
        html_parts.append("            <div class='source-col'>")
        html_parts.append(f"              <span class='col-name'>{html.escape(mapping['source_column'])}</span>")
        html_parts.append(f"              <span class='col-type'>{html.escape(mapping['source_type'])}</span>")
        html_parts.append("            </div>")
        html_parts.append("            <div class='arrow'>→</div>")
        html_parts.append("            <div class='target-col'>")
        html_parts.append(f"              <span class='col-name'>{html.escape(mapping['target_column'])}</span>")
        html_parts.append(f"              <span class='col-type'>{html.escape(mapping['target_type'])}</span>")
        html_parts.append("            </div>")
        html_parts.append(f"            <div class='confidence-badge {confidence_class}'>{mapping['confidence'].upper()}</div>")
        html_parts.append("          </div>")
        
        # Details (hidden by default)
        html_parts.append(f"          <div class='mapping-details' id='details-{i}'>")
        html_parts.append(f"            <p><strong>Similarity Score:</strong> {mapping['similarity_score']}%</p>")
        html_parts.append(f"            <p><strong>Transformation:</strong> {html.escape(mapping['transformation'])}</p>")
        html_parts.append(f"            <p><strong>SQL Expression:</strong> <code>{html.escape(mapping['sql_expression'])}</code></p>")
        html_parts.append(f"            <p><strong>Type Compatible:</strong> {'✅ Yes' if compatible else '❌ No - Review Required'}</p>")
        html_parts.append("          </div>")
        html_parts.append("        </div>")
    
    html_parts.append("      </div>")
    html_parts.append("    </div>")
    
    # Unmapped columns
    if mapping_analysis.get("unmapped_target_columns") or mapping_analysis.get("unmapped_source_columns"):
        html_parts.append("    <div class='unmapped-section'>")
        html_parts.append("      <h2>⚠️ Unmapped Columns</h2>")
        
        if mapping_analysis.get("unmapped_target_columns"):
            html_parts.append("      <div class='unmapped-group'>")
            html_parts.append("        <h3>Target Columns (Not Populated)</h3>")
            html_parts.append("        <ul>")
            for col in mapping_analysis["unmapped_target_columns"]:
                html_parts.append(f"          <li><code>{html.escape(col)}</code></li>")
            html_parts.append("        </ul>")
            html_parts.append("      </div>")
        
        if mapping_analysis.get("unmapped_source_columns"):
            html_parts.append("      <div class='unmapped-group'>")
            html_parts.append("        <h3>Source Columns (Not Used)</h3>")
            html_parts.append("        <ul>")
            for col_info in mapping_analysis["unmapped_source_columns"]:
                html_parts.append(f"          <li><code>{html.escape(col_info['column'])}</code> ({html.escape(col_info['type'])})</li>")
            html_parts.append("        </ul>")
            html_parts.append("      </div>")
        
        html_parts.append("    </div>")
    
    html_parts.append("  </div>")
    
    # JavaScript
    html_parts.append("  <script>")
    html_parts.append("    function toggleDetails(index) {")
    html_parts.append("      const details = document.getElementById('details-' + index);")
    html_parts.append("      if (details.style.display === 'none' || details.style.display === '') {")
    html_parts.append("        details.style.display = 'block';")
    html_parts.append("      } else {")
    html_parts.append("        details.style.display = 'none';")
    html_parts.append("      }")
    html_parts.append("    }")
    html_parts.append("  </script>")
    
    html_parts.append("</body>")
    html_parts.append("</html>")
    
    return "\n".join(html_parts)


def get_css_styles() -> str:
    """Return CSS styles for the HTML visualization."""
    return """
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
      line-height: 1.6;
    }
    
    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.2);
      padding: 40px;
    }
    
    header {
      text-align: center;
      margin-bottom: 40px;
      padding-bottom: 20px;
      border-bottom: 3px solid #667eea;
    }
    
    h1 {
      color: #2d3748;
      font-size: 2.5em;
      margin-bottom: 10px;
    }
    
    h2 {
      color: #4a5568;
      margin-bottom: 20px;
      font-size: 1.8em;
    }
    
    h3 {
      color: #718096;
      margin-bottom: 15px;
      font-size: 1.3em;
    }
    
    .timestamp {
      color: #718096;
      font-size: 0.95em;
    }
    
    .summary-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 20px;
      margin-bottom: 40px;
    }
    
    .card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 25px;
      border-radius: 10px;
      text-align: center;
      box-shadow: 0 4px 15px rgba(0,0,0,0.1);
      transition: transform 0.2s;
    }
    
    .card:hover {
      transform: translateY(-5px);
    }
    
    .card-title {
      font-size: 0.9em;
      opacity: 0.9;
      margin-bottom: 10px;
    }
    
    .card-value {
      font-size: 2em;
      font-weight: bold;
      margin-bottom: 5px;
    }
    
    .card-subtitle {
      font-size: 0.85em;
      opacity: 0.8;
    }
    
    .mapping-section {
      margin-bottom: 40px;
    }
    
    .mappings-container {
      display: flex;
      flex-direction: column;
      gap: 15px;
    }
    
    .mapping-item {
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      cursor: pointer;
      transition: all 0.3s;
      background: #f7fafc;
    }
    
    .mapping-item:hover {
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      transform: translateX(5px);
    }
    
    .mapping-item.high {
      border-left: 5px solid #48bb78;
    }
    
    .mapping-item.medium {
      border-left: 5px solid #ed8936;
    }
    
    .mapping-item.low {
      border-left: 5px solid #f56565;
    }
    
    .mapping-header {
      display: flex;
      align-items: center;
      gap: 20px;
      flex-wrap: wrap;
    }
    
    .source-col, .target-col {
      flex: 1;
      min-width: 200px;
    }
    
    .col-name {
      display: block;
      font-weight: bold;
      color: #2d3748;
      font-size: 1.1em;
      margin-bottom: 5px;
      font-family: 'Courier New', monospace;
    }
    
    .col-type {
      display: block;
      color: #718096;
      font-size: 0.9em;
      font-family: 'Courier New', monospace;
    }
    
    .arrow {
      font-size: 1.5em;
      color: #667eea;
      font-weight: bold;
    }
    
    .confidence-badge {
      padding: 8px 16px;
      border-radius: 20px;
      font-weight: bold;
      font-size: 0.85em;
      text-transform: uppercase;
    }
    
    .confidence-badge.high {
      background: #c6f6d5;
      color: #22543d;
    }
    
    .confidence-badge.medium {
      background: #feebc8;
      color: #7c2d12;
    }
    
    .confidence-badge.low {
      background: #fed7d7;
      color: #742a2a;
    }
    
    .mapping-details {
      display: none;
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid #e2e8f0;
      background: white;
      padding: 20px;
      border-radius: 6px;
    }
    
    .mapping-details p {
      margin-bottom: 10px;
      color: #4a5568;
    }
    
    .mapping-details code {
      background: #edf2f7;
      padding: 2px 8px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
      color: #2d3748;
      display: inline-block;
      margin-top: 5px;
    }
    
    .unmapped-section {
      background: #fff5f5;
      padding: 25px;
      border-radius: 8px;
      border: 2px solid #feb2b2;
    }
    
    .unmapped-group {
      margin-bottom: 20px;
    }
    
    .unmapped-group ul {
      list-style: none;
      padding-left: 20px;
    }
    
    .unmapped-group li {
      padding: 8px 0;
      color: #742a2a;
    }
    
    .unmapped-group code {
      background: white;
      padding: 4px 8px;
      border-radius: 4px;
      font-family: 'Courier New', monospace;
    }
    
    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 0.9em;
      font-weight: bold;
      margin: 0 4px;
    }
    
    .badge.high {
      background: #c6f6d5;
      color: #22543d;
    }
    
    .badge.medium {
      background: #feebc8;
      color: #7c2d12;
    }
    
    .badge.low {
      background: #fed7d7;
      color: #742a2a;
    }
    """

