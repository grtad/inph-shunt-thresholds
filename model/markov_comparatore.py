"""Markov del comparatore (iNPH non operato), L per contesto, K con morte
competitiva, frontiera s*(q) = (K - lambda q)/L e controlli di validazione.

Input in armonizzazione.py, che resta l'unica fonte dei costi unitari, delle tariffe e
delle soglie. Output: L_comparatore.csv, frontiera.csv, validazione.csv nella stessa
cartella. Uso: python3 model/markov_comparatore.py
"""
import csv
import math
from pathlib import Path

import numpy as np
from scipy.linalg import expm
from scipy.optimize import brentq

from armonizzazione import (STATI, PPP, GIORNI_RESIDENZA, P_REV_ANNO1, P_REV_ANNI_SUCC,
                            costo_annuo_per_mrs)

QUI = Path(__file__).parent
LIVELLI = ["0-2", "3", "4", "5"]

# Coorte: eta' 75 (SHQR, media 74,4 all'intervento, Sundstrom 2022), uomini 60,3 %
ETA0 = 75
QUOTA_M = 0.603

# Mortalita': HR rispetto alla popolazione. Operati 1,81 (Andren 2020, SHQR); non
# trattati = operati x rinvio 2,57 (1,13-5,83) (Andren 2021): composizione
# moltiplicativa, assunzione dichiarata.
HR_OPERATI = 1.81
HR_RINVIO = {"base": 2.57, "basso": 1.13, "alto": 5.83}

# Andren 2014 (tesi Andren 2020, p. 47): rinviati mRS <=2 dal 55 % al 39 % e mRS 5
# da 0 al 15 % in 13,2 mesi mediani, fra vivi (tutti operati dopo l'attesa).
T_ATTESA = 13.2 / 12
A_DIAGNOSI, A_ATTESA, D_ATTESA = 0.55, 0.39, 0.15

# Ripartizione di mRS 3-4 alla diagnosi: non in fonti aperte; caso base 2:1, sensibilita' 1:1 e 1:2
RIPARTIZIONI_3_4 = {"2:1": (2 / 3, 1 / 3), "1:1": (0.5, 0.5), "1:2": (1 / 3, 2 / 3)}

# Profilo della demenza (Tullberg 2018, proxy Socialstyrelsen: 42 % in residenza)
# espresso come mix di mRS che con i giorni di Lekander 2017 da' il 42 % dell'anno
# in residenza: 0/25/30/45 -> 0,25x0,110 + 0,30x0,214 + 0,45x0,726 = 0,419.
MIX_DEMENZA = np.array([0.0, 0.25, 0.30, 0.45])
ANNI_CONVERGENZA = (2, 5)  # dal 2o anno pieno al 5o, lineare (assunzione)

ORIZZONTI = {"5 anni": 5, "10 anni": 10, "vita intera": 30}

# Tetto del guadagno annuo di utilita' (Andersson 2024: 0,86 - 0,79): moltiplicato per
# gli anni di vita scontati del comparatore da' un QALY di riferimento di sola qualita'
# di vita, senza guadagno di sopravvivenza.
TETTO_UTILITA = 0.07

# Controllo esterno dei costi svedesi: unita' di Lekander 2017 (KPB 2016: 440 SEK/ora,
# 1.749 SEK/giorno) x CP13303 e CP13302 SE 2016->2025 (1,6139)
SE_LEKANDER = dict(ora_tot=440 * 1.6139, giorno_tot=1749 * 1.6139)


# ---------- mortalita' di fondo ----------

def leggi_tavole():
    tav = {}
    with open(QUI / "tavole_mortalita_2024.csv") as f:
        for r in csv.DictReader(f):
            if r["eta"].endswith("+"):
                continue
            tav.setdefault((r["stato"], r["sesso"]), {})[int(r["eta"])] = float(r["qx"])
    # oltre i 94 anni: Gompertz sulle eta' 85-94
    for chiave, q in tav.items():
        x = np.arange(85, 95)
        mu = -np.log(1 - np.array([q[e] for e in x]))
        b, a = np.polyfit(x, np.log(mu), 1)
        for e in range(95, ETA0 + 41):
            q[e] = 1 - math.exp(-math.exp(a + b * e))
    return tav


def q_con_hr(q, hr):
    """Probabilita' annua di morte con rapporto di rischio sull'azzardo."""
    return 1 - (1 - q) ** hr


# ---------- traiettoria di dipendenza ----------

def generatore(r, j):
    """Azzardo di peggioramento r da ogni stato vivo; una quota j salta diretta a mRS 5."""
    Q = np.zeros((4, 4))
    for i in (0, 1):
        Q[i, i + 1] = r * (1 - j)
        Q[i, 3] = r * j
    Q[2, 3] = r
    np.fill_diagonal(Q, -Q.sum(axis=1))
    return Q


def calibra(mix0):
    """r dalla discesa di mRS 0-2, j dall'arrivo a mRS 5 (Andren 2014)."""
    r = math.log(A_DIAGNOSI / A_ATTESA) / T_ATTESA
    d = lambda j: (mix0 @ expm(generatore(r, j) * T_ATTESA))[3] - D_ATTESA
    if d(0.0) >= 0:
        return r, 0.0
    return r, brentq(d, 0.0, 1.0)


def mix_iniziale(nome_rip, scenario_base):
    a3, a4 = RIPARTIZIONI_3_4[nome_rip]
    if scenario_base == "tutti":
        return np.array([A_DIAGNOSI, 0.45 * a3, 0.45 * a4, 0.0])
    if scenario_base == "mRS 0-2":
        return np.array([1.0, 0.0, 0.0, 0.0])
    return np.array([0.0, a3, a4, 0.0])  # mRS >=3


# ---------- coorte ----------

def coorte(stato, tav, P, mix0, anni, traiettoria, hr):
    """Occupazione degli stati di mRS fra i vivi, inizio di ogni ciclo, coorte mista per sesso.
    Restituisce array (anni+1, 4) di quote della coorte iniziale."""
    occ = np.zeros((anni + 1, 4))
    for sesso, peso in (("M", QUOTA_M), ("F", 1 - QUOTA_M)):
        x = mix0 * peso
        occ[0] += x
        for t in range(anni):
            qx = q_con_hr(tav[(stato, sesso)][ETA0 + t], hr)
            x = x * (1 - qx)
            if traiettoria == "plateau" and t >= 1:
                pass
            else:
                x = x @ P
            occ[t + 1] += x
    if traiettoria == "demenza":
        a0, a1 = ANNI_CONVERGENZA
        for t in range(1, anni + 1):
            w = min(max((t - a0 + 1) / (a1 - a0 + 1), 0.0), 1.0)
            vivi = occ[t].sum()
            occ[t] = (1 - w) * occ[t] + w * vivi * MIX_DEMENZA
    return occ


def spesa_scontata(occ, costi, r, anni):
    """Correzione di meta' ciclo (media fra inizio e fine), primo anno non scontato."""
    tot = 0.0
    for t in range(anni):
        medio = (occ[t] + occ[t + 1]) / 2
        tot += (medio @ costi) / (1 + r) ** t
    return tot


def K_con_morte_competitiva(s, tav, stato, anni, f_rev=1.0, p_rev=None):
    """Tariffa + revisioni attese fra i vivi del braccio operato (HR 1,81), scontate.
    f_rev riscala la probabilita' di revisione (sensibilita'); p_rev = (primo anno,
    anni successivi) sostituisce le reoperazioni di Andren 2018 (sensibilita' sui pazienti con almeno una reoperazione)."""
    p1, p2 = p_rev or (P_REV_ANNO1, P_REV_ANNI_SUCC)
    vivi, tot = 1.0, s["tariffa"]
    for t in range(anni):
        p = f_rev * (p1 if t == 0 else p2)
        tot += vivi * p * s["revisione"] / (1 + s["sconto"]) ** t
        qx = sum(peso * q_con_hr(tav[(stato, sx)][ETA0 + t], HR_OPERATI)
                 for sx, peso in (("M", QUOTA_M), ("F", 1 - QUOTA_M)))
        vivi *= 1 - qx
    return tot


# ---------- analisi ----------

def main():
    tav = leggi_tavole()
    righe_L, righe_fr, righe_val = [], [], []

    calib = {}
    for nome in RIPARTIZIONI_3_4:
        mix0 = mix_iniziale(nome, "tutti")
        r, j = calibra(mix0)
        calib[nome] = (r, j, expm(generatore(r, j)))
        print(f"Calibrazione {nome}: r {r:.3f}/anno, j {j:.3f}; P annua\n{np.round(calib[nome][2], 3)}")

    # varianti: (traiettoria, ripartizione, base di dipendenza, hr rinvio, sconto 3 %)
    varianti = [("continua", "2:1", "tutti", "base", False),
                ("plateau", "2:1", "tutti", "base", False),
                ("demenza", "2:1", "tutti", "base", False),
                ("continua", "1:1", "tutti", "base", False),
                ("continua", "1:2", "tutti", "base", False),
                ("continua", "2:1", "mRS 0-2", "base", False),
                ("continua", "2:1", "mRS >=3", "base", False),
                ("continua", "2:1", "tutti", "basso", False),
                ("continua", "2:1", "tutti", "alto", False),
                ("continua", "2:1", "tutti", "base", True),
                ("plateau", "2:1", "mRS 0-2", "base", False),
                ("demenza", "2:1", "mRS >=3", "base", False)]

    for st, s in STATI.items():
        for traj, rip, base, hrk, sc3 in varianti:
            P = calib[rip][2]
            mix0 = mix_iniziale(rip, base)
            hr = HR_OPERATI * HR_RINVIO[hrk]
            r = 0.03 if sc3 else s["sconto"]
            for nome_o, anni in ORIZZONTI.items():
                occ = coorte(st, tav, P, mix0, anni, traj, hr)
                ss = dict(s, sconto=r)
                K = K_con_morte_competitiva(ss, tav, st, anni)
                for prosp in ("pubblica", "totale"):
                    c = costo_annuo_per_mrs(s, prosp)
                    if any(v is None for v in c.values()):
                        continue
                    L = spesa_scontata(occ, np.array([c[k] for k in LIVELLI]), r, anni)
                    riga = dict(stato=st, valuta=s["valuta"], prospettiva=prosp, orizzonte=nome_o,
                                traiettoria=traj, ripartizione_3_4=rip, base_dipendenza=base,
                                hr_rinvio=hrk, sconto=r, K=round(K), L=round(L),
                                L_eur_pps=round(L / PPP[st]), s_dom=round(K / L, 3))
                    righe_L.append(riga)
                    r_esiti = 0.03 if sc3 else s.get("sconto_esiti", s["sconto"])  # Polonia: 3,5 % sugli esiti
                    anni_vita = spesa_scontata(occ, np.ones(4), r_esiti, anni)
                    if nome_o == "10 anni" and base == "tutti" and rip == "2:1" and hrk == "base" and not sc3:
                        for nome_l, lam in s["soglie"].items():
                            righe_fr.append(dict(stato=st, prospettiva=prosp, traiettoria=traj,
                                                 soglia=nome_l, lambda_=lam, K=round(K), L=round(L),
                                                 s_dom=round(K / L, 3), q_star=round(K / lam, 3),
                                                 anni_vita_scontati=round(anni_vita, 2),
                                                 q_rif=round(TETTO_UTILITA * anni_vita, 3),
                                                 s_a_q_rif=round((K - lam * TETTO_UTILITA * anni_vita) / L, 3),
                                                 s_a_q_0_25=round((K - lam * 0.25) / L, 3),
                                                 s_a_q_0_5=round((K - lam * 0.5) / L, 3)))

    # validazione: costi svedesi con le unita' di Lekander rivalutate
    s_se = dict(STATI["SE"], **SE_LEKANDER)
    for traj in ("continua", "plateau"):
        occ = coorte("SE", tav, calib["2:1"][2], mix_iniziale("2:1", "tutti"), 10, traj,
                     HR_OPERATI * HR_RINVIO["base"])
        c = costo_annuo_per_mrs(s_se, "pubblica")
        L = spesa_scontata(occ, np.array([c[k] for k in LIVELLI]), s_se["sconto"], 10)
        K = K_con_morte_competitiva(s_se, tav, "SE", 10)
        righe_val.append(dict(controllo=f"SE s_dom 10 anni, costi unitari Lekander x CP1330x ({traj})",
                              stato="SE", hr_rinvio="base", modello=round(K / L, 3),
                              riferimento="caso con 923 SEK/ora e 3.084 SEK/giorno (frontiera.csv)"))

    # validazione: mortalita' e residenza alla diagnosi
    for st in STATI:
        for hrk in HR_RINVIO:
            hr = HR_OPERATI * HR_RINVIO[hrk]
            vivi = {}
            for sx, peso in (("M", QUOTA_M), ("F", 1 - QUOTA_M)):
                for eta0, anni in ((76, 4), (75, 5)):
                    v = 1.0
                    for t in range(anni):
                        v *= 1 - q_con_hr(tav[(st, sx)][eta0 + t], hr)
                    vivi[(eta0, anni)] = vivi.get((eta0, anni), 0) + peso * v
            righe_val.append(dict(controllo="mortalita' a 4 anni da 76 anni", stato=st, hr_rinvio=hrk,
                                  modello=round(1 - vivi[(76, 4)], 3),
                                  riferimento="0,394 rinviati poi operati (Andren 2021); limite inferiore"))
            righe_val.append(dict(controllo="mortalita' a 5 anni da 75 anni", stato=st, hr_rinvio=hrk,
                                  modello=round(1 - vivi[(75, 5)], 3),
                                  riferimento="0,875 iNPH probabile di popolazione, n=24 (Jaraj 2017, abstract)"))
    for rip in RIPARTIZIONI_3_4:
        mix0 = mix_iniziale(rip, "tutti")
        res = sum(mix0[i] * GIORNI_RESIDENZA[k] / 365 for i, k in enumerate(LIVELLI))
        righe_val.append(dict(controllo="quota dell'anno in residenza alla diagnosi", stato="tutti",
                              hr_rinvio="", modello=round(res, 3),
                              riferimento="0,033 (1/30, IC esatto 0,001-0,172; Tullberg 2018)"))

    # traccia del comparatore: vivi, mRS fra i vivi e quota
    # dell'anno in residenza fra i vivi, caso base (2:1, tutti, HR base), per Stato e traiettoria
    righe_tr = []
    gres = np.array([GIORNI_RESIDENZA[k] / 365 for k in LIVELLI])
    for st in STATI:
        for traj in ("continua", "plateau"):
            occ = coorte(st, tav, calib["2:1"][2], mix_iniziale("2:1", "tutti"), 10, traj,
                         HR_OPERATI * HR_RINVIO["base"])
            for t in (0, 1, 2, 5, 10):
                vivi = occ[t].sum()
                quote = occ[t] / vivi
                righe_tr.append(dict(stato=st, traiettoria=traj, anno=t, vivi=round(vivi, 4),
                                     **{f"mrs_{k}": round(q, 4) for k, q in zip(LIVELLI, quote)},
                                     residenza=round(float(quote @ gres), 4)))

    for nome, righe in (("L_comparatore.csv", righe_L), ("frontiera.csv", righe_fr),
                        ("validazione.csv", righe_val), ("traccia_comparatore.csv", righe_tr)):
        with open(QUI / nome, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(righe[0]))
            w.writeheader(); w.writerows(righe)

    print("\nFrontiera, 10 anni, mix 2:1, tutti i livelli di dipendenza")
    for r in righe_fr:
        print(r)
    print("\nValidazione")
    for r in righe_val:
        print(r)


if __name__ == "__main__":
    main()
