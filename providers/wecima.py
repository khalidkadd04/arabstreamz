import os
import re
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id, unpack_packer

WECIMA_DOMAINS = [
    os.getenv("WECIMA_URL", "").rstrip("/"),
    "https://wecima.cx",
    "https://wemycima.live"
]
WECIMA_DOMAINS = [d for d in WECIMA_DOMAINS if d]


def _clean_search_title(raw_title: str) -> str:
    """Nettoie le titre arabe pour recherche multi-sources (enlève film, saison, trad...)"""
    t = re.sub(r'^(?:فيلم|مسلسل)\s+', '', raw_title, flags=re.I)
    t = re.sub(r'\s+(?:مترجم|مدبلج|كامل|اون لاين|HD|WEB-DL|BluRay|HDCAM).*$', '', t, flags=re.I)
    t = re.sub(r'\b(?:19|20)\d{2}\b', '', t)
    return t.strip()


class WeCimaProvider(BaseProvider):
    id = "wecima"
    name = "WeCima"
    description = "Films, séries, anime et émissions (wecima.cx & MyCima)"
    icon = "https://wecima.cx/favicon.ico"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "movie",
                "id": "wecima-movies",
                "name": "🍿 WeCima - Films",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "wecima-series",
                "name": "🍿 WeCima - Séries",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "wecima-movies-search",
                "name": "🔍 WeCima - Recherche Films",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "wecima-series-search",
                "name": "🔍 WeCima - Recherche Séries",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

    async def _fetch_wecima(self, path: str) -> str:
        clean_path = path.lstrip("/")
        for domain in WECIMA_DOMAINS:
            url = f"{domain}/{clean_path}"
            html = await fetch_html(url)
            if html and "challenges.cloudflare.com" not in html and len(html) > 500:
                return html
        return ""

    def _fetch_wecima_sync(self, path: str) -> str:
        clean_path = path.lstrip("/")
        for domain in WECIMA_DOMAINS:
            url = f"{domain}/{clean_path}"
            html = fetch_html_sync(url)
            if html and "challenges.cloudflare.com" not in html and len(html) > 500:
                return html
        return ""

    def _parse_items(self, html: str, media_type: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        metas = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'watch.php?vid=' in href:
                vid = href.split('vid=')[-1].split('&')[0]
                if vid in seen:
                    continue
                seen.add(vid)

                title = a.get_text(strip=True)
                if not title or title in ['WEB-DL', 'BluRay', 'HD', 'HDCAM']:
                    parent = a.find_parent('div')
                    if parent:
                        title = parent.get_text(separator=' ', strip=True)

                if not title:
                    title = f"Video {vid}"

                img = a.find('img')
                thumb = img.get('src') or '' if img else ''
                if not thumb and 'vid=' in href:
                    thumb = f"https://wemycima.live/uploads/thumbs/{vid}-1.jpg"

                item_id = encode_item_id("wecima", f"{title}::{href}")
                metas.append({
                    "id": item_id,
                    "type": media_type,
                    "name": title,
                    "poster": thumb or "https://via.placeholder.com/300x450?text=WeCima",
                    "background": thumb,
                    "genres": ["[WeCima]", "Action", "Drama"],
                    "description": f"📍 Source : WeCima (wecima.cx)\n\nRegarder {title} sur WeCima."
                })

        return metas

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        page_suffix = f"?page={page}" if page > 1 else ""
        if media_type == "movie":
            path = f"movies.php{page_suffix}"
        else:
            path = f"all-series.php{page_suffix}"

        html = await self._fetch_wecima(path)
        return self._parse_items(html, media_type)

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        path = f"search.php?keywords={quote_plus(query)}&page={page}"
        html = await self._fetch_wecima(path)
        return self._parse_items(html, media_type)

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "wecima")
        if "::" not in decoded:
            return None

        title, watch_url = decoded.split("::", 1)
        path = watch_url if not watch_url.startswith("http") else watch_url.split("/", 3)[-1]
        html = await self._fetch_wecima(path)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "id": item_id,
            "type": media_type,
            "name": title,
            "description": f"📍 Source : WeCima (wecima.cx)\n\nRegarder {title} sur WeCima.",
            "poster": "https://via.placeholder.com/300x450?text=WeCima",
            "background": "https://via.placeholder.com/1920x1080?text=WeCima",
            "genres": ["[WeCima]", "Action", "Drama"]
        }

        title_elem = soup.find('h1') or soup.find('title')
        if title_elem:
            metadata['name'] = title_elem.text.strip()

        desc_elem = soup.find('div', class_='description') or soup.find('div', class_='entry-content')
        if desc_elem:
            clean_desc = desc_elem.get_text(strip=True)
            metadata['description'] = f"📍 Source : WeCima (wecima.cx)\n\n{clean_desc}"

        return metadata

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "wecima")
        if "::" not in decoded:
            return []

        title, watch_url = decoded.split("::", 1)
        vid_match = re.search(r'vid=([a-zA-Z0-9]+)', watch_url)
        streams = []

        if vid_match:
            vid = vid_match.group(1)
            # 1. Vérifier si un embed lecteur contient un flux direct
            html_play = self._fetch_wecima_sync(f"embed.php?vid={vid}")
            if html_play:
                unpacked = unpack_packer(html_play)
                found = re.findall(r'(https?://[^\s\"\'<>]+\.(?:mp4|m3u8)[^\s\"\'<>]*)', unpacked or html_play)
                for f in found:
                    streams.append({
                        "name": "Arabstreamz\n[WeCima Direct]",
                        "title": f"🍿 {title}\n📍 Source : WeCima | ⚡ Direct Stream",
                        "url": f
                    })
                    break

        # 2. Résolution intelligente multi-sources pour WeCima
        # Si aucun lien direct natif, on recherche sur nos providers rapides vérifiés
        if not streams:
            search_title = _clean_search_title(title)
            if search_title and len(search_title) > 2:
                try:
                    from .akwam import AkwamProvider
                    akwam = AkwamProvider()
                    ak_streams = await akwam.get_streams_by_title(search_title, media_type)
                    if ak_streams:
                        for s in ak_streams:
                            streams.append({
                                "name": s.get("name", "Arabstreamz [Akwam HD]"),
                                "title": f"🍿 {title}\n📍 Source : WeCima via Akwam CDN | ⚡ 100% Jouable",
                                "url": s["url"]
                            })
                except Exception:
                    pass

        return streams

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if results:
            return await self.get_streams(results[0]['id'], media_type)
        return []
