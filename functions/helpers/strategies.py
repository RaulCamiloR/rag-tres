from helpers.rag_helpers import extract_pdf_text, get_chunks, get_embeddings, get_multimodal_embeddings, analyze_image_with_claude
from helpers.opensearch_indexing import opensearch_query
from payloads.payloads import get_payload_for_rag_response
from prompting.prompts import get_rag_response_prompt
import boto3
import json
from botocore.config import Config
import base64

def pdf_strategy(text):

    try:

        text_content = extract_pdf_text(text)

        if not text_content.strip():
            return {
                "success": False,
                "message": "No se pudo extraer texto"
        }

        chunks = get_chunks(text_content, 2000, 200)

        embeddings = []
        for chunk in chunks:
            chunk_embedding = get_multimodal_embeddings(
                base64_image=None,
                input_text=chunk,
                dimensions=1024
            )
            embeddings.extend(chunk_embedding)

        return (chunks, embeddings)
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error en pdf_strategy: {str(e)}"
        }


def jpg_strategy(file_content, filename="imagen.jpg"):

    try:

        description = analyze_image_with_claude(file_content, filename)
          
        base64_image = base64.b64encode(file_content).decode('utf-8')
        
        embeddings = get_multimodal_embeddings(
            base64_image=base64_image,
            input_text=description,
            dimensions=1024
        )
        
        chunks = [description]
        
        return (chunks, embeddings)
        
    except Exception as e:
        print(f"Error en jpg_strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error procesando imagen JPG: {str(e)}"
        }


def query_strategy(question, tenant_id, document_type=None):

    try:

        question_embeddings = get_multimodal_embeddings(
            base64_image=None,
            input_text=question,
            dimensions=1024
        )
        
        if not question_embeddings or len(question_embeddings) == 0:
            return {
                "success": False,
                "message": "No se pudo generar embedding de la pregunta"
            }
        
        question_embedding = question_embeddings[0]
        
        search_result = opensearch_query(
            question_embedding, 
            tenant_id, 
            document_type
        )
        
        if not search_result.get('success', False):
            return {
                "success": False,
                "message": f"Error en búsqueda OpenSearch: {search_result.get('message', 'Error desconocido')}"
            }
        
        relevant_docs = search_result.get('documents', [])
        
        if len(relevant_docs) == 0:
            return {
                "success": True,
                "answer": "No encontré información relevante en tus documentos para responder esa pregunta.",
                "sources": [],
                "total_documents_searched": 0
            }
        
        context_chunks = []
        sources = []
        
        for i, doc in enumerate(relevant_docs[:5]):  # Top 5 documentos más relevantes
            content = doc.get('content', '')
            source_file = doc.get('source_file', 'Archivo desconocido')
            score = doc.get('score', 0)
            
            context_chunks.append(f"[Documento {i+1}]: {content}")
            sources.append({
                "source_file": source_file,
                "content_snippet": content[:200] + "..." if len(content) > 200 else content,
                "relevance_score": round(score, 3)
            })
        
        context = "\n\n".join(context_chunks)
        
        answer = generate_llm_response(question, context)
        
        if not answer:
            return {
                "success": False,
                "message": "Error generando respuesta con LLM"
            }
        
        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "total_documents_searched": len(relevant_docs)
        }
        
    except Exception as e:
        print(f"❌ Error en query_strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error en estrategia RAG: {str(e)}"
        }


def generate_llm_response(question, context):

    try:
        config = Config(
            connect_timeout=3600,  # 60 minutos
            read_timeout=3600,     # 60 minutos
            retries={'max_attempts': 1}
        )
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-east-1', config=config)
        
        system_prompt, user_prompt = get_rag_response_prompt(question, context)

        payload = get_payload_for_rag_response(system_prompt, user_prompt)
        
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        response_body = json.loads(response['body'].read())
        
        output = response_body.get('output', {})
        message = output.get('message', {})
        content = message.get('content', [])
        
        if content and len(content) > 0:
            answer = content[0].get('text', '').strip()
            if answer:
                print(f"🎯 Nova Pro respondió: {answer[:100]}...")
                return answer
        
        print("❌ Nova Pro no retornó respuesta válida")
        print(f"🔍 Response body: {response_body}")
        return None
            
    except Exception as e:
        print(f"❌ Error en generate_llm_response con Nova Pro: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

