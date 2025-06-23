#!/usr/bin/env python3
"""
IAM Analyzer - Chat + History + Dashboards (v3)
"""

import streamlit as st
import pandas as pd
import openai
import io
import json
import traceback
import matplotlib.pyplot as plt
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()
st.set_page_config(page_title="IAM Analyzer v3", layout="wide")

# API Config
st.sidebar.title("🔐 IAM AI Tool v3")
api_key = st.sidebar.text_input("Enter OpenAI API Key:", type="password")
if not api_key:
    st.sidebar.warning("⚠️ Required: OpenAI API key.")
    st.stop()
openai.api_key = api_key

# Session History
if "history" not in st.session_state:
    st.session_state["history"] = []

# File Upload
st.title("📂 IAM Analyzer - Chat + Dashboard + Memory")
uploaded_files = st.file_uploader("Upload IAM data (CSV, Excel, TXT):", type=["csv", "xlsx", "xls", "txt"], accept_multiple_files=True)

if not uploaded_files:
    st.info("Upload at least one file to continue.")
    st.stop()

# Load Files
all_data = {}
for file in uploaded_files:
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        elif file.name.endswith(".txt"):
            content = file.read().decode("utf-8")
            df = pd.DataFrame({"Text": [content]})
        else:
            continue
        all_data[file.name] = df
    except Exception as e:
        st.error(f"Error loading {file.name}: {e}")

if not all_data:
    st.error("No usable files.")
    st.stop()

# Display data summary
st.subheader("📊 File Summary")
summary = []
for name, df in all_data.items():
    summary.append(f"File: {name}")
    summary.append(f"Shape: {df.shape}")
    summary.append(f"Columns: {', '.join(df.columns)}")
    summary.append(f"Sample:
{df.head(2).to_string(index=False)}")
    summary.append("---")
data_summary = "\n".join(summary)
st.text_area("🧠 GPT Input Preview", value=data_summary, height=300)

# Task Selection
st.subheader("📌 Select AI Tasks")
task_options = [
    "Detect SoD violations",
    "Find orphan accounts",
    "Suggest entitlement cleanup",
    "Create risk dashboard",
    "Summarize key issues"
]
tasks = st.multiselect("Choose tasks:", task_options)

# Run GPT Analysis
if st.button("🚀 Analyze with GPT-4"):
    try:
        prompt = f"""
You are an IAM governance expert. Review the IAM data below and complete the selected tasks:

Data Summary:
{data_summary}

Tasks:
{', '.join(tasks)}

Return valid JSON structured as:
{{
  "summary": "...",
  "risk_score": 8,
  "violations": [...],
  "recommendations": [...],
  "risk_distribution": [
    ["Role", "RiskLevel"],
    ["Finance Admin", "High"],
    ["HR User", "Low"]
  ]
}}
"""

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a cybersecurity identity expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        raw = response.choices[0].message.content
        json_data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])

        # Store to history
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "input_summary": data_summary,
            "output": json_data
        }
        st.session_state["history"].append(entry)

        # Show results
        st.success("✅ Analysis Complete")
        st.metric("Risk Score", f"{json_data.get('risk_score', 0)}/10")
        st.subheader("📝 Summary")
        st.info(json_data.get("summary", ""))

        st.subheader("🚨 Violations")
        for v in json_data.get("violations", []):
            st.warning(f"• {v}")

        st.subheader("✅ Recommendations")
        for r in json_data.get("recommendations", []):
            st.write(f"- {r}")

        # Dashboard
        st.subheader("📈 Risk Dashboard")
        dist = json_data.get("risk_distribution", [])
        if dist:
            dist_df = pd.DataFrame(dist[1:], columns=dist[0])
            fig, ax = plt.subplots()
            dist_df["RiskLevel"] = pd.Categorical(dist_df["RiskLevel"], ["Low", "Medium", "High"])
            count = dist_df["RiskLevel"].value_counts().sort_index()
            ax.bar(count.index, count.values)
            ax.set_title("Access Risk Level by Role")
            ax.set_ylabel("Count")
            st.pyplot(fig)

    except Exception as e:
        st.error("❌ GPT-4 Analysis Failed")
        st.code(traceback.format_exc())

# Live Chat Interface
st.sidebar.subheader("💬 AI Chat (Ask about current data)")
if "chat_log" not in st.session_state:
    st.session_state["chat_log"] = []

user_msg = st.sidebar.text_area("Type your question:", height=100)
if st.sidebar.button("Ask"):
    if user_msg:
        try:
            chat_prompt = f"""
You are an IAM assistant. The user has uploaded the following summary of IAM data:

{data_summary}

Now answer their question: {user_msg}
"""
            chat_resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an identity governance expert."},
                    {"role": "user", "content": chat_prompt}
                ],
                temperature=0.2
            )
            response_text = chat_resp.choices[0].message.content
            st.session_state["chat_log"].append((user_msg, response_text))
        except Exception as e:
            st.sidebar.error("Error during chat.")
            st.sidebar.code(traceback.format_exc())

# Chat history
if st.session_state["chat_log"]:
    st.sidebar.markdown("### 🧠 Chat History")
    for idx, (q, a) in enumerate(st.session_state["chat_log"]):
        st.sidebar.markdown(f"**Q{idx+1}:** {q}")
        st.sidebar.markdown(f"> {a}")

# Analysis History
st.subheader("📚 Previous Analyses (Session Memory)")
for entry in st.session_state["history"][-3:][::-1]:
    st.markdown(f"**🕒 {entry['timestamp']}**")
    st.code(entry["output"].get("summary", ""))
