import streamlit as st
import os
from dotenv import load_dotenv
from main import analyze_domain

# Load .env if running locally
load_dotenv()

def get_openai_api_key():
    # Try Streamlit secrets first, but handle missing secrets.toml gracefully
    try:
        return st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass
    # Fallback to environment variable (from .env)
    return os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Linguistic QA Email Generator", page_icon="📧", layout="centered")
st.title("📧 Linguistic QA Email Generator")
st.write("""
Enter a website URL below. The app will review a few pages, find linguistic issues, and generate a suggested outreach email you can quickly copy.
""")

url = st.text_input("Website URL (e.g. example.com or https://example.com)")

if st.button("Analyze and Generate Email"):
    if not url.strip():
        st.error("Please enter a website URL.")
    else:
        with st.spinner("Analyzing website and generating email..."):
            try:
                domain = url.strip().replace("https://", "").replace("http://", "").strip("/")
                api_key = get_openai_api_key()
                if not api_key:
                    st.error("No OpenAI API key found in st.secrets or .env!")
                else:
                    email, issues = analyze_domain(domain, api_key)
                    st.success("Email generated!")
                    st.subheader("Suggested Email")
                    st.code(email, language=None)
                    st.button("Copy Email", on_click=st.session_state.setdefault, args=("copied", True))
                    if issues:
                        st.markdown("---")
                        st.subheader("Sample Issues Found")
                        for i, issue in enumerate(issues, 1):
                            st.markdown(f"""**Issue {i}:**
```
{issue}
```""")
                    else:
                        st.info("No major linguistic issues found.")
            except Exception as e:
                st.error(f"An error occurred: {e}") 