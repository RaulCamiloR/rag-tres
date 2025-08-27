from aws_cdk import (
    Duration,  
    aws_lambda as lambda_,
    aws_iam as iam,
)

from aws_cdk.aws_lambda_python_alpha import PythonFunction, PythonLayerVersion

def create_langchain_layer(app, prefix):

    langchain_layer = PythonLayerVersion(
        app,
        f"{prefix}-LangChainAWSLayer",
        entry="layers/langchain_layer",
        compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
        description="Layer con LangChain-AWS y dependencias relacionadas"
    )

    return langchain_layer

