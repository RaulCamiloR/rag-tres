import json
import os
from helpers.rag_helpers import create_opensearch_client


def lambda_handler(event, context):
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
    }
    
    try:
        tenant_id = event.get('pathParameters', {}).get('tenant_id')
        
        if not tenant_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "tenant_id es requerido en el path"})
            }
        
        print(f"🔍 Verificando documentos para tenant: {tenant_id}")
        
        opensearch_client = create_opensearch_client()
        
        verification_result = verify_tenant_documents(tenant_id, opensearch_client)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(verification_result, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"❌ Error en verificación: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                "error": "Error interno en verificación",
                "message": str(e)
            })
        }


def verify_tenant_documents(tenant_id: str, opensearch_client):

    try:

        search_query = {
            "query": {
                "term": {
                    "tenant_id": tenant_id
                }
            },
            "size": 10,  # Máximo 10 documentos para el sample
            "sort": [
                {"created_at": {"order": "desc"}}  # Más recientes primero
            ]
        }
        
        index_pattern = "rag-documents-*"
        
        response = opensearch_client.search(
            index=index_pattern,
            body=search_query
        )
        
        hits = response.get('hits', {})
        total_hits = hits.get('total', {}).get('value', 0)
        documents = hits.get('hits', [])
        
        
        unique_indexes = set()
        document_samples = []
        
        for doc in documents:
            unique_indexes.add(doc['_index'])
            
            source = doc['_source']
            document_samples.append({
                "document_id": doc['_id'],
                "document_hash": source.get('document_hash', 'N/A'),
                "source_file": source.get('source_file', 'N/A'),
                "document_type": source.get('document_type', 'N/A'),
                "file_format": source.get('file_format', 'N/A'),
                "chunk_index": source.get('chunk_index', 0),
                "content_preview": source.get('content', '')[:150] + '...' if len(source.get('content', '')) > 150 else source.get('content', ''),
                "embedding_dimensions": len(source.get('embedding', [])),
                "created_at": source.get('created_at', 'N/A')
            })
        
        verification_result = {
            "tenant_id": tenant_id,
            "total_documents": total_hits,
            "indexes": list(unique_indexes),
            "sample_documents": document_samples,
            "statistics": {
                "unique_indexes_count": len(unique_indexes),
                "documents_shown": len(document_samples),
                "search_pattern": index_pattern
            },
            "status": "success" if total_hits > 0 else "no_documents_found"
        }
        
        return verification_result
        
    except Exception as e:
        print(f"❌ Error en verificación de documentos: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            "tenant_id": tenant_id,
            "error": f"Error buscando documentos: {str(e)}",
            "status": "error"
        }