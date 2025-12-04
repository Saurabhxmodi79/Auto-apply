import streamlit as st
import requests
from datetime import datetime
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Auto Apply",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .resume-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        background-color: #f9f9f9;
    }
    .resume-card:hover {
        background-color: #f0f0f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button {
        width: 100%;
    }
    .delete-button {
        background-color: #ff4444;
        color: white;
    }
    .delete-button:hover {
        background-color: #cc0000;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for API URL
if 'api_url' not in st.session_state:
    st.session_state.api_url = "http://localhost:8000"

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input(
        "API URL",
        value=st.session_state.api_url,
        help="URL of your FastAPI backend server",
        key="api_url_input"
    )
    st.session_state.api_url = api_url
    
    st.markdown("---")
    st.markdown("### 📋 Navigation")
    
    # Initialize page in session state
    if 'page' not in st.session_state:
        st.session_state.page = "🏠 Home"
    
    # Page selection - controlled by session state
    # Don't capture the return value to avoid conflicts with button navigation
    st.radio(
        "Select Page",
        ["🏠 Home", "📤 Upload Resume"],
        index=0 if st.session_state.page == "🏠 Home" else 1,
        label_visibility="collapsed",
        key="nav_radio",
        on_change=lambda: st.session_state.update(page=st.session_state.nav_radio)
    )
    
def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def format_date(date_str):
    """Format date string"""
    try:
        if isinstance(date_str, str):
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        else:
            dt = date_str
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return str(date_str)


def display_homepage():
    """Display homepage with list of resumes"""
    st.markdown('<h1 class="main-header">📄 Auto Apply</h1>', unsafe_allow_html=True)
    st.markdown("### 🏠 Home - Uploaded Resumes")
    
    # Fetch resumes from API
    try:
        with st.spinner("Loading resumes..."):
            response = requests.get(
                f"{st.session_state.api_url}/resumes",
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            resumes = data.get("resumes", [])
            count = data.get("count", 0)
            
            if count == 0:
                st.info("📭 No resumes uploaded yet. Go to the Upload page to upload your first resume!")
                st.markdown("---")
                if st.button("📤 Go to Upload Page", use_container_width=True):
                    st.session_state.page = "📤 Upload Resume"
                    st.rerun()
            else:
                st.success(f"✅ Found {count} resume(s)")
                st.info("ℹ️ **Note:** Deleting a resume removes it from the database, S3 bucket, and associated user profile.")
                st.markdown("---")
                
                # Display resumes
                for idx, resume in enumerate(resumes):
                    resume_id = resume.get('_id')
                    original_filename = resume.get('original_filename', 'Unknown')
                    
                    # Initialize delete confirmation state for this resume
                    delete_key = f"delete_confirm_{resume_id}"
                    if delete_key not in st.session_state:
                        st.session_state[delete_key] = False
                    
                    # Profile data is now integrated in the resume document
                    # Always show edit option - even if profile is empty, user can add data
                    has_profile = resume.get('email') is not None or resume.get('name') is not None
                    
                    with st.container():
                        # Resume header row
                        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**📄 {original_filename}**")
                            st.caption(f"Stored as: {resume.get('filename', 'N/A')}")
                            
                            # Display upload date if available
                            uploaded_at = resume.get('uploaded_at')
                            if uploaded_at:
                                formatted_date = format_date(uploaded_at)
                                st.caption(f"📅 Uploaded: {formatted_date}")
                            
                            # Show user profile name if available (now integrated)
                            if has_profile:
                                profile_name = resume.get('name', '')
                                profile_email = resume.get('email', '')
                                if profile_name:
                                    st.markdown(f"**👤 {profile_name}**")
                                if profile_email:
                                    st.caption(f"📧 {profile_email}")
                        
                        with col2:
                            file_size = resume.get('file_size', 0)
                            st.metric("Size", format_file_size(file_size))
                            
                            # Show profile stats if available (now integrated)
                            if has_profile:
                                skills_count = len(resume.get('skills', []))
                                st.metric("Skills", skills_count)
                        
                        with col3:
                            s3_url = resume.get('s3_url', '')
                            if s3_url:
                                st.markdown(f"[🔗 View PDF]({s3_url})")
                            else:
                                st.caption("No URL available")
                            
                            # Show profile links if available (now integrated)
                            if has_profile:
                                linkedin = resume.get('linkedin', '')
                                github = resume.get('github', '')
                                if linkedin:
                                    st.markdown(f"[💼 LinkedIn]({linkedin})")
                                if github:
                                    st.markdown(f"[💻 GitHub]({github})")
                        
                        with col4:
                            # Delete button with confirmation
                            if st.session_state[delete_key]:
                                # Show confirmation
                                st.warning("⚠️ Confirm deletion?")
                                col_yes, col_no = st.columns(2)
                                with col_yes:
                                    if st.button("✅ Yes", key=f"confirm_yes_{resume_id}", use_container_width=True):
                                        try:
                                            # Delete resume from MongoDB, S3, and profile
                                            delete_response = requests.delete(
                                                f"{st.session_state.api_url}/resumes/{resume_id}",
                                                timeout=30
                                            )
                                            
                                            if delete_response.status_code == 200:
                                                delete_result = delete_response.json()
                                                st.success("✅ Resume deleted successfully!")
                                                
                                                # Show detailed results
                                                if delete_result.get('resume_deleted'):
                                                    st.info("📄 Deleted from MongoDB (includes profile data)")
                                                if delete_result.get('s3_deleted'):
                                                    st.info("🗑️ Deleted from S3 bucket")
                                                
                                                # Show any errors
                                                if delete_result.get('s3_error'):
                                                    st.warning(f"⚠️ S3 deletion warning: {delete_result.get('s3_error')}")
                                                
                                                # Reset confirmation state
                                                st.session_state[delete_key] = False
                                                # Refresh the page after a short delay
                                                st.rerun()
                                            elif delete_response.status_code == 404:
                                                # Resume not found, but might still clean up profile/S3
                                                try:
                                                    delete_result = delete_response.json()
                                                    if delete_result.get('status') == 'partial_success':
                                                        st.warning("⚠️ Resume not found in MongoDB, but cleanup attempted")
                                                        if delete_result.get('s3_deleted'):
                                                            st.info("🗑️ Deleted from S3")
                                                        if delete_result.get('profile_deleted') or delete_result.get('profile_updated'):
                                                            st.info("👤 Profile cleaned up")
                                                        st.session_state[delete_key] = False
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ Resume not found: {delete_result.get('detail', 'Unknown error')}")
                                                except:
                                                    st.error("❌ Resume not found")
                                            else:
                                                error_detail = "Unknown error"
                                                try:
                                                    error_response = delete_response.json()
                                                    error_detail = error_response.get("detail", str(delete_response.text))
                                                except:
                                                    error_detail = delete_response.text
                                                st.error(f"❌ Failed to delete: {error_detail}")
                                                st.session_state[delete_key] = False
                                        except requests.exceptions.ConnectionError:
                                            st.error("❌ Connection Error: Could not connect to the API server.")
                                            st.session_state[delete_key] = False
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                                            st.session_state[delete_key] = False
                                
                                with col_no:
                                    if st.button("❌ Cancel", key=f"confirm_no_{resume_id}", use_container_width=True):
                                        st.session_state[delete_key] = False
                                        st.rerun()
                            else:
                                if st.button("🗑️ Delete", key=f"delete_{resume_id}", use_container_width=True):
                                    st.session_state[delete_key] = True
                                    st.rerun()
                        
                        # Expandable details section
                        expander_label = "View Details"
                        if has_profile:
                            expander_label = f"View Details & Profile: {resume.get('name', 'Profile')}"
                        
                        with st.expander(expander_label, expanded=False):
                            # Resume details
                            st.markdown("#### 📄 Resume Information")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.text(f"**MongoDB ID:**\n{resume_id}")
                                st.text(f"**S3 Key:**\n{resume.get('s3_key', 'N/A')}")
                            with col_b:
                                st.text(f"**Status:**\n{resume.get('status', 'N/A')}")
                                if s3_url:
                                    st.text(f"**S3 URL:**\n{s3_url}")
                            
                            # User Profile section - always show edit option
                            st.markdown("---")
                            
                            # Edit mode toggle
                            edit_key = f"edit_mode_{resume_id}"
                            if edit_key not in st.session_state:
                                st.session_state[edit_key] = False
                            
                            col_header, col_edit = st.columns([3, 1])
                            with col_header:
                                if has_profile:
                                    st.markdown("#### 👤 User Profile")
                                else:
                                    st.markdown("#### 👤 User Profile")
                                    st.caption("No profile data found. Click Edit to add information.")
                            with col_edit:
                                if st.button("✏️ Edit" if not st.session_state[edit_key] else "👁️ View", 
                                           key=f"toggle_edit_{resume_id}", use_container_width=True):
                                    st.session_state[edit_key] = not st.session_state[edit_key]
                                    st.rerun()
                            
                            if st.session_state[edit_key]:
                                # EDIT MODE - Form fields
                                # Initialize session state for entry counts
                                exp_count_key = f"exp_count_{resume_id}"
                                edu_count_key = f"edu_count_{resume_id}"
                                proj_count_key = f"proj_count_{resume_id}"
                                cert_count_key = f"cert_count_{resume_id}"
                                award_count_key = f"award_count_{resume_id}"
                                pub_count_key = f"pub_count_{resume_id}"
                                vol_count_key = f"vol_count_{resume_id}"
                                lead_count_key = f"lead_count_{resume_id}"
                                
                                # Initialize counts if not set
                                if exp_count_key not in st.session_state:
                                    st.session_state[exp_count_key] = max(len(resume.get('experience', [])), 1)
                                if edu_count_key not in st.session_state:
                                    st.session_state[edu_count_key] = max(len(resume.get('education', [])), 1)
                                if proj_count_key not in st.session_state:
                                    st.session_state[proj_count_key] = max(len(resume.get('projects', [])), 1)
                                if cert_count_key not in st.session_state:
                                    st.session_state[cert_count_key] = max(len(resume.get('certifications', [])), 1)
                                if award_count_key not in st.session_state:
                                    st.session_state[award_count_key] = max(len(resume.get('awards', [])), 1)
                                if pub_count_key not in st.session_state:
                                    st.session_state[pub_count_key] = max(len(resume.get('publications', [])), 1)
                                if vol_count_key not in st.session_state:
                                    st.session_state[vol_count_key] = max(len(resume.get('volunteer_work', [])), 1)
                                if lead_count_key not in st.session_state:
                                    st.session_state[lead_count_key] = max(len(resume.get('leadership', [])), 1)
                                
                                # Add buttons outside form
                                col_add1, col_add2, col_add3, col_add4 = st.columns(4)
                                with col_add1:
                                    if st.button("➕ Add Experience", key=f"add_exp_{resume_id}"):
                                        st.session_state[exp_count_key] += 1
                                        st.rerun()
                                with col_add2:
                                    if st.button("➕ Add Education", key=f"add_edu_{resume_id}"):
                                        st.session_state[edu_count_key] += 1
                                        st.rerun()
                                with col_add3:
                                    if st.button("➕ Add Project", key=f"add_proj_{resume_id}"):
                                        st.session_state[proj_count_key] += 1
                                        st.rerun()
                                with col_add4:
                                    if st.button("➕ Add Certification", key=f"add_cert_{resume_id}"):
                                        st.session_state[cert_count_key] += 1
                                        st.rerun()
                                
                                col_add5, col_add6, col_add7, col_add8 = st.columns(4)
                                with col_add5:
                                    if st.button("➕ Add Award", key=f"add_award_{resume_id}"):
                                        st.session_state[award_count_key] += 1
                                        st.rerun()
                                with col_add6:
                                    if st.button("➕ Add Publication", key=f"add_pub_{resume_id}"):
                                        st.session_state[pub_count_key] += 1
                                        st.rerun()
                                with col_add7:
                                    if st.button("➕ Add Volunteer", key=f"add_vol_{resume_id}"):
                                        st.session_state[vol_count_key] += 1
                                        st.rerun()
                                with col_add8:
                                    if st.button("➕ Add Leadership", key=f"add_lead_{resume_id}"):
                                        st.session_state[lead_count_key] += 1
                                        st.rerun()
                                
                                with st.form(key=f"edit_form_{resume_id}"):
                                        st.markdown("##### Personal Information")
                                        col_p1, col_p2 = st.columns(2)
                                        
                                        with col_p1:
                                            edit_name = st.text_input("Name", value=resume.get('name', ''), key=f"name_{resume_id}")
                                            edit_email = st.text_input("Email", value=resume.get('email', ''), key=f"email_{resume_id}")
                                            edit_phone = st.text_input("Phone", value=resume.get('phone', ''), key=f"phone_{resume_id}")
                                            edit_location = st.text_input("Location", value=resume.get('location', ''), key=f"location_{resume_id}")
                                        
                                        with col_p2:
                                            edit_linkedin = st.text_input("LinkedIn URL", value=resume.get('linkedin', ''), key=f"linkedin_{resume_id}")
                                            edit_github = st.text_input("GitHub URL", value=resume.get('github', ''), key=f"github_{resume_id}")
                                            edit_portfolio = st.text_input("Portfolio URL", value=resume.get('portfolio', ''), key=f"portfolio_{resume_id}")
                                        
                                        st.markdown("##### Summary")
                                        edit_summary = st.text_area("Professional Summary", value=resume.get('summary', ''), 
                                                                   height=100, key=f"summary_{resume_id}")
                                        
                                        st.markdown("##### Skills")
                                        skills_list = resume.get('skills', [])
                                        skills_text = ", ".join(skills_list) if skills_list else ""
                                        edit_skills = st.text_area("Skills (comma-separated)", value=skills_text, 
                                                                   height=80, key=f"skills_{resume_id}",
                                                                   help="Enter skills separated by commas")
                                        
                                        st.markdown("##### Languages")
                                        languages_list = resume.get('languages', [])
                                        languages_text = ", ".join(languages_list) if languages_list else ""
                                        edit_languages = st.text_input("Languages (comma-separated)", value=languages_text, 
                                                                       key=f"languages_{resume_id}")
                                        
                                        # Experience
                                        st.markdown("##### Work Experience")
                                        experience = resume.get('experience', [])
                                        exp_count = st.session_state[exp_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(experience) < exp_count:
                                            experience.append({})
                                        
                                        for i in range(exp_count):
                                            exp = experience[i] if i < len(experience) else {}
                                            with st.expander(f"Experience {i+1}", expanded=i==0):
                                                exp_title = st.text_input("Title", value=exp.get('title', ''), key=f"exp_title_{resume_id}_{i}")
                                                exp_company = st.text_input("Company", value=exp.get('company', ''), key=f"exp_company_{resume_id}_{i}")
                                                exp_start = st.text_input("Start Date", value=exp.get('start_date', ''), key=f"exp_start_{resume_id}_{i}")
                                                exp_end = st.text_input("End Date", value=exp.get('end_date', ''), key=f"exp_end_{resume_id}_{i}")
                                                exp_desc = st.text_area("Description", value=exp.get('description', ''), 
                                                                        height=60, key=f"exp_desc_{resume_id}_{i}")
                                        
                                        # Education
                                        st.markdown("##### Education")
                                        education = resume.get('education', [])
                                        edu_count = st.session_state[edu_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(education) < edu_count:
                                            education.append({})
                                        
                                        for i in range(edu_count):
                                            edu = education[i] if i < len(education) else {}
                                            with st.expander(f"Education {i+1}", expanded=i==0):
                                                edu_degree = st.text_input("Degree", value=edu.get('degree', ''), key=f"edu_degree_{resume_id}_{i}")
                                                edu_institution = st.text_input("Institution", value=edu.get('institution', ''), key=f"edu_institution_{resume_id}_{i}")
                                                edu_field = st.text_input("Field of Study", value=edu.get('field', ''), key=f"edu_field_{resume_id}_{i}")
                                                edu_year = st.text_input("Year", value=edu.get('year', ''), key=f"edu_year_{resume_id}_{i}")
                                                edu_cgpa = st.text_input("CGPA/GPA", value=edu.get('gpa', '') or edu.get('cgpa', ''), key=f"edu_cgpa_{resume_id}_{i}")
                                        
                                        # Projects
                                        st.markdown("##### Projects")
                                        projects = resume.get('projects', [])
                                        proj_count = st.session_state[proj_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(projects) < proj_count:
                                            projects.append({})
                                        
                                        for i in range(proj_count):
                                            proj = projects[i] if i < len(projects) else {}
                                            with st.expander(f"Project {i+1}", expanded=i==0):
                                                proj_name = st.text_input("Project Name", value=proj.get('name', ''), key=f"proj_name_{resume_id}_{i}")
                                                proj_desc = st.text_area("Description", value=proj.get('description', ''), 
                                                                         height=60, key=f"proj_desc_{resume_id}_{i}")
                                                proj_url = st.text_input("URL", value=proj.get('url', ''), key=f"proj_url_{resume_id}_{i}")
                                        
                                        # Certifications
                                        st.markdown("##### Certifications")
                                        certifications = resume.get('certifications', [])
                                        cert_count = st.session_state[cert_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(certifications) < cert_count:
                                            certifications.append({})
                                        
                                        for i in range(cert_count):
                                            cert = certifications[i] if i < len(certifications) else {}
                                            with st.expander(f"Certification {i+1}", expanded=i==0):
                                                cert_name = st.text_input("Certification Name", value=cert.get('name', ''), key=f"cert_name_{resume_id}_{i}")
                                                cert_org = st.text_input("Issuing Organization", value=cert.get('organization', ''), key=f"cert_org_{resume_id}_{i}")
                                                cert_date = st.text_input("Date", value=cert.get('date', ''), key=f"cert_date_{resume_id}_{i}")
                                        
                                        # Awards
                                        st.markdown("##### Awards & Honors")
                                        awards = resume.get('awards', [])
                                        award_count = st.session_state[award_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(awards) < award_count:
                                            awards.append("")
                                        
                                        for i in range(award_count):
                                            award = awards[i] if i < len(awards) else ""
                                            award_text = award if isinstance(award, str) else award.get('name', '') if isinstance(award, dict) else ""
                                            st.text_input(f"Award {i+1}", value=award_text, key=f"award_{resume_id}_{i}")
                                        
                                        # Publications
                                        st.markdown("##### Publications")
                                        publications = resume.get('publications', [])
                                        pub_count = st.session_state[pub_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(publications) < pub_count:
                                            publications.append({})
                                        
                                        for i in range(pub_count):
                                            pub = publications[i] if i < len(publications) else {}
                                            with st.expander(f"Publication {i+1}", expanded=i==0):
                                                pub_title = st.text_input("Title", value=pub.get('title', '') if isinstance(pub, dict) else (pub if isinstance(pub, str) else ''), key=f"pub_title_{resume_id}_{i}")
                                                pub_authors = st.text_input("Authors", value=pub.get('authors', '') if isinstance(pub, dict) else '', key=f"pub_authors_{resume_id}_{i}")
                                                pub_venue = st.text_input("Venue", value=pub.get('venue', '') if isinstance(pub, dict) else '', key=f"pub_venue_{resume_id}_{i}")
                                                pub_date = st.text_input("Date", value=pub.get('date', '') if isinstance(pub, dict) else '', key=f"pub_date_{resume_id}_{i}")
                                                pub_url = st.text_input("URL/DOI", value=pub.get('url', '') if isinstance(pub, dict) else '', key=f"pub_url_{resume_id}_{i}")
                                        
                                        # Volunteer Work
                                        st.markdown("##### Volunteer Work")
                                        volunteer_work = resume.get('volunteer_work', [])
                                        vol_count = st.session_state[vol_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(volunteer_work) < vol_count:
                                            volunteer_work.append({})
                                        
                                        for i in range(vol_count):
                                            vol = volunteer_work[i] if i < len(volunteer_work) else {}
                                            with st.expander(f"Volunteer Work {i+1}", expanded=i==0):
                                                vol_org = st.text_input("Organization", value=vol.get('organization', ''), key=f"vol_org_{resume_id}_{i}")
                                                vol_role = st.text_input("Role", value=vol.get('role', ''), key=f"vol_role_{resume_id}_{i}")
                                                vol_location = st.text_input("Location", value=vol.get('location', ''), key=f"vol_location_{resume_id}_{i}")
                                                vol_start = st.text_input("Start Date", value=vol.get('start_date', ''), key=f"vol_start_{resume_id}_{i}")
                                                vol_end = st.text_input("End Date", value=vol.get('end_date', ''), key=f"vol_end_{resume_id}_{i}")
                                                vol_desc = st.text_area("Description", value=vol.get('description', ''), 
                                                                        height=60, key=f"vol_desc_{resume_id}_{i}")
                                        
                                        # Leadership
                                        st.markdown("##### Leadership")
                                        leadership = resume.get('leadership', [])
                                        lead_count = st.session_state[lead_count_key]
                                        
                                        # Ensure we have enough entries
                                        while len(leadership) < lead_count:
                                            leadership.append({})
                                        
                                        for i in range(lead_count):
                                            lead = leadership[i] if i < len(leadership) else {}
                                            with st.expander(f"Leadership Role {i+1}", expanded=i==0):
                                                lead_role = st.text_input("Role", value=lead.get('role', ''), key=f"lead_role_{resume_id}_{i}")
                                                lead_org = st.text_input("Organization", value=lead.get('organization', ''), key=f"lead_org_{resume_id}_{i}")
                                                lead_desc = st.text_area("Description", value=lead.get('description', ''), 
                                                                         height=60, key=f"lead_desc_{resume_id}_{i}")
                                                lead_impact = st.text_input("Impact/Metrics", value=lead.get('impact', ''), key=f"lead_impact_{resume_id}_{i}")
                                                lead_start = st.text_input("Start Date", value=lead.get('start_date', ''), key=f"lead_start_{resume_id}_{i}")
                                                lead_end = st.text_input("End Date", value=lead.get('end_date', ''), key=f"lead_end_{resume_id}_{i}")
                                        
                                        # Hobbies & Interests
                                        st.markdown("##### Hobbies & Interests")
                                        hobbies = resume.get('hobbies', [])
                                        hobbies_text = ", ".join(hobbies) if hobbies else ""
                                        edit_hobbies = st.text_input("Hobbies (comma-separated)", value=hobbies_text, 
                                                                      key=f"hobbies_{resume_id}")
                                        
                                        # Professional Memberships
                                        st.markdown("##### Professional Memberships")
                                        memberships = resume.get('memberships', [])
                                        memberships_text = ", ".join(memberships) if memberships else ""
                                        edit_memberships = st.text_input("Memberships (comma-separated)", value=memberships_text, 
                                                                         key=f"memberships_{resume_id}")
                                        
                                        col_save, col_cancel = st.columns(2)
                                        with col_save:
                                            save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)
                                        with col_cancel:
                                            cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)
                                        
                                        if save_clicked:
                                            # Prepare update data from form inputs
                                            update_data = {
                                                "name": edit_name,
                                                "email": edit_email,
                                                "phone": edit_phone,
                                                "location": edit_location,
                                                "linkedin": edit_linkedin,
                                                "github": edit_github,
                                                "portfolio": edit_portfolio,
                                                "summary": edit_summary,
                                                "skills": [s.strip() for s in edit_skills.split(",") if s.strip()],
                                                "languages": [l.strip() for l in edit_languages.split(",") if l.strip()],
                                            }
                                            
                                            # Collect experience data from form
                                            exp_list = []
                                            for i in range(st.session_state[exp_count_key]):
                                                exp_title = st.session_state.get(f"exp_title_{resume_id}_{i}", "")
                                                exp_company = st.session_state.get(f"exp_company_{resume_id}_{i}", "")
                                                exp_start = st.session_state.get(f"exp_start_{resume_id}_{i}", "")
                                                exp_end = st.session_state.get(f"exp_end_{resume_id}_{i}", "")
                                                exp_desc = st.session_state.get(f"exp_desc_{resume_id}_{i}", "")
                                                
                                                if exp_title or exp_company:
                                                    exp_list.append({
                                                        "title": exp_title,
                                                        "company": exp_company,
                                                        "start_date": exp_start,
                                                        "end_date": exp_end,
                                                        "description": exp_desc
                                                    })
                                            update_data["experience"] = exp_list
                                            
                                            # Collect education data from form
                                            edu_list = []
                                            for i in range(st.session_state[edu_count_key]):
                                                edu_degree = st.session_state.get(f"edu_degree_{resume_id}_{i}", "")
                                                edu_institution = st.session_state.get(f"edu_institution_{resume_id}_{i}", "")
                                                edu_field = st.session_state.get(f"edu_field_{resume_id}_{i}", "")
                                                edu_year = st.session_state.get(f"edu_year_{resume_id}_{i}", "")
                                                edu_cgpa = st.session_state.get(f"edu_cgpa_{resume_id}_{i}", "")
                                                
                                                if edu_degree or edu_institution:
                                                    edu_entry = {
                                                        "degree": edu_degree,
                                                        "institution": edu_institution,
                                                        "field": edu_field,
                                                        "year": edu_year
                                                    }
                                                    # Save CGPA/GPA if provided
                                                    if edu_cgpa and edu_cgpa.strip():
                                                        edu_entry["gpa"] = edu_cgpa.strip()
                                                    edu_list.append(edu_entry)
                                            update_data["education"] = edu_list
                                            
                                            # Collect projects data from form
                                            proj_list = []
                                            for i in range(st.session_state[proj_count_key]):
                                                proj_name = st.session_state.get(f"proj_name_{resume_id}_{i}", "")
                                                proj_desc = st.session_state.get(f"proj_desc_{resume_id}_{i}", "")
                                                proj_url = st.session_state.get(f"proj_url_{resume_id}_{i}", "")
                                                
                                                if proj_name:
                                                    proj_list.append({
                                                        "name": proj_name,
                                                        "description": proj_desc,
                                                        "url": proj_url
                                                    })
                                            update_data["projects"] = proj_list
                                            
                                            # Collect certifications data from form
                                            cert_list = []
                                            for i in range(st.session_state[cert_count_key]):
                                                cert_name = st.session_state.get(f"cert_name_{resume_id}_{i}", "")
                                                cert_org = st.session_state.get(f"cert_org_{resume_id}_{i}", "")
                                                cert_date = st.session_state.get(f"cert_date_{resume_id}_{i}", "")
                                                
                                                if cert_name:
                                                    cert_list.append({
                                                        "name": cert_name,
                                                        "organization": cert_org,
                                                        "date": cert_date
                                                    })
                                            update_data["certifications"] = cert_list
                                            
                                            # Collect awards data from form
                                            awards_list = []
                                            for i in range(st.session_state[award_count_key]):
                                                award_text = st.session_state.get(f"award_{resume_id}_{i}", "")
                                                if award_text.strip():
                                                    awards_list.append(award_text.strip())
                                            update_data["awards"] = awards_list
                                            
                                            # Collect publications data from form
                                            pub_list = []
                                            for i in range(st.session_state[pub_count_key]):
                                                pub_title = st.session_state.get(f"pub_title_{resume_id}_{i}", "")
                                                pub_authors = st.session_state.get(f"pub_authors_{resume_id}_{i}", "")
                                                pub_venue = st.session_state.get(f"pub_venue_{resume_id}_{i}", "")
                                                pub_date = st.session_state.get(f"pub_date_{resume_id}_{i}", "")
                                                pub_url = st.session_state.get(f"pub_url_{resume_id}_{i}", "")
                                                
                                                if pub_title:
                                                    pub_list.append({
                                                        "title": pub_title,
                                                        "authors": pub_authors,
                                                        "venue": pub_venue,
                                                        "date": pub_date,
                                                        "url": pub_url
                                                    })
                                            update_data["publications"] = pub_list
                                            
                                            # Collect volunteer work data from form
                                            vol_list = []
                                            for i in range(st.session_state[vol_count_key]):
                                                vol_org = st.session_state.get(f"vol_org_{resume_id}_{i}", "")
                                                vol_role = st.session_state.get(f"vol_role_{resume_id}_{i}", "")
                                                vol_location = st.session_state.get(f"vol_location_{resume_id}_{i}", "")
                                                vol_start = st.session_state.get(f"vol_start_{resume_id}_{i}", "")
                                                vol_end = st.session_state.get(f"vol_end_{resume_id}_{i}", "")
                                                vol_desc = st.session_state.get(f"vol_desc_{resume_id}_{i}", "")
                                                
                                                if vol_org or vol_role:
                                                    vol_list.append({
                                                        "organization": vol_org,
                                                        "role": vol_role,
                                                        "location": vol_location,
                                                        "start_date": vol_start,
                                                        "end_date": vol_end,
                                                        "description": vol_desc
                                                    })
                                            update_data["volunteer_work"] = vol_list
                                            
                                            # Collect leadership data from form
                                            lead_list = []
                                            for i in range(st.session_state[lead_count_key]):
                                                lead_role = st.session_state.get(f"lead_role_{resume_id}_{i}", "")
                                                lead_org = st.session_state.get(f"lead_org_{resume_id}_{i}", "")
                                                lead_desc = st.session_state.get(f"lead_desc_{resume_id}_{i}", "")
                                                lead_impact = st.session_state.get(f"lead_impact_{resume_id}_{i}", "")
                                                lead_start = st.session_state.get(f"lead_start_{resume_id}_{i}", "")
                                                lead_end = st.session_state.get(f"lead_end_{resume_id}_{i}", "")
                                                
                                                if lead_role or lead_org:
                                                    lead_list.append({
                                                        "role": lead_role,
                                                        "organization": lead_org,
                                                        "description": lead_desc,
                                                        "impact": lead_impact,
                                                        "start_date": lead_start,
                                                        "end_date": lead_end
                                                    })
                                            update_data["leadership"] = lead_list
                                            
                                            # Collect hobbies and memberships
                                            update_data["hobbies"] = [h.strip() for h in edit_hobbies.split(",") if h.strip()]
                                            update_data["memberships"] = [m.strip() for m in edit_memberships.split(",") if m.strip()]
                                            
                                            # Send update request
                                            try:
                                                with st.spinner("Saving changes..."):
                                                    update_response = requests.put(
                                                        f"{st.session_state.api_url}/resumes/{resume_id}/profile",
                                                        json=update_data,
                                                        timeout=10
                                                    )
                                                
                                                if update_response.status_code == 200:
                                                    st.success("✅ Profile updated successfully!")
                                                    st.session_state[edit_key] = False
                                                    st.rerun()
                                                else:
                                                    error_detail = update_response.json().get("detail", "Unknown error")
                                                    st.error(f"❌ Failed to update: {error_detail}")
                                            except Exception as e:
                                                st.error(f"❌ Error updating profile: {str(e)}")
                                        
                                        if cancel_clicked:
                                            st.session_state[edit_key] = False
                                            st.rerun()
                            
                            else:
                                # VIEW MODE - Display complete parsed information
                                    # Personal Information
                                    col_p1, col_p2 = st.columns(2)
                                    with col_p1:
                                        st.text(f"**Name:** {resume.get('name', 'N/A')}")
                                        st.text(f"**Email:** {resume.get('email', 'N/A')}")
                                        st.text(f"**Phone:** {resume.get('phone', 'N/A')}")
                                        st.text(f"**Location:** {resume.get('location', 'N/A')}")
                                    
                                    with col_p2:
                                        linkedin = resume.get('linkedin', '')
                                        github = resume.get('github', '')
                                        portfolio = resume.get('portfolio', '')
                                        
                                        if linkedin:
                                            st.markdown(f"**LinkedIn:** [View Profile]({linkedin})")
                                        else:
                                            st.text("**LinkedIn:** N/A")
                                        
                                        if github:
                                            st.markdown(f"**GitHub:** [View Profile]({github})")
                                        else:
                                            st.text("**GitHub:** N/A")
                                        
                                        if portfolio:
                                            st.markdown(f"**Portfolio:** [View Site]({portfolio})")
                                        else:
                                            st.text("**Portfolio:** N/A")
                                    
                                    # Summary
                                    summary = resume.get('summary', '')
                                    if summary:
                                        st.markdown("**Summary:**")
                                        st.info(summary)
                                    
                                    # Skills - Complete list
                                    skills = resume.get('skills', [])
                                    if skills:
                                        st.markdown(f"**Skills ({len(skills)}):**")
                                        st.text(", ".join(skills))
                                    
                                    # Languages
                                    languages = resume.get('languages', [])
                                    if languages:
                                        st.markdown(f"**Languages ({len(languages)}):**")
                                        st.text(", ".join(languages))
                                    
                                    # Experience - Complete list
                                    experience = resume.get('experience', [])
                                    if experience:
                                        st.markdown(f"**Work Experience ({len(experience)} positions):**")
                                        for exp in experience:
                                            if isinstance(exp, dict):
                                                title = exp.get('title', 'N/A')
                                                company = exp.get('company', 'N/A')
                                                start_date = exp.get('start_date', '')
                                                end_date = exp.get('end_date', '')
                                                description = exp.get('description', '')
                                                
                                                st.markdown(f"**{title}** at *{company}*")
                                                if start_date or end_date:
                                                    st.caption(f"{start_date} - {end_date}")
                                                if description:
                                                    st.text(description)
                                                st.markdown("---")
                                    
                                    # Education - Complete list
                                    education = resume.get('education', [])
                                    if education:
                                        st.markdown(f"**Education ({len(education)} entries):**")
                                        for edu in education:
                                            if isinstance(edu, dict):
                                                degree = edu.get('degree', 'N/A')
                                                institution = edu.get('institution', 'N/A')
                                                field = edu.get('field', '')
                                                year = edu.get('year', '')
                                                gpa = edu.get('gpa', '') or edu.get('cgpa', '')
                                                
                                                st.markdown(f"**{degree}**")
                                                st.text(f"{institution}" + (f" - {field}" if field else ""))
                                                if year:
                                                    st.caption(f"Year: {year}")
                                                if gpa:
                                                    st.caption(f"📊 CGPA/GPA: {gpa}")
                                                st.markdown("---")
                                    
                                    # Projects - Complete list
                                    projects = resume.get('projects', [])
                                    if projects:
                                        st.markdown(f"**Projects ({len(projects)}):**")
                                        for proj in projects:
                                            if isinstance(proj, dict):
                                                name = proj.get('name', 'N/A')
                                                description = proj.get('description', '')
                                                url = proj.get('url', '')
                                                
                                                st.markdown(f"**{name}**")
                                                if description:
                                                    st.text(description)
                                                if url:
                                                    st.markdown(f"[View Project]({url})")
                                                st.markdown("---")
                                    
                                    # Certifications - Complete list
                                    certifications = resume.get('certifications', [])
                                    if certifications:
                                        st.markdown(f"**Certifications ({len(certifications)}):**")
                                        for cert in certifications:
                                            if isinstance(cert, dict):
                                                name = cert.get('name', 'N/A')
                                                organization = cert.get('organization', '')
                                                date = cert.get('date', '')
                                                
                                                st.markdown(f"**{name}**")
                                                if organization:
                                                    st.text(f"Issued by: {organization}")
                                                if date:
                                                    st.caption(f"Date: {date}")
                                                st.markdown("---")
                                    
                                    # Awards
                                    awards = resume.get('awards', [])
                                    if awards:
                                        st.markdown(f"**Awards ({len(awards)}):**")
                                        for award in awards:
                                            if isinstance(award, dict):
                                                st.text(f"• {award.get('name', 'N/A')}")
                                    
                                    # Publications
                                    publications = resume.get('publications', [])
                                    if publications:
                                        st.markdown(f"**Publications ({len(publications)}):**")
                                        for pub in publications:
                                            if isinstance(pub, dict):
                                                st.text(f"• {pub.get('title', 'N/A')}")
                                    
                                    # Volunteer Work
                                    volunteer_work = resume.get('volunteer_work', [])
                                    if volunteer_work:
                                        st.markdown(f"**Volunteer Work ({len(volunteer_work)}):**")
                                        for vol in volunteer_work:
                                            if isinstance(vol, dict):
                                                st.text(f"• {vol.get('organization', 'N/A')} - {vol.get('role', 'N/A')}")
                                    
                                    # Leadership
                                    leadership = resume.get('leadership', [])
                                    if leadership:
                                        st.markdown(f"**Leadership ({len(leadership)}):**")
                                        for lead in leadership:
                                            if isinstance(lead, dict):
                                                st.text(f"• {lead.get('role', 'N/A')} at {lead.get('organization', 'N/A')}")
                                                if lead.get('impact'):
                                                    st.caption(f"Impact: {lead.get('impact')}")
                                    
                                    # Hobbies
                                    hobbies = resume.get('hobbies', [])
                                    if hobbies:
                                        st.markdown(f"**Hobbies:** {', '.join(hobbies)}")
                                    
                                    # Memberships
                                    memberships = resume.get('memberships', [])
                                    if memberships:
                                        st.markdown(f"**Professional Memberships:** {', '.join(memberships)}")
                                    
                                    if not has_profile:
                                        st.info("ℹ️ No profile data found. Click 'Edit' above to add information.")
                        
                        st.markdown("---")
                
                # Navigation buttons
                st.markdown("---")
                col_refresh, col_upload = st.columns(2)
                with col_refresh:
                    if st.button("🔄 Refresh List", use_container_width=True):
                        st.rerun()
                with col_upload:
                    if st.button("📤 Upload Another Resume", use_container_width=True):
                        st.session_state.page = "📤 Upload Resume"
                        st.rerun()
        
        else:
            error_detail = "Unknown error"
            try:
                error_response = response.json()
                error_detail = error_response.get("detail", str(response.text))
            except:
                error_detail = response.text
            
            st.error(f"❌ Failed to load resumes: {error_detail}")
            st.info(f"Status Code: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection Error: Could not connect to the API server.")
        st.info("Please make sure your FastAPI backend is running at the configured URL.")
        if st.button("🔄 Retry", use_container_width=True):
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")


def display_upload_page():
    """Display upload page"""
    st.markdown('<h1 class="main-header">📄 Auto Apply</h1>', unsafe_allow_html=True)
    st.markdown("### 📤 Upload New Resume")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Only PDF files are accepted"
    )
    
    if uploaded_file is not None:
        # Display file info
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**File Name:** {uploaded_file.name}")
        with col2:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.info(f"**File Size:** {file_size_mb:.2f} MB")
        
        # Upload button
        if st.button("🚀 Upload Resume", type="primary", use_container_width=True):
            try:
                # Show progress
                with st.spinner("Uploading resume to S3..."):
                    # Prepare file for upload
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    
                    # Make API request
                    response = requests.post(
                        f"{st.session_state.api_url}/upload-resume",
                        files=files,
                        timeout=30
                    )
                
                # Handle response
                if response.status_code == 200:
                    result = response.json()
                    
                    # Success message
                    st.success("✅ Resume uploaded successfully!")
                    
                    # Display results
                    st.markdown("### 📊 Upload Details")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Original Filename", result.get("original_filename", "N/A"))
                        st.metric("Stored Filename", result.get("filename", "N/A"))
                    
                    with col2:
                        file_size_kb = result.get("file_size", 0) / 1024
                        st.metric("File Size", f"{file_size_kb:.2f} KB")
                        if result.get("mongodb_id"):
                            st.metric("MongoDB ID", result.get("mongodb_id", "N/A"))
                    
                    # S3 URL
                    s3_url = result.get("s3_url", "")
                    if s3_url:
                        st.markdown("### 🔗 S3 URL")
                        st.code(s3_url, language=None)
                        st.markdown(f"[Open in browser]({s3_url})")
                    
                    # Navigation buttons
                    # Navigation button
                    st.markdown("---")
                    if st.button("🏠 Back to Home", use_container_width=True):
                        st.session_state.page = "🏠 Home"
                        st.rerun()
                else:
                    # Error handling
                    error_detail = "Unknown error"
                    try:
                        error_response = response.json()
                        error_detail = error_response.get("detail", str(response.text))
                    except:
                        error_detail = response.text
                    
                    st.error(f"❌ Upload failed: {error_detail}")
                    st.info(f"Status Code: {response.status_code}")
            
            except requests.exceptions.ConnectionError:
                st.error("❌ Connection Error: Could not connect to the API server.")
                st.info("Please make sure your FastAPI backend is running at the configured URL.")
            
            except requests.exceptions.Timeout:
                st.error("❌ Request Timeout: The upload took too long.")
            
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
    
    # Navigation buttons at bottom of upload page
    # Navigation button at bottom of upload page
    st.markdown("---")
    if st.button("🏠 Back to Home", use_container_width=True, key="upload_bottom_home"):
        st.session_state.page = "🏠 Home"
        st.rerun()


def display_user_profiles_page():
    """Display user profiles page"""
    st.markdown('<h1 class="main-header">👤 User Profiles</h1>', unsafe_allow_html=True)
    st.markdown("### 📊 Parsed Resume Data")
    
    # Fetch user profiles from API
    try:
        with st.spinner("Loading user profiles..."):
            response = requests.get(
                f"{st.session_state.api_url}/user-profiles",
                timeout=10
            )
        
        if response.status_code == 200:
            data = response.json()
            profiles = data.get("profiles", [])
            count = data.get("count", 0)
            
            if count == 0:
                st.info("📭 No user profiles found. Upload resumes to create profiles!")
                st.markdown("---")
                if st.button("📤 Go to Upload Page", use_container_width=True):
                    st.session_state.page = "📤 Upload Resume"
                    st.rerun()
            else:
                st.success(f"✅ Found {count} user profile(s)")
                st.markdown("---")
                
                # Display profiles
                for profile in profiles:
                    with st.container():
                        # Profile header
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            name = profile.get('name', 'Unknown')
                            email = profile.get('email', 'N/A')
                            st.markdown(f"### 👤 {name}")
                            if email != 'N/A':
                                st.markdown(f"📧 {email}")
                        
                        with col2:
                            # Profile stats
                            skills_count = len(profile.get('skills', []))
                            exp_count = len(profile.get('experience', []))
                            edu_count = len(profile.get('education', []))
                            st.metric("Skills", skills_count)
                            st.metric("Experience", exp_count)
                            st.metric("Education", edu_count)
                        
                        # Expandable profile details
                        with st.expander(f"View Full Profile: {name}", expanded=False):
                            # Personal Information
                            st.markdown("#### 📋 Personal Information")
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.text(f"**Name:** {profile.get('name', 'N/A')}")
                                st.text(f"**Email:** {profile.get('email', 'N/A')}")
                                st.text(f"**Phone:** {profile.get('phone', 'N/A')}")
                                st.text(f"**Location:** {profile.get('location', 'N/A')}")
                            
                            with col_b:
                                linkedin = profile.get('linkedin', '')
                                github = profile.get('github', '')
                                portfolio = profile.get('portfolio', '')
                                
                                if linkedin:
                                    st.markdown(f"**LinkedIn:** [View Profile]({linkedin})")
                                else:
                                    st.text("**LinkedIn:** N/A")
                                
                                if github:
                                    st.markdown(f"**GitHub:** [View Profile]({github})")
                                else:
                                    st.text("**GitHub:** N/A")
                                
                                if portfolio:
                                    st.markdown(f"**Portfolio:** [View Site]({portfolio})")
                                else:
                                    st.text("**Portfolio:** N/A")
                            
                            # Summary
                            summary = profile.get('summary', '')
                            if summary:
                                st.markdown("#### 📝 Professional Summary")
                                st.info(summary)
                            
                            # Skills
                            skills = profile.get('skills', [])
                            if skills:
                                st.markdown("#### 🛠️ Skills")
                                # Display skills as badges
                                skill_cols = st.columns(min(5, len(skills)))
                                for idx, skill in enumerate(skills[:15]):  # Show first 15
                                    with skill_cols[idx % 5]:
                                        st.markdown(f"- {skill}")
                                if len(skills) > 15:
                                    st.caption(f"... and {len(skills) - 15} more skills")
                            
                            # Languages
                            languages = profile.get('languages', [])
                            if languages:
                                st.markdown("#### 🌐 Languages")
                                st.text(", ".join(languages))
                            
                            # Education
                            education = profile.get('education', [])
                            if education:
                                st.markdown("#### 🎓 Education")
                                for edu in education:
                                    if isinstance(edu, dict):
                                        st.markdown(f"**{edu.get('degree', 'N/A')}**")
                                        st.text(f"  {edu.get('field', '')} - {edu.get('institution', 'N/A')}")
                                        if edu.get('location'):
                                            st.text(f"  📍 {edu.get('location')}")
                                        if edu.get('graduation_date'):
                                            st.text(f"  📅 Graduated: {edu.get('graduation_date')}")
                                        gpa = edu.get('gpa', '') or edu.get('cgpa', '')
                                        if gpa:
                                            st.text(f"  📊 CGPA/GPA: {gpa}")
                                        st.markdown("---")
                            
                            # Experience
                            experience = profile.get('experience', [])
                            if experience:
                                st.markdown("#### 💼 Work Experience")
                                for exp in experience:
                                    if isinstance(exp, dict):
                                        st.markdown(f"**{exp.get('title', 'N/A')}** at **{exp.get('company', 'N/A')}**")
                                        if exp.get('location'):
                                            st.text(f"📍 {exp.get('location')}")
                                        
                                        date_range = ""
                                        if exp.get('start_date'):
                                            date_range = exp.get('start_date')
                                        if exp.get('end_date'):
                                            date_range += f" - {exp.get('end_date')}"
                                        if date_range:
                                            st.text(f"📅 {date_range}")
                                        
                                        if exp.get('description'):
                                            st.text(f"📝 {exp.get('description')}")
                                        
                                        achievements = exp.get('achievements', [])
                                        if achievements:
                                            st.markdown("**Achievements:**")
                                            for achievement in achievements:
                                                st.markdown(f"- {achievement}")
                                        
                                        st.markdown("---")
                            
                            # Projects
                            projects = profile.get('projects', [])
                            if projects:
                                st.markdown("#### 🚀 Projects")
                                for project in projects:
                                    if isinstance(project, dict):
                                        st.markdown(f"**{project.get('name', 'N/A')}**")
                                        if project.get('description'):
                                            st.text(f"  {project.get('description')}")
                                        technologies = project.get('technologies', [])
                                        if technologies:
                                            st.text(f"  🛠️ Technologies: {', '.join(technologies)}")
                                        if project.get('url'):
                                            st.markdown(f"  🔗 [View Project]({project.get('url')})")
                                        st.markdown("---")
                            
                            # Certifications
                            certifications = profile.get('certifications', [])
                            if certifications:
                                st.markdown("#### 🏆 Certifications")
                                for cert in certifications:
                                    if isinstance(cert, dict):
                                        st.markdown(f"**{cert.get('name', 'N/A')}**")
                                        st.text(f"  Issued by: {cert.get('issuer', 'N/A')}")
                                        if cert.get('date'):
                                            st.text(f"  📅 Date: {cert.get('date')}")
                                        if cert.get('expiry_date'):
                                            st.text(f"  ⏰ Expires: {cert.get('expiry_date')}")
                                        st.markdown("---")
                            
                            # Awards
                            awards = profile.get('awards', [])
                            if awards:
                                st.markdown("#### 🏅 Awards")
                                for award in awards:
                                    st.markdown(f"- {award}")
                            
                            # Publications
                            publications = profile.get('publications', [])
                            if publications:
                                st.markdown("#### 📚 Publications")
                                for pub in publications:
                                    st.markdown(f"- {pub}")
                            
                            # Volunteer Work
                            volunteer = profile.get('volunteer_work', [])
                            if volunteer:
                                st.markdown("#### 🤝 Volunteer Work")
                                for vol in volunteer:
                                    if isinstance(vol, dict):
                                        st.markdown(f"**{vol.get('role', 'N/A')}** at **{vol.get('organization', 'N/A')}**")
                                        if vol.get('description'):
                                            st.text(f"  {vol.get('description')}")
                                        date_range = ""
                                        if vol.get('start_date'):
                                            date_range = vol.get('start_date')
                                        if vol.get('end_date'):
                                            date_range += f" - {vol.get('end_date')}"
                                        if date_range:
                                            st.text(f"  📅 {date_range}")
                                        st.markdown("---")
                            
                            # Metadata
                            st.markdown("#### ℹ️ Metadata")
                            col_meta1, col_meta2 = st.columns(2)
                            with col_meta1:
                                resume_ids = profile.get('resume_ids', [])
                                st.text(f"**Resume IDs:** {len(resume_ids)} resume(s)")
                                if profile.get('created_at'):
                                    created = format_date(profile.get('created_at'))
                                    st.text(f"**Created:** {created}")
                            with col_meta2:
                                if profile.get('updated_at'):
                                    updated = format_date(profile.get('updated_at'))
                                    st.text(f"**Updated:** {updated}")
                                if profile.get('parsed_at'):
                                    parsed = format_date(profile.get('parsed_at'))
                                    st.text(f"**Last Parsed:** {parsed}")
                        
                        st.markdown("---")
                
                # Refresh button
                col_refresh, col_home = st.columns([1, 1])
                with col_refresh:
                    if st.button("🔄 Refresh List", use_container_width=True):
                        st.rerun()
                with col_home:
                    if st.button("🏠 Back to Home", use_container_width=True):
                        st.session_state.page = "🏠 Home"
                        st.rerun()
        
        else:
            error_detail = "Unknown error"
            try:
                error_response = response.json()
                error_detail = error_response.get("detail", str(response.text))
            except:
                error_detail = response.text
            
            st.error(f"❌ Failed to load profiles: {error_detail}")
            st.info(f"Status Code: {response.status_code}")
    
    except requests.exceptions.ConnectionError:
        st.error("❌ Connection Error: Could not connect to the API server.")
        st.info("Please make sure your FastAPI backend is running at the configured URL.")
        if st.button("🔄 Retry", use_container_width=True):
            st.rerun()
    
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")


# Main app logic
if st.session_state.page == "🏠 Home":
    display_homepage()
elif st.session_state.page == "📤 Upload Resume":
    display_upload_page()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>Auto Apply | Powered by FastAPI & Streamlit</div>",
    unsafe_allow_html=True
)
