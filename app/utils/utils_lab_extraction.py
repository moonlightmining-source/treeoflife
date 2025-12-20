# utils/lab_extraction.py
# AI-powered lab result extraction using Claude Vision API

import anthropic
import base64
import json
import os
from datetime import datetime

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

async def extract_lab_data(file_path: str, provider: str, test_date: str) -> dict:
    """
    Extract lab test results from image/PDF using Claude Vision API
    
    Args:
        file_path: Path to the uploaded file
        provider: Medical provider name
        test_date: Date of the test
    
    Returns:
        dict: Extracted lab data with results
    """
    try:
        # Read file and encode to base64
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        # Determine media type
        file_ext = os.path.splitext(file_path)[1].lower()
        media_type_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.pdf': 'application/pdf'
        }
        media_type = media_type_map.get(file_ext, 'image/jpeg')
        
        # Create prompt for Claude
        extraction_prompt = f"""You are an expert medical data extraction AI. Extract ALL lab test results from this medical document.

Provider: {provider}
Date: {test_date}

Extract and return ONLY valid JSON in this EXACT format (no markdown, no explanation):

{{
    "test_type": "Blood Panel",
    "test_date": "{test_date}",
    "provider": "{provider}",
    "results": [
        {{
            "name": "Glucose",
            "value": "95",
            "unit": "mg/dL",
            "reference_range": "70-100"
        }}
    ],
    "confidence": 0.95
}}

CRITICAL RULES:
1. Extract ALL visible test results
2. Use exact names from the document
3. Include units (mg/dL, %, etc.)
4. Include reference ranges if visible
5. Return ONLY the JSON object - no markdown formatting
6. If you can't find certain data, use empty string ""
7. For test_type, choose from: Blood Panel, Lipid Panel, Metabolic Panel, Thyroid Panel, Urinalysis, or Other

Extract now:"""

        # Call Claude API
        if file_ext == '.pdf':
            # For PDF, use document type
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data
                                }
                            },
                            {
                                "type": "text",
                                "text": extraction_prompt
                            }
                        ]
                    }
                ]
            )
        else:
            # For images, use image type
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_data
                                }
                            },
                            {
                                "type": "text",
                                "text": extraction_prompt
                            }
                        ]
                    }
                ]
            )
        
        # Extract response text
        response_text = message.content[0].text.strip()
        
        # Clean JSON (remove markdown if present)
        if response_text.startswith("```json"):
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif response_text.startswith("```"):
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response_text}")
            # Return fallback data
            extracted_data = {
                "test_type": "Blood Panel",
                "test_date": test_date,
                "provider": provider,
                "results": [],
                "confidence": 0.0
            }
        
        return extracted_data
        
    except Exception as e:
        print(f"Extraction error: {e}")
        # Return fallback data
        return {
            "test_type": "Blood Panel",
            "test_date": test_date,
            "provider": provider,
            "results": [],
            "confidence": 0.0,
            "error": str(e)
        }

# Helper function for manual parsing (fallback)
def parse_common_lab_format(text: str) -> list:
    """
    Fallback parser for common lab result formats
    """
    results = []
    
    # Common patterns for lab results
    # Example: "Glucose: 95 mg/dL (70-100)"
    import re
    
    pattern = r'([A-Za-z\s]+):\s*(\d+\.?\d*)\s*([a-zA-Z/%]+)?\s*\(?([\d\-\.]+)?\)?'
    matches = re.findall(pattern, text)
    
    for match in matches:
        name, value, unit, ref_range = match
        results.append({
            "name": name.strip(),
            "value": value,
            "unit": unit or "",
            "reference_range": ref_range or ""
        })
    
    return results
