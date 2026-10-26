import asyncio
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from .base import BaseProvider
from .akwam import AkwamProvider
from .wecima import WeCimaProvider
from .cartoony import CartoonyProvider
from .arabic_toons import ArabicToonsProvider
from .alooytv import AlooyTVProvider
from .ahwaktv import AhwakTVProvider
from .laroza import LarozaProvider

_PROVIDERS: Dict[str, BaseProvider] = {
    "akwam": AkwamProvider(),
    "wecima": WeCimaProvider(),
    "cartoony": CartoonyProvider(),
    "arabictoons": ArabicToonsProvider(),
    "alooytv": AlooyTVProvider(),
    "ahwaktv": AhwakTVProvider(),
    "laroza": LarozaProvider(),
}


def get_all_providers() -> List[BaseProvider]:
    """Retourne la liste de tous les fournisseurs enregistrés."""
    return list(_PROVIDERS.values())


def get_provider(provider_id: str) -> Optional[BaseProvider]:
    """Récupère un fournisseur par son identifiant."""
    return _PROVIDERS.get(provider_id.lower())


def get_provider_for_id(item_id: str) -> Optional[BaseProvider]:
    """Détecte quel fournisseur gère un identifiant donné."""
    clean_id = item_id.replace(".json", "")
    for pid, provider in _PROVIDERS.items():
        if clean_id.startswith(f"{pid}_") or clean_id.startswith(pid):
            return provider
    return None


def get_all_catalogs() -> List[Dict[str, Any]]:
    """Agrège tous les catalogues de tous les fournisseurs pour le manifest Stremio."""
    catalogs = []
    for provider in _PROVIDERS.values():
        catalogs.extend(provider.get_catalogs())
    return catalogs


def get_provider_for_catalog(catalog_id: str) -> Optional[BaseProvider]:
    """Trouve le fournisseur responsable d'un catalogue donné."""
    for provider in _PROVIDERS.values():
        for cat in provider.get_catalogs():
            if cat["id"] == catalog_id:
                return provider
    return None


async def search_all_streams_by_title(title: str, media_type: str, season: Optional[int] = None, episode: Optional[int] = None) -> List[Dict[str, Any]]:
    """Recherche en parallèle les flux sur tous les fournisseurs pour un titre donné."""
    tasks = [
        provider.get_streams_by_title(title, media_type, season, episode)
        for provider in _PROVIDERS.values()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_streams = []
    for res in results:
        if isinstance(res, list):
            all_streams.extend(res)

    return all_streams


# Alias pour compatibilité
resolve_all_streams_by_title = search_all_streams_by_title
