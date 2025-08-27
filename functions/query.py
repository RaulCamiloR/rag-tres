import json
from helpers.strategies import query_strategy

def lambda_handler(event, context):
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
    }
    
    try:
        body = json.loads(event.get('body', '{}'))
        
        tenant_id = body.get('tenant_id', '').strip()
        question = body.get('question', '').strip()
        document_type = body.get('document_type', None)  # Opcional
        
        validation_error = validate_query_request(tenant_id, question)
        if validation_error:
            return create_error_response(400, validation_error)
        
        if document_type:
            print(f"📂 Filtro document_type: {document_type}")
        
        rag_result = query_strategy(question, tenant_id, document_type)
        
        if not rag_result.get('success', False):
            return create_error_response(500, rag_result.get('message', 'Error en consulta RAG'))
        
        response_body = {
            'success': True,
            'answer': rag_result.get('answer'),
            'sources': rag_result.get('sources', []),
            'total_documents_searched': rag_result.get('total_documents_searched', 0),
            'tenant_id': tenant_id,
            'question': question
        }
        
        return create_success_response(response_body)
        
    except json.JSONDecodeError:
        return create_error_response(400, "Invalid JSON in request body")
    except Exception as e:
        print(f"❌ Error en query RAG: {str(e)}")
        import traceback
        traceback.print_exc()
        return create_error_response(500, "Error interno en consulta")


def validate_query_request(tenant_id, question):

    if not tenant_id:
        return "tenant_id es requerido"
    
    if not question:
        return "question es requerida"
    
    if len(question) < 3:
        return "question debe tener al menos 3 caracteres"
    
    if len(question) > 2000:
        return "question demasiado larga (máximo 2000 caracteres)"
    
    import re
    if not re.match(r'^cliente_[a-z0-9]+$', tenant_id):
        return "tenant_id debe tener formato: cliente_[a-z0-9]+"
    
    return None


def create_success_response(body):
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': json.dumps(body, ensure_ascii=False)
    }


def create_error_response(status_code, message):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        }, ensure_ascii=False)
    }