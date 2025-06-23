#!/usr/bin/env python3
"""
Professional IAM Analysis Tool
Advanced features for comprehensive IAM analysis and remediation
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
from datetime import datetime, timedelta
import json
import traceback
import re
from pathlib import Path

# File processing
try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.chart import BarChart, Reference
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from dotenv import load_dotenv
load_dotenv()

# Configuration
st.set_page_config(
    page_title="Professional IAM Analyzer",
    page_icon="🏢",
    layout="wide"
)

def check_password():
    """Enhanced password protection"""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.markdown("""
        <div style="text-align: center; padding: 2rem;">
            <h1>🏢 Professional IAM Analysis Platform</h1>
            <p style="font-size: 1.2em; color: #666;">Enterprise-grade Identity and Access Management Analysis</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            password = st.text_input("Access Code:", type="password", help="Enter your secure access code")
            
            if st.button("🔓 Access Platform", type="primary", use_container_width=True):
                if password == st.secrets.get("app_password", "demo123"):
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Invalid access code")
            
            st.info("💡 **Demo access:** demo123")
        
        st.markdown("---")
        st.markdown("""
        **🔐 Security Notice:** This platform processes IAM data using enterprise-grade AI analysis. 
        Do not upload highly classified data to cloud-hosted instances.
        """)
        return False
    return True

def get_openai_client():
    """Get OpenAI client with comprehensive error handling"""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "") or st.sidebar.text_input(
            "🔑 OpenAI API Key",
            type="password",
            help="Enterprise API key for AI analysis"
        )
        
        if not api_key:
            return None, "No API key provided"
        
        client = openai.OpenAI(api_key=api_key)
        
        # Test connection
        client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        
        return client, None
        
    except Exception as e:
        return None, str(e)

def process_files_advanced(uploaded_files):
    """Advanced file processing with detailed metadata"""
    results = {}
    processing_log = []
    
    for file in uploaded_files:
        try:
            file_info = {
                'name': file.name,
                'size': file.size,
                'type': Path(file.name).suffix.lower(),
                'processed': False,
                'rows': 0,
                'columns': 0,
                'data_types': [],
                'sample_data': None
            }
            
            if file_info['type'] in ['.csv']:
                # Enhanced CSV processing
                for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                    for sep in [',', ';', '\t', '|']:
                        try:
                            df = pd.read_csv(io.BytesIO(file.read()), encoding=encoding, sep=sep, nrows=5000)
                            if len(df.columns) > 1:
                                df.columns = [str(col).strip() for col in df.columns]
                                
                                # Enhanced metadata
                                file_info.update({
                                    'processed': True,
                                    'rows': len(df),
                                    'columns': len(df.columns),
                                    'column_names': list(df.columns),
                                    'data_types': [str(dtype) for dtype in df.dtypes],
                                    'sample_data': df.head(3).to_dict('records'),
                                    'encoding': encoding,
                                    'separator': sep
                                })
                                
                                results[file.name] = {
                                    'data': df,
                                    'metadata': file_info
                                }
                                break
                        except:
                            continue
                    if file_info['processed']:
                        break
                        
            elif file_info['type'] in ['.xlsx', '.xls']:
                # Enhanced Excel processing
                file.seek(0)  # Reset file pointer
                excel_file = pd.ExcelFile(io.BytesIO(file.read()))
                
                for sheet_name in excel_file.sheet_names[:10]:
                    try:
                        df = pd.read_excel(io.BytesIO(file.read()), sheet_name=sheet_name, nrows=5000)
                        if not df.empty:
                            df.columns = [str(col).strip() for col in df.columns]
                            
                            sheet_info = file_info.copy()
                            sheet_info.update({
                                'processed': True,
                                'rows': len(df),
                                'columns': len(df.columns),
                                'column_names': list(df.columns),
                                'sheet_name': sheet_name,
                                'sample_data': df.head(3).to_dict('records')
                            })
                            
                            results[f"{file.name}_{sheet_name}"] = {
                                'data': df,
                                'metadata': sheet_info
                            }
                            
                    except Exception as e:
                        processing_log.append(f"Error processing sheet {sheet_name}: {str(e)}")
                        
            processing_log.append(f"✅ Processed {file.name}: {file_info}")
            
        except Exception as e:
            processing_log.append(f"❌ Failed to process {file.name}: {str(e)}")
    
    return results, processing_log

def analyze_iam_professional(client, data_summary, requirements, analysis_type, compliance_framework):
    """Professional AI analysis with comprehensive prompts"""
    
    system_prompt = f"""You are a senior IAM consultant with expertise in {compliance_framework} compliance and enterprise security. 
    You specialize in {analysis_type} and provide executive-level analysis with detailed remediation plans."""
    
    analysis_prompt = f"""
    Conduct a comprehensive IAM analysis based on these requirements:
    
    **Client Requirements:**
    {requirements}
    
    **Analysis Type:** {analysis_type}
    **Compliance Framework:** {compliance_framework}
    
    **Data to Analyze:**
    {data_summary}
    
    Provide a comprehensive analysis in JSON format:
    {{
        "executive_summary": "Executive-level assessment with business impact and strategic recommendations",
        "risk_assessment": {{
            "overall_risk_score": 0-10,
            "risk_categories": {{
                "segregation_of_duties": 0-10,
                "excessive_privileges": 0-10,
                "orphaned_accounts": 0-10,
                "compliance_violations": 0-10
            }},
            "risk_trends": "Analysis of risk patterns and trends"
        }},
        "detailed_findings": [
            {{
                "id": "F001",
                "category": "SoD|Excessive_Access|Orphaned_Account|Policy_Violation|Compliance",
                "severity": "Critical|High|Medium|Low",
                "title": "Concise finding title",
                "description": "Detailed technical description",
                "business_impact": "Specific business risk and financial impact",
                "affected_entities": {{
                    "users": ["user1", "user2"],
                    "systems": ["system1", "system2"],
                    "processes": ["process1", "process2"]
                }},
                "compliance_impact": "Specific regulatory implications",
                "evidence": "Supporting evidence from data",
                "remediation": {{
                    "immediate_actions": ["action1", "action2"],
                    "long_term_solutions": ["solution1", "solution2"],
                    "estimated_effort": "Low|Medium|High",
                    "timeline": "Recommended timeline",
                    "responsible_party": "Who should handle this"
                }}
            }}
        ],
        "recommendations": {{
            "immediate": [
                {{
                    "action": "Specific immediate action",
                    "rationale": "Why this is needed now",
                    "effort": "Low|Medium|High",
                    "timeline": "24-48 hours"
                }}
            ],
            "short_term": [
                {{
                    "action": "Short-term improvement",
                    "rationale": "Business justification",
                    "effort": "Low|Medium|High",
                    "timeline": "1-4 weeks"
                }}
            ],
            "strategic": [
                {{
                    "action": "Strategic initiative",
                    "rationale": "Long-term value proposition",
                    "effort": "Medium|High",
                    "timeline": "1-6 months"
                }}
            ]
        }},
        "entitlement_remediation": {{
            "users_to_review": [
                {{
                    "user": "username",
                    "current_roles": ["role1", "role2"],
                    "recommended_roles": ["role1"],
                    "rationale": "Why this change is recommended",
                    "priority": "High|Medium|Low"
                }}
            ],
            "roles_to_modify": [
                {{
                    "role": "role_name",
                    "current_permissions": ["perm1", "perm2"],
                    "recommended_permissions": ["perm1"],
                    "rationale": "Why this change is needed"
                }}
            ],
            "new_controls_needed": [
                {{
                    "control_type": "Technical|Process|Policy",
                    "description": "What control is needed",
                    "implementation": "How to implement"
                }}
            ]
        }},
        "metrics": {{
            "total_users": 0,
            "total_roles": 0,
            "privileged_users": 0,
            "violations_by_severity": {{
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }},
            "compliance_score": 0-100
        }},
        "next_steps": [
            "Specific next step 1",
            "Specific next step 2"
        ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        response_text = response.choices[0].message.content
        
        # Extract JSON
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        
        if start != -1 and end != 0:
            json_text = response_text[start:end]
            return json.loads(json_text)
        else:
            return None
            
    except Exception as e:
        st.error(f"AI Analysis failed: {str(e)}")
        return None

def generate_professional_excel_report(data_dict, analysis_results, report_type="comprehensive"):
    """Generate professional Excel reports with advanced formatting"""
    
    if not EXCEL_AVAILABLE:
        return None
    
    try:
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        
        # Define professional color scheme
        colors = {
            'header': '1F497D',      # Professional blue
            'critical': 'C5504B',    # Red
            'high': 'E36C09',        # Orange
            'medium': 'F79646',      # Light orange
            'low': '9BBB59',         # Green
            'accent': '4F81BD'       # Light blue
        }
        
        # Create Executive Summary
        create_executive_summary_sheet(workbook, analysis_results, colors)
        
        # Create Risk Dashboard
        create_risk_dashboard_sheet(workbook, analysis_results, colors)
        
        # Create Detailed Findings
        create_findings_sheet(workbook, analysis_results, colors)
        
        # Create Remediation Plan
        create_remediation_sheet(workbook, analysis_results, colors)
        
        # Create Data Analysis sheets
        for name, data_info in data_dict.items():
            if isinstance(data_info.get('data'), pd.DataFrame):
                create_data_analysis_sheet(workbook, name, data_info['data'], colors)
        
        # Save to bytes
        output = io.BytesIO()
        workbook.save(output)
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        st.error(f"Excel report generation failed: {str(e)}")
        return None

def create_executive_summary_sheet(workbook, analysis, colors):
    """Create professional executive summary sheet"""
    ws = workbook.create_sheet("Executive Summary", 0)
    
    # Header
    ws.merge_cells('A1:F1')
    ws['A1'] = "IAM ANALYSIS - EXECUTIVE SUMMARY"
    ws['A1'].font = Font(size=16, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color=colors['header'], end_color=colors['header'], fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
    
    ws.merge_cells('A2:F2')
    ws['A2'] = f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}"
    ws['A2'].font = Font(size=10, italic=True)
    ws['A2'].alignment = Alignment(horizontal='center')
    
    row = 4
    
    # Executive Summary
    ws.merge_cells(f'A{row}:F{row}')
    ws[f'A{row}'] = "EXECUTIVE SUMMARY"
    ws[f'A{row}'].font = Font(size=14, bold=True)
    row += 1
    
    summary_text = analysis.get('executive_summary', 'No summary available')
    ws.merge_cells(f'A{row}:F{row+2}')
    ws[f'A{row}'] = summary_text
    ws[f'A{row}'].alignment = Alignment(wrap_text=True, vertical='top')
    row += 4
    
    # Key Metrics
    ws.merge_cells(f'A{row}:F{row}')
    ws[f'A{row}'] = "KEY METRICS"
    ws[f'A{row}'].font = Font(size=14, bold=True)
    row += 1
    
    metrics = analysis.get('metrics', {})
    risk_assessment = analysis.get('risk_assessment', {})
    
    # Create metrics table
    metric_data = [
        ['Total Users', metrics.get('total_users', 'N/A')],
        ['Total Roles', metrics.get('total_roles', 'N/A')],
        ['Privileged Users', metrics.get('privileged_users', 'N/A')],
        ['Overall Risk Score', f"{risk_assessment.get('overall_risk_score', 0)}/10"],
        ['Compliance Score', f"{metrics.get('compliance_score', 0)}%"]
    ]
    
    for metric, value in metric_data:
        ws[f'A{row}'] = metric
        ws[f'B{row}'] = value
        ws[f'A{row}'].font = Font(bold=True)
        row += 1
    
    # Critical Findings Count
    row += 1
    ws.merge_cells(f'A{row}:F{row}')
    ws[f'A{row}'] = "FINDINGS BY SEVERITY"
    ws[f'A{row}'].font = Font(size=14, bold=True)
    row += 1
    
    violations = metrics.get('violations_by_severity', {})
    for severity, count in violations.items():
        ws[f'A{row}'] = severity.title()
        ws[f'B{row}'] = count
        
        # Color code by severity
        if severity == 'critical':
            ws[f'B{row}'].fill = PatternFill(start_color=colors['critical'], end_color=colors['critical'], fill_type='solid')
            ws[f'B{row}'].font = Font(color='FFFFFF', bold=True)
        
        row += 1

def create_risk_dashboard_sheet(workbook, analysis, colors):
    """Create risk assessment dashboard"""
    ws = workbook.create_sheet("Risk Dashboard")
    
    # Header
    ws.merge_cells('A1:E1')
    ws['A1'] = "RISK ASSESSMENT DASHBOARD"
    ws['A1'].font = Font(size=16, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color=colors['header'], end_color=colors['header'], fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center')
    
    row = 3
    
    # Risk Categories
    risk_assessment = analysis.get('risk_assessment', {})
    risk_categories = risk_assessment.get('risk_categories', {})
    
    ws[f'A{row}'] = "Risk Category"
    ws[f'B{row}'] = "Score (0-10)"
    ws[f'C{row}'] = "Risk Level"
    ws[f'D{row}'] = "Status"
    
    # Style headers
    for col in ['A', 'B', 'C', 'D']:
        ws[f'{col}{row}'].font = Font(bold=True, color='FFFFFF')
        ws[f'{col}{row}'].fill = PatternFill(start_color=colors['accent'], end_color=colors['accent'], fill_type='solid')
    
    row += 1
    
    for category, score in risk_categories.items():
        ws[f'A{row}'] = category.replace('_', ' ').title()
        ws[f'B{row}'] = score
        
        # Determine risk level and color
        if score >= 8:
            risk_level = "Critical"
            color = colors['critical']
        elif score >= 6:
            risk_level = "High"
            color = colors['high']
        elif score >= 4:
            risk_level = "Medium"
            color = colors['medium']
        else:
            risk_level = "Low"
            color = colors['low']
        
        ws[f'C{row}'] = risk_level
        ws[f'C{row}'].fill = PatternFill(start_color=color, end_color=color, fill_type='solid')
        ws[f'C{row}'].font = Font(color='FFFFFF', bold=True)
        
        ws[f'D{row}'] = "Requires Attention" if score >= 6 else "Acceptable"
        
        row += 1

def create_findings_sheet(workbook, analysis, colors):
    """Create detailed findings sheet"""
    ws = workbook.create_sheet("Detailed Findings")
    
    # Header
    ws.merge_cells('A1:J1')
    ws['A1'] = "DETAILED FINDINGS AND RECOMMENDATIONS"
    ws['A1'].font = Font(size=16, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color=colors['header'], end_color=colors['header'], fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center')
    
    # Column headers
    headers = ['ID', 'Category', 'Severity', 'Title', 'Description', 'Business Impact', 
               'Affected Users', 'Compliance Impact', 'Immediate Actions', 'Timeline']
    
    row = 3
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row, column=col)
        cell.value = header
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color=colors['accent'], end_color=colors['accent'], fill_type='solid')
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
    
    # Findings data
    findings = analysis.get('detailed_findings', [])
    for finding in findings:
        row += 1
        
        data = [
            finding.get('id', ''),
            finding.get('category', ''),
            finding.get('severity', ''),
            finding.get('title', ''),
            finding.get('description', ''),
            finding.get('business_impact', ''),
            ', '.join(finding.get('affected_entities', {}).get('users', [])),
            finding.get('compliance_impact', ''),
            ', '.join(finding.get('remediation', {}).get('immediate_actions', [])),
            finding.get('remediation', {}).get('timeline', '')
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col)
            cell.value = value
            cell.alignment = Alignment(wrap_text=True, vertical='top')
            
            # Color code by severity
            severity = finding.get('severity', '').lower()
            if severity in colors:
                cell.fill = PatternFill(start_color=colors[severity], end_color=colors[severity], fill_type='solid')
                if severity in ['critical', 'high']:
                    cell.font = Font(color='FFFFFF')
    
    # Auto-adjust column widths
    for column in ws.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

def create_remediation_sheet(workbook, analysis, colors):
    """Create remediation action plan sheet"""
    ws = workbook.create_sheet("Remediation Plan")
    
    # Header
    ws.merge_cells('A1:F1')
    ws['A1'] = "REMEDIATION ACTION PLAN"
    ws['A1'].font = Font(size=16, bold=True, color='FFFFFF')
    ws['A1'].fill = PatternFill(start_color=colors['header'], end_color=colors['header'], fill_type='solid')
    ws['A1'].alignment = Alignment(horizontal='center')
    
    row = 3
    
    # Entitlement Remediation
    entitlement_rem = analysis.get('entitlement_remediation', {})
    
    # Users to Review
    users_to_review = entitlement_rem.get('users_to_review', [])
    if users_to_review:
        ws.merge_cells(f'A{row}:F{row}')
        ws[f'A{row}'] = "USERS REQUIRING ACCESS REVIEW"
        ws[f'A{row}'].font = Font(size=14, bold=True)
        row += 1
        
        # Headers
        user_headers = ['User', 'Current Roles', 'Recommended Roles', 'Rationale', 'Priority']
        for col, header in enumerate(user_headers, 1):
            cell = ws.cell(row=row, column=col)
            cell.value = header
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill(start_color=colors['accent'], end_color=colors['accent'], fill_type='solid')
        
        row += 1
        
        for user_info in users_to_review:
            data = [
                user_info.get('user', ''),
                ', '.join(user_info.get('current_roles', [])),
                ', '.join(user_info.get('recommended_roles', [])),
                user_info.get('rationale', ''),
                user_info.get('priority', '')
            ]
            
            for col, value in enumerate(data, 1):
                cell = ws.cell(row=row, column=col)
                cell.value = value
                cell.alignment = Alignment(wrap_text=True, vertical='top')
                
                # Color code by priority
                if col == 5:  # Priority column
                    if value.lower() == 'high':
                        cell.fill = PatternFill(start_color=colors['critical'], end_color=colors['critical'], fill_type='solid')
                        cell.font = Font(color='FFFFFF', bold=True)
            
            row += 1
        
        row += 2
    
    # Implementation Timeline
    recommendations = analysis.get('recommendations', {})
    
    for timeline_type, actions in recommendations.items():
        if actions:
            ws.merge_cells(f'A{row}:F{row}')
            ws[f'A{row}'] = f"{timeline_type.upper().replace('_', ' ')} ACTIONS"
            ws[f'A{row}'].font = Font(size=14, bold=True)
            row += 1
            
            for action_info in actions:
                ws[f'A{row}'] = f"• {action_info.get('action', '')}"
                ws[f'B{row}'] = action_info.get('rationale', '')
                ws[f'C{row}'] = action_info.get('effort', '')
                ws[f'D{row}'] = action_info.get('timeline', '')
                row += 1
            
            row += 1

def create_data_analysis_sheet(workbook, sheet_name, df, colors):
    """Create data analysis sheet for each dataset"""
    safe_name = sheet_name[:31].replace('/', '_').replace('\\', '_')
    ws = workbook.create_sheet(safe_name)
    
    # Add data
    for r in dataframe_to_rows(df.head(1000), index=False, header=True):  # Limit to 1000 rows
        ws.append(r)
    
    # Format headers
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = PatternFill(start_color=colors['accent'], end_color=colors['accent'], fill_type='solid')
        cell.alignment = Alignment(horizontal='center')

def main():
    """Professional IAM Analysis Application"""
    
    if not check_password():
        return
    
    # Professional header
    st.markdown("""
    <div style="background: linear-gradient(90deg, #1f497d, #4f81bd); padding: 1.5rem; border-radius: 10px; margin-bottom: 2rem;">
        <h1 style="color: white; text-align: center; margin: 0;">🏢 Professional IAM Analysis Platform</h1>
        <p style="color: #e6f2ff; text-align: center; margin: 0.5rem 0 0 0; font-size: 1.1em;">
            Enterprise-grade Identity and Access Management Analysis & Remediation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar setup
    with st.sidebar:
        st.markdown("### 🔧 **Platform Configuration**")
        
        # Check dependencies
        if not OPENAI_AVAILABLE:
            st.error("❌ AI Analysis Unavailable")
            st.stop()
        
        if not EXCEL_AVAILABLE:
            st.warning("⚠️ Advanced Excel features disabled")
        
        # Get OpenAI client
        client, error = get_openai_client()
        
        if error:
            st.error(f"❌ AI Configuration Error")
            st.write(error)
            return
        else:
            st.success("✅ AI Analysis Ready")
        
        st.markdown("---")
        
        # Analysis Configuration
        st.markdown("### 📊 **Analysis Configuration**")
        
        analysis_type = st.selectbox(
            "Analysis Type:",
            [
                "Comprehensive IAM Review",
                "SOX Compliance Assessment", 
                "PCI DSS Access Review",
                "Privileged Access Analysis",
                "Role-Based Access Review",
                "Segregation of Duties Audit",
                "User Access Certification",
                "Emergency Access Review"
            ]
        )
        
        compliance_framework = st.selectbox(
            "Compliance Framework:",
            [
                "SOX (Sarbanes-Oxley)",
                "PCI DSS",
                "HIPAA",
                "ISO 27001",
                "NIST Cybersecurity Framework",
                "GDPR",
                "General Security Best Practices"
            ]
        )
        
        report_type = st.selectbox(
            "Report Type:",
            [
                "Executive Summary",
                "Comprehensive Analysis",
                "Technical Deep Dive",
                "Remediation Plan",
                "Compliance Report"
            ]
        )
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📁 **Data Upload & Requirements**")
        
        # Requirements input
        st.markdown("#### 🎯 **Analysis Requirements**")
        requirements = st.text_area(
            "Describe what you need analyzed and your specific concerns:",
            placeholder="""Example: 
            - Review user access for finance team compliance with SOX requirements
            - Identify segregation of duties violations in accounts payable process  
            - Assess privileged user access and recommend least privilege implementation
            - Prepare for upcoming audit with detailed remediation timeline
            """,
            height=120
        )
        
        # File upload
        st.markdown("#### 📊 **Upload IAM Data**")
        uploaded_files = st.file_uploader(
            "Upload your IAM files (Excel, CSV, Text):",
            accept_multiple_files=True,
            type=['xlsx', 'xls', 'csv', 'txt'],
            help="Support for user lists, role assignments, access matrices, audit logs, etc."
        )
        
    with col2:
        st.markdown("### ℹ️ **Platform Capabilities**")
        
        capabilities = [
            "🔍 **Intelligent Pattern Detection** - AI identifies access anomalies",
            "🚨 **SoD Violation Analysis** - Automated segregation of duties checking", 
            "👥 **User Access Optimization** - Least privilege recommendations",
            "📋 **Compliance Mapping** - Framework-specific violation detection",
            "🔧 **Remediation Planning** - Detailed action plans with timelines",
            "📊 **Executive Reporting** - Professional presentations for leadership",
            "💼 **Entitlement Restructuring** - Role and permission optimization",
            "📈 **Risk Scoring** - Quantitative risk assessment"
        ]
        
        for capability in capabilities:
            st.markdown(capability)
    
    if not uploaded_files:
        st.info("👆 **Upload your IAM data files to begin professional analysis**")
        
        # Sample data option
        if st.button("📊 **Analyze Sample IAM Data**"):
            st.session_state['use_sample'] = True
            st.rerun()
        
        return
    
    # Process uploaded files
    if uploaded_files or st.session_state.get('use_sample'):
        
        if st.session_state.get('use_sample'):
            # Create sample data
            sample_data = {
                'sample_users.csv': {
                    'data': pd.DataFrame({
                        'UserID': ['jdoe', 'asmith', 'bmiller', 'kjohnson', 'lbrown'],
                        'Name': ['John Doe', 'Alice Smith', 'Bob Miller', 'Karen Johnson', 'Lisa Brown'],
                        'Department': ['Finance', 'IT', 'Finance', 'HR', 'IT'],
                        'Role': ['AP_Clerk', 'Domain_Admin', 'GL_Manager', 'HR_Specialist', 'Security_Admin'],
                        'Secondary_Role': ['', 'Backup_Admin', 'AP_Approver', '', 'Audit_Reviewer'],
                        'LastLogin': ['2024-01-15', '2024-01-14', '2024-01-13', '2024-01-12', '2024-01-11'],
                        'Status': ['Active', 'Active', 'Active', 'Active', 'Active'],
                        'Manager': ['bmiller', 'lbrown', 'kjohnson', 'jdoe', 'asmith']
                    }),
                    'metadata': {'name': 'sample_users.csv', 'rows': 5, 'columns': 8}
                }
            }
            
            processed_data = sample_data
            processing_log = ["✅ Sample data loaded"]
            
        else:
            # Process uploaded files
            with st.spinner("🔄 **Processing uploaded files...**"):
                processed_data, processing_log = process_files_advanced(uploaded_files)
        
        if not processed_data:
            st.error("❌ **No data could be processed from uploaded files**")
            return
        
        # Display processing results
        st.success(f"✅ **Successfully processed {len(processed_data)} data sources**")
        
        with st.expander("📋 **Processing Details**", expanded=False):
            for entry in processing_log:
                st.write(entry)
        
        # Data preview
        with st.expander("🔍 **Data Preview**", expanded=True):
            for name, data_info in list(processed_data.items())[:3]:
                st.markdown(f"**📊 {name}**")
                
                if isinstance(data_info.get('data'), pd.DataFrame):
                    df = data_info['data']
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Rows", len(df))
                    with col2:
                        st.metric("Columns", len(df.columns))
                    with col3:
                        st.metric("Data Quality", "Good" if df.notna().sum().sum() > 0 else "Check Required")
                    
                    st.write(f"**Columns:** {', '.join(df.columns.tolist())}")
                    st.dataframe(df.head(3), use_container_width=True)
                
                st.markdown("---")
        
        # Analysis section
        st.markdown("### 🤖 **Professional AI Analysis**")
        
        if not requirements:
            st.warning("⚠️ **Please describe your analysis requirements above for optimal results**")
            requirements = f"Perform {analysis_type} analysis focusing on {compliance_framework} compliance."
        
        if st.button("🚀 **Execute Professional Analysis**", type="primary", use_container_width=True):
            
            # Prepare data summary
            with st.spinner("📊 **Preparing comprehensive data analysis...**"):
                summary_parts = []
                
                for name, data_info in processed_data.items():
                    if isinstance(data_info.get('data'), pd.DataFrame):
                        df = data_info['data']
                        metadata = data_info.get('metadata', {})
                        
                        summary_parts.append(f"Dataset: {name}")
                        summary_parts.append(f"Records: {len(df)}, Fields: {len(df.columns)}")
                        summary_parts.append(f"Columns: {', '.join(df.columns)}")
                        
                        # Enhanced sample data
                        if len(df) > 0:
                            summary_parts.append("Sample records:")
                            summary_parts.append(df.head(3).to_string())
                        
                        summary_parts.append("---")
                
                data_summary = '\n'.join(summary_parts)
                
                # Limit summary size for API
                if len(data_summary) > 12000:
                    data_summary = data_summary[:12000] + "\n[Additional data truncated for analysis efficiency]"
            
            # AI Analysis
            with st.spinner("🧠 **Running advanced AI analysis...**"):
                analysis_results = analyze_iam_professional(
                    client, data_summary, requirements, analysis_type, compliance_framework
                )
            
            if not analysis_results:
                st.error("❌ **AI analysis failed - providing fallback analysis**")
                # Create fallback results
                analysis_results = {
                    "executive_summary": "Professional AI analysis was unavailable. Manual review of uploaded data recommended.",
                    "risk_assessment": {"overall_risk_score": 5, "risk_categories": {}},
                    "detailed_findings": [],
                    "recommendations": {"immediate": [], "short_term": [], "strategic": []},
                    "entitlement_remediation": {},
                    "metrics": {"violations_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}},
                    "next_steps": ["Conduct manual review", "Implement proper IAM controls"]
                }
            
            # Store results
            st.session_state['analysis_results'] = analysis_results
            st.session_state['processed_data'] = processed_data
            
            st.success("✅ **Professional analysis complete!**")
    
    # Display results
    if 'analysis_results' in st.session_state:
        
        analysis = st.session_state['analysis_results']
        
        st.markdown("### 📊 **Analysis Results**")
        
        # Executive Summary
        st.markdown("#### 📋 **Executive Summary**")
        summary = analysis.get('executive_summary', 'Analysis summary not available')
        st.info(summary)
        
        # Key Metrics Dashboard
        st.markdown("#### 📈 **Key Metrics Dashboard**")
        
        col1, col2, col3, col4 = st.columns(4)
        
        metrics = analysis.get('metrics', {})
        risk_assessment = analysis.get('risk_assessment', {})
        violations = metrics.get('violations_by_severity', {})
        
        with col1:
            st.metric("🎯 Overall Risk Score", 
                     f"{risk_assessment.get('overall_risk_score', 0)}/10",
                     delta="High Priority" if risk_assessment.get('overall_risk_score', 0) >= 7 else None)
        
        with col2:
            st.metric("👥 Total Users", metrics.get('total_users', 'N/A'))
        
        with col3:
            critical_count = violations.get('critical', 0) + violations.get('high', 0)
            st.metric("🚨 Critical/High Issues", critical_count,
                     delta="Requires Immediate Attention" if critical_count > 0 else None)
        
        with col4:
            st.metric("✅ Compliance Score", f"{metrics.get('compliance_score', 0)}%")
        
        # Risk Categories
        risk_categories = risk_assessment.get('risk_categories', {})
        if risk_categories:
            st.markdown("#### 🎯 **Risk Category Breakdown**")
            
            risk_df = pd.DataFrame(list(risk_categories.items()), columns=['Category', 'Score'])
            risk_df['Category'] = risk_df['Category'].str.replace('_', ' ').str.title()
            risk_df['Risk Level'] = risk_df['Score'].apply(
                lambda x: 'Critical' if x >= 8 else 'High' if x >= 6 else 'Medium' if x >= 4 else 'Low'
            )
            
            st.dataframe(risk_df, use_container_width=True)
        
        # Detailed Findings
        findings = analysis.get('detailed_findings', [])
        if findings:
            st.markdown("#### 🔍 **Detailed Findings**")
            
            # Filter by severity
            severity_filter = st.selectbox(
                "Filter by Severity:",
                ["All", "Critical", "High", "Medium", "Low"]
            )
            
            filtered_findings = findings if severity_filter == "All" else [
                f for f in findings if f.get('severity') == severity_filter
            ]
            
            for i, finding in enumerate(filtered_findings):
                severity = finding.get('severity', 'Unknown')
                severity_icons = {
                    'Critical': '🔴', 'High': '🟠', 'Medium': '🟡', 'Low': '🟢'
                }
                icon = severity_icons.get(severity, '⚪')
                
                with st.expander(f"{icon} **{finding.get('title', 'Unknown Finding')}** [{severity}]", 
                               expanded=(severity in ['Critical', 'High'] and i < 3)):
                    
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown("**📝 Description:**")
                        st.write(finding.get('description', 'No description available'))
                        
                        st.markdown("**💼 Business Impact:**")
                        st.warning(finding.get('business_impact', 'Impact assessment not available'))
                        
                        st.markdown("**⚖️ Compliance Impact:**")
                        st.info(finding.get('compliance_impact', 'Compliance impact not assessed'))
                    
                    with col2:
                        affected = finding.get('affected_entities', {})
                        
                        if affected.get('users'):
                            st.markdown("**👥 Affected Users:**")
                            for user in affected['users'][:5]:
                                st.write(f"• {user}")
                            if len(affected['users']) > 5:
                                st.write(f"• ... and {len(affected['users']) - 5} more")
                        
                        if affected.get('systems'):
                            st.markdown("**🖥️ Affected Systems:**")
                            for system in affected['systems']:
                                st.write(f"• {system}")
                    
                    # Remediation
                    remediation = finding.get('remediation', {})
                    if remediation:
                        st.markdown("**🔧 Recommended Actions:**")
                        
                        immediate = remediation.get('immediate_actions', [])
                        if immediate:
                            st.markdown("*Immediate (24-48 hours):*")
                            for action in immediate:
                                st.write(f"• {action}")
                        
                        long_term = remediation.get('long_term_solutions', [])
                        if long_term:
                            st.markdown("*Long-term solutions:*")
                            for solution in long_term:
                                st.write(f"• {solution}")
                        
                        effort = remediation.get('estimated_effort', '')
                        timeline = remediation.get('timeline', '')
                        responsible = remediation.get('responsible_party', '')
                        
                        if effort or timeline or responsible:
                            st.markdown("**📋 Implementation Details:**")
                            if effort:
                                st.write(f"**Effort:** {effort}")
                            if timeline:
                                st.write(f"**Timeline:** {timeline}")
                            if responsible:
                                st.write(f"**Responsible:** {responsible}")
        
        # Entitlement Remediation
        entitlement_rem = analysis.get('entitlement_remediation', {})
        if entitlement_rem:
            st.markdown("#### 🔧 **Entitlement Remediation Plan**")
            
            users_to_review = entitlement_rem.get('users_to_review', [])
            if users_to_review:
                st.markdown("**👥 Users Requiring Access Review:**")
                
                user_df = pd.DataFrame(users_to_review)
                if not user_df.empty:
                    st.dataframe(user_df, use_container_width=True)
            
            roles_to_modify = entitlement_rem.get('roles_to_modify', [])
            if roles_to_modify:
                st.markdown("**🔑 Roles Requiring Modification:**")
                
                for role in roles_to_modify:
                    with st.expander(f"**Role:** {role.get('role', 'Unknown')}"):
                        st.write(f"**Current Permissions:** {', '.join(role.get('current_permissions', []))}")
                        st.write(f"**Recommended Permissions:** {', '.join(role.get('recommended_permissions', []))}")
                        st.write(f"**Rationale:** {role.get('rationale', 'No rationale provided')}")
        
        # Recommendations
        recommendations = analysis.get('recommendations', {})
        if recommendations:
            st.markdown("#### 💡 **Strategic Recommendations**")
            
            for timeline_type, actions in recommendations.items():
                if actions:
                    timeline_icons = {
                        'immediate': '🚨',
                        'short_term': '⏰',
                        'strategic': '🎯'
                    }
                    icon = timeline_icons.get(timeline_type, '📌')
                    
                    st.markdown(f"**{icon} {timeline_type.replace('_', ' ').title()} Actions:**")
                    
                    for action in actions:
                        with st.expander(f"**Action:** {action.get('action', 'Unknown action')}"):
                            st.write(f"**Rationale:** {action.get('rationale', 'No rationale provided')}")
                            st.write(f"**Effort Required:** {action.get('effort', 'Unknown')}")
                            st.write(f"**Timeline:** {action.get('timeline', 'Unknown')}")
        
        # Generate Reports
        st.markdown("### 📄 **Professional Reports**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 **Generate Executive Report**", use_container_width=True):
                with st.spinner("Creating professional Excel report..."):
                    excel_bytes = generate_professional_excel_report(
                        st.session_state['processed_data'],
                        analysis,
                        "executive"
                    )
                    
                    if excel_bytes:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            "📥 **Download Excel Report**",
                            data=excel_bytes,
                            file_name=f"IAM_Executive_Report_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        st.success("✅ Executive report ready!")
                    else:
                        st.error("❌ Excel report generation failed")
        
        with col2:
            if st.button("📋 **Generate Summary Brief**", use_container_width=True):
                summary_text = f"""CONFIDENTIAL - IAM ANALYSIS EXECUTIVE BRIEF

Date: {datetime.now().strftime('%B %d, %Y')}
Analysis Type: {analysis_type}
Compliance Framework: {compliance_framework}

EXECUTIVE SUMMARY:
{analysis.get('executive_summary', 'Summary not available')}

KEY METRICS:
• Overall Risk Score: {risk_assessment.get('overall_risk_score', 0)}/10
• Total Users Analyzed: {metrics.get('total_users', 'N/A')}
• Critical/High Issues: {violations.get('critical', 0) + violations.get('high', 0)}
• Compliance Score: {metrics.get('compliance_score', 0)}%

IMMEDIATE ACTIONS REQUIRED:
{chr(10).join([f"• {action.get('action', '')}" for action in recommendations.get('immediate', [])])}

RECOMMENDED NEXT STEPS:
{chr(10).join([f"• {step}" for step in analysis.get('next_steps', [])])}

---
Generated by Professional IAM Analysis Platform
CONFIDENTIAL - FOR INTERNAL USE ONLY
"""
                
                st.download_button(
                    "📥 **Download Executive Brief**",
                    data=summary_text,
                    file_name=f"IAM_Executive_Brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
        
        with col3:
            # Chat with AI about results
            if st.button("💬 **Discuss Results with AI**", use_container_width=True):
                st.session_state['show_chat'] = True
        
        # AI Chat Interface
        if st.session_state.get('show_chat'):
            st.markdown("### 💬 **AI Consultant Discussion**")
            
            if 'chat_history' not in st.session_state:
                st.session_state['chat_history'] = []
            
            # Display chat history
            for chat in st.session_state['chat_history']:
                if chat['role'] == 'user':
                    st.markdown(f"**You:** {chat['message']}")
                else:
                    st.markdown(f"**AI Consultant:** {chat['message']}")
            
            # Chat input
            user_question = st.text_input(
                "Ask the AI consultant about your results:",
                placeholder="e.g., 'Which violations should I prioritize first?' or 'How can I present this to executive leadership?'"
            )
            
            if st.button("💬 **Ask AI Consultant**") and user_question:
                try:
                    context_prompt = f"""
                    You are a senior IAM consultant discussing analysis results with a client.
                    
                    Analysis Results Context:
                    {json.dumps(analysis, indent=2)[:3000]}
                    
                    Client Question: {user_question}
                    
                    Provide a professional, actionable response as an expert consultant.
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a senior IAM consultant providing expert advice to enterprise clients."},
                            {"role": "user", "content": context_prompt}
                        ],
                        temperature=0.1,
                        max_tokens=800
                    )
                    
                    ai_response = response.choices[0].message.content
                    
                    # Add to chat history
                    st.session_state['chat_history'].append({'role': 'user', 'message': user_question})
                    st.session_state['chat_history'].append({'role': 'ai', 'message': ai_response})
                    
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"AI consultation failed: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <p><strong>🏢 Professional IAM Analysis Platform</strong></p>
        <p>Enterprise-grade Identity and Access Management Analysis & Remediation</p>
        <p><em>Secure • Comprehensive • Actionable</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
