# Numantic Solutions | April 2026
# Module: Vertex AI Search Management Utilities
# Code for creating a Vertex AI Search App
#
# Steps
#  1. Create a Vertex AI Data Store (create_vais_data_store)
#  2. Update the Data Store's schema (update_vais_schema)
#  3. Import documents from BigQuery or Google Cloud Storage (import_documents_to_data_store)
#  4. Create Vertex AI Search App from Data Store (create_vai_search_engine)
#  5. Run utilities to manage app
#      5a. Get Data Store document count (get_document_count)
#      5b. Check Data Store schema (get_vais_schema)

# Python
import os, sys
import json
from typing import List, Dict, Optional, Union

# GCP
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine


def create_vais_data_store(
        project_id: str,
        location: str,
        data_store_id: str,
        display_name: str,
        industry_vertical: str = "GENERIC"
) -> str:
    """
    Creates a Vertex AI Data Store.

    Args:
        project_id: GCP Project ID.
        location: Data store location (e.g., 'global' or 'us').
        data_store_id: Unique identifier for the data store.
        display_name: Human-readable name for the console.
        industry_vertical: Vertical type, defaults to GENERIC.
    """
    client = discoveryengine.DataStoreServiceClient()
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"

    data_store = discoveryengine.DataStore(
        display_name=display_name,
        industry_vertical=getattr(discoveryengine.IndustryVertical, industry_vertical),
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
    )

    operation = client.create_data_store(
        parent=parent,
        data_store=data_store,
        data_store_id=data_store_id
    )

    print(f"Creating Data Store: {data_store_id}...")
    response = operation.result()
    return response.name


def update_vais_schema(
        project_id: str,
        location: str,
        data_store_id: str,
        schema_dict: Dict
):
    """
        Updates the schema for a Data Store using a dictionary parameter.

        Args:
            project_id: GCP Project ID.
            location: Data store location.
            data_store_id: Target data store ID.
            schema_dict: A dictionary representing the JSON schema.

        ---
        SCHEMA PARAMETER GUIDANCE:

        1. Managed by Discovery Engine (Key Property Mappings):
           - These fields should use "keyPropertyMapping" to tell Vertex their role.
           - 'title': Maps to the document title.
           - 'content': Maps to the main body text (keyPropertyMapping: "description").
           - 'uri': Maps to the source link (keyPropertyMapping: "uri").

        2. Explicitly Defined Attributes:
           - "retrievable": (bool) Set True if you want this field returned in the search snippet.
           - "indexable": (bool) Set True to allow filtering (e.g., filter="category: 'finance'").
           - "searchable": (bool) Set True if you want the user's natural language query
             to match against the text in this specific field.
           - "dynamicFacetable": (bool) Set True if you want Vertex to automatically generate
             navigation counts (facets) for this field (e.g., "Source Type: PDF (10), HTML (5)").

        ---
        EXAMPLE SCHEMA DICTIONARY:
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "keyPropertyMapping": "title",
                    "retrievable": True
                },
                "source_type": {
                    "type": "string",
                    "retrievable": True,
                    "indexable": True,
                    "dynamicFacetable": True
                },
                "internal_id": {
                    "type": "string",
                    "indexable": True,
                    "retrievable": False  # Use False if you only use it for backend logic
                }
            }
        }
        """
    client = discoveryengine.SchemaServiceClient()
    schema_name = client.schema_path(project_id, location, data_store_id, "default_schema")

    schema = discoveryengine.Schema(
        name=schema_name,
        json_schema=json.dumps(schema_dict)
    )

    request = discoveryengine.UpdateSchemaRequest(schema=schema)

    print(f"Updating schema for {data_store_id}...")
    try:
        operation = client.update_schema(request=request)
        response = operation.result()
        print(f"Schema updated successfully: {response.name}")
    except Exception as e:
        print(f"Error updating schema: {e}")


def import_documents_to_data_store(
        project_id: str,
        location: str,
        data_store_id: str,
        source_uri: Union[str, List[str]],
        source_type: str = "GCS",
        bq_dataset: Optional[str] = None,
        bq_table: Optional[str] = None
):
    """
    Imports documents from either Google Cloud Storage or BigQuery.

    Args:
        project_id: GCP Project ID.
        location: Data store location.
        data_store_id: Target data store ID.
        source_uri: For GCS: GCS path (gs://...). For BQ: Project ID (or None).
        source_type: 'GCS' or 'BIGQUERY'.
        bq_dataset: BigQuery Dataset ID (Required if source_type is BIGQUERY).
        bq_table: BigQuery Table ID (Required if source_type is BIGQUERY).
    """
    client = discoveryengine.DocumentServiceClient()
    parent = client.branch_path(project_id, location, data_store_id, "default_branch")

    if source_type.upper() == "GCS":
        # Supports single string or list of GCS URIs
        gcs_uris = [source_uri] if isinstance(source_uri, str) else source_uri
        import_config = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=gcs_uris,
                data_schema="document"  # Changed from "custom"
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )



    elif source_type.upper() == "BIGQUERY":
        if not bq_dataset or not bq_table:
            raise ValueError("bq_dataset and bq_table must be provided for BigQuery imports.")

        import_config = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            bigquery_source=discoveryengine.BigQuerySource(
                project_id=project_id,
                dataset_id=bq_dataset,
                table_id=bq_table,
                data_schema="custom"  # Allows mapping fields to schema
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
        )
    else:
        raise ValueError("source_type must be either 'GCS' or 'BIGQUERY'")

    print(f"Importing data from {source_type} source...")
    operation = client.import_documents(request=import_config)
    return operation.operation.name


def create_vai_search_engine(
        project_id: str,
        location: str,
        engine_id: str,
        display_name: str,
        data_store_ids: List[str]
):
    client = discoveryengine.EngineServiceClient()
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"

    engine = discoveryengine.Engine(
        display_name=display_name,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        data_store_ids=data_store_ids,
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_ENTERPRISE,
            # FIXED: SearchAddOn (no underscore)
            search_add_ons=[discoveryengine.SearchAddOn.SEARCH_ADD_ON_LLM]
        )
    )

    operation = client.create_engine(
        parent=parent,
        engine=engine,
        engine_id=engine_id
    )

    print(f"Creating search engine: {display_name}...")
    response = operation.result()
    return response.name


def get_document_count(
        project_id: str,
        location: str,
        data_store_id: str
) -> int:
    """Retrieves the total number of documents in the default branch."""
    client_options = ClientOptions(
        api_endpoint=f"{location}-discoveryengine.googleapis.com" if location != "global" else None
    )
    client = discoveryengine.DocumentServiceClient(client_options=client_options)
    parent = client.branch_path(project_id, location, data_store_id, "default_branch")

    request = discoveryengine.ListDocumentsRequest(parent=parent, page_size=1000)
    results = client.list_documents(request=request)

    total_count = sum(1 for _ in results)
    print(f"Data Store '{data_store_id}' contains {total_count} documents.")
    return total_count


def get_vais_schema(
        project_id: str,
        location: str,
        data_store_id: str
) -> Optional[Dict]:
    """Fetches and prints the current JSON schema for a Data Store."""
    client = discoveryengine.SchemaServiceClient()
    schema_name = client.schema_path(project_id, location, data_store_id, "default_schema")

    try:
        response = client.get_schema(name=schema_name)
        current_schema = json.loads(response.json_schema)
        print(f"Schema for {data_store_id}:", json.dumps(current_schema, indent=2))
        return current_schema
    except Exception as e:
        print(f"Error: {e}")
        return None