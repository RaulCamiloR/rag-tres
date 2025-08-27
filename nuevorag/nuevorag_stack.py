from aws_cdk import (
    Duration,  
    Stack,
    aws_s3 as s3,
    aws_apigateway as apigateway,
    RemovalPolicy,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_opensearchserverless as opensearchserverless,
    aws_s3_notifications as s3n, 
    CfnOutput
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion
from constructs import Construct
import json 
from nuevorag.resources.create_lambdas import create_test_lambda, create_process_lambda, create_upload_lambda, create_verify_lambda, create_query_lambda
from nuevorag.resources.create_opensearch import create_opensearch
from nuevorag.resources.layers import create_langchain_layer

class NuevoragStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, stack_variables: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        langchain_layer = create_langchain_layer(self, stack_variables['prefix'])

        bucket = s3.Bucket(self, f"{stack_variables['prefix']}-Bucket",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        test_lambda = create_test_lambda(self, stack_variables['prefix'], langchain_layer)
        
        process_lambda = create_process_lambda(self, stack_variables['prefix'], langchain_layer, None)
        
        verify_lambda = create_verify_lambda(self, stack_variables['prefix'], langchain_layer)
        
        query_lambda = create_query_lambda(self, stack_variables['prefix'], langchain_layer)
        
        vector_collection = create_opensearch(self, stack_variables['prefix'], process_lambda.role, verify_lambda.role, query_lambda.role)
        
        process_lambda.add_environment("OPENSEARCH_ENDPOINT", f"https://{vector_collection.attr_collection_endpoint}")
        
        upload_lambda = create_upload_lambda(self, stack_variables['prefix'], langchain_layer, bucket)
        
        verify_lambda.add_environment("OPENSEARCH_ENDPOINT", f"https://{vector_collection.attr_collection_endpoint}")
        
        query_lambda.add_environment("OPENSEARCH_ENDPOINT", f"https://{vector_collection.attr_collection_endpoint}")
        

        bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(process_lambda),
            s3.NotificationKeyFilter(prefix="uploads/") 
        )

        api = apigateway.RestApi(self, f"{stack_variables['prefix']}-Api")

        test_resource = api.root.add_resource("test")
        test_resource.add_method("POST", apigateway.LambdaIntegration(test_lambda))
        
        upload_resource = api.root.add_resource("upload")
        upload_resource.add_method("POST", apigateway.LambdaIntegration(upload_lambda))
        
        verify_resource = api.root.add_resource("verify")
        tenant_resource = verify_resource.add_resource("{tenant_id}")
        tenant_resource.add_method("GET", apigateway.LambdaIntegration(verify_lambda))
        
        # Endpoint /query
        query_resource = api.root.add_resource("query")
        query_resource.add_method("POST", apigateway.LambdaIntegration(query_lambda))
        
        # Método OPTIONS para CORS en todos los endpoints
        for resource in [test_resource, upload_resource, tenant_resource, query_resource]:
            resource.add_method("OPTIONS", apigateway.MockIntegration(
                integration_responses=[{
                    'statusCode': '200',
                    'responseParameters': {
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Methods': "'GET,POST,OPTIONS'"
                    }
                }],
                passthrough_behavior=apigateway.PassthroughBehavior.WHEN_NO_MATCH,
                request_templates={"application/json": "{\"statusCode\": 200}"}
            ), method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Origin': True,
                    'method.response.header.Access-Control-Allow-Methods': True
                }
            }])

        CfnOutput(self, "ApiUrl",
            value=api.url,
            description="URL base del API Gateway"
        )
        
        CfnOutput(self, "TestEndpoint", 
            value=f"{api.url}test",
            description="URL completa del endpoint /test"
        )
        
        CfnOutput(self, "UploadEndpoint", 
            value=f"{api.url}upload",
            description="URL completa del endpoint /upload"
        )
        
        CfnOutput(self, "VerifyEndpoint", 
            value=f"{api.url}verify/{{tenant_id}}",
            description="URL del endpoint /verify - reemplazar {{tenant_id}} con ID real"
        )
        
        CfnOutput(self, "QueryEndpoint", 
            value=f"{api.url}query",
            description="URL del endpoint /query para consultas RAG"
        )
        
        CfnOutput(self, "ProcessLambdaName",
            value=process_lambda.function_name,
            description="Nombre de la función Lambda que procesa archivos S3"
        )
        
        CfnOutput(self, "S3BucketName",
            value=bucket.bucket_name,
            description="Nombre del bucket S3 (sube archivos a la carpeta uploads/)"
        )
        
        CfnOutput(self, "OpenSearchEndpoint",
            value=f"https://{vector_collection.attr_collection_endpoint}",
            description="Endpoint de OpenSearch Serverless para conectividad"
        )
        
        CfnOutput(self, "OpenSearchCollectionId",
            value=vector_collection.attr_id,
            description="ID de la colección OpenSearch Serverless"
        )