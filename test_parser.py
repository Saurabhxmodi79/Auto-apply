#!/usr/bin/env python3
"""
Test script for resume parser
Tests Gemini API connection and model availability
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

def test_gemini_connection():
    """Test Gemini API connection and list available models"""
    print("=" * 60)
    print("Testing Gemini API Connection")
    print("=" * 60)
    
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY not found in environment variables")
        print("Please add it to your .env file")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:]}")
    
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured successfully")
    except Exception as e:
        print(f"❌ Failed to configure Gemini API: {e}")
        return False
    
    # List available models
    print("\n" + "=" * 60)
    print("Available Models:")
    print("=" * 60)
    
    try:
        models = genai.list_models()
        available_models = []
        
        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                model_name = model.name.replace('models/', '')
                available_models.append(model_name)
                print(f"  ✅ {model_name}")
        
        if not available_models:
            print("  ❌ No models found with generateContent support")
            return False
        
        print(f"\n✅ Found {len(available_models)} available model(s)")
        return available_models
    
    except Exception as e:
        print(f"❌ Failed to list models: {e}")
        return False


def test_model_initialization(model_name):
    """Test initializing a specific model"""
    print("\n" + "=" * 60)
    print(f"Testing Model: {model_name}")
    print("=" * 60)
    
    try:
        model = genai.GenerativeModel(model_name)
        print(f"✅ Model '{model_name}' initialized successfully")
        return model
    except Exception as e:
        print(f"❌ Failed to initialize model '{model_name}': {e}")
        return None


def test_simple_generation(model):
    """Test a simple text generation"""
    print("\n" + "=" * 60)
    print("Testing Simple Text Generation")
    print("=" * 60)
    
    try:
        prompt = "Say 'Hello, Resume Parser!' in one sentence."
        print(f"Prompt: {prompt}")
        
        response = model.generate_content(prompt)
        print(f"✅ Response: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return False


def test_resume_parsing(model):
    """Test parsing a sample resume text"""
    print("\n" + "=" * 60)
    print("Testing Resume Parsing")
    print("=" * 60)
    
    # Sample resume text
    sample_resume = """
    John Doe
    Software Engineer
    Email: john.doe@example.com
    Phone: +1-234-567-8900
    Location: San Francisco, CA
    LinkedIn: linkedin.com/in/johndoe
    GitHub: github.com/johndoe
    
    SUMMARY
    Experienced software engineer with 5+ years in full-stack development.
    
    SKILLS
    Python, JavaScript, React, Node.js, AWS, Docker, MongoDB
    
    EXPERIENCE
    Senior Software Engineer | Tech Corp | 2021-Present
    - Led development of microservices architecture
    - Improved system performance by 40%
    
    Software Engineer | Startup Inc | 2019-2021
    - Built RESTful APIs
    - Implemented CI/CD pipelines
    
    EDUCATION
    Bachelor of Science in Computer Science
    University of California, Berkeley | 2019
    GPA: 3.8
    """
    
    prompt = """Extract the following information from this resume and return it as a JSON object. 
    Be thorough and extract all relevant details. If information is not available, use null.

    Required fields:
    {
        "name": "Full name",
        "email": "Email address",
        "phone": "Phone number",
        "location": "City, State/Country",
        "linkedin": "LinkedIn profile URL",
        "github": "GitHub profile URL",
        "summary": "Professional summary or objective",
        "skills": ["skill1", "skill2", ...],
        "education": [
            {
                "degree": "Degree name",
                "institution": "University/College name",
                "graduation_date": "YYYY-MM or YYYY"
            }
        ],
        "experience": [
            {
                "title": "Job title",
                "company": "Company name",
                "start_date": "YYYY-MM or YYYY",
                "end_date": "YYYY-MM or YYYY or 'Present'",
                "description": "Job description"
            }
        ]
    }

    Resume text:
    """ + sample_resume
    
    try:
        print("Sending prompt to model...")
        response = model.generate_content(prompt)
        
        response_text = response.text.strip()
        print(f"\n✅ Raw Response received ({len(response_text)} characters)")
        print("\n" + "-" * 60)
        print("Response Preview:")
        print("-" * 60)
        print(response_text[:500])
        if len(response_text) > 500:
            print("...")
        print("-" * 60)
        
        # Try to extract JSON
        import json
        json_text = response_text
        
        # Remove markdown code blocks if present
        if "```json" in json_text:
            json_text = json_text.split("```json")[1].split("```")[0].strip()
        elif "```" in json_text:
            json_text = json_text.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        try:
            parsed_data = json.loads(json_text)
            print("\n✅ Successfully parsed JSON!")
            print("\nParsed Data:")
            print(json.dumps(parsed_data, indent=2))
            return True
        except json.JSONDecodeError as e:
            print(f"\n⚠️  JSON parsing failed: {e}")
            print("This might be okay - the model might return valid JSON in a different format")
            return False
        
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("RESUME PARSER TEST SUITE")
    print("=" * 60 + "\n")
    
    # Step 1: Test connection and list models
    available_models = test_gemini_connection()
    if not available_models:
        print("\n❌ Cannot proceed without available models")
        sys.exit(1)
    
    # Step 2: Try to initialize models (try common ones first)
    # Prioritize models that are actually available
    model_names_to_try = [
        'gemini-2.5-flash',  # Latest flash model
        'gemini-flash-latest',  # Latest flash alias
        'gemini-2.5-pro',  # Latest pro model
        'gemini-pro-latest',  # Latest pro alias
        'gemini-1.5-flash',  # Older but might work
        'gemini-1.5-pro',  # Older but might work
    ]
    
    # Also try models from the available list
    for model_name in available_models[:3]:  # Try first 3 available
        if model_name not in model_names_to_try:
            model_names_to_try.append(model_name)
    
    model = None
    working_model_name = None
    
    for model_name in model_names_to_try:
        model = test_model_initialization(model_name)
        if model:
            working_model_name = model_name
            break
    
    if not model:
        print("\n❌ Could not initialize any model")
        print("\nAvailable models from API:")
        for m in available_models:
            print(f"  - {m}")
        sys.exit(1)
    
    print(f"\n✅ Using model: {working_model_name}")
    
    # Step 3: Test simple generation
    if not test_simple_generation(model):
        print("\n❌ Simple generation test failed")
        sys.exit(1)
    
    # Step 4: Test resume parsing
    if test_resume_parsing(model):
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print(f"\nRecommended model name for resume_parser.py: {working_model_name}")
    else:
        print("\n" + "=" * 60)
        print("⚠️  SOME TESTS HAD ISSUES")
        print("=" * 60)
        print(f"\nModel '{working_model_name}' works but JSON parsing may need adjustment")


if __name__ == "__main__":
    main()

