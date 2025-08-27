import json
import boto3
import uuid
import re
import os
from datetime import datetime

headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
}

allowed_types = ['general']

def lambda_handler(event, context):

    s3_client = boto3.client('s3')
    
    try:
    
        body = json.loads(event.get('body', '{}'))
        
        tenant_id = body.get('tenant_id', '').strip()
        document_type = body.get('document_type', '').strip()
        filename = body.get('filename', '').strip()
        content_type = body.get('content_type', '').strip()
        
        validation_error = validate_upload_request(tenant_id, document_type, filename, content_type)

        if validation_error:
            return create_error_response(400, validation_error)
        
        bucket_name = get_bucket_name()
        
        file_key = generate_file_key(tenant_id, document_type, filename)
        
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'ContentType': content_type
            },
            ExpiresIn=300, 
            HttpMethod='PUT'
        )
        
        response_body = {
            'success': True,
            'upload_url': presigned_url,
            'file_key': file_key,
            'expires_in': 300,
            'method': 'PUT',
            'headers': headers,
            'tenant_id': tenant_id,
            'document_type': document_type
        }
        
        return create_success_response(response_body)
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body")
    except Exception as e:
        print(f"Error generating presigned URL: {str(e)}")
        return create_error_response(500, "Internal server error")


def validate_upload_request(tenant_id, document_type, filename, content_type):

    if not tenant_id:
        return "tenant_id is required"
    
    if not re.match(r'^cliente_[a-z0-9]+$', tenant_id):
        return "tenant_id must match format: cliente_[a-z0-9]+"

    if document_type not in allowed_types:
        return f"document_type must be one of: {', '.join(allowed_types)}"
    
    if not filename:
        return "filename is required"
    
    if len(filename) > 255:
        return "filename too long (max 255 characters)"
    
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return "filename contains invalid characters. Use only: a-z, A-Z, 0-9, ., _, -"
    
    allowed_content_types = {
        'application/pdf': ['.pdf'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
        'text/csv': ['.csv'],
        'application/msword': ['.doc'],
        'application/vnd.ms-excel': ['.xls'],
        'application/vnd.ms-powerpoint': ['.ppt'],
        # Tipos de imagen soportados
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/webp': ['.webp']
    }
    
    if content_type not in allowed_content_types:
        return f"content_type not allowed. Supported: {', '.join(allowed_content_types.keys())}"
    
    file_extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
    if file_extension not in allowed_content_types[content_type]:
        return f"File extension {file_extension} doesn't match content_type {content_type}"
    
    return None


def generate_file_key(tenant_id, document_type, filename):

    file_uuid = str(uuid.uuid4())[:8]
    
    timestamp = datetime.now().strftime('%Y%m%d')
    
    safe_filename = filename.replace(' ', '_')
    file_key = f"uploads/{tenant_id}/{document_type}/{timestamp}_{file_uuid}_{safe_filename}"
    
    return file_key


def get_bucket_name():

    bucket_name = os.environ.get('BUCKET_NAME')
    
    if not bucket_name:
        raise ValueError("BUCKET_NAME environment variable not set")
    
    return bucket_name


def create_success_response(body):
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps(body)
    }


def create_error_response(status_code, message):
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }