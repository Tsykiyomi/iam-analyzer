#!/usr/bin/env python3
"""
IAM Analyzer v5 - Enterprise Edition
Multi-format file support + Super in-depth reporting capabilities
"""

import streamlit as st
import pandas as pd
import io
import json
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from typing import Dict, List, Tuple, Optional, Any, Union
from openai import OpenAI
import openai
import base64
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# Document processing imports
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Try to import plotly, fall back to matplotlib if not available
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTLY_AVAILABLE = False

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="IAM Analyzer v5 Enterprise", 
    layout="wide",
    page_icon="🔐",
    initial_sidebar_state="expanded"
)

# Constants
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB for enterprise files
SUPPORTED_MODELS = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
RISK_COLORS = {"Low": "#28a745", "Medium": "#ffc107", "High": "#dc3545", "Critical": "#6f42c1"}
SUPPORTED_FILE_TYPES = ["csv", "xlsx", "xls", "txt", "docx", "pptx", "pdf", "png", "jpg", "jpeg", "gif", "bmp", "tiff", "pbi"]

# ================== AUTHENTICATION ==================

def check_authentication():
    """Simple password authentication"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False
    
    if st.session_state["authenticated"]:
        return True
    
    st.title("🔐 IAM Analyzer v5 Enterprise")
    st.markdown("Please enter the access password to continue.")
    
    try:
        correct_password = st.secrets.get("APP_PASSWORD", "IAMEnterprise2024!")
    except:
        correct_password = "IAMEnterprise2024!"
    
    entered_password = st.text_input("Password:", type="password", key="auth_password")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🚀 Access Enterprise Tool", type="primary", use_container_width=True):
            if entered_password == correct_password:
                st.session_state["authenticated"] = True
                st.success("✅ Access granted! Loading Enterprise IAM Analyzer...")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Contact administrator for access.")
    
    st.markdown("---")
    st.info("🛡️ Enterprise IAM Analysis Platform - Supports 10+ file formats with AI-powered insights")
    return False

# ================== UTILITY FUNCTIONS ==================

def validate_api_key(api_key: str) -> bool:
    """Validate OpenAI API key format"""
    if not api_key:
        return False
    return api_key.startswith('sk-') and len(api_key) > 20

def validate_file_size(file) -> bool:
    """Check if file size is within limits"""
    return file.size <= MAX_FILE_SIZE

def safe_json_parse(text: str) -> Optional[Dict]:
    """Safely parse JSON from AI response"""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return None

# ================== ADVANCED FILE PROCESSING ==================

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX files"""
    if not DOCX_AVAILABLE:
        return "DOCX processing not available. Install python-docx."
    
    try:
        doc = Document(io.BytesIO(file_content))
        text_content = []
        
        # Extract paragraphs
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text for cell in row.cells])
                if row_text.strip():
                    text_content.append(row_text)
        
        return "\n".join(text_content)
    except Exception as e:
        return f"Error processing DOCX: {str(e)}"

def extract_text_from_pptx(file_content: bytes) -> str:
    """Extract text from PowerPoint files"""
    if not PPTX_AVAILABLE:
        return "PPTX processing not available. Install python-pptx."
    
    try:
        prs = Presentation(io.BytesIO(file_content))
        text_content = []
        
        for slide_num, slide in enumerate(prs.slides, 1):
            text_content.append(f"=== SLIDE {slide_num} ===")
            
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text_content.append(shape.text)
                    
                # Extract table data
                if shape.has_table:
                    table = shape.table
                    for row in table.rows:
                        row_text = " | ".join([cell.text for cell in row.cells])
                        if row_text.strip():
                            text_content.append(row_text)
        
        return "\n".join(text_content)
    except Exception as e:
        return f"Error processing PPTX: {str(e)}"

def extract_text_from_image(file_content: bytes, file_name: str) -> str:
    """Extract text from images using OCR"""
    if not OCR_AVAILABLE:
        return "OCR not available. Install PIL and pytesseract."
    
    try:
        image = Image.open(io.BytesIO(file_content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Perform OCR
        extracted_text = pytesseract.image_to_string(image)
        
        if extracted_text.strip():
            return f"OCR Extracted Text from {file_name}:\n{extracted_text}"
        else:
            return f"No text detected in image: {file_name}"
            
    except Exception as e:
        return f"Error processing image {file_name}: {str(e)}"

def extract_text_from_pbi(file_content: bytes) -> str:
    """Extract metadata and structure from Power BI files"""
    try:
        # PBI files are essentially ZIP archives
        with zipfile.ZipFile(io.BytesIO(file_content), 'r') as zip_file:
            content_info = []
            content_info.append("Power BI File Structure Analysis:")
            
            # List all files in the archive
            for file_info in zip_file.filelist:
                content_info.append(f"- {file_info.filename} ({file_info.file_size} bytes)")
            
            # Try to extract some metadata
            try:
                if 'metadata.json' in zip_file.namelist():
                    metadata = zip_file.read('metadata.json').decode('utf-8')
                    content_info.append("\nMetadata:")
                    content_info.append(metadata[:1000] + "..." if len(metadata) > 1000 else metadata)
            except:
                pass
                
            # Try to extract model information
            try:
                model_files = [f for f in zip_file.namelist() if 'model' in f.lower() and f.endswith('.json')]
                for model_file in model_files[:3]:  # Limit to first 3 model files
                    model_content = zip_file.read(model_file).decode('utf-8')
                    content_info.append(f"\n{model_file}:")
                    content_info.append(model_content[:500] + "..." if len(model_content) > 500 else model_content)
            except:
                pass
        
        return "\n".join(content_info)
        
    except Exception as e:
        return f"Error processing Power BI file: {str(e)}"

# ================== ENHANCED FILE LOADING ==================

@st.cache_data
def load_file_content_v5(file_content: bytes, file_name: str, file_type: str) -> Optional[pd.DataFrame]:
    """Enhanced file loading with support for multiple formats"""
    try:
        if file_type == "csv":
            return pd.read_csv(io.BytesIO(file_content))
        
        elif file_type in ["xlsx", "xls"]:
            return pd.read_excel(io.BytesIO(file_content))
        
        elif file_type == "txt":
            content = file_content.decode("utf-8")
            return pd.DataFrame({"Text_Content": [content]})
        
        elif file_type == "docx":
            text_content = extract_text_from_docx(file_content)
            return pd.DataFrame({"Document_Content": [text_content]})
        
        elif file_type == "pptx":
            text_content = extract_text_from_pptx(file_content)
            return pd.DataFrame({"Presentation_Content": [text_content]})
        
        elif file_type in ["png", "jpg", "jpeg", "gif", "bmp", "tiff"]:
            text_content = extract_text_from_image(file_content, file_name)
            return pd.DataFrame({"Image_OCR_Content": [text_content]})
        
        elif file_type == "pbi":
            text_content = extract_text_from_pbi(file_content)
            return pd.DataFrame({"PowerBI_Analysis": [text_content]})
        
        else:
            return None
            
    except Exception as e:
        st.error(f"Error processing {file_name}: {str(e)}")
        return None

@st.cache_data
def generate_enhanced_summary(all_data: Dict[str, pd.DataFrame]) -> str:
    """Generate comprehensive data summary for AI analysis"""
    summary = []
    summary.append("=== COMPREHENSIVE IAM DATA ANALYSIS ===")
    summary.append(f"Analysis Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append(f"Total Files Processed: {len(all_data)}")
    summary.append("")
    
    total_records = 0
    file_types = {}
    
    for name, df in all_data.items():
        file_ext = name.split('.')[-1].lower()
        file_types[file_ext] = file_types.get(file_ext, 0) + 1
        total_records += df.shape[0]
        
        summary.append(f"📁 FILE: {name}")
        summary.append(f"   Type: {file_ext.upper()}")
        summary.append(f"   Dimensions: {df.shape[0]} rows × {df.shape[1]} columns")
        
        # Show column information
        if df.shape[1] <= 20:
            summary.append(f"   Columns: {', '.join(df.columns)}")
        else:
            summary.append(f"   Columns: {', '.join(df.columns[:15])} ... (+{df.shape[1] - 15} more)")
        
        # Show data sample with more context
        if df.shape[0] > 0:
            summary.append("   Sample Data:")
            sample_df = df.head(3)
            for idx, row in sample_df.iterrows():
                summary.append(f"     Row {idx + 1}: {dict(row)}")
        
        # Data quality insights
        if df.shape[1] > 1:
            null_counts = df.isnull().sum()
            if null_counts.sum() > 0:
                summary.append(f"   Data Quality: {null_counts.sum()} null values detected")
            
            # Look for potential IAM-related columns
            iam_keywords = ['user', 'role', 'permission', 'access', 'group', 'policy', 'entitlement', 'account', 'login', 'auth']
            iam_columns = [col for col in df.columns if any(keyword in col.lower() for keyword in iam_keywords)]
            if iam_columns:
                summary.append(f"   IAM-Related Columns: {', '.join(iam_columns)}")
        
        summary.append("   " + "─" * 80)
    
    # Overall statistics
    summary.append("\n=== DATASET OVERVIEW ===")
    summary.append(f"Total Records Across All Files: {total_records:,}")
    summary.append(f"File Type Distribution: {dict(file_types)}")
    summary.append(f"Analysis Scope: Enterprise IAM Security Assessment")
    
    return "\n".join(summary)

# ================== SETUP FUNCTIONS ==================

def initialize_session_state():
    """Initialize all session state variables"""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "chat_log" not in st.session_state:
        st.session_state["chat_log"] = []
    if "analysis_count" not in st.session_state:
        st.session_state["analysis_count"] = 0
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

def setup_sidebar_v5() -> Tuple[str, str, float, int]:
    """Enhanced sidebar setup for v5"""
    st.sidebar.title("🔐 IAM Analyzer v5 Enterprise")
    st.sidebar.markdown("*Multi-Format Support + Advanced Reporting*")
    
    # Add logout button
    if st.sidebar.button("🚪 Logout"):
        st.session_state["authenticated"] = False
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # API Configuration
    st.sidebar.subheader("⚙️ AI Configuration")
    
    # Check for API key in secrets
    api_key = None
    try:
        if "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
            st.sidebar.success("🔑 Using API key from secrets")
    except:
        pass
    
    if not api_key:
        api_key = st.sidebar.text_input(
            "OpenAI API Key:", 
            type="password",
            help="Enter your API key or configure in secrets"
        )
    
    if api_key and not validate_api_key(api_key):
        st.sidebar.error("❌ Invalid API key format")
        return None, None, None, None
    
    # Advanced settings
    with st.sidebar.expander("🎛️ Advanced AI Settings"):
        model = st.selectbox("AI Model:", SUPPORTED_MODELS, index=0)
        temperature = st.slider("Analysis Creativity:", 0.0, 1.0, 0.2, 0.1)
        max_tokens = st.slider("Response Depth:", 1000, 4000, 2500, 100)
    
    # File processing status
    st.sidebar.markdown("---")
    st.sidebar.subheader("📁 File Support Status")
    
    formats_status = {
        "📊 Spreadsheets (CSV/XLSX)": "✅ Full Support",
        "📄 Documents (DOCX)": "✅ Available" if DOCX_AVAILABLE else "❌ Install python-docx",
        "🎨 Presentations (PPTX)": "✅ Available" if PPTX_AVAILABLE else "❌ Install python-pptx", 
        "🖼️ Images (OCR)": "✅ Available" if OCR_AVAILABLE else "❌ Install pytesseract",
        "📈 Charts (Plotly)": "✅ Available" if PLOTLY_AVAILABLE else "❌ Install plotly",
        "📊 Power BI (PBI)": "✅ Basic Support"
    }
    
    for format_name, status in formats_status.items():
        if "✅" in status:
            st.sidebar.success(f"{format_name}: {status.replace('✅ ', '')}")
        else:
            st.sidebar.warning(f"{format_name}: {status.replace('❌ ', '')}")
    
    return api_key, model, temperature, max_tokens

# ================== AI ANALYSIS FUNCTIONS ==================

def create_enterprise_prompt(data_summary: str, tasks: List[str], analysis_depth: str = "comprehensive") -> str:
    """Create enterprise-grade analysis prompt"""
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    return f"""You are a Senior IAM (Identity and Access Management) Security Consultant conducting an enterprise-grade security assessment.

ENGAGEMENT DETAILS:
- Assessment Date: {current_date}
- Analysis Scope: {analysis_depth.title()} Enterprise IAM Review
- Deliverable: Executive + Technical Security Report

ANALYSIS TASKS:
{chr(10).join(f"• {task}" for task in tasks)}

IAM DATA INVENTORY:
{data_summary}

COMPREHENSIVE ANALYSIS REQUIREMENTS:

1. EXECUTIVE ASSESSMENT:
   - Business risk impact analysis
   - Compliance posture evaluation
   - Strategic recommendations with timelines
   - Budget implications for remediation

2. TECHNICAL FINDINGS:
   - Detailed security control gaps
   - Attack vector analysis
   - Privilege escalation paths
   - Data classification and access patterns

3. COMPLIANCE MAPPING:
   - SOX, SOD, GDPR, HIPAA considerations
   - Industry framework alignment (NIST, ISO 27001)
   - Audit trail and logging adequacy

4. RISK QUANTIFICATION:
   - Business impact scoring (1-10 scale)
   - Probability of exploitation
   - Estimated cost of breach scenarios
   - Risk appetite alignment

OUTPUT FORMAT - COMPREHENSIVE JSON STRUCTURE:
{{
  "executive_summary": {{
    "overall_risk_score": <integer 1-10>,
    "key_findings": ["finding 1", "finding 2", "finding 3"],
    "business_impact": "Critical/High/Medium/Low",
    "recommended_actions": ["immediate action 1", "action 2"],
    "investment_required": "Low/Medium/High",
    "timeline_to_remediate": "30/60/90/180 days"
  }},
  "detailed_findings": {{
    "access_violations": [
      {{
        "violation_type": "Segregation of Duties",
        "severity": "Critical/High/Medium/Low", 
        "description": "detailed description",
        "affected_users": "number or list",
        "business_risk": "impact description",
        "remediation": "specific steps"
      }}
    ],
    "privileged_access_analysis": {{
      "admin_account_count": "number",
      "service_accounts": "analysis",
      "emergency_access": "status",
      "mfa_coverage": "percentage",
      "review_frequency": "assessment"
    }},
    "compliance_gaps": [
      {{
        "control_framework": "SOX/GDPR/HIPAA/etc",
        "control_id": "specific control",
        "gap_description": "what's missing",
        "remediation_effort": "Low/Medium/High",
        "priority": "Critical/High/Medium/Low"
      }}
    ]
  }},
  "risk_matrix": [
    ["Risk Category", "Likelihood", "Impact", "Risk Score", "Priority"],
    ["Unauthorized Access", "High", "Critical", "9", "Immediate"],
    ["Data Exposure", "Medium", "High", "7", "30 days"]
  ],
  "remediation_roadmap": [
    {{
      "phase": "Immediate (0-30 days)",
      "actions": ["action 1", "action 2"],
      "estimated_effort": "person-hours or cost",
      "dependencies": ["dependency 1"]
    }},
    {{
      "phase": "Short-term (30-90 days)", 
      "actions": ["action 1", "action 2"],
      "estimated_effort": "estimate",
      "dependencies": ["dependency 1"]
    }}
  ],
  "technical_recommendations": [
    {{
      "category": "Access Controls",
      "recommendation": "specific technical change",
      "implementation_guide": "step-by-step process",
      "validation_criteria": "how to verify success"
    }}
  ],
  "metrics_dashboard": [
    ["Metric", "Current Value", "Target Value", "Timeline"],
    ["Users with Excessive Access", "25", "0", "60 days"],
    ["Accounts Without MFA", "150", "0", "30 days"]
  ]
}}

CRITICAL INSTRUCTIONS:
- Provide actionable, specific recommendations
- Include quantitative risk assessments where possible  
- Focus on business impact and ROI of security investments
- Address both immediate vulnerabilities and strategic improvements
- Ensure all JSON fields are properly formatted
- Response must be valid JSON only"""

def run_enterprise_analysis(data_summary: str, tasks: List[str], client: OpenAI, model: str, temperature: float, max_tokens: int) -> Optional[Dict]:
    """Run comprehensive enterprise IAM analysis"""
    try:
        prompt = create_enterprise_prompt(data_summary, tasks, "comprehensive")
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a Senior IAM Security Consultant with 15+ years of enterprise experience. You specialize in comprehensive security assessments, compliance frameworks, and risk quantification. Always provide executive-level insights with technical depth. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        raw_content = response.choices[0].message.content
        json_data = safe_json_parse(raw_content)
        
        if not json_data:
            st.error("❌ Failed to parse AI response as JSON")
            with st.expander("🔍 Raw AI Response"):
                st.code(raw_content)
            return None
        
        return json_data
        
    except Exception as e:
        st.error(f"❌ Analysis failed: {str(e)}")
        st.code(traceback.format_exc())
        return None

# ================== ADVANCED VISUALIZATION ==================

def create_enterprise_dashboard(json_data: Dict[str, Any]):
    """Create comprehensive enterprise dashboard"""
    st.subheader("📊 Enterprise Security Dashboard")
    
    try:
        # Executive metrics row
        exec_summary = json_data.get("executive_summary", {})
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            risk_score = exec_summary.get("overall_risk_score", 0)
            st.metric(
                "🎯 Overall Risk Score",
                f"{risk_score}/10",
                delta=f"Target: ≤3",
                delta_color="inverse"
            )
        
        with col2:
            investment = exec_summary.get("investment_required", "Unknown")
            st.metric("💰 Investment Level", investment)
        
        with col3:
            timeline = exec_summary.get("timeline_to_remediate", "Unknown")
            st.metric("⏱️ Remediation Timeline", timeline)
        
        with col4:
            business_impact = exec_summary.get("business_impact", "Unknown")
            color = "🔴" if business_impact == "Critical" else "🟡" if business_impact == "High" else "🟢"
            st.metric("📈 Business Impact", f"{color} {business_impact}")
        
        # Risk Matrix Heatmap
        st.subheader("🔥 Risk Heat Matrix")
        risk_matrix = json_data.get("risk_matrix", [])
        
        if risk_matrix and len(risk_matrix) > 1:
            df_risk = pd.DataFrame(risk_matrix[1:], columns=risk_matrix[0])
            
            if PLOTLY_AVAILABLE and "Risk Score" in df_risk.columns:
                df_risk["Risk Score"] = pd.to_numeric(df_risk["Risk Score"], errors='coerce')
                
                fig = px.scatter(
                    df_risk,
                    x="Likelihood" if "Likelihood" in df_risk.columns else df_risk.columns[1],
                    y="Impact" if "Impact" in df_risk.columns else df_risk.columns[2],
                    size="Risk Score",
                    color="Risk Score",
                    hover_name="Risk Category" if "Risk Category" in df_risk.columns else df_risk.columns[0],
                    title="Risk Assessment Matrix",
                    color_continuous_scale="Reds"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(df_risk, use_container_width=True)
        
        # Metrics Dashboard
        metrics = json_data.get("metrics_dashboard", [])
        if metrics and len(metrics) > 1:
            st.subheader("📈 Key Performance Indicators")
            df_metrics = pd.DataFrame(metrics[1:], columns=metrics[0])
            
            # Create progress bars for metrics
            for _, row in df_metrics.iterrows():
                metric_name = row.iloc[0]
                current = row.iloc[1]
                target = row.iloc[2]
                timeline = row.iloc[3] if len(row) > 3 else "TBD"
                
                try:
                    current_num = float(str(current).replace(',', ''))
                    target_num = float(str(target).replace(',', ''))
                    
                    if target_num > 0:
                        progress = max(0, min(100, (1 - current_num/target_num) * 100))
                    else:
                        progress = 100 if current_num <= target_num else 0
                    
                    st.markdown(f"**{metric_name}**")
                    st.progress(progress / 100)
                    st.markdown(f"Current: {current} | Target: {target} | Timeline: {timeline}")
                    
                except:
                    st.markdown(f"**{metric_name}**: {current} → {target} ({timeline})")
        
        # Remediation Timeline
        roadmap = json_data.get("remediation_roadmap", [])
        if roadmap:
            st.subheader("🗺️ Remediation Roadmap")
            
            for phase in roadmap:
                phase_name = phase.get("phase", "Unknown Phase")
                actions = phase.get("actions", [])
                effort = phase.get("estimated_effort", "TBD")
                
                with st.expander(f"📅 {phase_name}"):
                    st.markdown(f"**Estimated Effort:** {effort}")
                    st.markdown("**Actions:**")
                    for action in actions:
                        st.markdown(f"• {action}")
                    
                    if "dependencies" in phase:
                        st.markdown("**Dependencies:**")
                        for dep in phase["dependencies"]:
                            st.markdown(f"⚠️ {dep}")
    
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        st.write("Available data keys:", list(json_data.keys()))

# ================== ENHANCED EXPORT FUNCTIONS ==================

def create_comprehensive_exports(json_data: Dict[str, Any], data_summary: str):
    """Create multiple export formats"""
    st.subheader("📥 Enterprise Export Options")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Executive Summary PDF-style text
        exec_report = create_executive_report(json_data, timestamp)
        st.download_button(
            label="📋 Executive Summary",
            data=exec_report,
            file_name=f"IAM_Executive_Report_{timestamp}.txt",
            mime="text/plain",
            help="High-level executive summary for leadership"
        )
    
    with col2:
        # Technical JSON
        technical_json = json.dumps(json_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="🔧 Technical Analysis",
            data=technical_json,
            file_name=f"IAM_Technical_Analysis_{timestamp}.json",
            mime="application/json",
            help="Complete technical findings in JSON format"
        )
    
    with col3:
        # Risk Matrix CSV
        if "risk_matrix" in json_data:
            risk_csv = create_risk_matrix_csv(json_data["risk_matrix"])
            st.download_button(
                label="📊 Risk Matrix CSV",
                data=risk_csv,
                file_name=f"IAM_Risk_Matrix_{timestamp}.csv",
                mime="text/csv",
                help="Risk assessment data for further analysis"
            )
    
    with col4:
        # Remediation Plan
        remediation_plan = create_remediation_plan(json_data, timestamp)
        st.download_button(
            label="🗓️ Action Plan",
            data=remediation_plan,
            file_name=f"IAM_Remediation_Plan_{timestamp}.txt",
            mime="text/plain",
            help="Detailed implementation roadmap"
        )

def create_executive_report(json_data: Dict[str, Any], timestamp: str) -> str:
    """Generate executive summary report"""
    exec_summary = json_data.get("executive_summary", {})
    
    report = f"""
IAM SECURITY ASSESSMENT - EXECUTIVE SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Report ID: IAM-{timestamp}

═══════════════════════════════════════════════════════════════════

EXECUTIVE OVERVIEW

Overall Risk Score: {exec_summary.get('overall_risk_score', 'N/A')}/10
Business Impact: {exec_summary.get('business_impact', 'N/A')}
Investment Required: {exec_summary.get('investment_required', 'N/A')}
Timeline to Remediate: {exec_summary.get('timeline_to_remediate', 'N/A')}

KEY FINDINGS:
{chr(10).join(f"• {finding}" for finding in exec_summary.get('key_findings', []))}

IMMEDIATE ACTIONS REQUIRED:
{chr(10).join(f"• {action}" for action in exec_summary.get('recommended_actions', []))}

═══════════════════════════════════════════════════════════════════

DETAILED ANALYSIS SUMMARY

"""
    
    # Add detailed findings
    detailed = json_data.get("detailed_findings", {})
    
    if "access_violations" in detailed:
        report += "\nACCESS VIOLATIONS:\n"
        for violation in detailed["access_violations"]:
            report += f"• {violation.get('violation_type', 'Unknown')}: {violation.get('severity', 'N/A')} - {violation.get('description', 'No description')}\n"
    
    if "compliance_gaps" in detailed:
        report += "\nCOMPLIANCE GAPS:\n"
        for gap in detailed["compliance_gaps"]:
            report += f"• {gap.get('control_framework', 'Unknown Framework')}: {gap.get('gap_description', 'No description')}\n"
    
    # Add technical recommendations
    tech_recs = json_data.get("technical_recommendations", [])
    if tech_recs:
        report += "\nTECHNICAL RECOMMENDATIONS:\n"
        for rec in tech_recs:
            report += f"• {rec.get('category', 'General')}: {rec.get('recommendation', 'No recommendation')}\n"
    
    report += f"""
═══════════════════════════════════════════════════════════════════

This assessment was conducted using AI-powered analysis of your IAM data.
For questions or clarification, contact your security team.

Report generated by IAM Analyzer v5 Enterprise Edition
"""
    
    return report

def create_risk_matrix_csv(risk_matrix: List) -> str:
    """Convert risk matrix to CSV format"""
    if not risk_matrix or len(risk_matrix) <= 1:
        return "No risk matrix data available"
    
    df = pd.DataFrame(risk_matrix[1:], columns=risk_matrix[0])
    return df.to_csv(index=False)

def create_remediation_plan(json_data: Dict[str, Any], timestamp: str) -> str:
    """Generate detailed remediation plan"""
    
    plan = f"""
IAM SECURITY REMEDIATION PLAN
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Plan ID: REMED-{timestamp}

═══════════════════════════════════════════════════════════════════

IMPLEMENTATION ROADMAP

"""
    
    roadmap = json_data.get("remediation_roadmap", [])
    
    for i, phase in enumerate(roadmap, 1):
        plan += f"\nPHASE {i}: {phase.get('phase', 'Unknown Phase')}\n"
        plan += f"Estimated Effort: {phase.get('estimated_effort', 'TBD')}\n"
        
        plan += "\nActions:\n"
        for action in phase.get("actions", []):
            plan += f"□ {action}\n"
        
        if "dependencies" in phase:
            plan += "\nDependencies:\n"
            for dep in phase["dependencies"]:
                plan += f"⚠ {dep}\n"
        
        plan += "\n" + "─" * 50 + "\n"
    
    # Add technical implementation guides
    tech_recs = json_data.get("technical_recommendations", [])
    if tech_recs:
        plan += "\nTECHNICAL IMPLEMENTATION GUIDES:\n\n"
        
        for rec in tech_recs:
            plan += f"Category: {rec.get('category', 'General')}\n"
            plan += f"Recommendation: {rec.get('recommendation', 'N/A')}\n"
            plan += f"Implementation: {rec.get('implementation_guide', 'See technical team')}\n"
            plan += f"Validation: {rec.get('validation_criteria', 'TBD')}\n"
            plan += "\n" + "─" * 30 + "\n"
    
    return plan

# ================== MAIN APPLICATION ==================

def main():
    """Main application logic"""
    initialize_session_state()
    
    # Authentication check
    if not check_authentication():
        return
    
    # Capability warnings
    missing_capabilities = []
    if not PLOTLY_AVAILABLE:
        missing_capabilities.append("plotly (enhanced charts)")
    if not DOCX_AVAILABLE:
        missing_capabilities.append("python-docx (Word documents)")
    if not PPTX_AVAILABLE:
        missing_capabilities.append("python-pptx (PowerPoint)")
    if not OCR_AVAILABLE:
        missing_capabilities.append("pytesseract (image OCR)")
    
    if missing_capabilities:
        st.info(f"💡 Install these packages for full functionality: {', '.join(missing_capabilities)}")
    
    # Setup sidebar
    api_config = setup_sidebar_v5()
    if not all(api_config):
        st.warning("⚠️ Please configure your OpenAI API key to continue.")
        st.stop()
    
    api_key, model, temperature, max_tokens = api_config
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=api_key)
        client.models.list()
    except Exception as e:
        st.error(f"❌ Failed to connect to OpenAI: {str(e)}")
        st.stop()
    
    # Main interface
    st.title("🔐 IAM Analyzer v5 Enterprise Edition")
    st.markdown("**🚀 Multi-Format Analysis + Enterprise Reporting**")
    
    # File upload with enhanced support
    st.subheader("📂 Upload Enterprise Data")
    st.markdown(f"**Supported formats:** {', '.join(SUPPORTED_FILE_TYPES)}")
    
    uploaded_files = st.file_uploader(
        "Upload your IAM data files:",
        type=SUPPORTED_FILE_TYPES,
        accept_multiple_files=True,
        help=f"Maximum file size: {MAX_FILE_SIZE // (1024*1024)}MB per file. Supports documents, spreadsheets, presentations, images, and more!"
    )
    
    if not uploaded_files:
        st.info("👆 Upload files to begin comprehensive analysis")
        
        # Show previous analyses
        if st.session_state["history"]:
            st.subheader("📚 Previous Enterprise Analyses")
            for i, entry in enumerate(st.session_state["history"][-3:][::-1]):
                with st.expander(f"📋 Analysis {len(st.session_state['history'])-i} - {entry['timestamp']}"):
                    if "executive_summary" in entry["output"]:
                        exec_sum = entry["output"]["executive_summary"]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Risk Score", f"{exec_sum.get('overall_risk_score', 0)}/10")
                        with col2:
                            st.metric("Business Impact", exec_sum.get('business_impact', 'N/A'))
                        
                        st.markdown("**Key Findings:**")
                        for finding in exec_sum.get('key_findings', [])[:3]:
                            st.markdown(f"• {finding}")
        return
    
    # Load files with progress tracking
    st.subheader("🔄 Processing Files")
    all_data = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Processing {file.name}...")
        
        if not validate_file_size(file):
            st.error(f"❌ {file.name} exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit")
            continue
        
        file_type = file.name.split('.')[-1].lower()
        if file_type not in SUPPORTED_FILE_TYPES:
            st.warning(f"⚠️ Unsupported file type: {file.name}")
            continue
        
        file_content = file.read()
        df = load_file_content_v5(file_content, file.name, file_type)
        
        if df is not None:
            all_data[file.name] = df
            st.success(f"✅ Processed {file.name} ({df.shape[0]} records)")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.empty()
    status_text.empty()
    
    if not all_data:
        st.error("❌ No files could be processed. Please check file formats.")
        return
    
    # Generate enhanced summary
    data_summary = generate_enhanced_summary(all_data)
    
    # Data overview
    st.subheader("📋 Enterprise Data Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📁 Files Processed", len(all_data))
    with col2:
        total_records = sum(df.shape[0] for df in all_data.values())
        st.metric("📊 Total Records", f"{total_records:,}")
    with col3:
        file_types = set(f.split('.')[-1].upper() for f in all_data.keys())
        st.metric("📄 File Types", len(file_types))
    with col4:
        total_size = sum(df.memory_usage(deep=True).sum() for df in all_data.values())
        st.metric("💾 Data Size", f"{total_size // 1024:,} KB")
    
    # Data preview
    with st.expander("🔍 Data Preview"):
        for name, df in all_data.items():
            st.markdown(f"**📁 {name}**")
            st.dataframe(df.head(2), use_container_width=True)
    
    # Enhanced task selection
    st.subheader("🎯 Enterprise Analysis Scope")
    
    task_categories = {
        "🚨 Critical Security": [
            "Detect Segregation of Duties violations",
            "Identify privilege escalation paths", 
            "Analyze emergency access procedures",
            "Review administrative account security"
        ],
        "👥 Access Management": [
            "Identify orphaned and inactive accounts",
            "Analyze role-based access patterns",
            "Review guest and contractor access",
            "Assess shared account usage"
        ],
        "📊 Compliance & Governance": [
            "SOX compliance assessment",
            "GDPR privacy impact analysis", 
            "Audit trail completeness review",
            "Access certification gaps"
        ],
        "🔍 Advanced Analytics": [
            "Behavioral access pattern analysis",
            "Cross-system entitlement mining",
            "Risk-based access scoring",
            "Anomaly detection assessment"
        ]
    }
    
    selected_tasks = []
    
    for category, tasks in task_categories.items():
        st.markdown(f"**{category}**")
        cols = st.columns(2)
        for i, task in enumerate(tasks):
            with cols[i % 2]:
                if st.checkbox(task, key=f"{category}_{task}"):
                    selected_tasks.append(task)
    
    if not selected_tasks:
        st.warning("⚠️ Please select at least one analysis task.")
        return
    
    # Analysis execution
    if st.button("🚀 Run Enterprise Security Analysis", type="primary", use_container_width=True):
        
        with st.spinner("🤖 Conducting comprehensive IAM security assessment... This may take several minutes."):
            
            # Add analysis type indicator
            progress_cols = st.columns(3)
            with progress_cols[0]:
                st.info("🔍 Processing data sources...")
            with progress_cols[1]:
                st.info("🧠 Running AI analysis...")
            with progress_cols[2]:
                st.info("📊 Generating reports...")
            
            analysis_result = run_enterprise_analysis(
                data_summary, selected_tasks, client, model, temperature, max_tokens
            )
        
        if analysis_result:
            # Store in history
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "input_summary": data_summary,
                "output": analysis_result,
                "tasks": selected_tasks,
                "analysis_type": "Enterprise v5"
            }
            st.session_state["history"].append(entry)
            
            st.success("✅ Enterprise Analysis Complete!")
            
            # Display results
            exec_summary = analysis_result.get("executive_summary", {})
            
            # Executive metrics
            st.subheader("🎯 Executive Summary")
            metric_cols = st.columns(4)
            
            with metric_cols[0]:
                risk_score = exec_summary.get("overall_risk_score", 0)
                risk_color = "🔴" if risk_score >= 8 else "🟡" if risk_score >= 5 else "🟢"
                st.metric("Risk Score", f"{risk_color} {risk_score}/10")
            
            with metric_cols[1]:
                st.metric("Business Impact", exec_summary.get("business_impact", "N/A"))
            
            with metric_cols[2]:
                st.metric("Investment Required", exec_summary.get("investment_required", "N/A"))
            
            with metric_cols[3]:
                st.metric("Timeline", exec_summary.get("timeline_to_remediate", "N/A"))
            
            # Key findings
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🔍 Key Findings")
                for finding in exec_summary.get("key_findings", []):
                    st.warning(f"• {finding}")
            
            with col2:
                st.subheader("✅ Recommended Actions") 
                for action in exec_summary.get("recommended_actions", []):
                    st.success(f"• {action}")
            
            # Enterprise dashboard
            create_enterprise_dashboard(analysis_result)
            
            # Export options
            create_comprehensive_exports(analysis_result, data_summary)
            
        else:
            st.error("❌ Enterprise analysis failed. Please check your data and try again.")

if __name__ == "__main__":
    main()
