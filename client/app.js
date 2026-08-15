// Front de l'API d'estimation. Servi par FastAPI lui-meme : les URL sont relatives,
// donc aucun probleme de CORS et rien a changer si l'IP de la VM change.

const API = "";                 // meme origine que la page
let MAPPING = {};               // { ville: [quartiers] }

const $ = (id) => document.getElementById(id);
const radioCoche = (nom) => document.querySelector(`input[name="${nom}"]:checked`).value;

// --- Chargement initial ----------------------------------------------------
async function chargerCommunes() {
    try {
        const r = await fetch(`${API}/villes_quartiers`);
        if (!r.ok) throw new Error(r.status);
        MAPPING = await r.json();
    } catch (e) {
        // repli : listes plates, sans filtrage par commune
        const [v, q] = await Promise.all([
            fetch(`${API}/villes`).then((x) => x.json()),
            fetch(`${API}/quartiers`).then((x) => x.json()),
        ]);
        v.villes.forEach((ville) => { MAPPING[ville] = q.quartiers; });
    }

    const selVille = $("uiVille");
    selVille.innerHTML = "";
    Object.keys(MAPPING).sort().forEach((ville) => {
        selVille.appendChild(new Option(ville, ville));
    });
    selVille.value = MAPPING["Paris"] ? "Paris" : selVille.options[0].value;
    majQuartiers();
}

function majQuartiers() {
    const selQuartier = $("uiQuartier");
    selQuartier.innerHTML = "";
    (MAPPING[$("uiVille").value] || []).forEach((q) => {
        selQuartier.appendChild(new Option(q, q));
    });
}

// --- Coherence salles de bain : max = pieces - 1 ---------------------------
function majSallesDeBain() {
    const pieces = parseInt(radioCoche("pieces"), 10);
    const plafond = Math.max(1, pieces - 1);
    let coche = parseInt(radioCoche("sdb"), 10);

    document.querySelectorAll('input[name="sdb"]').forEach((input) => {
        const v = parseInt(input.value, 10);
        input.disabled = v > plafond;
        if (input.disabled && input.checked) coche = plafond;
    });
    document.querySelector(`input[name="sdb"][value="${Math.min(coche, plafond)}"]`).checked = true;
}

// --- Estimation ------------------------------------------------------------
async function estimer() {
    const bouton = $("uiEstimer");
    const zone = $("uiResultat");
    bouton.disabled = true;
    bouton.textContent = "Calcul en cours…";

    const corps = {
        ville: $("uiVille").value,
        quartier: $("uiQuartier").value,
        departement: "",                       // deduit cote serveur si absent des colonnes
        surface: parseFloat($("uiSurface").value),
        pieces: parseInt(radioCoche("pieces"), 10),
        salles_de_bain: parseInt(radioCoche("sdb"), 10),
        balcons: parseInt(radioCoche("balcons"), 10),
        dpe: $("uiDpe").value,
    };

    try {
        const r = await fetch(`${API}/predire`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(corps),
        });
        const data = await r.json();

        if (!r.ok) {
            const msg = Array.isArray(data.detail)
                ? data.detail.map((d) => d.msg).join(" · ")
                : data.detail;
            zone.className = "resultat erreur";
            zone.textContent = msg || "Erreur inattendue";
            return;
        }

        const euros = (n) => n.toLocaleString("fr-FR");
        zone.className = "resultat ok";
        zone.innerHTML =
            `<span class="prix">${euros(data.prix_eur)} €</span>` +
            `<span class="detail">${euros(data.prix_m2_eur)} €/m² — ` +
            `${data.quartier}, ${data.ville}</span>`;
    } catch (e) {
        zone.className = "resultat erreur";
        zone.textContent = "API injoignable : " + e.message;
    } finally {
        bouton.disabled = false;
        bouton.textContent = "Estimer le prix";
    }
}

// --- Branchements ----------------------------------------------------------
window.addEventListener("DOMContentLoaded", () => {
    chargerCommunes();
    majSallesDeBain();
    $("uiVille").addEventListener("change", majQuartiers);
    $("uiPieces").addEventListener("change", majSallesDeBain);
    $("uiEstimer").addEventListener("click", estimer);
});