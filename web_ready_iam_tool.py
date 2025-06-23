#!/usr/bin/env python3
"""
Debug IAM Analyzer - Shows exactly what's happening
"""

import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime
import json
import traceback

# Check what's available
try:
    import openai
    OPENAI_AVAILABLE = True
    st.sidebar.success("✅ OpenAI imported")
except ImportError as e:
    OPENAI_AVAILABLE = False
    st.sidebar.error(f"❌ OpenAI import failed: {e}")

try:
    import openpyxl
    EXCEL_AVAILABLE = True
    st.sidebar.success("✅ Excel support available")
except ImportError as e:
    EXCEL_AVAILABLE = False
    st.sidebar.error(f"❌ Excel support failed: {e}")

# Simple password check
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔐 Debug IAM Analyzer")
        password = st.text_input("Password:", type="password")
        
        if st.button("Login"):
            if password in ["demo123", "password", "test"]:  # Multiple options
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Try: demo123, password, or test")
        return False
    return True

def main():
    if not check_password():
        return
    
    st.title("🔧 Debug IAM Analyzer")
    st.write("**This version shows exactly what's happening at each step**")
    
    # Debug info panel
    with st.expander("🐛 System Debug Info", expanded=True):
        st.write("**Dependencies:**")
        st.write(f"- OpenAI Available: {OPENAI_AVAILABLE}")
        st.write(f"- Excel Available: {EXCEL_AVAILABLE}")
        st.write(f"- Streamlit Version: {st.__version__}")
        st.write(f"- Python Path: {os.getcwd()}")
        
        # Check secrets
        try:
            api_key_in_secrets = bool(st.secrets.get("OPENAI_API_KEY"))
            st.write(f"- API Key in Secrets: {api_key_in_secrets}")
        except:
            st.write("- API Key in Secrets: Cannot check")
    
    # Step 1: API Key
    st.header("Step 1: OpenAI Setup")
    
    if not OPENAI_AVAILABLE:
        st.error("❌ OpenAI not available - install with: pip install openai")
        return
    
    # Get API key
    api_key_from_secrets = st.secrets.get("OPENAI_API_KEY", "")
    api_key_from_input = st.text_input("Or enter API key manually:", type="password")
    
    api_key = api_key_from_secrets or api_key_from_input
    
    if not api_key:
        st.warning("⚠️ No API key found. Enter one above or add to secrets.")
        return
    
    st.success(f"✅ API Key found (starts with: {api_key[:8]}...)")
    
    # Test API key
    st.subheader("Testing API Connection...")
    
    try:
        with st.spinner("Testing OpenAI connection..."):
            client = openai.OpenAI(api_key=api_key)
            
            # Simple test
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            
            st.success("✅ OpenAI connection works!")
            st.write(f"Test response: {response.choices[0].message.content}")
            
    except Exception as e:
        st.error(f"❌ OpenAI connection failed: {str(e)}")
        st.code(traceback.format_exc())
        return
    
    # Step 2: File Upload
    st.header("Step 2: File Upload")
    
    uploaded_files = st.file_uploader(
        "Upload test files:",
        accept_multiple_files=True,
        type=['csv', 'xlsx', 'txt']
    )
    
    if not uploaded_files:
        st.info("Upload some files to continue")
        
        # Create sample data option
        if st.button("📊 Use Sample Data Instead"):
            st.session_state['sample_data'] = True
            st.rerun()
        
        return
    
    st.success(f"✅ {len(uploaded_files)} files uploaded")
    
    # Show file details
    for file in uploaded_files:
        st.write(f"- {file.name}: {file.size} bytes")
    
    # Step 3: Process Files
    st.header("Step 3: File Processing")
    
    processed_data = {}
    
    for file in uploaded_files:
        st.write(f"🔄 Processing {file.name}...")
        
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
                processed_data[file.name] = df
                st.success(f"✅ CSV loaded: {len(df)} rows, {len(df.columns)} columns")
                st.write(f"Columns: {list(df.columns)}")
                
            elif file.name.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file)
                processed_data[file.name] = df
                st.success(f"✅ Excel loaded: {len(df)} rows, {len(df.columns)} columns")
                st.write(f"Columns: {list(df.columns)}")
                
            elif file.name.endswith('.txt'):
                content = file.read().decode('utf-8')
                processed_data[file.name] = {'text': content}
                st.success(f"✅ Text loaded: {len(content)} characters")
                
            else:
                st.warning(f"⚠️ Unsupported file type: {file.name}")
                
        except Exception as e:
            st.error(f"❌ Failed to process {file.name}: {str(e)}")
            st.code(traceback.format_exc())
    
    if not processed_data:
        st.error("❌ No files could be processed")
        return
    
    st.success(f"✅ Processed {len(processed_data)} files successfully")
    
    # Step 4: Prepare for Analysis
    st.header("Step 4: Prepare Analysis")
    
    # Create simple summary
    summary_parts = []
    
    for filename, data in processed_data.items():
        st.write(f"📋 Summarizing {filename}...")
        
        if isinstance(data, pd.DataFrame):
            summary_parts.append(f"File: {filename}")
            summary_parts.append(f"Rows: {len(data)}, Columns: {len(data.columns)}")
            summary_parts.append(f"Column names: {', '.join(data.columns)}")
            
            # Add sample data
            if len(data) > 0:
                summary_parts.append("Sample data:")
                summary_parts.append(str(data.head(2)))
            
        elif isinstance(data, dict) and 'text' in data:
            summary_parts.append(f"File: {filename}")
            summary_parts.append(f"Text content: {data['text'][:200]}...")
        
        summary_parts.append("---")
    
    data_summary = '\n'.join(summary_parts)
    
    st.success(f"✅ Data summary created: {len(data_summary)} characters")
    
    with st.expander("🔍 View Data Summary"):
        st.text(data_summary)
    
    # Step 5: AI Analysis
    st.header("Step 5: AI Analysis")
    
    if st.button("🤖 Run AI Analysis", type="primary"):
        
        st.write("🔄 Starting AI analysis...")
        
        try:
            # Prepare prompt
            prompt = f"""
            Analyze this IAM data and provide insights.
            
            Data:
            {data_summary}
            
            Respond with JSON:
            {{
                "summary": "Brief assessment",
                "findings": ["finding 1", "finding 2"],
                "recommendations": ["rec 1", "rec 2"],
                "risk_score": 5
            }}
            """
            
            st.write("📤 Sending to OpenAI...")
            st.write(f"Prompt length: {len(prompt)} characters")
            
            # Make API call
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an IAM expert. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            st.write("📥 Received response from OpenAI")
            
            # Get response
            response_text = response.choices[0].message.content
            st.write(f"Response length: {len(response_text)} characters")
            
            with st.expander("🔍 Raw AI Response"):
                st.code(response_text)
            
            # Parse JSON
            st.write("🔄 Parsing JSON...")
            
            try:
                # Find JSON in response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                
                if start == -1 or end == 0:
                    raise ValueError("No JSON found in response")
                
                json_text = response_text[start:end]
                result = json.loads(json_text)
                
                st.success("✅ JSON parsed successfully!")
                
                # Display results
                st.subheader("📊 Analysis Results")
                
                st.write("**Summary:**")
                st.info(result.get('summary', 'No summary'))
                
                st.write("**Risk Score:**")
                st.metric("Risk", f"{result.get('risk_score', 0)}/10")
                
                st.write("**Key Findings:**")
                for finding in result.get('findings', []):
                    st.write(f"• {finding}")
                
                st.write("**Recommendations:**")
                for rec in result.get('recommendations', []):
                    st.write(f"• {rec}")
                
                # Store results for report
                st.session_state['analysis_results'] = result
                st.session_state['processed_data'] = processed_data
                
                st.success("✅ Analysis complete!")
                
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON parsing failed: {str(e)}")
                st.write("**Trying to extract readable content:**")
                st.write(response_text)
                
        except Exception as e:
            st.error(f"❌ AI analysis failed: {str(e)}")
            st.code(traceback.format_exc())
    
    # Step 6: Generate Report
    if 'analysis_results' in st.session_state:
        st.header("Step 6: Generate Report")
        
        if st.button("📊 Generate Simple Report", type="primary"):
            st.write("🔄 Creating report...")
            
            try:
                if not EXCEL_AVAILABLE:
                    # Text report fallback
                    st.write("📄 Creating text report (Excel not available)...")
                    
                    results = st.session_state['analysis_results']
                    
                    report_text = f"""IAM Analysis Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

SUMMARY:
{results.get('summary', 'No summary')}

RISK SCORE: {results.get('risk_score', 0)}/10

KEY FINDINGS:
{chr(10).join([f"• {f}" for f in results.get('findings', [])])}

RECOMMENDATIONS:
{chr(10).join([f"• {r}" for r in results.get('recommendations', [])])}

---
Generated by IAM Analyzer
"""
                    
                    st.download_button(
                        "📥 Download Text Report",
                        data=report_text,
                        file_name=f"iam_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
                    
                    st.success("✅ Text report ready!")
                    
                else:
                    # Excel report
                    st.write("📊 Creating Excel report...")
                    
                    workbook = openpyxl.Workbook()
                    ws = workbook.active
                    ws.title = "IAM Analysis"
                    
                    # Add content
                    ws['A1'] = "IAM Analysis Report"
                    ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    
                    results = st.session_state['analysis_results']
                    
                    row = 4
                    ws[f'A{row}'] = "Summary:"
                    ws[f'B{row}'] = results.get('summary', 'No summary')
                    
                    row += 2
                    ws[f'A{row}'] = "Risk Score:"
                    ws[f'B{row}'] = f"{results.get('risk_score', 0)}/10"
                    
                    row += 2
                    ws[f'A{row}'] = "Findings:"
                    row += 1
                    
                    for finding in results.get('findings', []):
                        ws[f'A{row}'] = f"• {finding}"
                        row += 1
                    
                    row += 1
                    ws[f'A{row}'] = "Recommendations:"
                    row += 1
                    
                    for rec in results.get('recommendations', []):
                        ws[f'A{row}'] = f"• {rec}"
                        row += 1
                    
                    # Save to bytes
                    output = io.BytesIO()
                    workbook.save(output)
                    output.seek(0)
                    
                    st.download_button(
                        "📥 Download Excel Report",
                        data=output.getvalue(),
                        file_name=f"iam_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                    st.success("✅ Excel report ready!")
                
            except Exception as e:
                st.error(f"❌ Report generation failed: {str(e)}")
                st.code(traceback.format_exc())
    
    # Sample data option
    if st.session_state.get('sample_data'):
        st.header("📊 Sample Data Test")
        
        # Create sample CSV data
        sample_df = pd.DataFrame({
            'User': ['john.doe', 'jane.smith', 'bob.jones'],
            'Role': ['Admin', 'User', 'Manager'],
            'Department': ['IT', 'HR', 'Finance'],
            'LastLogin': ['2024-01-15', '2024-01-14', '2024-01-13']
        })
        
        st.write("**Sample Data:**")
        st.dataframe(sample_df)
        
        if st.button("🤖 Analyze Sample Data"):
            # Quick analysis without AI
            st.write("**Quick Analysis (No AI):**")
            st.info("Found 3 users across 3 departments. Admin user in IT department detected.")
            st.write("**Findings:**")
            st.write("• Admin role detected for john.doe")
            st.write("• All users have recent login activity") 
            st.write("**Recommendations:**")
            st.write("• Review admin access privileges")
            st.write("• Implement regular access reviews")
            
            # Simple report
            simple_report = f"""Sample IAM Analysis
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Users Analyzed: 3
Admin Users: 1
Departments: 3

Findings:
• Admin role detected for john.doe
• All users have recent login activity

Recommendations:
• Review admin access privileges  
• Implement regular access reviews
"""
            
            st.download_button(
                "📥 Download Sample Report",
                data=simple_report,
                file_name="sample_iam_report.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()
