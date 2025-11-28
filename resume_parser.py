import pdfplumber
import json
import os
import re
from typing import Dict, Any, Optional
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not set. Resume parsing will fail.")


class ResumeParser:
    """Parse resume PDFs using Google Gemini AI and extract structured data"""
    
    def __init__(self):
        """Initialize the parser with Gemini API"""
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            # Use gemini-2.5-flash (latest, faster, free tier friendly)
            # Fallback to gemini-flash-latest alias if needed
            try:
                self.model = genai.GenerativeModel('gemini-2.5-flash')
            except Exception as e:
                print(f"Warning: Failed to initialize gemini-2.5-flash: {e}")
                print("Trying gemini-flash-latest as fallback...")
                try:
                    self.model = genai.GenerativeModel('gemini-flash-latest')
                except Exception as e2:
                    print(f"Warning: Failed to initialize fallback model: {e2}")
                    self.model = None
        else:
            self.model = None
    
    def extract_urls_from_text(self, text: str) -> Dict[str, str]:
        """Extract URLs from text using regex patterns"""
        urls = {}
        
        # Pattern for full URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, text, re.IGNORECASE)
        
        for url in found_urls:
            url_lower = url.lower()
            if 'linkedin.com' in url_lower or 'linkedin' in url_lower:
                urls['linkedin'] = url
            elif 'github.com' in url_lower or 'github' in url_lower:
                urls['github'] = url
            elif 'portfolio' in url_lower or 'website' in url_lower or ('http' in url_lower and 'linkedin' not in url_lower and 'github' not in url_lower):
                if 'portfolio' not in urls:  # Only store first portfolio URL
                    urls['portfolio'] = url
        
        # Pattern for partial URLs (without http/https)
        partial_patterns = [
            (r'linkedin\.com/in/[\w-]+', 'linkedin', 'https://www.'),
            (r'github\.com/[\w-]+', 'github', 'https://www.'),
            (r'linkedin\.com/[\w/-]+', 'linkedin', 'https://www.'),
        ]
        
        for pattern, key, prefix in partial_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches and key not in urls:
                urls[key] = prefix + matches[0]
        
        return urls
    
    def extract_text(self, pdf_content: bytes) -> str:
        """Extract text and hyperlinks from PDF bytes"""
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                text = ""
                hyperlinks = {}
                
                for page_num, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    
                    # Try to extract hyperlinks from page annotations
                    try:
                        # Access the underlying PDF page object
                        pdf_page = page.page_obj if hasattr(page, 'page_obj') else None
                        if pdf_page:
                            # Try to get annotations
                            if '/Annots' in pdf_page:
                                annots = pdf_page['/Annots']
                                if annots:
                                    for annot_ref in annots:
                                        annot = annot_ref.get_object()
                                        if annot.get('/Subtype') == '/Link':
                                            # Try to get URI action
                                            if '/A' in annot:
                                                action = annot['/A']
                                                if action.get('/S') == '/URI' and '/URI' in action:
                                                    uri = action['/URI']
                                                    if isinstance(uri, bytes):
                                                        uri = uri.decode('utf-8', errors='ignore')
                                                    
                                                    # Try to identify link type
                                                    uri_lower = uri.lower()
                                                    if 'linkedin' in uri_lower:
                                                        hyperlinks['linkedin'] = uri
                                                    elif 'github' in uri_lower:
                                                        hyperlinks['github'] = uri
                                                    elif 'portfolio' in uri_lower or ('http' in uri_lower and 'linkedin' not in uri_lower and 'github' not in uri_lower):
                                                        if 'portfolio' not in hyperlinks:
                                                            hyperlinks['portfolio'] = uri
                    except Exception:
                        # If annotation extraction fails, continue
                        pass
                
                # Extract URLs from the text itself
                text_urls = self.extract_urls_from_text(text)
                
                # Merge hyperlinks (annotations take priority)
                for key, url in text_urls.items():
                    if key not in hyperlinks:
                        hyperlinks[key] = url
                
                # Append extracted URLs to text for Gemini to use
                if hyperlinks:
                    text += "\n\n[Extracted URLs from PDF (including embedded hyperlinks):]\n"
                    for key, url in hyperlinks.items():
                        text += f"{key}: {url}\n"
                
                return text.strip()
        except Exception as e:
            raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    def parse_with_gemini(self, text: str) -> Dict[str, Any]:
        """Parse resume text using Gemini AI"""
        if not self.model:
            raise ValueError("Gemini API key not configured or model initialization failed")
        
        prompt = """You are an expert resume parser. Your task is to extract EVERY piece of information from this resume with maximum detail and accuracy. 

CRITICAL INSTRUCTIONS:
1. Extract ALL information - do not summarize, abbreviate, or skip any details
2. Preserve exact text when possible - only paraphrase if necessary for clarity
3. Extract ALL entries in each section - if there are 5 jobs, extract all 5; if there are 10 skills, extract all 10
4. Look for information in ALL sections: header, summary, experience, education, skills, projects, certifications, awards, publications, volunteer work, languages, hobbies, references, etc.
5. For dates, extract exactly as written (e.g., "Jan 2020", "2020-2023", "Present", "Current")
6. For locations, extract full location details (city, state/province, country if mentioned)
7. Extract ALL bullet points, achievements, responsibilities, and descriptions - do not combine or summarize them
8. For skills, extract ALL mentioned skills including technical skills, soft skills, tools, frameworks, languages, methodologies, etc.
9. For URLs, check the entire document including headers, footers, and the "[Extracted URLs]" section
10. Extract partial information even if incomplete - better to have partial data than null

URL EXTRACTION GUIDELINES:
- Look for actual URLs (starting with http:// or https://)
- Check for URLs in headers, contact sections, and project descriptions
- If you see text like "LinkedIn", "GitHub", "Portfolio", "Website", "Blog" - find the corresponding URL nearby
- Check the "[Extracted URLs from PDF]" section if present
- If URL is incomplete (e.g., "linkedin.com/in/username"), construct full URL: "https://www.linkedin.com/in/username"
- Extract ALL URLs found, prioritize LinkedIn, GitHub, Portfolio, but also extract personal websites, blogs, etc.

EXPERIENCE SECTION - Extract ALL details:
- Extract EVERY job/position listed
- For each position, extract: exact job title, full company name, location (city, state, country), start date, end date (or "Present")
- Extract ALL bullet points under each position - convert each bullet to an achievement or description item
- Extract responsibilities, achievements, metrics (numbers, percentages, dollar amounts), technologies used, team size, etc.
- Preserve the original wording and details - do not summarize
- Extract internship, contract, part-time, full-time indicators if mentioned
- Extract ALL metrics mentioned: "20+ features", "120+ teams", "$50k+", "25% improvement", "40% reduction", etc.
- Extract ALL technologies mentioned in each role: "C#", ".NET MVC", "Entity Framework", "SQL Server", "AngularJS", etc.
- Extract ALL numbers and achievements: "Delivered 20+ features", "resolved 15+ bugs", "adopted by 120+ teams", etc.

EDUCATION SECTION - Extract ALL details:
- Extract EVERY educational entry (degrees, diplomas, certificates, courses)
- For each entry: degree type (BS, MS, PhD, MBA, B.E., etc.), field of study, major/minor, institution name, location
- Extract graduation date, start date if mentioned (format: "Dec 2020 – Jul 2024" or "2020-2024")
- Extract GPA/CGPA exactly as written: "CGPA: 8.61/10", "GPA: 3.8/4.0", etc.
- Extract honors, dean's list, academic achievements
- Extract relevant coursework if mentioned
- Extract thesis/dissertation topics if mentioned
- Extract degree abbreviations: "B.E.", "B.S.", "M.S.", "Ph.D.", "MBA", etc.

PROJECTS SECTION - Extract ALL details:
- Extract EVERY project mentioned
- For each project: full project name, complete description, ALL technologies/tools used
- Extract project URLs, GitHub links, demo links
- Extract project duration, team size, role in project
- Extract key features, challenges solved, impact/results
- Extract ALL technologies mentioned: "Node.js", "OpenAI API", "Docker", "React", "Python (Flask/FastAPI)", "PostgreSQL", etc.
- Extract metrics and impact: "reduced manual overhead by 35%", "reduced interview prep time by 40%", etc.
- Extract integration details: "integrated with VS Code and Slack", "Docker-based code execution", etc.

SKILLS SECTION - Extract EVERYTHING:
- Extract ALL technical skills: programming languages, frameworks, libraries, tools, platforms
- Extract ALL soft skills: communication, leadership, teamwork, etc.
- Extract methodologies: Agile, Scrum, DevOps, etc.
- Extract domain expertise: finance, healthcare, e-commerce, etc.
- Extract proficiency levels if mentioned (beginner, intermediate, expert)
- Extract years of experience if mentioned for specific skills
- Look for skills mentioned in experience descriptions too
- IMPORTANT: If skills are organized by categories (Frontend, Backend, Databases, etc.), extract ALL skills from ALL categories into a single flat list
- Extract skills even if they're listed under category headers like "Frontend:", "Backend:", "Tools & Others:", etc.

CERTIFICATIONS - Extract ALL:
- Extract EVERY certification, license, or credential
- Include: full certification name, issuing organization, issue date, expiry date, credential ID if mentioned
- Extract online courses, MOOCs, bootcamps if listed

AWARDS & HONORS - Extract ALL:
- Extract EVERY award, honor, recognition, scholarship
- Include: award name, organization, date, description

PUBLICATIONS - Extract ALL:
- Extract EVERY publication: papers, articles, blog posts, books
- Include: title, co-authors, publication venue, date, DOI/URL if mentioned

VOLUNTEER WORK - Extract ALL:
- Extract EVERY volunteer position
- Include: organization name, role, location, dates, description of work

LANGUAGES - Extract ALL:
- Extract ALL languages mentioned
- Include proficiency levels (native, fluent, conversational, basic)

ADDITIONAL SECTIONS to look for:
- Hobbies & Interests
- References
- Professional Memberships
- Patents
- Conferences & Speaking Engagements
- Teaching Experience
- Research Experience
- Leadership Roles (mentoring, team leadership, etc.)
- Extracurricular Activities
- Achievements & Accomplishments
- Professional Summary/Objective (may be at the top)

LEADERSHIP SECTION - Extract ALL:
- Extract mentoring experience: number of mentees, duration, impact
- Extract team leadership roles: team size, responsibilities
- Extract any leadership activities, initiatives, or roles
- Include in "volunteer_work" or create separate "leadership" array if significant

OUTPUT FORMAT - Return a complete JSON object with ALL extracted information:

{
    "name": "Full name exactly as written",
    "email": "Email address",
    "phone": "Phone number (include country code if present)",
    "location": "Full location (City, State/Province, Country)",
    "linkedin": "Full LinkedIn URL or null",
    "github": "Full GitHub URL or null",
    "portfolio": "Full Portfolio/Website URL or null",
    "summary": "Complete professional summary/objective (preserve all details)",
    "skills": ["ALL skills mentioned - technical, soft, tools, frameworks, etc."],
    "languages": ["language1 with proficiency", "language2 with proficiency", ...],
    "education": [
        {
            "degree": "Exact degree name (BS, MS, PhD, etc.)",
            "field": "Field of study/Major",
            "institution": "Full institution name",
            "location": "City, State, Country",
            "start_date": "Start date as written",
            "graduation_date": "Graduation date as written (YYYY-MM or YYYY)",
            "gpa": "GPA if mentioned",
            "honors": "Honors, dean's list, etc. if mentioned",
            "coursework": ["relevant course1", "relevant course2", ...] if mentioned,
            "thesis": "Thesis/dissertation topic if mentioned"
        }
    ],
    "experience": [
        {
            "title": "Exact job title",
            "company": "Full company name",
            "location": "City, State, Country",
            "start_date": "Start date as written",
            "end_date": "End date as written or 'Present'",
            "employment_type": "Full-time, Part-time, Contract, Internship if mentioned",
            "description": "Complete job description",
            "responsibilities": ["responsibility1", "responsibility2", ...],
            "achievements": ["achievement1 with metrics", "achievement2", ...],
            "technologies": ["tech1", "tech2", ...] used in this role,
            "team_size": "Team size if mentioned",
            "reports_to": "Manager title if mentioned"
        }
    ],
    "projects": [
        {
            "name": "Full project name",
            "description": "Complete project description",
            "technologies": ["ALL technologies/tools used"],
            "url": "Project URL if available",
            "github_url": "GitHub URL if different from main url",
            "start_date": "Start date if mentioned",
            "end_date": "End date if mentioned",
            "role": "Role in project if mentioned",
            "team_size": "Team size if mentioned",
            "key_features": ["feature1", "feature2", ...],
            "impact": "Impact/results if mentioned"
        }
    ],
    "certifications": [
        {
            "name": "Full certification name",
            "organization": "Issuing organization",
            "date": "Issue date (YYYY-MM or YYYY)",
            "expiry_date": "Expiry date if applicable",
            "credential_id": "Credential ID if mentioned",
            "credential_url": "Verification URL if mentioned"
        }
    ],
    "awards": ["Complete award name with organization and date if mentioned"],
    "publications": [
        {
            "title": "Publication title",
            "authors": "Authors if mentioned",
            "venue": "Publication venue",
            "date": "Publication date",
            "url": "URL/DOI if mentioned"
        }
    ],
    "volunteer_work": [
        {
            "organization": "Organization name",
            "role": "Role/Position",
            "location": "Location if mentioned",
            "start_date": "Start date",
            "end_date": "End date or 'Present'",
            "description": "Complete description",
            "hours": "Hours per week/month if mentioned"
        }
    ],
    "leadership": [
        {
            "role": "Leadership role (e.g., Mentor, Team Lead)",
            "organization": "Organization/Company",
            "description": "Complete description of leadership activities",
            "impact": "Impact/metrics if mentioned (e.g., 'reduced ramp-up time by 30%')",
            "start_date": "Start date if mentioned",
            "end_date": "End date or 'Present'"
        }
    ] if mentioned,
    "hobbies": ["hobby1", "hobby2", ...] if mentioned,
    "memberships": ["membership1", "membership2", ...] if mentioned,
    "patents": ["patent1", "patent2", ...] if mentioned,
    "conferences": ["conference1", "conference2", ...] if mentioned,
    "references": ["reference1", "reference2", ...] if mentioned
}

Remember: Extract EVERYTHING. It's better to have too much detail than to miss information. Preserve original wording and extract all entries in each section.

Resume text:
""" + text[:20000]  # Increased limit to capture more content
        
        try:
            response = self.model.generate_content(prompt)
            
            # Extract JSON from response
            response_text = response.text.strip()
            
            # Try to find JSON in the response (might be wrapped in markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            parsed_data = json.loads(response_text)
            
            # Add metadata
            parsed_data["parsed_at"] = datetime.utcnow().isoformat()
            parsed_data["raw_text_length"] = len(text)
            
            return parsed_data
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Gemini response as JSON: {str(e)}\nResponse: {response_text[:500]}")
        except Exception as e:
            raise ValueError(f"Gemini API error: {str(e)}")
    
    def parse(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Parse resume PDF and return structured data using Gemini AI.
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing parsed resume data
            
        Raises:
            ValueError: If parsing fails
        """
        try:
            # Extract text from PDF
            text = self.extract_text(pdf_content)
            
            if not text or len(text.strip()) < 50:
                raise ValueError("PDF appears to be empty or unreadable")
            
            # Extract URLs from text before parsing
            extracted_urls = self.extract_urls_from_text(text)
            
            # Parse with Gemini AI
            parsed_data = self.parse_with_gemini(text)
            
            # Post-process: Fill in URLs if Gemini didn't extract them but we found them
            if extracted_urls:
                if not parsed_data.get('linkedin') and 'linkedin' in extracted_urls:
                    parsed_data['linkedin'] = extracted_urls['linkedin']
                if not parsed_data.get('github') and 'github' in extracted_urls:
                    parsed_data['github'] = extracted_urls['github']
                if not parsed_data.get('portfolio') and 'portfolio' in extracted_urls:
                    parsed_data['portfolio'] = extracted_urls['portfolio']
            
            return parsed_data
        
        except Exception as e:
            raise ValueError(f"Failed to parse resume: {str(e)}")

