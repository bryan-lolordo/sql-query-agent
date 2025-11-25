"""Streamlit UI for the SQL Query Agent."""

import os
from dotenv import load_dotenv

# Load environment variables FIRST before any other imports
load_dotenv()

# Verify the key is loaded
if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("OPENAI_API_KEY not found in environment. Please check your .env file.")

# Now import everything else AFTER load_dotenv()
import streamlit as st
import pandas as pd
from sql_query_agent.graph.workflow import create_graph
from sql_query_agent.tools.schema_analyzer import SchemaAnalyzer


# Page configuration
st.set_page_config(
    page_title="SQL Query Agent",
    page_icon="🔍",
    layout="wide"
)

# Title and description
st.title("🔍 SQL Query Agent")
st.markdown("""
A self-correcting SQL query agent that converts natural language to SQL and automatically fixes errors.
Powered by LangGraph and OpenAI.
""")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph" not in st.session_state:
    st.session_state.graph = None

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Database selection
    db_path = st.text_input(
        "Database Path",
        value="data/ecommerce.sqlite",
        help="Path to your SQLite database"
    )
    
    # Max attempts
    max_attempts = st.slider(
        "Max Retry Attempts",
        min_value=1,
        max_value=5,
        value=3,
        help="Maximum number of attempts to fix and retry failed queries"
    )
    
    # Show schema button
    if st.button("📋 Show Database Schema"):
        if os.path.exists(db_path):
            analyzer = SchemaAnalyzer(db_path)
            schema = analyzer.get_schema()
            st.subheader("Database Schema")
            for table_name, columns in schema.items():
                with st.expander(f"Table: {table_name}"):
                    st.write("**Columns:**")
                    for col in columns:
                        pk_marker = " 🔑" if col.get('primary_key') else ""
                        null_marker = " (NOT NULL)" if col.get('not_null') else ""
                        st.write(f"- {col['name']} ({col['type']}){pk_marker}{null_marker}")
        else:
            st.error(f"Database not found at: {db_path}")
    
    st.divider()
    
    st.markdown("""
    ### 🎯 How it works
    1. Enter your question in natural language
    2. Agent converts it to SQL
    3. If errors occur, agent automatically:
       - Analyzes the error
       - Learns from the mistake
       - Generates improved SQL
       - Retries execution
    4. Success after up to 3 attempts!
    """)

# Main chat interface
st.header("💬 Ask a Question")

# Chat input
if prompt := st.chat_input("Ask a question about your data..."):
    
    with st.spinner("🤔 Thinking..."):
        try:
            # Create or get the graph
            if st.session_state.graph is None:
                st.session_state.graph = create_graph(db_path)
            
            graph = st.session_state.graph
            
            # Run the agent
            initial_state = {
                "user_query": prompt,
                "sql_query": "",
                "execution_result": None,
                "execution_error": None,
                "attempt": 1,
                "max_attempts": max_attempts,
                "previous_errors": [],
                "previous_queries": [],
                "formatted_result": None,
                "success": False,
                "schema": {}
            }
            
            # Execute the graph
            result = graph.invoke(initial_state)
            
            # ============================================
            # VISUAL JOURNEY DISPLAY
            # ============================================
            
            # 1. Show User Query
            st.markdown("---")
            st.subheader("🗣️ Your Question")
            st.info(prompt)
            
            # 2. Show Self-Correction Journey
            st.subheader("🔄 Self-Correction Journey")
            
            # Get all attempts
            all_queries = result.get("previous_queries", []).copy()
            all_errors = result.get("previous_errors", []).copy()
            
            # Add final query
            if result.get("sql_query"):
                all_queries.append(result["sql_query"])
            
            # Display each attempt
            for i, query in enumerate(all_queries, 1):
                is_last = (i == len(all_queries))
                is_success = is_last and result.get("success")
                
                # Attempt header
                col1, col2 = st.columns([1, 11])
                with col1:
                    if is_success:
                        st.markdown(f"### ✅")
                    else:
                        st.markdown(f"### ❌")
                with col2:
                    st.markdown(f"### Attempt {i}")
                
                # SQL Code
                st.code(query, language="sql")
                
                # Result of this attempt
                if is_success:
                    st.success("**Success!** Query executed successfully.")
                elif i <= len(all_errors):
                    st.error(f"**Error:** {all_errors[i-1]}")
                    
                    # Show learning step
                    if not is_last:
                        st.warning("🧠 **Learning:** Analyzing error and adjusting approach...")
                
                st.markdown("")  # Spacing
            
            # 3. Show Results (if successful)
            if result["success"]:
                st.markdown("---")
                st.subheader("📊 Results")
                
                if result["execution_result"] and result["execution_result"].get("data"):
                    df = pd.DataFrame(result["execution_result"]["data"])
                    st.dataframe(df, width='stretch')
                    
                    row_count = result["execution_result"].get("row_count", len(df))
                    st.caption(f"Returned {row_count} row(s)")
                else:
                    st.info("Query executed successfully but returned no results.")
                
                # Summary
                st.markdown("---")
                if result["attempt"] > 1:
                    st.success(f"🎉 **Success after {result['attempt']} attempt(s)!** The agent learned from {result['attempt']-1} failed attempt(s) and self-corrected.")
                else:
                    st.success(f"🎉 **Success on first attempt!**")
            
            else:
                # Failed after all attempts
                st.markdown("---")
                st.error(f"❌ **Failed after {result['attempt']} attempt(s)**")
                
                if result.get("formatted_result"):
                    st.warning(result["formatted_result"])
                else:
                    st.warning("Unable to generate a working SQL query. Please try rephrasing your question or check the database schema.")
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            import traceback
            with st.expander("🐛 Error Details"):
                st.code(traceback.format_exc())

# Clear chat button
if st.sidebar.button("🗑️ Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray;'>
    Built with LangGraph • Self-correcting SQL queries through iterative refinement
</div>
""", unsafe_allow_html=True)