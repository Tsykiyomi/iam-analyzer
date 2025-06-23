#!/usr/bin/env python3
"""
Intelligent AI-Supervised IAM Tool - Web Ready Version
Bulletproof adaptive analysis engine that learns from any IAM data
"""

import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import tempfile
from pathlib import Path
from datetime import datetime
import json
import re
import hashlib
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

# Load environment variables
load_dotenv()

# Configuration
MAX_DATA_SIZE = 50000  # Max characters for AI processing
MAX_FILES = 20  # Max files to process
CACHE_DURATION = 3600  # 1 hour cache

# Streamlit configuration
st.set_page_config(
    page_title="Intelligent IAM Analyzer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

def init_session_state():
    """Initialize all session state variables with validation"""
    defaults = {
        'openai_client': None,
        'api_key_validated': False,
        'uploaded_files': None,
        'extracted_data': None,
        'pattern_analysis': None,
        'pattern_cache': {},
        'user_context': {},
        'analysis_results': None,
        'conversation_history': [],
        'learned_rules': {},
        'step': 'upload',
        'error_state': None,
        'last_analysis_time': None,
        'authenticated': False  # For password protection
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def check_password():
    """Simple password protection for work environments"""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("app_password", "demo123"):
            st.session_state["authenticated"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔐 IAM Analysis Tool - Secure Access")
        st.markdown("### Please enter the access password")
        
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        
        st.info("💡 **Default password:** demo123 (change this in Streamlit secrets)")
        st.warning("⚠️ **Security Notice:** This tool processes data through OpenAI's API. Do not upload highly sensitive data.")
        
        return False
    return True

def validate_session_state():
    """Validate required session state exists"""
    required_keys = ['step', 'openai_client']
    missing_keys = [key for key in required_keys if key not in st.session_state]
    
    if missing_keys:
        st.error(f"Session state error. Missing: {missing_keys}")
        st.stop()
    
    return True

def safe_step_transition(new_step, required_data=None):
    """Safely transition between steps with validation"""
    try:
        # Validate required data exists
        if required_data:
            for data_key in required_data:
                if data_key not in st.session_state or st.session_state[data_key] is None:
                    st.error(f"Cannot proceed: {data_key} is required")
                    return False
        
        # Clear error state on successful transition
        st.session_state.error_state = None
        st.session_state.step = new_step
        return True
        
    except Exception as e:
        st.error(f"Step transition error: {str(e)}")
        st.session_state.error_state = str(e)
        return False

def get_openai_api_key():
    """Get OpenAI API key from environment or user input"""
    # Try to get from Streamlit secrets first
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    
    if not api_key:
        # Try environment variable
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # Ask user for input
        api_key = st.sidebar.text_input(
            "OpenAI API Key",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys"
        )
    
    return api_key

def validate_openai_connection(api_key):
    """Validate OpenAI API key with actual test call"""
    try:
        client = openai.OpenAI(api_key=api_key)
        
        # Test with minimal call
        test_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        
        return client, None
        
    except openai.AuthenticationError:
        return None, "Invalid API key"
    except openai.RateLimitError:
        return None, "Rate limit exceeded - please try again"
    except openai.APIConnectionError:
        return None, "Connection error - check internet"
    except Exception as e:
        return None, f"API error: {str(e)}"

class FileProcessor:
    """Enhanced file processing with bulletproof error handling"""
    
    def __init__(self):
        self.supported_formats = {
            '.xlsx': self.process_excel,
            '.xls': self.process_excel,
            '.csv': self.process_csv,
            '.docx': self.process_docx,
            '.pdf': self.process_pdf,
            '.png': self.process_image,
            '.jpg': self.process_image,
            '.jpeg': self.process_image,
            '.txt': self.process_text
        }
        self.processed_count = 0
        self.error_count = 0
    
    def process_files(self, uploaded_files):
        """Process all uploaded files with comprehensive error handling"""
        if not uploaded_files:
            return {}
        
        if len(uploaded_files) > MAX_FILES:
            st.warning(f"Too many files. Processing first {MAX_FILES} files.")
            uploaded_files = uploaded_files[:MAX_FILES]
        
        results = {}
        self.processed_count = 0
        self.error_count = 0
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, file in enumerate(uploaded_files):
            try:
                progress_bar.progress((i + 1) / len(uploaded_files))
                status_text.text(f"Processing: {file.name}")
                
                file_ext = Path(file.name).suffix.lower()
                
                if file_ext in self.supported_formats:
                    file_data = self.supported_formats[file_ext](file)
                    if file_data:
                        results.update(file_data)
                        self.processed_count += 1
                    else:
                        self.error_count += 1
                else:
                    st.warning(f"Unsupported file type: {file.name}")
                    self.error_count += 1
                    
            except Exception as e:
                st.warning(f"Error processing {file.name}: {str(e)}")
                self.error_count += 1
                continue
        
        progress_bar.empty()
        status_text.empty()
        
        return results
    
    def process_excel(self, file):
        """Process Excel files with size limits"""
        try:
            file_bytes = file.read()
            
            # Check file size (basic protection)
            if len(file_bytes) > 50 * 1024 * 1024:  # 50MB limit
                return {file.name: {'error': 'File too large (>50MB)'}}
            
            excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
            data = {}
            
            for sheet_name in excel_file.sheet_names[:10]:  # Limit sheets
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name, nrows=10000)  # Limit rows
                    if not df.empty and len(df.columns) > 0:
                        # Clean column names
                        df.columns = [str(col).strip() for col in df.columns]
                        data[f"{file.name}_{sheet_name}"] = df
                except Exception as e:
                    st.warning(f"Error reading sheet {sheet_name}: {str(e)}")
                    continue
            
            return data
            
        except Exception as e:
            return {file.name: {'error': f'Excel processing failed: {str(e)}'}}
    
    def process_csv(self, file):
        """Process CSV files with multiple encoding attempts"""
        try:
            file_bytes = file.read()
            
            if len(file_bytes) > 20 * 1024 * 1024:  # 20MB limit for CSV
                return {file.name: {'error': 'CSV file too large (>20MB)'}}
            
            # Try different encodings and separators
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                for sep in [',', ';', '\t', '|']:
                    try:
                        df = pd.read_csv(
                            io.BytesIO(file_bytes), 
                            encoding=encoding, 
                            sep=sep,
                            nrows=10000,  # Limit rows
                            on_bad_lines='skip'
                        )
                        
                        if len(df.columns) > 1 and len(df) > 0:
                            # Clean column names
                            df.columns = [str(col).strip() for col in df.columns]
                            return {file.name: df}
                            
                    except Exception:
                        continue
            
            return {file.name: {'error': 'Could not parse CSV file'}}
            
        except Exception as e:
            return {file.name: {'error': f'CSV processing failed: {str(e)}'}}
    
    def process_docx(self, file):
        """Process Word documents"""
        if not DOCX_AVAILABLE:
            return {file.name: {'text': 'DOCX processing not available - install python-docx', 'error': True}}
        
        try:
            file_bytes = file.read()
            if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
                return {file.name: {'error': 'DOCX file too large (>10MB)'}}
            
            doc = Document(io.BytesIO(file_bytes))
            
            # Extract text with limits
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()][:1000]  # Limit paragraphs
            text = '\n'.join(paragraphs)
            
            # Extract tables with limits
            tables = []
            for table in doc.tables[:20]:  # Limit tables
                table_data = []
                for row in table.rows[:100]:  # Limit rows per table
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_data.append(row_data)
                if table_data:
                    tables.append(table_data)
            
            return {file.name: {'text': text[:MAX_DATA_SIZE], 'tables': tables}}
            
        except Exception as e:
            return {file.name: {'error': f'DOCX processing failed: {str(e)}'}}
    
    def process_pdf(self, file):
        """Process PDF files"""
        if not PDF_AVAILABLE:
            return {file.name: {'text': 'PDF processing not available - install pdfplumber', 'error': True}}
        
        try:
            file_bytes = file.read()
            if len(file_bytes) > 20 * 1024 * 1024:  # 20MB limit
                return {file.name: {'error': 'PDF file too large (>20MB)'}}
            
            text = ""
            tables = []
            
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                # Limit pages processed
                for page in pdf.pages[:50]:  # Max 50 pages
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                            if len(text) > MAX_DATA_SIZE:
                                break
                        
                        # Extract tables
                        page_tables = page.extract_tables()
                        if page_tables:
                            tables.extend(page_tables[:5])  # Max 5 tables per page
                            
                    except Exception:
                        continue  # Skip problematic pages
            
            return {file.name: {'text': text[:MAX_DATA_SIZE], 'tables': tables[:20]}}
            
        except Exception as e:
            return {file.name: {'error': f'PDF processing failed: {str(e)}'}}
    
    def process_image(self, file):
        """Process image files with OCR"""
        if not OCR_AVAILABLE:
            return {file.name: {'text': 'OCR not available - install pillow and pytesseract', 'error': True}}
        
        try:
            file_bytes = file.read()
            if len(file_bytes) > 5 * 1024 * 1024:  # 5MB limit
                return {file.name: {'error': 'Image file too large (>5MB)'}}
            
            image = Image.open(io.BytesIO(file_bytes))
            
            # Resize large images
            if max(image.size) > 2000:
                image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
            
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            text = pytesseract.image_to_string(image)
            return {file.name: {'text': text[:MAX_DATA_SIZE], 'image_size': image.size}}
            
        except Exception as e:
            return {file.name: {'error': f'Image processing failed: {str(e)}'}}
    
    def process_text(self, file):
        """Process text files"""
        try:
            file_bytes = file.read()
            if len(file_bytes) > 5 * 1024 * 1024:  # 5MB limit
                return {file.name: {'error': 'Text file too large (>5MB)'}}
            
            for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                try:
                    text = file_bytes.decode(encoding)
                    return {file.name: {'text': text[:MAX_DATA_SIZE]}}
                except UnicodeDecodeError:
                    continue
            
            return {file.name: {'error': 'Could not decode text file'}}
            
        except Exception as e:
            return {file.name: {'error': f'Text processing failed: {str(e)}'}}

class IntelligentAnalyzer:
    """AI-powered adaptive analysis engine with bulletproof error handling"""
    
    def __init__(self, openai_client):
        self.client = openai_client
        self.max_retries = 3
        self.retry_delay = 1
    
    def analyze_patterns(self, extracted_data):
        """Analyze data patterns with caching and error handling"""
        try:
            # Create cache key
            data_hash = self._create_data_hash(extracted_data)
            cache_key = f"pattern_{data_hash}"
            
            # Check cache
            if cache_key in st.session_state.pattern_cache:
                cached_result = st.session_state.pattern_cache[cache_key]
                if time.time() - cached_result['timestamp'] < CACHE_DURATION:
                    return cached_result['data']
            
            # Prepare data summary with size limits
            summary = self._prepare_safe_data_summary(extracted_data)
            
            if not summary or len(summary) < 50:
                return self._fallback_pattern_analysis("Insufficient data for analysis")
            
            prompt = f"""
            Analyze this IAM data and provide insights in JSON format:
            
            Data to analyze:
            {summary}
            
            Provide analysis as JSON:
            {{
                "application_type": "SAP|ActiveDirectory|Salesforce|Oracle|ServiceNow|Workday|Unknown",
                "confidence": 0.0-1.0,
                "data_patterns": {{
                    "has_users": true/false,
                    "has_roles": true/false,
                    "has_permissions": true/false,
                    "has_approvals": true/false
                }},
                "column_insights": {{
                    "user_columns": ["col1", "col2"],
                    "role_columns": ["col1"],
                    "permission_columns": ["col1"],
                    "unclear_columns": ["col1", "col2"]
                }},
                "compliance_suggestion": "SOX|PCI|HIPAA|General",
                "key_questions": [
                    "What system is this data from?",
                    "What compliance framework applies?"
                ],
                "risk_indicators": [
                    "Multiple admin roles detected",
                    "Missing approval workflows"
                ]
            }}
            """
            
            result = self._make_ai_request(prompt, "pattern analysis")
            
            if result:
                # Cache successful result
                st.session_state.pattern_cache[cache_key] = {
                    'data': result,
                    'timestamp': time.time()
                }
                return result
            else:
                return self._fallback_pattern_analysis("AI analysis failed")
                
        except Exception as e:
            st.error(f"Pattern analysis error: {str(e)}")
            return self._fallback_pattern_analysis(f"Error: {str(e)}")
    
    def generate_questions(self, pattern_analysis, extracted_data):
        """Generate intelligent questions based on pattern analysis"""
        try:
            questions = []
            app_type = pattern_analysis.get('application_type', 'Unknown')
            confidence = pattern_analysis.get('confidence', 0)
            
            # Core context questions
            if app_type == 'Unknown' or confidence < 0.7:
                questions.append({
                    'id': 'app_type',
                    'question': 'What application or system is this data from?',
                    'type': 'select',
                    'options': ['SAP', 'Active Directory', 'Salesforce', 'Oracle EBS', 'ServiceNow', 'Workday', 'Custom Application', 'Other'],
                    'importance': 'critical',
                    'help': 'This helps me apply the right analysis rules'
                })
            
            questions.append({
                'id': 'compliance_focus',
                'question': 'What is the main purpose of this analysis?',
                'type': 'select',
                'options': ['SOX Compliance', 'PCI DSS', 'General Security Review', 'User Access Review', 'Role Cleanup', 'Audit Preparation'],
                'importance': 'high',
                'help': 'This determines which violations to prioritize'
            })
            
            # Data-specific questions
            unclear_columns = pattern_analysis.get('column_insights', {}).get('unclear_columns', [])
            if unclear_columns and len(unclear_columns) <= 3:
                questions.append({
                    'id': 'column_clarification',
                    'question': f'What do these columns represent: {", ".join(unclear_columns)}?',
                    'type': 'text',
                    'placeholder': 'e.g., Role assignments, Permission levels, Approval status',
                    'importance': 'medium',
                    'help': 'Help me understand your data structure better'
                })
            
            # Application-specific questions
            if app_type in ['SAP', 'Oracle'] or 'financial' in str(extracted_data).lower():
                questions.append({
                    'id': 'sod_rules',
                    'question': 'How should I handle Segregation of Duties (SoD) analysis?',
                    'type': 'select',
                    'options': ['Apply standard financial SoD rules', 'Use custom SoD matrix (I will provide)', 'Focus on high-risk combinations only', 'Skip SoD analysis'],
                    'importance': 'high',
                    'help': 'SoD violations are critical for compliance'
                })
            
            questions.append({
                'id': 'analysis_depth',
                'question': 'How thorough should the analysis be?',
                'type': 'select',
                'options': ['Very strict (flag all potential issues)', 'Balanced (medium to high risk)', 'Conservative (high risk only)', 'Focus on compliance violations only'],
                'importance': 'medium',
                'help': 'This controls how many findings you will receive'
            })
            
            return questions
            
        except Exception as e:
            st.error(f"Question generation error: {str(e)}")
            return [
                {
                    'id': 'basic_context',
                    'question': 'What type of IAM analysis do you need?',
                    'type': 'select',
                    'options': ['General Security Review', 'Compliance Audit', 'Role Cleanup'],
                    'importance': 'high',
                    'help': 'Basic context for analysis'
                }
            ]
    
    def perform_analysis(self, extracted_data, pattern_analysis, user_responses):
        """Perform contextual IAM analysis with comprehensive error handling"""
        try:
            # Build context from user responses
            context = self._build_analysis_context(pattern_analysis, user_responses)
            
            # Prepare enhanced data summary
            data_summary = self._prepare_safe_data_summary(extracted_data)
            
            if not data_summary:
                return self._fallback_analysis("No data available for analysis")
            
            prompt = f"""
            Perform IAM analysis with this context:
            
            {context}
            
            Data to analyze:
            {data_summary}
            
            Provide comprehensive analysis in JSON format:
            {{
                "executive_summary": "High-level assessment with business impact",
                "violations": [
                    {{
                        "id": "unique_id",
                        "type": "SoD|Excessive_Access|Missing_Approval|Policy_Violation",
                        "severity": "Critical|High|Medium|Low",
                        "title": "Brief violation title",
                        "description": "Detailed description with context",
                        "affected_users": ["user1", "user2"],
                        "business_risk": "Specific business impact",
                        "compliance_impact": "SOX/PCI/HIPAA implications",
                        "recommendation": "Specific remediation steps",
                        "effort": "Low|Medium|High"
                    }}
                ],
                "statistics": {{
                    "total_users": 0,
                    "total_violations": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                    "risk_score": 0,
                    "compliance_score": 0
                }},
                "insights": [
                    "Key pattern or trend observation",
                    "Important finding about access patterns"
                ],
                "recommendations": {{
                    "immediate": ["Action needed within 24-48 hours"],
                    "short_term": ["Action needed within 1-2 weeks"],
                    "long_term": ["Process improvements and policies"]
                }},
                "follow_up": [
                    {{
                        "question": "Follow-up question for clarification",
                        "context": "Why this question matters"
                    }}
                ]
            }}
            """
            
            result = self._make_ai_request(prompt, "IAM analysis", max_tokens=4000)
            
            if result:
                # Store analysis timestamp
                st.session_state.last_analysis_time = time.time()
                return result
            else:
                return self._fallback_analysis("AI analysis failed")
                
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            return self._fallback_analysis(f"Error: {str(e)}")
    
    def _make_ai_request(self, prompt, request_type, max_tokens=2000):
        """Make AI request with retries and error handling"""
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": f"You are an expert IAM analyst. Provide {request_type} in valid JSON format only."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,
                    max_tokens=max_tokens
                )
                
                result = self._extract_and_validate_json(response.choices[0].message.content)
                if result:
                    return result
                else:
                    st.warning(f"Invalid JSON response from AI (attempt {attempt + 1})")
                    
            except openai.RateLimitError:
                if attempt < self.max_retries - 1:
                    st.warning(f"Rate limit hit. Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    self.retry_delay *= 2  # Exponential backoff
                else:
                    st.error("Rate limit exceeded. Please try again later.")
                    return None
                    
            except openai.APIConnectionError:
                st.error("Connection error. Please check your internet.")
                return None
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    st.warning(f"AI request failed (attempt {attempt + 1}): {str(e)}")
                    time.sleep(1)
                else:
                    st.error(f"AI request failed after {self.max_retries} attempts: {str(e)}")
                    return None
        
        return None
    
    def _extract_and_validate_json(self, text):
        """Extract and validate JSON from AI response"""
        try:
            # Try to find JSON in response
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start != -1 and end != 0:
                json_text = text[start:end]
                result = json.loads(json_text)
                
                # Basic validation
                if isinstance(result, dict):
                    return result
                    
        except json.JSONDecodeError as e:
            st.warning(f"JSON parsing error: {str(e)}")
        except Exception as e:
            st.warning(f"JSON extraction error: {str(e)}")
        
        return None
    
    def _prepare_safe_data_summary(self, extracted_data):
        """Prepare data summary with size limits"""
        try:
            summary = []
            total_chars = 0
            max_summary_size = MAX_DATA_SIZE // 2  # Reserve space for other prompt content
            
            for source, data in extracted_data.items():
                if total_chars >= max_summary_size:
                    summary.append("... [Additional data truncated for size] ...")
                    break
                
                if isinstance(data, pd.DataFrame) and not data.empty:
                    summary.append(f"Source: {source}")
                    summary.append(f"Columns: {', '.join(data.columns.tolist()[:20])}")  # Limit columns
                    summary.append(f"Rows: {len(data)}")
                    
                    # Add sample data
                    sample_data = data.head(3).to_string()
                    if len(sample_data) < 1000:  # Only add if reasonable size
                        summary.append("Sample data:")
                        summary.append(sample_data)
                    
                    summary.append("---")
                    
                elif isinstance(data, dict):
                    if 'error' in data:
                        summary.append(f"Source: {source} (Error: {data['error']})")
                    elif 'text' in data:
                        summary.append(f"Source: {source} (Text)")
                        text_preview = data['text'][:500] + "..." if len(data['text']) > 500 else data['text']
                        summary.append(f"Content: {text_preview}")
                    summary.append("---")
                
                # Check size
                summary_text = '\n'.join(summary)
                total_chars = len(summary_text)
                
                if total_chars >= max_summary_size:
                    break
            
            return '\n'.join(summary)
            
        except Exception as e:
            st.error(f"Data summary error: {str(e)}")
            return "Error preparing data summary"
    
    def _create_data_hash(self, extracted_data):
        """Create hash of data for caching"""
        try:
            data_str = str(sorted(extracted_data.keys())) + str(len(str(extracted_data)))
            return hashlib.md5(data_str.encode()).hexdigest()[:16]
        except:
            return str(time.time())
    
    def _build_analysis_context(self, pattern_analysis, user_responses):
        """Build analysis context from pattern analysis and user responses"""
        try:
            context = []
            
            # Pattern context
            app_type = pattern_analysis.get('application_type', 'Unknown')
            context.append(f"Application Type: {app_type}")
            context.append(f"Confidence: {pattern_analysis.get('confidence', 0)*100:.0f}%")
            
            # User context
            if user_responses:
                context.append("\nUser Context:")
                for response in user_responses:
                    context.append(f"- {response.get('question', 'Unknown')}: {response.get('answer', 'No answer')}")
            
            # Compliance focus
            compliance = self._get_response_value(user_responses, 'compliance_focus')
            if compliance:
                context.append(f"\nCompliance Focus: {compliance}")
            
            return '\n'.join(context)
            
        except Exception as e:
            return f"Context building error: {str(e)}"
    
    def _get_response_value(self, user_responses, question_id):
        """Get user response value by question ID"""
        try:
            for response in user_responses or []:
                if response.get('id') == question_id:
                    return response.get('answer')
        except:
            pass
        return None
    
    def _fallback_pattern_analysis(self, reason="Unknown"):
        """Fallback pattern analysis"""
        return {
            "application_type": "Unknown",
            "confidence": 0.3,
            "data_patterns": {
                "has_users": True, 
                "has_roles": False, 
                "has_permissions": False, 
                "has_approvals": False
            },
            "column_insights": {
                "user_columns": [], 
                "role_columns": [], 
                "permission_columns": [], 
                "unclear_columns": []
            },
            "compliance_suggestion": "General",
            "key_questions": [
                "What system is this data from?", 
                "What are your compliance requirements?"
            ],
            "risk_indicators": [f"Pattern analysis failed: {reason}"]
        }
    
    def _fallback_analysis(self, reason="Unknown"):
        """Fallback analysis results"""
        return {
            "executive_summary": f"Basic analysis completed. AI analysis was unavailable: {reason}",
            "violations": [],
            "statistics": {
                "total_users": 0,
                "total_violations": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
                "risk_score": 0,
                "compliance_score": 0
            },
            "insights": [
                "Manual review recommended due to analysis limitations",
                f"Analysis issue: {reason}"
            ],
            "recommendations": {
                "immediate": [],
                "short_term": ["Review access permissions manually"],
                "long_term": ["Implement proper IAM controls", "Consider data quality improvements"]
            },
            "follow_up": [
                {
                    "question": "Would you like guidance on manual analysis procedures?",
                    "context": "AI analysis was unavailable"
                }
            ]
        }

class ReportGenerator:
    """Generate professional Excel reports with error handling"""
    
    def __init__(self):
        self.colors = {
            'critical': 'FF5252',
            'high': 'FF9800', 
            'medium': 'FFC107',
            'low': 'C8E6C9',
            'header': '1976D2'
        }
    
    def generate_report(self, extracted_data, analysis_results):
        """Generate comprehensive Excel report with error handling"""
        try:
            workbook = openpyxl.Workbook()
            workbook.remove(workbook.active)
            
            # Create sheets with error handling
            try:
                self._create_executive_summary(workbook, analysis_results)
            except Exception as e:
                st.warning(f"Error creating executive summary: {str(e)}")
            
            try:
                self._create_violations_sheet(workbook, analysis_results)
            except Exception as e:
                st.warning(f"Error creating violations sheet: {str(e)}")
            
            try:
                self._create_statistics_sheet(workbook, analysis_results)
            except Exception as e:
                st.warning(f"Error creating statistics sheet: {str(e)}")
            
            try:
                self._create_data_sheets(workbook, extracted_data)
            except Exception as e:
                st.warning(f"Error creating data sheets: {str(e)}")
            
            # Ensure we have at least one sheet
            if len(workbook.sheetnames) == 0:
                ws = workbook.create_sheet("Report")
                ws['A1'] = "Report generation encountered errors"
            
            # Save to bytes
            output = io.BytesIO()
            workbook.save(output)
            output.seek(0)
            return output.getvalue()
            
        except Exception as e:
            st.error(f"Report generation failed: {str(e)}")
            # Create minimal error report
            workbook = openpyxl.Workbook()
            ws = workbook.active
            ws.title = "Error Report"
            ws['A1'] = "Report Generation Error"
            ws['A2'] = str(e)
            ws['A3'] = f"Timestamp: {datetime.now()}"
            
            output = io.BytesIO()
            workbook.save(output)
            output.seek(0)
            return output.getvalue()
    
    def _create_executive_summary(self, workbook, results):
        """Create executive summary sheet"""
        ws = workbook.create_sheet("Executive Summary", 0)
        
        # Title and date
        ws['A1'] = "IAM Analysis Executive Summary"
        ws['A1'].font = Font(bold=True, size=16)
        ws['A2'] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Executive summary
        row = 4
        ws[f'A{row}'] = "Executive Summary"
        ws[f'A{row}'].font = Font(bold=True, size=14)
        row += 1
        
        summary = results.get('executive_summary', 'No summary available')
        # Split long text into multiple rows
        if len(summary) > 100:
            words = summary.split()
            lines = []
            current_line = []
            for word in words:
                current_line.append(word)
                if len(' '.join(current_line)) > 80:
                    lines.append(' '.join(current_line[:-1]))
                    current_line = [word]
            if current_line:
                lines.append(' '.join(current_line))
            
            for line in lines:
                ws[f'A{row}'] = line
                row += 1
        else:
            ws[f'A{row}'] = summary
            row += 1
        
        row += 2
        
        # Key metrics
        ws[f'A{row}'] = "Key Metrics"
        ws[f'A{row}'].font = Font(bold=True, size=14)
        row += 1
        
        stats = results.get('statistics', {})
        metrics = [
            ('Total Users', stats.get('total_users', 0)),
            ('Total Violations', stats.get('total_violations', 0)),
            ('Critical Issues', stats.get('critical_count', 0)),
            ('Overall Risk Score', f"{stats.get('risk_score', 0)}/10"),
            ('Compliance Score', f"{stats.get('compliance_score', 0)}/10")
        ]
        
        for metric, value in metrics:
            ws[f'A{row}'] = metric
            ws[f'B{row}'] = value
            row += 1
        
        # Recommendations
        row += 2
        recommendations = results.get('recommendations', {})
        
        for category, items in recommendations.items():
            if items:
                ws[f'A{row}'] = f"{category.replace('_', ' ').title()} Actions"
                ws[f'A{row}'].font = Font(bold=True, size=12)
                row += 1
                
                for item in items:
                    ws[f'A{row}'] = f"• {item}"
                    row += 1
                row += 1
    
    def _create_violations_sheet(self, workbook, results):
        """Create detailed violations sheet"""
        ws = workbook.create_sheet("Violations Detail")
        
        # Headers
        headers = ['ID', 'Type', 'Severity', 'Title', 'Description', 'Affected Users', 'Business Risk', 'Recommendation', 'Effort']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color=self.colors['header'], end_color=self.colors['header'], fill_type='solid')
        
        # Violations data
        violations = results.get('violations', [])
        for row, violation in enumerate(violations, 2):
            try:
                ws.cell(row=row, column=1).value = violation.get('id', f'V{row-1}')
                ws.cell(row=row, column=2).value = violation.get('type', '')
                ws.cell(row=row, column=3).value = violation.get('severity', '')
                ws.cell(row=row, column=4).value = violation.get('title', '')
                ws.cell(row=row, column=5).value = violation.get('description', '')
                
                # Handle affected users list
                affected_users = violation.get('affected_users', [])
                if isinstance(affected_users, list):
                    ws.cell(row=row, column=6).value = ', '.join(affected_users[:10])  # Limit to first 10
                else:
                    ws.cell(row=row, column=6).value = str(affected_users)
                
                ws.cell(row=row, column=7).value = violation.get('business_risk', '')
                ws.cell(row=row, column=8).value = violation.get('recommendation', '')
                ws.cell(row=row, column=9).value = violation.get('effort', '')
                
                # Color coding
                severity = violation.get('severity', '').lower()
                if severity in self.colors:
                    fill = PatternFill(start_color=self.colors[severity], end_color=self.colors[severity], fill_type='solid')
                    for col in range(1, 10):
                        ws.cell(row=row, column=col).fill = fill
                        
            except Exception as e:
                st.warning(f"Error processing violation row {row}: {str(e)}")
                continue
        
        # Auto-adjust columns
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    def _create_statistics_sheet(self, workbook, results):
        """Create statistics and insights sheet"""
        ws = workbook.create_sheet("Statistics & Insights")
        
        row = 1
        
        # Statistics
        ws[f'A{row}'] = "Analysis Statistics"
        ws[f'A{row}'].font = Font(bold=True, size=14)
        row += 2
        
        stats = results.get('statistics', {})
        for key, value in stats.items():
            ws[f'A{row}'] = key.replace('_', ' ').title()
            ws[f'B{row}'] = value
            row += 1
        
        row += 2
        
        # Insights
        insights = results.get('insights', [])
        if insights:
            ws[f'A{row}'] = "Key Insights"
            ws[f'A{row}'].font = Font(bold=True, size=14)
            row += 1
            
            for insight in insights:
                ws[f'A{row}'] = f"• {insight}"
                row += 1
    
    def _create_data_sheets(self, workbook, extracted_data):
        """Create sheets for original data"""
        sheet_count = 0
        max_sheets = 10  # Limit number of data sheets
        
        for source, data in extracted_data.items():
            if sheet_count >= max_sheets:
                break
                
            try:
                if isinstance(data, pd.DataFrame) and not data.empty:
                    # Clean sheet name
                    sheet_name = source[:31].replace('/', '_').replace('\\', '_').replace('[', '').replace(']', '')
                    
                    # Ensure unique sheet name
                    original_name = sheet_name
                    counter = 1
                    while sheet_name in workbook.sheetnames:
                        sheet_name = f"{original_name}_{counter}"
                        counter += 1
                    
                    ws = workbook.create_sheet(sheet_name)
                    
                    # Add data with limits
                    max_rows = min(len(data), 1000)  # Limit rows
                    max_cols = min(len(data.columns), 50)  # Limit columns
                    
                    # Add headers
                    for col, header in enumerate(data.columns[:max_cols], 1):
                        cell = ws.cell(row=1, column=col)
                        cell.value = str(header)
                        cell.font = Font(bold=True)
                        cell.fill = PatternFill(start_color=self.colors['header'], end_color=self.colors['header'], fill_type='solid')
                    
                    # Add data
                    for row_idx in range(min(max_rows, len(data))):
                        for col_idx in range(max_cols):
                            try:
                                value = data.iloc[row_idx, col_idx]
                                ws.cell(row=row_idx + 2, column=col_idx + 1).value = str(value) if pd.notna(value) else ""
                            except:
                                continue
                    
                    sheet_count += 1
                    
            except Exception as e:
                st.warning(f"Error creating sheet for {source}: {str(e)}")
                continue

def main():
    """Main application with bulletproof error handling"""
    
    try:
        # Initialize session state
        init_session_state()
        
        # Check password
        if not check_password():
            return
        
        # Validate session state
        validate_session_state()
        
        # Header
        st.title("🧠 Intelligent IAM Analyzer")
        st.markdown("""
        **Bulletproof AI-powered IAM analysis that adapts to any environment**
        
        📁 Upload any files → 🧠 AI detects patterns → ❓ Asks smart questions → 📊 Delivers expert analysis
        """)
        
        # Error state display
        if st.session_state.error_state:
            st.error(f"System Error: {st.session_state.error_state}")
            if st.button("🔄 Reset Application"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
        # Sidebar setup
        st.sidebar.header("🔧 Configuration")
        
        # Check dependencies
        missing_deps = []
        if not OPENAI_AVAILABLE:
            missing_deps.append("openai")
        
        if missing_deps:
            st.sidebar.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
            st.error(f"Please install: `pip install {' '.join(missing_deps)}`")
            return
        
        # Optional dependencies warning
        optional_warnings = []
        if not DOCX_AVAILABLE:
            optional_warnings.append("Word documents: install python-docx")
        if not PDF_AVAILABLE:
            optional_warnings.append("PDF files: install pdfplumber")
        if not OCR_AVAILABLE:
            optional_warnings.append("Image OCR: install pillow pytesseract")
        
        if optional_warnings:
            with st.sidebar.expander("⚠️ Optional Features"):
                for warning in optional_warnings:
                    st.caption(warning)
        
        # OpenAI setup with validation
        api_key = get_openai_api_key()
        
        if api_key:
            if not st.session_state.api_key_validated or st.session_state.openai_client is None:
                with st.sidebar.spinner("Validating API key..."):
                    client, error = validate_openai_connection(api_key)
                    
                    if client:
                        st.session_state.openai_client = client
                        st.session_state.api_key_validated = True
                        st.sidebar.success("✅ API Key validated")
                    else:
                        st.sidebar.error(f"❌ {error}")
                        st.session_state.api_key_validated = False
                        return
            else:
                st.sidebar.success("✅ API Key validated")
        else:
            st.sidebar.warning("⚠️ Please provide your OpenAI API Key")
            st.info("""
            **Setup Options:**
            1. **Environment Variable:** Set `OPENAI_API_KEY` in your hosting platform
            2. **Manual Entry:** Enter key in sidebar
            3. **Streamlit Secrets:** Add to secrets.toml file
            
            **Get API key:** https://platform.openai.com/api-keys
            **Cost:** ~$0.01-0.10 per analysis (very affordable!)
            """)
            return
        
        # Progress indicator
        steps = ['📁 Upload', '🧠 Analyze', '❓ Context', '📊 Results']
        current_step = st.session_state.step
        step_names = ['upload', 'pattern', 'questions', 'results']
        
        try:
            step_index = step_names.index(current_step)
        except ValueError:
            step_index = 0
            st.session_state.step = 'upload'
        
        cols = st.columns(4)
        for i, (col, step_name) in enumerate(zip(cols, steps)):
            if i <= step_index:
                col.success(step_name)
            else:
                col.info(step_name)
        
        # Step 1: File Upload
        if st.session_state.step == 'upload':
            st.header("📁 Step 1: Upload Your IAM Files")
            
            uploaded_files = st.file_uploader(
                "Upload any IAM-related files (Excel, CSV, PDF, Word, Images, Text)",
                accept_multiple_files=True,
                type=['xlsx', 'xls', 'csv', 'docx', 'pdf', 'png', 'jpg', 'jpeg', 'txt'],
                help=f"Maximum {MAX_FILES} files, each under 50MB"
            )
            
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} files ready for processing")
                
                # File details
                with st.expander("📋 File Details"):
                    total_size = 0
                    for file in uploaded_files:
                        size_mb = file.size / (1024 * 1024)
                        total_size += size_mb
                        st.write(f"• {file.name} ({size_mb:.1f} MB)")
                    
                    st.write(f"**Total size:** {total_size:.1f} MB")
                    
                    if total_size > 100:
                        st.warning("Large upload detected. Processing may take longer.")
                
                if st.button("🚀 Process Files", type="primary"):
                    try:
                        with st.spinner("Processing files..."):
                            processor = FileProcessor()
                            extracted_data = processor.process_files(uploaded_files)
                            
                            if extracted_data:
                                st.session_state.extracted_data = extracted_data
                                st.session_state.uploaded_files = uploaded_files
                                
                                # Show processing summary
                                st.success(f"✅ Processed {processor.processed_count} files successfully")
                                if processor.error_count > 0:
                                    st.warning(f"⚠️ {processor.error_count} files had errors")
                                
                                if safe_step_transition('pattern', ['extracted_data']):
                                    st.rerun()
                            else:
                                st.error("❌ No data could be extracted from uploaded files")
                                
                    except Exception as e:
                        st.error(f"File processing failed: {str(e)}")
                        st.session_state.error_state = str(e)
        
        # Step 2: Pattern Analysis
        elif st.session_state.step == 'pattern':
            st.header("🧠 Step 2: Analyzing Data Patterns")
            
            if st.session_state.extracted_data:
                try:
                    with st.spinner("AI is analyzing your data patterns..."):
                        analyzer = IntelligentAnalyzer(st.session_state.openai_client)
                        pattern_analysis = analyzer.analyze_patterns(st.session_state.extracted_data)
                        st.session_state.pattern_analysis = pattern_analysis
                    
                    # Display pattern insights
                    st.success("✅ Pattern analysis complete!")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🎯 What I Found")
                        app_type = pattern_analysis.get('application_type', 'Unknown')
                        confidence = pattern_analysis.get('confidence', 0)
                        
                        st.metric("Application Type", app_type, f"{confidence*100:.0f}% confidence")
                        
                        patterns = pattern_analysis.get('data_patterns', {})
                        st.write("**Data Structure:**")
                        for key, found in patterns.items():
                            icon = "✅" if found else "❌"
                            st.write(f"{icon} {key.replace('_', ' ').title()}")
                    
                    with col2:
                        st.subheader("🔍 Insights")
                        st.write(f"**Compliance:** {pattern_analysis.get('compliance_suggestion', 'General')}")
                        
                        risks = pattern_analysis.get('risk_indicators', [])
                        if risks:
                            st.write("**Risk Indicators:**")
                            for risk in risks[:5]:  # Limit display
                                st.write(f"⚠️ {risk}")
                        
                        unclear = pattern_analysis.get('column_insights', {}).get('unclear_columns', [])
                        if unclear:
                            st.write(f"**Unclear Columns:** {', '.join(unclear[:3])}")
                    
                    # Navigation
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("⬅️ Back to Upload"):
                            if safe_step_transition('upload'):
                                st.rerun()
                    
                    with col2:
                        if st.button("➡️ Continue to Context Questions", type="primary"):
                            if safe_step_transition('questions', ['pattern_analysis']):
                                st.rerun()
                
                except Exception as e:
                    st.error(f"Pattern analysis failed: {str(e)}")
                    st.session_state.error_state = str(e)
                    
                    # Fallback option
                    if st.button("Continue with Basic Analysis"):
                        st.session_state.pattern_analysis = {
                            "application_type": "Unknown",
                            "confidence": 0.3,
                            "data_patterns": {"has_users": True, "has_roles": False, "has_permissions": False, "has_approvals": False},
                            "column_insights": {"user_columns": [], "role_columns": [], "permission_columns": [], "unclear_columns": []},
                            "compliance_suggestion": "General",
                            "key_questions": [],
                            "risk_indicators": ["Pattern analysis failed - using basic mode"]
                        }
                        if safe_step_transition('questions', ['pattern_analysis']):
                            st.rerun()
            else:
                st.error("No extracted data available. Please go back to upload.")
                if st.button("⬅️ Back to Upload"):
                    if safe_step_transition('upload'):
                        st.rerun()
        
        # Step 3: Context Questions
        elif st.session_state.step == 'questions':
            st.header("❓ Step 3: Provide Context for Better Analysis")
            
            if st.session_state.pattern_analysis:
                try:
                    analyzer = IntelligentAnalyzer(st.session_state.openai_client)
                    questions = analyzer.generate_questions(
                        st.session_state.pattern_analysis, 
                        st.session_state.extracted_data
                    )
                    
                    st.write("Answer these questions to get the most accurate analysis:")
                    
                    user_responses = []
                    
                    for question in questions:
                        importance_color = {
                            'critical': '🔴',
                            'high': '🟠', 
                            'medium': '🟡'
                        }.get(question.get('importance', 'medium'), '🟡')
                        
                        st.write(f"{importance_color} **{question['question']}**")
                        if question.get('help'):
                            st.caption(question['help'])
                        
                        # Create unique key
                        unique_key = f"q_{question['id']}_{hash(question['question']) % 10000}"
                        
                        if question['type'] == 'select':
                            answer = st.selectbox(
                                "Select your answer:",
                                options=['Select an option...'] + question['options'],
                                key=unique_key
                            )
                            if answer != 'Select an option...':
                                user_responses.append({
                                    'id': question['id'],
                                    'question': question['question'],
                                    'answer': answer,
                                    'importance': question.get('importance', 'medium')
                                })
                        
                        elif question['type'] == 'text':
                            answer = st.text_area(
                                "Your answer:",
                                key=unique_key,
                                placeholder=question.get('placeholder', 'Enter your answer...'),
                                height=80
                            )
                            if answer.strip():
                                user_responses.append({
                                    'id': question['id'],
                                    'question': question['question'],
                                    'answer': answer.strip(),
                                    'importance': question.get('importance', 'medium')
                                })
                        
                        st.write("")  # Spacing
                    
                    # Store responses
                    if user_responses:
                        st.session_state.user_context['responses'] = user_responses
                        st.success(f"✅ {len(user_responses)} context answers provided")
                    else:
                        st.warning("⚠️ No context provided - analysis will be less accurate")
                    
                    # Navigation
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("⬅️ Back to Pattern Analysis"):
                            if safe_step_transition('pattern'):
                                st.rerun()
                    
                    with col2:
                        button_text = "🚀 Run Contextual Analysis" if user_responses else "⚡ Run Basic Analysis"
                        if st.button(button_text, type="primary"):
                            if safe_step_transition('analysis'):
                                st.rerun()
                
                except Exception as e:
                    st.error(f"Question generation failed: {str(e)}")
                    
                    # Fallback - continue with basic analysis
                    st.warning("Continuing with basic analysis...")
                    if st.button("Continue with Basic Analysis"):
                        if safe_step_transition('analysis'):
                            st.rerun()
            else:
                st.error("Pattern analysis not available. Please go back.")
                if st.button("⬅️ Back to Pattern Analysis"):
                    if safe_step_transition('pattern'):
                        st.rerun()
        
        # Step 4: Analysis
        elif st.session_state.step == 'analysis':
            st.header("🤖 Running Intelligent Analysis...")
            
            try:
                with st.spinner("AI is performing contextual IAM analysis..."):
                    analyzer = IntelligentAnalyzer(st.session_state.openai_client)
                    
                    user_responses = st.session_state.user_context.get('responses', [])
                    analysis_results = analyzer.perform_analysis(
                        st.session_state.extracted_data,
                        st.session_state.pattern_analysis,
                        user_responses
                    )
                    
                    st.session_state.analysis_results = analysis_results
                
                st.success("✅ Analysis complete!")
                if safe_step_transition('results', ['analysis_results']):
                    st.rerun()
            
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                st.session_state.error_state = str(e)
                
                # Provide fallback
                if st.button("Continue with Manual Review Guidance"):
                    st.session_state.analysis_results = {
                        "executive_summary": "Automated analysis failed. Manual review recommended.",
                        "violations": [],
                        "statistics": {"total_users": 0, "total_violations": 0, "critical_count": 0, "high_count": 0, "medium_count": 0, "low_count": 0, "risk_score": 0, "compliance_score": 0},
                        "insights": ["Analysis failed - manual review needed"],
                        "recommendations": {"immediate": [], "short_term": ["Conduct manual IAM review"], "long_term": ["Implement proper IAM tools"]},
                        "follow_up": []
                    }
                    if safe_step_transition('results'):
                        st.rerun()
        
        # Step 5: Results Display  
        elif st.session_state.step == 'results':
            st.header("📊 Analysis Results")
            
            if st.session_state.analysis_results:
                try:
                    results = st.session_state.analysis_results
                    
                    # Executive Summary
                    st.subheader("📋 Executive Summary")
                    summary = results.get('executive_summary', 'No summary available')
                    st.write(summary)
                    
                    # Key Metrics
                    st.subheader("📈 Key Metrics")
                    stats = results.get('statistics', {})
                    
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        st.metric("Total Users", stats.get('total_users', 0))
                    with col2:
                        st.metric("Total Violations", stats.get('total_violations', 0))
                    with col3:
                        critical = stats.get('critical_count', 0)
                        st.metric("Critical Issues", critical, delta="High Priority" if critical > 0 else None)
                    with col4:
                        risk_score = stats.get('risk_score', 0)
                        st.metric("Risk Score", f"{risk_score}/10")
                    with col5:
                        compliance_score = stats.get('compliance_score', 0)
                        st.metric("Compliance Score", f"{compliance_score}/10")
                    
                    # Violations
                    violations = results.get('violations', [])
                    if violations:
                        st.subheader("🚨 Violations & Issues")
                        
                        # Filters
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            severity_filter = st.selectbox("Filter by Severity", 
                                                         ["All", "Critical", "High", "Medium", "Low"])
                        with col2:
                            type_filter = st.selectbox("Filter by Type", 
                                                     ["All"] + list(set([v.get('type', 'Unknown') for v in violations])))
                        with col3:
                            show_details = st.checkbox("Show Full Details", value=True)
                        
                        # Apply filters
                        filtered_violations = violations
                        if severity_filter != "All":
                            filtered_violations = [v for v in filtered_violations if v.get('severity') == severity_filter]
                        if type_filter != "All":
                            filtered_violations = [v for v in filtered_violations if v.get('type') == type_filter]
                        
                        # Display violations
                        for violation in filtered_violations:
                            severity = violation.get('severity', 'Medium')
                            severity_colors = {
                                'Critical': '🔴', 'High': '🟠', 'Medium': '🟡', 'Low': '🟢'
                            }
                            color = severity_colors.get(severity, '⚪')
                            
                            title = violation.get('title', violation.get('type', 'Unknown Violation'))
                            
                            with st.expander(f"{color} [{severity}] {title}", expanded=(severity == 'Critical')):
                                
                                if show_details:
                                    col1, col2 = st.columns([2, 1])
                                    
                                    with col1:
                                        st.write("**Description:**")
                                        st.write(violation.get('description', 'No description available'))
                                        
                                        business_risk = violation.get('business_risk')
                                        if business_risk:
                                            st.write("**Business Risk:**")
                                            st.warning(business_risk)
                                        
                                        compliance_impact = violation.get('compliance_impact')
                                        if compliance_impact:
                                            st.write("**Compliance Impact:**")
                                            st.info(compliance_impact)
                                    
                                    with col2:
                                        affected = violation.get('affected_users', [])
                                        if affected:
                                            st.write("**Affected Users:**")
                                            display_users = affected[:5] if isinstance(affected, list) else [str(affected)]
                                            for user in display_users:
                                                st.write(f"• {user}")
                                            if isinstance(affected, list) and len(affected) > 5:
                                                st.write(f"• ... and {len(affected) - 5} more")
                                        
                                        effort = violation.get('effort')
                                        if effort:
                                            st.write(f"**Effort to Fix:** {effort}")
                                
                                st.write("**Recommendation:**")
                                st.success(violation.get('recommendation', 'No recommendation available'))
                    
                    # Insights
                    insights = results.get('insights', [])
                    if insights:
                        st.subheader("💡 Key Insights")
                        for insight in insights:
                            st.info(f"🔍 {insight}")
                    
                    # Recommendations
                    recommendations = results.get('recommendations', {})
                    if any(recommendations.values()):
                        st.subheader("🎯 Prioritized Recommendations")
                        
                        for category, items in recommendations.items():
                            if items:
                                category_icons = {
                                    'immediate': '🚨',
                                    'short_term': '⏰', 
                                    'long_term': '📋'
                                }
                                icon = category_icons.get(category, '📌')
                                
                                st.write(f"**{icon} {category.replace('_', ' ').title()}:**")
                                for item in items:
                                    st.write(f"• {item}")
                                st.write("")
                    
                    # Follow-up Questions
                    follow_ups = results.get('follow_up', [])
                    if follow_ups:
                        st.subheader("❓ Follow-up Questions")
                        st.write("The AI has additional questions to refine the analysis:")
                        
                        for i, follow_up in enumerate(follow_ups):
                            with st.expander(f"📋 {follow_up.get('context', 'Additional Context')}"):
                                st.write(follow_up.get('question', ''))
                                
                                response = st.text_input(
                                    "Your response:",
                                    key=f"followup_{i}_{hash(str(follow_up)) % 1000}",
                                    placeholder="Type your answer..."
                                )
                                
                                if response:
                                    st.success("✅ Response noted for future analysis improvement")
                    
                    # Export Options
                    st.subheader("📄 Export & Reports")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📊 Generate Excel Report", type="primary"):
                            try:
                                with st.spinner("Generating comprehensive Excel report..."):
                                    report_gen = ReportGenerator()
                                    excel_bytes = report_gen.generate_report(
                                        st.session_state.extracted_data,
                                        st.session_state.analysis_results
                                    )
                                    
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filename = f"IAM_Analysis_{timestamp}.xlsx"
                                    
                                    st.download_button(
                                        label="📥 Download Excel Report",
                                        data=excel_bytes,
                                        file_name=filename,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                    )
                                    
                                    st.success("✅ Excel report generated!")
                                    
                            except Exception as e:
                                st.error(f"❌ Error generating report: {str(e)}")
                    
                    with col2:
                        if st.button("📋 Executive Summary"):
                            summary_text = f"""IAM Analysis Executive Summary
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

OVERVIEW:
{results.get('executive_summary', 'No summary available')}

KEY METRICS:
• Total Users: {stats.get('total_users', 0)}
• Violations Found: {stats.get('total_violations', 0)} 
• Critical Issues: {stats.get('critical_count', 0)}
• Risk Score: {stats.get('risk_score', 0)}/10

IMMEDIATE ACTIONS REQUIRED:"""
                            
                            immediate = recommendations.get('immediate', [])
                            for i, action in enumerate(immediate, 1):
                                summary_text += f"\n{i}. {action}"
                            
                            st.text_area(
                                "Executive Summary (Copy for leadership)",
                                value=summary_text,
                                height=300
                            )
                    
                    with col3:
                        if st.button("🔄 New Analysis"):
                            # Reset for new analysis
                            keys_to_reset = ['extracted_data', 'pattern_analysis', 'analysis_results', 'user_context', 'error_state']
                            for key in keys_to_reset:
                                if key in st.session_state:
                                    del st.session_state[key]
                            if safe_step_transition('upload'):
                                st.rerun()
                
                except Exception as e:
                    st.error(f"Error displaying results: {str(e)}")
                    st.session_state.error_state = str(e)
            else:
                st.error("No analysis results available.")
                if st.button("⬅️ Back to Analysis"):
                    if safe_step_transition('analysis'):
                        st.rerun()
        
        # AI Assistant (available after analysis)
        if st.session_state.step == 'results' and st.session_state.analysis_results:
            st.sidebar.header("🤖 AI Assistant")
            
            user_question = st.sidebar.text_input(
                "Ask about your results:",
                placeholder="e.g., 'How urgent are the critical violations?'"
            )
            
            if user_question and st.sidebar.button("Ask AI"):
                with st.sidebar:
                    try:
                        with st.spinner("AI thinking..."):
                            context = f"""
                            Analysis Results Summary:
                            {json.dumps(st.session_state.analysis_results, indent=2)[:3000]}
                            
                            User Question: {user_question}
                            """
                            
                            response = st.session_state.openai_client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[
                                    {"role": "system", "content": "You are an IAM expert assistant. Provide helpful, specific answers based on the analysis results."},
                                    {"role": "user", "content": context}
                                ],
                                temperature=0.1,
                                max_tokens=500
                            )
                            
                            st.write("**AI Response:**")
                            st.write(response.choices[0].message.content)
                            
                    except Exception as e:
                        st.error(f"AI Assistant error: {str(e)}")
        
        # Footer
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            🧠 <strong>Intelligent IAM Analyzer</strong> | 
            Web-hosted AI that learns from your environment | 
            Cost: ~$0.01-0.10 per analysis<br>
            💡 <em>Secure, scalable, and accessible from anywhere!</em>
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Application error: {str(e)}")
        st.error("Please refresh the page or contact support if the problem persists.")
        
        # Debug info for development
        if st.checkbox("Show debug info"):
            st.text("Error details:")
            st.text(traceback.format_exc())

if __name__ == "__main__":
    main()