# Numantic Solutions | April 2026
# Module: Bedrock Knowledge Base Retriever
# Object for retrieving and generating AI results from a Bedrock Knowledge Base

import os
import pandas as pd
import time
import json

# AWS Python
import boto3


class BedrockKBRetriever:
    """
    Class to demonstrate AWS Bedrock Knowledge Base retrieve and retrieve and generate results.
    """

    def __init__(self,
                 aws_profile: str,
                 aws_region: str,
                 kb_id: str,
                 s3_bucket:str,
                 s3_path: str):

        self.aws_profile = aws_profile
        self.aws_region = aws_region
        self.kb_id = kb_id

        # Retrieval configuration
        self.num_srch_res = 5
        self.s3_bucket = s3_bucket
        self.s3_path = s3_path
        self.s3_doc_loc = "s3://{}/{}".format(self.s3_bucket,
                                              self.s3_path)

        # Retrieval and Generation configuration
        self.aws_account_id = os.environ["AWS_ACCOUNT_ID"]
        # self.inference_model = "amazon.nova-lite-v1:0" #?
        # self.inference_model = "anthropic.claude-sonnet-4-6" # Requires Anthropic request form
        # self.inference_model = "google.gemma-3-4b-it" # Not available
        # self.inference_model = "meta.llama4-scout-17b-instruct-v1:0"
        self.inference_model = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        # self.inference_model = "amazon.nova-pro-v1:0"
        # self.inference_model = "google.gemma-3-12b-it"
        self.model_arn = "arn:aws:bedrock:{}:{}:inference-profile/us.{}".format(self.aws_region,
                                                                                self.aws_account_id,
                                                                                self.inference_model)
        self.search_sleep_time = 1 # pause time between queries
        self.ai_sleep_time = 1 # pause time between queries

        # Outputs
        self.df_ret_res = pd.DataFrame()
        self.df_query_finds = pd.DataFrame()
        self.df_rag_res = pd.DataFrame()
        self.bedrock_models = pd.DataFrame() # AWS foundation models - requires get_bedrock_foundational_models method
        self.rag_responses = []
        self.client_response = "" # Direct client AI response
        self.response_models = []  # AI models available to Bedrock

        # Establish an AWS client
        self.set_aws_client()

    def set_aws_client(self):
        """
        Create a AWS client
        :return:
        """

        # Initialize Bedrock Agent Runtime client for querying
        session = boto3.Session(profile_name=self.aws_profile)

        # Bedrock client
        self.br_rt = session.client('bedrock-agent-runtime',
                                    region_name=self.aws_region)

        # Direct model queryi client (Converse API)
        self.br_runtime = session.client('bedrock-runtime', region_name=self.aws_region)

        # S3 client
        self.s3 = session.client('s3',
                                 region_name=self.aws_region)

    def get_bedrock_foundational_models(self):
        """
        Get a list of foundation models available through Bedrock
        :return:
        """

        # Initialize a bedrock client
        session = boto3.Session(profile_name=self.aws_profile)
        self.br = session.client('bedrock', region_name=self.aws_region)

        response = self.br.list_foundation_models()
        self.response_models = response

        models_rows = []
        for model in response['modelSummaries']:
            models_rows.append(dict(model_name=model['modelName'],
                                    model_id=model['modelId'],
                                    model_provider=model['providerName'],
                                    input_modalities=model['inputModalities'],
                                    output_modalities=model['outputModalities'],
                                    infer_types=model['inferenceTypesSupported'],
                                    model_lifecycle=model['modelLifecycle']
                                    )
                               )

        self.bedrock_models = pd.DataFrame(data=models_rows)
        self.bedrock_models = self.bedrock_models.sort_values(by="model_provider")
        self.bedrock_models = self.bedrock_models.reset_index(drop=True)

    def retrieve_query_results(self,
                               query: str,
                               metadata_filters: dict = None):
        """
        General search for AWS Bedrock with dynamic metadata filtering.

        :param query: A user query to apply to the Bedrock knowledge
        :param metadata_filters: Dict of key-value pairs, e.g.,
                                 {'source_type': ['pdf', 'txt'], 'document_index': [1, 2]}
        """

        # 1. Build the dynamic filter expression
        filter_expression = None

        if metadata_filters:
            filter_list = []
            for key, values in metadata_filters.items():
                if values:  # Only add if there are values to filter by
                    filter_list.append({
                        'in': {
                            'key': key,
                            'value': values
                        }
                    })

            # If multiple filters exist, wrap them in an 'and' operator
            if len(filter_list) > 1:
                filter_expression = {'and': filter_list}
            elif len(filter_list) == 1:
                filter_expression = filter_list[0]

        # 2. Set retrieval configurations
        ret_config = {
            'vectorSearchConfiguration': {
                'numberOfResults': self.num_srch_res
            }
        }

        if filter_expression:
            ret_config['vectorSearchConfiguration']['filter'] = filter_expression

        search_results = []

        # Set retrieval configurations
        ret_query_param = {'text': query
                           }

        response = self.br_rt.retrieve(knowledgeBaseId=self.kb_id,
                                       retrievalQuery=ret_query_param,
                                       retrievalConfiguration=ret_config
                                       )

        for result in response["retrievalResults"]:

            # Get metadata
            s3_loc=result['location']['s3Location']['uri']
            doc_name = s3_loc.replace(self.s3_doc_loc, "")
            key = "{}.metadata.json".format(doc_name)

            # Read the file from S3
            response_docread = self.s3.get_object(Bucket=self.s3_bucket,
                                                  Key="{}{}".format(self.s3_path,
                                                                    key)
                                                  )
            content = response_docread['Body'].read().decode('utf-8')

            # Parse JSON into dictionary
            metadata_dict = json.loads(content)
            source_type = metadata_dict["metadataAttributes"]["source_type"]

            res_dict = dict(query=query,
                            search_res=result['content']['text'],
                            score=result['score'],
                            s3_loc=result['location']['s3Location']['uri'],
                            source_type=source_type,
                            doc_metadata=metadata_dict
                            )

            search_results.append(res_dict)

            time.sleep(self.search_sleep_time)

        # Put the detailed retrieval results into a dataframe
        self.df_ret_res = pd.DataFrame(search_results)

        # Aggregate results by query
        self.aggregate_retrieval_results()

    def aggregate_retrieval_results(self):
        """
        Aggregate retrieval results by query
        :param queries:
        :return:
        """

        q_rows = []
        for query in self.df_ret_res["query"].unique():

            mask = self.df_ret_res["query"] == query

            doc_value_cnts = self.df_ret_res[mask]["s3_loc"].value_counts()

            doc_dict = {}
            for s3_loc_idx in doc_value_cnts.index:
                ikey = s3_loc_idx.replace(self.s3_doc_loc, "")
                doc_dict[ikey] = int(doc_value_cnts[s3_loc_idx])

            doc_count = len(doc_dict)

            max_score = self.df_ret_res[mask]["score"].max()

            source_types = self.df_ret_res[mask]["source_type"].unique().tolist()

            q_rows.append(dict(query=query,
                               doc_count=doc_count,
                               max_score=max_score,
                               doc_scores=doc_dict,
                               source_types=source_types
                               )
                          )

        self.df_query_finds = pd.DataFrame(q_rows)

    def _build_kb_filter(self,
                         metadata_filters: dict):
        """Helper to construct the Bedrock filter expression with type safety."""
        if not metadata_filters:
            return None

        filter_list = []
        for k, v in metadata_filters.items():
            if v is not None:
                # Ensure v is a list
                if not isinstance(v, list):
                    v = [v]

                # Ensure all elements in the list are strings
                v_string_list = [str(item) for item in v]

                filter_list.append({
                    'in': {
                        'key': k,
                        'value': v_string_list
                    }
                })

        if len(filter_list) > 1:
            return {'and': filter_list}
        return filter_list[0] if filter_list else None

    def retrieve_and_generate_results(self,
                                      query: str,
                                      metadata_filters: dict = None):
        """
        Retrieve and Generate AI responses using dynamic metadata filtering.

        :param metadata_filters: Dict like {'source_type': ['A'], 'document_index': [123]}
        """

        # 1. Construct the filter expression
        filter_expr = self._build_kb_filter(metadata_filters)

        # 2. Build the base configuration
        kb_config = {
            'knowledgeBaseId': self.kb_id,
            'modelArn': self.model_arn
        }

        # 3. Add retrievalConfiguration only if filters or custom result counts are needed
        if filter_expr or hasattr(self, 'num_srch_res'):
            kb_config['retrievalConfiguration'] = {
                'vectorSearchConfiguration': {
                    'numberOfResults': self.num_srch_res
                }
            }
            if filter_expr:
                kb_config['retrievalConfiguration']['vectorSearchConfiguration']['filter'] = filter_expr

        ret_gen_config = {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': kb_config
        }

        search_results = []
        rag_response = self.br_rt.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration=ret_gen_config
        )

        self.rag_responses.append(rag_response)

        # Collect citations using list comprehension for brevity
        citations_list = [
            ref['location']['s3Location']['uri']
            for citation in rag_response.get('citations', [])
            for ref in citation.get('retrievedReferences', [])
            if 's3Location' in ref.get('location', {})
        ]

        # Reduce and clean citations
        citations_list =  list(set(citations_list))
        citations_list = [rc.replace(self.s3_doc_loc, "").replace(".txt", "") \
                           for rc in citations_list]

        search_results.append({
            'query': query,
            'rag_answer': rag_response['output']['text'],
            'rag_citations': list(set(citations_list))
        })

        time.sleep(self.ai_sleep_time)

        self.df_rag_res = pd.DataFrame(search_results)

    def query_ai_direct(self,
                        query: str,
                        source_text: str):
        """
        Directly query an AI model via Bedrock using provided context.
        Replaces the Google query_ai_client logic.
        """
        # Define the prompt
        prompt_base = (
            "Use the provided input text to provide a short answer to the following question. "
            f"\n\nQuestion: {query} "
            f"\n\nInput Text: {source_text}"
        )

        # Format message for the Converse API
        messages = [
            {
                "role": "user",
                "content": [{"text": prompt_base}]
            }
        ]

        try:
            # Use the Converse API for multi-model compatibility
            response = self.br_runtime.converse(
                modelId=self.model_arn, # Uses your existing Inference Profile ARN
                messages=messages,
                inferenceConfig={
                    "maxTokens": 512,
                    "temperature": 0.5
                }
            )

            # Extract the text response
            self.client_response = response['output']['message']['content'][0]['text']


        except Exception as e:
            print(f"Error querying Bedrock: {e}")
            return None