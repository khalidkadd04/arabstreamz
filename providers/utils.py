import base64
import os
import hashlib
import threading
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.9,en;q=0.8,fr;q=0.7",
}

CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", 3600))
_cache_lock = threading.Lock()
_cache: Dict[str, Any] = {}
_cache_expiry: Dict[str, datetime] = {}

http_client: Optional[httpx.AsyncClient] = None
http_client_sync: Optional[httpx.Client] = None


def init_http_clients():
    global http_client, http_client_sync
    if http_client is None:
        http_client = httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=25.0, follow_redirects=True, verify=False)
    if http_client_sync is None:
        http_client_sync = httpx.Client(headers=DEFAULT_HEADERS, timeout=25.0, follow_redirects=True, verify=False)


async def close_http_clients():
    global http_client, http_client_sync
    if http_client:
        await http_client.aclose()
        http_client = None
    if http_client_sync:
        http_client_sync.close()
        http_client_sync = None


def get_cache(key: str) -> Optional[Any]:
    with _cache_lock:
        if key in _cache and key in _cache_expiry:
            if datetime.now() < _cache_expiry[key]:
                return _cache[key]
            del _cache[key]
            del _cache_expiry[key]
    return None


def set_cache(key: str, value: Any, ttl: int = CACHE_TTL):
    with _cache_lock:
        _cache[key] = value
        _cache_expiry[key] = datetime.now() + timedelta(seconds=ttl)


def make_cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


async def fetch_html(url: str, headers: Optional[dict] = None) -> str:
    """Effectue une requête GET asynchrone avec cache."""
    cache_key = make_cache_key(url)
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    init_http_clients()
    try:
        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)
        res = await http_client.get(url, headers=req_headers)
        if res.status_code == 200:
            text = res.text
            set_cache(cache_key, text)
            return text
    except Exception as e:
        print(f"⚠️ Erreur fetch_html ({url}): {e}")
    return ""


def fetch_html_sync(url: str, headers: Optional[dict] = None) -> str:
    """Effectue une requête GET synchrone avec cache."""
    cache_key = make_cache_key(url)
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    init_http_clients()
    try:
        req_headers = DEFAULT_HEADERS.copy()
        if headers:
            req_headers.update(headers)
        res = http_client_sync.get(url, headers=req_headers)
        if res.status_code == 200:
            text = res.text
            set_cache(cache_key, text)
            return text
    except Exception as e:
        print(f"⚠️ Erreur fetch_html_sync ({url}): {e}")
    return ""


def encode_item_id(provider_prefix: str, data: str) -> str:
    """Encode une chaîne d'identifiant en base64 avec préfixe du provider."""
    b64 = base64.urlsafe_b64encode(data.encode('utf-8')).decode('utf-8').rstrip('=')
    return f"{provider_prefix}_{b64}"


def decode_item_id(raw_id: str, provider_prefix: str) -> str:
    """Décode un identifiant base64."""
    cleaned = raw_id.replace(".json", "")
    prefix = f"{provider_prefix}_"
    if cleaned.startswith(prefix):
        cleaned = cleaned[len(prefix):]
    elif cleaned.startswith(provider_prefix):
        cleaned = cleaned[len(provider_prefix):]

    padding_needed = len(cleaned) % 4
    if padding_needed:
        cleaned += "=" * (4 - padding_needed)

    try:
        return base64.urlsafe_b64decode(cleaned.encode('utf-8')).decode('utf-8')
    except Exception:
        return raw_id


def unpack_packer(script_text: str) -> str:
    """Décompresse le JavaScript obfusqué avec Dean Edwards Packer (eval(function(p,a,c,k,e,d)...))"""
    m = re.search(r"eval\(function\(p,a,c,k,e,d\).+?return p\}\('(.*?)',(\d+),(\d+),'(.*?)'\.split\('\|'\)", script_text, re.DOTALL)
    if not m:
        return ""
    p, a, c, k = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4).split('|')
    def base_n(num: int, base: int) -> str:
        digits = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if num == 0:
            return '0'
        res = []
        while num > 0:
            res.append(digits[num % base])
            num //= base
        return ''.join(reversed(res))
    for idx in range(c - 1, -1, -1):
        key = base_n(idx, a)
        val = k[idx] if idx < len(k) and k[idx] else key
        p = re.sub(r'\b' + key + r'\b', val, p)
    return p
