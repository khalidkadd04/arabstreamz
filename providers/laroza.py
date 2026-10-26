import os
import re
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id, unpack_packer

LAROZA_BASE_URL = os.getenv("LAROZA_URL", "https://llaroza.beer").rstrip("/")


class LarozaProvider(BaseProvider):
    id = "laroza"
    name = "Laroza"
    description = "Séries turques, arabes et nouveautés cinéma (Laroza / لاروزا)"
    icon = "https://llaroza.beer/favicon.ico"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "series",
                "id": "laroza-series",
                "name": "📺 Laroza - Séries & Drames",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "laroza-movies",
                "name": "🎬 Laroza - Films",
                "extra": [{"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "laroza-series-search",
                "name": "🔍 Laroza - Recherche Séries",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            },
            {
                "type": "movie",
                "id": "laroza-movies-search",
                "name": "🔍 Laroza - Recherche Films",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

    def _parse_items(self, html: str, media_type: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        metas = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'video.php?vid=' in href or 'watch.php?vid=' in href:
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
                    thumb = img.get('data-echo') or img.get('data-original-thumbnail') or img.get('src') or ''
                if not thumb or 'placeholder' in thumb:
                    thumb = f"{LAROZA_BASE_URL}/uploads/thumbs/{vid}-1.jpg"

                item_id = encode_item_id("laroza", f"{title}::{href}")
                metas.append({
                    "id": item_id,
                    "type": media_type,
                    "name": title,
                    "poster": thumb,
                    "background": thumb,
                    "genres": ["[Laroza]", "Drame", "Turc"],
                    "description": f"📍 Source : Laroza Video\n\nRegarder {title} en streaming haute définition."
                })

        return metas

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        page_suffix = f"?page={page}" if page > 1 else ""

        if media_type == "movie":
            url = f"{LAROZA_BASE_URL}/category.php?cat=movies{page_suffix}"
        else:
            url = f"{LAROZA_BASE_URL}/newvideos.php{page_suffix}"

        html = await fetch_html(url)
        items = self._parse_items(html, media_type)
        return items[:24]

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        page = (skip // 24) + 1
        url = f"{LAROZA_BASE_URL}/search.php?keywords={quote_plus(query)}&page={page}"
        html = await fetch_html(url)
        items = self._parse_items(html, media_type)
        return items[:24]

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "laroza")
        if "::" not in decoded:
            return None

        title, watch_url = decoded.split("::", 1)
        full_url = watch_url if watch_url.startswith("http") else f"{LAROZA_BASE_URL}/{watch_url.lstrip('/')}"
        html = await fetch_html(full_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "id": item_id,
            "type": media_type,
            "name": title,
            "description": f"📍 Source : Laroza Video\n\nRegarder {title} sur Laroza.",
            "poster": f"{LAROZA_BASE_URL}/laroza-placeholder-ui-20261001.webp",
            "background": f"{LAROZA_BASE_URL}/laroza-placeholder-ui-20261001.webp",
            "genres": ["[Laroza]", "Drame", "Turc"]
        }

        desc_elem = soup.find('div', id='video-description') or soup.find('div', class_='entry-content')
        if desc_elem:
            metadata['description'] = f"📍 Source : Laroza Video\n\n{desc_elem.get_text(strip=True)}"

        img_elem = soup.find('meta', property='og:image')
        if img_elem and img_elem.get('content'):
            metadata['poster'] = img_elem['content']
            metadata['background'] = img_elem['content']

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
        decoded = decode_item_id(item_id, "laroza")
        if "::" not in decoded:
            return []

        title, watch_url = decoded.split("::", 1)
        vid_match = re.search(r'vid=([a-zA-Z0-9]+)', watch_url)
        if not vid_match:
            return []

        vid = vid_match.group(1)
        emb_page_url = f"{LAROZA_BASE_URL}/embed.php?vid={vid}"
        html_emb_page = fetch_html_sync(emb_page_url, headers={'Referer': watch_url})
        if not html_emb_page:
            return []

        soup_emb = BeautifulSoup(html_emb_page, 'html.parser')
        iframes = [i['src'] for i in soup_emb.find_all('iframe', src=True)]
        if not iframes:
            return []

        embed_src = iframes[0]
        html_player = fetch_html_sync(embed_src, headers={'Referer': emb_page_url})
        if not html_player:
            return []

        unpacked = unpack_packer(html_player)
        stream_urls = re.findall(r'file\s*:\s*[\"\'\`]?([^\s\"\'\`\,]+)', unpacked)
        if not stream_urls:
            stream_urls = re.findall(r'(https?://[^\s\"\'<>]+\.m3u8[^\s\"\'<>]*)', html_player)

        streams = []
        for st in stream_urls:
            if '.m3u8' in st:
                streams.append({
                    "name": "Arabstreamz\n[Laroza HLS]",
                    "title": f"📺 {title}\n📍 Source : Laroza | ⚡ HLS HD Direct",
                    "url": st,
                    "behaviorHints": {
                        "notWebReady": False,
                        "proxyHeaders": {
                            "request": {
                                "Referer": embed_src,
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                            }
                        }
                    }
                })
                break

        return streams

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if results:
            return await self.get_streams(results[0]['id'], media_type)
        return []
