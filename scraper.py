import os, sys, json, time, re, hashlib
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
    "דלית אל-כרמל", "עספיא", "נצרת", "נצרת עילית", "נוף הגליל",
    "עכו", "נהריה", "קריית שמונה", "טבריה", "צפת", "כרמיאל",
    "מעלות", "שלומי", "חצור הגלילית", "ראש פינה", "כפר תבור", "יבנאל",
    "בית שאן", "עפולה", "מגדל העמק", "יקנעם", "קריית טבעון",
    "שפרעם", "כפר כנא", "ריינה", "משהד", "שעב", "עראבה", "דייר חנא",
    "דייר אל-אסד", "נחף", "מג'ד אל-כרום", "ירכא", "ג'וליס",
    "כפר יאסיף", "אבו סנאן", "ג'דיידה-מכר", "בענה", "כאבול",
    "טמרה", "סח'נין", "זכרון יעקב", "בנימינה", "אור עקיבא",
    "פרדס חנה", "כרכור", "חדרה", "כפר ורדים", "בית ג'ן", "חורפיש",
    "פקיעין", "מעלות-תרשיחא", "הרצליה", "תל אביב", "רמת גן",
    "גבעתיים", "ראשון לציון", "פתח תקווה", "נתניה", "אשדוד",
    "באר שבע", "ירושלים", "מודיעין", "רחובות", "חולון", "בת ים",
    "כפר סבא", "רעננה", "הוד השרון", "אלעד", "בית שמש"
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
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)

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
    driver.get("https://www.jobkarov.com/Search/?area=16")
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
    driver.get("https://www.nisha.co.il/job_cat/high-tech/")
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
    driver.get("https://www.dialog.co.il/high-tech/jobs/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .job-card, [class*=job], [class*=position]"):
        title_el = safe_find(item, By.CSS_SELECTOR, ".title, h3, h4")
        title = title_el.text.strip() if title_el else ""
        if not title: continue
        link_el = safe_find(item, By.TAG_NAME, "a")
        url = link_el.get_attribute("href") if link_el else ""
        desc = item.text[:300]
        if is_tech(title) or is_tech(desc):
            jobs.append({"title": title, "url": url, "company": "דיאלוג", "location": "",
                         "description": desc, "source": "Dialog"})
    print(f"  Dialog: {len(jobs)} jobs")
    return jobs


def parse_alljobs(driver):
    """AllJobs - search results"""
    driver.get("https://www.alljobs.co.il/SearchResultsGuest.aspx?position=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&type=5")
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
    """Jobinfo"""
    urls = [
        "https://www.jobinfo.co.il/search?search=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&city=%D7%97%D7%99%D7%A4%D7%94",
        "https://www.jobinfo.co.il/search?cat=1"
    ]
    jobs = []
    for url in urls:
        driver.get(url)
        wait_for(driver, By.TAG_NAME, "body", 8)
        for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .result-item, .listing"):
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
                         "description": desc, "source": "Jobinfo"})
    print(f"  Jobinfo: {len(jobs)} jobs")
    return jobs


def parse_cps(driver):
    """CPS Jobs"""
    driver.get("https://www.cps.co.il/search_page/")
    wait_for(driver, By.TAG_NAME, "body", 8)
    jobs = []
    for item in safe_finds(driver, By.CSS_SELECTOR, ".job-item, .card, .post, article"):
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
    driver.get("https://www.sqlink.com/%D7%9E%D7%A9%D7%A8%D7%95%D7%AA-%D7%91%D7%94%D7%99%D7%99%D7%98%D7%A7/")
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


def parse_jobmaster(driver):
    """JobMaster"""
    driver.get("https://www.jobmaster.co.il/search/?q=%D7%9E%D7%AA%D7%9B%D7%A0%D7%AA&city=%D7%97%D7%99%D7%A4%D7%94")
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
                     "description": desc, "source": "JobMaster"})
    print(f"  JobMaster: {len(jobs)} jobs")
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


def parse_experis(driver):
    """Experis Israel"""
    driver.get("https://www.experis.co.il")
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
                     "description": desc, "source": "Experis"})
    print(f"  Experis: {len(jobs)} jobs")
    return jobs


def parse_manpower(driver):
    """Manpower"""
    driver.get("https://www.manpower.co.il/search")
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
    """Geektime careers section"""
    driver.get("https://insider.geektime.co.il/careers/")
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
    driver.get("https://www.ethosia.co.il")
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
    driver.get("https://www.yad2.co.il/vehicles/jobs")
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
    driver.get("https://www.hever.co.il")
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


# ============================================================
# SOURCE REGISTRY
# ============================================================
SOURCES = [
    # Blocked from GAS (NetFree on local machine, should work from GitHub)
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
def main():
    driver = get_driver()
    all_jobs = []

    # Only run a subset if argument given (e.g., "scraper.py JobKarov")
    sources_to_run = SOURCES
    if len(sys.argv) > 1:
        sources_to_run = [s for s in SOURCES if s[0].lower() == sys.argv[1].lower()]
        if not sources_to_run:
            print(f"Unknown source: {sys.argv[1]}")
            print(f"Available: {', '.join(s[0] for s in SOURCES)}")
            driver.quit()
            return

    print(f"Running {len(sources_to_run)} sources...")
    for name, parser in sources_to_run:
        try:
            print(f"\n--- {name} ---")
            jobs = parser(driver)
            for j in jobs:
                if not is_tech(j["title"]) and not is_tech(j.get("description", "")):
                    continue
            all_jobs.extend(jobs)
        except WebDriverException as e:
            print(f"  ERROR: {str(e)[:100]}")
        except Exception as e:
            print(f"  ERROR: {str(e)[:100]}")

    driver.quit()

    print(f"\n=== Total: {len(all_jobs)} jobs from {len(sources_to_run)} sources ===")

    # Filter: keep only north + tech
    north_tech = []
    for j in all_jobs:
        text = j["title"] + " " + j.get("description", "") + " " + j.get("location", "") + " " + j.get("company", "")
        if is_north(text) and is_tech(text):
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
        st = [j for j in sjobs if is_north(j["title"] + " " + j.get("description","") + " " + j.get("location","")) and is_tech(j["title"] + " " + j.get("description",""))]
        if st:
            write_rss(build_rss(st), f"{src.lower()}.xml")


if __name__ == "__main__":
    main()
