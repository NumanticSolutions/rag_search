# Numantic Solutions | April 2026
# Module: Bedrock Knowledge Base Management Utilities
# Code for creating a Bedrock Knowledge Base
#
# Prerequisites:
# 1. S3 bucket with .txt files containing document text (already uploaded)
# 2. AWS credentials configured
# 3. Python packages: boto3, opensearchpy
#
# Steps
#  1. Create a vector index (create_vector_index)
#  2. Delete an existing knowledge base (delete_existing_kb)
#  3. Create a new knowledge base (create_kb)
#  4. Ingest documents into knowledge base (ingest_docs_kb)
#  5. Check status of ingestion job (check_status_ingestion_job)

import time
import json

# AWS Python
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def create_vector_index(index_name,
                        aoss_client,
                        awsauth,
                        collection_name,
                        delete_existing=False
                        ):
    """
    Creates a vector index in an OpenSearch cluster with the specified configuration. The function ensures the
    existence of the index and can optionally delete and recreate it if it already exists. The index supports KNN
    vector search using the FAISS engine.

    :param index_name: The name of the vector index to be created.
    :type index_name: str
    :param aoss_client: The client object for interacting with the OpenSearch Serverless cluster.
    :type aoss_client: object
    :param awsauth: The AWS authentication object for secure communication with the OpenSearch cluster.
    :type awsauth: object
    :param collection_name: The name of the OpenSearch collection to gather the endpoint details.
    :type collection_name: str
    :param delete_existing: A flag to indicate whether to delete the existing index before creating a new one.
                           Defaults to False if not specified.
    :type delete_existing: bool
    :return: None
    """

    # Get the collection endpoint
    collection_endpoint = aoss_client.batch_get_collection(names=[collection_name])['collectionDetails'][0][
        'collectionEndpoint']
    host = collection_endpoint.replace('https://', '')

    os_client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

    # Create the index with proper mapping for Bedrock
    index_body = {
        "settings": {
            "index.knn": True
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "engine": "faiss",
                        "name": "hnsw"
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text"
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text"
                }
            }
        }
    }

    # Create index if it doesn't exist
    if not os_client.indices.exists(index=index_name):
        os_client.indices.create(index=index_name,
                                 ody=index_body)
        print(f"✓ Vector index created: {index_name}")
    else:
        print(f"✓ Vector index already exists: {index_name}")
        if delete_existing:
            print(f"✓ Deleting {index_name} and creating a new vector index: {index_name}")
            os_client.indices.delete(index=index_name)
            os_client.indices.create(index=index_name,
                                     body=index_body)
        else:
            print(f"✓ Use the delete_existing parameter to delete and creating a new vector index: {index_name}")

    # Wait for index to be ready
    time.sleep(5)


def delete_existing_kb(kb_name,
                       bedrock_agent):
    """
    Deletes an existing knowledge base if it matches the given name. The function checks for a
    knowledge base with the specified name, deletes it if it exists, and waits for the deletion
    process to complete. The process will timeout if the knowledge base is not deleted within
    180 seconds.

    :param kb_name: The name of the knowledge base to check and delete.
    :type kb_name: str
    :param bedrock_agent: The Bedrock agent instance used to manage the knowledge base.
    :type bedrock_agent: Any
    :return: None
    :rtype: None
    :raises TimeoutError: If the knowledge base deletion does not complete within the allowed time.
    """

    print(f"Checking for existing Knowledge Base named '{kb_name}'...")
    existing_kb_id = None
    paginator = bedrock_agent.get_paginator('list_knowledge_bases')
    for page in paginator.paginate():
        for kb in page['knowledgeBaseSummaries']:
            if kb['name'] == kb_name:
                existing_kb_id = kb['knowledgeBaseId']
                print(f"Found existing KB {existing_kb_id}. Deleting...")
                bedrock_agent.delete_knowledge_base(knowledgeBaseId=existing_kb_id)

    if existing_kb_id:
        start = time.time()
        while True:
            kb_ids = []
            paginator = bedrock_agent.get_paginator('list_knowledge_bases')
            for page in paginator.paginate():
                kb_ids.extend([k['knowledgeBaseId'] for k in page['knowledgeBaseSummaries']])

            if existing_kb_id not in kb_ids:
                print("✓ Existing KB deleted")
                break

            if time.time() - start > 180:
                raise TimeoutError(f"Timed out waiting for KB {existing_kb_id} deletion")

            print("Waiting for KB deletion to complete...")
            time.sleep(10)

def create_kb(kb_name,
              bedrock_agent,
              aoss_client,
              role_arn,
              collection_name,
              index_name,
              region_name,
              embedding_model):
    """
    Creates a knowledge base configured for vector search using Amazon Bedrock
    and OpenSearch Serverless. This function initializes the OpenSearch collection,
    configures the embedding model, and establishes the knowledge base with specified
    settings. Retries are implemented for handling eventual consistency issues.

    :param kb_name: Name of the Knowledge Base to be created.
    :type kb_name: str
    :param bedrock_agent: An instance of the Bedrock API client.
    :type bedrock_agent: object
    :param aoss_client: An instance of the OpenSearch Serverless API client.
    :type aoss_client: object
    :param role_arn: ARN of the role to be used for Bedrock operations.
    :type role_arn: str
    :param collection_name: Name of the OpenSearch collection to be created.
    :type collection_name: str
    :param index_name: Name of the index in the OpenSearch collection.
    :type index_name: str
    :param region_name: AWS region where the resources are created.
    :type region_name: str
    :param embedding_model: Name of the embedding model used in the Bedrock knowledge base.
    :type embedding_model: str
    :return: None
    :rtype: None
    :raises RuntimeError: If the knowledge base could not be created after retries.
    :raises Exception: For unexpected errors during OpenSearch collection creation.
    """

    try:
        coll = aoss_client.create_collection(name=collection_name,
                                             type='VECTORSEARCH')
        coll_arn = coll['createCollectionDetail']['arn']
        print("Waiting for collection to activate...")
    except Exception:
        coll_arn = aoss_client.batch_get_collection(names=[collection_name])['collectionDetails'][0]['arn']

    while aoss_client.batch_get_collection(names=[collection_name])['collectionDetails'][0]['status'] != 'ACTIVE':
        time.sleep(5)

    # --- Create Knowledge Base (retry for eventual consistency) ---
    last_err = None
    for attempt in range(1, 8):
        try:
            kb_response = bedrock_agent.create_knowledge_base(
                name=kb_name,
                roleArn=role_arn,
                knowledgeBaseConfiguration={
                    'type': 'VECTOR',
                    'vectorKnowledgeBaseConfiguration': {
                        'embeddingModelArn': (f'arn:aws:bedrock:{region_name}::'
                                              f'foundation-model/{embedding_model}')
                    }
                },
                storageConfiguration={
                    'type': 'OPENSEARCH_SERVERLESS',
                    'opensearchServerlessConfiguration': {
                        'collectionArn': coll_arn,
                        'vectorIndexName': index_name,
                        'fieldMapping': {
                            'vectorField': 'bedrock-knowledge-base-default-vector',
                            'textField': 'AMAZON_BEDROCK_TEXT_CHUNK',
                            'metadataField': 'AMAZON_BEDROCK_METADATA'
                        }
                    }
                }
            )
            kb_id = kb_response['knowledgeBase']['knowledgeBaseId']
            print(f"✓ Knowledge Base Created: {kb_id}")
            return kb_id

        except bedrock_agent.exceptions.ValidationException as e:
            last_err = e
            if 'security_exception' in str(e) and attempt < 7:
                wait_seconds = attempt * 15
                print(f"Attempt {attempt}/7 failed due to AOSS security propagation. Retrying in {wait_seconds}s...")
                time.sleep(wait_seconds)
                continue
            raise

    if 'kb_id' not in locals():
        raise RuntimeError(f"Failed to create knowledge base after retries: {last_err}")

    return kb_id

def ingest_docs_kb(kb_id,
                   bedrock_agent,
                   bucket_name,
                   s3_prefix,
                   ):
    """
    Ingests documents from an S3 bucket into a knowledge base by configuring a data source
    and initiating an ingestion job. The function checks for an existing data source with a
    stable name and reuses it if available; otherwise, it creates a new one.

    :param kb_id: The identifier of the knowledge base where the data will be ingested.
    :type kb_id: str
    :param bedrock_agent: The client or agent object for interacting with the Bedrock service.
    :type bedrock_agent: object
    :param bucket_name: The name of the S3 bucket containing the documents to ingest.
    :type bucket_name: str
    :param s3_prefix: The optional prefix within the S3 bucket to narrow down the data source.
    :type s3_prefix: str, optional
    :return: None
    """

    s3_config = {
        'bucketArn': f'arn:aws:s3:::{bucket_name}'
    }
    if s3_prefix:
        s3_config['inclusionPrefixes'] = [s3_prefix]

    # Use stable naming to allow reruns.
    existing_data_source = None
    paginator = bedrock_agent.get_paginator('list_data_sources')
    for page in paginator.paginate(knowledgeBaseId=kb_id):
        for ds in page['dataSourceSummaries']:
            if ds['name'] == 's3-docs-with-metadata':
                existing_data_source = ds['dataSourceId']
                break

    if existing_data_source:
        ds_id = existing_data_source
        print(f"Reusing existing data source: {ds_id}")
    else:
        ds_response = bedrock_agent.create_data_source(
            knowledgeBaseId=kb_id,
            name='s3-docs-with-metadata',
            dataSourceConfiguration={
                'type': 'S3',
                's3Configuration': s3_config
            }
        )
        ds_id = ds_response['dataSource']['dataSourceId']
        print(f"Created data source: {ds_id}")

    # --- Start Ingestion ---
    ingestion_response = bedrock_agent.start_ingestion_job(knowledgeBaseId=kb_id, dataSourceId=ds_id)
    print(f"✓ Ingestion started for {bucket_name}/{s3_prefix}")
    print("You can now filter by 'source_type' or 'doc_index' in your queries!")

    return ingestion_response

def check_status_ingestion_job(ingestion_job_id,
                               bedrock_agent,
                               kb_id,
                               ds_id
                               ):
    """
    Check the status of an ingestion job and print detailed summaries and statistics upon completion.

    This function continuously polls the status of the specified ingestion job
    until the job reaches a terminal state such as 'COMPLETE', 'FAILED', or 'STOPPED'.
    It also prints debugging details, including statistics on documents processed,
    failure reasons, and a JSON dump of the job details.

    :param ingestion_job_id: Identifier of the ingestion job to monitor
    :type ingestion_job_id: str
    :param bedrock_agent: Agent used to communicate with the Bedrock service and retrieve job details
    :type bedrock_agent: object
    :param kb_id: Identifier of the knowledge base to which the job belongs
    :type kb_id: str
    :param ds_id: Identifier of the data source that the ingestion job is processing
    :type ds_id: str
    :return: None
    """

    while True:
        job_response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=ds_id,
            ingestionJobId=ingestion_job_id
        )

        status = job_response['ingestionJob']['status']
        print(f"Current Status: {status}")

        if status in ['COMPLETE', 'FAILED', 'STOPPED']:
            break

        time.sleep(10)

    # --- Detailed Reporting ---
    job_data = job_response['ingestionJob']

    print("\n" + "=" * 30)
    print("INGESTION JOB SUMMARY")
    print("=" * 30)
    print(f"Status: {job_data['status']}")

    # Print Statistics if available
    if 'statistics' in job_data:
        stats = job_data['statistics']
        print(f"Documents Scanned: {stats.get('numberOfDocumentsScanned', 0)}")
        print(f"Documents Indexed: {stats.get('numberOfNewDocumentsIndexed', 0)}")
        print(f"Documents Failed:  {stats.get('numberOfDocumentsFailed', 0)}")

    # Print Failure Reasons
    if 'failureReasons' in job_data:
        print("\nFailure Reasons:")
        for reason in job_data['failureReasons']:
            print(f"  - {reason}")

    # Full Debugging Dump
    print("\nFull JSON Job Details (for debugging):")
    print(json.dumps(job_data, indent=2, default=str))
