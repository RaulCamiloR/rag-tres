from helpers.rag_helpers import extract_pdf_text, get_chunks, get_embeddings, get_multimodal_embeddings, analyze_image_with_rekognition
from helpers.opensearch_indexing import opensearch_query
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

        # Usar Titan Multimodal para compatibilidad con imágenes
        embeddings = []
        for chunk in chunks:
            chunk_embedding = get_multimodal_embeddings(
                base64_image=None,  # Solo texto
                input_text=chunk,
                dimensions=1024
            )
            embeddings.extend(chunk_embedding)  # get_multimodal_embeddings devuelve lista

        return (chunks, embeddings)
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Error en pdf_strategy: {str(e)}"
        }


def jpg_strategy(file_content, filename="imagen.jpg"):
    """
    Procesa imagen JPG usando Rekognition para análisis visual y embeddings multimodales
    
    Args:
        file_content: Contenido binario de la imagen JPG
        filename: Nombre del archivo para referencia
    
    Returns:
        chunks, embeddings: Tupla con descripción de Rekognition y embeddings multimodales
    """

    try:
        
        import base64
        
        print(f"🖼️ Procesando imagen: {filename}")
        
        # 1. Analizar imagen con Rekognition para obtener descripción textual
        description = analyze_image_with_rekognition(file_content, filename)
        
        # 2. Convertir imagen a base64 para embeddings multimodales  
        base64_image = base64.b64encode(file_content).decode('utf-8')
        print(f"📝 Base64 generado: {len(base64_image)} caracteres")
        
        # 3. Generar embeddings multimodales combinando imagen + descripción textual
        embeddings = get_multimodal_embeddings(
            base64_image=base64_image,
            input_text=description,  # Combinar imagen con descripción de Rekognition
            dimensions=1024
        )
        
        # 4. Usar descripción real en lugar de placeholder
        chunks = [description]  # Descripción textual rica del contenido visual
        
        print(f"✅ jpg_strategy completada: imagen analizada → descripción + embedding híbrido")
        return (chunks, embeddings)
        
    except Exception as e:
        print(f"❌ Error en jpg_strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error procesando imagen JPG: {str(e)}"
        }


def query_strategy(question, tenant_id, document_type=None):

    try:

        # Usar Titan Multimodal para compatibilidad con imágenes indexadas
        question_embeddings = get_multimodal_embeddings(
            base64_image=None,  # Solo texto para query
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
        
        system_prompt = """Eres un asistente especializado en responder preguntas basándote únicamente en la información proporcionada en los documentos. 

INSTRUCCIONES:
- Responde SOLO con información que aparece explícitamente en los documentos
- Si no hay información suficiente, di claramente "No tengo información suficiente en los documentos proporcionados"
- Mantén un tono profesional y conciso
- Cita información específica cuando sea relevante
- No inventes información que no esté en los documentos"""

        user_prompt = f"""CONTEXTO DE DOCUMENTOS:
{context}

PREGUNTA DEL USUARIO:
{question}

RESPUESTA:"""

        # Payload para Amazon Nova Pro (formato messages-v1)
        payload = {
            "schemaVersion": "messages-v1",
            "system": [
                {
                    "text": system_prompt
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "text": user_prompt
                        }
                    ]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 1000,
                "temperature": 0.1,
                "topP": 0.9,
                "stopSequences": []
            }
        }
        
        # Llamar a Amazon Nova Pro
        response = bedrock_runtime.invoke_model(
            modelId="amazon.nova-pro-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        
        # Parsear respuesta
        response_body = json.loads(response['body'].read())
        
        # Nova Pro retorna la respuesta en formato similar a Claude v3
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

