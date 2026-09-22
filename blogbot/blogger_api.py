import requests

from config import Settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
POSTS_URL = "https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts"


def refresh_access_token(settings: Settings) -> str:
    """refresh_token으로 새 access_token을 발급받는다."""
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "refresh_token": settings.google_refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def create_draft_post(
    settings: Settings, access_token: str, title: str, html: str
) -> str:
    """Blogger에 임시저장(draft) 글을 생성하고 편집 URL을 반환한다."""
    url = POSTS_URL.format(blog_id=settings.blogger_blog_id) + "?isDraft=true"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"title": title, "content": html},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return f"https://www.blogger.com/blog/post/edit/{settings.blogger_blog_id}/{data['id']}"
