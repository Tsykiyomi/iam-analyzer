#!/usr/bin/env python3
"""
IAM Analyzer v4 - Enhanced Security, Performance & UX
Complete rewrite with modular design, proper error handling, and modern OpenAI API
"""

import streamlit as st
import pandas as pd
import io
import json
import traceback
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
import os
from typing import Dict, List, Tuple, Optional, Any
from openai import OpenAI
import openai

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="IAM Analyzer v4", 
    layout="wide",
    page_icon="🔐",
    initial_sidebar_state="expanded"
)

# Constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
SUPPORTED_MODELS = ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
RISK_COLORS = {"Low": "#28a745", "Medium": "#ffc107", "High": "#dc3545"}

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
        # Find JSON block in response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return None

# ================== CACHING FUNCTIONS ==================

@st.cache_data
def load_file_content(file_content: bytes, file_name: str, file_type: str) -> Optional[pd.DataFrame]:
    """Load and cache file content"""
    try:
        if file_type == "csv":
            return pd.read_csv(io.BytesIO(file_content))
        elif file_type in ["xlsx", "xls"]:
            return pd.read_excel(io.BytesIO(file_content))
        elif file_type == "txt":
            content = file_content.decode("utf-8")
            return pd.DataFrame({"Text": [content]})
    except Exception as e:
        st.error(f"Error loading {file_name}: {str(e)}")
        return None
    return None

@st.cache_data
def generate_data_summary(all_data: Dict[str, pd.DataFrame]) -> str:
    """Generate and cache data summary"""
    summary = []
    for name, df in all_data.items():
        summary.append(f"📁 File: {name}")
        summary.append(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
        summary.append(f"   Columns: {', '.join(df.columns[:10])}")
        if len(df.columns) > 10:
            summary.append(f"   (+ {len(df.columns) - 10} more columns)")
        
        # Show sample data (first 2 rows, first 5 columns)
        sample_df = df.head(2).iloc[:, :5]
        summary.append(f"   Sample data:")
        summary.append(f"   {sample_df.to_string(index=False)}")
        summary.append("   " + "─" * 50)
    
    return "\n".join(summary)

# ================== CORE FUNCTIONS ==================

def initialize_session_state():
    """Initialize all session state variables"""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    if "chat_log" not in st.session_state:
        st.session_state["chat_log"] = []
    if "analysis_count" not in st.session_state:
        st.session_state["analysis_count"] = 0

def setup_sidebar() -> Tuple[str, str, float, int]:
    """Setup sidebar with API configuration and settings"""
    st.sidebar.title("🔐 IAM AI Analyzer v4")
    st.sidebar.markdown("*Enhanced Security & Performance*")
    
    # API Configuration
    st.sidebar.subheader("⚙️ AI Configuration")
    api_key = st.sidebar.text_input(
        "OpenAI API Key:", 
        type="password",
        help="Your API key is kept secure and only used for this session"
    )
    
    if api_key and not validate_api_key(api_key):
        st.sidebar.error("❌ Invalid API key format")
        return None, None, None, None
    
    # Advanced settings
    with st.sidebar.expander("🎛️ Advanced Settings"):
        model = st.selectbox("AI Model:", SUPPORTED_MODELS, index=0)
        temperature = st.slider("Creativity Level:", 0.0, 1.0, 0.3, 0.1)
        max_tokens = st.slider("Response Length:", 500, 3000, 1500, 100)
    
    return api_key, model, temperature, max_tokens

def load_uploaded_files(uploaded_files) -> Dict[str, pd.DataFrame]:
    """Load and validate uploaded files"""
    all_data = {}
    
    if not uploaded_files:
        return all_data
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, file in enumerate(uploaded_files):
        status_text.text(f"Loading {file.name}...")
        
        # Validate file size
        if not validate_file_size(file):
            st.error(f"❌ {file.name} is too large (max {MAX_FILE_SIZE // (1024*1024)}MB)")
            continue
        
        # Get file type
        file_type = file.name.split('.')[-1].lower()
        if file_type not in ["csv", "xlsx", "xls", "txt"]:
            st.warning(f"⚠️ Unsupported file type: {file.name}")
            continue
        
        # Load file content
        file_content = file.read()
        df = load_file_content(file_content, file.name, file_type)
        
        if df is not None:
            all_data[file.name] = df
            st.success(f"✅ Loaded {file.name} ({df.shape[0]} rows)")
        
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.empty()
    status_text.empty()
    
    return all_data

def create_analysis_prompt(data_summary: str, tasks: List[str]) -> str:
    """Create structured prompt for AI analysis"""
    return f"""You are an expert IAM (Identity and Access Management) governance analyst. 

TASK: Analyze the provided IAM data and complete these specific security assessments:
{chr(10).join(f"• {task}" for task in tasks)}

IAM DATA SUMMARY:
{data_summary}

ANALYSIS REQUIREMENTS:
1. Focus on actionable security insights
2. Identify specific compliance violations
3. Provide concrete remediation steps
4. Assess risk levels based on industry standards

OUTPUT FORMAT (valid JSON only):
{{
  "summary": "Brief 2-3 sentence executive summary of key findings",
  "risk_score": <integer from 1-10, where 10 is highest risk>,
  "violations": [
    "Specific violation description 1",
    "Specific violation description 2"
  ],
  "recommendations": [
    "Actionable recommendation 1 with timeline",
    "Actionable recommendation 2 with priority"
  ],
  "risk_distribution": [
    ["Entity", "RiskLevel", "Count"],
    ["Admin Accounts", "High", "5"],
    ["Service Accounts", "Medium", "12"],
    ["User Accounts", "Low", "150"]
  ],
  "compliance_status": [
    ["Control", "Status", "Gap"],
    ["Segregation of Duties", "Non-Compliant", "3 violations found"],
    ["Privileged Access", "Partially Compliant", "Missing MFA on 2 accounts"]
  ]
}}

Ensure all JSON fields are properly formatted and the response contains only valid JSON."""

def run_gpt_analysis(data_summary: str, tasks: List[str], client: OpenAI, model: str, temperature: float, max_tokens: int) -> Optional[Dict]:
    """Run GPT analysis with comprehensive error handling"""
    try:
        prompt = create_analysis_prompt(data_summary, tasks)
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a cybersecurity and identity governance expert specializing in IAM analysis. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        raw_content = response.choices[0].message.content
        json_data = safe_json_parse(raw_content)
        
        if not json_data:
            st.error("❌ Failed to parse AI response as JSON")
            st.code(raw_content)
            return None
            
        # Validate required fields
        required_fields = ["summary", "risk_score", "violations", "recommendations"]
        missing_fields = [field for field in required_fields if field not in json_data]
        
        if missing_fields:
            st.warning(f"⚠️ Missing fields in response: {', '.join(missing_fields)}")
        
        return json_data
        
    except openai.APIError as e:
        st.error(f"❌ OpenAI API Error: {str(e)}")
    except openai.RateLimitError:
        st.error("❌ Rate limit exceeded. Please wait and try again.")
    except openai.AuthenticationError:
        st.error("❌ Invalid API key. Please check your OpenAI API key.")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        st.code(traceback.format_exc())
    
    return None

def create_risk_dashboard(json_data: Dict[str, Any]):
    """Create interactive risk visualization dashboard"""
    st.subheader("📊 Interactive Risk Dashboard")
    
    # Risk Score Gauge
    risk_score = json_data.get("risk_score", 0)
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Risk gauge
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = risk_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Overall Risk Score"},
            delta = {'reference': 5},
            gauge = {
                'axis': {'range': [None, 10]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 3], 'color': "lightgreen"},
                    {'range': [3, 7], 'color': "yellow"},
                    {'range': [7, 10], 'color': "lightcoral"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 8
                }
            }
        ))
        fig_gauge.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
    
    with col2:
        # Risk distribution chart
        dist = json_data.get("risk_distribution", [])
        if dist and len(dist) > 1:
            df_dist = pd.DataFrame(dist[1:], columns=dist[0])
            if "Count" in df_dist.columns:
                df_dist["Count"] = pd.to_numeric(df_dist["Count"], errors='coerce')
            
            fig_bar = px.bar(
                df_dist, 
                x="Entity" if "Entity" in df_dist.columns else df_dist.columns[0],
                y="Count" if "Count" in df_dist.columns else None,
                color="RiskLevel" if "RiskLevel" in df_dist.columns else None,
                title="Risk Distribution by Entity Type",
                color_discrete_map=RISK_COLORS
            )
            fig_bar.update_layout(height=300, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_bar, use_container_width=True)
    
    # Compliance status table
    compliance = json_data.get("compliance_status", [])
    if compliance and len(compliance) > 1:
        st.subheader("🛡️ Compliance Status")
        df_compliance = pd.DataFrame(compliance[1:], columns=compliance[0])
        
        # Style the dataframe
        def color_status(val):
            if val == "Compliant":
                return "background-color: #d4edda"
            elif val == "Non-Compliant":
                return "background-color: #f8d7da"
            elif val == "Partially Compliant":
                return "background-color: #fff3cd"
            return ""
        
        styled_df = df_compliance.style.applymap(color_status, subset=["Status"])
        st.dataframe(styled_df, use_container_width=True)

def create_export_options(json_data: Dict[str, Any]):
    """Create download options for analysis results"""
    st.subheader("📥 Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # JSON export
        json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
        st.download_button(
            label="📋 Download JSON Report",
            data=json_str,
            file_name=f"iam_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col2:
        # Executive summary export
        summary_text = f"""IAM ANALYSIS EXECUTIVE SUMMARY
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RISK SCORE: {json_data.get('risk_score', 'N/A')}/10

SUMMARY:
{json_data.get('summary', 'No summary available')}

VIOLATIONS:
{chr(10).join(f"• {v}" for v in json_data.get('violations', []))}

RECOMMENDATIONS:
{chr(10).join(f"• {r}" for r in json_data.get('recommendations', []))}
"""
        st.download_button(
            label="📄 Download Summary",
            data=summary_text,
            file_name=f"iam_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    with col3:
        # CSV export for compliance data
        compliance = json_data.get("compliance_status", [])
        if compliance and len(compliance) > 1:
            df_compliance = pd.DataFrame(compliance[1:], columns=compliance[0])
            csv = df_compliance.to_csv(index=False)
            st.download_button(
                label="📊 Download CSV",
                data=csv,
                file_name=f"iam_compliance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

def run_chat_interface(data_summary: str, client: OpenAI, model: str):
    """Enhanced chat interface for IAM questions"""
    st.sidebar.subheader("💬 AI Assistant Chat")
    st.sidebar.markdown("*Ask questions about your current data*")
    
    user_msg = st.sidebar.text_area(
        "Your question:", 
        height=100,
        placeholder="e.g., 'Which users have admin access?' or 'What are the biggest security risks?'"
    )
    
    if st.sidebar.button("🤔 Ask AI", type="primary"):
        if user_msg and client:
            with st.sidebar.spinner("🧠 Analyzing..."):
                try:
                    chat_prompt = f"""You are an IAM security expert assistant. Based on the following IAM data summary, answer the user's question with specific, actionable insights.

IAM DATA CONTEXT:
{data_summary}

USER QUESTION: {user_msg}

Provide a clear, concise answer focused on security implications and actionable recommendations. If the data doesn't contain enough information to answer fully, explain what additional data would be needed."""

                    response = client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": "You are an expert IAM security consultant. Provide practical, actionable advice."},
                            {"role": "user", "content": chat_prompt}
                        ],
                        temperature=0.2,
                        max_tokens=1000
                    )
                    
                    response_text = response.choices[0].message.content
                    timestamp = datetime.now().strftime("%H:%M")
                    st.session_state["chat_log"].append((user_msg, response_text, timestamp))
                    
                except Exception as e:
                    st.sidebar.error(f"Chat error: {str(e)}")
    
    # Display chat history
    if st.session_state["chat_log"]:
        st.sidebar.markdown("### 💭 Recent Conversations")
        
        # Show last 3 conversations
        for i, (q, a, time) in enumerate(st.session_state["chat_log"][-3:][::-1]):
            with st.sidebar.expander(f"🕒 {time} - Q{len(st.session_state['chat_log'])-i}"):
                st.markdown(f"**Q:** {q}")
                st.markdown(f"**A:** {a}")
        
        if st.sidebar.button("🗑️ Clear Chat History"):
            st.session_state["chat_log"] = []
            st.experimental_rerun()

def display_analysis_history():
    """Display previous analysis results"""
    if st.session_state["history"]:
        st.subheader("📚 Analysis History")
        
        # Show statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Analyses", len(st.session_state["history"]))
        with col2:
            avg_risk = sum(entry["output"].get("risk_score", 0) for entry in st.session_state["history"]) / len(st.session_state["history"])
            st.metric("Average Risk Score", f"{avg_risk:.1f}")
        with col3:
            latest_risk = st.session_state["history"][-1]["output"].get("risk_score", 0)
            st.metric("Latest Risk Score", latest_risk)
        
        # Show recent analyses
        for i, entry in enumerate(st.session_state["history"][-3:][::-1]):
            with st.expander(f"📋 Analysis {len(st.session_state['history'])-i} - {entry['timestamp']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Summary:** {entry['output'].get('summary', 'No summary')}")
                with col2:
                    st.metric("Risk Score", f"{entry['output'].get('risk_score', 0)}/10")
                
                if entry['output'].get('violations'):
                    st.markdown("**Key Violations:**")
                    for violation in entry['output']['violations'][:3]:
                        st.markdown(f"• {violation}")

# ================== MAIN APPLICATION ==================

def main():
    """Main application logic"""
    # Initialize session state
    initialize_session_state()
    
    # Setup sidebar and get configuration
    api_config = setup_sidebar()
    if not all(api_config):
        st.warning("⚠️ Please configure your OpenAI API key in the sidebar to continue.")
        st.stop()
    
    api_key, model, temperature, max_tokens = api_config
    
    # Initialize OpenAI client
    try:
        client = OpenAI(api_key=api_key)
        # Test the connection
        client.models.list()
    except Exception as e:
        st.error(f"❌ Failed to connect to OpenAI: {str(e)}")
        st.stop()
    
    # Main title and description
    st.title("🔐 IAM Analyzer v4")
    st.markdown("**Enhanced Security Analysis with AI-Powered Insights**")
    st.markdown("---")
    
    # File upload section
    st.subheader("📂 Upload IAM Data")
    uploaded_files = st.file_uploader(
        "Upload your IAM data files (CSV, Excel, TXT):",
        type=["csv", "xlsx", "xls", "txt"],
        accept_multiple_files=True,
        help=f"Maximum file size: {MAX_FILE_SIZE // (1024*1024)}MB per file"
    )
    
    if not uploaded_files:
        st.info("👆 Upload at least one file to begin analysis")
        
        # Show analysis history even without files
        display_analysis_history()
        return
    
    # Load and validate files
    all_data = load_uploaded_files(uploaded_files)
    
    if not all_data:
        st.error("❌ No usable files were loaded. Please check your file formats and try again.")
        return
    
    # Generate data summary
    data_summary = generate_data_summary(all_data)
    
    # Display data preview
    st.subheader("📋 Data Overview")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with st.expander("🔍 Data Preview", expanded=False):
            for name, df in all_data.items():
                st.markdown(f"**📁 {name}**")
                st.markdown(f"*{df.shape[0]} rows × {df.shape[1]} columns*")
                st.dataframe(df.head(3), use_container_width=True)
                st.markdown("---")
    
    with col2:
        st.metric("Total Files", len(all_data))
        total_rows = sum(df.shape[0] for df in all_data.values())
        st.metric("Total Records", total_rows)
        total_columns = sum(df.shape[1] for df in all_data.values())
        st.metric("Total Fields", total_columns)
    
    # Task selection
    st.subheader("🎯 Analysis Tasks")
    task_options = [
        "🚨 Detect Segregation of Duties violations",
        "👤 Identify orphaned and inactive accounts",
        "🔑 Analyze privileged access patterns",
        "🧹 Suggest entitlement cleanup opportunities",
        "📊 Generate compliance risk dashboard",
        "⚠️ Identify high-risk access combinations",
        "🔄 Review access certification gaps",
        "🌐 Analyze cross-system access patterns"
    ]
    
    selected_tasks = st.multiselect(
        "Select analysis tasks to perform:",
        task_options,
        default=task_options[:3],
        help="Choose specific security assessments to run on your data"
    )
    
    if not selected_tasks:
        st.warning("⚠️ Please select at least one analysis task.")
        return
    
    # Run analysis
    if st.button("🚀 Run AI Security Analysis", type="primary", use_container_width=True):
        if not selected_tasks:
            st.error("Please select at least one analysis task.")
            return
        
        with st.spinner("🤖 AI is analyzing your IAM data... This may take a moment."):
            json_data = run_gpt_analysis(
                data_summary, selected_tasks, client, model, temperature, max_tokens
            )
        
        if json_data:
            # Store analysis in history
            entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "input_summary": data_summary,
                "output": json_data,
                "tasks": selected_tasks
            }
            st.session_state["history"].append(entry)
            st.session_state["analysis_count"] += 1
            
            st.success("✅ Analysis Complete!")
            
            # Display results
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🎯 Risk Score", f"{json_data.get('risk_score', 0)}/10")
            with col2:
                st.metric("🚨 Violations Found", len(json_data.get('violations', [])))
            with col3:
                st.metric("✅ Recommendations", len(json_data.get('recommendations', [])))
            
            # Executive summary
            st.subheader("📋 Executive Summary")
            st.info(json_data.get("summary", "No summary available"))
            
            # Violations and recommendations
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🚨 Security Violations")
                violations = json_data.get("violations", [])
                if violations:
                    for i, violation in enumerate(violations, 1):
                        st.error(f"**{i}.** {violation}")
                else:
                    st.success("No violations detected!")
            
            with col2:
                st.subheader("✅ Recommendations")
                recommendations = json_data.get("recommendations", [])
                if recommendations:
                    for i, rec in enumerate(recommendations, 1):
                        st.success(f"**{i}.** {rec}")
                else:
                    st.info("No specific recommendations at this time.")
            
            # Risk dashboard
            create_risk_dashboard(json_data)
            
            # Export options
            create_export_options(json_data)
            
        else:
            st.error("❌ Analysis failed. Please check your data and try again.")
    
    # Chat interface
    run_chat_interface(data_summary, client, model)
    
    # Analysis history
    display_analysis_history()

if __name__ == "__main__":
    main()
