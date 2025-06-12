# ... [IMPORTS AND SETUP – Unchanged] ...

# Page configuration
st.set_page_config(
    page_title="Multi-Agent-Research-Assistant",
    page_icon="🔍",
    layout="wide"
)

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
                st.warning("""**To fix this:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy and paste it in your secrets""")
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

# ... [STATE SCHEMA, API FUNCTIONS, PROCESSING LOGIC – Unchanged] ...

# Main app
st.title("🔍 Multi-Agent-Research-Assistant")
st.markdown("### 🤖 Powered by Google Gemini API + Tavily Search")
st.write("Enter a research query and the AI agents will gather and synthesize information from the web.")

# Show API status
api_ready, api_status = are_api_keys_ready()

if not api_ready:
    st.error(f"⚠️ Setup required: {api_status}")
    st.info("Please check the sidebar for API configuration.")

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
                # ... [Progress Bar and Processing Logic – Unchanged] ...

                # Display results in tabs
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
st.markdown("""<div style='text-align: center'>
    <p>🤖 <strong>Powered by Google Gemini + Tavily Search</strong></p>
    <p>Built with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
