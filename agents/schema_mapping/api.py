#!/usr/bin/env python3
"""
FastAPI wrapper for Schema Mapping Agent.
Exposes schema_mapper.py functionality as a REST API for Cloud Run deployment.
"""

import os
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Import existing schema_mapper functions (no modification needed)
from schema_mapper import generate_schema_mapping

# Load environment variables
load_dotenv('.env')

# Initialize FastAPI app
app = FastAPI(
    title="Schema Mapping API",
    description="Generate intelligent schema mappings between BigQuery datasets using LLM",
    version="1.0.0"
)


# --- Request/Response Models ---

class SchemaMappingRequest(BaseModel):
    """Request model for schema mapping generation."""

    source_dataset: str = Field(
        ...,
        description="Source BigQuery dataset name (e.g., 'worldbank_staging_dataset')",
        example="worldbank_staging_dataset"
    )

    target_dataset: str = Field(
        ...,
        description="Target BigQuery dataset name (e.g., 'worldbank_target_dataset')",
        example="worldbank_target_dataset"
    )

    mode: str = Field(
        default="REPORT",
        description="Mapping mode: REPORT (flag unmapped columns) or FIX (suggest defaults)",
        pattern="^(REPORT|FIX)$",
        example="FIX"
    )

    project_id: Optional[str] = Field(
        default=None,
        description="GCP Project ID (optional, defaults to environment variable)",
        example="my-gcp-project"
    )


class SchemaMappingResponse(BaseModel):
    """Response model for schema mapping."""

    status: str = Field(..., description="Status: success or error")
    message: Optional[str] = Field(None, description="Error message if status is error")
    mapping: Optional[dict] = Field(None, description="Generated schema mapping JSON")
    metadata: Optional[dict] = Field(None, description="Metadata about the mapping")


# --- API Endpoints ---

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Schema Mapping API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check for Cloud Run."""
    return {"status": "healthy"}


@app.post("/generate-mapping", response_model=SchemaMappingResponse)
async def generate_mapping(request: SchemaMappingRequest):
    """
    Generate schema mapping between source and target BigQuery datasets.

    **Parameters:**
    - **source_dataset**: Source BigQuery dataset name
    - **target_dataset**: Target BigQuery dataset name
    - **mode**: REPORT (flag unmapped columns) or FIX (suggest defaults)
    - **project_id**: Optional GCP project ID (uses env var if not provided)

    **Returns:**
    - JSON response with generated schema mapping

    **Example Request:**
    ```json
    {
        "source_dataset": "worldbank_staging_dataset",
        "target_dataset": "worldbank_target_dataset",
        "mode": "FIX"
    }
    ```
    """
    try:
        # Set project ID from request or environment
        if request.project_id:
            os.environ["GCP_PROJECT_ID"] = request.project_id

        # Validate mode
        if request.mode not in ["REPORT", "FIX"]:
            raise HTTPException(
                status_code=400,
                detail="mode must be either 'REPORT' or 'FIX'"
            )

        # Call existing schema_mapper function (no modification needed!)
        # Use /tmp directory which exists in Cloud Run containers
        result = generate_schema_mapping(
            source_dataset=request.source_dataset,
            target_dataset=request.target_dataset,
            output_file="/tmp/temp_mapping.json",  # Use /tmp directory in container
            mode=request.mode
        )

        # Check result
        if result.get("status") == "error":
            raise HTTPException(
                status_code=500,
                detail=result.get("message", "Unknown error occurred")
            )

        # Return success response
        mapping_data = result.get("mapping", {})

        return SchemaMappingResponse(
            status="success",
            mapping=mapping_data,
            metadata={
                "source_dataset": request.source_dataset,
                "target_dataset": request.target_dataset,
                "mode": request.mode,
                "num_mappings": len(mapping_data.get("mappings", [])),
                "confidence": mapping_data.get("metadata", {}).get("confidence", "unknown")
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/generate-mapping/simple")
async def generate_mapping_simple(
    source_dataset: str,
    target_dataset: str,
    mode: str = "REPORT"
):
    """
    Simplified endpoint using query parameters instead of JSON body.

    **Query Parameters:**
    - source_dataset: Source BigQuery dataset name
    - target_dataset: Target BigQuery dataset name
    - mode: REPORT or FIX (default: REPORT)

    **Example:**
    ```
    POST /generate-mapping/simple?source_dataset=staging&target_dataset=prod&mode=FIX
    ```
    """
    request = SchemaMappingRequest(
        source_dataset=source_dataset,
        target_dataset=target_dataset,
        mode=mode
    )

    return await generate_mapping(request)


@app.get("/mappings/example")
async def get_example_mapping():
    """
    Get an example schema mapping output.
    Useful for understanding the response format.
    """
    example = {
        "status": "success",
        "mapping": {
            "metadata": {
                "source_dataset": "project.staging_dataset",
                "target_dataset": "project.target_dataset",
                "generated_at": "2025-12-16T00:00:00Z",
                "confidence": "high",
                "mode": "FIX"
            },
            "mappings": [
                {
                    "source_table": "staging.countries",
                    "target_table": "target.dim_country",
                    "match_confidence": 0.95,
                    "column_mappings": [
                        {
                            "source_column": "country_code",
                            "target_column": "country_key",
                            "source_type": "STRING",
                            "target_type": "STRING",
                            "type_conversion_needed": False,
                            "transformation": None,
                            "notes": "Direct mapping"
                        },
                        {
                            "source_column": "GENERATED",
                            "target_column": "loaded_at",
                            "source_type": "EXPRESSION",
                            "target_type": "TIMESTAMP",
                            "type_conversion_needed": False,
                            "transformation": "DEFAULT: CURRENT_TIMESTAMP()",
                            "notes": "Auto-generated timestamp"
                        }
                    ],
                    "validation_rules": [
                        {
                            "column": "country_key",
                            "type": "NOT_NULL",
                            "reason": "Primary key"
                        }
                    ],
                    "primary_key": ["country_key"]
                }
            ]
        },
        "metadata": {
            "source_dataset": "staging_dataset",
            "target_dataset": "target_dataset",
            "mode": "FIX",
            "num_mappings": 1,
            "confidence": "high"
        }
    }

    return JSONResponse(content=example)


# --- Error Handlers ---

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "status": "error",
            "message": "Endpoint not found",
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc)
        }
    )


# --- For local development ---
if __name__ == "__main__":
    import uvicorn

    # Run with: python api.py
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=True
    )
