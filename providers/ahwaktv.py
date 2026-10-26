import os
import re
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id, unpack_packer

AHWAKTV_BASE_URL = os.getenv("AHWAKTV_URL", "https://yam.ahwaktv.net").rstrip("/")


class AhwakTVProvider(BaseProvider):
    id = "ahwaktv"
    name = "AhwakTV"
    description = "Séries du Ramadan, films et feuilletons arabes (Ahwak TV)"
    icon = "https://yam.ahwaktv.net/favicon.ico"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "series",
                "id": "ahwaktv-series",
                "name": "📺 Ahwak TV - Séries & Ramadan",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "ahwaktv-movies",
                "name": "🎬 Ahwak TV - Films",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "ahwaktv-series-search",
                "name": "🔍 Ahwak TV - Recherche Séries",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "ahwaktv-movies-search",
                "name": "🔍 Ahwak TV - Recherche Films",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

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

                img = a.find('img')
                title = a.get('title') or (img.get('alt') if img else '') or a.get_text(strip=True)
                title = title.replace('\n', ' ').strip()
                if not title or len(title) < 3:
                    continue

                thumb = ''
                if img:
                    thumb = img.get('data-echo') or img.get('data-original') or img.get('src') or ''
                if not thumb or 'echo-lzld.png' in thumb:
                    thumb = f"{AHWAKTV_BASE_URL}/uploads/thumbs/{vid}-1.jpg"

                item_id = encode_item_id("ahwaktv", f"{title}::{href}")
                metas.append({
                    "id": item_id,
                    "type": media_type,
                    "name": title,
                    "poster": thumb,
                    "background": thumb,
                    "genres": ["[AhwakTV]", "Ramadan", "Arabe"],
                    "description": f"📍 Source : Ahwak TV\n\nRegarder {title} en streaming haute définition."
                })

        return metas

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        page_suffix = f"?page={page}" if page > 1 else ""

        if media_type == "movie":
            url = f"{AHWAKTV_BASE_URL}/newvideos.php{page_suffix}"
        else:
            url = f"{AHWAKTV_BASE_URL}/topvideos.php{page_suffix}"

        html = await fetch_html(url)
        items = self._parse_items(html, media_type)
        return items[:24]

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        url = f"{AHWAKTV_BASE_URL}/search.php?keywords={quote_plus(query)}&page={page}"
        html = await fetch_html(url)
        items = self._parse_items(html, media_type)
        return items[:24]

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "ahwaktv")
        if "::" not in decoded:
            return None

        title, watch_url = decoded.split("::", 1)
        full_url = watch_url if watch_url.startswith("http") else f"{AHWAKTV_BASE_URL}/{watch_url.lstrip('/')}"
        html = await fetch_html(full_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "id": item_id,
            "type": media_type,
            "name": title,
            "description": f"📍 Source : Ahwak TV\n\nRegarder {title} sur Ahwak TV.",
            "poster": f"{AHWAKTV_BASE_URL}/templates/ahwak/img/echo-lzld.png",
            "background": f"{AHWAKTV_BASE_URL}/templates/ahwak/img/echo-lzld.png",
            "genres": ["[AhwakTV]", "Ramadan", "Arabe"]
        }

        desc_elem = soup.find('div', id='video-description') or soup.find('div', class_='entry-content')
        if desc_elem:
            metadata['description'] = f"📍 Source : Ahwak TV\n\n{desc_elem.get_text(strip=True)}"

        img_elem = soup.find('meta', property='og:image')
        if img_elem and img_elem.get('content'):
            metadata['poster'] = img_elem['content']
            metadata['background'] = img_elem['content']

        # Si c'est une série, on peut ajouter la vidéo directe pour Stremio
        if media_type == "series":
            metadata['videos'] = [
                {
                    "id": item_id,
                    "title": title,
                    "season": 1,
                    "episode": 1
                }
            ]

        return metadata

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "ahwaktv")
        if "::" not in decoded:
            return []

        title, watch_url = decoded.split("::", 1)
        vid_match = re.search(r'vid=([a-zA-Z0-9]+)', watch_url)
        if not vid_match:
            return []

        vid = vid_match.group(1)
        see_url = f"{AHWAKTV_BASE_URL}/see.php?vid={vid}"
        html_see = fetch_html_sync(see_url, headers={'Referer': watch_url})
        if not html_see:
            return []

        soup_see = BeautifulSoup(html_see, 'html.parser')
        iframes = [i['src'] for i in soup_see.find_all('iframe', src=True)]
        if not iframes:
            return []

        embed_url = iframes[0]
        html_emb = fetch_html_sync(embed_url, headers={'Referer': see_url})
        if not html_emb:
            return []

        unpacked = unpack_packer(html_emb)
        stream_urls = re.findall(r'file\s*:\s*[\"\'\`]?([^\s\"\'\`\,]+)', unpacked)
        if not stream_urls:
            # Fallback regex direct m3u8
            stream_urls = re.findall(r'(https?://[^\s\"\'<>]+\.m3u8[^\s\"\'<>]*)', html_emb)

        streams = []
        for st in stream_urls:
            if '.m3u8' in st:
                streams.append({
                    "name": "Arabstreamz\n[AhwakTV HLS]",
                    "title": f"📺 {title}\n📍 Source : Ahwak TV | ⚡ HLS HD Direct",
                    "url": st
                })
                break

        return streams

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if results:
            return await self.get_streams(results[0]['id'], media_type)
        return []
