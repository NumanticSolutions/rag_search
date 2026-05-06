# Numantic Solutions | April 2026
# Module: GCS Data Load
# Code for loading documents to Google Cloud Storage
#
# Initialize GCS client globally or within your orchestration script
# storage_client = storage.Client()
# bucket = storage_client.bucket('your-bucket-name')

# Python
import os, sys
import json

import pandas as pd

# GCP
from google.cloud import storage


def delete_existing_blobs(bucket_name: str,
                          key_prefix: str):
    """
    Deletes all objects under a specific GCS prefix to ensure a clean upload.

    Args:
        bucket_name (str): The name of the GCS bucket.
        key_prefix (str): The directory path (prefix) to clear.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    # List all blobs with the given prefix
    blobs = bucket.list_blobs(prefix=key_prefix)

    deleted_count = 0
    for blob in blobs:
        blob.delete()
        deleted_count += 1

    if deleted_count > 0:
        print(f"Cleaned up {deleted_count} existing objects from {key_prefix}")
    else:
        print(f"No existing objects found in {key_prefix}. Proceeding...")


def process_and_upload_gcp(df,
                           bucket_name: str,
                           text_col: str,
                           meta_cols: list,
                           key_prefix: str = 'documents/'):
    """
    Processes a DataFrame into individual text files and a central metadata.jsonl file
    for Vertex AI Search.

    Args:
        df (pd.DataFrame): Source data containing text and metadata.
        bucket_name (str): The target GCS bucket.
        text_col (str): The column name containing the document body text.
        meta_cols (list): List of column names to be included as filterable metadata.
        key_prefix (str): The folder path in the bucket. Defaults to 'documents/'.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    metadata_records = []

    # Ensure key_prefix ends with a slash
    if not key_prefix.endswith('/'):
        key_prefix += '/'

    for idx, row in df.iterrows():
        # 1. Prepare Content
        title = row.get('title', '')
        raw_text = row.get(text_col, '')
        clean_content = f"TITLE: {title}\n\n{raw_text}"

        # 2. Build Metadata Dictionary (Nested Object, NOT stringified)
        # Vertex AI maps these keys to schema fields for filtering
        meta_content = {"doc_index": f"doc_{idx}"}
        for col in meta_cols:
            val = row.get(col)
            # Handle NaNs/Nulls to prevent JSON serialization errors
            meta_content[col] = val if pd.notna(val) else ""

        # 3. Define Paths
        file_name = f"doc_{idx}.txt"
        blob_path = f"{key_prefix}{file_name}"
        gcs_uri = f"gs://{bucket_name}/{blob_path}"

        # 4. Upload Text File
        blob = bucket.blob(blob_path)
        blob.upload_from_string(
            clean_content,
            content_type='text/plain'
        )

        # 5. Create NDJSON Record
        metadata_entry = {
            "id": f"doc_{idx}",
            "jsonData": json.dumps(meta_content),  # Stringify this specifically
            "content": {
                "mimeType": "text/plain",
                "uri": gcs_uri
            }
        }
        metadata_records.append(metadata_entry)

    # 6. Finalize and Upload Metadata Manifest
    metadata_jsonl_content = "\n".join([json.dumps(record) for record in metadata_records])

    metadata_blob = bucket.blob(f"{key_prefix}metadata.jsonl")
    metadata_blob.upload_from_string(
        metadata_jsonl_content,
        content_type='application/x-ndjson'
    )

    print(f"Success: Uploaded {len(metadata_records)} documents and manifest to {key_prefix}")


