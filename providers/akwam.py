import os
import re
import asyncio
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id

AKWAM_BASE_URL = os.getenv("AKWAM_URL", "https://akwam.ss").rstrip("/")
MAX_WORKERS = int(os.getenv("MAX_WORKERS", 4))

GENRES_LIST = [
    ("أكشن", 18), ("كوميدي", 20), ("دراما", 23), ("رومانسي", 27),
    ("رعب", 22), ("خيال علمي", 24), ("فانتازيا", 43), ("مغامرة", 19),
    ("جريمة", 21), ("تاريخي", 26), ("وثائقي", 28), ("حربي", 25),
    ("رياضي", 32), ("عائلي", 33), ("موسيقى", 31), ("سيرة ذاتية", 29),
    ("مدبلج", 71), ("NETFLIX", 72), ("أطفال", 88), ("قصير", 89), ("رمضان", 87)
]
GENRES_MAP = {name: id_ for name, id_ in GENRES_LIST}
GENRE_NAMES = [g[0] for g in GENRES_LIST]


class AkwamProvider(BaseProvider):
    id = "akwam"
    name = "Akwam"
    description = "Films et séries arabes et internationaux (Akwam / Akoam)"
    icon = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAr_UMfGGxBCd0GKqqW77SMWbYM2nOWPoIwA&s"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "movie",
                "id": "akwam-movies",
                "name": "🎬 Akwam - Films",
                "extra": [
                    {"name": "genre", "options": GENRE_NAMES, "isRequired": False},
                    {"name": "skip", "isRequired": False}
                ]
            },
            {
                "type": "series",
                "id": "akwam-series",
                "name": "🎬 Akwam - Séries",
                "extra": [
                    {"name": "genre", "options": GENRE_NAMES, "isRequired": False},
                    {"name": "skip", "isRequired": False}
                ]
            },
            {
                "type": "movie",
                "id": "akwam-movies-search",
                "name": "🔍 Akwam - Recherche Films",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            },
            {
                "type": "series",
                "id": "akwam-series-search",
                "name": "🔍 Akwam - Recherche Séries",
                "extra": [{"name": "search", "isRequired": True}, {"name": "skip", "isRequired": False}]
            }
        ]

    def _parse_entries(self, html: str, stremio_type: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html, 'html.parser')
        metas = []
        widget_body = soup.find('div', class_='widget-body row flex-wrap')
        if not widget_body:
            return metas

        for entry_box in widget_body.find_all('div', class_='entry-box'):
            title_elem = entry_box.find('h3', class_='entry-title')
            title = title_elem.text.strip() if title_elem else 'Sans titre'

            link_elem = entry_box.find('a', class_='box')
            link = link_elem.get('href', '') if link_elem else ''
            if not link:
                continue

            thumb_elem = entry_box.find('img', class_='img-fluid')
            thumb = thumb_elem.get('data-src') or thumb_elem.get('src') or '' if thumb_elem else ''

            year_elem = entry_box.find('span', class_='badge badge-pill badge-secondary')
            year = year_elem.text.strip() if year_elem else ''

            tags = [t.text.strip() for t in entry_box.find_all('span', class_='badge badge-pill badge-light') if t.text.strip()]
            genres = ["[Akwam]"] + tags

            item_id = encode_item_id("akwam", f"{title}::{link}")
            metas.append({
                "id": item_id,
                "type": stremio_type,
                "name": title,
                "poster": thumb or "https://via.placeholder.com/300x450?text=Akwam",
                "background": thumb,
                "year": year,
                "genres": genres,
                "description": f"📍 Source : Akwam\n\nRegarder {title} en streaming haute qualité."
            })
        return metas

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        section = "movies" if media_type == "movie" else "series"
        category_id = GENRES_MAP.get(genre, 0) if genre else 0
        page = (skip // 30) + 1
        url = f"{AKWAM_BASE_URL}/{section}?category={category_id}&page={page}"
        html = await fetch_html(url)
        return self._parse_entries(html, media_type)

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        section = "movie" if media_type == "movie" else "series"
        page = (skip // 30) + 1
        url = f"{AKWAM_BASE_URL}/search?q={quote_plus(query)}&section={section}&page={page}"
        html = await fetch_html(url)
        return self._parse_entries(html, media_type)

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "akwam")
        if "::" not in decoded:
            return None

        title, akwam_url = decoded.split("::", 1)
        html = await fetch_html(akwam_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "id": item_id,
            "type": media_type,
            "name": title,
            "description": f"📍 Source : Akwam\n\nRegarder {title} en streaming haute qualité.",
            "poster": "https://via.placeholder.com/300x450?text=Akwam",
            "background": "https://via.placeholder.com/1920x1080?text=Akwam",
            "year": "",
            "genres": ["[Akwam]"]
        }

        title_elem = soup.find('h1', class_='entry-title')
        if title_elem:
            metadata['name'] = title_elem.text.strip()

        poster_img = soup.find('div', class_='col-lg-3')
        if poster_img and poster_img.find('img'):
            src = poster_img.find('img').get('src', '')
            if src:
                metadata['poster'] = src.replace('thumb/260x380/', '')
                metadata['background'] = metadata['poster']

        year_match = re.search(r'السنة\s*:\s*(\d{4})', html)
        if year_match:
            metadata['year'] = year_match.group(1)

        rating_elem = soup.find('span', class_='mx-2')
        if rating_elem:
            rating_match = re.search(r'(\d+\.?\d*)\s*/\s*(\d+\.?\d*)', rating_elem.text)
            if rating_match:
                metadata['imdbRating'] = rating_match.group(2)

        story_widget = soup.find('div', class_='widget-body')
        if story_widget:
            text_white = story_widget.find('div', class_='text-white')
            if text_white:
                desc = text_white.get_text(separator=' ', strip=True)
                desc = re.sub(r'مشاهدة و تحميل (فيلم|مسلسل) .+? حيث يدور العمل حول ', '', desc)
                clean_desc = re.sub(r'\s+', ' ', desc).strip()
                metadata['description'] = f"📍 Source : Akwam\n\n{clean_desc}"

        badges = soup.find_all('a', class_='badge badge-pill badge-light')
        metadata['genres'] = ["[Akwam]"] + [b.text.strip() for b in badges if b.text.strip()]

        if media_type == 'series':
            videos = []
            episodes = soup.find_all('div', class_='bg-primary2')
            for ep_div in episodes:
                h2 = ep_div.find('h2', class_='font-size-18')
                if not h2:
                    continue
                a_tag = h2.find('a')
                if not a_tag:
                    continue

                ep_url = a_tag.get('href', '')
                ep_title = a_tag.text.strip()

                ep_match = re.search(r'حلقة\s*(\d+)', ep_title)
                if ep_match:
                    ep_num = int(ep_match.group(1))
                else:
                    num_match = re.search(r'/episode/(\d+)/', ep_url)
                    ep_num = int(num_match.group(1)) if num_match else len(videos) + 1

                video_id = encode_item_id("akwam", f"Episode {ep_num}::{ep_url}")
                videos.append({
                    "id": video_id,
                    "title": f"Episode {ep_num}",
                    "episode": ep_num,
                    "season": 1,
                })

            videos.sort(key=lambda x: x['episode'])
            metadata['videos'] = videos

        return metadata

    def _resolve_single_stream(self, dl_page_url: str, quality_name: str, media_title: str, file_size: str = ""):
        html = fetch_html_sync(dl_page_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        direct_url = None

        dl_btn = soup.find('a', class_='link-download')
        if dl_btn and dl_btn.get('href'):
            direct_url = dl_btn['href']

        if not direct_url:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if 'downet.net' in href or href.endswith(('.mp4', '.mkv')):
                    direct_url = href
                    break

        if direct_url:
            title_text = f"🎬 {media_title}\n📍 Source : Akwam"
            if file_size:
                title_text += f" | 💾 {file_size}"
            return {
                "name": f"Arabstreamz\n[Akwam {quality_name}]",
                "title": title_text,
                "url": direct_url
            }
        return None

    def _get_page_streams(self, page_url: str, media_title: str) -> List[Dict[str, Any]]:
        html = fetch_html_sync(page_url)
        if not html:
            return []

        soup = BeautifulSoup(html, 'html.parser')
        tab_qualities = {}
        for a in soup.select('ul.header-tabs a[href^="#tab-"]'):
            tab_id = a['href'].lstrip('#')
            q_name = a.get_text(strip=True)
            tab_qualities[tab_id] = q_name

        qualities_to_fetch = []
        for tab_id, q_name in tab_qualities.items():
            tab_div = soup.find('div', id=tab_id)
            if tab_div:
                dl_link = tab_div.find('a', class_='link-download')
                if dl_link and dl_link.get('href'):
                    size_elem = dl_link.find('span', class_='font-size-14')
                    size_text = size_elem.get_text(strip=True) if size_elem else ""
                    qualities_to_fetch.append((dl_link['href'], q_name, size_text))

        streams = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._resolve_single_stream, dl_url, q_name, media_title, size): q_name
                for dl_url, q_name, size in qualities_to_fetch
            }
            for future in as_completed(futures):
                stream = future.result()
                if stream:
                    streams.append(stream)

        priority = {"1080p": 4, "720p": 3, "480p": 2, "360p": 1}
        streams.sort(key=lambda s: priority.get(s['name'].split('[Akwam ')[-1].replace(']', '').strip(), 0), reverse=True)
        return streams

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "akwam")
        if "::" not in decoded:
            return []
        media_title, page_url = decoded.split("::", 1)
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_page_streams, page_url, media_title)

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if not results:
            return []

        first = results[0]
        decoded = decode_item_id(first['id'], "akwam")
        if "::" not in decoded:
            return []
        m_title, m_url = decoded.split("::", 1)

        if media_type == "movie":
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._get_page_streams, m_url, m_title)
        elif media_type == "series" and episode:
            meta = await self.get_meta(first['id'], "series")
            if meta and meta.get('videos'):
                target_video = next((v for v in meta['videos'] if v.get('episode') == episode), None)
                if target_video:
                    return await self.get_streams(target_video['id'], "series")
        return []
