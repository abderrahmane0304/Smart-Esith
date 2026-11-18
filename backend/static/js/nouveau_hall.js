let currentCycleIndex = 0;
let currentCyclePageIndex = 0;
const MAX_PER_PAGE = 8;        // 8 séances max par colonne (4 lignes de 2) calibré pour grande télé dans le hall
const cycles = ['licence', 'ingenieur', 'master', 'fc', 're', 'event'];
const cycleNames = {
    'licence': 'CYCLE LICENCE',
    'ingenieur': "CYCLE INGÉNIEUR D'ETAT",
    'master': 'CYCLE MASTER',
    'fc': 'FORMATION CONTINUE',
    're': 'RELATIONS ENTREPRISES',
    'event': 'ACCUEIL & ÉVÉNEMENT'
};
const SPLASH_MS = 6000;       // 6 s pour la page d'accueil (selon demande utilisateur)
const ROTATION_MS = 10000;    // 10 s par cycle / page de cours (selon demande utilisateur)
const FC_ROTATION_MS = 10000; // 10 s pour la Formation Continue (selon demande utilisateur)
const EVENT_ROTATION_MS = 10000; // 10 s pour l'affiche d'événement en rotation
const REFRESH_MS = 60000;    // rafraîchissement des données : 60 s
let allData = null;
let firstRenderDone = false;
let isShowingSplash = true;
let currentCycleTotalPages = 1;
let rotationTimeout = null;
let lastTickerRawText = '';

function updateTickerDuration(track, containerW) {
    const halfWidth = track.scrollWidth / 2;
    if (halfWidth <= 0) return;
    // Vitesse constante fluide (~135 px/s sur 1920px, proportionnelle à l'écran)
    const pxPerSec = Math.max(95, (containerW || window.innerWidth || 1280) * 0.085);
    const duration = Math.max(6, halfWidth / pxPerSec);
    track.style.setProperty('--ticker-duration', `${duration.toFixed(2)}s`);
}

function renderEventTicker(rawText, forceRebuild = false) {
    const ticker = document.getElementById('event-ticker');
    const track = document.getElementById('event-marquee');
    if (!ticker || !track) return;

    const text = (rawText || '').trim();
    if (!text) return;

    const containerW = ticker.clientWidth || window.innerWidth || 1280;
    if (!forceRebuild && text === lastTickerRawText && track.children.length === 2) {
        updateTickerDuration(track, containerW);
        return;
    }
    lastTickerRawText = text;

    const unit = `${text}     ★     `;
    const chunk1 = document.createElement('span');
    chunk1.className = 'ticker-chunk';
    chunk1.textContent = unit;

    track.innerHTML = '';
    track.appendChild(chunk1);

    if (chunk1.offsetWidth > 0) {
        let safety = 0;
        while (chunk1.offsetWidth < containerW + 120 && safety < 24) {
            chunk1.textContent += unit;
            safety++;
        }
    } else {
        const approxReps = Math.max(2, Math.min(12, Math.ceil((containerW + 120) / Math.max(120, unit.length * 14))));
        chunk1.textContent = unit.repeat(approxReps);
    }

    const chunk2 = chunk1.cloneNode(true);
    track.appendChild(chunk2);

    updateTickerDuration(track, containerW);
}

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
        main.style.display = 'flex';
    }
    if (lastTickerRawText) {
        renderEventTicker(lastTickerRawText, true);
    } else {
        const footer = document.querySelector('footer');
        const track = document.getElementById('event-marquee');
        if (footer && footer.style.display !== 'none' && track && track.textContent.trim()) {
            renderEventTicker(track.textContent.trim(), true);
        }
    }
}

function scheduleNextRotation(delayMs) {
    if (rotationTimeout) clearTimeout(rotationTimeout);
    rotationTimeout = setTimeout(stepRotation, delayMs);
}

let currentPosterIndex = 0;
let figeCarouselTimer = null;

function renderPosterElement(poster, totalCount = 1, activeIdx = 0) {
    const posterContainer = document.getElementById('event-poster-container');
    const posterImg = document.getElementById('event-poster-img');
    if (!posterContainer || !posterImg || !poster) return;

    const cycleTitle = document.getElementById('current-cycle');
    if (cycleTitle) {
        cycleTitle.innerText = poster.titre ? String(poster.titre).toUpperCase() : 'BIENVENUE À L\'ESITH';
    }

    if (posterImg.src !== poster.media_path) {
        posterImg.style.opacity = '0';
        setTimeout(() => {
            posterImg.src = poster.media_path;
            posterImg.onload = () => { posterImg.style.opacity = '1'; };
            posterImg.onerror = () => { posterImg.style.opacity = '1'; };
        }, 120);
    } else {
        posterImg.style.opacity = '1';
    }

    // Indicateurs du carousel si plusieurs affiches
    let indicators = document.getElementById('poster-carousel-indicators');
    if (totalCount > 1) {
        if (!indicators) {
            indicators = document.createElement('div');
            indicators.id = 'poster-carousel-indicators';
            indicators.className = 'poster-indicators';
            posterContainer.appendChild(indicators);
        }
        indicators.innerHTML = '';
        for (let i = 0; i < totalCount; i++) {
            const dot = document.createElement('span');
            dot.className = `poster-dot ${i === activeIdx ? 'active' : ''}`;
            indicators.appendChild(dot);
        }
        indicators.style.display = 'flex';
    } else if (indicators) {
        indicators.style.display = 'none';
    }

    posterContainer.style.display = 'flex';
}

function getActiveCycleIndices() {
    if (!allData) return [];
    // Si une affiche d'événement est en mode 'fige', elle monopolise l'écran
    const hasFige = (allData.event_posters && allData.event_posters.some(p => p.mode_affichage === 'fige')) ||
                    (allData.event_poster && allData.event_poster.media_path && allData.event_poster.mode_affichage === 'fige');
    if (hasFige) {
        return [];
    }

    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();

    // Règle : le matin, l'affichage des cours en direct commence à partir de 07h00
    // Avant 07h00 du matin, l'écran reste sur la page d'accueil (splash)
    const isTomorrowFI = Boolean(allData.is_tomorrow_fi);
    if (!isTomorrowFI && nowMin < 7 * 60) {
        return [];
    }

    const active = [];
    for (let i = 0; i < cycles.length; i++) {
        const cycleKey = cycles[i];
        if (cycleKey === 'event') {
            const hasRotation = (allData.event_posters && allData.event_posters.some(p => p.mode_affichage === 'rotation')) ||
                                (allData.event_poster && allData.event_poster.media_path && allData.event_poster.mode_affichage === 'rotation');
            if (hasRotation) {
                active.push(i);
            }
            continue;
        }
        const list = allData[cycleKey];
        if (list && list.length > 0) {
            if (cycleKey === 're' || cycleKey === 'fc') {
                active.push(i);
            } else if (filterCoursesByTime(list, isTomorrowFI).length > 0) {
                active.push(i);
            }
        }
    }
    return active;
}

function getCycleDuration(cycleKey) {
    if (cycleKey === 'fc') return FC_ROTATION_MS;
    if (cycleKey === 'event') {
        const rotationPosters = (allData && allData.event_posters)
            ? allData.event_posters.filter(p => p.mode_affichage === 'rotation')
            : [];
        if (rotationPosters.length > 0) {
            const idx = (currentPosterIndex > 0 ? currentPosterIndex - 1 : rotationPosters.length - 1) % rotationPosters.length;
            const p = rotationPosters[idx];
            if (p && p.duree_affichage_sec) {
                return Math.max(3000, p.duree_affichage_sec * 1000);
            }
        }
        return EVENT_ROTATION_MS;
    }
    return ROTATION_MS;
}

function applyModeFige(poster) {
    if (rotationTimeout) clearTimeout(rotationTimeout);
    if (figeCarouselTimer) clearTimeout(figeCarouselTimer);
    document.body.classList.add('mode-fige');
    showMainContent();

    // Masque les cours
    const yearCols = document.getElementById('year-columns');
    if (yearCols) yearCols.style.display = 'none';
    const noCourses = document.getElementById('no-courses');
    if (noCourses) noCourses.style.display = 'none';

    const figePosters = (allData && allData.event_posters && allData.event_posters.length > 0)
        ? allData.event_posters.filter(p => p.mode_affichage === 'fige' || p.force_active)
        : (poster ? [poster] : []);

    const activeList = figePosters.length > 0 ? figePosters : (poster ? [poster] : []);
    if (activeList.length === 0) return;

    if (currentPosterIndex >= activeList.length) currentPosterIndex = 0;
    const cur = activeList[currentPosterIndex];
    renderPosterElement(cur, activeList.length, currentPosterIndex);

    // Auto-défilement carousel en mode figé si plusieurs affiches
    if (activeList.length > 1) {
        const dur = Math.max(3000, (cur.duree_affichage_sec || 10) * 1000);
        figeCarouselTimer = setTimeout(() => {
            currentPosterIndex = (currentPosterIndex + 1) % activeList.length;
            applyModeFige(poster);
        }, dur);
    }
}

function removeModeFige() {
    if (figeCarouselTimer) {
        clearTimeout(figeCarouselTimer);
        figeCarouselTimer = null;
    }
    if (document.body.classList.contains('mode-fige')) {
        document.body.classList.remove('mode-fige');
        const posterContainer = document.getElementById('event-poster-container');
        if (posterContainer) posterContainer.style.display = 'none';
        if (!rotationTimeout) {
            scheduleNextRotation(500);
        }
    }
}

function stepRotation() {
    const active = getActiveCycleIndices();
    if (active.length === 0) {
        // S'il n'y a pas de visites ou séances programmées : afficher seulement la page d'accueil (splash)
        if (!isShowingSplash) {
            showSplashScreen();
        }
        scheduleNextRotation(SPLASH_MS);
        return;
    }

    if (isShowingSplash) {
        // Fin de l'affichage de la page d'accueil (6 s) -> afficher le 1er cycle actif
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
        // Réafficher la page d'accueil pour 6 secondes
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
            footer.style.display = 'block';
            renderEventTicker(eventText);
        } else {
            lastTickerRawText = '';
            footer.style.display = 'none';
        }

        // Bandeau de date masqué par défaut (géré dynamiquement dans renderCycle selon le cycle)
        const banner = document.getElementById('date-banner');
        if (banner) {
            banner.style.display = 'none';
        }

        // Si aucune séance ni visite n'est programmée, afficher uniquement la page d'accueil (splash)
        const active = getActiveCycleIndices();
        const hasFigePoster = (allData.event_posters && allData.event_posters.some(p => p.mode_affichage === 'fige')) ||
                              (allData.event_poster && allData.event_poster.media_path && allData.event_poster.mode_affichage === 'fige');
        if (active.length === 0 && !hasFigePoster) {
            if (!isShowingSplash) {
                showSplashScreen();
            }
        }

        // ── Gestion du mode Figé (Accueil exclusif avec affiche d'événement toute la journée) ──
        if (hasFigePoster) {
            applyModeFige(allData.event_poster);
            return;
        } else {
            removeModeFige();
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


// ── Formate la durée de retard pour affichage clair dans la pilule ───────────
function formatRetardDuration(raw) {
    if (!raw) return '';
    let s = String(raw).trim();
    if (!s || s === 'nan' || s === 'None') return '';

    // Nettoie d'éventuels préfixes comme "Retard :", "Retard -", "Retard"
    s = s.replace(/^retard\s*[:\-]?\s*/i, '').trim();

    // Si c'est juste un nombre (ex: "15" ou "+15")
    if (/^\+?\d+$/.test(s)) {
        return '+' + s.replace(/^\+/, '') + ' min';
    }

    // Si "15min", "+15min", "15 minutes", "15 mins", "+15 min"
    const m = s.match(/^\+?(\d+)\s*(?:min(?:ute)?s?)?$/i);
    if (m) {
        return '+' + m[1] + ' min';
    }

    if (!s.startsWith('+')) {
        s = '+' + s;
    }
    return s;
}

// ── Construit une pilule de cours ─────────────────────────────────────────────
function buildPill(c, alertClass, salleContent, retard) {
    const div = document.createElement('div');
    div.className = 'course-pill' + (alertClass ? ' ' + alertClass : '');

    const textColor = alertClass ? 'white' : '#0B4F6C';

    const groupeStr = c.groupe || '';
    const gLen = groupeStr.length;
    let modClass = 'mod-normal';
    if (gLen > 22) {
        modClass = 'mod-long';
    } else if (gLen > 11) {
        modClass = 'mod-medium';
    }

    // Calibrage adaptatif de la taille de police de la salle pour couvrir toute l'écriture
    const salleStr = c.salle || '';
    let roomClass = 'room-normal';
    if (salleStr.length > 22) {
        roomClass = 'room-long';
    } else if (salleStr.length > 13) {
        roomClass = 'room-medium';
    }

    // Badge de retard si le cours est retardé
    let retardBadge = '';
    if (retard) {
        const formattedDur = formatRetardDuration(retard.duree);
        const retardText = formattedDur ? `⏳ Retard ${formattedDur}` : '⏳ Retard';
        retardBadge = `<span class="course-retard-badge">${esc(retardText)}</span>`;
    }

    const timeStr = esc(c.h || ((c.hd || '') + (c.hf ? '-' + c.hf : '')));

    div.innerHTML = `
        <div class="course-time" style="color:${textColor};">
            <span class="course-time-val">${timeStr}</span>
            ${retardBadge}
        </div>
        <div class="course-module ${modClass}" style="color:${textColor};">
            ${esc(groupeStr)}
        </div>
        <div class="course-room ${roomClass}" style="color:${textColor};">
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

function filterCoursesByTime(courses, isTomorrow = false) {
    const MORNING_CUTOFF = 12 * 60 + 30; // 12h30

    if (isTomorrow) {
        // ── Règle planning de demain (à partir de 17h30) ──
        // 1. Détecter tous les sous-groupes ayant au moins une séance le matin (< 12h30)
        const morningSubGroups = new Set();
        for (const c of courses) {
            const hdMin = timeToMinutes(c.hd);
            if (hdMin !== null && hdMin < MORNING_CUTOFF) {
                const tokens = (c.groupe || '').trim().split(/\s+/).filter(Boolean);
                for (const t of tokens) {
                    morningSubGroups.add(t.toUpperCase());
                }
            }
        }

        // 2. Afficher les séances du matin pour tous, et les séances de l'après-midi
        // uniquement pour les filières qui n'ont AUCUN cours le matin
        return courses.filter(c => {
            const hdMin = timeToMinutes(c.hd);
            if (hdMin === null) return true;
            if (hdMin < MORNING_CUTOFF) return true;

            const tokens = (c.groupe || '').trim().split(/\s+/).filter(Boolean);
            const hasMorning = tokens.some(t => morningSubGroups.has(t.toUpperCase()));
            return !hasMorning;
        });
    }

    // ── Règle affichage en direct aujourd'hui ──
    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const isMorning = (nowMin < MORNING_CUTOFF); // avant 12h30

    const withoutTime = courses.filter(c => timeToMinutes(c.hd) === null);
    const withTime = courses.filter(c => timeToMinutes(c.hd) !== null);

    let filteredWithTime = [];

    if (isMorning) {
        // Le matin (dès 07h00) : SEULEMENT les séances des filières qui ont cours le matin (< 12h30)
        // Les filières qui n'ont cours que l'après-midi ne s'affichent pas le matin
        const morningCourses = withTime.filter(c => timeToMinutes(c.hd) < MORNING_CUTOFF);

        // 1. Séances du matin actuellement en cours (hd - 30 <= now <= hf)
        const active = morningCourses.filter(c => {
            const hd = timeToMinutes(c.hd);
            const hf = timeToMinutes(c.hf);
            const start = hd - 30;
            const end = hf !== null ? hf : hd + 120;
            return nowMin >= start && nowMin <= end;
        });

        if (active.length > 0) {
            filteredWithTime = active;
        } else {
            // 2. Séances du matin pas encore terminées (end > nowMin)
            const upcoming = morningCourses.filter(c => {
                const hd = timeToMinutes(c.hd);
                const hf = timeToMinutes(c.hf);
                const end = hf !== null ? hf : hd + 120;
                return end > nowMin;
            });
            if (upcoming.length > 0) {
                filteredWithTime = upcoming;
            } else {
                // Fallback : séances du matin terminées
                filteredWithTime = morningCourses;
            }
        }
    } else {
        // Après-midi : séances à partir de 12h30
        const afternoonCourses = withTime.filter(c => timeToMinutes(c.hd) >= MORNING_CUTOFF);

        const active = afternoonCourses.filter(c => {
            const hd = timeToMinutes(c.hd);
            const hf = timeToMinutes(c.hf);
            const start = hd - 30;
            const end = hf !== null ? hf : hd + 120;
            return nowMin >= start && nowMin <= end;
        });

        if (active.length > 0) {
            filteredWithTime = active;
        } else {
            const upcoming = afternoonCourses.filter(c => {
                const hd = timeToMinutes(c.hd);
                const hf = timeToMinutes(c.hf);
                const end = hf !== null ? hf : hd + 120;
                return end > nowMin;
            });
            if (upcoming.length > 0) {
                filteredWithTime = upcoming;
            } else {
                filteredWithTime = afternoonCourses;
            }
        }
    }

    return [...filteredWithTime, ...withoutTime];
}

// ── Pour chaque groupe : garde 1 seule séance selon l'heure actuelle ──────────
// Priorité :
//   - Pour demain : 1ère séance de reprise de la journée
//   - Pour aujourd'hui :
//       1. Séance EN COURS (hd <= now <= hf)         → afficher
//       2. Aucune en cours → PROCHAINE séance (hd > now, la plus tôt)  → afficher
//       3. Tout terminé → la dernière séance terminée → afficher
function deduplicateCoursesByGroup(courses, isTomorrow = false) {
    const now   = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();

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

        if (isTomorrow) {
            // Pour demain : première séance de reprise de la journée pour le groupe
            result.push(sorted[0]);
            continue;
        }

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

    const retard = (allData.retards || []).find(x => matchesGroup(x.groupe));
    if (retard) alertClass = 'alert-orange';
    if ((allData.absences || []).find(x => matchesGroup(x.groupe))) alertClass = 'alert-red';
    return { alertClass, salleContent, retard: (alertClass === 'alert-orange' ? retard : null) };
}


function renderCycle() {
    if (!allData) return;

    const isTomorrowFI = Boolean(allData && allData.is_tomorrow_fi);

    // Si on démarre un nouveau cycle (page 0), on cherche le prochain cycle non-vide
    if (currentCyclePageIndex === 0) {
        let foundCycle = false;
        let attempts = 0;
        while (attempts < cycles.length) {
            const cKey = cycles[currentCycleIndex];
            if (cKey === 'event') {
                if (allData.event_poster && allData.event_poster.media_path && allData.event_poster.mode_affichage === 'rotation') {
                    foundCycle = true;
                    break;
                }
            } else {
                const list = allData[cKey];
                if (list && list.length > 0) {
                    if (cKey === 're' || cKey === 'fc') {
                        foundCycle = true;
                        break;
                    } else if (filterCoursesByTime(list, isTomorrowFI).length > 0) {
                        foundCycle = true;
                        break;
                    }
                }
            }
            currentCycleIndex = (currentCycleIndex + 1) % cycles.length;
            attempts++;
        }

        if (!foundCycle) {
            showSplashScreen();
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
    const posterContainer = document.getElementById('event-poster-container');
    const posterImg = document.getElementById('event-poster-img');
    const legend = document.querySelector('.legend');
    const isFICycle = (cycleKey === 'licence' || cycleKey === 'ingenieur' || cycleKey === 'master');

    // Bandeau de date : affiché uniquement pour les cycles de Formation Initiale quand il s'agit du planning de demain
    const banner = document.getElementById('date-banner');
    if (banner) {
        if (isTomorrowFI && isFICycle) {
            banner.innerText = `Planning de demain — ${allData.date_fi || allData.date_affichee}`;
            banner.style.display = 'inline-block';
        } else {
            banner.style.display = 'none';
        }
    }

    // ── Événement (Affiche d'accueil dans la rotation) ──
    if (cycleKey === 'event') {
        yearColumns.style.display = 'none';
        if (legend) legend.style.display = 'none';

        const rotationPosters = (allData && allData.event_posters && allData.event_posters.length > 0)
            ? allData.event_posters.filter(p => p.mode_affichage === 'rotation')
            : (allData && allData.event_poster ? [allData.event_poster] : []);

        if (rotationPosters.length > 0) {
            if (currentPosterIndex >= rotationPosters.length) currentPosterIndex = 0;
            const cur = rotationPosters[currentPosterIndex];
            renderPosterElement(cur, rotationPosters.length, currentPosterIndex);
            currentPosterIndex = (currentPosterIndex + 1) % rotationPosters.length;
        }
        return 1;
    }

    // Réinitialisation pour les cycles de cours normaux
    if (posterContainer) posterContainer.style.display = 'none';
    if (legend && !document.body.classList.contains('mode-fige')) {
        legend.style.display = 'flex';
    }

    let courses = [];
    if (cycleKey === 're' || cycleKey === 'fc') {
        // Pour RE et FC, les séances programmées pour le jour restent visibles toute la journée.
        // Déduplication uniquement des doublons stricts.
        const raw = allData[cycleKey] || [];
        const seen = new Set();
        courses = raw.filter(c => {
            const sig = `${c.groupe || ''}|${c.module || ''}|${c.salle || ''}|${c.hd || ''}|${c.hf || ''}`;
            if (seen.has(sig)) return false;
            seen.add(sig);
            return true;
        });
    } else {
        courses = deduplicateCoursesByGroup(filterCoursesByTime(allData[cycleKey] || [], isTomorrowFI), isTomorrowFI);
    }

    let totalPages = 1;
    currentCycleTotalPages = 1;

    // ── RE et FC : cartes libres, centrées verticalement & horizontalement ──
    if (cycleKey === 're' || cycleKey === 'fc') {
        yearColumns.classList.add('fc-mode');
        gridHeader.innerHTML = '';
        gridHeader.style.display = 'none';

        const isRe = (cycleKey === 're');
        const maxPerPage = isRe ? 6 : 8;
        totalPages = Math.max(1, Math.ceil(courses.length / maxPerPage));
        currentCycleTotalPages = totalPages;
        if (currentCyclePageIndex >= totalPages) {
            currentCyclePageIndex = 0;
        }

        const baseTitle = cycleNames[cycleKey];
        if (totalPages > 1) {
            document.getElementById('current-cycle').innerHTML = `${baseTitle} <span class="page-badge">(${currentCyclePageIndex + 1}/${totalPages})</span>`;
        } else {
            document.getElementById('current-cycle').innerText = baseTitle;
        }

        const sortedCourses = [...courses]
            .sort((a, b) => (a.hd || '99:99').localeCompare(b.hd || '99:99') || (a.groupe || '').localeCompare(b.groupe || ''));
        const start = currentCyclePageIndex * maxPerPage;
        const pageCourses = sortedCourses.slice(start, start + maxPerPage);

        const flat = document.createElement('div');
        let gridClass = isRe ? 'grid-re' : 'grid-fc';
        if (isRe) {
            if (pageCourses.length === 1) gridClass += ' re-cols-1';
            else if (pageCourses.length >= 5) gridClass += ' re-cols-3';
            else gridClass += ' re-cols-2';
        }
        flat.className = 'flat-cards ' + gridClass;

        pageCourses.forEach(c => {
            const { alertClass, retard } = getAlert(c);
            const div = document.createElement('div');
            div.className = 'course-pill flat-card ' + (isRe ? 'card-re' : 'card-fc') + (alertClass ? ' ' + alertClass : '');
            const horaire = c.h || ((c.hd || '') + (c.hf ? '-' + c.hf : ''));
            let retardBadge = '';
            if (retard) {
                const formattedDur = formatRetardDuration(retard.duree);
                const retardText = formattedDur ? `⏳ Retard ${formattedDur}` : '⏳ Retard';
                retardBadge = ` <span class="course-retard-badge">${esc(retardText)}</span>`;
            }
            div.innerHTML = `
                ${horaire ? `<div class="flat-time">${esc(horaire)}${retardBadge}</div>` : ''}
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
                    const hA = (a.hd || '00:00').localeCompare(b.hd || '00:00');
                    if (hA !== 0) return hA;
                    const fA = (a.filiere || 'AUTRE').localeCompare(b.filiere || 'AUTRE');
                    if (fA !== 0) return fA;
                    return (a.groupe || '').localeCompare(b.groupe || '');
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
                const { alertClass, salleContent, retard } = getAlert(c);
                cell.appendChild(buildPill(c, alertClass, salleContent, retard));
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

// ── Détection automatique de changement d'écran ou projection ──────────────────
let resizeDebounce = null;
function handleDisplayChange() {
    clearTimeout(resizeDebounce);
    resizeDebounce = setTimeout(() => {
        updateClock();
        if (!isShowingSplash && allData) {
            renderCycle();
        }
        if (!isShowingSplash && lastTickerRawText) {
            renderEventTicker(lastTickerRawText, true);
        }
    }, 150);
}

window.addEventListener('resize', handleDisplayChange);
window.addEventListener('orientationchange', handleDisplayChange);
document.addEventListener('fullscreenchange', handleDisplayChange);

// Raccourci projection : double-clic ou touche F pour basculer en plein écran
document.addEventListener('dblclick', () => {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
    } else {
        document.exitFullscreen().catch(() => {});
    }
});

document.addEventListener('keydown', (e) => {
    if ((e.key === 'f' || e.key === 'F') && !e.ctrlKey && !e.altKey && !e.metaKey) {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen().catch(() => {});
        } else {
            document.exitFullscreen().catch(() => {});
        }
    }
});

