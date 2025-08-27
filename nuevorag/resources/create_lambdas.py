from aws_cdk import (
    Duration,  
    aws_lambda as lambda_,
    aws_iam as iam,
)

from aws_cdk.aws_lambda_python_alpha import PythonFunction


def create_test_lambda(app, prefix, layer):

    test_lambda = PythonFunction(app, f"{prefix}-TestLambda",
        runtime=lambda_.Runtime.PYTHON_3_12,
        entry="functions",  
        handler="lambda_handler",    
        index="test.py",           
        layers=[layer],    
        timeout=Duration.minutes(5), 
        memory_size=1024,         
    )

    test_lambda.add_to_role_policy(
        iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=[
            "bedrock:InvokeModel",
            "bedrock:ListFoundationModels",
            "bedrock:GetFoundationModel"
        ],
        resources=["*"]  # En producción, especifica ARNs específicos
        )
    )

    return test_lambda


def create_process_lambda(app, prefix, layer, opensearch_collection):
    """
    Crea la Lambda para procesar archivos subidos a S3
    """
    
    # Environment variables - se agregará OPENSEARCH_ENDPOINT después si es necesario
    env_vars = {}
    if opensearch_collection:
        env_vars["OPENSEARCH_ENDPOINT"] = f"https://{opensearch_collection.attr_collection_endpoint}"
    
    process_lambda = PythonFunction(app, f"{prefix}-ProcessLambda",
        runtime=lambda_.Runtime.PYTHON_3_12,
        entry="functions",  
        handler="lambda_handler",    
        index="process.py",           
        layers=[layer],    
        timeout=Duration.minutes(15),  # Más tiempo para procesamiento
        memory_size=2048,              # Más memoria para procesar archivos grandes
        environment=env_vars
    )

    # Permisos para leer de S3
    process_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetObject",
                "s3:GetObjectVersion"
            ],
            resources=["*"]  # En producción, especificar bucket específico
        )
    )
    
    # Permisos para Bedrock
    process_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            resources=["*"]
        )
    )
    
    # Permisos para Rekognition (análisis de imágenes)
    process_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "rekognition:DetectLabels",
                "rekognition:DetectText",
                "rekognition:DetectFaces"  # Opcional para futuras funcionalidades
            ],
            resources=["*"]
        )
    )
    
    # Permisos para OpenSearch Serverless (solo si la colección existe)
    if opensearch_collection:
        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "aoss:CreateIndex",
                    "aoss:DeleteIndex", 
                    "aoss:UpdateIndex",
                    "aoss:DescribeIndex",
                    "aoss:ReadDocument",
                    "aoss:WriteDocument",
                    "aoss:CreateCollection",
                    "aoss:DeleteCollection",
                    "aoss:UpdateCollection",
                    "aoss:DescribeCollection"
                ],
                resources=[opensearch_collection.attr_arn, f"{opensearch_collection.attr_arn}/*"]
            )
        )
    else:
        # Permisos generales para OpenSearch Serverless (se refinará después)
        process_lambda.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "aoss:*"
                ],
                resources=["*"]
            )
        )

    return process_lambda


def create_upload_lambda(app, prefix, layer, bucket):
    
    upload_lambda = PythonFunction(app, f"{prefix}-UploadLambda",
        runtime=lambda_.Runtime.PYTHON_3_12,
        entry="functions",  
        handler="lambda_handler",    
        index="upload.py",           
        layers=[layer],    
        timeout=Duration.minutes(1),   
        memory_size=512,              
        environment={
            "BUCKET_NAME": bucket.bucket_name
        }
    )

    upload_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            resources=[f"{bucket.bucket_arn}/uploads/*"]
        )
    )
    
    upload_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "s3:GetBucketLocation"
            ],
            resources=[bucket.bucket_arn]
        )
    )

    return upload_lambda


def create_verify_lambda(app, prefix, layer):

    verify_lambda = PythonFunction(app, f"{prefix}-VerifyLambda",
        runtime=lambda_.Runtime.PYTHON_3_12,
        entry="functions",  
        handler="lambda_handler",    
        index="verify.py",           
        layers=[layer],    
        timeout=Duration.minutes(1),   
        memory_size=512,               
        environment={
            # Se agregará OPENSEARCH_ENDPOINT en el stack principal
        }
    )

    verify_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "aoss:*"
            ],
            resources=["*"]
        )
    )

    return verify_lambda


def create_query_lambda(app, prefix, layer):

    query_lambda = PythonFunction(app, f"{prefix}-QueryLambda",
        runtime=lambda_.Runtime.PYTHON_3_12,
        entry="functions",  
        handler="lambda_handler",    
        index="query.py",           
        layers=[layer],    
        timeout=Duration.minutes(2),   
        memory_size=1024,              
        environment={
            # Se agregará OPENSEARCH_ENDPOINT en el stack principal
        }
    )

    query_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "aoss:*"
            ],
            resources=["*"]
        )
    )
    
    query_lambda.add_to_role_policy(
        iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels",
                "bedrock:GetFoundationModel"
            ],
            resources=["*"]
        )
    )

    return query_lambda