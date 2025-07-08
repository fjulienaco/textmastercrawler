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

# Supported languages for selection (langdetect codes)
language_options = {
    "English": "en",
    "French": "fr",
    "German": "de",
    "Spanish": "es",
    "Italian": "it",
    "Dutch": "nl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Chinese": "zh-cn",
    "Japanese": "ja",
    "Polish": "pl",
    "Turkish": "tr",
    "Arabic": "ar",
    "Czech": "cs",
    "Danish": "da",
    "Finnish": "fi",
    "Greek": "el",
    "Hungarian": "hu",
    "Norwegian": "no",
    "Swedish": "sv"
}

selected_languages = st.multiselect(
    "Select language(s) to analyze (detected by content)",
    options=list(language_options.keys()),
    default=["English", "French", "German", "Spanish", "Italian", "Dutch"],
    help="Only pages detected in these languages will be analyzed."
)
allowed_language_codes = [language_options[lang] for lang in selected_languages]

default_prompt = (
    "You are a senior translation QA specialist reviewing website content. Your task is to extract **exactly 1 example** of a linguistic issue from this content. Your focus should be on **clear, verifiable errors** that a native speaker or reviewer would reasonably flag.\n\n"
    "Only include examples if they fall into these categories:\n"
    "- Mistranslations\n"
    "- Grammar issues\n"
    "- Unnatural expressions\n"
    "- Incorrect word choice\n\n"
    "Avoid:\n"
    "- Issues about punctuation or spacing unless no other issues exist\n"
    "- Multiple errors from the same sentence, even across different pages\n"
    "- False positives (acceptable phrasing or domain/product-specific terms)\n\n"
    "\u26a0\ufe0f You may include punctuation or spacing issues ONLY if no better errors exist in the full input.\n\n"
    "Response format:\n"
    "- Original sentence: \"...\"\n"
    "- Issue: [Short explanation]\n"
    "- Suggested correction: \"...\"\n\n"
    "If no issue is found, return an empty string.\n\n"
    "Text:\n{text}"
)

prompt_template = st.text_area(
    "Main Quality Assessment Prompt (edit if needed before scanning)",
    value=default_prompt,
    height=300,
    help="This prompt will be used for the linguistic quality assessment. You can modify it before launching the scan. Use {text} as a placeholder for the page content."
)

# Add UI option for robots.txt enlargement
use_robots_enlargement = st.checkbox(
    "Enlarge crawl to all domains referenced in robots.txt (advanced)",
    value=False,
    help="If enabled, the crawl will include all domains referenced in robots.txt (Sitemap, Allow, Disallow). Default is OFF."
)

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
                    email, issues = analyze_domain(
                        domain,
                        api_key,
                        prompt_template=prompt_template,
                        allowed_languages=allowed_language_codes,
                        use_robots_enlargement=use_robots_enlargement
                    )
                    st.success("Email generated!")
                    st.subheader("Suggested Email")
                    st.code(email, language=None)
                    if issues:
                        st.markdown("---")
                        st.subheader("Sample Issues Found")
                        for i, issue in enumerate(issues, 1):
                            st.markdown(f"""**Issue {i}:**\n```
{issue}
```""")
                    else:
                        st.info("No major linguistic issues found.")
            except Exception as e:
                st.error(f"An error occurred: {e}")
                logging.error(f"Exception in Streamlit app: {e}") 