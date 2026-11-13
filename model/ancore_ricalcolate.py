"""Le ancore pubblicate ricalcolate sul comparatore del modello,
cosi' che la loro s sia una quota di L come la frontiera.

Ogni modello pubblicato entra come meccanismo applicato alla stessa coorte (caso base:
10 anni, prospettiva pubblica, progressione continua, mRS 3:4 = 2:1, HR del rinvio 2,57)
e con la stessa mortalita' (operati HR 1,81, non trattati 4,65): le ancore differiscono
solo per l'ipotesi sulla dipendenza e sull'utilita'. Output: ancore_ricalcolate.csv.
Uso: python3 model/ancore_ricalcolate.py
"""
import csv
from pathlib import Path

import numpy as np
from scipy.linalg import expm

from armonizzazione import STATI, costo_annuo_per_mrs
from markov_comparatore import (LIVELLI, HR_OPERATI, HR_RINVIO, leggi_tavole, calibra,
                                generatore, mix_iniziale, coorte, K_con_morte_competitiva)

QUI = Path(__file__).parent
ANNI = 10

# Tullberg 2018 (Table 1): primo anno migliorato 0,73, complicanza 0,15,
# peggiorato 0,10 (normalizzati fra i vivi); poi dal migliorato complicanza 0,02/anno e
# peggioramento 0,10/anno, dalla complicanza miglioramento 0,70 (il resto peggiora).
# Utilita': migliorato 0,71; complicanza, peggiorato e non trattato 0,57.
# Il profilo di assistenza degli operati (7 % in residenza a 6 mesi) coincide con il mix
# della diagnosi del modello (6,6-8,2 %): il migliorato costa come il mix della diagnosi,
# tenuto fermo; complicanza e peggiorato costano come il comparatore allo stesso anno.
TU_ANNO1 = np.array([0.73, 0.15, 0.10]) / 0.98
TU_U_MIGL, TU_U_ALTRI = 0.71, 0.57

# Tinelli 2021 (Appendici 1 e 2): successo 70 %, insuccesso "come non trattato";
# nei riusciti i livelli di assistenza arrivano due anni dopo che nei non trattati.
# Utilita' 0,62 (shunt) e 0,45 (non shunt).
TI_SUCCESSO, TI_RITARDO, TI_U_SHUNT, TI_U_NON = 0.70, 2, 0.62, 0.45

# Taddei 2026: un anno di assistenza evitato, letto come un anno di ritardo della
# dipendenza; q preso da Tullberg 2018, quindi qui il q di Tullberg ricalcolato.
TA_RITARDO = 1


def scontata(v, r):
    """Correzione di meta' ciclo e primo anno non scontato, come spesa_scontata."""
    return sum((v[t] + v[t + 1]) / 2 / (1 + r) ** t for t in range(ANNI))


def profili(st, tav, P, hrk="base", traiettoria="continua"):
    s = STATI[st]
    c = costo_annuo_per_mrs(s, "pubblica")
    c = np.array([c[k] for k in LIVELLI])
    mix0 = mix_iniziale("2:1", "tutti")
    occ = coorte(st, tav, P, mix0, ANNI, traiettoria, HR_OPERATI * HR_RINVIO[hrk])
    vivi_c = occ.sum(axis=1)
    pc_c = (occ @ c) / vivi_c                      # assistenza per vivo del comparatore
    vivi_o = coorte(st, tav, np.eye(4), mix0, ANNI, "continua", HR_OPERATI).sum(axis=1)
    return s, c, mix0, vivi_c, pc_c, vivi_o


def tullberg_quote():
    """Quote fra i vivi di migliorato, complicanza, peggiorato all'inizio di ogni ciclo."""
    q = np.zeros((ANNI + 1, 3))
    q[0] = (1, 0, 0)  # alla diagnosi: tutti col mix della diagnosi
    q[1] = TU_ANNO1
    for t in range(1, ANNI):
        m, k, d = q[t]
        q[t + 1] = (m * (1 - 0.02 - 0.10) + k * 0.70, m * 0.02, d + m * 0.10 + k * 0.30)
    return q


def ritardato(pc, anni):
    return np.array([pc[max(t - anni, 0)] for t in range(ANNI + 1)])


def ancore(st, tav, P, hrk="base", traiettoria="continua", ti_ritardo=TI_RITARDO):
    """Le tre ancore per uno Stato; i parametri non di default sono gli scenari di sensibilita'."""
    righe = []
    s, c, mix0, vivi_c, pc_c, vivi_o = profili(st, tav, P, hrk, traiettoria)
    r, re = s["sconto"], s.get("sconto_esiti", s["sconto"])
    K = K_con_morte_competitiva(s, tav, st, ANNI)
    L = scontata(vivi_c * pc_c, r)
    c0 = mix0 @ c

    tq = tullberg_quote()
    pc_tu = tq[:, 0] * c0 + (tq[:, 1] + tq[:, 2]) * pc_c
    u_tu = tq[:, 0] * TU_U_MIGL + (tq[:, 1] + tq[:, 2]) * TU_U_ALTRI
    q_tu = scontata(vivi_o * u_tu, re) - scontata(vivi_c * TU_U_ALTRI, re)

    pc_ti = TI_SUCCESSO * ritardato(pc_c, ti_ritardo) + (1 - TI_SUCCESSO) * pc_c
    u_ti = TI_SUCCESSO * TI_U_SHUNT + (1 - TI_SUCCESSO) * TI_U_NON
    q_ti = scontata(vivi_o * u_ti, re) - scontata(vivi_c * TI_U_NON, re)

    pc_ta = ritardato(pc_c, TA_RITARDO)

    for nome, pc_o, q in (("Tullberg (2018)", pc_tu, q_tu), ("Tinelli (2021)", pc_ti, q_ti),
                          ("Taddei (2026)", pc_ta, q_tu)):
        netta = (L - scontata(vivi_o * pc_o, r)) / L      # assistenza negli anni guadagnati contata
        lorda = (L - scontata(vivi_c * pc_o, r)) / L      # stessa dipendenza, sopravvivenza ignorata
        riga = dict(stato=st, ancora=nome, K=round(K), L=round(L), s_dom=round(K / L, 4),
                    q=round(q, 3), s_netta=round(netta, 4), s_lorda=round(lorda, 4),
                    icer_netto=round((K - netta * L) / q), icer_lordo=round((K - lorda * L) / q))
        for nome_l, lam in s["soglie"].items():
            riga[f"margine_{nome_l}"] = round(netta - (K - lam * q) / L, 3)
        righe.append(riga)
    return righe


# Scenari di sensibilita': mortalita' del rinvio 1,13 e 5,83 e plateau per le tre ancore; Tinelli
# con ritardo uniforme di 1 anno accanto ai 2 del caso base, perche' il calendario dell'Appendix 2
# cade fra i due.
SCENARI = [("base", "continua"), ("basso", "continua"), ("alto", "continua"), ("base", "plateau")]


def scenari(tav, P):
    righe = []
    for st in STATI:
        for hrk, traj in SCENARI:
            for rit in (1, 2):
                for r in ancore(st, tav, P, hrk, traj, rit):
                    if rit == 1 and r["ancora"] != "Tinelli (2021)":
                        continue
                    righe.append(dict(hr_rinvio=hrk, traiettoria=traj,
                                      ritardo_tinelli=rit if r["ancora"] == "Tinelli (2021)" else "", **r))
    campi = list(dict.fromkeys(k for x in righe for k in x))
    with open(QUI / "ancore_scenari.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campi)
        w.writeheader()
        w.writerows(righe)
    return righe


def main():
    tav = leggi_tavole()
    P = expm(generatore(*calibra(mix_iniziale("2:1", "tutti"))))
    righe = [r for st in STATI for r in ancore(st, tav, P)]
    scenari(tav, P)

    campi = list(dict.fromkeys(k for x in righe for k in x))
    with open(QUI / "ancore_ricalcolate.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campi)
        w.writeheader()
        w.writerows(righe)
    for x in righe:
        print({k: v for k, v in x.items() if not k.startswith("margine")},
              [v for k, v in x.items() if k.startswith("margine")])
    return righe


if __name__ == "__main__":
    main()
