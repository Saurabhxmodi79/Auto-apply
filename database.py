from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, InvalidURI
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import quote_plus, urlparse, urlunparse

# Load environment variables
load_dotenv()

# MongoDB connection string
MONGODB_URI = os.getenv('MONGODB_URI')
DATABASE_NAME = os.getenv('MONGODB_DATABASE_NAME', 'resume_upload_db')
COLLECTION_NAME = os.getenv('MONGODB_COLLECTION_NAME', 'resumes')

# Initialize MongoDB client
_client: Optional[MongoClient] = None
_db = None
_collection = None


def _encode_mongodb_uri(uri: str) -> str:
    """
    Encode username and password in MongoDB URI according to RFC 3986.
    
    Args:
        uri: MongoDB connection string
        
    Returns:
        Encoded MongoDB URI
    """
    try:
        # Check if URI contains credentials (has @ symbol after scheme)
        if '@' not in uri:
            return uri
        
        # Parse the URI - handle mongodb:// and mongodb+srv:// schemes
        parsed = urlparse(uri)
        
        # If there's userinfo (username:password), encode it
        if parsed.username or parsed.password:
            username = quote_plus(parsed.username) if parsed.username else ''
            password = quote_plus(parsed.password) if parsed.password else ''
            userinfo = f"{username}:{password}" if password else username
            
            # Build netloc with encoded credentials
            netloc_parts = [userinfo]
            if parsed.hostname:
                netloc_parts.append('@')
                netloc_parts.append(parsed.hostname)
            if parsed.port:
                netloc_parts.append(f':{parsed.port}')
            
            netloc = ''.join(netloc_parts)
            
            # Reconstruct URI with encoded credentials
            encoded_uri = urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            return encoded_uri
        
        return uri
    except Exception as e:
        # If parsing fails, try to encode manually
        try:
            # Simple fallback: find username:password@ and encode
            if '@' in uri:
                parts = uri.split('@', 1)
                if len(parts) == 2:
                    creds_part = parts[0]
                    rest = parts[1]
                    # Find the last : before @ (password separator)
                    if '://' in creds_part:
                        scheme_part = creds_part.split('://')[0] + '://'
                        creds = creds_part.split('://')[1]
                        if ':' in creds:
                            username, password = creds.rsplit(':', 1)
                            encoded_creds = f"{quote_plus(username)}:{quote_plus(password)}"
                            return f"{scheme_part}{encoded_creds}@{rest}"
            return uri
        except Exception:
            # Last resort: return original URI
            return uri


def get_mongodb_client() -> MongoClient:
    """
    Get or create MongoDB client instance.
    
    Returns:
        MongoClient instance
        
    Raises:
        ValueError: If MONGODB_URI is not set
        ConnectionFailure: If connection to MongoDB fails
    """
    global _client
    
    if not MONGODB_URI:
        raise ValueError("MONGODB_URI environment variable is required")
    
    if _client is None:
        try:
            # Encode the URI to handle special characters in username/password
            encoded_uri = _encode_mongodb_uri(MONGODB_URI)
            _client = MongoClient(encoded_uri, serverSelectionTimeoutMS=5000)
            # Test connection
            _client.admin.command('ping')
        except InvalidURI as e:
            raise ValueError(f"Invalid MongoDB URI: {str(e)}")
        except ConnectionFailure as e:
            raise ConnectionFailure(f"Failed to connect to MongoDB: {str(e)}")
    
    return _client


def get_database():
    """
    Get database instance.
    
    Returns:
        Database instance
    """
    global _db
    
    if _db is None:
        client = get_mongodb_client()
        _db = client[DATABASE_NAME]
    
    return _db


def get_collection():
    """
    Get collection instance.
    
    Returns:
        Collection instance
    """
    global _collection
    
    if _collection is None:
        db = get_database()
        _collection = db[COLLECTION_NAME]
    
    return _collection


def save_resume_with_profile(resume_data: Dict[str, Any], profile_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Save resume with integrated user profile data in a single document.
    If profile_data is provided and email exists, merges with existing profile.
    
    Args:
        resume_data: Dictionary containing resume metadata:
            - filename: Unique filename
            - original_filename: Original filename
            - s3_key: S3 object key
            - s3_url: S3 URL
            - file_size: File size in bytes
        profile_data: Dictionary containing parsed resume data (optional)
        
    Returns:
        MongoDB document ID as string
        
    Raises:
        OperationFailure: If MongoDB operation fails
    """
    try:
        collection = get_collection()
        
        # Prepare base document with resume metadata
        document = {
            "filename": resume_data.get("filename"),
            "original_filename": resume_data.get("original_filename"),
            "s3_key": resume_data.get("s3_key"),
            "s3_url": resume_data.get("s3_url"),
            "file_size": resume_data.get("file_size"),
            "uploaded_at": resume_data.get("uploaded_at", datetime.utcnow()),
            "status": "uploaded"
        }
        
        # Add profile data if provided
        if profile_data:
            # Extract email for deduplication
            email = profile_data.get("email")
            
            if email:
                # Check if profile with this email already exists
                existing_doc = collection.find_one({"email": email})
                
                if existing_doc:
                    # Merge profile data intelligently
                    # Keep resume-specific fields separate, merge profile fields
                    merged_profile = existing_doc.copy()
                    
                    # Merge skills
                    existing_skills = merged_profile.get("skills", [])
                    new_skills = profile_data.get("skills", [])
                    if isinstance(existing_skills, list) and isinstance(new_skills, list):
                        merged_profile["skills"] = list(set(existing_skills + new_skills))
                    
                    # Merge experience (deduplicate by company+title)
                    existing_experience = merged_profile.get("experience", [])
                    new_experience = profile_data.get("experience", [])
                    if isinstance(existing_experience, list) and isinstance(new_experience, list):
                        combined = existing_experience.copy()
                        for exp in new_experience:
                            if isinstance(exp, dict):
                                exists = any(
                                    e.get("company") == exp.get("company") and 
                                    e.get("title") == exp.get("title")
                                    for e in combined if isinstance(e, dict)
                                )
                                if not exists:
                                    combined.append(exp)
                        merged_profile["experience"] = combined
                    
                    # Update profile fields with latest data - include all possible fields
                    fields_to_update = [
                        "name", "phone", "location", "linkedin", "github", "portfolio", "summary",
                        "languages", "education", "experience", "projects", "certifications", 
                        "awards", "publications", "volunteer_work", "leadership", "hobbies", 
                        "memberships", "patents", "conferences", "references", "skills"
                    ]
                    for key in fields_to_update:
                        if key in profile_data:
                            merged_profile[key] = profile_data[key]
                    
                    # Update timestamps
                    merged_profile["updated_at"] = datetime.utcnow()
                    merged_profile["parsed_at"] = profile_data.get("parsed_at", datetime.utcnow())
                    
                    # Add resume metadata to the merged profile
                    merged_profile.update(document)
                    
                    # Update the existing document
                    collection.update_one(
                        {"email": email},
                        {"$set": merged_profile}
                    )
                    
                    # Return the existing document ID
                    return str(existing_doc["_id"])
            
            # No email or new email - add profile data to document
            for key, value in profile_data.items():
                if value is not None:
                    document[key] = value
            
            document["created_at"] = datetime.utcnow()
            document["updated_at"] = datetime.utcnow()
        else:
            # No profile data - just resume metadata
            document["created_at"] = datetime.utcnow()
        
        # Insert new document
        result = collection.insert_one(document)
        return str(result.inserted_id)
    
    except OperationFailure as e:
        raise OperationFailure(f"MongoDB operation failed: {str(e)}")


def get_resume_by_id(resume_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a resume record by MongoDB document ID.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        Resume document with profile data or None if not found
    """
    try:
        from bson import ObjectId
        collection = get_collection()
        
        try:
            document = collection.find_one({"_id": ObjectId(resume_id)})
        except Exception:
            document = collection.find_one({"_id": resume_id})
        
        if document:
            document["_id"] = str(document["_id"])
        
        return document
    except Exception:
        return None


def get_resume_by_s3_key(s3_key: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a resume record by S3 key.
    
    Args:
        s3_key: S3 object key
        
    Returns:
        Resume document with profile data or None if not found
    """
    try:
        collection = get_collection()
        document = collection.find_one({"s3_key": s3_key})
        
        if document:
            document["_id"] = str(document["_id"])
        
        return document
    except Exception:
        return None


def get_all_resumes(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve all resume records with their profile data.
    
    Args:
        limit: Maximum number of records to return
        
    Returns:
        List of resume documents with profile data
    """
    try:
        collection = get_collection()
        cursor = collection.find().sort("uploaded_at", -1).limit(limit)
        resumes = []
        
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            resumes.append(doc)
        
        return resumes
    except Exception as e:
        raise OperationFailure(f"Failed to retrieve resumes: {str(e)}")


def get_resumes_by_email(email: str) -> List[Dict[str, Any]]:
    """
    Retrieve all resumes for a specific email address.
    
    Args:
        email: Email address
        
    Returns:
        List of resume documents
    """
    try:
        collection = get_collection()
        cursor = collection.find({"email": email}).sort("uploaded_at", -1)
        resumes = []
        
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            resumes.append(doc)
        
        return resumes
    except Exception as e:
        raise OperationFailure(f"Failed to retrieve resumes by email: {str(e)}")


def get_resume_before_delete(resume_id: str) -> Optional[Dict[str, Any]]:
    """
    Get resume data before deletion (without deleting).
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        Resume document data if found, None otherwise
    """
    try:
        from bson import ObjectId
        collection = get_collection()
        
        try:
            document = collection.find_one({"_id": ObjectId(resume_id)})
        except Exception:
            document = collection.find_one({"_id": resume_id})
        
        if document:
            document["_id"] = str(document["_id"])
            return document
        return None
    
    except Exception as e:
        print(f"Error getting resume: {e}")
        return None


def update_resume_profile(resume_id: str, profile_data: Dict[str, Any]) -> bool:
    """
    Update profile data for a resume document.
    
    Args:
        resume_id: MongoDB document ID
        profile_data: Dictionary containing profile fields to update
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        from bson import ObjectId
        collection = get_collection()
        
        # Prepare update data
        update_data = {}
        allowed_fields = [
            "name", "email", "phone", "location", "linkedin", "github", "portfolio",
            "summary", "skills", "languages", "education", "experience", "projects",
            "certifications", "awards", "publications", "volunteer_work", "leadership",
            "hobbies", "memberships", "patents", "conferences", "references"
        ]
        
        # Only include allowed fields
        for field in allowed_fields:
            if field in profile_data:
                update_data[field] = profile_data[field]
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        if not update_data:
            return False
        
        # Update the document
        try:
            result = collection.update_one(
                {"_id": ObjectId(resume_id)},
                {"$set": update_data}
            )
        except Exception:
            result = collection.update_one(
                {"_id": resume_id},
                {"$set": update_data}
            )
        
        return result.modified_count > 0
    
    except Exception as e:
        raise OperationFailure(f"Failed to update resume profile: {str(e)}")


def delete_resume(resume_id: str) -> bool:
    """
    Delete a resume record from MongoDB.
    
    Args:
        resume_id: MongoDB document ID
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        from bson import ObjectId
        collection = get_collection()
        
        try:
            result = collection.delete_one({"_id": ObjectId(resume_id)})
        except Exception:
            result = collection.delete_one({"_id": resume_id})
        
        return result.deleted_count > 0
    
    except Exception as e:
        raise OperationFailure(f"Failed to delete resume: {str(e)}")


def get_user_profile_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve user profile by email address.
    Returns the most recent resume document for that email.
    
    Args:
        email: Email address
        
    Returns:
        User profile document or None if not found
    """
    try:
        collection = get_collection()
        # Get the most recent resume for this email
        document = collection.find_one(
            {"email": email},
            sort=[("uploaded_at", -1)]
        )
        
        if document:
            document["_id"] = str(document["_id"])
        
        return document
    except Exception:
        return None


def get_all_user_profiles(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieve all unique user profiles (one per email).
    Returns the most recent resume for each email.
    
    Args:
        limit: Maximum number of profiles to return
        
    Returns:
        List of user profile documents
    """
    try:
        collection = get_collection()
        
        # Use aggregation to get one document per email (most recent)
        pipeline = [
            {"$sort": {"uploaded_at": -1}},
            {"$group": {
                "_id": "$email",
                "doc": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$doc"}},
            {"$limit": limit}
        ]
        
        profiles = []
        for doc in collection.aggregate(pipeline):
            doc["_id"] = str(doc["_id"])
            profiles.append(doc)
        
        return profiles
    except Exception as e:
        raise OperationFailure(f"Failed to retrieve profiles: {str(e)}")


def close_connection():
    """
    Close MongoDB connection.
    """
    global _client, _db, _collection
    
    if _client:
        _client.close()
        _client = None
        _db = None
        _collection = None
