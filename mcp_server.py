#!/usr/bin/env python3
"""
MongoDB MCP Server for Auto Apply
Exposes user profile data to Claude via MCP (Model Context Protocol)
"""

import asyncio
import json
from typing import Any
from datetime import datetime

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

# Import database functions
from database import (
    get_collection,
    get_all_resumes,
    get_resume_by_id,
    get_mongodb_client,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create MCP server instance
server = Server("autoapply-profile-db")


def serialize_document(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable format."""
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["id"] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [
                serialize_document(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[key] = serialize_document(value)
        else:
            result[key] = value
    return result


# ============== TOOLS ==============

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="get_all_profiles",
            description="Get all user profiles from the database. Returns a list of all profiles with their resume data, skills, experience, education, and contact information.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_profile_by_email",
            description="Get a specific user profile by email address. Returns full profile including name, contact info, skills, experience, education, projects, certifications, and resume URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_profile_by_id",
            description="Get a specific user profile by MongoDB document ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "profile_id": {
                        "type": "string",
                        "description": "MongoDB document ID"
                    }
                },
                "required": ["profile_id"]
            }
        ),
        Tool(
            name="get_resume_url",
            description="Get the S3 URL for a user's resume by email. Use this to get the downloadable resume file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_user_skills",
            description="Get the list of skills for a user by email. Returns technical skills, soft skills, tools, and technologies.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_user_experience",
            description="Get work experience for a user by email. Returns job titles, companies, dates, descriptions, and achievements.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_user_education",
            description="Get education history for a user by email. Returns degrees, institutions, graduation dates, GPA, and coursework.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_user_projects",
            description="Get projects for a user by email. Returns project names, descriptions, technologies used, and URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="get_contact_info",
            description="Get contact information for a user by email. Returns name, email, phone, location, LinkedIn, GitHub, and portfolio URLs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
        Tool(
            name="search_profiles",
            description="Search profiles by skill, company, or keyword. Returns matching profiles.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (skill name, company name, or keyword)"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_profile_emails",
            description="List all profile email addresses in the database. Useful to see available profiles.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_application_summary",
            description="Get a summary of user's profile formatted for job applications. Includes key highlights, top skills, recent experience, and education.",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "Email address of the user"
                    }
                },
                "required": ["email"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        collection = get_collection()
        
        if name == "get_all_profiles":
            profiles = list(collection.find({}))
            serialized = [serialize_document(p) for p in profiles]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": len(serialized),
                    "profiles": serialized
                }, indent=2)
            )]
        
        elif name == "get_profile_by_email":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email})
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps(serialize_document(profile), indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "get_profile_by_id":
            from bson import ObjectId
            profile_id = arguments.get("profile_id")
            if not profile_id:
                return [TextContent(type="text", text="Error: profile_id is required")]
            
            try:
                profile = collection.find_one({"_id": ObjectId(profile_id)})
            except:
                profile = collection.find_one({"_id": profile_id})
            
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps(serialize_document(profile), indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for ID: {profile_id}")]
        
        elif name == "get_resume_url":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email}, {"s3_url": 1, "s3_key": 1, "original_filename": 1})
            if profile and profile.get("s3_url"):
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "s3_url": profile.get("s3_url"),
                        "s3_key": profile.get("s3_key"),
                        "filename": profile.get("original_filename")
                    }, indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No resume found for email: {email}")]
        
        elif name == "get_user_skills":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email}, {"skills": 1, "name": 1})
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "name": profile.get("name"),
                        "skills": profile.get("skills", [])
                    }, indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "get_user_experience":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email}, {"experience": 1, "name": 1})
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "name": profile.get("name"),
                        "experience": profile.get("experience", [])
                    }, indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "get_user_education":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email}, {"education": 1, "name": 1})
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "name": profile.get("name"),
                        "education": profile.get("education", [])
                    }, indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "get_user_projects":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email}, {"projects": 1, "name": 1})
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "name": profile.get("name"),
                        "projects": profile.get("projects", [])
                    }, indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "get_contact_info":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one(
                {"email": email}, 
                {"name": 1, "email": 1, "phone": 1, "location": 1, "linkedin": 1, "github": 1, "portfolio": 1}
            )
            if profile:
                return [TextContent(
                    type="text",
                    text=json.dumps(serialize_document(profile), indent=2)
                )]
            else:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
        
        elif name == "search_profiles":
            query = arguments.get("query", "")
            if not query:
                return [TextContent(type="text", text="Error: query is required")]
            
            # Search in skills, experience companies, and name
            search_filter = {
                "$or": [
                    {"skills": {"$regex": query, "$options": "i"}},
                    {"experience.company": {"$regex": query, "$options": "i"}},
                    {"experience.title": {"$regex": query, "$options": "i"}},
                    {"name": {"$regex": query, "$options": "i"}},
                    {"summary": {"$regex": query, "$options": "i"}}
                ]
            }
            
            profiles = list(collection.find(search_filter, {"name": 1, "email": 1, "skills": 1}))
            serialized = [serialize_document(p) for p in profiles]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "count": len(serialized),
                    "results": serialized
                }, indent=2)
            )]
        
        elif name == "list_profile_emails":
            profiles = list(collection.find({}, {"name": 1, "email": 1}))
            result = [{"name": p.get("name"), "email": p.get("email")} for p in profiles if p.get("email")]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "count": len(result),
                    "profiles": result
                }, indent=2)
            )]
        
        elif name == "get_application_summary":
            email = arguments.get("email")
            if not email:
                return [TextContent(type="text", text="Error: email is required")]
            
            profile = collection.find_one({"email": email})
            if not profile:
                return [TextContent(type="text", text=f"No profile found for email: {email}")]
            
            # Build application summary
            summary = {
                "personal_info": {
                    "name": profile.get("name"),
                    "email": profile.get("email"),
                    "phone": profile.get("phone"),
                    "location": profile.get("location"),
                    "linkedin": profile.get("linkedin"),
                    "github": profile.get("github"),
                    "portfolio": profile.get("portfolio")
                },
                "professional_summary": profile.get("summary"),
                "top_skills": profile.get("skills", [])[:15],  # Top 15 skills
                "total_skills_count": len(profile.get("skills", [])),
                "recent_experience": profile.get("experience", [])[:3],  # Last 3 positions
                "total_experience_count": len(profile.get("experience", [])),
                "education": profile.get("education", []),
                "certifications": profile.get("certifications", []),
                "languages": profile.get("languages", []),
                "resume_url": profile.get("s3_url")
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(summary, indent=2)
            )]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error executing tool {name}: {str(e)}")]


# ============== RESOURCES ==============

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    try:
        collection = get_collection()
        profiles = list(collection.find({}, {"name": 1, "email": 1}))
        
        resources = []
        for profile in profiles:
            if profile.get("email"):
                resources.append(Resource(
                    uri=f"profile://{profile.get('email')}",
                    name=f"Profile: {profile.get('name', 'Unknown')}",
                    description=f"User profile for {profile.get('name', profile.get('email'))}",
                    mimeType="application/json"
                ))
        
        return resources
    except Exception as e:
        return []


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a specific resource."""
    try:
        if uri.startswith("profile://"):
            email = uri.replace("profile://", "")
            collection = get_collection()
            profile = collection.find_one({"email": email})
            
            if profile:
                return json.dumps(serialize_document(profile), indent=2)
            else:
                return json.dumps({"error": f"Profile not found: {email}"})
        
        return json.dumps({"error": f"Unknown resource URI: {uri}"})
    
    except Exception as e:
        return json.dumps({"error": str(e)})


# ============== MAIN ==============

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

