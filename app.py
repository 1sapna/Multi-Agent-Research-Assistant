import streamlit as st
import requests
import google.generativeai as genai
from datetime import datetime
import time

# Load secrets
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "")
tavily_api_key = st.secrets.get("TAVILY_API_KEY", "")

# Configure Gemini API
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# Function to check Gemini API status
def check_gemini_api_status():
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest'")
        response = model.generate_content("Say hi")
        return True, "Active"
    except Exception as e:
        return False, str(e)

# Check if both APIs are ready
def are_api_keys_ready():
    if not gemini_api_key:
        return False, "Gemini API Key missing"
    if not tavily_api_key:
        return False, "Tavily API Key missing"
    ok, msg = check_gemini_api_status()
    if not ok:
        return False, f"Gemini error: {msg}"
    return True, "All APIs loaded"

# Tavily search function
def search_tavily(query, num_results=3):
    try:
        url = "https://api.tavily.com/search"
        headers = {"Content-Type": "application/json"}
        payload = {
            "api_key": tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "include_images": False,
            "max_results": num_results
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        return []

# Multi-agent research system
def run_multi_agent_research(query):
    results = {
        "research_plan": [],
        "extracted_info": [],
        "final_answer": "",
        "errors": []
    }

    try:
        # Agent 1: Coordination Agent
        model = genai.GenerativeModel("gemini-1.5-flash-latest'")
        coord_prompt = f"""Break this query into smaller sub-questions for research:

Query: {query}

Respond with a numbered list."""
        coord_response = model.generate_content(coord_prompt)
        questions = coord_response.text.strip().split("\n")
        sub_questions = [q.split(".", 1)[1].strip() if "." in q else q for q in questions]
        results["research_plan"] = sub_questions

        # Agent 2: Research Agent
        for sub_q in sub_questions:
            search_results = search_tavily(sub_q, num_results=3)
            for r in search_results:
                results["extracted_info"].append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "relevance_score": r.get("score", 0)
                })
            time.sleep(1)

        # Agent 3: Synthesis Agent
        sources_text = ""
        for i, info in enumerate(results["extracted_info"], 1):
            sources_text += f"Source {i}:\nTitle: {info['title']}\nURL: {info['url']}\nContent: {info['content'][:1000]}\n\n"

        synthesis_prompt = f"""Based on the following research sources, write a draft response to the query:

Query: {query}

Sources:
{sources_text}

Write a markdown-formatted draft."""
        synth_response = model.generate_content(synthesis_prompt)
        draft = synth_response.text

        # Agent 4: Finalization Agent
        final_prompt = f"""Polish and organize the following draft into a clear, well-formatted final answer using markdown:

Query: {query}

Draft:
{draft}

Final polished version:"""
        final_response = model.generate_content(final_prompt)
        results["final_answer"] = final_response.text

    except Exception as e:
        results["errors"].append(str(e))

    return results

# PAGE SETUP
st.set_page_config(
    page_title="Multi-Agent-Research-Assistant",
    page_icon="🔍",
    layout="wide"
)

# SIDEBAR
with st.sidebar:
    st.title("API Configuration")
    if gemini_api_key:
        ok, msg = check_gemini_api_status()
        if ok:
            st.success(f"✅ Gemini API Key: {msg}")
        else:
            st.error(f"❌ Gemini API Error: {msg}")
    else:
        st.error("❌ Gemini API Key not found")

    if tavily_api_key:
        st.success("✅ Tavily API Key loaded")
    else:
        st.error("❌ Tavily API Key not found")

    st.markdown("---")
    st.markdown("""## About This App

**Multi-Agent-Research-Assistant** uses Google Gemini AI and a multi-agent architecture to handle complex research tasks.

### How It Works:

1. 🤖 **Coordination Agent**  
   Breaks down the main query into multiple sub-questions for targeted research.

2. 🔍 **Research Agent**  
   Performs web searches for each sub-question using Tavily.

3. 📊 **Synthesis Agent**  
   Compiles and combines information from multiple sources into a structured draft.

4. ✨ **Finalization Agent**  
   Refines the draft into a well-polished research report with markdown formatting.

This approach ensures accurate, multi-perspective, and logically structured answers to complex queries.
""")

# MAIN PAGE
st.title("🔍 Multi-Agent-Research-Assistant")
st.markdown("### 🤖 Powered by Google Gemini API + Tavily Search")
st.write("Enter a research query and the AI agents will gather and synthesize information from the web.")

api_ready, status = are_api_keys_ready()

if not api_ready:
    st.error(f"⚠️ Setup required: {status}")
    st.info("Please check the sidebar for API configuration.")

st.markdown("**💡 Example queries:**")
st.markdown("- What are the latest developments in renewable energy technology?")
st.markdown("- How does artificial intelligence impact healthcare in 2024?")
st.markdown("- What are the main causes and effects of climate change?")
st.markdown("- Compare different programming languages for web development")

query = st.text_area("Research Query", height=100, placeholder="Enter your research question here...")

if st.button("🚀 Start Research", type="primary", disabled=not api_ready):
    if not api_ready:
        st.error(f"Cannot start research: {status}")
    else:
        with st.spinner("🔍 AI agents are researching your query..."):
            result = run_multi_agent_research(query)

        tab1, tab2, tab3, tab4 = st.tabs(["📋 Final Answer", "📝 Research Plan", "🔗 Sources", "⚠️ Debug Info"])

        with tab1:
            if result["final_answer"]:
                st.markdown("## 🎯 Research Results")
                st.markdown(result["final_answer"])
                st.download_button(
                    label="📥 Download Research Report",
                    data=result["final_answer"],
                    file_name=f"research_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
            else:
                st.warning("No answer generated. Check Debug Info.")

        with tab2:
            st.markdown("## 📋 Research Strategy")
            if result["research_plan"]:
                for i, q in enumerate(result["research_plan"], 1):
                    st.markdown(f"**{i}.** {q}")
            else:
                st.info("No research plan generated.")

        with tab3:
            st.markdown("## 🔗 Source Information")
            if result["extracted_info"]:
                st.markdown(f"**Sources used:** {len(result['extracted_info'])}")
                for i, info in enumerate(result["extracted_info"], 1):
                    with st.expander(f"📄 {info['title']}", expanded=False):
                        st.markdown(f"🔗 [{info['url']}]({info['url']})")
                        st.markdown(f"⭐ Score: {info['relevance_score']}")
                        st.markdown(f"_Preview:_\n{info['content'][:300]}...")
            else:
                st.info("No sources found.")

        with tab4:
            st.markdown("## ⚠️ Debug Info")
            if result["errors"]:
                for err in result["errors"]:
                    st.error(err)
            else:
                st.success("✅ No errors detected.")
            st.metric("Questions", len(result["research_plan"]))
            st.metric("Sources", len(result["extracted_info"]))
            st.metric("Errors", len(result["errors"]))

# FOOTER
st.markdown("---")
st.markdown("""<div style='text-align: center'>
    <p>🤖 <strong>Powered by Google Gemini + Tavily Search</strong></p>
    <p>Built with ❤️ using Streamlit</p>
</div>""", unsafe_allow_html=True)
