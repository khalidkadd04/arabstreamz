import os
import asyncio
from contextlib import asynccontextmanager
from urllib.parse import unquote

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from providers import (
    get_all_providers,
    get_provider,
    get_provider_for_id,
    get_all_catalogs,
    resolve_all_streams_by_title
)
from providers.utils import init_http_clients, close_http_clients, http_client

load_dotenv()

VERSION = "2.1.0"
ADDON_ID = os.getenv("ADDON_ID", "community.arabstreamz")
ADDON_NAME = "Arabstreamz"

# --- Manifest Stremio Arabstreamz ---
manifest_data = {
    "id": ADDON_ID,
    "version": VERSION,
    "name": ADDON_NAME,
    "description": "Le meilleur du streaming arabe : Films, Séries, Dessins animés et Anime depuis Akwam, Cartoony.net, AhwakTV, Laroza, WeCima, Arabic-Toons et AlooyTV",
    "icon": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTAr_UMfGGxBCd0GKqqW77SMWbYM2nOWPoIwA&s",
    "resources": ["catalog", "meta", "stream"],
    "types": ["movie", "series"],
    "idPrefixes": ["arabstreamz", "akwam", "wecima", "cartoony", "arabictoons", "alooytv", "ahwaktv", "laroza", "tt"],
    "catalogs": get_all_catalogs(),
    "behaviorHints": {
        "configurable": True,
        "configurationRequired": False
    }
}


# --- Lifecycle FastAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_clients()
    yield
    await close_http_clients()


app = FastAPI(title=ADDON_NAME, version=VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")
if os.path.exists("templates"):
    app.mount("/static", StaticFiles(directory="templates"), name="static")


# --- Routes Accueil & Configuration ---
@app.get("/")
async def root():
    return RedirectResponse(url="/configure")


@app.get("/configure")
@app.get("/{config}/configure")
async def configure(request: Request):
    providers_info = [
        {"id": p.id, "name": p.name, "description": p.description, "icon": p.icon}
        for p in get_all_providers()
    ]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": VERSION,
            "addonName": ADDON_NAME,
            "providers": providers_info
        }
    )


@app.get("/manifest.json")
@app.get("/{config}/manifest.json")
async def get_manifest():
    manifest_copy = manifest_data.copy()
    manifest_copy["catalogs"] = get_all_catalogs()
    return JSONResponse(content=manifest_copy)


# --- Helper Paramètres Catalogue ---
def parse_catalog_extras(extra_str: str):
    extras = {}
    if not extra_str:
        return extras
    clean_extra = extra_str.replace(".json", "")
    for pair in clean_extra.split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            extras[k] = unquote(v)
    return extras


# --- Routes Catalog (Onglet Découvrir & Accueil Stremio) ---
@app.get("/catalog/{catalog_type}/{catalog_id}.json")
@app.get("/{config}/catalog/{catalog_type}/{catalog_id}.json")
@app.get("/catalog/{catalog_type}/{catalog_id}/{extra_path:path}")
@app.get("/{config}/catalog/{catalog_type}/{catalog_id}/{extra_path:path}")
async def get_catalog(
    catalog_type: str,
    catalog_id: str,
    config: str = None,
    extra_path: str = "",
    skip: int = 0,
    genre: str = None,
    search: str = None
):
    extras = parse_catalog_extras(extra_path)
    final_skip = int(extras.get("skip", skip or 0))
    final_genre = extras.get("genre", genre)
    final_search = extras.get("search", search)

    # Identifier le bon fournisseur d'après le catalog_id (ex: akwam-movies, cartoony-series, etc.)
    target_provider = None
    for provider in get_all_providers():
        if catalog_id.startswith(provider.id):
            target_provider = provider
            break

    if not target_provider:
        target_provider = get_provider("akwam")

    # Cas 1 : Recherche
    if "search" in catalog_id or final_search:
        search_query = final_search or ""
        if not search_query and "search=" in extra_path:
            search_query = extra_path.split("search=")[-1].replace(".json", "")
        search_query = unquote(search_query)

        if search_query:
            metas = await target_provider.search(search_query, catalog_type, skip=final_skip)
            return JSONResponse(content={"metas": metas})
        return JSONResponse(content={"metas": []})

    # Cas 2 : Catalogue standard
    metas = await target_provider.get_catalog_items(catalog_id, catalog_type, skip=final_skip, genre=final_genre)
    return JSONResponse(content={"metas": metas})


# --- Routes Meta (Détails du Film / Série) ---
@app.get("/meta/{meta_type}/{meta_id}.json")
@app.get("/{config}/meta/{meta_type}/{meta_id}.json")
async def get_meta(meta_type: str, meta_id: str, config: str = None):
    provider = get_provider_for_id(meta_id)
    if provider:
        meta = await provider.get_meta(meta_id, meta_type)
        if meta:
            return JSONResponse(content={"meta": meta})

    return JSONResponse(content={
        "meta": {
            "id": meta_id,
            "type": meta_type,
            "name": "Titre inconnu",
            "description": "Contenu multimédia arabe - Arabstreamz",
            "poster": "https://via.placeholder.com/300x450?text=Arabstreamz"
        }
    })


# --- Résolution IMDb via Cinemeta ---
async def resolve_imdb_streams(imdb_id: str, stream_type: str):
    """Interroge Cinemeta pour récupérer le titre puis lance la recherche multi-fournisseurs."""
    try:
        parts = imdb_id.split(":")
        base_imdb_id = parts[0]
        season_num = int(parts[1]) if len(parts) > 1 else None
        episode_num = int(parts[2]) if len(parts) > 2 else None

        init_http_clients()
        cinemeta_url = f"https://v3-cinemeta.strem.io/meta/{stream_type}/{base_imdb_id}.json"
        res = await http_client.get(cinemeta_url)
        if res.status_code == 200:
            meta = res.json().get('meta', {})
            title = meta.get('name')
            if title:
                return await resolve_all_streams_by_title(title, stream_type, season=season_num, episode=episode_num)
    except Exception as e:
        print(f"⚠️ Erreur Cinemeta IMDb {imdb_id}: {e}")

    return []


# --- Routes Stream (Lecture Vidéo) ---
@app.get("/stream/{stream_type}/{stream_id}.json")
@app.get("/{config}/stream/{stream_type}/{stream_id}.json")
@app.get("/stream/{stream_type}/{stream_id}")
@app.get("/{config}/stream/{stream_type}/{stream_id}")
async def get_stream(stream_type: str, stream_id: str, config: str = None):
    clean_id = stream_id.replace(".json", "")

    # Cas 1 : Identifiant IMDb (ex: tt0111161 ou tt0903747:1:1) -> Recherche multi-sources en parallèle
    if clean_id.startswith("tt"):
        streams = await resolve_imdb_streams(clean_id, stream_type)
        return JSONResponse(content={"streams": streams})

    # Cas 2 : Identifiant spécifique d'un fournisseur
    provider = get_provider_for_id(clean_id)
    if provider:
        streams = await provider.get_streams(clean_id, stream_type)
        return JSONResponse(content={"streams": streams})

    return JSONResponse(content={"streams": []})


# --- Point d'entrée Local ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)