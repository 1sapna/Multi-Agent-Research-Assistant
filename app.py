import os
import streamlit as st
import time
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# Import required packages with error handling
try:
    import google.generativeai as genai
    from langchain_community.tools.tavily_search import TavilySearchResults
except ImportError as e:
    st.error(f"Error importing required packages: {e}. Please install required packages with:")
    st.code("pip install google-generativeai tavily-python streamlit python-dotenv pydantic")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="AI Research Agent System (Gemini)",
    page_icon="🔍",
    layout="wide"
)

# Get API keys from environment variables
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "")

# Configure Gemini
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# Function to check Gemini API key status
def check_gemini_api_status():
    """Check if Gemini API key is valid"""
    if not gemini_api_key:
        return False, "API key not found"
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Hi")
        return True, "API key is valid and working"
    except Exception as e:
        if "API_KEY_INVALID" in str(e):
            return False, "Invalid API key"
        elif "QUOTA_EXCEEDED" in str(e):
            return False, "Quota exceeded - but Gemini is free with good limits!"
        else:
            return False, f"API error: {str(e)}"

# Sidebar with API key status
with st.sidebar:
    st.title("API Configuration")
    
    # Check and display Gemini API status
    if gemini_api_key:
        is_valid, status_msg = check_gemini_api_status()
        if is_valid:
            st.success(f"✅ Gemini API Key: {status_msg}")
        else:
            st.error(f"❌ Gemini API Key: {status_msg}")
            
            if "invalid" in status_msg.lower():
                st.warning("""
                **To fix this:**
                1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
                2. Create a new API key
                3. Copy and paste it in your secrets
                
                Gemini API is **FREE** with generous limits!
                """)
    else:
        st.error("❌ Gemini API Key not found")
        
    if tavily_api_key:
        st.success("✅ Tavily API Key loaded")
    else:
        st.error("❌ Tavily API Key not found")
    
    st.markdown("---")
    st.markdown("""
    ## About This App
    
    This application uses **Google Gemini AI** (FREE!) with a multi-agent system:
    
    1. **Coordination Agent** - Plans research strategy
    2. **Research Agent** - Searches web using Tavily
    3. **Synthesis Agent** - Creates comprehensive answers
    4. **Finalization Agent** - Polishes responses
    
    **✨ Uses FREE Google Gemini API!**
    """)
    st.markdown("---")
    st.markdown("""
    ### Setup Instructions:

    **Get FREE Gemini API Key:**
    1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
    2. Click "Create API Key"
    3. Copy your free API key

    **Get FREE Tavily API Key:**
    1. Visit [Tavily](https://tavily.com)
    2. Sign up for free account
    3. Get your API key

    **For Streamlit Cloud:**
    ```
    GEMINI_API_KEY = "your_gemini_key"
    TAVILY_API_KEY = "your_tavily_key"
    ```

    **For local (.env file):**
    ```
    GEMINI_API_KEY=your_gemini_key
    TAVILY_API_KEY=your_tavily_key
    ```

    **Gemini Free Limits:**
    - 15 requests per minute
    - 1,500 requests per day
    - Completely FREE! 🎉
    """)

# Define the state schema
class AgentState(BaseModel):
    query: str = Field(description="The original research query")
    research_plan: List[str] = Field(default_factory=list, description="Research plan with sub-questions")
    search_results: List[Dict[str, Any]] = Field(default_factory=list, description="Collected search results")
    extracted_info: List[Dict[str, str]] = Field(default_factory=list, description="Extracted information from search results")
    draft_answer: str = Field(default="", description="Draft answer to the query")
    final_answer: str = Field(default="", description="Final answer to the query")
    current_step: str = Field(default="start", description="Current step in the research process")
    errors: List[str] = Field(default_factory=list, description="Errors encountered during the process")
    iteration_count: int = Field(default=0, description="Count of iterations through the graph")

# Function to call Gemini API
def call_gemini(prompt: str, model_name: str = "gemini-1.5-flash-latest") -> str:
    """Call Gemini API with error handling"""
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")

# Function to extract relevant information from search results
def extract_relevant_info(search_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Extract and structure relevant information from search results."""
    extracted_info = []
    
    for result in search_results:
        extracted = {
            "title": result.get("title", ""),
            "content": result.get("content", ""),
            "url": result.get("url", ""),
            "relevance_score": result.get("score", 0),
            "extracted_at": datetime.now().isoformat()
        }
        extracted_info.append(extracted)
        
    return extracted_info

# Check if API keys are available and valid
def are_api_keys_ready():
    if not gemini_api_key or not tavily_api_key:
        return False, "Missing API keys"
    
    is_valid, status_msg = check_gemini_api_status()
    if not is_valid:
        return False, status_msg
    
    return True, "All APIs ready"

# Research processing function using Gemini
def process_research_query(query: str):
    """Process a research query using Gemini API and Tavily search."""
    result = {
        "query": query,
        "research_plan": [],
        "extracted_info": [],
        "final_answer": "",
        "errors": []
    }
    
    try:
        # 1. Planning phase with Gemini coordination agent
        try:
            planning_prompt = f"""You are a research coordination agent. Your job is to break down a research query into a structured plan with specific sub-questions that will help answer the main query comprehensively.

Create 3-4 focused sub-questions that will guide the research process for this query: "{query}"

Format your response as a numbered list:
1. [First sub-question]
2. [Second sub-question]
3. [Third sub-question]
4. [Fourth sub-question]

Keep the sub-questions specific and actionable for web search."""

            planning_response = call_gemini(planning_prompt)
            
            # Extract research plan from response
            plan_lines = [line.strip() for line in planning_response.split("\n") if line.strip()]
            research_plan = []
            
            for line in plan_lines:
                if any(line.startswith(prefix) for prefix in ["1.", "2.", "3.", "4.", "5.", "- "]):
                    # Clean up the line
                    clean_line = line
                    for prefix in ["1.", "2.", "3.", "4.", "5.", "- "]:
                        if clean_line.startswith(prefix):
                            clean_line = clean_line[len(prefix):].strip()
                            break
                    research_plan.append(clean_line)
            
            if not research_plan:
                research_plan = [query]  # Fallback to original query
                
            result["research_plan"] = research_plan
            
        except Exception as e:
            result["errors"].append(f"Planning error: {str(e)}")
            result["research_plan"] = [query]  # Use original query as fallback
        
        # 2. Research phase with Tavily search
        try:
            tavily_tool = TavilySearchResults(max_results=4, api_key=tavily_api_key)
            all_search_results = []
            
            # Search for each research question
            for question in result["research_plan"][:3]:  # Limit to 3 to avoid rate limits
                try:
                    search_result = tavily_tool.invoke({"query": question})
                    all_search_results.extend(search_result)
                    time.sleep(0.5)  # Small delay to be respectful to APIs
                except Exception as e:
                    result["errors"].append(f"Search error for '{question}': {str(e)}")
                    
        except Exception as e:
            result["errors"].append(f"Tavily search setup error: {str(e)}")
            all_search_results = []
        
        # 3. Extract information from search results
        extracted_info = extract_relevant_info(all_search_results)
        result["extracted_info"] = extracted_info
        
        # 4. Synthesis with Gemini
        if extracted_info:
            try:
                # Create context from search results
                context = ""
                for i, info in enumerate(extracted_info[:5], 1):  # Limit to 5 sources
                    context += f"\n--- Source {i} ---\n"
                    context += f"Title: {info['title']}\n"
                    context += f"URL: {info['url']}\n"
                    context += f"Content: {info['content'][:500]}...\n"  # Limit content length
                
                synthesis_prompt = f"""You are a synthesis agent responsible for creating comprehensive research answers.

Research Query: "{query}"

Based on the following information sources, create a detailed, well-structured answer to the research query.

Information Sources:
{context}

Instructions:
1. Create a comprehensive answer that directly addresses the research query
2. Structure your answer with clear sections and use markdown formatting
3. Include relevant facts, figures, and insights from the sources
4. Cite sources using [Source X] format where appropriate
5. If there are conflicting information, mention it
6. Provide a balanced and objective analysis
7. Include a brief summary at the end

Please provide a thorough, well-researched answer:"""

                synthesis_response = call_gemini(synthesis_prompt)
                
                # 5. Finalization with Gemini
                finalize_prompt = f"""You are a finalization agent. Review and improve this research answer:

Original Query: "{query}"

Draft Answer:
{synthesis_response}

Please review and finalize this research answer by:
1. Ensuring logical flow and coherence
2. Checking for completeness
3. Improving readability and structure
4. Adding a clear executive summary at the beginning
5. Making sure all key points are covered
6. Ensuring proper formatting

Provide the final, polished research answer:"""

                final_response = call_gemini(finalize_prompt)
                result["final_answer"] = final_response
                
            except Exception as e:
                result["errors"].append(f"Synthesis/Finalization error: {str(e)}")
                
                # Provide a basic answer using search results if Gemini fails
                basic_answer = f"# Research Results for: {query}\n\n"
                for i, info in enumerate(extracted_info[:4], 1):
                    basic_answer += f"## Source {i}: {info['title']}\n"
                    basic_answer += f"**URL:** {info['url']}\n\n"
                    basic_answer += f"{info['content'][:300]}...\n\n"
                    basic_answer += "---\n\n"
                result["final_answer"] = basic_answer
        else:
            result["errors"].append("No search results found")
            result["final_answer"] = "Unable to gather sufficient information for this query. Please try rephrasing your question or check if the topic exists online."
        
    except Exception as e:
        result["errors"].append(f"General error: {str(e)}")
        
    return result

# Main app
st.title("🔍 Deep Research AI Agent System")
st.markdown("### 🆓 **Powered by FREE Google Gemini API + Tavily Search**")
st.write("Enter a research query and the AI agents will gather and synthesize information from the web.")

# Show API status
api_ready, api_status = are_api_keys_ready()

if not api_ready:
    st.error(f"⚠️ Setup required: {api_status}")
    st.info("Please check the sidebar for setup instructions.")

# Add some example queries
st.markdown("**💡 Example queries:**")
st.markdown("- What are the latest developments in renewable energy technology?")
st.markdown("- How does artificial intelligence impact healthcare in 2024?")
st.markdown("- What are the main causes and effects of climate change?")
st.markdown("- Compare different programming languages for web development")

query = st.text_area("Research Query", height=100, placeholder="Enter your research question here...")

if st.button("🚀 Start Research", type="primary", disabled=not api_ready):
    if not api_ready:
        st.error(f"Cannot start research: {api_status}")
    else:
        with st.spinner("🔍 AI agents are researching your query..."):
            try:
                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Research process steps
                status_text.text("🤖 Coordination Agent: Planning research strategy...")
                progress_bar.progress(15)
                time.sleep(1)
                
                status_text.text("🔍 Research Agent: Searching the web...")
                progress_bar.progress(40)
                time.sleep(2)
                
                status_text.text("📊 Extracting and organizing information...")
                progress_bar.progress(60)
                time.sleep(1)
                
                status_text.text("✍️ Synthesis Agent: Creating comprehensive answer...")
                progress_bar.progress(80)
                time.sleep(1)
                
                status_text.text("✨ Finalization Agent: Polishing the response...")
                progress_bar.progress(95)
                
                # Run the research process
                result = process_research_query(query)
                
                progress_bar.progress(100)
                status_text.text("✅ Research complete!")
                time.sleep(1)
                
                # Clear progress indicators
                progress_bar.empty()
                status_text.empty()
                
                # Display results in tabs
                tab1, tab2, tab3, tab4 = st.tabs(["📋 Final Answer", "📝 Research Plan", "🔗 Sources", "⚠️ Debug Info"])
                
                with tab1:
                    if result["final_answer"]:
                        st.markdown("## 🎯 Research Results")
                        st.markdown(result["final_answer"])
                        
                        # Add download button for the answer
                        st.download_button(
                            label="📥 Download Research Report",
                            data=result["final_answer"],
                            file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.warning("No answer generated due to errors. Check the Debug Info tab for details.")
                    
                with tab2:
                    st.markdown("## 📋 Research Strategy")
                    if result["research_plan"]:
                        st.markdown("The AI coordination agent created this research plan:")
                        for i, question in enumerate(result["research_plan"], 1):
                            st.markdown(f"**{i}.** {question}")
                    else:
                        st.info("No research plan generated.")
                
                with tab3:
                    st.markdown("## 🔗 Source Information")
                    if result["extracted_info"]:
                        st.markdown(f"**📊 Number of sources analyzed:** {len(result['extracted_info'])}")
                        st.markdown("---")
                        
                        # Display sources in a more organized way
                        for i, info in enumerate(result["extracted_info"], 1):
                            with st.expander(f"📄 Source {i}: {info['title']}", expanded=False):
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"**🔗 URL:** [{info['url']}]({info['url']})")
                                with col2:
                                    st.markdown(f"**⭐ Score:** {info['relevance_score']}")
                                
                                st.markdown("**📝 Content Preview:**")
                                st.markdown(f"_{info['content'][:200]}..._")
                    else:
                        st.info("No sources were retrieved.")
                
                with tab4:
                    st.markdown("## ⚠️ Debug Information")
                    if result["errors"]:
                        st.error("Issues encountered during research:")
                        for i, error in enumerate(result["errors"], 1):
                            st.error(f"**{i}.** {error}")
                    else:
                        st.success("✅ No errors encountered during research!")
                    
                    # Show some stats
                    st.markdown("### 📊 Research Statistics")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Research Questions", len(result["research_plan"]))
                    with col2:
                        st.metric("Sources Found", len(result["extracted_info"]))
                    with col3:
                        st.metric("Errors", len(result["errors"]))
                
            except Exception as e:
                st.error(f"❌ Error running research system: {str(e)}")
                st.error("Please check your API keys and try again.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>🤖 <strong>Powered by Google Gemini (FREE) + Tavily Search</strong></p>
    <p>Built with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
