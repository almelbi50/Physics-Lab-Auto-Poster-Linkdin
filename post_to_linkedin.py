import os
import sys
import random
import requests
import feedparser

# جلب البيانات من GitHub Secrets
ACCESS_TOKEN = os.environ.get("LINKEDIN_ACCESS_TOKEN")
# تأكد أن هذا المتغير في GitHub هو: urn:li:person:68172092
AUTHOR_URN = os.environ.get("LINKEDIN_AUTHOR_URN")

SITE_URL = "https://phy-lab.com" 
RSS_URL = f"{SITE_URL}/feed"
DB_FILE = "posted_links.txt"

def load_posted_links():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_posted_link(link):
    with open(DB_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def post_to_linkedin(title, link, context_text=""):
    url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # النشر كفرد (شخصي) وهو المسار الأضمن والأسرع
    post_data = {
        "author": AUTHOR_URN, 
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": f"{context_text}\n\n{title}\n\nللقراءة عبر الرابط:\n{link}"
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
        print(f"نجاح: تم النشر بنجاح على حسابك الشخصي!")
        save_posted_link(link)
    else:
        print(f"فشل النشر، نص الخطأ: {response.text}")

def handle_new_posts():
    posted = load_posted_links()
    feed = feedparser.parse(RSS_URL)
    for entry in reversed(feed.entries):
        if entry.link not in posted:
            post_to_linkedin(entry.title, entry.link, "🎯 جديد معامل الفيزياء:")
            return 

def handle_old_posts():
    posted = load_posted_links()
    feed = feedparser.parse(RSS_URL)
    unposted = [e for e in feed.entries if e.link not in posted]
    if unposted:
        selected = random.choice(unposted)
        post_to_linkedin(selected.title, selected.link, "📚 من الأرشيف الفيزيائي:")
    else:
        print("لا يوجد مقالات جديدة للنشر.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--old":
        handle_old_posts()
    else:
        handle_new_posts()
