import streamlit as st
from main import analyze_domain

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
                # Clean up input
                domain = url.strip().replace("https://", "").replace("http://", "").strip("/")
                email, issues = analyze_domain(domain)
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