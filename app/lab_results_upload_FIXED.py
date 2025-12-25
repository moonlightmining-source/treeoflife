# ==================== FIXED LAB RESULTS UPLOAD ENDPOINT ====================
# Replace your existing @app.post("/api/lab-results/upload") function with this

@app.post("/api/lab-results/upload")
async def upload_lab_result(
    request: Request,
    file: UploadFile = File(...),
    provider: str = Form(...),
    test_date: str = Form(...)
):
    """Upload and extract lab results from image or PDF"""
    user_id = get_current_user_id(request)
    
    # ==================== FILE VALIDATION ====================
    
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type '{file.content_type}'. Please upload JPG, PNG, or PDF only."
        )
    
    # Read file content
    file_content = await file.read()
    
    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024  # 10MB
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )
    
    print(f"📄 Processing lab results upload: {file.filename} ({len(file_content)} bytes)")
    
    # ==================== PREPARE FOR AI EXTRACTION ====================
    
    try:
        base64_content = base64.b64encode(file_content).decode('utf-8')
        
        # Determine media type
        media_type = file.content_type
        if file.filename.lower().endswith('.pdf'):
            media_type = "application/pdf"
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            media_type = "image/jpeg"
        elif file.filename.lower().endswith('.png'):
            media_type = "image/png"
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Build content block based on file type
        if media_type == "application/pdf":
            content_block = {
                "type": "document", 
                "source": {
                    "type": "base64", 
                    "media_type": media_type, 
                    "data": base64_content
                }
            }
        else:
            content_block = {
                "type": "image", 
                "source": {
                    "type": "base64", 
                    "media_type": media_type, 
                    "data": base64_content
                }
            }
        
        # ==================== IMPROVED EXTRACTION PROMPT ====================
        
        extraction_prompt = """You are a medical lab results extraction expert. Extract ALL lab test values from this document.

CRITICAL INSTRUCTIONS:
1. Extract EVERY test result you can find
2. For EACH test, provide ALL four fields: name, value, unit, reference_range
3. Return ONLY valid JSON - no markdown, no explanations

REQUIRED JSON FORMAT:
{
  "test_type": "Name of the lab panel (e.g., 'Basic Metabolic Panel', 'Lipid Panel', 'Complete Blood Count')",
  "results": [
    {
      "name": "TEST NAME (e.g., 'SODIUM', 'Glucose', 'Hemoglobin')",
      "value": "NUMERIC VALUE ONLY (e.g., '143', '4.5', '92')",
      "unit": "UNIT (e.g., 'mEq/L', 'mg/dL', 'g/dL', '%')",
      "reference_range": "RANGE (e.g., '135-145', '70-100', '<5.7', '>50')"
    }
  ]
}

EXTRACTION RULES:
- Test names are usually in CAPS or bold (SODIUM, POTASSIUM, GLUCOSE, etc.)
- Values are the numbers next to test names (143, 4.1, 5.7, etc.)
- Units come after values (mEq/L, mg/dL, g/dL, %, etc.)
- Reference ranges are labeled "Normal range:", "Reference:", "Range:", or appear as "135-145 mEq/L"
- If you see "Normal range: 135 - 145", extract as "135-145"
- If you see "<5.7" or ">50", include the < or > symbol
- Extract the actual test name from the document, not a description

IMPORTANT:
- Do NOT skip any tests
- Do NOT leave any field empty - if you can't find reference_range, put "N/A"
- Do NOT add explanations or comments
- Return ONLY the JSON object

Now extract all lab values from this document:"""

        # ==================== CALL CLAUDE API ====================
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            temperature=0,  # Use 0 for consistent extraction
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": extraction_prompt}
                ]
            }]
        )
        
        response_text = message.content[0].text
        print(f"🤖 Raw AI Response:\n{response_text}\n")
        
        # ==================== PARSE JSON RESPONSE ====================
        
        # Clean up response - remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        response_text = response_text.strip()
        
        # Parse JSON
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print(f"Attempted to parse: {response_text[:500]}...")
            raise HTTPException(
                status_code=500,
                detail="Failed to parse extracted data. Please try uploading a clearer image."
            )
        
        # ==================== VALIDATE EXTRACTION ====================
        
        # Ensure proper structure
        if not isinstance(extracted_data, dict):
            raise HTTPException(
                status_code=500,
                detail="Invalid extraction format. Please try again."
            )
        
        if 'results' not in extracted_data:
            extracted_data['results'] = []
        
        if not isinstance(extracted_data['results'], list):
            extracted_data['results'] = []
        
        # Validate each result has required fields
        validated_results = []
        for result in extracted_data.get('results', []):
            if isinstance(result, dict):
                validated_result = {
                    'name': result.get('name', '').strip() or 'Unknown Test',
                    'value': result.get('value', '').strip() or '0',
                    'unit': result.get('unit', '').strip() or '',
                    'reference_range': result.get('reference_range', '').strip() or 'N/A'
                }
                validated_results.append(validated_result)
        
        extracted_data['results'] = validated_results
        
        # ==================== ADD METADATA ====================
        
        extracted_data['provider'] = provider
        extracted_data['test_date'] = test_date
        extracted_data['file_url'] = f"uploaded/{file.filename}"
        
        # Set default test_type if not provided
        if 'test_type' not in extracted_data or not extracted_data['test_type']:
            extracted_data['test_type'] = 'Lab Results'
        
        print(f"✅ Successfully extracted {len(validated_results)} lab values")
        print(f"📊 Test type: {extracted_data.get('test_type')}")
        
        return extracted_data
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    
    except Exception as e:
        print(f"❌ Lab extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process lab results: {str(e)}"
        )
