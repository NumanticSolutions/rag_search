# Numantic Solutions | April 2026
# Module: Bedrock Knowledge Base Security Management Utilities
# Code for creating security policies and roles to interact with a Bedrock Knowledge Base
#
# Steps
#  1. Ensure an AWS OpenSearch policy (ensure_aoss_policy)
#  2. Ensures an AWS IAM execution role with necessary permissions (ensure_execution_role)
#  3. Ensure collection data policy (ensure_data_access_policy)
#  4. Ensure IAM role with Bedrock KB permissions (ensure_iam_role)
#  5. Ensure propagation of IAM and AOSS policies (ensure_policy_propagation)


# Python
import os, sys
import json
import time


def ensure_aoss_policy(name,
                       client,
                       policy_type,
                       policy_doc):
    """
    Ensures the specified Amazon OpenSearch policy is created. If the policy already
    exists, it will catch the conflict and notify without raising an exception.
    If any other error occurs, it will be re-raised.

    :param name: The name of the policy to create.
        :type name: str
    :param client: AWS 'opensearchserverless' client.
        :type client: botocore.client.OpenSearchServiceServerless
    :param policy_type: The type of the policy (e.g., "access", "index", etc.).
        :type policy_type: str
    :param policy_doc: The policy document to be applied, typically in JSON format.
        :type policy_doc: dict
    :return: None
    """

    try:
        client.create_security_policy(name=name,
                                      type=policy_type,
                                      policy=json.dumps(policy_doc)
                                      )
        print(f"Created {policy_type} policy: {name}")
    except Exception as e:
        if 'ConflictException' in str(e):
            print(f"{policy_type.capitalize()} policy already exists: {name}")
        else:
            raise


def ensure_execution_role(client,
                          role_name,
                          bucket_name,
                          region_name,
                          embedding_model):
    """
    Ensures the creation and configuration of an AWS IAM execution role with specific
    trust and execution policies. This role is used to grant permissions to specific
    AWS services and actions relating to Bedrock and S3.

    This function creates the role if it does not exist already and attaches a trust
    policy allowing the `bedrock.amazonaws.com` service to assume the role. Additionally,
    an execution policy is defined and applied to the role to grant permissions for
    S3 and Bedrock-related actions.


    :raises iam_client.exceptions.EntityAlreadyExistsException: Raised when the IAM
        role already exists during creation attempt.
    :param client: AWS 'iam' client.
        :type client: botocore.client.IAM
    :param role_name: Name of the IAM role to create or retrieve.
        :type role_name: str
    :param bucket_name: Name of the S3 bucket to grant read access to.
        :type bucket_name: str
    :param region_name: AWS region used to scope the Bedrock InvokeModel permission.
        :type region_name: str
    :param embedding_model: Bedrock foundation model ID granted InvokeModel permission.
        :type embedding_model: str
    :return: The Amazon Resource Name (ARN) of the created or retrieved IAM role.
    :rtype: str
    """

    trust_pol = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        role_arn = client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_pol)
        )['Role']['Arn']
        print(f"Created role: {role_name}")
    except client.exceptions.EntityAlreadyExistsException:
        role_arn = client.get_role(RoleName=role_name)['Role']['Arn']
        print(f"Role already exists: {role_name}")

    exec_pol = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": [f"arn:aws:s3:::{bucket_name}", f"arn:aws:s3:::{bucket_name}/*"]
            },
            {
                "Effect": "Allow",
                "Action": ["aoss:APIAccessAll"],
                "Resource": ["*"]
            },
            {
                "Effect": "Allow",
                "Action": ["bedrock:InvokeModel"],
                "Resource": [f"arn:aws:bedrock:{region_name}::foundation-model/{embedding_model}"]
            }
        ]
    }

    # Always upsert policy to avoid stale role permissions.
    client.put_role_policy(
        RoleName=role_name,
        PolicyName='BedrockPolicy',
        PolicyDocument=json.dumps(exec_pol)
    )
    print("Upserted inline role policy: BedrockPolicy")
    return role_arn


def ensure_data_access_policy(role_arn,
                              client,
                              collection_name,
                              account_id,
                              current_user_arn):
    """
    Ensures that a data access policy exists for a specified collection. If the policy does not exist,
    it is created. If a conflicting policy exists, the existing policy is updated. If no changes are
    detected in an existing policy, the operation confirms that the policy is already up-to-date.

    :param role_arn: The ARN of the role to be granted access.
    :type role_arn: str
    :param client: The AWS 'opensearchserverless' client used to manage access policies.
    :type client: boto3.client
    :param collection_name: The name of the collection for which the access policy is being applied.
    :type collection_name: str
    :param account_id: The AWS account ID associated with the resources.
    :type account_id: str
    :param current_user_arn: The ARN of the current user performing the operation.
    :type current_user_arn: str
    :return: None
    """
    policy_name = f"{collection_name}-acc"
    role_name = role_arn.split('/')[-1]

    access_policy = [{
        "Rules": [
            {
                "Resource": [f"collection/{collection_name}"],
                "Permission": ["aoss:*"],
                "ResourceType": "collection"
            },
            {
                "Resource": [f"index/{collection_name}/*"],
                "Permission": ["aoss:*"],
                "ResourceType": "index"
            }
        ],
        "Principal": [
            role_arn,
            f"arn:aws:sts::{account_id}:assumed-role/{role_name}/*",
            current_user_arn
        ]
    }]

    try:
        client.create_access_policy(
            name=policy_name,
            type='data',
            policy=json.dumps(access_policy)
        )
        print(f"Created data access policy: {policy_name}")
    except Exception as e:
        if 'ConflictException' in str(e):
            existing_policy = client.get_access_policy(name=policy_name, type='data')
            try:
                client.update_access_policy(
                    name=policy_name,
                    type='data',
                    policyVersion=existing_policy['accessPolicyDetail']['policyVersion'],
                    policy=json.dumps(access_policy)
                )
                print(f"Updated data access policy: {policy_name}")
            except Exception as ve:
                if 'No changes detected' in str(ve):
                    print(f"Data access policy already up to date: {policy_name}")
                else:
                    raise
        else:
            raise

def ensure_iam_role(role_arn,
                    client):
    """
    Confirm if the provided IAM role exists in AWS using the given client.

    This function verifies the existence of an AWS IAM role by extracting its name
    from the provided ARN and querying the AWS API using the provided boto3 client.
    If the role is valid and exists, a success message is printed. Otherwise, an
    error message detailing the issue is displayed.

    :param role_arn: The Amazon Resource Name (ARN) of the IAM role to verify.
    :param client: The boto3 client object used to interact with the AWS API.
    :return: None
    """

    # Add before creating KB
    print(f"Using role: {role_arn}")
    try:
        role_name = role_arn.split('/')[-1]
        client.get_role(RoleName=role_name)
        print("✓ Role exists")
    except Exception as e:
        print(f"✗ Role issue: {e}")

def ensure_policy_propagation(role_arn,
                              iam_client,
                              aoss_client,
                              role_name,
                              collection_name):
    """
    Ensure propagation of IAM and AOSS policies and waits for the policies to become active before
    creating a knowledge base (KB).

    This function waits for a specified period to ensure IAM and AOSS policy propagation is complete,
    making the necessary access policies available for further operations.

    :param role_arn: The Amazon Resource Name (ARN) of the IAM role to be checked.
    :type role_arn: str
    :param iam_client: The IAM service client used to interact with the AWS IAM API.
    :type iam_client: botocore.client.BaseClient
    :param aoss_client: The AOSS service client used to interact with the AWS OpenSearch Serverless API.
    :type aoss_client: botocore.client.BaseClient
    :param role_name: The name of the IAM role to validate against the IAM service.
    :type role_name: str
    :param collection_name: The name of the AOSS collection to validate the access policy.
    :type collection_name: str
    :return: None
    :rtype: NoneType
    :raises TimeoutError: If policy propagation does not complete within the maximum allowed wait time.
    """

    # Wait for IAM and AOSS policy propagation before KB creation
    MAX_WAIT_SECONDS = 180
    SLEEP_SECONDS = 10

    print(f"Using role: {role_arn}")
    iam_client.get_role(RoleName=role_name)

    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > MAX_WAIT_SECONDS:
            raise TimeoutError("Timed out waiting for IAM/AOSS policy propagation.")

        try:
            pol = aoss_client.get_access_policy(name=f"{collection_name}-acc", type='data')
            version = pol['accessPolicyDetail']['policyVersion']
            print(f"✓ Access policy visible (version {version}); proceeding.")
            break
        except Exception as e:
            print(f"Waiting for policy propagation ({int(elapsed)}s): {e}")
            time.sleep(SLEEP_SECONDS)
