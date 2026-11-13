"""Tavole di mortalita' per i 21 Stati del modello, qx per eta' singola 75-94 e
classe aperta 95+, maschi e femmine.

Eurostat demo_mlifetable, PROBDEATH, anno 2024, per i 20 Stati UE ed EFTA (i cinque
originali riscaricati e confrontati con tavole_mortalita_eurostat_2024.csv); ONS National
life tables, England, 2022-2024 (foglio "2022-2024" di nlte198020223.xlsx) per il Regno Unito.
Output: tavole_mortalita_2024.csv.
Uso: python3 model/scarica_tavole.py
"""
import csv
import json
import urllib.request
from pathlib import Path

import openpyxl

QUI = Path(__file__).parent
ONS = QUI / "ONS_national_life_tables_England_nlte198020223.xlsx"
API = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_mlifetable"
       "?format=JSON&lang=EN&indic_de=PROBDEATH&sex=M&sex=F&time=2024")
ETA = [f"Y{e}" for e in range(75, 95)] + ["Y_GE95"]

NOMI = {"SE": "Svezia", "DE": "Germania", "FR": "Francia", "ES": "Spagna", "PL": "Polonia",
        "EE": "Estonia", "NO": "Norvegia", "IE": "Irlanda", "DK": "Danimarca",
        "NL": "Paesi Bassi", "PT": "Portogallo", "LV": "Lettonia", "CZ": "Repubblica Ceca",
        "SK": "Slovacchia", "BG": "Bulgaria", "CH": "Svizzera", "AT": "Austria",
        "FI": "Finlandia", "LT": "Lituania", "SI": "Slovenia", "UK": "Regno Unito"}


def eurostat(geo):
    url = API + f"&geo={geo}" + "".join(f"&age={a}" for a in ETA)
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    # JSON-stat: 'value' e 'status' sono sparsi, indice = posizione nel prodotto delle dimensioni
    ids, size = d["id"], d["size"]
    idx = {k: d["dimension"][k]["category"]["index"] for k in ids}
    righe = []
    for sesso in ("M", "F"):
        for a in ETA:
            pos = {"freq": 0, "indic_de": 0, "sex": idx["sex"][sesso], "age": idx["age"][a],
                   "geo": 0, "time": 0}
            n = 0
            for k, s in zip(ids, size):
                n = n * s + pos[k]
            v = d["value"].get(str(n))
            assert v is not None, (geo, sesso, a)  # eta' mancante: si ferma
            righe.append(dict(stato=geo, nome_stato=NOMI[geo], sesso=sesso,
                              eta="95+" if a == "Y_GE95" else a[1:], qx=v, anno=2024,
                              flag_eurostat=(d.get("status") or {}).get(str(n), ""),
                              fonte=f"Eurostat demo_mlifetable (agg. {d['updated'][:10]})"))
    return righe


def ons():
    ws = openpyxl.load_workbook(ONS, read_only=True, data_only=True)["2022-2024"]
    righe = {"M": {}, "F": {}}
    for r in ws.iter_rows(values_only=True):
        if isinstance(r[0], int) and 75 <= r[0] <= 94:
            righe["M"][r[0]] = r[2]
            assert r[7] == r[0]
            righe["F"][r[7]] = r[9]
    # controllo: valori letti nella tavola ONS
    assert (righe["M"][75], righe["M"][94], righe["F"][75]) == (0.02953, 0.249629, 0.02036), righe
    return [dict(stato="UK", nome_stato=NOMI["UK"], sesso=sx, eta=e, qx=q, anno="2022-2024",
                 flag_eurostat="", fonte="ONS National life tables, England 2022-2024")
            for sx in ("M", "F") for e, q in sorted(righe[sx].items())]


def main():
    righe = []
    for geo in NOMI:
        righe += ons() if geo == "UK" else eurostat(geo)
    for geo in NOMI:  # 20 eta' singole per sesso in ogni Stato
        for sx in ("M", "F"):
            assert sum(1 for r in righe if r["stato"] == geo and r["sesso"] == sx
                       and not str(r["eta"]).endswith("+")) == 20, (geo, sx)
    # confronto con la tavola salvata dei cinque Stati originali, se presente nella cartella
    vecchia = QUI / "tavole_mortalita_eurostat_2024.csv"
    if vecchia.exists():
        with open(vecchia) as f:
            vecchie = {(r["stato"], r["sesso"], r["eta"]): float(r["qx"]) for r in csv.DictReader(f)}
        nuove = {(r["stato"], r["sesso"], str(r["eta"])): r["qx"] for r in righe}
        diff = {k: (v, nuove.get(k)) for k, v in vecchie.items() if nuove.get(k) != v}
        print("Differenze con la tavola salvata dei cinque Stati:", diff or "nessuna")
    with open(QUI / "tavole_mortalita_2024.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0]))
        w.writeheader()
        w.writerows(righe)
    flag = sorted({(r["stato"], r["flag_eurostat"]) for r in righe if r["flag_eurostat"]})
    print(f"{len(righe)} righe scritte; flag Eurostat: {flag or 'nessuno'}")


if __name__ == "__main__":
    main()
