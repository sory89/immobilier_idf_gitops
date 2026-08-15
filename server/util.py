"""Chargement des artefacts et logique de prediction.

Ce module ne connait rien au HTTP : il peut etre importe depuis une API,
un notebook, un script batch ou un test unitaire.

    import util
    util.charger_artefacts()
    util.estimer_prix("Paris", "Le Marais", "75", 65, 3)
"""
from pathlib import Path
import json
import pickle

import numpy as np
import pandas as pd

BASE = Path(__file__).parent
ARTEFACTS = BASE / "artefacts"

# --- Etat du module, rempli par charger_artefacts() ------------------------
__modele = None
__colonnes = None
__villes = None
__quartiers = None
__mapping = None          # {commune: [quartiers]}


class DonneeInvalide(ValueError):
    """Saisie refusee : commune inconnue, couple incoherent, etc."""


def charger_artefacts():
    """Charge le modele et les metadonnees. A appeler une fois au demarrage."""
    global __modele, __colonnes, __villes, __quartiers, __mapping

    with open(ARTEFACTS / "colonnes.json", encoding="utf-8") as f:
        meta = json.load(f)

    __colonnes = meta["colonnes"]
    __villes = meta["villes"]
    __quartiers = meta["quartiers"]

    with open(ARTEFACTS / "modele_prix_idf.pickle", "rb") as f:
        __modele = pickle.load(f)

    # Correspondance commune -> quartiers : evite de proposer un couple
    # inexistant comme "Trappes / Le Marais".
    csv = next((p for p in (ARTEFACTS / "ventes_idf_v3.csv",
                            ARTEFACTS / "ventes_idf.csv") if p.exists()), None)
    if csv is not None:
        table = pd.read_csv(csv, usecols=["ville", "quartier"]).dropna()
        __mapping = {v: sorted(g.quartier.unique().tolist())
                     for v, g in table.groupby("ville")}
    else:
        __mapping = {v: __quartiers for v in __villes}

    print(f"artefacts charges : {len(__colonnes)} variables, {len(__villes)} communes")


# --- Accesseurs ------------------------------------------------------------
def get_villes():
    return __villes


def get_quartiers():
    return __quartiers


def get_mapping():
    return __mapping


def est_charge():
    return __modele is not None


# --- Regles metier ---------------------------------------------------------
def plafond_salles_de_bain(pieces):
    """Un T4 = sejour + 3 chambres : au plus 3 salles d'eau."""
    return max(1, pieces - 1)


def valider(ville, quartier, pieces, salles_de_bain):
    """Leve DonneeInvalide si la saisie est incoherente."""
    if __modele is None:
        raise DonneeInvalide("Artefacts non charges : appelle charger_artefacts()")
    if ville not in __villes:
        raise DonneeInvalide(f"Commune inconnue : {ville}")
    if quartier not in __quartiers:
        raise DonneeInvalide(f"Quartier inconnu : {quartier}")
    if quartier not in __mapping.get(ville, __quartiers):
        raise DonneeInvalide(f"Le quartier {quartier} n'est pas a {ville}")
    if salles_de_bain > plafond_salles_de_bain(pieces):
        raise DonneeInvalide(
            f"Un T{pieces} ne peut pas avoir {salles_de_bain} salles de bain"
        )


# --- Prediction ------------------------------------------------------------
def estimer_prix(ville, quartier, departement, surface, pieces,
                 salles_de_bain=1, balcons=0, dpe="D"):
    """Prix estime en euros.

    Le modele a ete entraine sur log(prix_eur) : d'ou l'exponentielle en sortie.
    Sans elle, on renverrait un logarithme (de l'ordre de 13) au lieu d'un prix.
    """
    valider(ville, quartier, pieces, salles_de_bain)

    x = np.zeros(len(__colonnes))
    for nom, valeur in [("surface", surface),
                        ("pieces", pieces),
                        ("salles_de_bain", salles_de_bain),
                        ("balcons", balcons)]:
        x[__colonnes.index(nom)] = valeur

    # Une modalite absente des colonnes est la reference retiree par
    # drop_first : il n'y a rien a activer, c'est le cas nominal.
    for colonne in (f"ville_{ville}", f"quartier_{quartier}",
                    f"departement_{departement}", f"dpe_{dpe}"):
        if colonne in __colonnes:
            x[__colonnes.index(colonne)] = 1

    log_prix = __modele.predict(pd.DataFrame([x], columns=__colonnes))[0]
    return float(np.exp(log_prix))


if __name__ == "__main__":
    charger_artefacts()
    for v, q, d in [("Paris", "Le Marais", "75"),
                    ("Saint-Denis", "Pleyel", "93"),
                    ("Trappes", "Village", "78")]:
        prix = estimer_prix(v, q, d, surface=65, pieces=3, salles_de_bain=1, balcons=1, dpe="C")
        print(f"{v:16} {q:12} {prix:>10,.0f} EUR")