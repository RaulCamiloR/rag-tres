from aws_cdk import (
    aws_opensearchserverless as opensearchserverless,
)
import json

def create_opensearch(app, prefix, process_lambda_role, verify_lambda_role=None, query_lambda_role=None):

    network_policy = opensearchserverless.CfnSecurityPolicy(
        app, f"{prefix}-network-policy",
        name=f"{prefix}-network-policy",
        type="network",
        policy=json.dumps([
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{prefix}-vector-collection"]
                    }
                ],
                "AllowFromPublic": True,
                
            }
        ])
    )

    encryption_policy = opensearchserverless.CfnSecurityPolicy(
        app, f"{prefix}-encryption-policy", 
        name=f"{prefix}-encryption-policy",
        type="encryption",
        policy=json.dumps({
            "Rules": [
                {
                    "Resource": [f"collection/{prefix}-vector-collection"],
                    "ResourceType": "collection"
                }
            ],
            "AWSOwnedKey": True  # Usar AWS managed key
        })
    )

    # Data Access Policy - CRÍTICO para acceso desde Lambda
    # Incluir roles: process, verify y query
    principals = [process_lambda_role.role_arn]
    if verify_lambda_role:
        principals.append(verify_lambda_role.role_arn)
    if query_lambda_role:
        principals.append(query_lambda_role.role_arn)
    
    data_access_policy = opensearchserverless.CfnAccessPolicy(
        app, f"{prefix}-data-access-policy",
        name=f"{prefix}-data-access-policy",
        type="data",
        description="Data access policy for Lambda to access OpenSearch collection and indexes",
        policy=json.dumps([
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{prefix}-vector-collection"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:UpdateCollectionItems", 
                            "aoss:DescribeCollectionItems"
                        ]
                    },
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{prefix}-vector-collection/*"],
                        "Permission": ["aoss:*"]
                    }
                ],
                "Principal": principals
            }
        ])
    )

    vector_collection = opensearchserverless.CfnCollection(
        app, f"{prefix}-vector-collection",
        name=f"{prefix}-vector-collection",
        type="VECTORSEARCH",  # Optimizada para búsqueda vectorial
        description="Multi-tenant RAG vector search collection"
    )

    vector_collection.add_dependency(network_policy)
    vector_collection.add_dependency(encryption_policy)
    vector_collection.add_dependency(data_access_policy)

    return vector_collection