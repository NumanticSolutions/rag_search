# Numantic Solutions | April 2026
# Module: S3 Data Load
# Code for loading documents to AWS S3

import json


def process_and_upload(df,
                       s3_client,
                       bucket: str,
                       text_col: str,
                       metadata_cols: list,
                       key_prefix='documents/'):
    """
    Prepare and upload documents to an S3 bucket under a specified prefix. Each document is processed by splitting
    its raw text into annotated blocks, generating metadata, and uploading both the formatted text and metadata
    to S3. The function assumes the presence of a stable S3 client and bucket name accessible within its scope.

    :param df: A pandas DataFrame containing the document data to process. Each row should include:
                - 'text': The raw text of the document.
                - 'source_url': The URL source of the document.
                - 'source_type': The type/category of the document source.
    :param key_prefix: A string prefix for S3 keys where documents and metadata files will be uploaded.
                       Defaults to 'documents/'.
    :return: None
    """

    # Prepare and load documents to S3 under a stable prefix.
    for idx in df.index:

        # Step 1: Get text and metadata fields
        raw_text = df.loc[idx, text_col]

        # Step 2: Create metadata
        metadata = {"metadataAttributes": {
                        }
                    }
        # Get document index
        metadata["metadataAttributes"]["document_index"]= "doc_{}".format(idx)

        # Get the other metadata elements
        for mc in metadata_cols:
            metadata["metadataAttributes"][mc] = df.loc[idx, mc]

        # Step 3: Create filenames/keys
        file_name = f"doc_{idx}.txt"
        metadata_name = f"{file_name}.metadata.json"
        text_key = f"{key_prefix}{file_name}"
        metadata_key = f"{key_prefix}{metadata_name}"

        # Step 4: Upload text and metadata files
        s3_client.put_object(
            Bucket=bucket,
            Key=text_key,
            Body=raw_text.encode('utf-8')
        )

        s3_client.put_object(
            Bucket=bucket,
            Key=metadata_key,
            Body=json.dumps(metadata).encode('utf-8')
        )

    print(f"Successfully uploaded {len(df)} documents and metadata files to prefix '{key_prefix}'.")

def delete_bucket_files(s3_client,
                        bucket,
                        s3_prefix):
    """
    Deletes all files in an S3 bucket within the specified prefix.

    This function uses the provided S3 client to paginate through all objects
    located in the specified bucket and prefix, and deletes each object.

    :param s3_client: S3 client used to interact with AWS S3.
    :param bucket: Name of the S3 bucket from which files will be deleted.
    :type bucket: str
    :param s3_prefix: Prefix inside the S3 bucket to target for file deletion.
    :type s3_prefix: str
    :return: None
    """

    ### Step 3. Delete existing documents first
    print(f"Deleting existing documents from {bucket}/{s3_prefix}...")
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket, Prefix=s3_prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
    print("✓ Existing documents deleted")

def read_text_file_from_s3(s3_client,
                           bucket: str,
                           file_key: str) -> str:
    """
    Reads the content of a single text file from an S3 bucket.

    :param s3_client: S3 client used to interact with AWS S3.
    :param bucket: Name of the S3 bucket.
    :param file_key: The full key (path) of the file to read.
    :return: The content of the file as a string.
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=file_key)
        # Read and decode the streaming body
        file_content = response['Body'].read().decode('utf-8')
        return file_content
    except s3_client.exceptions.NoSuchKey:
        print(f"Error: The file '{file_key}' was not found in bucket '{bucket}'.")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred while reading {file_key}: {e}")
        return ""