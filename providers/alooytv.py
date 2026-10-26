import os
import re
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id

ALOOYTV_BASE_URL = os.getenv("ALOOYTV_URL", "https://alooytv.tv").rstrip("/")


class AlooyTVProvider(BaseProvider):
    id = "alooytv"
    name = "AlooyTV"
    description = "Séries du Golfe, arabes, koweïtiennes, saoudiennes et turques (AlooyTV)"
    icon = "https://alooytv.tv/favicon.ico"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "series",
                "id": "alooytv-series",
                "name": "📺 AlooyTV - Séries du Golfe & Arabes",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "alooytv-search",
                "name": "🔍 AlooyTV - Recherche",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

    def _parse_series(self, html: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        metas = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(p in href for p in ['/contact', '/privacy', '/dmca', '/terms', '/link', '/go', '/safe', '#']):
                continue

            text = a.get_text(separator=' ', strip=True)
            if not text or len(text) < 4:
                continue

            slug = href.strip('/').split('/')[-1]
            if not slug or slug in seen:
                continue
            seen.add(slug)

            full_url = href if href.startswith('http') else f"{ALOOYTV_BASE_URL}/{slug}/"
            item_id = encode_item_id("alooytv", f"{text}::{full_url}")

            metas.append({
                "id": item_id,
                "type": "series",
                "name": text.split(' - ')[0].strip(),
                "poster": "https://via.placeholder.com/300x450?text=AlooyTV",
                "background": "https://via.placeholder.com/1920x1080?text=AlooyTV",
                "genres": ["[AlooyTV]", "Drama", "Khaleeji", "Ramadan"],
                "description": f"📍 Source : AlooyTV\n\nRegarder {text} sur AlooyTV."
            })

        return metas

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        html = await fetch_html(f"{ALOOYTV_BASE_URL}/")
        items = self._parse_series(html)
        return items[skip:skip + 30]

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        html = await fetch_html(f"{ALOOYTV_BASE_URL}/")
        items = self._parse_series(html)
        q_lower = query.lower().strip()
        matched = [it for it in items if q_lower in it['name'].lower()]
        return matched[skip:skip + 30]

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "alooytv")
        if "::" not in decoded:
            return None

        title, series_url = decoded.split("::", 1)
        html = await fetch_html(series_url)
        if not html:
            html = await fetch_html(f"{ALOOYTV_BASE_URL}/")

        metadata = {
            "id": item_id,
            "type": "series",
            "name": title,
            "description": f"📍 Source : AlooyTV\n\nRegarder {title} sur AlooyTV.",
            "poster": "https://via.placeholder.com/300x450?text=AlooyTV",
            "background": "https://via.placeholder.com/1920x1080?text=AlooyTV",
            "genres": ["[AlooyTV]", "Drama", "Khaleeji", "Ramadan"]
        }

        videos = []
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.find_all('a', href=True):
            t = a.get_text(strip=True)
            if 'حلقة' in t or 'مشاهدة' in t:
                m = re.search(r'(\d+)', t)
                ep_num = int(m.group(1)) if m else len(videos) + 1
                vid_id = encode_item_id("alooytv", f"{title} Ep {ep_num}::{a['href']}")
                videos.append({
                    "id": vid_id,
                    "title": f"Episode {ep_num}",
                    "episode": ep_num,
                    "season": 1
                })

        if not videos:
            videos.append({
                "id": encode_item_id("alooytv", f"{title} Ep 1::{series_url}"),
                "title": "Episode 1",
                "episode": 1,
                "season": 1
            })

        metadata['videos'] = videos
        return metadata

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "alooytv")
        if "::" not in decoded:
            return []

        title, ep_url = decoded.split("::", 1)
        html = fetch_html_sync(ep_url)
        streams = []

        if html:
            matches = re.findall(r'(https?://[^\s\"\']+\.(?:m3u8|mp4)[^\s\"\']*)', html)
            for m in matches[:2]:
                streams.append({
                    "name": "Arabstreamz\n[AlooyTV HD]",
                    "title": f"📺 {title}\n📍 Source : AlooyTV | ⚡ Stream Direct",
                    "url": m
                })

        return streams

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if results:
            return await self.get_streams(results[0]['id'], media_type)
        return []
