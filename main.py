import requests
from bs4 import BeautifulSoup
import html2text
import time
import os
import csv
import random
import langdetect
from openai import OpenAI
 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
 
def detect_lang(text):
    try:
        return langdetect.detect(text)
    except:
        return "unknown"
 
def get_page_text(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=' ')
            return html2text.html2text(text)
    except:
        pass
    return ""
 
def get_all_links(base_url, max_pages=200):
    langs = ["", "/en", "/fr", "/nl", "/it", "/de", "/es"]
    pages = set()
    for lang in langs:
        full_url = base_url + lang
        try:
            response = requests.get(full_url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(response.text, 'html.parser')
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href']
                if any(x in href for x in [".jpg", ".png", ".css", ".js", "#", "tel:", "mailto:"]):
                    continue
                if href.startswith("/"):
                    pages.add(base_url + href)
                elif href.startswith("http") and base_url in href:
                    pages.add(href)
                if len(pages) >= max_pages:
                    break
        except:
            pass
    return list(pages)[:max_pages]
 
def check_linguistic_issues(text, api_key, allow_minor=False):
    prompt = f"""You are a senior translation QA specialist reviewing website content. Your task is to extract **exactly 1 example** of a linguistic issue from this content. Your focus should be on **clear, verifiable errors** that a native speaker or reviewer would reasonably flag.
 
Only include examples if they fall into these priority categories:
- Mistranslations
- Awkward phrasing
- Unnatural expressions
- Grammar issues
- Incorrect word choice
 
Avoid flagging issues related to:
- Punctuation only (e.g., missing quotes, commas, periods)
- Extra spaces
- Truncated or incomplete phrases unless clearly visible and wrong in full context
 
⚠️ You may include punctuation or spacing issues ONLY if no better errors exist in the entire input.
 
Response format:
- Original sentence: "..."
- Issue: [Short explanation]
- Suggested correction: "..."
 
If no issue is found, return an empty string.
 
Text:
{text[:5000]}"""
 
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a language quality control expert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return ""
 
def estimate_total_pages():
    return 1000
 
def get_intro_variation(domain):
    variants = [
        f"After a quick look at a few pages from {domain}, one of our reviewers noticed some language details that could be improved.",
        f"One of our expert linguists reviewed parts of {domain} and found a few small things that could hurt clarity or brand perception.",
        f"We had one of our senior linguists look over content from {domain}, and they found some phrasing issues that are easy to fix."
    ]
    return random.choice(variants)
 
def get_outro_variation(error_count, page_count, estimated_total_errors):
    body = f"{error_count} issues across just {page_count} pages suggests there might be significant inconsistencies throughout the site."
    ctas = [
        "Would you be open to a quick 15-minute call to go through a more in-depth review?",
        "We'd be happy to run a full audit if you'd like. Let us know if we should schedule a time.",
        "Let us know if you'd like us to prepare a detailed quote or deeper linguistic report.",
    ]
    return f"{body}\n\n{random.choice(ctas)}"
 
def generate_email(domain, examples, error_count, page_count, estimated_total_pages):
    estimated_total_errors = round((error_count / page_count) * estimated_total_pages) if page_count else "?"
    intro = get_intro_variation(domain)
    outro = get_outro_variation(error_count, page_count, estimated_total_errors)
    email = f"""{intro}
 
Here are a few examples:
 
{examples}
 
{outro}"""
    return email
 
def analyze_domain(domain: str, api_key: str):
    base_url = f"https://{domain}" if not domain.startswith("http") else domain
    links = get_all_links(base_url, max_pages=200)
    total_errors = 0
    collected_issues = []
    pages_used = 0

    for url in links:
        content = get_page_text(url)
        lang = detect_lang(content)
        if content and len(content) > 500:
            issues = check_linguistic_issues(content, api_key)
            if issues and "Original sentence:" in issues and "extra space" not in issues.lower() and "punctuation" not in issues.lower():
                formatted = f"{issues}\nURL: {url}\nLanguage: {lang.upper()}"
                collected_issues.append(formatted)
                total_errors += 1
                pages_used += 1
            if len(collected_issues) >= 3:
                break
            time.sleep(1)

    if len(collected_issues) < 3:
        for url in links:
            content = get_page_text(url)
            lang = detect_lang(content)
            if content and len(content) > 500:
                issues = check_linguistic_issues(content, api_key, allow_minor=True)
                if issues and "Original sentence:" in issues:
                    formatted = f"{issues}\nURL: {url}\nLanguage: {lang.upper()}"
                    collected_issues.append(formatted)
                    total_errors += 1
                    pages_used += 1
                if len(collected_issues) >= 3:
                    break
                time.sleep(1)

    if collected_issues:
        examples = "\n\n".join(collected_issues)
        email = generate_email(domain, examples, total_errors, pages_used, estimate_total_pages())
    else:
        email = f"After a brief review of {domain}, we didn't find any obvious linguistic mistakes. If you'd like us to look deeper or provide guidance, we'd be happy to assist."

    return email, collected_issues

if __name__ == "__main__":
    with open("test_sites.txt", "r", encoding="utf-8") as f:
        domains = [line.strip() for line in f if line.strip()]
    for domain in domains:
        print(f"\n🔍 Analyse de : {domain}")
        email, _ = analyze_domain(domain, "your_api_key_here")
        print(f"✅ Email généré pour {domain}")