import json
import google.generativeai as genai

def parse_disruption_natural_language(text, api_key, context_entities=None):
    """
    Uses Gemini LLM to parse natural language into a structured JSON disruption array.
    """
    genai.configure(api_key=api_key)
    
    # Dynamically find a valid model if the default isn't available
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception as e:
        pass
        
    model_name = 'gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else (available_models[0] if available_models else 'gemini-1.0-pro')
    model = genai.GenerativeModel(model_name)
    
    context_str = ""
    if context_entities:
        context_str = f"""
        Valid Rooms: {context_entities.get('rooms', [])}
        Valid Panels: {context_entities.get('panels', [])}
        Valid Companies: {context_entities.get('companies', [])}
        Valid Students: {context_entities.get('students', [])}
        """

    prompt = f"""
    You are an AI assistant for a University Placement Scheduling system.
    Your job is to extract disruptions from natural language.
    
    A disruption can be one of four types:
    1. ROOM_UNAVAILABLE (Requires a Room ID, e.g., 'R12')
    2. COMPANY_DELAY (Requires a Company ID/Name and delay_minutes as an integer)
    3. PANEL_DROPOUT (Requires a Panel ID)
    4. STUDENT_WITHDRAWAL (Requires a Student ID, e.g., 'S042')
    
    {context_str}
    
    User Input: "{text}"
    
    Analyze the user input. It may contain MULTIPLE disruptions.
    Output ONLY a raw JSON array of objects. Do not include markdown blocks like ```json.
    Each object must exactly match this format:
    {{
        "type": "<TYPE>",
        "target_id": "<TARGET_ID>",
        "details": {{ <any details like "delay_minutes"> }}
    }}
    
    If no disruption can be found, return an empty array [].
    """
    
    response = model.generate_content(prompt)
    # Clean potential markdown
    text_resp = response.text.strip().removeprefix('```json').removesuffix('```').strip()
    parsed = json.loads(text_resp)
    if isinstance(parsed, list):
        return parsed
    elif isinstance(parsed, dict):
        return [parsed]
    return []
