# RAG Search Testing with GCP Vertex AI Search

This directory contains code for constructing a GCP Vertex AI Search application and for testing it using a standardized RAG evaluation dataset.

## About GCP Vertex AI Search

Google Cloud Vertex AI Search is a fully managed service that enables you to build enterprise-grade search and Retrieval Augmented Generation (RAG) applications. It provides semantic and keyword search backed by Google's search infrastructure, automatic document ingestion and indexing, and seamless integration with foundation models for question-answering. Vertex AI Search handles the infrastructure complexity of RAG systems, allowing you to focus on building AI applications that can query and reason over your private data.

## Date
May 5, 2026

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

#### `S10_load_data_bq.ipynb`
Loads the RAG evaluation dataset into Google BigQuery for use in Vertex AI Search workflows. This notebook:
- Reads local CSV files (`documents.csv`, `no_answer_questions.csv`, `single_passage_answer_questions.csv`) from `../data/rag_eval_dataset/`
- Enriches documents with `source_type` and `title` attributes from `doc_metadata.json`
- Uploads a documents table (`rag_tests_2`) and a passages table (`rag_tests_3`) to the `ns_bq` BigQuery dataset
- The passages table splits each document into semantic chunks separated by double newlines

#### `S12_load_data_gcs.ipynb`
Processes documents and uploads them to Google Cloud Storage in a format compatible with Vertex AI Search data stores. This notebook:
- Reads and enriches the same local RAG evaluation dataset as S10
- Clears existing files from the GCS bucket prefix before uploading
- Uploads 20 individual document text files and a consolidated `metadata.jsonl` manifest to GCS bucket `ns_datasets` under the `rag-tests/documents/` prefix
- Annotates passage splits within each document with numeric markers for granular retrieval tracking

#### `S20_build_vertexai_search_app.ipynb`
Creates and configures the Vertex AI Search infrastructure. This notebook:
- Creates a Vertex AI data store (`rag-tests-datastore-v26`) with a custom schema defining `title`, `source_url`, `source_type`, and `doc_index` fields
- Imports 20 documents from the GCS `metadata.jsonl` manifest using incremental reconciliation mode
- Creates a Vertex AI Search engine (`rag-tests-searchapp-v26`) linked to the data store, configured with Enterprise tier and LLM add-on for RAG
- Verifies document count after ingestion

#### `S30_query_vertexai_searchapp.ipynb`
Tests and evaluates RAG retrieval performance using the Vertex AI Search app. This notebook:
- Runs 40 single-passage questions against the search app without filters, measuring source retrieval accuracy
- Re-runs failed queries using a `doc_index` filter to restrict search to the correct source document
- Tests direct AI generation by bypassing the search app and sending source text directly to `gemini-2.5-flash` via the Vertex AI generative model client
- Reports per-query retrieval success and compares filtered vs. unfiltered performance (9 failures identified in baseline)

### Python Modules

#### `gcs_data_load.py`
Utility module for uploading and managing documents in GCS for Vertex AI Search ingestion. Provides:
- `delete_existing_blobs()` — deletes all objects under a GCS prefix for clean re-uploads
- `process_and_upload_gcp()` — uploads individual document text files and a consolidated NDJSON `metadata.jsonl` manifest to GCS, with each entry containing a document ID, JSON-stringified metadata, and GCS content URI

#### `vai_search_app_build.py`
Utility module for creating and managing Vertex AI Search data stores and search engines. Provides:
- `create_vais_data_store()` — creates a new Vertex AI data store with GENERIC vertical and CONTENT_REQUIRED configuration
- `update_vais_schema()` — updates the data store schema supporting retrievable, indexable, searchable, and dynamically facetable field attributes
- `import_documents_to_data_store()` — imports documents from a GCS JSONL manifest or BigQuery table using incremental reconciliation
- `create_vai_search_engine()` — creates a search engine connected to one or more data stores with Enterprise tier and LLM add-on
- `get_document_count()` — returns the total number of documents in a data store
- `get_vais_schema()` — retrieves and pretty-prints the current data store schema

#### `vai_search_app_query.py`
Class-based module for querying a Vertex AI Search engine and evaluating retrieval results. The `QueryVaiSearch` class provides:
- `search_and_generate_answer()` — end-to-end workflow combining search and RAG answer generation, with optional SQL-like metadata filter
- `search_vertex_ai()` — executes a search query with extractive content specs, query expansion, and spell correction
- `get_vertex_answer()` — calls the answer endpoint to generate an LLM summary with citations and related questions
- `extract_response_data()` — parses search and answer responses to extract generated text and cited document IDs
- `query_ai_client()` — bypasses Vertex AI Search and sends a question plus source text directly to `gemini-2.5-flash` for comparison testing

## GCP Authentication

Here's a step-by-step guide for one way to authenticate with GCP for Vertex AI access:

1. **Install Google Cloud SDK**: Ensure you have the `gcloud` CLI installed on your machine.
2. **Authenticate with Application Default Credentials**: Run `gcloud auth application-default login` from the terminal to set up credentials used automatically by GCP client libraries.
3. **Set your project**: Run `gcloud config set project <your-project-id>` or set the `GOOGLE_CLOUD_PROJECT_ID` environment variable in your shell or `.env` file.
4. **Enable required APIs**: Ensure the Discovery Engine, BigQuery, and Cloud Storage APIs are enabled in your GCP project.

---

*Developed by [Numantic Solutions](https://numanticsolutions.com/#)*
