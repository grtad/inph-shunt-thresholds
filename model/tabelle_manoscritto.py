"""Tabelle e fatti del manoscritto, generati dai CSV del modello.

Unica origine dei numeri delle tabelle e della prosa del manoscritto e del suo supplemento:
scrive tabelle_manoscritto.md (tabelle in inglese pronte da incollare, poi i fatti per la prosa).
Non ricalcola il modello: legge soltanto i CSV scritti dagli altri script.
"""
from pathlib import Path
import itertools
import pandas as pd

import armonizzazione as A

QUI = Path(__file__).parent
OUT = QUI / "tabelle_manoscritto.md"

NOME = {"SE": "Sweden", "DE": "Germany", "FR": "France", "ES": "Spain", "PL": "Poland",
        "EE": "Estonia", "NO": "Norway", "IE": "Ireland", "UK": "England (UK)", "DK": "Denmark",
        "NL": "Netherlands", "PT": "Portugal", "LV": "Latvia", "CZ": "Czechia", "SK": "Slovakia",
        "BG": "Bulgaria", "CH": "Switzerland", "AT": "Austria", "FI": "Finland", "LT": "Lithuania",
        "SI": "Slovenia"}
VAL = {"SEK": "SEK", "EUR": "€", "PLN": "zł", "NOK": "NOK", "GBP": "£", "DKK": "DKK",
       "CZK": "CZK", "CHF": "CHF"}
# Soglie in inglese, nell'ordine di STATI[...]["soglie"]
SOGLIA_EN = {
    "SE": "high severity class (reference range)", "DE": "1 and 3 × GDP per capita",
    "FR": "1 and 3 × GDP per capita", "ES": "empirical estimate", "PL": "statutory (3 × GDP per capita)",
    "EE": "Health Insurance Fund, usual and upper", "NO": "opportunity cost and severity steps",
    "IE": "HIQA, lower and upper reference", "UK": "NICE range", "DK": "1 and 3 × GDP per capita",
    "NL": "burden-of-disease classes", "PT": "1 and 3 × GDP per capita",
    "LV": "statutory (3 × GDP per capita)", "CZ": "SÚKL, applied", "SK": "statutory (2 and 3 × GDP per capita)",
    "BG": "1 and 3 × GDP per capita", "CH": "1 and 3 × GDP per capita", "AT": "1 and 3 × GDP per capita",
    "FI": "1 and 3 × GDP per capita", "LT": "1, 3 and 5 × GDP per capita", "SI": "1 and 3 × GDP per capita",
}


def n(x, d=0):
    """Numero in stile inglese con separatore delle migliaia e segno meno tipografico."""
    s = f"{x:,.{d}f}"
    return s.replace("-", "−")


def f3(x):
    return n(x, 3)


def rng(vals, fmt=f3, sep=" to "):
    vals = list(vals)
    lo, hi = min(vals), max(vals)
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)}{sep}{fmt(hi)}"


def carica():
    d = {}
    for nome in ["frontiera", "L_comparatore", "griglia_strutturale", "probabilistica", "sopravvivenza",
                 "ancore_ricalcolate", "ancore_scenari", "sensibilita_una_via", "validazione",
                 "input_armonizzati", "traccia_comparatore"]:
        d[nome] = pd.read_csv(QUI / f"{nome}.csv")
    return d


def main():
    d = carica()
    F = d["frontiera"]
    righe = []
    w = righe.append

    base = F[(F.prospettiva == "pubblica") & (F.traiettoria == "continua")]
    plat = F[(F.prospettiva == "pubblica") & (F.traiettoria == "plateau")]
    tot = F[(F.prospettiva == "totale") & (F.traiettoria == "continua")]
    sdom = base.groupby("stato").s_dom.first().sort_values(kind="stable")
    ordine = list(sdom.index)

    # ---------------- Table 1: inputs ----------------
    I = d["input_armonizzati"]
    Ip = I[I.prospettiva == "pubblica"].pivot(index="stato", columns="mrs", values="costo_annuo_eur_pps")
    w("# Tabelle e fatti del manoscritto (generato da tabelle_manoscritto.py)\n")
    w("Stati in ordine di s_dom di caso base (pubblica, progressione continua, 10 anni).\n")
    w("## Table 1. Inputs by country, 2025 prices\n")
    w("| Country | Index tariff (national currency) | K (euro PPS) | Annual public care cost, mRS 0 to 2 (euro PPS) | mRS 3 | mRS 4 | mRS 5 |")
    w("|---|---|---|---|---|---|---|")
    for st in ordine:
        s = A.STATI[st]
        K = base[base.stato == st].K.iloc[0]
        w(f"| {NOME[st]} | {n(s['tariffa'])} {VAL[s['valuta']]} | {n(K / A.PPP[st])} | "
          + " | ".join(n(Ip.loc[st, m]) for m in ["0-2", "3", "4", "5"]) + " |")
    w("")
    w("Nota: per la Bulgaria la tariffa è in euro (4.670 leva al tasso fisso 1,95583).\n")

    # ---------------- Table 2: base case ----------------
    w("## Table 2. Base case thresholds\n")
    w("| Country | Threshold λ per QALY (national currency) | K | L, 10 years | L (euro PPS) | s_dom | s_dom, plateau | q* | Reference QALY | s* at reference QALY |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for st in ordine:
        b = base[base.stato == st]
        p = plat[plat.stato == st]
        s = A.STATI[st]
        lam = " / ".join(n(x) for x in b.lambda_)
        qs = " / ".join(f"{x:.2f}" for x in b.q_star)
        ss = " / ".join(("+" if x > 0 else "") + f3(x) for x in b.s_a_q_rif)
        w(f"| {NOME[st]} | {lam} {VAL[s['valuta']]} ({SOGLIA_EN[st]}) | {n(b.K.iloc[0])} | {n(b.L.iloc[0])} | "
          f"{n(b.L.iloc[0] / A.PPP[st])} | {f3(b.s_dom.iloc[0])} | {f3(p.s_dom.iloc[0])} | {qs} | "
          f"{b.q_rif.iloc[0]:.3f} | {ss} |")
    w("")

    # ---------------- Fatti: caso base ----------------
    w("## Fatti per la prosa\n")
    w(f"s_dom caso base: da {f3(sdom.min())} ({NOME[sdom.idxmin()]}) a {f3(sdom.max())} ({NOME[sdom.idxmax()]}); "
      f"rapporto max/min {sdom.max() / sdom.min():.1f}; mediana {f3(sdom.median())}.")
    w("Ordine: " + ", ".join(f"{NOME[s]} {f3(v)}" for s, v in sdom.items()))
    ps = plat.groupby("stato").s_dom.first()
    w(f"s_dom plateau: da {f3(ps.min())} ({NOME[ps.idxmin()]}) a {f3(ps.max())} ({NOME[ps.idxmax()]}).")
    ts = tot.groupby("stato").s_dom.first()
    w(f"Prospettiva totale calcolabile per {len(ts)} Stati: s_dom da {f3(ts.min())} a {f3(ts.max())}; "
      f"non calcolabile per {', '.join(NOME[s] for s in ordine if s not in ts.index)}.")
    LPPS = (base.groupby("stato").L.first() / pd.Series(A.PPP))
    KPPS = (base.groupby("stato").K.first() / pd.Series(A.PPP))
    w(f"L in euro PPS: da {n(LPPS.min())} ({NOME[LPPS.idxmin()]}) a {n(LPPS.max())} ({NOME[LPPS.idxmax()]}), "
      f"rapporto {LPPS.max() / LPPS.min():.1f}. K in euro PPS: da {n(KPPS.min())} ({NOME[KPPS.idxmin()]}) a "
      f"{n(KPPS.max())} ({NOME[KPPS.idxmax()]}), rapporto {KPPS.max() / KPPS.min():.1f}.")
    m4 = Ip["4"]
    w(f"Costo annuo pubblico mRS 4 in euro PPS: da {n(m4.min())} ({NOME[m4.idxmin()]}) a {n(m4.max())} ({NOME[m4.idxmax()]}).")
    # correlazione di rango
    w(f"Correlazione di Spearman fra s_dom e L in PPS: {sdom.corr(LPPS[sdom.index], method='spearman'):.2f}; "
      f"fra s_dom e K in PPS: {sdom.corr(KPPS[sdom.index], method='spearman'):.2f}.")
    w("")
    # q* e guadagno di riferimento
    lo = base.loc[base.groupby("stato").lambda_.idxmin()].set_index("stato")
    hi = base.loc[base.groupby("stato").lambda_.idxmax()].set_index("stato")
    w(f"q* alla soglia più bassa: da {lo.q_star.min():.2f} ({NOME[lo.q_star.idxmin()]}) a {lo.q_star.max():.2f} "
      f"({NOME[lo.q_star.idxmax()]}); alla più alta da {hi.q_star.min():.2f} a {hi.q_star.max():.2f}.")
    w(f"Guadagno di riferimento (0,07/anno sugli anni del comparatore): da {base.q_rif.min():.2f} a {base.q_rif.max():.2f}.")
    pos_lo = [s for s in ordine if lo.loc[s, "s_a_q_rif"] > 0]
    pos_all = [s for s in ordine if (base[base.stato == s].s_a_q_rif > 0).all()]
    w(f"s* al guadagno di riferimento positiva (serve un risparmio netto) alla soglia più bassa in {len(pos_lo)} Stati: "
      + ", ".join(f"{NOME[s]} {f3(lo.loc[s, 's_a_q_rif'])}" for s in pos_lo) + ".")
    w(f"Positiva a tutte le soglie in {len(pos_all)}: " + ", ".join(NOME[s] for s in pos_all) + ".")
    w(f"Negativa a tutte le soglie (il guadagno di riferimento basta anche con spesa netta in aumento) in "
      f"{sum((base[base.stato == s].s_a_q_rif <= 0).all() for s in ordine)} Stati.")
    w("")

    # ---------------- Sottogruppi ----------------
    L = d["L_comparatore"]
    sconto_uff = {s: A.STATI[s]["sconto"] for s in A.STATI}
    Lb = L[(L.prospettiva == "pubblica") & (L.orizzonte == "10 anni") & (L.traiettoria == "continua")
           & (L.ripartizione_3_4 == "2:1") & (L.hr_rinvio == "base")]
    Lb = Lb[Lb.apply(lambda r: abs(r.sconto - sconto_uff[r.stato]) < 1e-9, axis=1)]
    sg = Lb.pivot_table(index="stato", columns="base_dipendenza", values=["s_dom", "L_eur_pps"], aggfunc="first")
    w("## Table S (sottogruppi). s_dom and L by dependence at diagnosis\n")
    w("| Country | L, all (euro PPS) | s_dom, all | L, mRS 0 to 2 | s_dom, mRS 0 to 2 | L, mRS 3 or worse | s_dom, mRS 3 or worse |")
    w("|---|---|---|---|---|---|---|")
    for st in ordine:
        w(f"| {NOME[st]} | {n(sg.loc[st, ('L_eur_pps', 'tutti')])} | {f3(sg.loc[st, ('s_dom', 'tutti')])} | "
          f"{n(sg.loc[st, ('L_eur_pps', 'mRS 0-2')])} | {f3(sg.loc[st, ('s_dom', 'mRS 0-2')])} | "
          f"{n(sg.loc[st, ('L_eur_pps', 'mRS >=3')])} | {f3(sg.loc[st, ('s_dom', 'mRS >=3')])} |")
    chk = (sg[("s_dom", "tutti")] - sdom).abs().max()
    w(f"\nControllo: s_dom 'tutti' di L_comparatore contro frontiera, scarto massimo {chk:.4f}.")
    r02 = sg[("s_dom", "mRS 0-2")] / sg[("s_dom", "tutti")]
    w(f"s_dom mRS 0-2 / tutti: da {r02.min():.2f} a {r02.max():.2f}. s_dom mRS 0-2 da {f3(sg[('s_dom','mRS 0-2')].min())} "
      f"a {f3(sg[('s_dom','mRS 0-2')].max())}; mRS ≥3 da {f3(sg[('s_dom','mRS >=3')].min())} a {f3(sg[('s_dom','mRS >=3')].max())}.\n")

    # ---------------- Griglia ----------------
    G = d["griglia_strutturale"]
    G["combo"] = G.traiettoria + "/" + G.hr_rinvio + "/" + G.volumi.astype(str)
    piv = G.pivot(index="combo", columns="stato", values="s_dom")
    w("## Griglia strutturale (18 combinazioni)\n")
    w("| Country | s_dom, min to max over 18 combinations | Rank, best to worst |")
    w("|---|---|---|")
    ranks = piv.rank(axis=1, method="min")
    for st in ordine:
        w(f"| {NOME[st]} | {f3(piv[st].min())} to {f3(piv[st].max())} | {int(ranks[st].min())} to {int(ranks[st].max())} |")
    rat = piv.max(axis=1) / piv.min(axis=1)
    w(f"\nRapporto max/min fra Stati per combinazione: da {rat.min():.1f} a {rat.max():.1f}.")
    w("Stato più basso per combinazione: " + ", ".join(f"{NOME[s]} {c}" for s, c in piv.idxmin(axis=1).value_counts().items())
      + ". Più alto: " + ", ".join(f"{NOME[s]} {c}" for s, c in piv.idxmax(axis=1).value_counts().items()) + ".")
    # gruppi che non si incrociano mai: coppie (a,b) con a sempre < b
    sempre = {(a, b) for a, b in itertools.permutations(ordine, 2) if (piv[a] < piv[b]).all()}
    # terzili del caso base
    terz = [ordine[:7], ordine[7:14], ordine[14:]]
    for i, j in [(0, 1), (1, 2), (0, 2)]:
        tot_c = len(terz[i]) * len(terz[j])
        ok = sum((a, b) in sempre for a in terz[i] for b in terz[j])
        w(f"Terzile {i+1} sempre sotto terzile {j+1}: {ok} coppie su {tot_c}.")
    # partizione massima: soglia di taglio k tale che i primi k sono sempre sotto gli altri
    tagli = [k for k in range(1, len(ordine)) if all((a, b) in sempre for a in ordine[:k] for b in ordine[k:])]
    w("Tagli dell'ordine di caso base che nessuna combinazione rompe (primi k sempre sotto tutti gli altri): "
      + (", ".join(f"k={k} (dopo {NOME[ordine[k-1]]})" for k in tagli) if tagli else "nessuno") + ".")
    st_ = piv.stack()
    gt1 = st_[st_ > 1]
    w("Celle con s_dom > 1: " + (", ".join(f"{NOME[s]} {c} {v:.2f}" for (c, s), v in gt1.items()) if len(gt1) else "nessuna") + ".")
    w("")

    # ---------------- Probabilistica ----------------
    P = d["probabilistica"]
    Ps = P[P.grandezza == "s_dom"].set_index("stato")
    w("## Probabilistica sui prezzi (s_dom, mediana e 95 %)\n")
    w("| Country | s_dom median (95% interval) | q* at lowest threshold, median (95% interval) |")
    w("|---|---|---|")
    Pq = P[P.grandezza == "q_star"]
    for st in ordine:
        q = Pq[Pq.stato == st]
        qlo = q.loc[q.mediana.idxmax()]  # soglia piu' bassa = q* piu' alto
        w(f"| {NOME[st]} | {f3(Ps.loc[st,'mediana'])} ({f3(Ps.loc[st,'p2_5'])} to {f3(Ps.loc[st,'p97_5'])}) | "
          f"{qlo.mediana:.2f} ({qlo.p2_5:.2f} to {qlo.p97_5:.2f}) |")
    lowmax = Ps.loc[ordine[:5], "p97_5"].max()
    w(f"\nIl limite alto più alto fra i cinque Stati più bassi è {f3(lowmax)}; Stati il cui limite basso lo supera: "
      + ", ".join(NOME[s] for s in ordine if Ps.loc[s, "p2_5"] > lowmax) + ".")
    nonsovr = [(a, b) for a, b in itertools.combinations(ordine, 2) if Ps.loc[a, "p97_5"] < Ps.loc[b, "p2_5"]]
    w(f"Coppie di Stati con intervalli che non si sovrappongono: {len(nonsovr)} su {len(ordine)*(len(ordine)-1)//2}.\n")

    # ---------------- Tornado: voci principali ----------------
    S = d["sensibilita_una_via"]
    w("## Analisi a una via: le tre voci che muovono di più s_dom\n")
    w("| Country | s_dom range over all one-way items | Top three items (range of s_dom) |")
    w("|---|---|---|")
    for st in ordine:
        x = S[(S.stato == st) & (S.voce != "base")]
        g = x.groupby("voce").s_dom.agg(["min", "max"])
        b0 = sdom[st]
        g["min"] = g["min"].clip(upper=b0)
        g["max"] = g["max"].clip(lower=b0)
        g["amp"] = g["max"] - g["min"]
        top = g.sort_values("amp", ascending=False).head(3)
        w(f"| {NOME[st]} | {f3(x.s_dom.min())} to {f3(x.s_dom.max())} | "
          + "; ".join(f"{v} ({f3(r['min'])} to {f3(r['max'])})" for v, r in top.iterrows()) + " |")
    w("")

    # ---------------- Sopravvivenza e arresto ----------------
    SO = d["sopravvivenza"]
    w("## Sola sopravvivenza e arresto della progressione\n")
    w("| Country | Life years gained (discounted) | s, survival alone | ICER survival alone, utility 0.57 (0.79 to 0.45) | Lowest and highest λ | Verdict at utility 0.57 | s, arrest: continuing | s_dom | Plateau: s arrest | s_dom plateau |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for st in ordine:
        r = SO[(SO.stato == st) & (SO.variante == "base")].iloc[0]
        rp = SO[(SO.stato == st) & (SO.variante == "plateau")].iloc[0]
        lams = sorted(A.STATI[st]["soglie"].values())
        ic = r["icer_u0.57"]
        ver = "above all" if ic > lams[-1] else ("below all" if ic <= lams[0] else "between")
        w(f"| {NOME[st]} | {r.anni_vita_guadagnati:.2f} | {f3(r.s_sopravvivenza)} | {n(ic)} ({n(r['icer_u0.79'])} to {n(r['icer_u0.45'])}) | "
          f"{n(lams[0])} / {n(lams[-1])} | {ver} | {f3(r.s_arresto)} | {f3(r.s_dom)} | {f3(rp.s_arresto)} | {f3(rp.s_dom)} |")
    bs = SO[SO.variante == "base"].set_index("stato")
    w(f"\nAnni di vita guadagnati: da {bs.anni_vita_guadagnati.min():.2f} a {bs.anni_vita_guadagnati.max():.2f}; "
      f"s sola sopravvivenza da {f3(bs.s_sopravvivenza.max())} a {f3(bs.s_sopravvivenza.min())}.")
    cnt = {"above all": [], "below all": [], "between": []}
    for st in ordine:
        lams = sorted(A.STATI[st]["soglie"].values())
        ic = bs.loc[st, "icer_u0.57"]
        cnt["above all" if ic > lams[-1] else ("below all" if ic <= lams[0] else "between")].append(NOME[st])
    for k, v in cnt.items():
        w(f"ICER sola sopravvivenza (u 0,57) {k}: {len(v)}: {', '.join(v)}.")
    lo_ = SO[SO.variante == "HR rinvio basso"].set_index("stato")
    w(f"Con HR del rinvio 1,13: anni guadagnati da {lo_.anni_vita_guadagnati.min():.2f} a {lo_.anni_vita_guadagnati.max():.2f}; "
      f"ICER/ICER base (u 0,57) da {(lo_['icer_u0.57']/bs['icer_u0.57']).min():.2f} a {(lo_['icer_u0.57']/bs['icer_u0.57']).max():.2f}.")
    above_lo = [NOME[s] for s in ordine if lo_.loc[s, "icer_u0.57"] > max(A.STATI[s]["soglie"].values())]
    w(f"Con HR 1,13, ICER (u 0,57) sopra la soglia più alta in {len(above_lo)}: {', '.join(above_lo)}.")
    hi_ = SO[SO.variante == "HR rinvio alto"].set_index("stato")
    w(f"Con HR alto: ICER/ICER base da {(hi_['icer_u0.57']/bs['icer_u0.57']).min():.2f} a {(hi_['icer_u0.57']/bs['icer_u0.57']).max():.2f}.")
    arr_dom = [NOME[s] for s in ordine if bs.loc[s, "s_arresto"] >= bs.loc[s, "s_dom"]]
    w(f"Arresto (continua) s ≥ s_dom in {len(arr_dom)} Stati su 21; s arresto da {f3(bs.s_arresto.min())} a {f3(bs.s_arresto.max())}.")
    pl_ = SO[SO.variante == "plateau"].set_index("stato")
    pl_dom = [NOME[s] for s in ordine if pl_.loc[s, "s_arresto"] >= pl_.loc[s, "s_dom"]]
    w(f"Arresto con plateau: s da {f3(pl_.s_arresto.min())} a {f3(pl_.s_arresto.max())}; s ≥ s_dom plateau in {len(pl_dom)}: {', '.join(pl_dom)}.")
    w(f"Arresto con HR alto: s da {f3(hi_.s_arresto.min())} a {f3(hi_.s_arresto.max())}.")
    w("")

    # ---------------- Ancore ----------------
    AS = d["ancore_scenari"]
    marg_cols = [c for c in AS.columns if c.startswith("margine_")]
    w("## Modelli pubblicati ricollocati\n")

    def sintesi(df, etichetta):
        w(f"### {etichetta}\n")
        w("| Model | q (range) | Net s (range) | Gross s (range) | Countries dominant with net s (net s ≥ s_dom, q > 0) | Cost-effective at lowest λ (net s) | at highest λ |")
        w("|---|---|---|---|---|---|---|")
        for an, g in df.groupby("ancora", sort=False):
            g = g.set_index("stato")
            dom = [s for s in ordine if g.loc[s, "s_netta"] >= g.loc[s, "s_dom"] and g.loc[s, "q"] > 0]
            ce_lo, ce_hi = [], []
            for s in ordine:
                m = g.loc[s, marg_cols].dropna().astype(float)
                lams = A.STATI[s]["soglie"]
                ml = {k.replace("margine_", ""): v for k, v in m.items()}
                kl = min(lams, key=lams.get)
                kh = max(lams, key=lams.get)
                if ml[kl] >= 0:
                    ce_lo.append(s)
                if ml[kh] >= 0:
                    ce_hi.append(s)
            w(f"| {an} | {g.q.min():.2f} to {g.q.max():.2f} | {f3(g.s_netta.min())} to {f3(g.s_netta.max())} | "
              f"{f3(g.s_lorda.min())} to {f3(g.s_lorda.max())} | {len(dom)}: {', '.join(dom)} | "
              f"{len(ce_lo)}/21 (not: {', '.join(s for s in ordine if s not in ce_lo)}) | "
              f"{len(ce_hi)}/21 (not: {', '.join(s for s in ordine if s not in ce_hi)}) |")
        w("")

    for (hr, tr, lab) in [("base", "continua", "Caso base (HR 2,57, continua)"),
                          ("basso", "continua", "HR del rinvio 1,13"),
                          ("alto", "continua", "HR del rinvio 5,83"),
                          ("base", "plateau", "Plateau")]:
        df = AS[(AS.hr_rinvio == hr) & (AS.traiettoria == tr)]
        df = pd.concat([df[df.ritardo_tinelli.isna()],
                        df[df.ritardo_tinelli == 1].assign(ancora="Tinelli (2021), 1-year delay"),
                        df[df.ritardo_tinelli == 2].assign(ancora="Tinelli (2021), 2-year delay")])
        sintesi(df, lab)
    # lorda: dominanza con s lorda nel caso base
    b = AS[(AS.hr_rinvio == "base") & (AS.traiettoria == "continua") & (AS.ritardo_tinelli.isna() | (AS.ritardo_tinelli == 2))]
    for an, g in b.groupby("ancora", sort=False):
        g = g.set_index("stato")
        domL = [s for s in ordine if g.loc[s, "s_lorda"] >= g.loc[s, "s_dom"]]
        w(f"Caso base, {an}: dominante con s lorda in {len(domL)} Stati; non dominante in "
          + ", ".join(s for s in ordine if s not in domL) + ".")
    w("")
    w("ICER netti di caso base per Stato (moneta nazionale):\n")
    w("| Country | Tullberg 2018 | Tinelli 2021, 2-year to 1-year delay | Taddei 2026 |")
    w("|---|---|---|---|")
    b1 = AS[(AS.hr_rinvio == "base") & (AS.traiettoria == "continua") & (AS.ritardo_tinelli == 1)].set_index("stato")
    for st in ordine:
        g = b[b.stato == st].set_index("ancora")
        t1, t2 = b1.loc[st, 'icer_netto'], g.loc['Tinelli (2021)', 'icer_netto']
        w(f"| {NOME[st]} | {n(g.loc['Tullberg (2018)', 'icer_netto'])} | {n(min(t1, t2))} to {n(max(t1, t2))} | "
          f"{n(g.loc['Taddei (2026)', 'icer_netto'])} |")
    w("")

    # ---------------- Validazione ----------------
    V = d["validazione"]
    V = V[V.hr_rinvio == "base"]
    m4 = V[V.controllo.str.contains("4 anni")].set_index("stato").modello.astype(float)
    m5 = V[V.controllo.str.contains("5 anni")].set_index("stato").modello.astype(float)
    Vall = d["validazione"]
    m5hi = Vall[(Vall.hr_rinvio == "alto") & Vall.controllo.str.contains("5 anni")].modello.astype(float)
    res = d["validazione"][d["validazione"].controllo.str.contains("residenza")]
    w("## Validazione\n")
    w(f"Mortalità a 4 anni da 76 anni: da {m4.min():.0%} ({NOME[m4.idxmin()]}) a {m4.max():.0%} ({NOME[m4.idxmax()]}); Svezia {m4['SE']:.0%}.")
    w(f"Mortalità a 5 anni da 75 anni: da {m5.min():.0%} a {m5.max():.0%}; con HR alto da {m5hi.min():.0%} a {m5hi.max():.0%}.")
    vv = Vall[Vall.controllo.str.contains("anni da")].copy()
    vv["k"] = vv.controllo.str.extract(r"(\d) anni")[0] + "_" + vv.hr_rinvio
    vp = vv.pivot_table(index="stato", columns="k", values="modello", aggfunc="first")
    w("\n| Country | 4-year mortality from age 76: HR 1.13 / base / HR 5.83 | 5-year mortality from age 75: HR 1.13 / base / HR 5.83 |")
    w("|---|---|---|")
    for st in ordine:
        w(f"| {NOME[st]} | {vp.loc[st, '4_basso']:.0%} / {vp.loc[st, '4_base']:.0%} / {vp.loc[st, '4_alto']:.0%} | "
          f"{vp.loc[st, '5_basso']:.0%} / {vp.loc[st, '5_base']:.0%} / {vp.loc[st, '5_alto']:.0%} |")
    w("")
    w("Quota dell'anno in residenza alla diagnosi: " + "; ".join(f"{r.stato} {r.hr_rinvio} {r.modello}" for r in res.itertuples()))
    w("")

    # ---------------- Scomposizione della varianza ----------------
    import numpy as np
    lk, ll = np.log(KPPS[ordine]), np.log(LPPS[ordine])
    ls = np.log(sdom[ordine])
    vk, vl, cv = lk.var(), ll.var(), np.cov(lk, ll)[0, 1]
    w("## Scomposizione della varianza di log s_dom (log s_dom = log K − log L, in PPS)\n")
    w(f"Var(log s_dom) {ls.var():.4f} = Var(log K) {vk:.4f} + Var(log L) {vl:.4f} − 2 Cov {2*cv:.4f}; "
      f"correlazione log K / log L {np.corrcoef(lk, ll)[0,1]:.2f}.")
    w(f"Quota attribuibile (Cov(log s, ·)/Var(log s)): K {np.cov(ls, lk)[0,1]/ls.var():.2f}, "
      f"L {-np.cov(ls, ll)[0,1]/ls.var():.2f} (sommano a 1). Regressione semplice log s su log L: R² {np.corrcoef(ls, ll)[0,1]**2:.2f}; su log K: R² {np.corrcoef(ls, lk)[0,1]**2:.2f}.\n")

    # griglia completa
    w("## Griglia completa (s_dom), per traiettoria\n")
    for tr, lab in [("continua", "Continuing progression"), ("plateau", "Plateau after the first year")]:
        cols = [(h, v) for h in ["basso", "base", "alto"] for v in [0.5, 1.0, 1.5]]
        hl = {"basso": "1.13", "base": "2.57", "alto": "5.83"}
        w(f"### {lab}\n")
        w("| Country | " + " | ".join(f"HR {hl[h]}, ×{v:g}" for h, v in cols) + " |")
        w("|---|" + "---|" * len(cols))
        for st in ordine:
            g = G[(G.stato == st) & (G.traiettoria == tr)].set_index(["hr_rinvio", "volumi"]).s_dom
            w(f"| {NOME[st]} | " + " | ".join(f3(g.loc[(h, v)]) for h, v in cols) + " |")
        w("")

    # varianti di sopravvivenza
    w("## Varianti della sola sopravvivenza e dell'arresto (per Stato)\n")
    w("| Country | Base: ICER at utility 0.79 / 0.57 / 0.45 | HR 1.13: life years gained; ICER at utility 0.57 | HR 5.83: life years gained; ICER at utility 0.57 | s, arrest: HR 1.13 / HR 5.83 |")
    w("|---|---|---|---|---|")
    for st in ordine:
        r = bs.loc[st]; a = lo_.loc[st]; z = hi_.loc[st]
        w(f"| {NOME[st]} | {n(r['icer_u0.79'])} / {n(r['icer_u0.57'])} / {n(r['icer_u0.45'])} | {a.anni_vita_guadagnati:.2f}; {n(a['icer_u0.57'])} | "
          f"{z.anni_vita_guadagnati:.2f}; {n(z['icer_u0.57'])} | {f3(a.s_arresto)} / {f3(z.s_arresto)} |")
    w("")

    # ancore: margini di caso base e dominanza con HR 1,13 per Stato
    w("## Ancore per Stato: margine dalla frontiera (net s − s*(q)) alla soglia più bassa / più alta, caso base; dominanza con HR 1,13\n")
    w("| Country | Tullberg 2018 | Tinelli 2021, 2-year delay | Tinelli 2021, 1-year delay | Taddei 2026 | Dominant with net s at hazard ratio of delay 1.13 |")
    w("|---|---|---|---|---|---|")
    def marg(row, st):
        lams = A.STATI[st]["soglie"]
        kl, kh = min(lams, key=lams.get), max(lams, key=lams.get)
        a_, b_ = row[f"margine_{kl}"], row[f"margine_{kh}"]
        sg_ = lambda x: ("+" if x > 0 else "") + f3(x)
        return sg_(a_) if kl == kh else f"{sg_(a_)} / {sg_(b_)}"
    AB = AS[(AS.hr_rinvio == "base") & (AS.traiettoria == "continua")]
    AL = AS[(AS.hr_rinvio == "basso") & (AS.traiettoria == "continua")]
    for st in ordine:
        x = AB[AB.stato == st]
        tu = x[x.ancora == "Tullberg (2018)"].iloc[0]; ta = x[x.ancora == "Taddei (2026)"].iloc[0]
        t2 = x[(x.ancora == "Tinelli (2021)") & (x.ritardo_tinelli == 2)].iloc[0]
        t1 = x[(x.ancora == "Tinelli (2021)") & (x.ritardo_tinelli == 1)].iloc[0]
        y = AL[AL.stato == st]
        dom = []
        for lab, sel in [("Tullberg", y.ancora == "Tullberg (2018)"),
                         ("Tinelli 2-year", (y.ancora == "Tinelli (2021)") & (y.ritardo_tinelli == 2)),
                         ("Tinelli 1-year", (y.ancora == "Tinelli (2021)") & (y.ritardo_tinelli == 1)),
                         ("Taddei", y.ancora == "Taddei (2026)")]:
            r = y[sel].iloc[0]
            if r.s_netta >= r.s_dom and r.q > 0:
                dom.append(lab)
        w(f"| {NOME[st]} | {marg(tu, st)} | {marg(t2, st)} | {marg(t1, st)} | {marg(ta, st)} | {', '.join(dom) if dom else 'none'} |")
    w("")

    # ---------------- Traccia del comparatore ----------------
    T = d["traccia_comparatore"]
    w("## Traccia del comparatore (caso base: mix 2:1, HR 2,57)\n")
    w("La distribuzione di mRS fra i vivi e la quota in residenza non dipendono dallo Stato "
      "(stesso HR in tutti i livelli); dallo Stato dipende solo la quota di vivi.\n")
    w("| Year | Alive, % of cohort (range across countries) | mRS 0 to 2 | mRS 3 | mRS 4 | mRS 5 | Share of the year in residential care |")
    w("|---|---|---|---|---|---|---|")
    for tr, lab in [("continua", "Continuing progression"), ("plateau", "Plateau after the first year")]:
        w(f"| *{lab}* | | | | | | |")
        for anno, g in T[T.traiettoria == tr].groupby("anno"):
            assert g[["mrs_0-2", "mrs_3", "mrs_4", "mrs_5", "residenza"]].nunique().max() == 1
            r = g.iloc[0]
            w(f"| {anno} | {rng(g.vivi * 100, fmt=lambda x: f'{x:.0f}')} | {r['mrs_0-2']:.0%} | {r.mrs_3:.0%} | "
              f"{r.mrs_4:.0%} | {r.mrs_5:.0%} | {r.residenza:.0%} |")
    w("")

    OUT.write_text("\n".join(righe), encoding="utf-8")
    print(f"scritto {OUT.name}: {len(righe)} righe")


if __name__ == "__main__":
    main()
