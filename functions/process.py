import json
import urllib.parse
import boto3
import os
from helpers.rag_helpers import (
    extract_pdf_text, 
    get_chunks, 
    get_embeddings,
    create_opensearch_client,
    create_index_if_not_exists,
    index_document_bulk
)
from helpers.strategies import pdf_strategy, jpg_strategy
from helpers.opensearch_indexing import opensearch_indexing

def lambda_handler(event, context):
    
    s3_client = boto3.client('s3')
    
    for record in event.get('Records', []):
        try:
            event_name = record.get('eventName', '')
            bucket_name = record['s3']['bucket']['name']
            object_key = urllib.parse.unquote_plus(
                record['s3']['object']['key'], 
                encoding='utf-8'
            )
            object_size = record['s3']['object']['size']
            
            path_parts = object_key.split('/')
            if len(path_parts) < 3:
                print(f"❌ Path inválido: {object_key}")
                continue
                
            tenant_id = path_parts[1] if path_parts[0] == 'uploads' else 'unknown'
            document_type = path_parts[2] if len(path_parts) >= 3 else 'general'
            filename = path_parts[-1]
            
            extension = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
            
            print(f"Tenant ID: {tenant_id}")
            print(f"Tipo documento: {document_type}")
            print(f"Nombre archivo: {filename}")
            print(f"Extensión: {extension}")
            
            result = process_file(
                s3_client, bucket_name, object_key, 
                tenant_id, document_type, filename, extension
            )
              
        except Exception as e:
            print(f"❌ Error procesando archivo {object_key}: {str(e)}")
            continue
        
        print("=== FIN PROCESAMIENTO ===")
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Procesados {len(event.get("Records", []))} archivos exitosamente'
        })
    }


def process_file(s3_client, bucket_name, object_key, tenant_id, document_type, filename, extension):
    
    try:
        
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response['Body'].read()

        embeddings = None
        chunks = None

        if extension == '.pdf':
            chunks, embeddings = pdf_strategy(file_content)
        
        elif extension == '.jpg':
            chunks, embeddings = jpg_strategy(file_content, filename)
        
        else:
            return {
                "message": "Proximamente mas extensiones"
            }

        
        if not embeddings or not chunks:
            return {
                "success": False,
                "message": "No se pudieron generar embeddings o chunks"
            }
        
        opensearch_indexing(embeddings, chunks, tenant_id, document_type, object_key, filename)

        return {
            "success": True,
            "message": "Archivo procesado correctamente"
        }

        
    except Exception as e:
        print(f"❌ Error procesando PDF: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error procesando PDF: {str(e)}"
        }