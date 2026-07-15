import os
import sys
import random
import requests
import feedparser

# جلب البيانات السرية من GitHub
ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
AUTHOR_URN = os.environ.get("LINKEDIN_AUTHOR_URN")

# رابط الـ RSS لموقعك (تأكد من تعديله لرابط موقعك الفعلي)
RSS_URL = "https://www.phy-lab.com/feed" 

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
                    "text": f"{context_text}\n\n{title}\n\nتفضلوا بالقراءة عبر الرابط:"
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
    
    # الفحص من الأقدم للأحدث في التغذية الحالية
    new_posts_found = False
    for entry in reversed(feed.entries):
        if entry.link not in posted:
            print(f"اكتشاف مقال جديد: {entry.title}")
            post_to_linkedin(entry.title, entry.link, "🎯 مقال جديد من معامل الفيزياء:")
            new_posts_found = True
            
    if not new_posts_found:
        print("لا توجد مقالات جديدة في الوقت الحالي.")

def handle_old_posts():
    """جلب مقال قديم عشوائي لم يتم نشره مسبقاً"""
    posted = load_posted_links()
    wp_api_url = RSS_URL.replace("/feed", "/wp-json/wp/v2/posts")
    
    try:
        # محاولة جلب المقالات عبر WordPress API للحصول على أرشيف أكبر
        # جلب أول صفحة لمعرفة عدد الصفحات الكلي
        res = requests.get(f"{wp_api_url}?per_page=1")
        if res.status_code == 200:
            total_pages = int(res.headers.get('X-WP-TotalPages', 1))
            # محاولة العثور على مقال غير منشور باختيار صفحات عشوائية
            for _ in range(10): # محاولة 10 مرات كحد أقصى
                random_page = random.randint(1, total_pages)
                page_res = requests.get(f"{wp_api_url}?per_page=10&page={random_page}")
                if page_res.status_code == 200:
                    posts = page_res.json()
                    unposted = [p for p in posts if p['link'] not in posted]
                    if unposted:
                        selected = random.choice(unposted)
                        title = selected['title']['rendered']
                        link = selected['link']
                        post_to_linkedin(title, link, "📚 من أرشيف معامل الفيزياء (مقال قديم نُعيده للفائدة):")
                        return
            print("لم نجد مقال قديم غير منشور في الصفحات العشوائية التي تم فحصها.")
            return
    except Exception as e:
        print(f"تعذر استخدام WordPress API، سيتم الاعتماد على الـ RSS: {e}")

    # حل بديل (Fallback) في حال لم يكن الموقع ووردبريس أو فشل الـ API
    feed = feedparser.parse(RSS_URL)
    unposted = [e for e in feed.entries if e.link not in posted]
    if unposted:
        selected = random.choice(unposted)
        post_to_linkedin(selected.title, selected.link, "📖 اخترنا لكم من مكتبة معامل الفيزياء:")
    else:
        print("لم يتم العثور على مقالات غير منشورة في التغذية الحالية.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--old":
        print("تشغيل النظام: نشر موضوع قديم...")
        handle_old_posts()
    else:
        print("تشغيل النظام: فحص ونشر المواضيع الجديدة...")
        handle_new_posts()
