def get_payload_for_image_analysis(system_prompt, user_prompt, media_type, base64_image):

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": user_prompt
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "top_p": 0.9
        }

    return payload

def get_payload_for_rag_response(system_prompt, user_prompt):
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
                "maxTokens": 2000,
                "temperature": 0.1,
                "topP": 0.9,
                "stopSequences": ["\n\n"]
            }
        }

    return payload


