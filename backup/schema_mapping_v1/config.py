"""Configuration for schema mapping agent."""

import os
from pathlib import Path
from typing import Optional


class SchemaMapperConfig:
    """Configuration settings for the schema mapper."""
    
    def __init__(self):
        # BigQuery settings
        self.default_project = os.getenv('GCP_PROJECT', 'ccibt-hack25ww7-750')
        
        # Mapping preferences
        self.similarity_threshold = int(os.getenv('SIMILARITY_THRESHOLD', '80'))
        self.use_safe_cast = os.getenv('USE_SAFE_CAST', 'true').lower() == 'true'
        
        # Output settings
        self.output_dir = Path(os.getenv('OUTPUT_DIR', 'schema_mapping/output'))
        self.generate_html = os.getenv('GENERATE_HTML', 'true').lower() == 'true'
        self.generate_markdown = os.getenv('GENERATE_MARKDOWN', 'true').lower() == 'true'
        
        # Vertex AI settings
        self.vertex_ai_location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
        self.vertex_ai_staging_bucket = os.getenv('VERTEX_AI_STAGING_BUCKET', None)
        
    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def to_dict(self):
        """Convert config to dictionary."""
        return {
            'default_project': self.default_project,
            'similarity_threshold': self.similarity_threshold,
            'use_safe_cast': self.use_safe_cast,
            'output_dir': str(self.output_dir),
            'generate_html': self.generate_html,
            'generate_markdown': self.generate_markdown,
            'vertex_ai_location': self.vertex_ai_location,
            'vertex_ai_staging_bucket': self.vertex_ai_staging_bucket
        }


# Global config instance
config = SchemaMapperConfig()

