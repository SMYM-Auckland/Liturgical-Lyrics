import azure.functions as func
from azure.functions.decorators import FunctionApp
import json
import re
from bs4 import BeautifulSoup
import requests

# ✅ Define the FunctionApp properly for Azure
app = FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

WAYBACK_BASE = "https://web.archive.org/web/20250831152901"

# 🔹 Helper: fetch HTML via Wayback Machine
def fetch_html_from_wayback(url: str) -> str:
    archived_url = f"{WAYBACK_BASE}/{url}"
    print(f"Fetching archived page: {archived_url}")
    r = requests.get(archived_url, timeout=30)
    r.raise_for_status()
    return r.text


# 🔹 Helper: extract the lyrics and title
def extract_manglish_lyrics_and_title(html: str):
    soup = BeautifulSoup(html, "html.parser")

    # Find the song title
    title_tag = soup.find("a", id="SongTitleName")
    title = title_tag.get_text(strip=True) if title_tag else "Untitled"

    # Extract Manglish lyrics
    spans = soup.find_all("span", class_="spanManglish MangFont")
    if not spans:
        raise ValueError("No lyrics found (class='spanManglish MangFont')")

    lines = []
    for s in spans:
        parts = re.split(r"<br\s*/?>", str(s))
        for part in parts:
            text = BeautifulSoup(part, "html.parser").get_text().strip()
            if text:
                lines.append(text)

    # Split lyrics into slides using "-----"
    slides = []
    current = []
    for line in lines:
        if "-----" in line:
            if current:
                slides.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        slides.append("\n".join(current))

    return title, slides


# 🔹 Main Azure Function Endpoint
@app.function_name(name="create_pptx_from_lyrics")
@app.route(route="create_pptx_from_lyrics", methods=["POST"])
def create_pptx_from_lyrics(req: func.HttpRequest) -> func.HttpResponse:
    """
    POST body example:
    {
        "url": "https://madely.us/lyrics/nanniyode-njan-sthuthi-paadidum/"
    }
    """
    try:
        body = req.get_json()
        url = body.get("url")
        if not url:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'url' in request body"}),
                status_code=400,
                mimetype="application/json"
            )

        html = fetch_html_from_wayback(url)
        title, slides = extract_manglish_lyrics_and_title(html)

        result = {
            "title": title,
            "slide_count": len(slides),
            "slides": slides
        }

        return func.HttpResponse(
            json.dumps(result, ensure_ascii=False, indent=2),
            mimetype="application/json",
            status_code=200
        )

    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )
