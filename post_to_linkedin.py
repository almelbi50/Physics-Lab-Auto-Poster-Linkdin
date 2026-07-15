import os
import sys
import random
import requests
import feedparser

# جلب البيانات السرية من GitHub
ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
AUTHOR_URN = os.environ.get("LINKEDIN_AUTHOR_URN")

# روابط الموقع (تم تحديثها لتكون أكثر دقة)
SITE_URL = "https://phy-lab.com" 
RSS_URL = f"{SITE_URL}/feed"

DB_FILE = "posted_links.txt"

def load_posted_links():
    """تحميل الروابط المنشورة سابقاً لمنع التكرار"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_posted_link(link):
    """حفظ الرابط الجديد في الذاكرة"""
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def post_to_linkedin(title, link, context_text=""):
    """إرسال المنشور إلى LinkedIn"""
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    post_data = {
        "author": AUTHOR_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": f"{context_text}\n\n{title}\n\nتفضلوا بالقراءة عبر الرابط:\n{link}"
                },
                "shareMediaCategory": "ARTICLE",
                "media": [
                    {
                        "status": "READY",
                        "originalUrl": link,
                        "title": {"text": title}
                    }
                ]
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }

    response = requests.post(url, headers=headers, json=post_data)
    if response.status_code == 201:
        print(f"نجاح: تم نشر المقال: {title}")
        save_posted_link(link)
    else:
        print(f"فشل النشر: {response.text}")

def handle_new_posts():
    """البحث عن مقالات جديدة لم تنشر من قبل"""
    posted = load_posted_links()
    feed = feedparser.parse(RSS_URL)
    
    new_posts_found = False
    for entry in reversed(feed.entries):
        if entry.link not in posted:
            print(f"اكتشاف مقال جديد: {entry.title}")
            post_to_linkedin(entry.title, entry.link, "🎯 مقال جديد من معامل الفيزياء:")
            new_posts_found = True
            
    if not new_posts_found:
        print("لا توجد مقالات جديدة في الوقت الحالي.")

def handle_old_posts():
    """جلب مقال قديم عشوائي بطريقة السحب المجمع"""
    posted = load_posted_links()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # 1. محاولة جلب المقالات عبر WordPress API (لحد 100 مقال)
    try:
        wp_url = f"{SITE_URL}/wp-json/wp/v2/posts?per_page=100"
        res = requests.get(wp_url, headers=headers, timeout=10)
        if res.status_code == 200:
            posts = res.json()
            if isinstance(posts, list) and len(posts) > 0:
                unposted = [p for p in posts if p.get('link') not in posted]
                if unposted:
                    selected = random.choice(unposted)
                    title = selected.get('title', {}).get('rendered', 'موضوع فيزيائي')
                    link = selected.get('link')
                    post_to_linkedin(title, link, "📚 من أرشيف معامل الفيزياء (مقال نُعيده للفائدة):")
                    return
    except Exception:
        pass

    # 2. محاولة جلب المقالات عبر Blogger API (إذا كان الموقع مدعوماً ببلوجر)
    try:
        blogger_url = f"{SITE_URL}/feeds/posts/default?max-results=150&alt=json"
        res = requests.get(blogger_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            entries = data.get('feed', {}).get('entry', [])
            if entries:
                unposted = []
                for entry in entries:
                    title = entry.get('title', {}).get('$t', '')
                    links = entry.get('link', [])
                    link = next((l['href'] for l in links if l.get('rel') == 'alternate'), None)
                    if link and link not in posted:
                        unposted.append((title, link))
                
                if unposted:
                    title, link = random.choice(unposted)
                    post_to_linkedin(title, link, "📚 من أرشيف معامل الفيزياء (مقال نُعيده للفائدة):")
                    return
    except Exception:
        pass

    # 3. الحل الأخير (Fallback) باستخدام RSS العادي
    try:
        feed = feedparser.parse(RSS_URL)
        unposted = [e for e in feed.entries if e.link not in posted]
        if unposted:
            selected = random.choice(unposted)
            post_to_linkedin(selected.title, selected.link, "📖 اخترنا لكم من مكتبة معامل الفيزياء:")
            return
    except Exception:
        pass

    print("لم يتم العثور على مقالات قديمة غير منشورة في الأرشيف المتاح.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--old":
        print("تشغيل النظام: نشر موضوع قديم...")
        handle_old_posts()
    else:
        print("تشغيل النظام: فحص ونشر المواضيع الجديدة...")
        handle_new_posts()
