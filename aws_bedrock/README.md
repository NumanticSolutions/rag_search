# RAG Search Testing with AWS Bedrock Knowledge Base

This directory contains code for constructing a AWS Bedrock Knowledge Base and for testing it product using a standardized RAG evaluation dataset.

## About AWS Bedrock Knowledge Base

Amazon Bedrock Knowledge Bases is a fully managed service that enables you to build Retrieval Augmented Generation (RAG) applications. It provides serverless vector storage using OpenSearch Serverless, automatic document chunking and embedding, and seamless integration with foundation models for question-answering. Knowledge Bases handle the infrastructure complexity of RAG systems, allowing you to focus on building AI applications that can query and reason over your private data.

## Date
May 6, 2026

## Dataset

This project uses the **Single-Topic RAG Evaluation Dataset** originally created by Samuel Matsuo Harris available at Kaggle ([link](https://www.kaggle.com/datasets/samuelmatsuoharris/single-topic-rag-evaluation-dataset)).

This dataset was designed to evaluate the performance of RAG AI querying text documents about a single topic with word counts ranging from a few thousand to a few tens of thousands, such as articles, blogs, and documentation. The sources were intentionally chosen to have been produced within the last few years (from the time of writing in July 2024) and to be relatively niche, to reduce the chance of evaluated LLMs including this information in their training datasets.

**Dataset Composition:**
- **120 question-answer pairs** total
- **40 questions** that do not have an answer within the document
- **40 question-answer pairs** that require a single passage from the document
- **40 question-answer pairs** that require multiple passages from the document

## Files and Notebooks

### Notebooks

#### `S10_load_data_s3.ipynb`
Loads the RAG evaluation dataset to Amazon S3 in a Bedrock-compatible format. This notebook:
- Reads local CSV files (`documents.csv`, `no_answer_questions.csv`, `single_passage_answer_questions.csv`) from `../data/rag_eval_dataset/`
- Enriches documents with `source_type` and `title` attributes from `doc_metadata.json`
- Clears existing files from the S3 bucket prefix before uploading
- Uploads 20 documents and JSON metadata sidecar files to S3

#### `S20_build_bedrock_knowledgebase.ipynb`
Creates and configures the AWS Bedrock Knowledge Base infrastructure. This notebook:
- Creates OpenSearch Serverless encryption and network security policies
- Creates or retrieves an IAM execution role with S3, OpenSearch, and Bedrock permissions
- Creates a FAISS-backed KNN vector index (1024 dimensions) in OpenSearch Serverless
- Creates the Bedrock Knowledge Base using Amazon Titan Embed Text v2 for embeddings
- Configures an S3 data source and ingests 20 documents, monitoring job status until completion

#### `S30_search_bedrock_knowledgebase.ipynb`
Tests and evaluates RAG retrieval performance using the Bedrock Knowledge Base. This notebook:
- Runs 40 single-passage questions against the Knowledge Base without filters, measuring source retrieval accuracy
- Re-runs failed queries with `document_index` metadata filters to isolate specific documents
- Tests direct AI generation by bypassing the knowledge base and sending source text directly to Claude via the Bedrock Converse API
- Reports per-query retrieval success, citation accuracy, and compares filtered vs. unfiltered performance

### Python Modules

#### `s3_data_load.py`
Utility module for uploading and managing documents in S3 for Bedrock ingestion. Provides:
- `process_and_upload()` — uploads document text files and JSON metadata sidecars to S3
- `delete_bucket_files()` — deletes all objects under an S3 prefix for clean re-uploads
- `read_text_file_from_s3()` — retrieves and decodes a single text file from S3

#### `bedrock_kb_security_build.py`
Utility module for provisioning the AWS security infrastructure required by Bedrock Knowledge Bases. Provides:
- `ensure_aoss_policy()` — creates OpenSearch Serverless encryption or network policies
- `ensure_execution_role()` — creates or retrieves an IAM role with S3, OpenSearch, and Bedrock permissions
- `ensure_data_access_policy()` — creates or updates the OpenSearch data access policy for the execution role and current user
- `ensure_policy_propagation()` — polls until IAM/AOSS policy changes are visible (180-second timeout) before proceeding with knowledge base creation

#### `bedrock_kb_build.py`
Utility module for creating and managing Bedrock Knowledge Bases. Provides:
- `create_vector_index()` — creates a FAISS KNN vector index in OpenSearch Serverless
- `delete_existing_kb()` — deletes a knowledge base by name and polls until removal completes
- `create_kb()` — creates the Bedrock Knowledge Base with retry logic for IAM/AOSS propagation delays
- `ingest_docs_kb()` — creates an S3 data source and starts a document ingestion job
- `check_status_ingestion_job()` — polls ingestion job status and reports document counts and failures

#### `bedrock_kb_query.py`
Class-based module for querying a Bedrock Knowledge Base and evaluating retrieval results. The `BedrockKBRetriever` class provides:
- `retrieve_query_results()` — vector search with optional metadata filtering, returns top-5 results with relevance scores read from S3 metadata
- `retrieve_and_generate_results()` — combined retrieval and LLM generation with metadata filter support and citation extraction
- `query_ai_direct()` — bypasses the knowledge base and sends a question plus source text directly to Claude via the Bedrock Converse API
- `get_bedrock_foundational_models()` — lists available Bedrock foundation models and their capabilities

## AWS Authentication

Here's a step-by-step guide to how we authenticate with AWS for Bedrock access:

1. **Install AWS CLI**: Ensure you have the AWS Command Line Interface (CLI) installed on your machine.
2. **Configure AWS CLI**: Run `aws configure sso` from the terminal and provide the following SSO information:
   3. Session name
   4. Start URL (from AWS) 
   5. Region
   6. Registration scopes (we have previously established 3 roles that can be selected at this stage)
   7. Default region and CLI option
   8. Profile name (e.g. ns-admin which can be used within the Python code to set user scope)

---

*Developed by [Numantic Solutions](https://numanticsolutions.com/#)*
