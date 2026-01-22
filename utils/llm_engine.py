import json
import re
import time
import streamlit as st

# --- HELPER: JSON CLEANER ---
def extract_json_from_text(text):
    """
    Robustly extracts JSON object from text using regex.
    Fixes issues where LLM adds "Here is the JSON:" or markdown fences.
    """
    # 1. Try standard cleaning
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.endswith("```"):
        text = text[:-3]
    
    # 2. If simple cleaning failed to make it valid, try regex
    try:
        json.loads(text)
        return text
    except:
        # Look for the first opening brace { and the last closing brace }
        match = re.search(r'(\{.*\})', text, re.DOTALL)
        if match:
            return match.group(1)
        return text

# --- HELPER: RETRY LOGIC ---
def api_retry_wrapper(func, *args, retries=3, **kwargs):
    """
    Retries an API call if it fails due to network or overload.
    """
    for attempt in range(retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2) # Wait 2 seconds before retry
                continue
            else:
                raise e

# --- PROVIDER FUNCTIONS ---
def get_openai_json(api_key, system_prompt, user_text):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]
    )
    return response.choices[0].message.content

def get_anthropic_json(api_key, system_prompt, user_text):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4096,
        messages=[
             {"role": "user", "content": f"{system_prompt}\n\n{user_text}"}
        ]
    )
    return response.content[0].text

def get_google_json(api_key, system_prompt, user_text):
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    # Updated to a valid model version (1.5 Flash is standard as of late 2024/2025)
    model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
    
    prompt = f"{system_prompt}\n\nText to convert:\n{user_text}"
    response = model.generate_content(prompt)
    return response.text

# --- MAIN ANALYSIS FUNCTION ---
def analyze_and_structure_text(provider, api_key, text, guidance, num_slides_est):
    """
    Routes the request to the correct LLM provider.
    Analyzes text and returns structured JSON for slides.
    Includes Prompt Engineering for better quality.
    """
    
    # 1. Enhanced System Prompt
    if api_key == "TEST_KEY":
        return [
            {"title": "Intro to AI", "content": ["AI is changing the world", "It helps coders"], "notes": "Start with a strong hook."},
            {"title": "The Solution", "content": ["Automated coding", "Smart presentations"], "notes": "Explain the value prop."}
        ]

    system_prompt = f"""
    You are an expert presentation designer and content strategist.
    
    **Goal:** Convert the input text into a structured PowerPoint presentation.
    **User Guidance:** "{guidance}"
    **Target Length:** Approximately {num_slides_est} slides (adapt if necessary for flow).
    
    **Instructions:**
    1. **Structure:** Create a logical flow (e.g., Intro -> Problem -> Solution -> Conclusion).
    2. **Content:** Summarize long text into concise, punchy bullet points. Do NOT paste long paragraphs.
    3. **Tone:** Adapt the language to match the requested "{guidance}" tone.
    4. **Speaker Notes:** Write detailed script-like notes for the speaker to explain the slide.
    
    Output strictly VALID JSON. Structure:
    **JSON Output Format (Strict):**
    {{
      "slides": [
        {{
          "title": "Compelling Headline",
          "content": [
            "Short bullet point 1",
            "Short bullet point 2",
            "Key statistic or insight"
          ],
          "notes": "Detailed speaker notes explaining the context of these bullets."
        }}
      ]
    }}
    Ensure the first slide is an Intro/Title slide.
    """

    try:
        content = ""
        raw_content = ""
        
        # 2. Call Provider with Retry Logic
        if provider == "OpenAI":
            raw_content = api_retry_wrapper(get_openai_json, api_key, system_prompt, text)
        elif provider == "Anthropic":
            raw_content = api_retry_wrapper(get_anthropic_json, api_key, system_prompt, text)
        elif provider == "Google Gemini":
            raw_content = api_retry_wrapper(get_google_json, api_key, system_prompt, text)
        
        # Fallback if no provider selected (sanity check, though UI prevents this)
        if not raw_content:
             return []

        # 3. Clean and Parse JSON
        cleaned_json = extract_json_from_text(raw_content)
        data = json.loads(cleaned_json)

        # 4. Standardize Return
        if "slides" in data:
            return data["slides"]
        elif isinstance(data, list):
            return data
        else:
            st.error("AI returned valid JSON but incorrect structure (missing 'slides' key).")
            return []

    except json.JSONDecodeError:
        st.error("Error: AI response was not valid JSON. Please try again or reduce text size.")
        return None
    except Exception as e:
        st.error(f"AI Provider Error: {str(e)}")
        return None
