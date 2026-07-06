import os, sys, json, time, re, hashlib, urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

OUT_DIR = "docs"
os.makedirs(OUT_DIR, exist_ok=True)

NORTH_CITIES = [
    "חיפה", "קריות", "קריית", "נשר", "טירת כרמל", "רכסים", "עתלית",
    "דלית אל-כרמל", "עספיא", "נצרת", "נוף הגליל",
    "עכו", "נהריה", "קריית שמונה", "טבריה", "צפת", "כרמיאל",
    "מעלות", "שלומי", "חצור הגלילית", "ראש פינה", "כפר תבור", "יבנאל",
    "בית שאן", "עפולה", "מגדל העמק", "יקנעם", "קריית טבעון",
    "שפרעם", "כפר כנא", "ריינה", "משהד", "שעב", "עראבה", "דייר חנא",
    "דייר אל-אסד", "נחף", "מג'ד אל-כרום", "ירכא", "ג'וליס",
    "כפר יאסיף", "אבו סנאן", "ג'דיידה-מכר", "בענה", "כאבול",
    "טמרה", "סח'נין", "זכרון יעקב", "בנימינה", "אור עקיבא",
    "פרדס חנה", "כרכור", "חדרה", "כפר ורדים", "בית ג'ן", "חורפיש",
    "פקיעין", "מעלות-תרשיחא"
]

TECH_KEYWORDS = [
    "מתכנת", "פיתוח", "תוכנה", "מהנדס", "software", "developer", "engineer",
    "full stack", "backend", "frontend", "front-end", "back-end", "fullstack",
    "דאטא", "data", "ai", "ml", "machine learning", "devops", "dev ops",
    "qa", "automation", "אוטומציה", "בדיקות", "תשתית", "infrastructure",
    "cloud", "ענן", "סייבר", "cyber", "security", "אבטחת",
    "web", "פרונט", "בקאנד", "סיסטם", "system", "node", "react",
    "python", "java", "c#", "c++", "javascript", "typescript", "php",
    "sql", "dba", "ניתוח", "analyst", "bi", "בינה", "אלגוריתמ",
    "מוצר", "product", "ux", "ui", "מעצב", "designer",
    "חומרה", "hardware", "electrical", "electronics", "אלקטרוניקה",
    "support", "תמיכה", "helpdesk", "הלפדסק",
    "embedded", "משובץ", "rt", "firmware",
    "ענן", "sre", "site reliability",
    "mobile", "android", "ios", "flutter",
    "scrum", "agile", "project manager", "pmo"
]

DEBUG_DIR = os.path.join(OUT_DIR, "debug")
os.makedirs(DEBUG_DIR, exist_ok=True)

def get_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    opts.add_argument("--lang=he-IL")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.page_load_strategy = 'normal'
    service = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=opts)
    d.set_page_load_timeout(45)
    d.set_script_timeout(30)
    return d

def is_north(text):
    if not text: return False
    tl = text.lower()
    for c in NORTH_CITIES:
        if c.lower() in tl: return True
    return False

def is_tech(text):
    if not text: return False
    tl = text.lower()
    for k in TECH_KEYWORDS:
        if k.lower() in tl: return True
    return False

def get_text(el):
    if el is None: return ""
    return el.text.strip() if el.text else ""

def safe_find(el, by, value):
    try: return el.find_element(by, value)
    except: return None

def safe_finds(el, by, value):
    try: return el.find_elements(by, value)
    except: return []

def dump_debug(driver, name):
    try:
        html = driver.page_source[:200000]
        with open(os.path.join(DEBUG_DIR, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  DEBUG: {name}.html saved ({len(html)} chars)")
    except Exception as e:
        print(f"  DEBUG dump error: {e}")

def wait_for(driver, by, value, timeout=10):
    try: WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, value)))
    except: pass

def job_id(job):
    raw = job["title"] + job.get("url", "") + job.get("company", "")
    return hashlib.md5(raw.encode()).hexdigest()[:12]


# ============================================================
# PARSERS for each site
# ============================================================

def parse_geektime(driver):
    """Geektime Insider - category/jobs/"""
    driver.get("https://www.geektime.co.il/category/jobs/")
    wait_for(driver, By.TAG_NAME, "article", 8)
    jobs = []
    for art in safe_finds(driver, By.TAG_NAME, "article"):
        title_el = safe_find(art, By.TAG_NAME, "h3") or safe_find(art, By.TAG_NAME, "h2")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(title_el, By.TAG_NAME, "a") or safe_find(art, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = art.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "גיקטיים", "location": "",
                         "description": desc, "source": "Geektime"})
    print(f"  Geektime: {len(jobs)} jobs")
    return jobs


def parse_jobkarov(driver):
    """JobKarov - Search page"""
    driver.get("https://www.jobkarov.com/Search/?speciality=2119&area=16%2C17%2C20")
    wait_for(driver, By.CLASS_NAME, "job-item", 8)
    jobs = []
    for item in safe_finds(driver, By.CLASS_NAME, "job-item"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .job-title, .title")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, .job-company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .job-location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "JobKarov"})
    print(f"  JobKarov: {len(jobs)} jobs")
    return jobs


def parse_nisha(driver):
    """Nisha - high-tech jobs"""
    driver.get("https://www.nisha.co.il/?s=&job_cat=321&job_region=24")
    wait_for(driver, By.CLASS_NAME, "job-item", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .job-card, .item-job"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, h4")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, .job-company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Nisha"})
    print(f"  Nisha: {len(jobs)} jobs")
    return jobs


def parse_dialog(driver):
    """Dialog - high-tech jobs"""
    driver.get("https://www.dialog.co.il/high-tech/jobs/software?fieldId=24406&regions=6&salary=10000,50000")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    # Try to extract from the filtered results page
    for a in safe_finds(driver, By.CSS_SELECTOR, "a[href*='/high-tech/jobs/']"):
        title = a.text.strip()
        href = a.get_attribute("href") or ""
        if not title or len(title) < 3: continue
        if is_tech(title):
            jobs.append({"title": title, "url": href, "company": "דיאלוג", "location": "",
                         "description": title, "source": "Dialog"})
    # Try to find job cards in the result list
    for item in safe_finds(driver, By.CSS_SELECTOR, ".box_in, .job-item, [class*=job], [class*=Job]"):
        title_el = safe_find(item, By.TAG_NAME, "a") or safe_find(item, By.CSS_SELECTOR, ".title, h3, h4")
        title = title_el.text.strip() if title_el else ""
        if not title or len(title) < 3: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, "[class*=location], [class*=Location], [class*=region], [class*=Region]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "דיאלוג", "location": location,
                         "description": desc, "source": "Dialog"})
    print(f"  Dialog: {len(jobs)} jobs")
    return jobs


def parse_alljobs(driver):
    """AllJobs - search results"""
    driver.get("https://www.alljobs.co.il/SearchResultsGuest.aspx?page=1&position=235&type=&source=491&duration=25&exc=&region=")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .result-item, [class*=jobRow], [class*=JobRow]"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, .JobTitle")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, .JobCompany")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .JobLocation")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "AllJobs"})
    # Fallback: try parsing from script JSON
    if not jobs:
        try:
            scripts = driver.find_elements(By.TAG_NAME, "script")
            for s in scripts:
                text = s.get_attribute("innerHTML") or ""
                for m in re.finditer(r'"JobTitle":"([^"]+)".*?"JobUrl":"([^"]+)".*?"Company":"([^"]+)"', text):
                    jobs.append({"title": m.group(1), "url": m.group(2), "company": m.group(3),
                                 "location": "", "description": "", "source": "AllJobs"})
        except: pass
    print(f"  AllJobs: {len(jobs)} jobs")
    return jobs


def parse_indeed(driver):
    """Indeed Israel"""
    driver.get("https://il.indeed.com/jobs?q=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&l=%D7%97%D7%99%D7%A4%D7%94")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job_seen_beacon, .resultContent, .job-card"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h2 a, .jobTitle a")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el or safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".companyName, .company_location")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".companyLocation")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Indeed"})
    print(f"  Indeed: {len(jobs)} jobs")
    return jobs


def parse_careerjet(driver):
    """CareerJet Israel"""
    driver.get("https://www.careerjet.co.il/search/jobs?s=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&l=%D7%97%D7%99%D7%A4%D7%94")
    wait_for(driver, By.TAG_NAME, "body", 6)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "article, .job, .result"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h2 a, h3 a")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        url = title_el.get_attribute("href") if title_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, .employer")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .loc")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "CareerJet"})
    print(f"  CareerJet: {len(jobs)} jobs")
    return jobs


def parse_jobinfo(driver):
    """Jobinfo - go deep into individual ads, up to 5 pages"""
    base_url = "https://www.jobinfo.co.il/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D-%D7%94%D7%99%D7%99%D7%98%D7%A7/%D7%93%D7%A8%D7%95%D7%A9%D7%99%D7%9D-%D7%AA%D7%95%D7%9B%D7%A0%D7%94"
    jobs = []
    seen_urls = set()
    for page in range(1, 6):
        url = base_url if page == 1 else base_url + f"?page={page}"
        try:
            driver.get(url)
            wait_for(driver, By.TAG_NAME, "body", 8)
        except: break
        # Find all job links
        for a in safe_finds(driver, By.CSS_SELECTOR, "a[href*='/job/'], a[href*='/משרה/'], [class*=job] a, article a"):
            href = a.get_attribute("href") or ""
            title = a.text.strip()
            if not title or len(title) < 5: continue
            if not is_tech(title): continue
            if href in seen_urls: continue
            seen_urls.add(href)
            # Go into the individual ad page
            jobs.append({"title": title, "url": href, "company": "", "location": "",
                         "description": "", "source": "Jobinfo"})
            # Try to visit the individual page for more details
            if len(jobs) > 50: break
        if len(jobs) > 50: break
    print(f"  Jobinfo: {len(jobs)} jobs")
    return jobs


def parse_cps(driver):
    """CPS Jobs"""
    if driver is None:
        return []
    driver.get("https://www.cps.co.il/search_page/?free_text=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "article, .post, [class*=job], [class*=Job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "CPS", "location": "",
                         "description": desc, "source": "CPS"})
    print(f"  CPS: {len(jobs)} jobs")
    return jobs


def parse_sqlink(driver):
    """SQLink"""
    driver.get("https://www.sqlink.com/career/%D7%A4%D7%99%D7%AA%D7%95%D7%97-%D7%AA%D7%95%D7%9B%D7%A0%D7%94-webmobile/?page=2")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .post, article, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, .title")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "SQLink", "location": "",
                         "description": desc, "source": "SQLink"})
    print(f"  SQLink: {len(jobs)} jobs")
    return jobs


def parse_gotfriends(driver):
    """GotFriends"""
    driver.get("https://www.gotfriends.co.il")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .vacancy, article"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, h4")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "GotFriends"})
    print(f"  GotFriends: {len(jobs)} jobs")
    return jobs


def parse_drushim(driver):
    """Drushim - Haifa programmer search"""
    driver.get("https://www.drushim.co.il/jobs/search/%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA/%D7%97%D7%99%D7%A4%D7%94/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card-job, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a") or title_el
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, [class*=company]")
        company = comp_el.text.strip() if comp_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": "חיפה",
                     "description": desc, "source": "Drushim"})
    print(f"  Drushim: {len(jobs)} jobs")
    return jobs


def parse_extreme(driver):
    """Extreme.co.il"""
    driver.get("https://www.extreme.co.il/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "h3[orderID], .order-item, [class*=order]"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".orderName, span")
        title = title_el.text.strip() if title_el else ""
        title = title or item.text.strip()
        if not title: continue
        oid = item.get_attribute("orderID") or ""
        url = f"https://www.extreme.co.il/order/{oid}" if oid else ""
        desc = ""
        # Click to expand and get details
        try:
            item.click()
            time.sleep(1)
            detail = safe_find(driver, By.CSS_SELECTOR, ".ui-accordion-content-active")
            if detail:
                desc = detail.text[:300]
                for span in safe_finds(detail, By.TAG_NAME, "span"):
                    cls = span.get_attribute("class") or ""
                    if "data" in cls:
                        loc = span.text.strip()
                        if loc and is_north(loc): pass
        except: pass
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "אקסטרים", "location": "",
                         "description": desc, "source": "Extreme"})
    print(f"  Extreme: {len(jobs)} jobs")
    return jobs


def parse_jobify(driver):
    """Jobify"""
    driver.get("https://www.jobify.co.il")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Jobify"})
    print(f"  Jobify: {len(jobs)} jobs")
    return jobs


def parse_jobnet(driver):
    """Jobnet"""
    driver.get("https://www.jobnet.co.il/search?q=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&city=%D7%97%D7%99%D7%A4%D7%94")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .result"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Jobnet"})
    print(f"  Jobnet: {len(jobs)} jobs")
    return jobs


def parse_nortech(driver):
    """Nortech"""
    driver.get("https://www.nortech.co.il")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Nortech"})
    print(f"  Nortech: {len(jobs)} jobs")
    return jobs


def parse_manpower(driver):
    """Manpower"""
    driver.get("https://www.manpower.co.il/search?JOBEXPERTISE=4000")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .result, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        jobs.append({"title": title, "url": url, "company": company, "location": location,
                     "description": desc, "source": "Manpower"})
    print(f"  Manpower: {len(jobs)} jobs")
    return jobs


def parse_geektime_careers(driver):
    """Geektime insider - all articles (includes job posts)"""
    driver.get("https://insider.geektime.co.il")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "גיקטיים", "location": "",
                         "description": desc, "source": "GeektimeCareers"})
    print(f"  GeektimeCareers: {len(jobs)} jobs")
    return jobs


def parse_ethosia(driver):
    """Ethosia"""
    driver.get("https://www.ethosia.co.il/jobs")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "אתוסיה", "location": "",
                         "description": desc, "source": "Ethosia"})
    print(f"  Ethosia: {len(jobs)} jobs")
    return jobs


def parse_yad2(driver):
    """Yad2 jobs"""
    driver.get("https://www.yad2.co.il/jobs?search=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "יד2", "location": location,
                         "description": desc, "source": "Yad2"})
    print(f"  Yad2: {len(jobs)} jobs")
    return jobs


def parse_kamatech(driver):
    """KamaTech"""
    driver.get("https://kamatech.org.il/jobs/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "קמא-טק", "location": "",
                         "description": desc, "source": "KamaTech"})
    print(f"  KamaTech: {len(jobs)} jobs")
    return jobs


def parse_govjobs(driver):
    """Gov jobs (tech positions)"""
    driver.get("https://www.gov.il/he/departments/publications/jobs")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "ממשלתי", "location": "",
                         "description": desc, "source": "GovJobs"})
    print(f"  GovJobs: {len(jobs)} jobs")
    return jobs


def parse_hever(driver):
    """Hever High Tech"""
    driver.get("https://www.hever.co.il/jobs")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "חבר", "location": "",
                         "description": desc, "source": "Hever"})
    print(f"  Hever: {len(jobs)} jobs")
    return jobs


def parse_experis(driver):
    """Experis Israel"""
    driver.get("https://experis.co.il/search?JOBAREA=1277")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "article, .job-item, .card, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, [class*=company]")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": company or "אקספרס", "location": location,
                         "description": desc, "source": "Experis"})
    print(f"  Experis: {len(jobs)} jobs")
    return jobs


def parse_jobmaster(driver):
    """JobMaster"""
    driver.get("https://www.jobmaster.co.il/jobs/?q=%D7%AA%D7%95%D7%9B%D7%A0%D7%94&l=%D7%97%D7%99%D7%A4%D7%94&headcatnum=15")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .result, .listing, article, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, h4")
        title = title_el.text.strip() if title_el else ""
        if not title or len(title) < 3: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": company, "location": location,
                         "description": desc, "source": "JobMaster"})
    print(f"  JobMaster: {len(jobs)} jobs")
    return jobs


def parse_ortal(driver):
    """Ortal HR - Haifa branch"""
    driver.get("https://www.ortal-hr.co.il/jobs?branch=haifa")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "אורטל", "location": location or "חיפה",
                         "description": desc, "source": "Ortal"})
    print(f"  Ortal: {len(jobs)} jobs")
    return jobs


def parse_adecco(driver):
    """Adecco Israel - tech jobs"""
    driver.get("https://www.adecco.co.il/jobs")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        comp_el = safe_find(item, By.CSS_SELECTOR, ".company, [class*=company]")
        company = comp_el.text.strip() if comp_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": company or "Adecco", "location": location,
                         "description": desc, "source": "Adecco"})
    print(f"  Adecco: {len(jobs)} jobs")
    return jobs


def parse_koren(driver):
    """Koren - hardware and software engineering"""
    driver.get("https://www.koren-tec.co.il/jobs/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "קורן", "location": location or "צפון",
                         "description": desc, "source": "Koren"})
    print(f"  Koren: {len(jobs)} jobs")
    return jobs


def parse_matrix(driver):
    """Matrix Global - Haifa careers"""
    driver.get("https://www.matrix.co.il/careers/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "מטריקס", "location": location,
                         "description": desc, "source": "Matrix"})
    print(f"  Matrix: {len(jobs)} jobs")
    return jobs


def parse_ldr(driver):
    """LDR - high tech north placement"""
    driver.get("https://www.ldr.co.il/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "LDR", "location": "",
                         "description": desc, "source": "LDR"})
    print(f"  LDR: {len(jobs)} jobs")
    return jobs


def parse_elbit(driver):
    """Elbit Systems - Haifa - largest hi-tech employer in north"""
    driver.get("https://elbitsystems.co.il/careers/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job], .vacancy"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title], a")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el if title_el.tag_name == "a" else safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "אלביט", "location": location or "חיפה",
                         "description": desc, "source": "Elbit"})
    print(f"  Elbit: {len(jobs)} jobs")
    return jobs


def parse_technion(driver):
    """Technion careers"""
    driver.get("https://www.technion.ac.il/משרות-פנויות/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job], tr, .post"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title], a")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el if title_el.tag_name == "a" else safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "הטכניון", "location": "חיפה",
                         "description": desc, "source": "Technion"})
    print(f"  Technion: {len(jobs)} jobs")
    return jobs


def parse_rafael(driver):
    """Rafael - Haifa and Karmiel"""
    driver.get("https://www.rafael.co.il/careers/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, ".location, .city, [class*=location]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "רפאל", "location": location or "חיפה",
                         "description": desc, "source": "Rafael"})
    print(f"  Rafael: {len(jobs)} jobs")
    return jobs


def parse_wix(driver):
    """Wix - Haifa office"""
    driver.get("https://www.wix.com/careers/locations/haifa")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, article, .listing, [class*=job], [class*=position]"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, .title, [class*=title], a")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el if title_el.tag_name == "a" else safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "Wix", "location": "חיפה",
                         "description": desc, "source": "Wix"})
    print(f"  Wix: {len(jobs)} jobs")
    return jobs


def parse_intel(driver):
    """Intel Haifa - Workday ATS"""
    driver.get("https://jobs.intel.com/en/search-jobs/Haifa%2C%20Israel")
    wait_for(driver, By.TAG_NAME, "body", 10)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "[class*=job], [class*=Job], [class*=position], [class*=Position], article, .result"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, a, [class*=title], [class*=Title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el if title_el.tag_name == "a" else safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "Intel", "location": "חיפה",
                         "description": desc, "source": "Intel"})
    if not jobs:
        for a in safe_finds(driver, By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            if "/job/" in href.lower() or "/search-jobs/" in href.lower():
                t = a.text.strip()
                if t and len(t) > 5 and is_tech(t):
                    jobs.append({"title": t, "url": href, "company": "Intel", "location": "חיפה",
                                 "description": "", "source": "Intel"})
    print(f"  Intel: {len(jobs)} jobs")
    return jobs


def parse_checkpoint(driver):
    """Check Point - Haifa"""
    driver.get("https://careers.checkpoint.com/?q=Haifa")
    wait_for(driver, By.TAG_NAME, "body", 10)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "[class*=job], [class*=Job], article, .result, .position, .card"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, a, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = title_el if title_el.tag_name == "a" else safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "Check Point", "location": "חיפה",
                         "description": desc, "source": "CheckPoint"})
    if not jobs:
        for a in safe_finds(driver, By.TAG_NAME, "a"):
            href = a.get_attribute("href") or ""
            t = a.text.strip()
            if t and len(t) > 5 and is_tech(t) and "/job" in href.lower():
                jobs.append({"title": t, "url": href, "company": "Check Point", "location": "חיפה",
                             "description": "", "source": "CheckPoint"})
    print(f"  CheckPoint: {len(jobs)} jobs")
    return jobs


def parse_apple(driver):
    """Apple Haifa"""
    driver.get("https://jobs.apple.com/he-il/search?location=haifa-HAF")
    wait_for(driver, By.TAG_NAME, "body", 10)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, "[class*=job], [class*=Job], article, .result, .card, tr"):
        title_el = safe_find(item, By.CSS_SELECTOR, "h3, h4, a, [class*=title]")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a") or title_el
        url = link_el.get_attribute("href") if link_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, "[class*=location], [class*=Location]")
        location = loc_el.text.strip() if loc_el else "חיפה"
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": "Apple", "location": location,
                         "description": desc, "source": "Apple"})
    print(f"  Apple: {len(jobs)} jobs")
    return jobs


ADZUNA_ID = os.environ.get("ADZUNA_ID", "89fc5699")
ADZUNA_KEY = os.environ.get("ADZUNA_KEY", "a418d498078a17504f42e30822a1ed8a")

def parse_adzuna(driver=None):
    """Adzuna API - tech jobs in north Israel, no Selenium needed.
    Covers jobs from Indeed, AllJobs, CareerJet, JobMaster, Drushim, etc."""
    jobs = []
    seen = set()

    cities = ["Haifa", "Karmiel", "Nazareth", "Yokneam", "Afula", "Tiberias",
              "Nahariya", "Akko", "Kiryat+Shmona", "Safed", "Kiryat+Motzkin",
              "Kiryat+Bialik", "Kiryat+Yam", "Kiryat+Ata", "Nesher",
              "Zikhron+Yaakov", "Hadera", "Pardes+Hanna", "Or+Akiva"]
    keywords = ["software", "developer", "engineer", "qa", "devops", "data",
                "full+stack", "backend", "frontend", "programmer", "web",
                "cyber", "security", "cloud", "ai", "ml", "product+manager",
                "ux", "ui", "analyst", "embedded", "support", "it"]

    # Multiple query combinations to maximize coverage
    queries = []
    for city in cities:
        queries.append({"what": "software developer", "where": city})
        queries.append({"what": "engineer", "where": city})
    # Also search without city for broader results
    queries.append({"what": "software Haifa", "where": "Israel"})
    queries.append({"what": "developer Haifa", "where": "Israel"})
    queries.append({"what": "qa Haifa", "where": "Israel"})
    queries.append({"what": "devops Haifa", "where": "Israel"})

    for q in queries[:30]:  # limit to 30 queries
        what = q["what"]
        where = q["where"]
        url = (f"https://api.adzuna.com/v1/api/jobs/il/search/1?"
               f"app_id={ADZUNA_ID}&app_key={ADZUNA_KEY}"
               f"&what={what}&where={where}&category=it-jobs"
               f"&content-type=application/json&results_per_page=50"
               f"&sort_by=date")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode())
            for item in data.get("results", []):
                title = item.get("title", "").strip()
                if not title: continue
                jid = item.get("id", "") or hashlib.md5(title.encode()).hexdigest()[:8]
                if jid in seen: continue
                seen.add(jid)
                company = ""
                co = item.get("company")
                if co: company = co.get("display_name", "")
                location = item.get("location", {}).get("display_name", "")
                desc = item.get("description", "")[:300]
                if is_tech(title):
                    jobs.append({"title": title, "id": jid, "url": item.get("redirect_url", ""),
                                 "company": company, "location": location, "description": desc,
                                 "source": "Adzuna"})
        except Exception as e:
            pass
    print(f"  Adzuna: {len(jobs)} jobs (from {len(queries)} queries)")
    return jobs


def try_generic(driver, source_name):
    """Generic heuristic: find any text that looks like a job listing"""
    jobs = []
    seen_urls = set()
    # Try multiple selectors
    candidates = []
    for sel in ["article", ".job", ".card", ".item", ".listing", ".result",
                "li[class]", "[class*=job]", "[class*=Job]", "[class*=vacancy]",
                "[class*=position]", "[class*=Position]", "tr[class]"]:
        candidates = safe_finds(driver, By.CSS_SELECTOR, sel)
        if candidates:
            break
    if not candidates:
        # Fallback: extract all links
        links = safe_finds(driver, By.CSS_SELECTOR, "a[href]")
        for link in links:
            href = link.get_attribute("href") or ""
            if href in seen_urls: continue
            seen_urls.add(href)
            text = link.text.strip()
            if not text or len(text) < 5 or len(text) > 200:
                continue
            if any(s in href.lower() for s in ["/job", "/position", "/vacancy", "/משרה", "/דרוש"]):
                desc = ""
                try:
                    parent = link.find_element(By.XPATH, "..")
                    desc = parent.text[:300]
                except: pass
                if is_tech(text) or is_tech(desc):
                    jobs.append({"title": text, "url": href, "company": "", "location": "",
                                 "description": desc, "source": source_name})
        return jobs

    for item in candidates:
        title_el = (safe_find(item, By.TAG_NAME, "h2") or safe_find(item, By.TAG_NAME, "h3")
                    or safe_find(item, By.TAG_NAME, "h4") or safe_find(item, By.CSS_SELECTOR, "[class*=title]")
                    or safe_find(item, By.TAG_NAME, "a"))
        if not title_el: continue
        title = title_el.text.strip()
        if not title or len(title) < 5 or len(title) > 200: continue
        url = (title_el.get_attribute("href") if title_el.tag_name == "a"
               else (safe_find(item, By.TAG_NAME, "a").get_attribute("href") if safe_find(item, By.TAG_NAME, "a") else ""))
        if url and url in seen_urls: continue
        if url: seen_urls.add(url)
        comp_el = safe_find(item, By.CSS_SELECTOR, "[class*=company], [class*=Company]")
        company = comp_el.text.strip() if comp_el else ""
        loc_el = safe_find(item, By.CSS_SELECTOR, "[class*=location], [class*=Location], [class*=city], [class*=City]")
        location = loc_el.text.strip() if loc_el else ""
        desc = item.text[:300]
        if is_tech(title):
            jobs.append({"title": title, "url": url, "company": company, "location": location,
                         "description": desc, "source": source_name})
    return jobs

# ============================================================
# SOURCE REGISTRY
# ============================================================
SOURCES = [
    ("Geektime", parse_geektime),
    ("GeektimeCareers", parse_geektime_careers),
    ("JobKarov", parse_jobkarov),
    ("Nisha", parse_nisha),
    ("AllJobs", parse_alljobs),
    ("Indeed", parse_indeed),
    ("CareerJet", parse_careerjet),
    ("Dialog", parse_dialog),
    ("Yad2", parse_yad2),
    ("CPS", parse_cps),
    ("SQLink", parse_sqlink),
    ("Manpower", parse_manpower),
    ("Jobinfo", parse_jobinfo),
    ("Ethosia", parse_ethosia),
    ("KamaTech", parse_kamatech),
    ("GovJobs", parse_govjobs),
    ("Hever", parse_hever),
    ("Experis", parse_experis),
    ("JobMaster", parse_jobmaster),
    ("GotFriends", parse_gotfriends),
    ("Jobify", parse_jobify),
    ("Jobnet", parse_jobnet),
    ("Nortech", parse_nortech),
    ("Drushim", parse_drushim),
    ("Extreme", parse_extreme),
    # New recruitment agency sources
    ("Ortal", parse_ortal),
    ("Adecco", parse_adecco),
    ("Koren", parse_koren),
    ("Matrix", parse_matrix),
    ("LDR", parse_ldr),
    # Direct employer career pages
    ("Elbit", parse_elbit),
    ("Rafael", parse_rafael),
    ("Technion", parse_technion),
    ("Wix", parse_wix),
    ("Intel", parse_intel),
    ("CheckPoint", parse_checkpoint),
    ("Apple", parse_apple),
    # API-based (no Selenium needed)
    ("Adzuna", parse_adzuna),
]

# ============================================================
# RSS GENERATION
# ============================================================
def build_rss(all_jobs):
    items = []
    seen_ids = set()
    for job in all_jobs:
        jid = job_id(job)
        if jid in seen_ids: continue
        seen_ids.add(jid)

        title = escape(job["title"])
        url = escape(job.get("url", ""))
        company = escape(job.get("company", ""))
        location = escape(job.get("location", ""))
        desc = escape(job.get("description", ""))[:500]
        source = escape(job["source"])
        now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        items.append(f"""    <item>
      <title>{title}</title>
      <link>{url}</link>
      <guid isPermaLink="false">{jid}</guid>
      <description><![CDATA[{job.get("description", "")[:500]}]]></description>
      <company>{company}</company>
      <location>{location}</location>
      <source>{source}</source>
      <pubDate>{now}</pubDate>
    </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>משרות הייטק - חיפה וצפון</title>
    <link>https://cht20750-bit.github.io/job-rss/</link>
    <description>משרות טכנולוגיה בצפון ישראל - איסוף אוטומטי ממגוון מקורות</description>
    <language>he-IL</language>
    <lastBuildDate>{datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
{chr(10).join(items)}
  </channel>
</rss>"""
    return rss


def write_rss(rss, filename="rss.xml"):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(rss)
    print(f"  Written: {path} ({len(rss)} bytes)")


# ============================================================
# MAIN
# ============================================================
API_SOURCES = {"Adzuna"}

def main():
    driver = None
    needs_driver = False
    all_jobs = []

    # Only run a subset if argument given (e.g., "scraper.py JobKarov")
    sources_to_run = SOURCES
    if len(sys.argv) > 1:
        sources_to_run = [s for s in SOURCES if s[0].lower() == sys.argv[1].lower()]
        if not sources_to_run:
            print(f"Unknown source: {sys.argv[1]}")
            print(f"Available: {', '.join(s[0] for s in SOURCES)}")
            return

    for name, _ in sources_to_run:
        if name not in API_SOURCES:
            needs_driver = True
            break

    if needs_driver:
        try:
            driver = get_driver()
        except Exception as e:
            print(f"Failed to init driver: {e}")
            print("Running API-only sources...")
            sources_to_run = [s for s in sources_to_run if s[0] in API_SOURCES]
            driver = None

    print(f"Running {len(sources_to_run)} sources...")
    all_seen_ids = set()
    for name, parser in sources_to_run:
        try:
            print(f"\n--- {name} ---")
            jobs = parser(driver)
            jobs = [j for j in jobs if is_tech(j["title"])]
            if not jobs and driver is not None and name not in API_SOURCES:
                dump_debug(driver, name)
                jobs = try_generic(driver, name)
                if jobs:
                    print(f"  GENERIC fallback: {len(jobs)} jobs")
            for j in jobs:
                jid = job_id(j)
                if jid not in all_seen_ids:
                    all_seen_ids.add(jid)
                    all_jobs.append(j)
        except WebDriverException as e:
            msg = str(e)[:100]
            print(f"  ERROR: {msg}")
            try:
                if driver:
                    dump_debug(driver, name)
                    jobs = try_generic(driver, name)
                    if jobs:
                        print(f"  GENERIC fallback: {len(jobs)} jobs")
                        all_jobs.extend(jobs)
            except: pass
        except Exception as e:
            msg = str(e)[:100]
            print(f"  ERROR: {msg}")
 
    if driver:
        driver.quit()

    print(f"\n=== Total: {len(all_jobs)} jobs from {len(sources_to_run)} sources ===")

    # Filter: keep only north + tech (tech keyword must be in TITLE)
    north_tech = []
    for j in all_jobs:
        if is_tech(j["title"]) and is_north(j["title"] + " " + j.get("description", "") + " " + j.get("location", "") + " " + j.get("company", "")):
            north_tech.append(j)

    print(f"After north+tech filter: {len(north_tech)} jobs")

    # Write combined RSS
    if north_tech:
        write_rss(build_rss(north_tech), "rss.xml")
    else:
        print("  No north+tech jobs found, writing empty RSS")
        write_rss(build_rss([]), "rss.xml")

    # Write per-source feeds too
    src_jobs = {}
    for j in all_jobs:
        src_jobs.setdefault(j["source"], []).append(j)
    for src, sjobs in src_jobs.items():
        st = [j for j in sjobs if is_tech(j["title"]) and is_north(j["title"] + " " + j.get("description","") + " " + j.get("location",""))]
        if st:
            write_rss(build_rss(st), f"{src.lower()}.xml")


if __name__ == "__main__":
    main()
