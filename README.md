# Resume Upload Service

A simple FastAPI backend service with Streamlit frontend that accepts PDF resumes and stores them in AWS S3.

## Features

- **Backend**: FastAPI REST API for resume uploads
- **Frontend**: Streamlit web interface for easy file uploads
- Upload PDF resumes via REST API or web UI
- Automatic file validation (PDF only)
- Unique filename generation to prevent conflicts
- Stores files in S3 with organized folder structure (`resumes/`)
- **MongoDB integration**: Automatically stores resume metadata and S3 links in MongoDB Cloud
- **AI-Powered Resume Parser**: Uses Google Gemini AI to extract structured data from resumes
- **User Profile Database**: Stores parsed resume data in user profiles (deduplicated by email)
- Returns S3 URL, MongoDB document ID, and parsed profile data after successful upload

## Prerequisites

- Python 3.8 or higher
- AWS Account with S3 bucket created
- AWS Access Key ID and Secret Access Key
- MongoDB Atlas account (free tier available) or MongoDB Cloud instance
- Google Gemini API key (free tier available at https://makersuite.google.com/app/apikey)

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials:**
   - Copy `.env.example` to `.env`
   - Fill in your AWS credentials and S3 bucket name:
     ```
     AWS_ACCESS_KEY_ID=your_access_key_here
     AWS_SECRET_ACCESS_KEY=your_secret_key_here
     AWS_REGION=us-east-1
     S3_BUCKET_NAME=your-bucket-name
     ```

3. **Configure MongoDB Cloud:**
   - Create a MongoDB Atlas account at https://www.mongodb.com/cloud/atlas
   - Create a new cluster (free tier available)
   - Create a database user with read/write permissions
   - Get your connection string from "Connect" → "Connect your application"
   - Add MongoDB credentials to your `.env` file:
     ```
     MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
     MONGODB_DATABASE_NAME=resume_upload_db
     MONGODB_COLLECTION_NAME=resumes
     MONGODB_USER_PROFILE_COLLECTION=user_profiles
     ```

4. **Configure Gemini API:**
   - Get a free API key from https://makersuite.google.com/app/apikey
   - Add to your `.env` file:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

5. **Configure S3 bucket permissions:**
   - Ensure your AWS credentials have permission to upload to the S3 bucket
   - The IAM user/role needs `s3:PutObject` permission

**Note**: MongoDB connection is optional. If MongoDB credentials are not configured, the application will still work but won't save resume metadata to the database.

## Running the Application

### Backend Server (FastAPI)

```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload
```

The server will start on `http://localhost:8000`

### Frontend (Streamlit)

In a separate terminal, run:

```bash
streamlit run frontend.py
```

The Streamlit app will open in your browser at `http://localhost:8501`

**Note**: Make sure the FastAPI backend is running before starting the Streamlit frontend.

## API Endpoints

### Health Check
```
GET /health
```

### Upload Resume
```
POST /upload-resume
Content-Type: multipart/form-data

Body: file (PDF file)
```

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/upload-resume" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@resume.pdf"
```

**Example using Python requests:**
```python
import requests

url = "http://localhost:8000/upload-resume"
files = {"file": open("resume.pdf", "rb")}
response = requests.post(url, files=files)
print(response.json())
```

**Response:**
```json
{
  "message": "Resume uploaded successfully",
  "filename": "uuid-generated-filename.pdf",
  "original_filename": "resume.pdf",
  "s3_key": "resumes/uuid-generated-filename.pdf",
  "s3_url": "https://your-bucket.s3.us-east-1.amazonaws.com/resumes/uuid-generated-filename.pdf",
  "file_size": 12345,
  "mongodb_id": "507f1f77bcf86cd799439011",
  "profile_id": "507f1f77bcf86cd799439012",
  "parsed_data": {
    "name": "John Doe",
    "email": "john.doe@example.com",
    "phone": "+1-234-567-8900",
    "skills_count": 15,
    "experience_count": 3,
    "education_count": 2
  }
}
```

The `mongodb_id` field will only be present if MongoDB is properly configured.
The `profile_id` and `parsed_data` fields will only be present if Gemini API is configured and parsing succeeds.

### Get All Resumes
```
GET /resumes?limit=100
```

### Get User Profiles
```
GET /user-profiles?limit=100
```

### Get User Profile by Email
```
GET /user-profiles/{email}
```

### Get User Profile by ID
```
GET /user-profiles/id/{profile_id}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Frontend Usage

1. Start the FastAPI backend server
2. Start the Streamlit frontend
3. Open the Streamlit app in your browser
4. Use the sidebar to configure the API URL (default: `http://localhost:8000`)
5. Click "Choose a PDF file" and select your resume
6. Click "Upload Resume" button
7. View the upload details and S3 URL

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid file type or missing file)
- `500`: Server error (AWS S3 error or other internal errors)

The Streamlit frontend displays user-friendly error messages for common issues like connection errors, timeout errors, and validation errors.

## Database Schema

### Resume Records

Resume records are stored in MongoDB with the following structure:

```json
{
  "_id": "ObjectId",
  "filename": "uuid-generated-filename.pdf",
  "original_filename": "resume.pdf",
  "s3_key": "resumes/uuid-generated-filename.pdf",
  "s3_url": "https://your-bucket.s3.us-east-1.amazonaws.com/resumes/uuid-generated-filename.pdf",
  "file_size": 12345,
  "uploaded_at": "2024-01-01T12:00:00.000Z",
  "status": "uploaded"
}
```

### User Profiles

User profiles contain parsed resume data and are deduplicated by email:

```json
{
  "_id": "ObjectId",
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "+1-234-567-8900",
  "location": "San Francisco, CA",
  "linkedin": "https://www.linkedin.com/in/johndoe",
  "github": "https://github.com/johndoe",
  "portfolio": "https://johndoe.dev",
  "summary": "Experienced software engineer...",
  "skills": ["Python", "JavaScript", "React", "AWS"],
  "languages": ["English", "Spanish"],
  "education": [
    {
      "degree": "Bachelor of Science",
      "field": "Computer Science",
      "institution": "University of California",
      "location": "Berkeley, CA",
      "graduation_date": "2020-05",
      "gpa": "3.8"
    }
  ],
  "experience": [
    {
      "title": "Senior Software Engineer",
      "company": "Tech Corp",
      "location": "San Francisco, CA",
      "start_date": "2021-06",
      "end_date": "Present",
      "description": "Led development of...",
      "achievements": ["Achievement 1", "Achievement 2"]
    }
  ],
  "projects": [...],
  "certifications": [...],
  "awards": [...],
  "resume_ids": ["507f1f77bcf86cd799439011"],
  "created_at": "2024-01-01T12:00:00.000Z",
  "updated_at": "2024-01-01T12:00:00.000Z",
  "parsed_at": "2024-01-01T12:00:00.000Z"
}
```

## Project Structure

```
.
├── main.py              # FastAPI backend application
├── frontend.py          # Streamlit frontend application
├── database.py          # MongoDB database operations
├── resume_parser.py     # AI-powered resume parser using Gemini
├── pyproject.toml       # Project dependencies
├── env.example          # Environment variables template
└── README.md            # This file
```

## Resume Parsing

The application uses Google Gemini AI to extract structured data from uploaded resumes. The parser extracts:

- **Personal Information**: Name, email, phone, location
- **Social Profiles**: LinkedIn, GitHub, portfolio URLs
- **Professional Summary**: Summary or objective statement
- **Skills**: Technical and soft skills
- **Languages**: Spoken languages
- **Education**: Degrees, institutions, graduation dates, GPA
- **Experience**: Job titles, companies, dates, descriptions, achievements
- **Projects**: Project names, descriptions, technologies used
- **Certifications**: Certification names, issuers, dates
- **Awards**: Awards and honors
- **Publications**: Published works
- **Volunteer Work**: Volunteer experience

Profiles are automatically deduplicated by email address. If the same person uploads multiple resumes, their profiles are merged intelligently.

