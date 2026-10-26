import re
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id

ARABIC_TOONS_BASE_URL = "https://www.arabic-toons.com"


class ArabicToonsProvider(BaseProvider):
    id = "arabictoons"
    name = "Arabic-Toons"
    description = "Dessins animés, séries Spacetoon et films d'animation doublés en arabe"
    icon = "https://www.arabic-toons.com/favicon.ico"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "series",
                "id": "arabictoons-series",
                "name": "🎨 Arabic-Toons - Séries Animées",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "arabictoons-movies",
                "name": "🎨 Arabic-Toons - Films Animés",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "arabictoons-series-search",
                "name": "🔍 Arabic-Toons - Recherche",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

    def _parse_catalog_html(self, html: str, media_type: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            is_valid = (media_type == "movie" and "-movies-streaming.html" in href) or \
                       (media_type == "series" and "-anime-streaming.html" in href)

            if is_valid:
                clean_href = href.split('?')[0]
                if clean_href in seen:
                    continue
                seen.add(clean_href)

                title = a.get_text(strip=True)
                if not title or title in ['مشاهدة', 'المزيد']:
                    continue

                full_url = clean_href if clean_href.startswith('http') else f"{ARABIC_TOONS_BASE_URL}/{clean_href}"

                img = a.find('img')
                thumb = img.get('src') or '' if img else ''
                if thumb and not thumb.startswith('http'):
                    thumb = f"{ARABIC_TOONS_BASE_URL}/{thumb}"

                item_id = encode_item_id("arabictoons", f"{title}::{full_url}")
                items.append({
                    "id": item_id,
                    "type": media_type,
                    "name": title,
                    "poster": thumb or "https://via.placeholder.com/300x450?text=ArabicToons",
                    "background": thumb,
                    "genres": ["[Arabic-Toons]", "Animation", "Anime", "Kids"],
                    "description": f"📍 Source : Arabic-Toons\n\nRegarder {title} مدبلج عربي."
                })

        return items

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        page = (skip // 20) + 1
        page_suffix = f"?next={page}" if page > 1 else ""
        if media_type == "movie":
            url = f"{ARABIC_TOONS_BASE_URL}/movies.php{page_suffix}"
        else:
            url = f"{ARABIC_TOONS_BASE_URL}/cartoon.php{page_suffix}"

        html = await fetch_html(url)
        return self._parse_catalog_html(html, media_type)

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        matched = []
        q_lower = query.lower().strip()

        for page in range(1, 4):
            page_suffix = f"?next={page}" if page > 1 else ""
            url = f"{ARABIC_TOONS_BASE_URL}/cartoon.php{page_suffix}"
            html = await fetch_html(url)
            items = self._parse_catalog_html(html, "series")
            for it in items:
                if q_lower in it['name'].lower():
                    matched.append(it)

        return matched[skip:skip + 30]

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "arabictoons")
        if "::" not in decoded:
            return None

        title, page_url = decoded.split("::", 1)
        html = await fetch_html(page_url)
        if not html:
            return None

        metadata = {
            "id": item_id,
            "type": media_type,
            "name": title,
            "description": f"📍 Source : Arabic-Toons\n\nRegarder {title} مدبلج عربي.",
            "poster": "https://via.placeholder.com/300x450?text=ArabicToons",
            "background": "https://via.placeholder.com/1920x1080?text=ArabicToons",
            "genres": ["[Arabic-Toons]", "Animation", "Anime", "Kids"]
        }

        if media_type == "series":
            soup = BeautifulSoup(html, 'html.parser')
            videos = []
            seen_eps = set()

            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.endswith('.html') or '#sets' in href:
                    clean_href = href.split('#')[0]
                    if '-' in clean_href and clean_href not in seen_eps:
                        link_text = a.get_text(strip=True)
                        m = re.search(r'الحلقة\s*(\d+)', link_text)
                        if m:
                            ep_num = int(m.group(1))
                            seen_eps.add(clean_href)
                            full_ep_url = clean_href if clean_href.startswith('http') else f"{ARABIC_TOONS_BASE_URL}/{clean_href}"
                            v_id = encode_item_id("arabictoons", f"Episode {ep_num}::{full_ep_url}")
                            videos.append({
                                "id": v_id,
                                "title": f"Episode {ep_num}",
                                "season": 1,
                                "episode": ep_num
                            })

            videos.sort(key=lambda x: x['episode'])
            metadata['videos'] = videos

        return metadata

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "arabictoons")
        if "::" not in decoded:
            return []

        title, watch_url = decoded.split("::", 1)
        html = fetch_html_sync(watch_url)
        if not html:
            return []

        matches = re.findall(r'(https?://[^\s\"\']+(?:foupix|video|stream)[^\s\"\']*\.(?:mp4|m3u8)[^\s\"\']*)', html)
        streams = []
        for url in matches[:2]:
            streams.append({
                "name": "Arabstreamz\n[Arabic-Toons HD]",
                "title": f"🎨 {title}\n📍 Source : Arabic-Toons | ⚡ Direct Stream",
                "url": url
            })

        return streams

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if not results:
            return []

        first = results[0]
        if media_type == "movie":
            return await self.get_streams(first['id'], "movie")
        elif media_type == "series" and episode:
            meta = await self.get_meta(first['id'], "series")
            if meta and meta.get('videos'):
                target_video = next((v for v in meta['videos'] if v.get('episode') == episode), None)
                if target_video:
                    return await self.get_streams(target_video['id'], "series")
        return []
