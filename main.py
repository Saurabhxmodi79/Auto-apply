from fastapi import FastAPI, File, UploadFile, HTTPException, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv
import uuid
from typing import Optional
from database import (
    save_resume_with_profile, 
    get_mongodb_client, 
    get_all_resumes, 
    get_resume_by_s3_key,
    get_resumes_by_email
)
from pymongo.errors import ConnectionFailure, OperationFailure
from resume_parser import ResumeParser

# Load environment variables
load_dotenv()

app = FastAPI(title="Resume Upload Service", version="1.0.0")

# Initialize S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Get S3 bucket name from environment
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

if not S3_BUCKET_NAME:
    raise ValueError("S3_BUCKET_NAME environment variable is required")

# Initialize MongoDB connection
try:
    get_mongodb_client()
except (ValueError, ConnectionFailure) as e:
    print(f"Warning: MongoDB connection failed: {e}")
    print("Resume records will not be saved to MongoDB")


@app.get("/")
async def root():
    return {"message": "Resume Upload Service is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/test-mongodb")
async def test_mongodb():
    """
    Test MongoDB connection endpoint.
    
    Returns:
        JSON response with MongoDB connection status and database information
    """
    try:
        from database import get_mongodb_client, get_database, get_collection
        
        # Test connection
        client = get_mongodb_client()
        db = get_database()
        collection = get_collection()
        
        # Get document count
        count = collection.count_documents({})
        
        # Get database and collection names
        db_name = db.name
        collection_name = collection.name
        
        # Count documents with profile data
        profiles_count = collection.count_documents({"email": {"$exists": True, "$ne": None}})
        
        return {
            "status": "success",
            "message": "MongoDB connection successful",
            "database": db_name,
            "collection": collection_name,
            "total_documents": count,
            "documents_with_profiles": profiles_count,
            "connection": "active"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB not configured: {str(e)}"
        )
    except ConnectionFailure as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing MongoDB: {str(e)}"
        )


@app.get("/resumes")
async def get_resumes(limit: int = 100):
    """
    Get all uploaded resumes with integrated user profile data.
    
    Args:
        limit: Maximum number of resumes to return (default: 100)
        
    Returns:
        JSON response with list of resumes (each includes profile data if available)
    """
    try:
        resumes = get_all_resumes(limit=limit)
        
        return {
            "status": "success",
            "count": len(resumes),
            "resumes": resumes
        }
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB not configured: {str(e)}"
        )
    except ConnectionFailure as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving resumes: {str(e)}"
        )


@app.delete("/resumes/{resume_id}/mongodb")
async def delete_resume_from_mongodb(resume_id: str):
    """
    Delete a resume record from MongoDB only.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        JSON response with deletion status
    """
    try:
        from database import get_resume_before_delete, delete_resume
        
        # Get resume data before deletion
        resume_data = get_resume_before_delete(resume_id)
        
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found in MongoDB")
        
        # Delete resume from MongoDB
        deleted = delete_resume(resume_id)
        
        if deleted:
            return {
                "status": "success",
                "message": "Resume deleted from MongoDB successfully",
                "resume_id": resume_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete resume from MongoDB")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting resume from MongoDB: {str(e)}"
        )


@app.delete("/resumes/{resume_id}/s3")
async def delete_resume_from_s3(resume_id: str):
    """
    Delete a resume file from S3 only.
    
    Args:
        resume_id: MongoDB document ID (used to find s3_key)
        
    Returns:
        JSON response with deletion status
    """
    try:
        from database import get_resume_before_delete
        
        # Get s3_key from resume record
        resume_data = get_resume_before_delete(resume_id)
        
        if not resume_data:
            raise HTTPException(
                status_code=404,
                detail="Resume not found in MongoDB"
            )
        
        s3_key = resume_data.get('s3_key')
        
        if not s3_key:
            raise HTTPException(
                status_code=404,
                detail="S3 key not found in resume data"
            )
        
        # Delete from S3
        try:
            print(f"Attempting to delete S3 object: {s3_key} from bucket: {S3_BUCKET_NAME}")
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            print(f"Successfully deleted S3 object: {s3_key}")
            
            return {
                "status": "success",
                "message": "Resume deleted from S3 successfully",
                "resume_id": resume_id,
                "s3_key": s3_key
            }
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey':
                return {
                    "status": "success",
                    "message": "S3 object not found (may have been deleted already)",
                    "resume_id": resume_id,
                    "s3_key": s3_key
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error deleting from S3 (Code: {error_code}): {str(e)}"
                )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting resume from S3: {str(e)}"
        )


@app.delete("/resumes/{resume_id}/profile")
async def delete_resume_from_profile(resume_id: str):
    """
    Delete user profile data from a resume document (keeps resume metadata).
    Note: With combined structure, this removes profile fields but keeps resume info.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        JSON response with deletion status
    """
    try:
        from database import get_resume_before_delete, get_collection
        from bson import ObjectId
        
        resume_data = get_resume_before_delete(resume_id)
        
        if not resume_data:
            raise HTTPException(
                status_code=404,
                detail="Resume not found"
            )
        
        # Remove profile fields but keep resume metadata
        collection = get_collection()
        profile_fields_to_remove = [
            "name", "email", "phone", "location", "linkedin", "github", "portfolio",
            "summary", "skills", "languages", "education", "experience", "projects",
            "certifications", "awards", "publications", "volunteer_work",
            "parsed_at", "raw_text_length"
        ]
        
        unset_dict = {field: "" for field in profile_fields_to_remove}
        
        try:
            result = collection.update_one(
                {"_id": ObjectId(resume_id)},
                {"$unset": unset_dict}
            )
        except Exception:
            result = collection.update_one(
                {"_id": resume_id},
                {"$unset": unset_dict}
            )
        
        if result.modified_count > 0:
            return {
                "status": "success",
                "message": "Profile data removed from resume (resume metadata kept)",
                "resume_id": resume_id
            }
        else:
            return {
                "status": "success",
                "message": "No profile data found to remove",
                "resume_id": resume_id
            }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing profile data: {str(e)}"
        )


@app.delete("/resumes/{resume_id}")
async def delete_resume_endpoint(resume_id: str):
    """
    Delete a resume record from MongoDB and S3.
    Since profile data is integrated, deleting the resume also removes its profile data.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        JSON response with deletion status
    """
    try:
        from database import get_resume_before_delete, delete_resume
        
        # Get resume data before deletion (needed for S3 deletion)
        resume_data = get_resume_before_delete(resume_id)
        
        if not resume_data:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        s3_key = resume_data.get('s3_key')
        
        # Delete resume from MongoDB (includes profile data)
        resume_deleted = False
        try:
            resume_deleted = delete_resume(resume_id)
            print(f"Resume deleted from MongoDB: {resume_deleted}")
        except Exception as e:
            print(f"Error deleting resume from MongoDB: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete resume: {str(e)}")
        
        # Delete from S3
        s3_deleted = False
        s3_error = None
        if s3_key:
            try:
                print(f"Attempting to delete S3 object: {s3_key} from bucket: {S3_BUCKET_NAME}")
                s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                s3_deleted = True
                print(f"Successfully deleted S3 object: {s3_key}")
            except ClientError as e:
                s3_error = str(e)
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                if error_code == 'NoSuchKey':
                    print(f"S3 object not found (may have been deleted already): {s3_key}")
                    s3_deleted = True  # Consider it deleted if it doesn't exist
                else:
                    print(f"Error deleting from S3 (Code: {error_code}): {e}")
            except Exception as e:
                s3_error = str(e)
                print(f"Unexpected error deleting from S3: {e}")
        else:
            s3_error = "No s3_key found in resume data"
            print(f"Warning: {s3_error}")
        
        response_data = {
            "status": "success",
            "message": "Resume deleted successfully",
            "resume_id": resume_id,
            "resume_deleted": resume_deleted,
            "s3_deleted": s3_deleted
        }
        
        if s3_error:
            response_data["s3_error"] = s3_error
        
        return response_data
    
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB not configured: {str(e)}"
        )
    except ConnectionFailure as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting resume: {str(e)}"
        )


@app.get("/user-profiles")
async def get_user_profiles(limit: int = 100):
    """
    Get all user profiles from MongoDB.
    
    Args:
        limit: Maximum number of profiles to return (default: 100)
        
    Returns:
        JSON response with list of user profiles
    """
    try:
        from database import get_all_user_profiles
        
        profiles = get_all_user_profiles(limit=limit)
        
        return {
            "status": "success",
            "count": len(profiles),
            "profiles": profiles
        }
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB not configured: {str(e)}"
        )
    except ConnectionFailure as e:
        raise HTTPException(
            status_code=500,
            detail=f"MongoDB connection failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving profiles: {str(e)}"
        )


@app.get("/user-profiles/{email}")
async def get_user_profile_by_email(email: str):
    """
    Get user profile by email address.
    Returns the most recent resume document for that email.
    
    Args:
        email: Email address of the user
        
    Returns:
        JSON response with user profile (includes resume metadata)
    """
    try:
        from database import get_user_profile_by_email
        
        profile = get_user_profile_by_email(email)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        return {
            "status": "success",
            "profile": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving profile: {str(e)}"
        )


@app.get("/user-profiles/{email}/resumes")
async def get_user_resumes_by_email(email: str):
    """
    Get all resumes for a specific email address.
    
    Args:
        email: Email address of the user
        
    Returns:
        JSON response with list of resumes for that user
    """
    try:
        from database import get_resumes_by_email
        
        resumes = get_resumes_by_email(email)
        
        return {
            "status": "success",
            "count": len(resumes),
            "resumes": resumes
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving resumes: {str(e)}"
        )


@app.get("/resumes/id/{resume_id}")
async def get_resume_by_id_endpoint(resume_id: str):
    """
    Get resume by MongoDB document ID.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        JSON response with resume (includes profile data if available)
    """
    try:
        from database import get_resume_by_id
        
        resume = get_resume_by_id(resume_id)
        
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        return {
            "status": "success",
            "resume": resume
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving resume: {str(e)}"
        )


@app.put("/resumes/{resume_id}/profile")
async def update_resume_profile_endpoint(resume_id: str, profile_data: Dict[str, Any] = Body(...)):
    """
    Update profile data for a resume.
    
    Args:
        resume_id: MongoDB document ID
        profile_data: Dictionary containing profile fields to update
        
    Returns:
        JSON response with update status
    """
    try:
        from database import update_resume_profile, get_resume_by_id
        
        # Check if resume exists
        resume = get_resume_by_id(resume_id)
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        
        # Update profile data
        updated = update_resume_profile(resume_id, profile_data)
        
        if updated:
            # Get updated resume
            updated_resume = get_resume_by_id(resume_id)
            return {
                "status": "success",
                "message": "Profile updated successfully",
                "resume_id": resume_id,
                "resume": updated_resume
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No valid fields to update"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating profile: {str(e)}"
        )


@app.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Upload a PDF resume to S3 bucket.
    
    Args:
        file: PDF file to upload
        
    Returns:
        JSON response with upload status and file URL
    """
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    # Validate file extension
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="File must have .pdf extension"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        s3_key = f"resumes/{unique_filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType='application/pdf',
            Metadata={
                'original-filename': file.filename
            }
        )
        
        # Generate S3 URL
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{os.getenv('AWS_REGION', 'us-east-1')}.amazonaws.com/{s3_key}"
        
        # Prepare resume data
        resume_data = {
            "filename": unique_filename,
            "original_filename": file.filename,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "file_size": len(file_content)
        }
        
        # Parse resume and get profile data
        parsed_data = None
        try:
            parser = ResumeParser()
            parsed_data = parser.parse(file_content)
            print(f"Resume parsed successfully for: {parsed_data.get('name', 'Unknown')}")
        except ValueError as e:
            # Log error but don't fail the request if parsing fails
            print(f"Warning: Failed to parse resume: {e}")
        except Exception as e:
            # Log any other parsing errors
            print(f"Warning: Unexpected error during resume parsing: {e}")
        
        # Save resume with integrated profile data to MongoDB
        mongodb_id = None
        try:
            mongodb_id = save_resume_with_profile(resume_data, parsed_data)
            print(f"Resume and profile saved to MongoDB: {mongodb_id}")
        except (ConnectionFailure, OperationFailure, ValueError) as e:
            # Log error but don't fail the request if MongoDB fails
            print(f"Warning: Failed to save to MongoDB: {e}")
        
        response_data = {
            "message": "Resume uploaded successfully",
            "filename": unique_filename,
            "original_filename": file.filename,
            "s3_key": s3_key,
            "s3_url": s3_url,
            "file_size": len(file_content)
        }
        
        if mongodb_id:
            response_data["mongodb_id"] = mongodb_id
        
        # Include parsed data summary (not full raw text)
        if parsed_data:
            response_data["parsed_data"] = {
                "name": parsed_data.get("name"),
                "email": parsed_data.get("email"),
                "phone": parsed_data.get("phone"),
                "skills_count": len(parsed_data.get("skills", [])),
                "experience_count": len(parsed_data.get("experience", [])),
                "education_count": len(parsed_data.get("education", []))
            }
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
    
    except ClientError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AWS S3 error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )
    
    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

