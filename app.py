#!/usr/bin/env python3
import os

import aws_cdk as cdk

from nuevorag.nuevorag_stack import NuevoragStack


app = cdk.App()

prefix = "rag-uno"

rag_stack = NuevoragStack(app, f"{prefix}-first-Stack", stack_variables={
    "prefix": prefix
})

app.synth()
