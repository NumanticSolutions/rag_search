# RAG Search Testing with AWS Bedrock Knowledge Base

This repository contains code for testing the AWS Bedrock Knowledge Base product using a standardized RAG evaluation dataset.

## About AWS Bedrock Knowledge Base

Amazon Bedrock Knowledge Bases is a fully managed service that enables you to build Retrieval Augmented Generation (RAG) applications. It provides serverless vector storage using OpenSearch Serverless, automatic document chunking and embedding, and seamless integration with foundation models for question-answering. Knowledge Bases handle the infrastructure complexity of RAG systems, allowing you to focus on building AI applications that can query and reason over your private data.

## Date
Aptil 3, 2026

## Dataset

This project uses the **Single-Topic RAG Evaluation Dataset** from Kaggle ([link](https://www.kaggle.com/datasets/samuelmatsuoharris/single-topic-rag-evaluation-dataset)).

This dataset was designed to evaluate the performance of RAG AI querying text documents about a single topic with word counts ranging from a few thousand to a few tens of thousands, such as articles, blogs, and documentation. The sources were intentionally chosen to have been produced within the last few years (from the time of writing in July 2024) and to be relatively niche, to reduce the chance of evaluated LLMs including this information in their training datasets.

**Dataset Composition:**
- **120 question-answer pairs** total
- **40 questions** that do not have an answer within the document
- **40 question-answer pairs** that require a single passage from the document
- **40 question-answer pairs** that require multiple passages from the document

## Notebooks

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

### `S30_search_bedrock_knowledgebase.ipynb`
Queries the Knowledge Base and evaluates retrieval performance. This notebook:
- Loads the test questions (no-answer, single-passage, and multi-passage)
- Performs retrieval queries against the Knowledge Base
- Analyzes search results including document counts and relevance scores
- Evaluates the system's ability to handle different question types

---

*Developed by [Numantic Solutions](https://numanticsolutions.com/#)*
