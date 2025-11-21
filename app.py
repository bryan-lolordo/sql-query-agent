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

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask a question about your data..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
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
                
                # Display results
                if result["success"]:
                    st.success(f"✅ Success after {result['attempt']} attempt(s)!")
                    
                    # Show generated SQL
                    with st.expander("📝 Generated SQL", expanded=True):
                        st.code(result["sql_query"], language="sql")
                    
                    # Show results
                    if result["execution_result"] and result["execution_result"].get("data"):
                        st.subheader("📊 Results")
                        df = pd.DataFrame(result["execution_result"]["data"])
                        st.dataframe(df, width='stretch')
                        
                        row_count = result["execution_result"].get("row_count", len(df))
                        st.caption(f"Returned {row_count} row(s)")
                    elif result["execution_result"]:
                        st.info("Query executed successfully but returned no results.")
                    
                    # Show attempt history if multiple attempts
                    if result["attempt"] > 1 and result.get("previous_queries"):
                        with st.expander("🔄 Attempt History"):
                            for i, (query, error) in enumerate(zip(
                                result["previous_queries"],
                                result["previous_errors"]
                            ), 1):
                                st.markdown(f"**Attempt {i}:**")
                                st.code(query, language="sql")
                                st.error(f"Error: {error}")
                                st.divider()
                    
                    response_content = "Query executed successfully!"
                else:
                    st.error(f"❌ Failed after {result['attempt']} attempt(s)")
                    
                    # Show last SQL attempted
                    with st.expander("📝 Last SQL Attempt", expanded=True):
                        st.code(result["sql_query"], language="sql")
                    
                    # Show error
                    if result["execution_error"]:
                        st.error(f"Error: {result['execution_error']}")
                    
                    # Show all attempts
                    if result.get("previous_queries"):
                        with st.expander("🔄 All Attempts"):
                            for i, (query, error) in enumerate(zip(
                                result["previous_queries"],
                                result["previous_errors"]
                            ), 1):
                                st.markdown(f"**Attempt {i}:**")
                                st.code(query, language="sql")
                                st.error(f"Error: {error}")
                                st.divider()
                    
                    response_content = result.get("formatted_result") or "I couldn't complete your query. Please try rephrasing or check the database schema."
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response_content
                })
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                })

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