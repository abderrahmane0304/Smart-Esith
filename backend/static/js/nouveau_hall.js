let currentCycleIndex = 0;
let currentCyclePageIndex = 0;
const MAX_PER_PAGE = 8;        // 8 séances max par colonne (4 lignes de 2) calibré pour grande télé dans le hall
const cycles = ['licence', 'ingenieur', 'master', 'fc', 're'];
const cycleNames = {
    'licence': 'CYCLE LICENCE',
    'ingenieur': "CYCLE INGÉNIEUR D'ETAT",
    'master': 'CYCLE MASTER',
    'fc': 'FORMATION CONTINUE',
    're': 'RELATIONS ENTREPRISES'
};
const SPLASH_MS = 3000;       // 3 s pour la page d'accueil (selon demande utilisateur)
const ROTATION_MS = 6000;     // 6 s par page de cours (Formation Initiale)
const FC_ROTATION_MS = 10000; // 10 s pour la Formation Continue (selon demande utilisateur)
const REFRESH_MS = 60000;    // rafraîchissement des données : 60 s
let allData = null;
let firstRenderDone = false;
let isShowingSplash = true;
let currentCycleTotalPages = 1;
let rotationTimeout = null;

// ── Sécurité & Encodage : échappe et nettoie le texte inséré dans le HTML ───
function fixEncoding(str) {
    if (!str) return '';
    return String(str)
        .replace(/Amphith[\ufffd?]+tre/gi, 'Amphithéâtre')
        .replace(/Amphithtre/gi, 'Amphithéâtre')
        .replace(/\ufffd\ufffd/g, 'éâ')
        .replace(/\ufffd/g, 'é');
}

function esc(value) {
    const cleaned = fixEncoding(value);
    return String(cleaned ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function norm(value) {
    return String(value ?? '').replace(/\s+/g, '').toLowerCase();
}

function updateClock() {
    const now = new Date();
    const days = ['DIMANCHE', 'LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI'];
    const months = ['JANVIER', 'FÉVRIER', 'MARS', 'AVRIL', 'MAI', 'JUIN', 'JUILLET', 'AOÛT', 'SEPTEMBRE', 'OCTOBRE', 'NOVEMBRE', 'DÉCEMBRE'];

    const dateStr = `${days[now.getUTCDay()]} ${now.getUTCDate()} ${months[now.getUTCMonth()]} ${now.getUTCFullYear()}`;
    const timeStr = now.toLocaleTimeString('fr-FR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const splashDate = document.getElementById('splash-date');
    const splashTime = document.getElementById('splash-time');
    if (splashDate) splashDate.innerText = dateStr;
    if (splashTime) splashTime.innerText = timeStr;

    const dateDisplay = document.getElementById('date-display');
    const timeDisplay = document.getElementById('time-display');
    if (dateDisplay) dateDisplay.innerText = dateStr;
    if (timeDisplay) timeDisplay.innerText = timeStr;
}

setInterval(updateClock, 1000);
updateClock();

function showSplashScreen() {
    isShowingSplash = true;
    const splash = document.getElementById('splash-screen');
    const main = document.getElementById('main-content');
    if (splash) {
        splash.style.display = 'block';
        splash.style.opacity = '1';
        splash.style.visibility = 'visible';
    }
    if (main) {
        main.style.display = 'none';
    }
    updateClock();
    scheduleNextRotation(SPLASH_MS);
}

function showMainContent() {
    isShowingSplash = false;
    const splash = document.getElementById('splash-screen');
    const main = document.getElementById('main-content');
    if (splash) {
        splash.style.display = 'none';
    }
    if (main) {
        main.style.display = 'block';
    }
}

function scheduleNextRotation(delayMs) {
    if (rotationTimeout) clearTimeout(rotationTimeout);
    rotationTimeout = setTimeout(stepRotation, delayMs);
}

function getActiveCycleIndices() {
    if (!allData) return [];
    const active = [];
    for (let i = 0; i < cycles.length; i++) {
        const list = allData[cycles[i]];
        if (list && list.length > 0 && filterCoursesByTime(list).length > 0) {
            active.push(i);
        }
    }
    return active;
}

function getCycleDuration(cycleKey) {
    if (cycleKey === 'fc') return FC_ROTATION_MS;
    return ROTATION_MS;
}

function stepRotation() {
    const active = getActiveCycleIndices();
    if (active.length === 0) {
        if (isShowingSplash) {
            showMainContent();
            document.getElementById('current-cycle').innerText = 'PROGRAMME DU JOUR';
            document.getElementById('year-columns').style.display = 'none';
            document.getElementById('no-courses').style.display = 'block';
            scheduleNextRotation(ROTATION_MS);
        } else {
            showSplashScreen();
        }
        return;
    }

    if (isShowingSplash) {
        // Fin de l'affichage de la page d'accueil (3 s) -> afficher le 1er cycle actif
        showMainContent();
        currentCycleIndex = active[0];
        currentCyclePageIndex = 0;
        renderCycle();
        scheduleNextRotation(getCycleDuration(cycles[currentCycleIndex]));
        return;
    }

    // Si le cycle actuel possède d'autres pages (ex. Ingénieur 2/2)
    if (currentCyclePageIndex + 1 < currentCycleTotalPages) {
        currentCyclePageIndex++;
        renderCycle();
        scheduleNextRotation(getCycleDuration(cycles[currentCycleIndex]));
        return;
    }

    // Le cycle actuel a fini toutes ses pages
    currentCyclePageIndex = 0;
    const activePos = active.indexOf(currentCycleIndex);

    if (activePos !== -1 && activePos + 1 < active.length) {
        // Passer au cycle suivant dans la liste active
        currentCycleIndex = active[activePos + 1];
        renderCycle();
        scheduleNextRotation(getCycleDuration(cycles[currentCycleIndex]));
    } else {
        // Tous les cycles de la boucle ont été affichés !
        // Réafficher la page d'accueil pour 3 secondes
        showSplashScreen();
    }
}

async function fetchData() {
    try {
        const response = await fetch('/api/hall/all_data', { cache: 'no-store' });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        allData = await response.json();

        if (allData.empreinte_carbone !== undefined && allData.empreinte_carbone !== null) {
            const val = Math.max(0, Math.min(100, Number(allData.empreinte_carbone) || 0));
            document.getElementById('carbone-val').innerText = val + '%';
            document.getElementById('carbon-fill').style.width = val + '%';
        }

        // Bandeau d'événements : ÉVÉNEMENT : Titre — Date — Lieu
        const footer = document.querySelector('footer');
        if (allData.events && allData.events.length > 0) {
            const eventText = allData.events.map(e => {
                const parts = [`ÉVÉNEMENT : ${String(e.titre || '').toUpperCase()}`];
                if (e.date) parts.push(e.date + (e.heure_debut ? ' à ' + e.heure_debut : ''));
                if (e.lieu) parts.push(String(e.lieu).toUpperCase());
                return parts.join(' — ');
            }).join('     ★     ');
            const marquee = document.getElementById('event-marquee');
            if (marquee.innerText !== eventText) marquee.innerText = eventText;
            footer.style.display = 'block';
        } else {
            footer.style.display = 'none';
        }

        // Indique la date affichée si ce n'est pas aujourd'hui (aucune séance aujourd'hui)
        const banner = document.getElementById('date-banner');
        if (banner) {
            if (allData.is_today === false && allData.date_affichee) {
                banner.innerText = `Aucune séance aujourd'hui — Programme du ${allData.date_affichee}`;
                banner.style.display = 'inline-block';
            } else {
                banner.style.display = 'none';
            }
        }

        if (!firstRenderDone) {
            firstRenderDone = true;
        }
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

function parseGroup(groupe) {
    if (!groupe) return { year: 1, filiere: 'AUTRE' };

    const g = groupe.trim().toUpperCase();
    let year = 1;

    // ── 1. Cas prioritaires nommés ────────────────────────────────────────────
    // INGTCG (Tronc Commun Génie) = TOUJOURS 1ère année Ingénieur
    // Le chiffre après INGTCG est un numéro de groupe, pas une année
    if (g.startsWith('INGTCG') || g.includes('TC')) {
        year = 1;
    }
    // Master : M1 / M2
    else if (/(?:^|[^A-Z])M1(?:[^A-Z]|$)/.test(g)) { year = 1; }
    else if (/(?:^|[^A-Z])M2(?:[^A-Z]|$)/.test(g)) { year = 2; }
    // Ingénieur : 1A / 2A / 3A
    else if (g.includes('1A')) { year = 1; }
    else if (g.includes('2A')) { year = 2; }
    else if (g.includes('3A')) { year = 3; }
    // Licence semestres : S1/S2 = an1, S3/S4 = an2, S5/S6 = an3
    // On utilise un regex avec limite de mot pour éviter de matcher GAS2 → S2
    else if (/(?:^|[-_\s.])S[12](?:[-_\s.\d]|$)/.test(g)) { year = 1; }
    else if (/(?:^|[-_\s.])S[34](?:[-_\s.\d]|$)/.test(g)) { year = 2; }
    else if (/(?:^|[-_\s.])S[56](?:[-_\s.\d]|$)/.test(g)) { year = 3; }
    // GAS : le chiffre après GAS = numéro d'année (GAS1=an1, GAS2=an2...)
    else if (/^GAS(\d)/.test(g)) {
        year = Math.min(parseInt(g.match(/^GAS(\d)/)[1]), 3) || 1;
    }
    // Fallback : premier chiffre dans le nom
    else {
        const m = g.match(/(\d)/);
        if (m) {
            year = parseInt(m[1]);
            if (year > 3) year = 3;
            if (year === 0) year = 1;
        }
    }

    // ── 2. Clamp ──────────────────────────────────────────────────────────────
    if (year < 1) year = 1;
    if (year > 3) year = 3;

    // ── 3. Filière ────────────────────────────────────────────────────────────
    let base = g.replace(/(?:1A|2A|3A|M1|M2|S[1-6]|LICENCE|INGENIEUR|MASTER)/g, '');
    let filiere = base.replace(/[^A-Z]/g, ''); // Keep only letters
    if (!filiere) filiere = 'AUTRE';

    return { year, filiere };
}


// ── Construit une pilule de cours ─────────────────────────────────────────────
function buildPill(c, alertClass, salleContent) {
    const div = document.createElement('div');
    div.className = 'course-pill' + (alertClass ? ' ' + alertClass : '');

    const textColor = alertClass ? 'white' : '#0B4F6C';

    const groupeStr = c.groupe || '';
    const gLen = groupeStr.length;
    let fontSize = '2.25rem';
    if (gLen > 22) {
        fontSize = '1.45rem';
    } else if (gLen > 11) {
        fontSize = '1.75rem';
    }

    // Calibrage adaptatif de la taille de police de la salle pour couvrir toute l'écriture
    const salleStr = c.salle || '';
    let roomFontSize = '1.45rem';
    let roomLineHeight = '1.2';
    if (salleStr.length > 22) {
        roomFontSize = '0.98rem';
        roomLineHeight = '1.15';
    } else if (salleStr.length > 13) {
        roomFontSize = '1.2rem';
        roomLineHeight = '1.18';
    }

    div.innerHTML = `
        <div class="course-time" style="font-size:1.18rem;font-weight:800;color:${textColor};opacity:0.95;margin-bottom:3px;letter-spacing:0.5px;">
            ${esc(c.h || ((c.hd || '') + (c.hf ? '-' + c.hf : '')))}
        </div>
        <div class="course-module" style="font-size:${fontSize};font-weight:900;color:${textColor};line-height:1.12;white-space:normal;word-break:break-word;">
            ${esc(groupeStr)}
        </div>
        <div class="course-room" style="font-size:${roomFontSize};line-height:${roomLineHeight};font-weight:800;color:${textColor};margin-top:3px;white-space:normal;word-break:break-word;">
            ${salleContent}
        </div>
    `;
    return div;
}

// ── Convertit "HH:MM" en minutes depuis minuit ────────────────────────────
function timeToMinutes(timeStr) {
    if (!timeStr || timeStr === 'nan' || timeStr === 'None') return null;
    const match = String(timeStr).match(/^(\d{1,2})[:hH](\d{2})/);
    if (!match) return null;
    return parseInt(match[1], 10) * 60 + parseInt(match[2], 10);
}

function filterCoursesByTime(courses) {
    const now = new Date();
    const nowMin = now.getUTCHours() * 60 + now.getUTCMinutes();
    const isMorning = nowMin < 13 * 60; // avant 13h00

    // Les cours sans heures (fréquent pour FC / RE) restent toujours visibles
    const withoutTime = courses.filter(c => timeToMinutes(c.hd) === null);

    // Les cours avec heures
    const withTime = courses.filter(c => timeToMinutes(c.hd) !== null);

    let filteredWithTime = [];

    // Séances actuellement en cours (hd <= now <= hf, tolérance +30 min avant hd)
    const active = withTime.filter(c => {
        const hd = timeToMinutes(c.hd);
        const hf = timeToMinutes(c.hf);
        const start = hd - 30;
        const end = hf !== null ? hf : hd + 120;
        return nowMin >= start && nowMin <= end;
    });

    if (active.length > 0) {
        filteredWithTime = active;
    } else {
        // Aucune séance en cours → séances de la demi-journée pas encore terminées
        const upcoming = withTime.filter(c => {
            const hd = timeToMinutes(c.hd);
            const hf = timeToMinutes(c.hf);
            const end = hf !== null ? hf : hd + 120;
            const isCurrentHalfDay = isMorning ? hd < 13 * 60 : hd >= 13 * 60;
            return isCurrentHalfDay && end > nowMin;
        });

        if (upcoming.length > 0) {
            filteredWithTime = upcoming;
        } else {
            // Fallback : toutes les séances de la demi-journée (déjà terminées incluses)
            filteredWithTime = withTime.filter(c => {
                const hd = timeToMinutes(c.hd);
                return isMorning ? hd < 13 * 60 : hd >= 13 * 60;
            });
        }
    }

    // Combine courses with time and without time
    return [...filteredWithTime, ...withoutTime];
}

// ── Pour chaque groupe : garde 1 seule séance selon l'heure actuelle ──────────
// Priorité :
//   1. Séance EN COURS (hd <= now <= hf)         → afficher
//   2. Aucune en cours → PROCHAINE séance (hd > now, la plus tôt)  → afficher
//   3. Tout terminé → la dernière séance terminée → afficher
function deduplicateCoursesByGroup(courses) {
    const now   = new Date();
    const nowMin = now.getUTCHours() * 60 + now.getUTCMinutes();

    // Regrouper par groupe
    const byGroup = {};
    for (const c of courses) {
        const key = c.groupe || '__no_groupe__';
        if (!byGroup[key]) byGroup[key] = [];
        byGroup[key].push(c);
    }

    const result = [];
    for (const key of Object.keys(byGroup)) {
        const list = byGroup[key];

        // 1 seule séance → on la garde directement
        if (list.length === 1) { result.push(list[0]); continue; }

        // Séances sans heure (FC / RE) : on les garde toutes (sessions distinctes)
        const noTime = list.filter(c => timeToMinutes(c.hd) === null);
        const timed = list.filter(c => timeToMinutes(c.hd) !== null);
        if (timed.length === 0) { result.push(...noTime); continue; }

        // Trier par heure de début
        const sorted = [...timed].sort((a, b) => timeToMinutes(a.hd) - timeToMinutes(b.hd));

        // Cherche la séance en cours
        const active = sorted.find(c => {
            const hd = timeToMinutes(c.hd);
            const hf = timeToMinutes(c.hf);
            const end = hf !== null ? hf : hd + 120;
            return nowMin >= hd && nowMin <= end;
        });
        if (active) { result.push(active); continue; }

        // Cherche la prochaine séance (la plus tôt qui n'a pas encore commencé)
        const next = sorted.find(c => timeToMinutes(c.hd) > nowMin);
        if (next) { result.push(next); continue; }

        // Tout terminé → affiche la dernière de la journée
        result.push(sorted[sorted.length - 1]);
    }

    return result;
}

// ── Alertes (absence / retard / changement de salle) pour une séance ─────────
function getAlert(c) {
    let alertClass = '';
    let salleContent = c.salle ? `S. ${esc(c.salle)}` : '';

    const changes = allData.changements_salle || [];
    const cGroupTokens = (c.groupe || '').trim().split(/\s+/).filter(Boolean);
    const matchesGroup = (alertGroupe) => {
        if (!alertGroupe || !c.groupe) return false;
        if (alertGroupe === c.groupe) return true;
        if (cGroupTokens.includes(alertGroupe)) return true;
        const alertTokens = alertGroupe.trim().split(/\s+/).filter(Boolean);
        return alertTokens.some(t => cGroupTokens.includes(t));
    };

    // Le backend met déjà à jour la salle de la séance : on compare donc avec
    // la nouvelle salle (ou l'ancienne si la séance n'a pas été modifiée).
    const change = changes.find(x => matchesGroup(x.groupe) &&
        (norm(x.nouvelle_salle) === norm(c.salle) || (x.ancienne_salle && norm(x.ancienne_salle) === norm(c.salle))));
    if (change) {
        alertClass = 'alert-vert-fonce alert-yellow alert-mauve';
        const oldS = change.ancienne_salle ? `<span class="salle-barree">${esc(change.ancienne_salle)}</span>` : '';
        salleContent = `${oldS} S. ${esc(change.nouvelle_salle)}`;
    }

    if ((allData.retards || []).find(x => matchesGroup(x.groupe)))  alertClass = 'alert-orange';
    if ((allData.absences || []).find(x => matchesGroup(x.groupe))) alertClass = 'alert-red';
    return { alertClass, salleContent };
}


function renderCycle() {
    if (!allData) return;

    // Si on démarre un nouveau cycle (page 0), on cherche le prochain cycle non-vide
    if (currentCyclePageIndex === 0) {
        let foundCycle = false;
        let attempts = 0;
        while (attempts < cycles.length) {
            const list = allData[cycles[currentCycleIndex]];
            if (list && list.length > 0 && filterCoursesByTime(list).length > 0) {
                foundCycle = true;
                break;
            }
            currentCycleIndex = (currentCycleIndex + 1) % cycles.length;
            attempts++;
        }

        if (!foundCycle) {
            document.getElementById('current-cycle').innerText = 'PROGRAMME DU JOUR';
            document.getElementById('year-columns').style.display = 'none';
            document.getElementById('no-courses').style.display = 'block';
            return;
        }
    }

    const gridBody = document.getElementById('grid-body');
    const gridHeader = document.getElementById('grid-header');
    const yearColumns = document.getElementById('year-columns');
    gridBody.innerHTML = '';
    document.getElementById('no-courses').style.display = 'none';
    yearColumns.style.display = 'flex';

    const cycleKey = cycles[currentCycleIndex];
    const courses = deduplicateCoursesByGroup(filterCoursesByTime(allData[cycleKey]));

    let totalPages = 1;
    currentCycleTotalPages = 1;

    // ── RE et FC : cartes libres, centrées verticalement & horizontalement ──
    if (cycleKey === 're' || cycleKey === 'fc') {
        yearColumns.classList.add('fc-mode');
        gridHeader.innerHTML = '';
        gridHeader.style.display = 'none';
        document.getElementById('current-cycle').innerText = cycleNames[cycleKey];

        const flat = document.createElement('div');
        flat.className = 'flat-cards ' + (cycleKey === 'fc' ? 'grid-fc' : 'grid-re');

        [...courses]
            .sort((a, b) => (a.hd || '99:99').localeCompare(b.hd || '99:99') || (a.groupe || '').localeCompare(b.groupe || ''))
            .forEach(c => {
                const div = document.createElement('div');
                div.className = 'course-pill flat-card ' + (cycleKey === 'fc' ? 'card-fc' : 'card-re');
                const horaire = c.h || ((c.hd || '') + (c.hf ? '-' + c.hf : ''));
                div.innerHTML = `
                    ${horaire ? `<div class="flat-time">${esc(horaire)}</div>` : ''}
                    <div class="flat-title">${esc(c.groupe || '')}</div>
                    ${c.module ? `<div class="flat-sub">${esc(c.module)}</div>` : ''}
                    ${c.prof ? `<div class="flat-prof">${esc(c.prof)}</div>` : ''}
                    ${c.salle ? `<div class="flat-salle">${/^s(alle)?[\s.]/i.test(c.salle) ? '' : 'S. '}${esc(c.salle)}</div>` : ''}
                `;
                flat.appendChild(div);
            });

        gridBody.appendChild(flat);

    } else {
        yearColumns.classList.remove('fc-mode');
        // ── Cycles académiques (Formation Initiale) : grille par colonnes d'années ──
        gridHeader.style.display = 'flex';

        const isMaster = (cycleKey === 'master');
        const numCols  = isMaster ? 2 : 3;

        // Header dynamique
        if (isMaster) {
            gridHeader.innerHTML = `
                <div class="year-title">1<span class="year-sup">ÈRE</span> ANNÉE</div>
                <div class="year-title">2<span class="year-sup">ÈME</span> ANNÉE</div>
            `;
        } else {
            gridHeader.innerHTML = `
                <div class="year-title">1<span class="year-sup">ÈRE</span> ANNÉE</div>
                <div class="year-title">2<span class="year-sup">ÈME</span> ANNÉE</div>
                <div class="year-title">3<span class="year-sup">ÈME</span> ANNÉE</div>
            `;
        }

        const coursesParsed = courses.map(c => {
            const parsed = parseGroup(c.groupe);
            return { ...c, year: Math.min(parsed.year, numCols), filiere: parsed.filiere };
        });

        // Calcul des séances triées par colonne d'année et détection du nombre de pages
        const coursesByYear = [];
        let maxCoursesInAnyCol = 0;

        for (let y = 1; y <= numCols; y++) {
            const listY = coursesParsed
                .filter(c => c.year === y)
                .sort((a, b) => {
                    const fA = (a.filiere || 'AUTRE').localeCompare(b.filiere || 'AUTRE');
                    if (fA !== 0) return fA;
                    const gA = (a.groupe || '').localeCompare(b.groupe || '');
                    if (gA !== 0) return gA;
                    return (a.hd || '00:00').localeCompare(b.hd || '00:00');
                });
            coursesByYear.push(listY);
            if (listY.length > maxCoursesInAnyCol) {
                maxCoursesInAnyCol = listY.length;
            }
        }

        // Calcul du nombre de pages pour le cycle (max 8 séances par colonne pour une lisibilité optimale sur grande télé)
        totalPages = Math.max(1, Math.ceil(maxCoursesInAnyCol / MAX_PER_PAGE));
        currentCycleTotalPages = totalPages;
        if (currentCyclePageIndex >= totalPages) {
            currentCyclePageIndex = 0;
        }

        // Titre du cycle avec indicateur de page si multi-pages
        const baseTitle = cycleNames[cycleKey];
        if (totalPages > 1) {
            document.getElementById('current-cycle').innerHTML = `${baseTitle} <span class="page-badge">(${currentCyclePageIndex + 1}/${totalPages})</span>`;
        } else {
            document.getElementById('current-cycle').innerText = baseTitle;
        }

        // Création de la ligne contenant les colonnes d'années
        const row = document.createElement('div');
        row.className = 'filiere-row';
        row.style.alignItems = 'stretch';
        row.style.flex = '1';

        for (let y = 1; y <= numCols; y++) {
            const cell = document.createElement('div');
            cell.className = 'filiere-cell';

            const listY = coursesByYear[y - 1] || [];
            const start = currentCyclePageIndex * MAX_PER_PAGE;
            const displayedCourses = listY.slice(start, start + MAX_PER_PAGE);

            displayedCourses.forEach(c => {
                const { alertClass, salleContent } = getAlert(c);
                cell.appendChild(buildPill(c, alertClass, salleContent));
            });

            row.appendChild(cell);
        }
        gridBody.appendChild(row);
    }

    return totalPages;
}

fetchData();
setInterval(fetchData, REFRESH_MS);
showSplashScreen();
