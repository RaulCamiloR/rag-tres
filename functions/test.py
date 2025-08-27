
import json

from helpers.rag_helpers import get_embeddings, get_chunks


def lambda_handler(event, context):
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token'
    }
    
    try:

        body_data = json.loads(event.get('body', '{}'))
        
        if 'text' not in body_data:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "Field 'text' is required"})
            }
        
        text = body_data['text']
        
        if not text.strip():
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "Text cannot be empty"})
            }
        
        chunks = get_chunks(text, 1000, 200)
        
        if not chunks:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({"error": "No chunks were generated from the text"})
            }
        
        embeddings = get_embeddings(chunks, model_id="amazon.titan-embed-text-v2:0", dimensions=1024)
        
        if not embeddings:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({"error": "Failed to generate embeddings"})
            }
        
        response_body = {
            "ok": True,
            "chunks": chunks[:3],
            "embeddings": embeddings[:3]
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in request body: {e}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({"error": "Invalid JSON in request body"})
        }
    except Exception as e:
        print(f"❌ Error in processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                "error": "Internal processing error",
                "message": str(e)
            })
        }
