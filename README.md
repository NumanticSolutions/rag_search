# RAG Search Testing with AWS Bedrock Knowledge Base

This repository contains code for testing the AWS Bedrock Knowledge Base product using a standardized RAG evaluation dataset.

## About AWS Bedrock Knowledge Base

Amazon Bedrock Knowledge Bases is a fully managed service that enables you to build Retrieval Augmented Generation (RAG) applications. It provides serverless vector storage using OpenSearch Serverless, automatic document chunking and embedding, and seamless integration with foundation models for question-answering. Knowledge Bases handle the infrastructure complexity of RAG systems, allowing you to focus on building AI applications that can query and reason over your private data.

## Date
April 25, 2026

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

# S3 Configuration
S3_BUCKET=<your-s3-bucket-name>
S3_PREFIX=<your-s3-prefix-with-trailing-slash>/

# Bedrock / OpenSearch Configuration
COLLECTION_NAME=<your-opensearch-collection-name>
KB_NAME=<your-knowledge-base-name>
INDEX_NAME=bedrock-knowledge-base-default-index
ROLE_NAME=AmazonBedrockExecutionRoleForKnowledgeBase
EMBEDDING_MODEL=amazon.titan-embed-text-v2:0

# Knowledge Base ID (generated on creation — update after rebuilding)
KB_ID=<your-knowledge-base-id>
```

`AWS_PROFILE` refers to a named profile in your `~/.aws/credentials` file. If you have not configured named profiles, use `default`.

## Notebooks

The notebooks are designed to be run in sequence (S10 → S20 → S30). However, see the note on S20 below if you already have a provisioned Knowledge Base.

### `S10_load_data_s3.ipynb`
Loads the RAG evaluation dataset to Amazon S3 in a Bedrock-compatible format. This notebook:
- Reads the local CSV files containing documents and questions
- Adds metadata attributes (source type, document index) to enable filtering
- Annotates documents with passage numbers for better retrieval tracking
- Uploads documents and metadata sidecars to S3

### `S20_build_bedrock_knowledgebase.ipynb`
Creates and configures the AWS Bedrock Knowledge Base infrastructure. This notebook:
- Sets up OpenSearch Serverless collection with security policies
- Creates IAM roles and permissions for Bedrock access
- Creates the Knowledge Base with vector embeddings using Amazon Titan
- Configures the S3 data source
- Initiates and monitors the document ingestion process

**If you do not already have a Knowledge Base:** You will have to uncommment the code blocks in S20 that provision both a new knowledge base and an execution role used to run the document ingestion process. Aftewards, set `KB_ID` in your `.env` file to the resulting Knowledge Base ID (or to the ID of your pre-existing Knowledge Base), comment out that same code (so it does not run again later). The KB ID is visible in the AWS console under Bedrock > Knowledge Bases, or was printed at the end of a prior S20 run as `✓ Knowledge Base Created: <KB_ID>`.

### `S30_search_bedrock_knowledgebase.ipynb`
Queries the Knowledge Base and evaluates retrieval performance. This notebook:
- Loads the evaluation dataset — ground-truth questions and answers used to benchmark the Knowledge Base
  - `documents.csv` — the 20 source documents indexed in the Knowledge Base
  - `single_passage_answer_questions.csv` — questions answerable from a single passage
  - `multi_passage_answer_questions.csv` — questions requiring multiple passages
  - `no_answer_questions.csv` — questions with no answer in the documents (tests for hallucination)
- Performs retrieval queries against the Knowledge Base
- Analyzes search results including document counts and relevance scores
- Evaluates the system's ability to handle different question types

## Dataset

This project uses the **Single-Topic RAG Evaluation Dataset** from Kaggle ([link](https://www.kaggle.com/datasets/samuelmatsuoharris/single-topic-rag-evaluation-dataset)).

This dataset was designed to evaluate the performance of RAG AI querying text documents about a single topic with word counts ranging from a few thousand to a few tens of thousands, such as articles, blogs, and documentation. The sources were intentionally chosen to have been produced within the last few years (from the time of writing in July 2024) and to be relatively niche, to reduce the chance of evaluated LLMs including this information in their training datasets.

**Dataset Composition:**
- **120 question-answer pairs** total
- **40 questions** that do not have an answer within the document
- **40 question-answer pairs** that require a single passage from the document
- **40 question-answer pairs** that require multiple passages from the document

---

*Developed by [Numantic Solutions](https://numanticsolutions.com/#)*
