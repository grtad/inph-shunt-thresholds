"""Sensibilita' a una via (tornado di s_dom e q*), probabilistica su K e sui
costi per stato di L, stima di s con il solo guadagno di sopravvivenza, figure.

Input da armonizzazione.py, Markov da markov_comparatore.py (unica fonte di entrambi).
Output: sensibilita_una_via.csv, probabilistica.csv, sopravvivenza.csv in questa
cartella; figure in ../figures/ (PDF e PNG a 300 dpi, testi in inglese).
Uso: python3 model/fase4_sensibilita.py
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import expm

from armonizzazione import (STATI, PPP, ORE_DOMICILIO, GIORNI_RESIDENZA, P_REV_PAZIENTI,
                            costo_annuo_per_mrs)
from markov_comparatore import (LIVELLI, HR_OPERATI, HR_RINVIO, ORIZZONTI, RIPARTIZIONI_3_4,
                                leggi_tavole, calibra, generatore, mix_iniziale, coorte,
                                spesa_scontata, K_con_morte_competitiva)
import ancore_ricalcolate

QUI = Path(__file__).parent
FIG = QUI.parent / "figures"
N_PSA, SEME = 10000, 20261007

NOMI = {"SE": "Sweden", "DE": "Germany", "FR": "France", "ES": "Spain", "PL": "Poland",
        "EE": "Estonia", "NO": "Norway", "IE": "Ireland", "UK": "England", "DK": "Denmark",
        "NL": "Netherlands", "PT": "Portugal", "LV": "Latvia", "CZ": "Czechia", "SK": "Slovakia",
        "BG": "Bulgaria", "CH": "Switzerland", "AT": "Austria", "FI": "Finland", "LT": "Lithuania",
        "SI": "Slovenia"}
# Disegno delle figure per 21 Stati: nel testo una figura
# di sintesi di tutti gli Stati (fig1_sintesi); mappe e tornado di tutti gli Stati nel supplemento,
# in pagine (figS_mappe_*, figS_tornado_*), Stati ordinati per s_dom di caso base.
STATI_PER_MAPPA, PAGINE_TORNADO = 8, 6
STATI_PER_PANNELLO_Q = 3  # figS1_q_star_lambda: piccoli pannelli

# Caso base: progressione continua, 10 anni, prospettiva pubblica,
# mRS 3:4 = 2:1, HR del rinvio 2,57, sconto ufficiale.
BASE = dict(traiettoria="continua", rip="2:1", base="tutti", hrk="base", anni=10,
            prosp="pubblica", sconto=None, f_rev=1.0, f_rev_costo=1.0, f_ora=1.0,
            f_giorno=1.0, f_vol=1.0, tariffa=None, revisione=None, p_rev=None, voci=None)

# Tariffa indice dei cinque Stati originali, intervallo per Stato: None = valore base.
# SE prezzi regionali Södra (Sus 128.760, altri 118.184); DE B20D 2026 senza quota
# infermieristica (8.154) e 2025 con quota (10.374); FR GHS 26 (base) e GHS 27, livello 2
# (10.996); ES SOI 1 (7.913,56 2024 x CP063) e media (base); PL punto JGP 1,00 zl per
# intervento e revisione.
TARIFFA_INT = {"SE": (dict(tariffa=118184), dict(tariffa=128760)),
               "DE": (dict(tariffa=8154), dict(tariffa=10374)),
               "FR": (dict(), dict(tariffa=10996.38)),
               "ES": (dict(tariffa=7913.56 / 0.9774), dict()),
               "PL": (dict(tariffa=16539 * 1.00, revisione=11959 * 1.00), dict())}
TARIFFA_ETICHETTE = {"SE": ("118,184", "128,760"), "DE": ("8,154", "10,374"),
                     "FR": ("level 1", "level 2"), "ES": ("SOI 1", "mean"), "PL": ("1.00 zł/pt", "1.96")}


def V(**campi):
    """Alternativa che sostituisce uno o piu' campi di STATI insieme (prima dei fattori f_*)."""
    return dict(voci=campi)


ORE_SE = 34.77 * 12  # ore annue per utente svedese per PT e BG
# Sensibilita' dichiarate per Stato (dettaglio nelle Tabelle supplementari S1 e S2 dell'articolo).
# (etichetta, kw basso, kw alto, etichetta basso, etichetta alto, tocca K); dict() = valore base.
# Per le alternative multiple di un solo parametro, che agisce in modo monotono, si tengono
# il minimo e il massimo letti (i valori intermedi stanno dentro la barra).
SENS_STATO = {
    "DE": [("Revision DRG", V(revisione=1.482 * 4394.22), dict(), "B18C", "B18B", True)],
    "EE": [("Index DRG tariff (payment rule)", V(tariffa=4653.69), V(tariffa=10484.63),
            "4,654", "10,485", True),
           ("Home-care public share", dict(), V(quota_pub_dom=1 - 2.1 / 18.2),
            "0.840 (KOV)", "0.885", False),
           ("Residential public share", V(quota_pub_res=88 / 189), dict(),
            "0.466 (STAR list)", "0.546 (spend)", False)],
    "NO": [("Revision DRG", V(revisione=1.772 * 54412), dict(), "443 (T85.0)", "1D", True),
           ("Hourly home-care cost (source)", V(ora_tot=406.9), V(ora_tot=1100.1),
            "406.9", "1,100.1", False),
           ("Daily residential cost (source)", V(giorno_tot=5017.6), dict(),
            "5,017.6", "5,545", False)],
    "IE": [("Index DRG tariff (complexity)", dict(), V(tariffa=60007), "B02C", "B02A", True),
           ("Hourly home-care cost (source)", V(ora_tot=28.10), V(ora_tot=32.49),
            "28.10", "32.49", False)],
    "UK": [("Index HRG tariff", V(tariffa=2527), V(tariffa=10388),
            "AA54C", "AA52D non-elective", True),
           ("Revision HRG", V(revisione=2527), V(revisione=8406), "AA54C", "AA51D", True),
           ("Hourly home-care cost (source)", dict(), V(ora_tot=30 * 167.3 / 159.075),
            "ASC-FR", "PSSRU", False),
           ("Residential cost without FNC", V(giorno_tot=152.87, quota_pub_res=0.7135 * (1 - 0.489)),
            dict(), "without FNC", "with FNC", False),
           ("Public shares (self-funders)", dict(), V(quota_pub_dom=0.7652, quota_pub_res=0.7329),
            "whole population", "council-funded only", False)],
    "DK": [("Hourly home-care cost (source)", V(ora_tot=656.4 * 100 / 95.35),
            V(ora_tot=846.2 * 100 / 95.35), "656.4 (2024)", "846.2 (2024)", False),
           ("Daily residential cost (source)", V(giorno_tot=2000.0),
            V(giorno_tot=2189.9 * 100 / 91.93), "2,000.0 (2025)", "2,189.9 (2024)", False)],
    "NL": [("Index DBC tariff", V(tariffa=8285), V(tariffa=12312.24), "8,285", "12,312", True),
           ("Revision DBC tariff", V(revisione=6260), V(revisione=11490.93), "6,260", "11,491", True),
           ("Home-care public share", dict(), V(quota_pub_dom=1.0), "0.983 (Wlz)", "1.0 (Zvw)", False)],
    "PT": [("Index DRG tariff (SOI)", dict(), V(tariffa=23423.96), "SOI 1", "SOI 4", True),
           ("Hours per home-care user", V(ora_pub=362.49 * 12 / (ORE_SE * 1.5)),
            V(ora_pub=362.49 * 12 / (ORE_SE * 0.5)), "+50% (6.95/h)", "-50% (20.85/h)", False),
           ("Residential public share (dependency supplement)", dict(), V(quota_pub_res=0.500),
            "0.409", "0.500", False),
           ("Residential setting (RNCCI)", dict(), V(giorno_tot=85.48, quota_pub_res=0.477),
            "ERPI", "RNCCI ULDM", False)],
    "LV": [("Index DRG tariff and revision", V(tariffa=2.5118 * 1307.73, revisione=2.5118 * 1307.73),
            V(tariffa=2.5118 * 1432.47, revisione=2.5118 * 1432.47), "3,285", "3,598", True),
           ("Public hourly amount", V(ora_pub=8.12), V(ora_pub=8.20), "8.12", "8.20", False),
           ("Residential public share", dict(), V(quota_pub_res=0.4272), "0.408", "0.427", False),
           ("Daily residential cost (spend / days)", V(giorno_tot=36.91), dict(),
            "36.91", "37.18", False)],
    "CZ": [("Hourly home-care cost (method)", V(ora_tot=631.5), dict(), "631.5 (staff)", "800.4 (CSU)", False),
           ("Residential public share (care allowance)", V(quota_pub_res=1 - 21720622 / 44542407.382),
            dict(), "private (0.512)", "public (0.720)", False)],
    "SK": [("Index DRG tariff and revision (base rate)", V(tariffa=7297.9, revisione=4668.5),
            V(tariffa=8369.3, revisione=5353.9), "group 1", "group 4", True),
           ("Residential public share", V(quota_pub_res=0.588), dict(), "0.588", "0.632", False)],
    "BG": [("Revision without valve", V(revisione=3590 / 1.95583), dict(), "without", "with valve", True),
           ("Valve at full price", V(tariffa=(3590 + 3000) / 1.95583), V(tariffa=(3590 + 4500) / 1.95583),
            "3,000 lv", "4,500 lv", True),
           ("Hours per home-care user", V(ora_pub=8096 / 1.95583 / (ORE_SE * 1.5)),
            V(ora_pub=8096 / 1.95583 / (ORE_SE * 0.5)), "+50%", "-50%", False)],
    "CH": [("Base rate (tariff and revision)", V(tariffa=1.627 * 9940, revisione=1.627 * 9940),
            V(tariffa=1.627 * 11267, revisione=1.627 * 11267), "9,940", "11,267", True),
           ("Revision DRG", V(revisione=1.372 * 10549.25), dict(), "B09D", "B09C", True),
           ("Hourly home-care cost (source)", V(ora_tot=109.89), V(ora_tot=120.75),
            "109.89", "120.75", False),
           ("Residential public share (EL as public)", dict(), V(quota_pub_res=0.602),
            "0.397", "0.602", False)],
    "AT": [("LKF point value", V(tariffa=14604 * 1.61, revisione=7964 * 1.61),
            V(tariffa=14604 * 2.41, revisione=7964 * 2.41), "1.61", "2.41", True),
           ("LKF point, national derivation", V(tariffa=14604 * 1.7604, revisione=7964 * 1.7604),
            dict(), "1.76", "1.80", True)],
    "FI": [("Index tariff (KYS list)", V(tariffa=7700, revisione=7700), dict(), "7,700", "10,505", True),
           ("Hourly home-care cost (source)", V(ora_tot=123.2), V(ora_tot=138.9),
            "123.2", "138.9", False),
           ("Public shares (2024)", V(quota_pub_dom=0.8155, quota_pub_res=0.7845), dict(),
            "2024", "2025", False)],
    "LT": [("Insertion DRG", V(tariffa=1483.80), dict(), "B07B", "B02C", True),
           ("Home-care public share", V(quota_pub_dom=0.8), dict(), "0.8", "1.0", False),
           ("Residential cost and share (other pair)",
            V(giorno_tot=1750.34 * 12 / 365, quota_pub_res=1169 / 1750.34), dict(),
            "57.55 / 0.668", "61.35 / 0.627", False)],
    "SI": [("Insertion DRG", V(tariffa=1.14 * 1912.17), dict(), "B07B", "B02C", True),
           ("Residential DO payment period", dict(),
            V(giorno_tot=51.80 + 29.73 + 738.49 * 12 / 365,
              quota_pub_res=(51.80 + 29.73) / (51.80 + 29.73 + 738.49 * 12 / 365)),
            "Apr-Jul", "Dec-Jul", False),
           ("Residential without ZZZS nursing",
            V(giorno_tot=41.59 + 738.49 * 12 / 365, quota_pub_res=41.59 / (41.59 + 738.49 * 12 / 365)),
            dict(), "without", "with", False)],
}
# Soglia alternativa per gli Stati con una sola soglia
SOGLIA_ALT = {"LV": (66000, "3 x GDP pc 2024")}

# Revisioni: quota di pazienti revisionati a 10 anni, 26 % (Andren 2018) contro 14 % con valvole
# regolabili e 30 % con valvole fisse (Oksa 2026, Kuopio; Oksa da' solo quote di pazienti). K conta
# le reoperazioni: i rapporti 0,14/0,26 e 0,30/0,26 si applicano al tasso di reoperazioni, cioe'
# reoperazioni per paziente revisionato fisse a 410/257 = 1,6 (ipotesi). P_REV_10 resta la quota
# di pazienti, solo denominatore.
# Costo della revisione: +/-50 % (assunzione).
P_REV_10 = 0.26

# Probabilistica (assunzioni dichiarate): gamma con CV 20 % sulla tariffa, 25 % sul costo
# della revisione e sui costi unitari (ora, giorno), 20 % sui volumi di Lekander per mRS
# (indipendenti fra livelli); beta(257, 722) sulla quota di revisionati (Andren 2018,
# 257/979), applicata come fattore relativo (/0,26) al tasso di reoperazioni (come sopra).
CV = dict(tariffa=0.20, revisione=0.25, ora=0.25, giorno=0.25, volume=0.20)
BETA_REV = (257, 979 - 257)

# Utilita' del non trattato per il QALY della sola sopravvivenza: Tinelli 2021 (0,45),
# Tullberg 2018 (0,57, base), Andersson 2024 (0,79, iNPH di popolazione).
UTILITA = {"0.45": 0.45, "0.57": 0.57, "0.79": 0.79}

# Ancore: i tre modelli pubblicati ricalcolati sul comparatore (ancore_ricalcolate.py);
# sulla mappa la s netta, la lorda solo in tabella.
ANCORE = ["Tullberg (2018)", "Tinelli (2021)", "Taddei (2026)"]
S_MIN, S_MAX, Q_MAX = -1.0, 1.25, 3.2  # limite dichiarato della frontiera estesa


# ---------- modello ----------

def prepara():
    tav = leggi_tavole()
    P = {}
    for rip in RIPARTIZIONI_3_4:
        r, j = calibra(mix_iniziale(rip, "tutti"))
        P[rip] = expm(generatore(r, j))
    return tav, P


def scala(d, f):
    return {k: v * f for k, v in d.items()}


def stato_mod(st, o):
    s = dict(STATI[st])
    if o["voci"]:
        s.update(o["voci"])
    for k in ("tariffa", "revisione"):
        if o[k] is not None:
            s[k] = o[k]
    s["revisione"] *= o["f_rev_costo"]
    if o["sconto"] is not None:
        s["sconto"] = o["sconto"]
    for k in ("ora_tot", "ora_pub"):
        if s.get(k):
            s[k] *= o["f_ora"]
    for k in ("giorno_tot", "giorno_pub"):
        if s.get(k):
            s[k] *= o["f_giorno"]
    return s


def costi(s, prosp, f_vol=1.0):
    c = costo_annuo_per_mrs(s, prosp, scala(ORE_DOMICILIO, f_vol), scala(GIORNI_RESIDENZA, f_vol))
    if any(v is None for v in c.values()):
        return None
    return np.array([c[k] for k in LIVELLI])


def caso(st, tav, P, **kw):
    """K e L del comparatore per uno Stato, con le modifiche al caso base in kw."""
    o = dict(BASE, **kw)
    s = stato_mod(st, o)
    c = costi(s, o["prosp"], o["f_vol"])
    if c is None:
        return None
    occ = coorte(st, tav, P[o["rip"]], mix_iniziale(o["rip"], o["base"]), o["anni"],
                 o["traiettoria"], HR_OPERATI * HR_RINVIO[o["hrk"]])
    L = spesa_scontata(occ, c, s["sconto"], o["anni"])
    K = K_con_morte_competitiva(s, tav, st, o["anni"], o["f_rev"], o["p_rev"])
    return K, L


def voci_tornado(st):
    """(etichetta, kw basso, kw alto, etichetta basso, etichetta alto, tocca K)"""
    v = [("Index DRG tariff", *TARIFFA_INT[st], *TARIFFA_ETICHETTE[st], True)] if st in TARIFFA_INT else []
    v += SENS_STATO.get(st, [])
    v += [("Share revised at 10 y", dict(f_rev=0.14 / P_REV_10), dict(f_rev=0.30 / P_REV_10),
          "14%", "30%", True),
         ("Revisions counted", dict(), dict(p_rev=P_REV_PAZIENTI), "reoperations", "patients", True),
         ("Revision cost", dict(f_rev_costo=0.5), dict(f_rev_costo=1.5), "-50%", "+50%", True),
         ("Time horizon", dict(anni=5), dict(anni=ORIZZONTI["vita intera"]), "5 y", "lifetime", True),
         ("Discount rate (common)", dict(sconto=0.0), dict(sconto=0.05), "0%", "5%", True),
         ("Course after year 1", dict(traiettoria="plateau"), dict(traiettoria="demenza"),
          "plateau", "dementia mix", False),
         ("mRS 3:4 at diagnosis", dict(rip="1:1"), dict(rip="1:2"), "1:1", "1:2", False),
         ("Mortality HR, untreated", dict(hrk="basso"), dict(hrk="alto"), "x1.13", "x5.83", False),
         ("Hourly home-care cost", dict(f_ora=0.75), dict(f_ora=1.25), "-25%", "+25%", False),
         ("Daily residential cost", dict(f_giorno=0.75), dict(f_giorno=1.25), "-25%", "+25%", False),
         ("Care volumes (Lekander)", dict(f_vol=0.5), dict(f_vol=1.5), "x0.5", "x1.5", False)]
    if costi(STATI[st], "totale") is not None:  # prospettiva totale calcolabile
        v.append(("Perspective", dict(), dict(prosp="totale"), "public", "total", False))
    return v


# ---------- analisi ----------

def una_via(tav, P):
    righe = []
    for st, s in STATI.items():
        K0, L0 = caso(st, tav, P)
        lam = min(s["soglie"].values())
        righe.append(dict(stato=st, voce="base", alternativa="", K=round(K0), L=round(L0),
                          s_dom=round(K0 / L0, 4), q_star_lambda_min=round(K0 / lam, 4),
                          tocca_K=""))
        for nome, kl, kh, el, eh, tk in voci_tornado(st):
            for kw, et in ((kl, el), (kh, eh)):
                K, L = caso(st, tav, P, **kw)
                righe.append(dict(stato=st, voce=nome, alternativa=et, K=round(K), L=round(L),
                                  s_dom=round(K / L, 4), q_star_lambda_min=round(K / lam, 4),
                                  tocca_K=tk))
        if len(s["soglie"]) > 1:
            lmax = max(s["soglie"].values())
            righe.append(dict(stato=st, voce="Threshold (declared range)", alternativa="upper",
                              K=round(K0), L=round(L0), s_dom=round(K0 / L0, 4),
                              q_star_lambda_min=round(K0 / lmax, 4), tocca_K="lambda"))
        if st in SOGLIA_ALT:
            lam_alt, et = SOGLIA_ALT[st]
            righe.append(dict(stato=st, voce="Threshold (alternative)", alternativa=et,
                              K=round(K0), L=round(L0), s_dom=round(K0 / L0, 4),
                              q_star_lambda_min=round(K0 / lam_alt, 4), tocca_K="lambda"))
    return righe


def gamma(rng, media, cv, n):
    k = 1 / cv ** 2
    return rng.gamma(k, media / k, n)


def probabilistica(tav, P):
    rng = np.random.default_rng(SEME)
    righe = []
    for st, s0 in STATI.items():
        o = dict(BASE)
        r = s0["sconto"]
        occ = coorte(st, tav, P["2:1"], mix_iniziale("2:1", "tutti"), 10, "continua",
                     HR_OPERATI * HR_RINVIO["base"])
        # K lineare nella tariffa, nel costo e nella probabilita' di revisione
        K0 = K_con_morte_competitiva(s0, tav, st, 10)
        B = (K0 - s0["tariffa"]) / s0["revisione"]
        tar = gamma(rng, s0["tariffa"], CV["tariffa"], N_PSA)
        rev = gamma(rng, s0["revisione"], CV["revisione"], N_PSA)
        prev = rng.beta(*BETA_REV, N_PSA) / P_REV_10
        K = tar + rev * prev * B
        f_ora = gamma(rng, 1, CV["ora"], N_PSA)
        f_gio = gamma(rng, 1, CV["giorno"], N_PSA)
        f_vol = gamma(rng, 1, CV["volume"], (N_PSA, 4))
        L = np.empty(N_PSA)
        for i in range(N_PSA):
            s = stato_mod(st, dict(o, f_ora=f_ora[i], f_giorno=f_gio[i]))
            ore = {k: ORE_DOMICILIO[k] * f_vol[i, n] for n, k in enumerate(LIVELLI)}
            gio = {k: GIORNI_RESIDENZA[k] * f_vol[i, n] for n, k in enumerate(LIVELLI)}
            c = costo_annuo_per_mrs(s, "pubblica", ore, gio)
            L[i] = spesa_scontata(occ, np.array([c[k] for k in LIVELLI]), r, 10)
        sd = K / L
        pc = lambda x: np.percentile(x, [50, 2.5, 97.5])
        m, a, b = pc(sd)
        righe.append(dict(stato=st, grandezza="s_dom", soglia="", mediana=round(m, 4),
                          p2_5=round(a, 4), p97_5=round(b, 4)))
        for nome, lam in s0["soglie"].items():
            m, a, b = pc(K / lam)
            righe.append(dict(stato=st, grandezza="q_star", soglia=nome, mediana=round(m, 4),
                              p2_5=round(a, 4), p97_5=round(b, 4)))
    return righe


def sopravvivenza(tav, P):
    """s quando lo shunt allunga la vita (HR 1,81 degli operati) senza cambiare la
    dipendenza, e quando ferma la progressione con la stessa sopravvivenza."""
    righe = []
    varianti = [("base", "continua", "2:1", "base"), ("HR rinvio basso", "continua", "2:1", "basso"),
                ("HR rinvio alto", "continua", "2:1", "alto"), ("plateau", "plateau", "2:1", "base"),
                ("mRS 3:4 = 1:2", "continua", "1:2", "base")]
    for st, s in STATI.items():
        c = costi(s, "pubblica")
        r = s["sconto"]
        re = s.get("sconto_esiti", r)
        K = K_con_morte_competitiva(s, tav, st, 10)
        for nome, traj, rip, hrk in varianti:
            mix = mix_iniziale(rip, "tutti")
            oc = coorte(st, tav, P[rip], mix, 10, traj, HR_OPERATI * HR_RINVIO[hrk])
            osv = coorte(st, tav, P[rip], mix, 10, traj, HR_OPERATI)
            oar = coorte(st, tav, np.eye(4), mix, 10, "continua", HR_OPERATI)
            Lc, Ls, La = (spesa_scontata(x, c, r, 10) for x in (oc, osv, oar))
            dly = spesa_scontata(osv, np.ones(4), re, 10) - spesa_scontata(oc, np.ones(4), re, 10)
            riga = dict(stato=st, variante=nome, L=round(Lc), s_sopravvivenza=round((Lc - Ls) / Lc, 4),
                        s_arresto=round((Lc - La) / Lc, 4), anni_vita_guadagnati=round(dly, 3),
                        s_dom=round(K / Lc, 4))
            for nu, u in UTILITA.items():
                q = u * dly
                riga[f"q_u{nu}"] = round(q, 3)
                riga[f"icer_u{nu}"] = round((K + Ls - Lc) / q) if q > 0 else None
            righe.append(riga)
    return righe


def griglia(tav, P):
    """s_dom su traiettoria x HR del rinvio x volumi di Lekander,
    tutte le combinazioni (incertezza strutturale come analisi principale)."""
    righe = []
    for st in STATI:
        for traj in ("continua", "plateau"):
            for hrk in ("basso", "base", "alto"):
                for fv in (0.5, 1.0, 1.5):
                    K, L = caso(st, tav, P, traiettoria=traj, hrk=hrk, f_vol=fv)
                    righe.append(dict(stato=st, traiettoria=traj, hr_rinvio=hrk, volumi=fv,
                                      K=round(K), L=round(L), s_dom=round(K / L, 4)))
    return righe


# ---------- figure ----------

BLU = {"chiaro": "#5598e7", "scuro": "#184f95"}
ARANCIO, ACQUA, GRIGIO, INCHIOSTRO, TESTO2 = "#eb6834", "#1baf7a", "#f0efec", "#0b0b0b", "#52514e"
MARKER_ANCORE = ["D", "s", "o"]
# tre tinte per i pannelli della figura S1 (il verde ha
# contrasto < 3:1, quindi ogni pannello ha la legenda con i nomi degli Stati)
SERIE = ["#2a78d6", "#eb6834", "#1baf7a"]


def stile():
    plt.rcParams.update({"font.family": "sans-serif",
                         "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
                         "font.size": 8, "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8,
                         "axes.labelcolor": INCHIOSTRO, "xtick.color": TESTO2, "ytick.color": TESTO2,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.color": "#e6e5e0", "grid.linewidth": 0.6,
                         "legend.frameon": False, "savefig.dpi": 300})


def salva(fig, nome):
    FIG.mkdir(exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{nome}.{ext}", bbox_inches="tight")
    plt.close(fig)


def fmt(x):
    return f"{x:,.0f}"


def figura_mappe(tav, P, sopr, anc, stati, file_fig):
    righe_fig = (len(stati) + 1 + 2) // 3  # Stati piu' il pannello di legenda, tre colonne
    fig, assi = plt.subplots(righe_fig, 3, figsize=(7.5, 2.8 * righe_fig), sharex=True, sharey=True)
    for ax in assi.flat[len(stati) + 1:]:
        ax.axis("off")
    for ax, st in zip(assi.flat, stati):
        s = STATI[st]
        K, L = caso(st, tav, P)
        q = np.linspace(0, Q_MAX, 200)
        ax.axhspan(1, S_MAX, color=GRIGIO, lw=0, zorder=0)
        ax.axhline(0, color="#9a9890", lw=0.8, zorder=1)
        soglie = sorted(s["soglie"].values())
        # una tinta per soglia, dalla piu' chiara (soglia bassa) alla piu' scura; fino a tre soglie (NO, NL, LT)
        tinte = {1: (BLU["scuro"],), 2: (BLU["chiaro"], BLU["scuro"]),
                 3: ("#a9cbf2", BLU["chiaro"], BLU["scuro"])}[len(soglie)]
        for lam, col in zip(soglie, tinte):
            ax.plot(q, (K - lam * q) / L, color=col, lw=2, solid_capstyle="round", zorder=3,
                    label=f"λ = {fmt(lam)}")
        ax.plot(0, K / L, "o", ms=6, color=BLU["scuro"], mec="white", mew=1.5, zorder=5)
        r = next(x for x in sopr if x["stato"] == st and x["variante"] == "base")
        ax.annotate(f"$s_{{dom}}$ {K / L:.3f}", (0, K / L), xytext=(10, 4),
                    textcoords="offset points", fontsize=7, color=INCHIOSTRO)
        # ancore pubblicate, ricalcolate sul comparatore
        for nome, mk in zip(ANCORE, MARKER_ANCORE):
            a = next(x for x in anc if x["stato"] == st and x["ancora"] == nome)
            ax.plot(a["q"], a["s_netta"], mk, ms=5.5, color=ARANCIO, mec="white", mew=1.2, zorder=6)
        # stima del modello: sola sopravvivenza (l'arresto della progressione resta nel
        # testo)
        ax.plot([r["q_u0.45"], r["q_u0.79"]], [r["s_sopravvivenza"]] * 2, color=ACQUA, lw=2,
                solid_capstyle="round", zorder=4)
        ax.plot(r["q_u0.57"], r["s_sopravvivenza"], "o", ms=6, color=ACQUA, mec="white", mew=1.5,
                zorder=5)
        ax.set_title(f"{NOMI[st]} ({s['valuta']})", fontsize=8.5, loc="left", fontweight="bold")
        ax.set_xlim(0, Q_MAX)
        ax.set_ylim(S_MIN, S_MAX)
        ax.legend(loc="upper right", bbox_to_anchor=(1.0, 0.86), fontsize=6.5, handlelength=1.5)
    for i, ax in enumerate(assi.flat[:len(stati)]):
        ax.tick_params(labelbottom=True)
        if i >= len(stati) - 3:
            ax.set_xlabel("Incremental QALYs, q")
    for ax in assi[:, 0]:
        ax.set_ylabel("Share of comparator\ncare cost avoided, s")
    # pannello di legenda
    leg = assi.flat[len(stati)]
    leg.cla()
    leg.axis("off")
    voci = [("line", BLU["scuro"], "Break-even frontier s*(q) = (K − λq)/L;\nshunt cost-effective above the line"),
            ("o", BLU["scuro"], "$s_{dom}$ = K/L: dominance at q = 0"),
            ("D", ARANCIO, "Tullberg (2018)"),
            ("s", ARANCIO, "Tinelli (2021)"),
            ("o", ARANCIO, "Taddei (2026)"),
            ("note", ARANCIO, "published assumptions re-run on the\ncomparator, care in life-years gained counted"),
            ("seg", ACQUA, "Survival gain only (operated HR 1.81);\nbar: utility 0.45–0.79, dot 0.57"),
            ("box", GRIGIO, "s > 1: more care avoided than\nthe comparator consumes")]
    y = 0.97
    for tipo, col, testo in voci:
        if tipo == "line":
            leg.plot([0.02, 0.12], [y, y], color=col, lw=2, transform=leg.transAxes)
        elif tipo in ("seg", "hline"):
            leg.plot([0.02, 0.12], [y, y], color=col, lw=2 if tipo == "seg" else 1.2,
                     transform=leg.transAxes)
            if tipo == "seg":
                leg.plot(0.07, y, "o", ms=6, color=col, mec="white", mew=1.5, transform=leg.transAxes)
        elif tipo == "note":
            pass
        elif tipo == "box":
            leg.add_patch(plt.Rectangle((0.02, y - 0.025), 0.10, 0.05, color=col,
                                        transform=leg.transAxes))
        else:
            leg.plot(0.07, y, tipo, ms=6, color=col, mec="white", mew=1.2, transform=leg.transAxes)
        leg.text(0.17, y, testo, transform=leg.transAxes, va="center", fontsize=6.8, color=INCHIOSTRO)
        y -= 0.115 if "\n" in testo else 0.09
    fig.text(0.0, -0.02, "Base case: 10-year horizon, public payer perspective, continuing progression, "
             "national discount rates. λ in national currency per QALY.", fontsize=6.5, color=TESTO2)
    fig.tight_layout()
    salva(fig, file_fig)


# Etichette dei tornado: dal CSV arrivano con sigle nazionali; qui si traducono in inglese piano
# solo per la figura (il CSV non cambia). Sigle di cui il supplemento non dice il significato
# sono lasciate: KOV, Wlz, CSU, ASC-FR, DO.
TRAD = {
    "Index tariff (KYS list)": "Index tariff (regional list price)",
    "LKF point value": "Tariff, point value of five hospitals (euros per point)",
    "LKF point, national derivation": "Tariff, point value, national derivation",
    "0.466 (STAR list)": "0.466 (from price list)",
    "1.0 (Zvw)": "1.0 (fully public)",
    "ERPI": "care home",
    "RNCCI ULDM": "long-term care network unit",
    "Residential setting (RNCCI)": "Residential setting",
    "631.5 (staff)": "631.5 (staff cost)",
    "PSSRU": "PSSRU unit costs",
    "with FNC": "with nursing-care payment",
    "without FNC": "without nursing-care payment",
    "Residential cost without FNC": "Residential cost without nursing-care payment",
    "SOI 1": "severity 1",
    "SOI 4": "severity 4",
    "Index DRG tariff (SOI)": "Index DRG tariff (severity level)",
    "private (0.512)": "allowance counted as private (0.512)",
    "public (0.720)": "allowance counted as public (0.720)",
    "Residential public share (EL as public)": "Residential public share (supplementary benefits as public)",
    "Residential without ZZZS nursing": "Residential cost without insurance-fund nursing payment",
    "Mortality HR, untreated": "Hazard ratio of delay",
    "x1.13": "HR of delay 1.13",
    "x5.83": "HR of delay 5.83",
    "Threshold (declared range)": "Threshold used",
    "Threshold (alternative)": "Threshold used (alternative)",
}


def T(s):
    return TRAD.get(s, s)


def figura_tornado(righe, stati, nome):
    n_barre = [len({r["voce"] for r in righe if r["stato"] == st}) for st in stati]
    fig, assi = plt.subplots(len(stati), 2, figsize=(7.5, sum(0.13 * n + 0.6 for n in n_barre)),
                             gridspec_kw=dict(width_ratios=[1.35, 1], height_ratios=n_barre),
                             squeeze=False)
    for i, st in enumerate(stati):
        rr = [r for r in righe if r["stato"] == st]
        base = rr[0]
        for j, (col, nome_ax) in enumerate((("s_dom", "$s_{dom}$ = K/L"),
                                            ("q_star_lambda_min", "q* at the lower threshold used"))):
            ax = assi[i, j]
            voci = {}
            for r in rr[1:]:
                if col == "q_star_lambda_min" and not r["tocca_K"]:
                    continue
                if col == "s_dom" and r["tocca_K"] == "lambda":
                    continue
                voci.setdefault(r["voce"], []).append((r["alternativa"], r[col]))
            if col == "q_star_lambda_min" and "Threshold (declared range)" in voci:
                v = voci.pop("Threshold (declared range)")
                voci["Threshold (declared range)"] = [("lower", base[col]), v[0]]
            ordine = sorted(voci, key=lambda k: abs(voci[k][0][1] - voci[k][-1][1]))
            b0 = base[col]
            for y, k in enumerate(ordine):
                (ea, va), (eb, vb) = voci[k][0], voci[k][-1]
                lo, hi = min(va, vb, b0), max(va, vb, b0)
                ax.barh(y, hi - lo, left=lo, height=0.55, color=BLU["chiaro"], lw=0, zorder=3)
                et = [(T(e), v) for e, v in ((ea, va), (eb, vb)) if abs(v - b0) > 1e-9]
                if len(et) == 2 and (et[0][1] > b0) == (et[1][1] > b0):
                    # stesso lato: un'unica etichetta all'estremo, dal piu' vicino al piu' lontano
                    et.sort(key=lambda x: abs(x[1] - b0))
                    et = [(f"{et[0][0]}, {et[1][0]}", et[1][1])]
                for e, v in et:
                    dx = 3 if v > b0 else -3
                    ax.annotate(e, (v, y), xytext=(dx, 0), textcoords="offset points",
                                ha="left" if v > b0 else "right", va="center", fontsize=6,
                                color=TESTO2)
            ax.axvline(b0, color=INCHIOSTRO, lw=1, zorder=4)
            ax.set_yticks(range(len(ordine)))
            ax.set_yticklabels([T(k) for k in ordine], fontsize=6.5)
            ax.grid(axis="y", visible=False)
            ax.tick_params(axis="x", labelsize=6.5)
            xs = [v for k in ordine for _, v in voci[k]] + [b0]
            pad = (max(xs) - min(xs)) * 0.30
            ax.set_xlim(min(xs) - 2.2 * pad, max(xs) + pad)
            titolo = f"{NOMI[st]} ({STATI[st]['valuta']}): {nome_ax}" if j == 0 else nome_ax
            ax.set_title(f"{titolo} (base {b0:.3f})", fontsize=7.5, loc="left",
                         fontweight="bold" if j == 0 else "normal")
    fig.tight_layout(h_pad=1.2)
    salva(fig, nome)


def figura_sintesi(uv, psa):
    """Tutti gli Stati, ordinati per s_dom di caso base: punto = caso base, barra spessa =
    intervallo al 95 % della probabilistica, linea sottile = estremi delle analisi a una via.
    A destra q* = K/lambda alla soglia piu' bassa dichiarata, con la stessa codifica."""
    base = {r["stato"]: r for r in uv if r["voce"] == "base"}
    ordine = sorted(base, key=lambda st: base[st]["s_dom"])[::-1]  # il piu' basso in alto
    fig, assi = plt.subplots(1, 2, figsize=(7.5, 5.6), sharey=True)
    for j, (col, titolo) in enumerate((("s_dom", "$s_{dom}$ = K/L: share of comparator care cost\n"
                                         "the shunt must avoid to be dominant"),
                                        ("q_star_lambda_min", "q* = K/λ at the lower threshold used:\n"
                                         "QALYs needed with no care avoided"))):
        ax = assi[j]
        for y, st in enumerate(ordine):
            uv_st = [r for r in uv if r["stato"] == st and r["voce"] != "base"]
            if col == "s_dom":
                vv = [r[col] for r in uv_st if r["tocca_K"] != "lambda"]
                pr = next(r for r in psa if r["stato"] == st and r["grandezza"] == "s_dom")
            else:
                vv = [r[col] for r in uv_st if r["tocca_K"]]
                lam_min = min(STATI[st]["soglie"], key=STATI[st]["soglie"].get)
                pr = next(r for r in psa if r["stato"] == st and r["grandezza"] == "q_star"
                          and r["soglia"] == lam_min)
            b0 = base[st][col]
            ax.plot([min(vv + [b0]), max(vv + [b0])], [y, y], color="#9a9890", lw=1,
                    solid_capstyle="round", zorder=2)
            ax.plot([pr["p2_5"], pr["p97_5"]], [y, y], color=BLU["chiaro"], lw=4,
                    solid_capstyle="round", zorder=3)
            ax.plot(b0, y, "o", ms=5.5, color=BLU["scuro"], mec="white", mew=1.2, zorder=4)
        ax.set_yticks(range(len(ordine)))
        ax.set_yticklabels([f"{NOMI[st]} ({STATI[st]['valuta']})" for st in ordine], fontsize=7)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(left=0)
        ax.set_title(titolo, fontsize=7.5, loc="left")
        ax.tick_params(axis="x", labelsize=7)
    assi[0].set_xlabel("$s_{dom}$")
    assi[1].set_xlabel("q* (QALYs)")
    from matplotlib.lines import Line2D
    maniglie = [Line2D([], [], marker="o", ls="", ms=5.5, color=BLU["scuro"], mec="white", mew=1.2),
                Line2D([], [], color=BLU["chiaro"], lw=4),
                Line2D([], [], color="#9a9890", lw=1)]
    fig.legend(maniglie, ["Base case", "Probabilistic analysis, 95% interval",
                          "Range across one-way analyses"],
               loc="lower center", ncol=3, fontsize=7, bbox_to_anchor=(0.5, -0.04))
    fig.text(0.0, -0.08, "Base case: 10-year horizon, public payer perspective, continuing progression, "
             "national discount rates. Countries ordered by base-case $s_{dom}$.", fontsize=6.5, color=TESTO2)
    fig.tight_layout()
    salva(fig, "fig1_sintesi")


def figura_q_lambda(tav, P, ordine):
    """q* = K/lambda contro lambda in euro PPS, per confrontare gli Stati sulla stessa scala di
    soglie; piccoli pannelli di tre Stati nell'ordine della sintesi, soglie dichiarate come punti."""
    gruppi = [ordine[i:i + STATI_PER_PANNELLO_Q] for i in range(0, len(ordine), STATI_PER_PANNELLO_Q)]
    n_righe = (len(gruppi) + 1) // 2
    fig, assi = plt.subplots(n_righe, 2, figsize=(7.5, 2.3 * n_righe), sharex=True, sharey=True)
    lam = np.linspace(15000, 200000, 400)
    for ax in assi.flat[len(gruppi):]:
        ax.axis("off")
    for k, (ax, gruppo) in enumerate(zip(assi.flat, gruppi)):
        for st, col, tratto, marc in zip(gruppo, SERIE, ("-", (0, (5, 2)), (0, (1, 1.5))), ("o", "s", "^")):
            K, _ = caso(st, tav, P)
            kp = K / PPP[st]
            ax.plot(lam / 1000, kp / lam, color=col, lw=2, ls=tratto, zorder=3, label=NOMI[st])
            for l in STATI[st]["soglie"].values():
                lp = l / PPP[st]
                if lam[0] <= lp <= lam[-1]:
                    ax.plot(lp / 1000, kp / lp, marc, ms=6, color=col, mec="white", mew=1.5, zorder=4)
        ax.legend(loc="upper right", fontsize=7, handlelength=1.5)
        ax.set_ylim(0, 1.8)
        ax.set_xlim(15, 200)
        ax.tick_params(labelbottom=True, labelsize=7)
        if k % 2 == 0:
            ax.set_ylabel("q* = K/λ (QALYs)", fontsize=7.5)
        if k >= len(gruppi) - 2:
            ax.set_xlabel("λ (thousand PPS-adjusted euros per QALY, 2025)", fontsize=7.5)
    fig.text(0.0, -0.01, "Dots: thresholds used (declared or 1 and 3 times GDP per capita). Base case K (10 years, revisions with competing "
             "mortality). Panels follow the order of Figure 1 (base-case $s_{dom}$). In the first panel the curves of Finland, Sweden "
             "and the Netherlands coincide (K in PPS almost identical).", fontsize=6.5, color=TESTO2)
    fig.tight_layout()
    salva(fig, "figS1_q_star_lambda")


# ---------- main ----------

def scrivi(nome, righe):
    with open(QUI / nome, "w", newline="") as f:
        campi = list(dict.fromkeys(k for r in righe for k in r))
        w = csv.DictWriter(f, fieldnames=campi)
        w.writeheader()
        w.writerows(righe)


def main():
    tav, P = prepara()
    # controllo: il caso base riproduce frontiera.csv
    attesi = {"SE": 0.037, "DE": 0.094, "FR": 0.057, "ES": 0.208, "PL": 0.284}
    for st, v in attesi.items():
        K, L = caso(st, tav, P)
        assert round(K / L, 3) == v, (st, K / L)

    uv = una_via(tav, P)
    sopr = sopravvivenza(tav, P)
    psa = probabilistica(tav, P)
    scrivi("sensibilita_una_via.csv", uv)
    scrivi("sopravvivenza.csv", sopr)
    scrivi("probabilistica.csv", psa)
    gr = griglia(tav, P)
    scrivi("griglia_strutturale.csv", gr)

    anc = ancore_ricalcolate.main()
    stile()
    ordine = sorted(STATI, key=lambda st: next(r["s_dom"] for r in uv
                                               if r["stato"] == st and r["voce"] == "base"))
    figura_sintesi(uv, psa)
    for n, i in enumerate(range(0, len(ordine), STATI_PER_MAPPA), 1):
        figura_mappe(tav, P, sopr, anc, ordine[i:i + STATI_PER_MAPPA], f"figS_mappe_{n}")
    for n, pagina in enumerate(np.array_split(ordine, PAGINE_TORNADO), 1):
        figura_tornado(uv, list(pagina), f"figS_tornado_{n}")
    figura_q_lambda(tav, P, ordine)

    for nome, righe in (("Una via", uv), ("Sopravvivenza", sopr), ("Probabilistica", psa)):
        print(f"\n{nome}")
        for r in righe:
            print(r)


if __name__ == "__main__":
    main()
