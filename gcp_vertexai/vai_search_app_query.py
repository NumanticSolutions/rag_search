# Numantic Solutions | April 2026
# Module: Vertex AI Search App Query Class
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
import requests

import pandas as pd


# GCP
from google.cloud import discoveryengine_v1 as discoveryengine
from google import genai
import google.auth
import google.auth.transport.requests


class QueryVaiSearch:
    """
    A client for querying Vertex AI Search engines and retrieving RAG-based summaries.

    This class manages the connection to a specific Search App (Engine) endpoint,
    configures the generative AI summary parameters, and parses the results into a
    Pandas DataFrame for easy analysis.

    Attributes:
        gcp_project (str): The Google Cloud Project ID.
        gcp_location (str): The location of the data store (e.g., 'global', 'us').
        search_app_id (str): The unique ID of the Search Engine/App.
        serving_config (str): The full resource path for the search serving configuration.
        last_summary (str): Stores the LLM-generated summary from the most recent query.
        struct_data_df (pd.DataFrame): DataFrame containing the metadata/structured
            fields of the retrieved documents.
    """

    def __init__(self,
                 search_app_id: str,
                 gcp_project: str,
                 gcp_location: str,
                 **kwargs):
        """
        Initializes the search client with default RAG and summary configurations. Note that this
        class uses the Vertex AI Search App API to query and retrieve documents. It provides
        methods for querying the search app, retrieving summaries, and accessing structured
        data from the retrieved documents.

        Two API calls are used to (1) retrieve content relative to searches and (2) to generate a summary
        answer based on the search results.

        Endpoints:

        - Search App Query: /default_search:search - this endpoint returns related search finds
        - Document Retrieval: /default_search:answer - this endpoint returns the answer to the query
            (based on the saerch results)

        Args:
            search_app_id (str): The ID of the search engine created in Vertex AI.
            gcp_project (str): The target GCP Project ID.
            gcp_location (str): The geographic location of the engine.
            **kwargs: Override default attributes (e.g., page_size, model_version).
        """
        self.gcp_project = gcp_project
        self.gcp_location = gcp_location
        self.search_app_id = search_app_id

        # The default_search config is standard for all Vertex AI Search Apps
        self.search_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{self.gcp_project}/locations/{self.gcp_location}/collections/default_collection/"
            f"engines/{self.search_app_id}/servingConfigs/default_search:search"
        )
        self.answer_url = (
            f"https://discoveryengine.googleapis.com/v1alpha/"
            f"projects/{self.gcp_project}/locations/{self.gcp_location}/collections/default_collection/"
            f"engines/{self.search_app_id}/servingConfigs/default_search:answer"
        )

        self.headers = {} # Updated in authentication with token

        # Authentication parameters
        self.scopes = ['https://www.googleapis.com/auth/cloud-platform']

        # Generative AI (RAG) parameters
        self.page_size = 10
        self.max_extractive_answer_count = 5
        self.max_extractive_segment_count = 1
        self.rag_ai_model = "stable"
        self.client_ai_model = "gemini-2.5-flash"

        # Output
        self.credentials = None
        self.search_response = None
        self.session_name = None
        self.query_id = None
        self.answer_response = None
        self.client_response = None
        self.answer = "" # RAG answer
        self.res_doc_ids = []  # Search document citations

        # Dynamic attribute override
        self.__dict__.update(kwargs)
        self.authenticate()

    def authenticate(self):
        """
        Initializes the Discovery Engine Search Service Client.
        Sets regional API endpoints if the location is not 'global'.
        """

        # 1. Handle Authentication
        # This finds credentials via env var or metadata server
        self.credentials, project_id = google.auth.default(scopes=self.scopes)

        # Refresh the token to ensure it is active
        auth_req = google.auth.transport.requests.Request()
        self.credentials.refresh(auth_req)

        # Update headers
        self.headers = {
            "Authorization": f"Bearer {self.credentials.token}",
            "Content-Type": "application/json"
        }

    def search_and_generate_answer(self,
                                   query: str,
                                   search_filter: str = ""):
        """
        Execute a search query and generate a summary answer based on the search results.
        :return:
        """

        # 1. Search results
        self.search_vertex_ai(query=query,
                              search_filter=search_filter)

        # 2. Get answer
        self.get_vertex_answer(query=query)

        # 3. Extract results
        self.extract_response_data()

    def search_vertex_ai(self,
                         query: str,
                         search_filter: str = ""):
        """
        Executes a search query against the Vertex AI App and updates internal state.

        This method triggers both a vector/keyword search and a generative summary
        request based on the retrieved chunks.

        Args:
            query (str): The natural language question or keywords.
            search_filter (str, optional): A SQL-like filter string used for
                metadata filtering (e.g., 'source_type: ANY("pdf")').
                Defaults to "".
        """

        # Create a search payload
        payload = {
            "query": query,
            "pageSize": self.page_size,
            "queryExpansionSpec": {"condition": "AUTO"},
            "spellCorrectionSpec": {"mode": "AUTO"},
            "languageCode": "en-US",
            "contentSearchSpec": {
                "extractiveContentSpec": {
                    "maxExtractiveAnswerCount": self.max_extractive_answer_count,
                    "maxExtractiveSegmentCount": self.max_extractive_segment_count
                }
            },
            "userInfo": {"timeZone": "America/Los_Angeles"},
            "session": (f"projects/{self.gcp_project}/locations/{self.gcp_location}/"
                        f"collections/default_collection/engines/{self.search_app_id}/sessions/-")
        }

        # Add a filter
        if len(search_filter) > 0:
            payload["filter"] = search_filter

        # 3. Execute Request
        response = requests.post(self.search_url,
                                 headers=self.headers,
                                 json=payload)

        if response.status_code == 200:

            # Get the RAG search response
            self.search_response = response.json()

            # Get session_name and query_id
            self.session_name = self.search_response["sessionInfo"]["name"]
            self.query_id = self.search_response["sessionInfo"]["queryId"]

        else:
            response.raise_for_status()

    def get_vertex_answer(self,
                          query: str):

        # 3. Payload Construction
        payload = {
            "query": {
                "text": query,
                "queryId": self.query_id
            },
            "session": self.session_name,
            "relatedQuestionsSpec": {
                "enable": True
            },
            "answerGenerationSpec": {
                "ignoreAdversarialQuery": True,
                "ignoreNonAnswerSeekingQuery": False,
                "ignoreLowRelevantContent": True,
                "includeCitations": True,
                "modelSpec": {"modelVersion": self.rag_ai_model}
            }
        }

        # 4. Request Execution
        response = requests.post(self.answer_url,
                                 headers=self.headers,
                                 json=payload)

        if response.status_code == 200:
            self.answer_response = response.json()
        else:
            response.raise_for_status()

    def extract_response_data(self):
        """
        Parses responses
        """
        # RAG answer
        self.answer = self.answer_response["answer"]["answerText"]

        # Doc citations
        self.res_doc_ids = []
        try:
            for result in self.search_response["results"]:
                self.res_doc_ids.append(result["id"])
        except:
            pass

    def query_ai_client(self,
                        query: str,
                        source_text: str):
        """
        Directly query an AI agent
        :return:
        """

        # Define a prompt base
        prompt_base = ("Use the provided input text to provide a short answer "
                       "the following question. "
                       "Question: {} "
                       "Input Text: {} "
                       )

        # Create a prompt
        prompt = prompt_base.format(query, source_text)

        # Initialize client
        client = genai.Client(vertexai=True,
                              project=self.gcp_project,
                              location=self.gcp_location
                              )

        # Get response
        self.client_response = client.models.generate_content(
            model=self.client_ai_model,
            contents=[prompt]
        )


