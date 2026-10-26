# ⚡ Arabstreamz - Stremio Addon

**Arabstreamz** est l'addon Stremio ultime réunissant les plus grandes plateformes de streaming arabes avec des flux 100% jouables en direct : **Akwam (Akoam)**, **Cartoony.net**, **Ahwak TV**, **Laroza Video**, **WeCima**, **Arabic-Toons** et **AlooyTV**.

Dans l'onglet **Découvrir** de Stremio, chaque catalogue indique clairement sa source d'origine pour vous repérer en un coup d'œil.

---

## 🌟 Sources & Catalogues dans Stremio

Dans Stremio > Onglet **Découvrir (Discover)** :

| Source | Type | Nom du Catalogue | Description |
| :--- | :--- | :--- | :--- |
| **Akwam** | Films | `🎬 Akwam - Films` | Films arabes et internationaux avec filtres par genres (CDN MP4 1080p/720p/480p) |
| **Akwam** | Séries | `🎬 Akwam - Séries` | Séries avec épisodes triés et multi-qualités |
| **Cartoony (cartoony.net)** | Séries | `🧸 Cartoony - Anime & Cartoons` | 330+ Anime & dessins animés cultes en HLS 1080p/720p direct |
| **Ahwak TV** | Séries | `📺 Ahwak TV - Séries & Ramadan` | Séries du Ramadan 2026/2025 et feuilletons arabes (HLS Direct) |
| **Ahwak TV** | Films | `🎬 Ahwak TV - Films` | Nouveautés cinéma arabe |
| **Laroza Video** | Séries | `📺 Laroza - Séries & Drames` | Séries turques doublées, séries arabes et drames (HLS Direct) |
| **Laroza Video** | Films | `🎬 Laroza - Films` | Longs-métrages et sorties récentes |
| **WeCima (wecima.cx)** | Films | `🍿 WeCima - Films` | Dernières sorties et films populaires (wecima.cx & miroirs) |
| **WeCima (wecima.cx)** | Séries | `🍿 WeCima - Séries` | Séries internationales et arabes |
| **Arabic-Toons**| Films | `🎨 Arabic-Toons - Films Animés` | Films d'animation doublés en arabe (CDN direct) |
| **Arabic-Toons**| Séries | `🎨 Arabic-Toons - Séries Animées`| Séries animées et Spacetoon |
| **AlooyTV** | Séries | `📺 AlooyTV - Séries du Golfe & Arabes` | Drames du Golfe (Koweït, Arabie Saoudite) et turcs |

---

## 🎯 Affichage clair dans Stremio

1. **Étiquettes de Source (`Genres`)** : Chaque contenu affiche le badge de sa source (ex: `[Akwam]`, `[Cartoony]`, `[WeCima]`) directement sous son titre.
2. **Détails (`Description`)** : La fiche détaillée affiche la ligne `📍 Source : <Nom du site>`.
3. **Lecteur Vidéo (`Streams`)** : Les flux portent la mention `Arabstreamz [Source Qualité]` avec la taille et la vitesse du serveur (ex: `Arabstreamz [Akwam 1080p]`, `Arabstreamz [Cartoony HD]`).

---

## 🔗 Installation dans Stremio

### 1. En local sur votre machine
1. Lancez l'addon :
   ```bash
   .venv/bin/python main.py
   ```
2. Ouvrez Stremio, allez dans **Extensions (🧩 Addons)**.
3. Dans le champ **Search addons** (en haut à droite), collez :
   ```text
   http://127.0.0.1:3000/manifest.json
   ```
4. Appuyez sur **Entrée** puis cliquez sur **Install**.
5. Interface de configuration disponible sur : [http://127.0.0.1:3000/configure](http://127.0.0.1:3000/configure).

### 2. En ligne / Cloud (Render, Koyeb, Railway, VPS...)
Une fois hébergé avec votre domaine HTTPS :
```text
https://<votre-domaine>/manifest.json
```
*(ou `stremio://<votre-domaine>/manifest.json`)*

---

## 📂 Structure du Projet

```text
├── main.py                # Serveur FastAPI et routage Stremio Arabstreamz
├── providers/             # Architecture multi-sources modulaire
│   ├── base.py            # Interface BaseProvider
│   ├── akwam.py           # Akwam / Akoam (Films & Séries 1080p/720p/480p)
│   ├── cartoony.py        # Cartoony (cartoony.net 330+ Anime en HLS 1080p)
│   ├── ahwaktv.py         # Ahwak TV (Séries Ramadan & HLS Direct)
│   ├── laroza.py          # Laroza Video (Séries turques & HLS Direct)
│   ├── wecima.py          # WeCima (wecima.cx & recherche direct CDN)
│   ├── arabic_toons.py    # Arabic-Toons (Animation Spacetoon)
│   ├── alooytv.py         # AlooyTV (Dramas du Golfe)
│   └── utils.py           # Client HTTP asynchrone, unpacker et cache
├── templates/             # Interface web Arabstreamz
│   ├── config.js
│   └── index.html
├── Dockerfile             # Déploiement conteneurisé
└── requirements.txt       # Dépendances Python
```
