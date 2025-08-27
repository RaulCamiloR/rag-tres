
def get_analize_image_prompt(filename):

    system_prompt = """
    Eres un asistente especializado en analizar imágenes de documentos empresariales.
    Tu objetivo es generar descripciones ricas y detalladas que sean útiles para búsquedas semánticas posteriores.

    INSTRUCCIONES:
    - Describe el contenido visual de forma detallada y contextual
    - Extrae y transcribe TODO el texto visible con precisión
    - Identifica el tipo de documento (reporte, gráfico, tabla, presentación, etc.)
    - Describe elementos visuales importantes (gráficos, tablas, diagramas)
    - Incluye información numérica y datos específicos cuando sea visible
    - Usa un tono profesional y estructurado
    """

    user_prompt = f"""Analiza esta imagen '{filename}' y proporciona una descripción completa y estructurada de su contenido.

    FORMATO DE RESPUESTA:
    TIPO DE DOCUMENTO: [Identifica el tipo]
    CONTENIDO TEXTUAL: [Transcribe todo el texto visible]
    ELEMENTOS VISUALES: [Describe gráficos, tablas, diagramas]
    DATOS NUMÉRICOS: [Extrae números, fechas, métricas importantes]
    CONTEXTO: [Proporciona contexto empresarial relevante]

    Genera una descripción que sea útil para búsquedas semánticas posteriores.
    """

    return (system_prompt, user_prompt)

def get_image_description(filename, description):

       final_description = f"""Imagen '{filename}' analizada con Claude 3.5 Sonnet:

       {description}

       Esta imagen ha sido procesada con análisis visual avanzado multimodal y está optimizada para búsquedas semánticas."""

       return final_description

def get_image_description_error(e, filename):
    
    final_description_error = f"""Imagen '{filename}' (Error en análisis con Claude):

    CONTENIDO: Imagen subida al sistema pero no se pudo analizar con Claude 3.5 Sonnet.

    ERROR: {str(e)}

    Esta imagen está indexada y puede ser encontrada por búsquedas semánticas."""

    return final_description_error

def get_rag_response_prompt(question, context):
    system_prompt = """Eres un asistente especializado en responder preguntas basándote únicamente en la información proporcionada en los documentos. 

    INSTRUCCIONES:
    - Responde SOLO con información que aparece explícitamente en los documentos
    - Si no hay información suficiente, di claramente "No tengo información suficiente en los documentos proporcionados"
    - Mantén un tono profesional y conciso
    - Cita información específica cuando sea relevante
    - No inventes información que no esté en los documentos
    """

    user_prompt = f"""CONTEXTO DE DOCUMENTOS:
    {context}

    PREGUNTA DEL USUARIO:
    {question}

    RESPUESTA:"""

    return (system_prompt, user_prompt)

