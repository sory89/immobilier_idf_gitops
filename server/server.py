"""API HTTP d'estimation immobiliere en Ile-de-France.

Ce module ne contient que la couche transport : schemas d'entree/sortie,
routes, codes d'erreur. Toute la logique vit dans util.py.

Lancement :
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload

Documentation interactive : http://<ip-vm>:8000/docs
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import util

BASE = Path(__file__).parent
CLIENT = BASE.parent / "client"


@asynccontextmanager
async def cycle_de_vie(app: FastAPI):
    """Charge le modele une seule fois, au demarrage du serveur."""
    util.charger_artefacts()
    yield


app = FastAPI(
    title="Prix immobilier Île-de-France",
    description="Estimation du prix de vente à partir des caractéristiques du bien",
    version="1.0.0",
    lifespan=cycle_de_vie,
)


# --- Schemas ---------------------------------------------------------------
class Bien(BaseModel):
    ville: str = Field(..., examples=["Paris"])
    quartier: str = Field(..., examples=["Le Marais"])
    departement: str = Field("", examples=["75"], description="Optionnel")
    surface: float = Field(..., gt=8, lt=400, description="Surface habitable en m²")
    pieces: int = Field(..., ge=1, le=8)
    salles_de_bain: int = Field(1, ge=1, le=5)
    balcons: int = Field(0, ge=0, le=3)
    dpe: str = Field("D", pattern="^[A-G]$")


class Estimation(BaseModel):
    prix_eur: int
    prix_m2_eur: int
    ville: str
    quartier: str


# --- Routes ----------------------------------------------------------------
@app.get("/health")
def health():
    """Sonde de disponibilite."""
    return {"status": "ok" if util.est_charge() else "degrade",
            "communes": len(util.get_villes() or [])}


@app.get("/villes")
def villes():
    """Communes connues du modele."""
    return {"villes": util.get_villes()}


@app.get("/quartiers")
def quartiers():
    """Quartiers connus du modele."""
    return {"quartiers": util.get_quartiers()}


@app.get("/villes_quartiers")
def villes_quartiers():
    """Correspondance commune -> quartiers, pour les menus deroulants."""
    return util.get_mapping()


@app.post("/predire", response_model=Estimation)
def predire(bien: Bien):
    """Estime le prix de vente d'un bien."""
    try:
        prix = util.estimer_prix(
            ville=bien.ville,
            quartier=bien.quartier,
            departement=bien.departement,
            surface=bien.surface,
            pieces=bien.pieces,
            salles_de_bain=bien.salles_de_bain,
            balcons=bien.balcons,
            dpe=bien.dpe,
        )
    except util.DonneeInvalide as e:
        raise HTTPException(status_code=422, detail=str(e))

    return Estimation(prix_eur=round(prix),
                      prix_m2_eur=round(prix / bien.surface),
                      ville=bien.ville,
                      quartier=bien.quartier)


# --- Front statique, servi par la meme application (donc pas de CORS) ------
if CLIENT.exists():
    app.mount("/static", StaticFiles(directory=CLIENT, html=True), name="static")

    @app.get("/", include_in_schema=False)
    def racine():
        return RedirectResponse("/static/index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        """Les navigateurs demandent /favicon.ico a la racine, pas dans /static."""
        return FileResponse(CLIENT / "favicon.ico")
else:
    @app.get("/", include_in_schema=False)
    def racine():
        return RedirectResponse("/docs")