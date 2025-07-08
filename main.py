import requests
from bs4 import BeautifulSoup
import html2text
import time
import os
import csv
import random
import langdetect
from openai import OpenAI
import logging
import urllib.robotparser
import urllib.request
import ssl
from urllib.parse import urljoin, urlparse
 
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
 
def detect_lang(text):
    try:
        return langdetect.detect(text)
    except:
        return "unknown"
 
def get_page_text(url):
    logging.info(f"Fetching page text for URL: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            text = soup.get_text(separator=' ')
            return html2text.html2text(text)
        else:
            logging.warning(f"Non-200 status code {response.status_code} for URL: {url}")
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
    return ""
 
def get_all_links(base_url, max_pages=200, allowed_languages=None, tld_mode=False):
    logging.info(f"Getting all links from base URL: {base_url}")
    # Use allowed_languages to build language variants
    if allowed_languages and not tld_mode:
        langs = [""] + [f"/{code}" for code in allowed_languages if code != ""]
    else:
        langs = [""]
    logging.info(f"Language variants considered for link crawling: {langs}")
    pages = set()
    checked_links = set()
    parsed = urlparse(base_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}"
    for lang in langs:
        full_url = urljoin(root_url + "/", lang.lstrip("/"))
        try:
            response = requests.get(full_url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(response.text, 'html.parser')
            for a_tag in soup.find_all("a", href=True):
                href = a_tag['href']
                if any(x in href for x in [".jpg", ".png", ".css", ".js", "#", "tel:", "mailto:"]):
                    continue
                candidate_url = None
                if href.startswith("/"):
                    candidate_url = urljoin(root_url + "/", href.lstrip("/"))
                elif href.startswith("http") and root_url in href:
                    candidate_url = href
                else:
                    continue
                if candidate_url in checked_links:
                    continue
                # Only add candidate_url if it matches allowed language paths (for .com)
                if allowed_languages and not tld_mode:
                    parsed_candidate = urlparse(candidate_url)
                    path = parsed_candidate.path
                    if not (path == "/" or any(path.startswith(f"/{code}") for code in allowed_languages if code)):
                        continue
                checked_links.add(candidate_url)
                # Fetch and check language if filtering is enabled and not tld_mode
                if allowed_languages is not None and not tld_mode:
                    page_text = get_page_text(candidate_url)
                    lang_code = detect_lang(page_text)
                    if lang_code not in allowed_languages:
                        continue
                pages.add(candidate_url)
                if len(pages) >= max_pages:
                    break
            if len(pages) >= max_pages:
                break
        except Exception as e:
            logging.error(f"Error getting links from {full_url}: {e}")
    logging.info(f"Found {len(pages)} pages from {base_url} matching allowed_languages={allowed_languages} tld_mode={tld_mode}")
    return list(pages)[:max_pages]
 
def check_linguistic_issues(text, existing_sentences, api_key, allow_minor=False, prompt_template=None):
    logging.info(f"Checking linguistic issues (allow_minor={allow_minor}) on text of length {len(text)}")
    if prompt_template is None:
        prompt_template = (
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
            "Text:\n{text}"  # {text} will be replaced below
        )
    prompt = prompt_template.format(text=text[:5000])
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
        result = response.choices[0].message.content.strip()
        if any(orig in result for orig in existing_sentences):
            return ""
        return result
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
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
 
def analyze_domain(domain: str, api_key: str, prompt_template=None, allowed_languages=None, use_robots_enlargement=False):
    logging.info(f"Starting analysis for domain: {domain}")
    base_url = f"https://{domain}" if not domain.startswith("http") else domain
    from urllib.parse import urlparse, urljoin
    parsed = urlparse(base_url)
    root_url = f"{parsed.scheme}://{parsed.netloc}"

    # Determine TLD mode
    tld = parsed.netloc.split('.')[-1].lower()
    tld_mode = tld != 'com'

    # Try to fetch and parse robots.txt, ignoring SSL verification
    robots_url = root_url.rstrip("/") + "/robots.txt"
    logging.info(f"Attempting to fetch robots.txt from: {robots_url}")
    rp = urllib.robotparser.RobotFileParser()
    def fetch_robots_txt(url):
        context = ssl._create_unverified_context()
        try:
            with urllib.request.urlopen(url, context=context) as response:
                logging.info(f"Successfully fetched robots.txt from: {url}")
                return response.read().decode('utf-8')
        except Exception as e:
            logging.warning(f"Could not fetch robots.txt: {e}")
            return None

    base_urls_to_crawl = [root_url]
    if use_robots_enlargement:
        robots_txt = fetch_robots_txt(robots_url)
        if robots_txt:
            logging.info(f"Parsing robots.txt for allowed paths.")
            rp.parse(robots_txt.splitlines())
            allowed_domains = set()
            # Always add the current root domain
            allowed_domains.add(root_url)
            # Parse robots.txt for any full URLs in Sitemap, Allow, or Disallow rules
            for line in robots_txt.splitlines():
                line = line.strip()
                if (
                    line.lower().startswith('allow:') or
                    line.lower().startswith('disallow:') or
                    line.lower().startswith('sitemap:')
                ):
                    value = line.split(':', 1)[1].strip()
                    if value.startswith('http://') or value.startswith('https://'):
                        parsed_url = urlparse(value)
                        domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        allowed_domains.add(domain_url)
            # Use allowed_languages from the UI instead of hardcoded langs
            if allowed_languages and not tld_mode:
                langs = [""] + [f"/{code}" for code in allowed_languages if code != ""]
            else:
                langs = [""]
            logging.info(f"Language variants considered for robots.txt enlargement: {langs}")
            for lang in langs:
                test_url = urljoin(root_url + "/", lang.lstrip("/"))
                if rp.can_fetch("*", test_url):
                    parsed_url = urlparse(test_url)
                    domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                    allowed_domains.add(domain_url)
                    logging.info(f"Added allowed domain from robots.txt/lang variant: {domain_url} (lang path: '{lang}')")
            # Deduplicate base domains, treating www and non-www as the same domain (prefer non-www)
            normalized_domains = {}
            for domain_url in allowed_domains:
                parsed = urlparse(domain_url)
                netloc = parsed.netloc.lower()
                # Remove www. for normalization
                if netloc.startswith('www.'):
                    netloc_naked = netloc[4:]
                else:
                    netloc_naked = netloc
                # Always prefer non-www if both exist
                if netloc_naked not in normalized_domains or not netloc.startswith('www.'):
                    normalized_domains[netloc_naked] = f"{parsed.scheme}://{netloc_naked}"
            base_urls_to_crawl = list(normalized_domains.values())
            if base_urls_to_crawl:
                logging.info(f"Allowed base domains from robots.txt: {base_urls_to_crawl}")
            else:
                logging.info(f"No allowed base domains found in robots.txt, falling back to default base_url.")
                base_urls_to_crawl = [root_url]
        else:
            logging.warning("robots.txt not found or could not be fetched. Falling back to default logic.")
            base_urls_to_crawl = [root_url]

    # Aggregate links from all allowed base URLs, splitting the limit equally
    links = set()
    max_total_pages = 200
    num_bases = len(base_urls_to_crawl)
    if num_bases > 0:
        per_base_limit = max(1, max_total_pages // num_bases)
    else:
        per_base_limit = max_total_pages
    for crawl_url in base_urls_to_crawl:
        new_links = get_all_links(crawl_url, max_pages=per_base_limit, allowed_languages=allowed_languages, tld_mode=tld_mode)
        links.update(new_links)
    links = list(links)
    total_errors = 0
    collected_issues = []
    pages_used = 0
    used_sentences = set()

    # First pass: look for major issues
    for url in links:
        logging.info(f"Analyzing URL: {url}")
        content = get_page_text(url)
        lang = detect_lang(content)
        if allowed_languages is not None and not tld_mode and lang not in allowed_languages:
            logging.info(f"Skipping URL due to language '{lang}' not in allowed_languages: {allowed_languages}")
            continue
        if content and len(content) > 500:
            issue = check_linguistic_issues(content, used_sentences, api_key, prompt_template=prompt_template)
            if issue and "Original sentence:" in issue:
                sentence_line = issue.split("\n")[0]
                if sentence_line not in used_sentences:
                    formatted = f"{issue}\nURL: {url}\nLanguage: {lang.upper()}"
                    collected_issues.append(formatted)
                    used_sentences.add(sentence_line)
                    total_errors += 1
                    pages_used += 1
            if len(collected_issues) >= 7:
                break
            time.sleep(1)
        else:
            logging.info(f"Skipping URL due to insufficient content or empty: {url}")

    # Second pass: allow minor issues if not enough found
    if len(collected_issues) < 7:
        logging.info("Trying to find minor issues...")
        for url in links:
            content = get_page_text(url)
            lang = detect_lang(content)
            if allowed_languages is not None and not tld_mode and lang not in allowed_languages:
                logging.info(f"Skipping URL due to language '{lang}' not in allowed_languages: {allowed_languages}")
                continue
            if content and len(content) > 500:
                issue = check_linguistic_issues(content, used_sentences, api_key, allow_minor=True, prompt_template=prompt_template)
                if issue and "Original sentence:" in issue:
                    sentence_line = issue.split("\n")[0]
                    if sentence_line not in used_sentences:
                        formatted = f"{issue}\nURL: {url}\nLanguage: {lang.upper()}"
                        collected_issues.append(formatted)
                        used_sentences.add(sentence_line)
                        total_errors += 1
                        pages_used += 1
                if len(collected_issues) >= 7:
                    break
                time.sleep(1)
            else:
                logging.info(f"Skipping URL due to insufficient content or empty: {url}")

    if collected_issues:
        examples = "\n\n".join(collected_issues)
        email = generate_email(domain, examples, total_errors, pages_used, estimate_total_pages())
        logging.info(f"Generated email for {domain}")
    else:
        email = f"After a review of {domain}, no clear linguistic issues were identified. We'd be happy to run a deeper audit if needed."
        logging.info(f"No issues found for {domain}")

    return email, collected_issues

if __name__ == "__main__":
    # Entry point intentionally left blank; domain input is now handled via the UI.
    pass