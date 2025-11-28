#!/usr/bin/env python3
"""
Test resume parser with an actual PDF file
Usage: python test_parser_with_pdf.py <path_to_pdf>
"""

import sys
import os
from dotenv import load_dotenv
from resume_parser import ResumeParser

# Load environment variables
load_dotenv()

def test_parser_with_pdf(pdf_path):
    """Test the resume parser with a PDF file"""
    print("=" * 60)
    print("Testing Resume Parser with PDF File")
    print("=" * 60)
    
    if not os.path.exists(pdf_path):
        print(f"❌ Error: File not found: {pdf_path}")
        return False
    
    print(f"📄 PDF File: {pdf_path}")
    print(f"📊 File Size: {os.path.getsize(pdf_path)} bytes")
    
    # Initialize parser
    print("\n" + "-" * 60)
    print("Initializing Resume Parser...")
    print("-" * 60)
    
    try:
        parser = ResumeParser()
        if not parser.model:
            print("❌ Error: Parser model not initialized")
            print("Please check your GEMINI_API_KEY in .env file")
            return False
        print("✅ Parser initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing parser: {e}")
        return False
    
    # Read PDF file
    print("\n" + "-" * 60)
    print("Reading PDF file...")
    print("-" * 60)
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        print(f"✅ PDF file read successfully ({len(pdf_content)} bytes)")
    except Exception as e:
        print(f"❌ Error reading PDF file: {e}")
        return False
    
    # Parse the resume
    print("\n" + "-" * 60)
    print("Parsing resume with Gemini AI...")
    print("-" * 60)
    print("This may take a few moments...")
    
    try:
        parsed_data = parser.parse(pdf_content)
        print("✅ Resume parsed successfully!")
    except Exception as e:
        print(f"❌ Error parsing resume: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Display results
    print("\n" + "=" * 60)
    print("PARSED RESUME DATA")
    print("=" * 60)
    
    import json
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Name: {parsed_data.get('name', 'N/A')}")
    print(f"Email: {parsed_data.get('email', 'N/A')}")
    print(f"Phone: {parsed_data.get('phone', 'N/A')}")
    print(f"Location: {parsed_data.get('location', 'N/A')}")
    print(f"Skills: {len(parsed_data.get('skills', []))} skills found")
    print(f"Experience: {len(parsed_data.get('experience', []))} positions found")
    print(f"Education: {len(parsed_data.get('education', []))} entries found")
    print(f"Projects: {len(parsed_data.get('projects', []))} projects found")
    
    print("\n✅ Test completed successfully!")
    return True


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python test_parser_with_pdf.py <path_to_pdf>")
        print("\nExample:")
        print("  python test_parser_with_pdf.py sample_resume.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if test_parser_with_pdf(pdf_path):
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe parser is ready to be integrated into the application.")
    else:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

