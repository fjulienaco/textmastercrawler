import streamlit as st
import os
from dotenv import load_dotenv
from main import analyze_domain
import logging

# Load .env if running locally
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def get_openai_api_key():
    # Try Streamlit secrets first, but handle missing secrets.toml gracefully
    try:
        return st.secrets.get("OPENAI_API_KEY", None)
    except Exception:
        pass
    # Fallback to environment variable (from .env)
    return os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Linguistic QA Email Generator", page_icon="📧", layout="wide")
st.title("📧 Linguistic QA Email Generator")
st.write("""
Enter a website URL below. The app will review a few pages, find linguistic issues, and generate a suggested outreach email you can quickly copy.
""")

url = st.text_input("Website URL (e.g. example.com or https://example.com)")
logging.info(f"User input URL: {url}")

if st.button("Analyze and Generate Email"):
    logging.info("Analyze and Generate Email button clicked.")
    if not url.strip():
        st.error("Please enter a website URL.")
        logging.error("No URL entered by user.")
    else:
        with st.spinner("Analyzing website and generating email..."):
            try:
                domain = url.strip().replace("https://", "").replace("http://", "").strip("/")
                api_key = get_openai_api_key()
                if not api_key:
                    st.error("No OpenAI API key found in st.secrets or .env!")
                    logging.error("No OpenAI API key found.")
                else:
                    logging.info(f"Calling analyze_domain for domain: {domain}")
                    email, issues = analyze_domain(domain, api_key)
                    st.success("Email generated!")
                    st.subheader("Suggested Email")
                    st.code(email, language=None)
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
                logging.error(f"Exception in Streamlit app: {e}") 