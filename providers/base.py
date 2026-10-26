from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class BaseProvider(ABC):
    """Classe de base pour tous les fournisseurs de contenu arabes."""

    id: str = "base"
    name: str = "Base"
    description: str = ""
    icon: str = ""
    enabled: bool = True

    @abstractmethod
    def get_catalogs(self) -> List[Dict[str, Any]]:
        """Retourne la déclaration des catalogues pour le manifest Stremio."""
        pass

    @abstractmethod
    async def get_catalog_items(
        self,
        catalog_id: str,
        media_type: str,
        skip: int = 0,
        genre: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retourne la liste des éléments pour un catalogue donné."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        media_type: str,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """Recherche des films ou séries."""
        pass

    @abstractmethod
    async def get_meta(
        self,
        item_id: str,
        media_type: str
    ) -> Optional[Dict[str, Any]]:
        """Récupère les métadonnées d'un élément (synopsis, note, épisodes)."""
        pass

    @abstractmethod
    async def get_streams(
        self,
        item_id: str,
        media_type: str
    ) -> List[Dict[str, Any]]:
        """Extrait les flux vidéo directs pour un élément de ce fournisseur."""
        pass

    async def get_streams_by_title(
        self,
        title: str,
        media_type: str,
        season: Optional[int] = None,
        episode: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Permet de résoudre un flux à partir d'un titre (pour les résolutions IMDb)."""
        return []
