<div style="text-align: center;">
<img src="./data/images/ns_rag_search_banner.png" alt="Numantic Solutions" width="900" height="300">
</div> 

# RAG Search Testing

This repository evaluates turnkey RAG (Retrieval Augmented Generation) solutions from AWS and GCP, provides working code examples for practitioners, and explores techniques for improving retrieval quality and user experience.

## Project Objectives

### 1. Evaluate Turnkey RAG Solutions
Compare AWS Bedrock Knowledge Base and GCP Vertex AI Search across two dimensions:
- **Ease of deployment** — time and complexity required to go from raw documents to a working RAG endpoint, including infrastructure setup, permissions, and data ingestion
- **Quality of responses** — accuracy of document retrieval and relevance of generated answers against a standardized evaluation dataset

### 2. Provide Jumpstart Code Examples
All code is written to be readable and reusable. Each cloud implementation is self-contained in its own directory, with modular Python utilities that can be adapted to other projects. Notebooks walk through every step of the pipeline from data loading to querying, making it straightforward to adapt the code for a new dataset or cloud environment.

### 3. Explore Techniques for Improving RAG Responses
Beyond baseline RAG, the notebooks investigate techniques that can improve retrieval and answer quality.

### 4. Provide simple RAG examples helping builders develop intuition into how these tools work and how they might be improved
Because RAG tools often operate a large amounts of unstructured data and measuring performance is challenging, it's helpful to have a small number of digestable examples to gain intuition on how these platform perform.

---
## Resources

### Production Deployments
| **Presentation Covering the Work**                                                                                                                                                                                                      | **Test Questions and RAG responses**                                                                                                                                                                                                                                                                       |
|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <div style="text-align: center;"><a href="./data/images/RAG_Platform_Tests_V1.pdf"><img src="./data/images/presentation_page_1.png" alt="CCC Policy Assistant" width="450" height="300"><p>Click to view the presentation</p></a></div> | <div style="text-align: center;"><a href="https://docs.google.com/spreadsheets/d/1eXTQMtT6YsKCSbpxKjGMv24B3E7aR-WDd6dB-zlkVkc/edit?usp=sharing"><img src="./data/images/RAG_test_questions_responses.png" alt="CCC Policy Assistant" width="450" height="300"><p>Click to see test questions</p></a></div> |


## Setup

### Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

### Environment variables

All notebooks read configuration from a `.env` file in the project root. This file is not committed to git. Create it by copying the template below and filling in your values:

```bash
# AWS Configuration
AWS_ACCOUNT_ID=<your-aws-account-id>
AWS_REGION=<your-aws-region>
AWS_PROFILE=<your-aws-cli-profile-name>

# Bedrock / OpenSearch Configuration
COLLECTION_NAME=<your-opensearch-collection-name>
KB_NAME=<your-knowledge-base-name>
INDEX_NAME=bedrock-knowledge-base-default-index
ROLE_NAME=AmazonBedrockExecutionRoleForKnowledgeBase
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# Knowledge Base ID (generated on creation — update after rebuilding)
KB_ID=<your-knowledge-base-id>

# S3 Configuration
S3_BUCKET=<your-s3-bucket-name>
S3_PREFIX=<your-s3-prefix-with-trailing-slash>/

# Data file paths
INPUT_DATA_PATH=../data/rag_eval_dataset
DOCS_FILENAME=documents.csv
MULTI_PAS_QS=multi_passage_answer_questions.csv
NO_ANSWER_QS=no_answer_questions.csv
SINGLE_PAS_ANSWER_QS=single_passage_answer_questions.csv
```

`AWS_PROFILE` refers to a named profile in your `~/.aws/credentials` file. If you have not configured named profiles, use `default`.

---
## Repository Structure

```
rag_search/
├── data/
│   └── rag_eval_dataset/          # Shared evaluation dataset (CSV + metadata JSON)
├── aws_bedrock/                   # AWS Bedrock Knowledge Base implementation
│   ├── README.md
│   ├── S10_load_data_s3.ipynb
│   ├── S20_build_bedrock_knowledgebase.ipynb
│   ├── S30_search_bedrock_knowledgebase.ipynb
│   ├── s3_data_load.py
│   ├── bedrock_kb_security_build.py
│   ├── bedrock_kb_build.py
│   └── bedrock_kb_query.py
└── gcp_vertexai/                  # GCP Vertex AI Search implementation
    ├── README.md
    ├── S10_load_data_bq.ipynb
    ├── S12_load_data_gcs.ipynb
    ├── S20_build_vertexai_search_app.ipynb
    ├── S30_query_vertexai_searchapp.ipynb
    ├── gcs_data_load.py
    ├── vai_search_app_build.py
    └── vai_search_app_query.py
```

Each cloud directory contains its own `README.md` with detailed descriptions of every notebook and Python module, authentication setup, and configuration parameters.

---
## Evaluation Dataset

Both implementations are tested against the **Single-Topic RAG Evaluation Dataset** originally created by Samuel Matsuo Harris, available on [Kaggle](https://www.kaggle.com/datasets/samuelmatsuoharris/single-topic-rag-evaluation-dataset).

The dataset contains 120 question-answer pairs across 20 documents, designed to test three retrieval scenarios:
- Questions with **no answer** in the document corpus (40)
- Questions requiring a **single passage** from one document (40)
- Questions requiring **multiple passages** from one document (40)

---
## Cloud Implementations

### AWS Bedrock Knowledge Base

Located in `aws_bedrock/`. Uses Amazon Bedrock Knowledge Bases backed by OpenSearch Serverless with Amazon Titan Embed Text v2 embeddings. Documents are stored in S3 with JSON metadata sidecars. See [`aws_bedrock/README.md`](aws_bedrock/README.md) for details.

The notebooks are designed to be run in sequence (S10 → S20 → S30). However, see the note on S20 below if you already have a provisioned Knowledge Base.

#### `S10_load_data_s3.ipynb`

Loads the RAG evaluation dataset to Amazon S3 in a Bedrock-compatible format. This notebook:
- Reads the local CSV files containing documents and questions
- Adds metadata attributes (source type, document index) to enable filtering
- Annotates documents with passage numbers for better retrieval tracking
- Uploads documents and metadata sidecars to S3

#### `S20_build_bedrock_knowledgebase.ipynb`

Creates and configures the AWS Bedrock Knowledge Base infrastructure. This notebook:
- Sets up OpenSearch Serverless collection with security policies
- Creates IAM roles and permissions for Bedrock access
- Creates the Knowledge Base with vector embeddings using Amazon Titan
- Configures the S3 data source
- Initiates and monitors the document ingestion process

**If you do not already have a Knowledge Base:** You will have to uncommment the code blocks in S20 that provision both a new knowledge base and an execution role used to run the document ingestion process. Aftewards, set `KB_ID` in your `.env` file to the resulting Knowledge Base ID (or to the ID of your pre-existing Knowledge Base), comment out that same code (so it does not run again later). The KB ID is visible in the AWS console under Bedrock > Knowledge Bases, or was printed at the end of a prior S20 run as `✓ Knowledge Base Created: <KB_ID>`.

#### `S30_search_bedrock_knowledgebase.ipynb`

Queries the Knowledge Base and evaluates retrieval performance. This notebook:
- Loads the evaluation dataset — ground-truth questions and answers used to benchmark the Knowledge Base
    - `documents.csv` — the 20 source documents indexed in the Knowledge Base
    - `single_passage_answer_questions.csv` — questions answerable from a single passage
    - `multi_passage_answer_questions.csv` — questions requiring multiple passages
    - `no_answer_questions.csv` — questions with no answer in the documents (tests for hallucination)
- Performs retrieval queries against the Knowledge Base
- Analyzes search results including document counts and relevance scores
- Evaluates the system's ability to handle different question types

### GCP Vertex AI Search
Located in `gcp_vertexai/`. Uses Google Cloud Vertex AI Search with Enterprise tier and LLM add-on. Documents are stored in GCS and optionally indexed in BigQuery. The search engine is configured with a custom schema enabling metadata filtering and faceted navigation. See [`gcp_vertexai/README.md`](gcp_vertexai/README.md) for details.

---
*Developed by [Numantic Solutions](https://numanticsolutions.com/#)*
