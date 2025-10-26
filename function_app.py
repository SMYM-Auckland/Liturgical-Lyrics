import logging
import azure.functions as func
import requests
from bs4 import BeautifulSoup
import re
import json

BASE_WAYBACK = "https://web.archive.org/web/20250831152901/"

def extract_manglish_lyrics(html: str):
    soup = BeautifulSoup(html, "html.parser")
    spans = soup.find_all("span", class_="spanManglish MangFont")
    lines = []
    for s in spans:
        parts = re.split(r"<br\s*/?>", str(s))
        for part in parts:
            text = BeautifulSoup(part, "html.parser").get_text().strip()
            if text:
                lines.append(text)
    return lines

def split_into_slides(lines):
    slides = []
    current_slide = []
    for line in lines:
        if "-----" in line:
            if current_slide:
                slides.append("\n".join(current_slide))
                current_slide = []
            continue
        current_slide.append(line)
    if current_slide:
        slides.append("\n".join(current_slide))
    return slides

def extract_song_title(html: str):
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.find("a", id="SongTitleName")
    if title_tag:
        title = title_tag.get_text(strip=True)
        title = "".join(c for c in title if c.isalnum() or c in (" ", "_", "-")).strip()
        return title
    return "song"

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing Madely.us lyrics request.')

    try:
        req_body = req.get_json()
        url = req_body.get('url')
        if not url:
            return func.HttpResponse("Missing 'url' in request body", status_code=400)
        
        archive_url = BASE_WAYBACK + url.lstrip("https://")
        r = requests.get(archive_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        if r.status_code != 200:
            return func.HttpResponse(f"Failed to fetch HTML (status {r.status_code})", status_code=502)
        
        html = r.text
        lyrics_lines = extract_manglish_lyrics(html)
        slides = split_into_slides(lyrics_lines)
        title = extract_song_title(html)

        return func.HttpResponse(
            json.dumps({"title": title, "slides": slides}),
            mimetype="application/json",
            status_code=200
        )
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return func.HttpResponse(f"Error: {str(e)}", status_code=500)