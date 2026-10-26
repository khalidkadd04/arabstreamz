import json
import logging
import re
from typing import List, Dict, Optional, Any
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

from .base import BaseProvider
from .utils import fetch_html, fetch_html_sync, encode_item_id, decode_item_id, get_cache, set_cache

logger = logging.getLogger(__name__)

CARTOONY_NET_URL = "https://cartoony.net"
KARTONEY_BASE_URL = "https://kartoney.com"
CARTOONY_AES_KEY = b"7annaba3l_loves_crypto_safe_key!"


def _decrypt_cartoony_data(encrypted_hex: str, iv_hex: str) -> Any:
    """Déchiffre les données AES-CBC renvoyées par l'API cartoony.net"""
    try:
        iv = bytes.fromhex(iv_hex)
        ciphertext = bytes.fromhex(encrypted_hex)
        cipher = Cipher(algorithms.AES(CARTOONY_AES_KEY), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        decrypted = unpadder.update(padded_data) + unpadder.finalize()
        return json.loads(decrypted.decode("utf-8"))
    except Exception as e:
        logger.error(f"Error decrypting cartoony.net data: {e}")
        return None


class CartoonyProvider(BaseProvider):
    id = "cartoony"
    name = "Cartoony"
    description = "Dessins animés cultes, Spacetoon et anime doublés en arabe (Cartoony.net & Kartoney)"
    icon = "https://cartoony.net/assets/img/logo.webp"

    def get_catalogs(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "series",
                "id": "cartoony-series",
                "name": "🧸 Cartoony - Anime & Cartoons",
                "extra": [
                    {"name": "skip", "isRequired": False}
                ]
            },
            {
                "type": "series",
                "id": "cartoony-search",
                "name": "🔍 Cartoony - Recherche",
                "extra": [
                    {"name": "search", "isRequired": True},
                    {"name": "skip", "isRequired": False}
                ]
            }
        ]

    async def _fetch_cartoony_net_shows(self) -> List[Dict[str, Any]]:
        """Récupère les séries complètes depuis l'API chiffrée cartoony.net"""
        cached = get_cache("cartoony_net_shows")
        if cached:
            return cached

        try:
            import httpx
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": f"{CARTOONY_NET_URL}/",
                "Accept": "application/json, text/plain, */*"
            }
            async with httpx.AsyncClient(headers=headers, timeout=12.0) as client:
                r = await client.get(f"{CARTOONY_NET_URL}/api/tvshows")
                if r.status_code == 200:
                    data = r.json()
                    shows = _decrypt_cartoony_data(data.get("encryptedData", ""), data.get("iv", ""))
                    if shows and isinstance(shows, list):
                        set_cache("cartoony_net_shows", shows, ttl=3600)
                        return shows
        except Exception as e:
            logger.error(f"Error fetching shows from cartoony.net: {e}")

        return []

    async def _fetch_legacy_kartoney_items(self) -> List[Dict[str, Any]]:
        """Fallback sur kartoney.com si cartoony.net est indisponible"""
        cached = get_cache("cartoony_legacy_items")
        if cached:
            return cached

        html = await fetch_html(f"{KARTONEY_BASE_URL}/library/")
        if not html:
            html = await fetch_html(f"{KARTONEY_BASE_URL}/")

        soup = BeautifulSoup(html, 'html.parser')
        items = []
        seen = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/cartoon/' in href and href != '/cartoon/':
                slug = href.strip('/').split('/')[-1]
                if slug in seen:
                    continue
                seen.add(slug)

                img = a.find('img')
                title = img.get('alt', '').strip() if img else ''
                if not title:
                    title = a.get_text(strip=True)
                if not title:
                    title = slug.replace('-', ' ').title()

                thumb = img.get('src') or img.get('data-src') or '' if img else ''
                if thumb.startswith('/'):
                    thumb = f"{KARTONEY_BASE_URL}{thumb}"

                item_id = encode_item_id("cartoony", f"legacy::{title}::{href}")
                items.append({
                    "id": item_id,
                    "type": "series",
                    "name": title,
                    "poster": thumb or f"{CARTOONY_NET_URL}/assets/img/default_cover.webp",
                    "background": thumb,
                    "genres": ["[Cartoony]", "Animation", "Anime", "Nostalgie"],
                    "description": f"📍 Source : Cartoony (Kartoney.com)\n\nRegarder {title} مدبلج عربي."
                })

        if items:
            set_cache("cartoony_legacy_items", items, ttl=7200)
        return items

    async def get_catalog_items(self, catalog_id: str, media_type: str, skip: int = 0, genre: Optional[str] = None) -> List[Dict[str, Any]]:
        # 1. Essai avec cartoony.net
        shows = await self._fetch_cartoony_net_shows()
        if shows:
            items = []
            for s in shows:
                show_id = s.get("id")
                title = s.get("title", "")
                desc = s.get("description", "") or s.get("description_technical", "")
                poster_cover = s.get("poster_cover_alt") or s.get("poster_cover") or ""
                poster_url = f"{CARTOONY_NET_URL}/assets/img/posters/{poster_cover}" if poster_cover else f"{CARTOONY_NET_URL}/assets/img/default_cover.webp"
                banner = s.get("poster_banner") or poster_cover or ""
                banner_url = f"{CARTOONY_NET_URL}/assets/img/posters/{banner}" if banner else poster_url

                category = s.get("category", "Animation")
                year = s.get("release_year")
                genres = ["[Cartoony]", category, "Animation", "Anime"]
                if year:
                    genres.append(str(year))

                item_id = encode_item_id("cartoony", f"net::{show_id}::{title}")
                items.append({
                    "id": item_id,
                    "type": "series",
                    "name": title,
                    "poster": poster_url,
                    "background": banner_url,
                    "genres": genres,
                    "description": f"📍 Source : Cartoony (cartoony.net)\n\n{desc.strip()}"
                })
            return items[skip:skip + 30]

        # 2. Fallback kartoney.com
        fallback = await self._fetch_legacy_kartoney_items()
        return fallback[skip:skip + 30]

    async def search(self, query: str, media_type: str, skip: int = 0) -> List[Dict[str, Any]]:
        shows = await self._fetch_cartoony_net_shows()
        q_lower = query.lower().strip()

        if shows:
            matched_shows = [
                s for s in shows
                if q_lower in s.get("title", "").lower()
                or q_lower in s.get("category", "").lower()
                or q_lower in s.get("description", "").lower()
            ]
            items = []
            for s in matched_shows:
                show_id = s.get("id")
                title = s.get("title", "")
                poster_cover = s.get("poster_cover_alt") or s.get("poster_cover") or ""
                poster_url = f"{CARTOONY_NET_URL}/assets/img/posters/{poster_cover}" if poster_cover else f"{CARTOONY_NET_URL}/assets/img/default_cover.webp"
                item_id = encode_item_id("cartoony", f"net::{show_id}::{title}")
                items.append({
                    "id": item_id,
                    "type": "series",
                    "name": title,
                    "poster": poster_url,
                    "genres": ["[Cartoony]", s.get("category", "Animation")],
                    "description": f"📍 Source : Cartoony (cartoony.net)\n\n{s.get('description', '').strip()}"
                })
            return items[skip:skip + 30]

        fallback = await self._fetch_legacy_kartoney_items()
        matched = [it for it in fallback if q_lower in it['name'].lower()]
        return matched[skip:skip + 30]

    async def get_meta(self, item_id: str, media_type: str) -> Optional[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "cartoony")

        # Cas 1 : cartoony.net
        if decoded.startswith("net::"):
            parts = decoded.split("::", 2)
            if len(parts) < 3:
                return None
            _, show_id_str, title = parts
            show_id = int(show_id_str)

            # Trouver les infos du show
            shows = await self._fetch_cartoony_net_shows()
            show = next((s for s in shows if s.get("id") == show_id), None)

            desc = show.get("description", "") if show else ""
            poster_cover = show.get("poster_cover_alt") or show.get("poster_cover") or "" if show else ""
            poster_url = f"{CARTOONY_NET_URL}/assets/img/posters/{poster_cover}" if poster_cover else f"{CARTOONY_NET_URL}/assets/img/default_cover.webp"
            banner = show.get("poster_banner") or poster_cover if show else ""
            banner_url = f"{CARTOONY_NET_URL}/assets/img/posters/{banner}" if banner else poster_url

            # Récupérer les épisodes via l'API cartoony.net
            videos = []
            try:
                import httpx
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Referer": f"{CARTOONY_NET_URL}/",
                    "Accept": "application/json, text/plain, */*"
                }
                async with httpx.AsyncClient(headers=headers, timeout=12.0) as client:
                    r = await client.get(f"{CARTOONY_NET_URL}/api/episodes?id={show_id}")
                    if r.status_code == 200:
                        data = r.json()
                        eps = _decrypt_cartoony_data(data.get("encryptedData", ""), data.get("iv", ""))
                        if eps and isinstance(eps, list):
                            for idx, ep in enumerate(eps):
                                ep_id = ep.get("id")
                                ep_title = ep.get("title") or f"الحلقة {idx + 1}"
                                ep_num = idx + 1
                                ep_season = ep.get("season") or 1
                                thumb = ep.get("thumbnail")
                                thumb_url = f"{CARTOONY_NET_URL}/assets/img/posters/{thumb}" if thumb else poster_url

                                video_id = encode_item_id("cartoony", f"netep::{show_id}::{ep_id}::{title}::{ep_title}")
                                videos.append({
                                    "id": video_id,
                                    "title": ep_title,
                                    "season": ep_season,
                                    "episode": ep_num,
                                    "thumbnail": thumb_url
                                })
            except Exception as e:
                logger.error(f"Error fetching episodes for show {show_id}: {e}")

            return {
                "id": item_id,
                "type": "series",
                "name": title,
                "description": f"📍 Source : Cartoony (cartoony.net)\n\n{desc.strip()}",
                "poster": poster_url,
                "background": banner_url,
                "genres": ["[Cartoony]", show.get("category", "Anime") if show else "Anime"],
                "videos": videos
            }

        # Cas 2 : legacy kartoney.com
        clean_decoded = decoded[8:] if decoded.startswith("legacy::") else decoded
        if "::" not in clean_decoded:
            return None

        title, cartoon_path = clean_decoded.split("::", 1)
        full_url = cartoon_path if cartoon_path.startswith("http") else f"{KARTONEY_BASE_URL}{cartoon_path}"
        html = await fetch_html(full_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        metadata = {
            "id": item_id,
            "type": "series",
            "name": title,
            "description": f"📍 Source : Cartoony (Kartoney.com)\n\nRegarder {title} مدبلج عربي.",
            "poster": f"{CARTOONY_NET_URL}/assets/img/default_cover.webp",
            "background": f"{CARTOONY_NET_URL}/assets/img/default_cover.webp",
            "genres": ["[Cartoony]", "Animation", "Anime", "Nostalgie"]
        }

        desc_elem = soup.find('p', class_='cartoon-desc') or soup.find('div', class_='description')
        if desc_elem:
            clean_desc = desc_elem.get_text(strip=True)
            metadata['description'] = f"📍 Source : Cartoony (Kartoney.com)\n\n{clean_desc}"

        videos = []
        seen_episodes = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            if '/watch/' in href:
                parts = href.strip('/').split('/')
                if len(parts) >= 3:
                    se_part = parts[-1]
                    if '-' in se_part:
                        s_str, e_str = se_part.split('-', 1)
                        season_num = int(s_str) if s_str.isdigit() else 1
                        episode_num = int(e_str) if e_str.isdigit() else 1
                    elif se_part.isdigit():
                        season_num = 1
                        episode_num = int(se_part)
                    else:
                        season_num = 1
                        episode_num = len(videos) + 1
                else:
                    season_num = 1
                    episode_num = len(videos) + 1

                ep_key = (season_num, episode_num)
                if ep_key in seen_episodes:
                    continue
                seen_episodes.add(ep_key)

                ep_title = a.get_text(strip=True) or f"Episode {episode_num}"
                watch_url = href if href.startswith("http") else f"{KARTONEY_BASE_URL}{href}"
                video_id = encode_item_id("cartoony", f"legacyep::{ep_title}::{watch_url}")

                videos.append({
                    "id": video_id,
                    "title": f"Episode {episode_num}",
                    "season": season_num,
                    "episode": episode_num
                })

        videos.sort(key=lambda x: (x['season'], x['episode']))
        metadata['videos'] = videos
        return metadata

    async def get_streams(self, item_id: str, media_type: str) -> List[Dict[str, Any]]:
        decoded = decode_item_id(item_id, "cartoony")

        # 1. Flux cartoony.net HLS direct
        if decoded.startswith("netep::"):
            parts = decoded.split("::", 4)
            if len(parts) >= 5:
                _, show_id_str, ep_id_str, show_title, ep_title = parts
                show_id = int(show_id_str)
                ep_id = int(ep_id_str)

                try:
                    import httpx
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Referer": f"{CARTOONY_NET_URL}/",
                        "Accept": "application/json, text/plain, */*"
                    }
                    async with httpx.AsyncClient(headers=headers, timeout=12.0) as client:
                        r = await client.get(f"{CARTOONY_NET_URL}/api/episode?episodeId={ep_id}&showId={show_id}")
                        if r.status_code == 200:
                            data = r.json()
                            stream_info = _decrypt_cartoony_data(data.get("encryptedData", ""), data.get("iv", ""))
                            if stream_info and stream_info.get("streamUrl"):
                                master_url = stream_info["streamUrl"]
                                base_m3u8 = master_url.rsplit("/", 1)[0]

                                # Qualités disponibles sur Pegasus HLS
                                hints = {
                                    "notWebReady": False,
                                    "proxyHeaders": {
                                        "request": {
                                            "Referer": "https://cartoony.net/",
                                            "Origin": "https://cartoony.net",
                                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                                        }
                                    }
                                }
                                return [
                                    {
                                        "name": "Arabstreamz\n[Cartoony.net 1080p]",
                                        "title": f"🧸 {show_title} - {ep_title}\n📍 Source : Cartoony.net | ⚡ Full HD 1080p HLS",
                                        "url": f"{base_m3u8}/1080p/playlist.m3u8",
                                        "behaviorHints": hints
                                    },
                                    {
                                        "name": "Arabstreamz\n[Cartoony.net 720p]",
                                        "title": f"🧸 {show_title} - {ep_title}\n📍 Source : Cartoony.net | ⚡ HD 720p HLS",
                                        "url": f"{base_m3u8}/720p/playlist.m3u8",
                                        "behaviorHints": hints
                                    },
                                    {
                                        "name": "Arabstreamz\n[Cartoony.net 480p]",
                                        "title": f"🧸 {show_title} - {ep_title}\n📍 Source : Cartoony.net | ⚡ SD 480p HLS",
                                        "url": f"{base_m3u8}/480p/playlist.m3u8",
                                        "behaviorHints": hints
                                    },
                                    {
                                        "name": "Arabstreamz\n[Cartoony.net Auto]",
                                        "title": f"🧸 {show_title} - {ep_title}\n📍 Source : Cartoony.net | ⚡ Master Adaptatif HLS",
                                        "url": master_url,
                                        "behaviorHints": hints
                                    }
                                ]
                except Exception as e:
                    logger.error(f"Error fetching cartoony.net stream: {e}")

        # 2. Flux legacy kartoney.com
        clean_decoded = decoded[10:] if decoded.startswith("legacyep::") else decoded
        if "::" in clean_decoded:
            title, watch_url = clean_decoded.split("::", 1)
            html = fetch_html_sync(watch_url)
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                streams = []
                for s in soup.find_all('source', src=True):
                    src = s['src']
                    if src.endswith(('.mp4', '.m3u8')) or 'archive.org' in src:
                        streams.append({
                            "name": "Arabstreamz\n[Cartoony HD]",
                            "title": f"🧸 {title}\n📍 Source : Cartoony | ⚡ Archive.org HD Direct",
                            "url": src
                        })
                        break

                if not streams:
                    matches = re.findall(r'(https?://[^\s\"\']+(?:archive\.org|videos|cdn)[^\s\"\']*\.(?:mp4|m3u8)[^\s\"\']*)', html)
                    if matches:
                        streams.append({
                            "name": "Arabstreamz\n[Cartoony HD]",
                            "title": f"🧸 {title}\n📍 Source : Cartoony | ⚡ Archive.org HD Direct",
                            "url": matches[0]
                        })
                return streams

        return []

    async def get_streams_by_title(self, title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
        results = await self.search(title, media_type, skip=0)
        if not results:
            return []

        first = results[0]
        meta = await self.get_meta(first['id'], media_type)
        if meta and meta.get('videos'):
            target_ep = episode or 1
            target_season = season or 1
            video = next((v for v in meta['videos'] if v.get('episode') == target_ep and v.get('season') == target_season), None)
            if not video and meta['videos']:
                video = meta['videos'][0]
            if video:
                return await self.get_streams(video['id'], media_type)
        return []
