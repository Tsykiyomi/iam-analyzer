#!/usr/bin/env python3
"""
Simple IAM Analyzer - One Page Version
Avoids complex step transitions that cause issues
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
from pathlib import Path
from datetime import datetime
import json
import re
import time
import traceback

# File processing imports
import openpyxl
from openpyxl.styles import PatternFill, Font
from openpyxl.utils.dataframe import dataframe_to_rows

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()

# Configuration
st.set_page_config(
    page_title="Simple IAM Analyzer",
    page_icon="🔐",
    layout="wide"
)

def check_password():
    """Simple password protection"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔐 IAM Analysis Tool")
        password = st.text_input("Enter password:", type="password")
        
        if st.button("Login"):
            if password == st.secrets.get("app_password", "demo123"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Wrong password")
        
        st.info("💡 **Default password:** demo123")
        return False
    return True

def get_openai_client():
    """Get OpenAI client with error handling"""
    try:
        # Try to get API key from secrets first
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        
        if not api_key:
            # Ask user for input
            api_key = st.sidebar.text_input(
                "OpenAI API Key",
                type="password",
                help="Get your API key from https://platform.openai.com/api-keys"
            )
        
        if not api_key:
            return None, "No API key provided"
        
        # Test the client
        client = openai.OpenAI(api_key=api_key)
        
        # Quick test
        test_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        
        return client, None
        
    except Exception as e:
        return None, str(e)

def process_file(uploaded_file):
    """Process a single uploaded file"""
    try:
        file_ext = Path(uploaded_file.name).suffix.lower()
        file_bytes = uploaded_file.read()
        
        if file_ext in ['.xlsx', '.xls']:
            # Excel processing
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            data = {}
            for sheet_name in excel_file.sheet_names[:5]:  # Limit sheets
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, nrows=1000)
                    if not df.empty:
                        df.columns = [str(col).strip() for col in df.columns]
                        data[f"{uploaded_file.name}_{sheet_name}"] = df
                except:
                    continue
            return data
            
        elif file_ext == '.csv':
            # CSV processing
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                for sep in [',', ';', '\t']:
                    try:
                        df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, sep=sep, nrows=1000)
                        if len(df.columns) > 1:
                            df.columns = [str(col).strip() for col in df.columns]
                            return {uploaded_file.name: df}
                    except:
                        continue
            return {}
            
        elif file_ext == '.txt':
            # Text processing
            try:
                text = file_bytes.decode('utf-8')
                return {uploaded_file.name: {'text': text[:5000]}}
            except:
                return {}
                
        else:
            return {uploaded_file.name: {'error': f'Unsupported format: {file_ext}'}}
            
    except Exception as e:
        return {uploaded_file.name: {'error': str(e)}}

def analyze_with_ai(client, data_summary, context="General IAM analysis"):
    """Simple AI analysis function"""
    try:
        prompt = f"""
        Analyze this IAM data and provide insights in JSON format.
        
        Context: {context}
        
        Data:
        {data_summary}
        
        Provide response as JSON:
        {{
            "summary": "Brief overall assessment",
            "findings": [
                {{
                    "type": "SoD|Access|Policy",
                    "severity": "High|Medium|Low", 
                    "description": "What was found",
                    "recommendation": "What to do about it"
                }}
            ],
            "recommendations": [
                "Key recommendation 1",
                "Key recommendation 2"
            ],
            "risk_score": 0-10
        }}
        """
        
        st.write("🔄 Sending request to OpenAI...")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an IAM security expert. Respond only with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        st.write("✅ Got response from OpenAI")
        
        # Extract JSON
        response_text = response.choices[0].message.content
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end != 0:
            json_text = response_text[start:end]
            result = json.loads(json_text)
            st.write("✅ Successfully parsed JSON")
            return result
        else:
            st.error("❌ Could not find valid JSON in response")
            return None
            
    except Exception as e:
        st.error(f"❌ AI analysis failed: {str(e)}")
        return None

def create_excel_report(data, analysis):
    """Create simple Excel report"""
    try:
        workbook = openpyxl.Workbook()
        ws = workbook.active
        ws.title = "IAM Analysis"
        
        # Add header
        ws['A1'] = "IAM Analysis Report"
        ws['A1'].font = Font(bold=True, size=16)
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        row = 4
        
        # Summary
        if analysis:
            ws[f'A{row}'] = "Summary"
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
            ws[f'A{row}'] = analysis.get('summary', 'No summary available')
            row += 3
            
            # Findings
            ws[f'A{row}'] = "Key Findings"
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
            
            for finding in analysis.get('findings', []):
                ws[f'A{row}'] = f"• {finding.get('type', 'Unknown')} ({finding.get('severity', 'Unknown')}): {finding.get('description', '')}"
                row += 1
            
            row += 2
            
            # Recommendations
            ws[f'A{row}'] = "Recommendations"
            ws[f'A{row}'].font = Font(bold=True)
            row += 1
            
            for rec in analysis.get('recommendations', []):
                ws[f'A{row}'] = f"• {rec}"
                row += 1
        
        # Save to bytes
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Report generation failed: {str(e)}")
        return None

def main():
    """Main application - single page"""
    
    try:
        # Check password
        if not check_password():
            return
        
        # Header
        st.title("🔐 Simple IAM Analyzer")
        st.markdown("**Upload files → Get AI analysis → Download report**")
        
        # Sidebar setup
        st.sidebar.header("🔧 Setup")
        
        # Check dependencies
        if not OPENAI_AVAILABLE:
            st.error("❌ OpenAI library not installed")
            return
        
        # Get OpenAI client
        with st.spinner("Setting up OpenAI connection..."):
            client, error = get_openai_client()
            
        if error:
            st.sidebar.error(f"❌ OpenAI Error: {error}")
            if "No API key" in error:
                st.info("Please enter your OpenAI API key in the sidebar")
            return
        else:
            st.sidebar.success("✅ OpenAI connected")
        
        # File upload section
        st.header("📁 Upload IAM Files")
        
        uploaded_files = st.file_uploader(
            "Upload files (Excel, CSV, Text)",
            accept_multiple_files=True,
            type=['xlsx', 'xls', 'csv', 'txt'],
            help="Upload up to 10 files, max 10MB each"
        )
        
        if not uploaded_files:
            st.info("👆 Upload some files to get started")
            return
        
        # Show uploaded files
        st.success(f"✅ {len(uploaded_files)} files uploaded")
        with st.expander("📋 File Details"):
            for file in uploaded_files:
                st.write(f"• {file.name} ({file.size:,} bytes)")
        
        # Processing section
        st.header("🔄 Processing & Analysis")
        
        # Analysis options
        col1, col2 = st.columns(2)
        with col1:
            analysis_type = st.selectbox(
                "Analysis Type:",
                ["General Security Review", "SOX Compliance", "Access Review", "Role Cleanup"]
            )
        
        with col2:
            analysis_depth = st.selectbox(
                "Analysis Depth:",
                ["Quick Overview", "Standard Analysis", "Detailed Review"]
            )
        
        # Process button
        if st.button("🚀 Analyze Files", type="primary"):
            
            # Step 1: Process files
            st.subheader("📊 Step 1: Processing Files")
            
            all_data = {}
            progress_bar = st.progress(0)
            
            for i, file in enumerate(uploaded_files):
                progress_bar.progress((i + 1) / len(uploaded_files))
                st.write(f"Processing: {file.name}")
                
                file_data = process_file(file)
                all_data.update(file_data)
            
            progress_bar.empty()
            
            if not all_data:
                st.error("❌ No data could be extracted from files")
                return
            
            st.success(f"✅ Processed {len(all_data)} data sources")
            
            # Show data preview
            with st.expander("🔍 Data Preview"):
                for source, data in list(all_data.items())[:3]:  # Show first 3
                    st.write(f"**{source}:**")
                    if isinstance(data, pd.DataFrame):
                        st.write(f"- {len(data)} rows, {len(data.columns)} columns")
                        st.write(f"- Columns: {', '.join(data.columns.tolist()[:5])}")
                        if len(data.columns) > 5:
                            st.write("  (and more...)")
                    elif isinstance(data, dict):
                        if 'error' in data:
                            st.write(f"- Error: {data['error']}")
                        elif 'text' in data:
                            st.write(f"- Text content: {len(data['text'])} characters")
            
            # Step 2: Prepare data summary
            st.subheader("📋 Step 2: Preparing Data Summary")
            
            summary_parts = []
            for source, data in all_data.items():
                if isinstance(data, pd.DataFrame):
                    summary_parts.append(f"File: {source}")
                    summary_parts.append(f"Columns: {', '.join(data.columns.tolist())}")
                    summary_parts.append(f"Sample data:\n{data.head(2).to_string()}")
                    summary_parts.append("---")
                elif isinstance(data, dict) and 'text' in data:
                    summary_parts.append(f"File: {source}")
                    summary_parts.append(f"Content: {data['text'][:300]}...")
                    summary_parts.append("---")
            
            data_summary = '\n'.join(summary_parts)
            
            # Limit summary size
            if len(data_summary) > 8000:
                data_summary = data_summary[:8000] + "\n[Content truncated for analysis]"
            
            st.success(f"✅ Data summary prepared ({len(data_summary)} characters)")
            
            # Step 3: AI Analysis
            st.subheader("🤖 Step 3: AI Analysis")
            
            context = f"{analysis_type} - {analysis_depth}"
            
            with st.spinner("Running AI analysis..."):
                analysis_results = analyze_with_ai(client, data_summary, context)
            
            if not analysis_results:
                st.error("❌ AI analysis failed")
                
                # Fallback results
                st.warning("📋 Providing basic analysis instead...")
                analysis_results = {
                    "summary": "AI analysis unavailable. Manual review recommended.",
                    "findings": [
                        {
                            "type": "Manual Review",
                            "severity": "Medium",
                            "description": "Automated analysis failed - conduct manual review",
                            "recommendation": "Review access permissions manually"
                        }
                    ],
                    "recommendations": [
                        "Conduct manual IAM review",
                        "Implement proper access controls",
                        "Regular access reviews"
                    ],
                    "risk_score": 5
                }
            
            # Step 4: Display Results
            st.subheader("📊 Step 4: Analysis Results")
            
            # Summary
            st.write("**📋 Summary:**")
            st.info(analysis_results.get('summary', 'No summary available'))
            
            # Risk score
            risk_score = analysis_results.get('risk_score', 0)
            st.metric("🎯 Risk Score", f"{risk_score}/10")
            
            # Findings
            findings = analysis_results.get('findings', [])
            if findings:
                st.write("**🚨 Key Findings:**")
                for finding in findings:
                    severity = finding.get('severity', 'Unknown')
                    severity_color = {'High': '🔴', 'Medium': '🟡', 'Low': '🟢'}.get(severity, '⚪')
                    
                    with st.expander(f"{severity_color} {finding.get('type', 'Unknown')} - {severity}"):
                        st.write("**Description:**", finding.get('description', 'No description'))
                        st.write("**Recommendation:**", finding.get('recommendation', 'No recommendation'))
            
            # Recommendations
            recommendations = analysis_results.get('recommendations', [])
            if recommendations:
                st.write("**💡 Recommendations:**")
                for i, rec in enumerate(recommendations, 1):
                    st.write(f"{i}. {rec}")
            
            # Step 5: Generate Report
            st.subheader("📄 Step 5: Generate Report")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📊 Generate Excel Report"):
                    with st.spinner("Generating report..."):
                        excel_bytes = create_excel_report(all_data, analysis_results)
                        
                        if excel_bytes:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            st.download_button(
                                label="📥 Download Report",
                                data=excel_bytes,
                                file_name=f"IAM_Report_{timestamp}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                            st.success("✅ Report ready for download!")
            
            with col2:
                if st.button("📋 Copy Summary"):
                    summary_text = f"""IAM Analysis Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Summary: {analysis_results.get('summary', '')}

Risk Score: {risk_score}/10

Key Recommendations:
{chr(10).join([f"• {rec}" for rec in recommendations])}
"""
                    st.text_area("Copy this summary:", value=summary_text, height=200)
        
        # Footer
        st.markdown("---")
        st.markdown("🔐 **Simple IAM Analyzer** | Cost: ~$0.01-0.05 per analysis")
        
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        
        # Show error details
        with st.expander("🐛 Error Details"):
            st.code(traceback.format_exc())
        
        # Reset button
        if st.button("🔄 Reset Application"):
            st.rerun()

if __name__ == "__main__":
    main()
