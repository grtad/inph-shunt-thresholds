# Shunt thresholds in iNPH: model code and outputs

Code and output files of the threshold analysis in *Shunt Surgery versus No Surgery for Idiopathic Normal Pressure Hydrocephalus in European Countries: A Cost-Effectiveness Threshold Analysis* (Taddei et al., manuscript submitted for publication).

The model asks, for 21 European countries, how much of the public long-term care expenditure of an untreated patient a shunt operation must avoid to pay for itself (s_dom = K/L), and how large a health gain it must produce when no care is avoided (q* = K/λ). K is the cost of the operation with reoperations over 10 years, L the discounted public care expenditure of an untreated patient over the same horizon, λ the national threshold.

## Contents

| File | Content |
|---|---|
| `model/armonizzazione.py` | National inputs (hospital tariffs, unit costs of long-term care, public shares, discount rates, thresholds, price indices and purchasing power parities), harmonised to 2025 prices. Every value carries its source in a comment. Writes `input_armonizzati.csv` and `tappa_A.csv`. |
| `model/markov_comparatore.py` | Markov model of the untreated comparator (modified Rankin Scale states), L by country, K with competing mortality, frontier s*(q) = (K − λq)/L and validation checks. Writes `L_comparatore.csv`, `frontiera.csv`, `validazione.csv`, `traccia_comparatore.csv`. |
| `model/ancore_ricalcolate.py` | The three published models (Tullberg 2018, Tinelli 2021, Taddei 2026) re-expressed on the cohort of the present model. Writes `ancore_ricalcolate.csv` and `ancore_scenari.csv`. |
| `model/fase4_sensibilita.py` | One-way sensitivity analysis, probabilistic analysis on prices (10,000 draws, fixed seed), survival-only scenarios, structural grid (18 combinations) and figures. Writes `sensibilita_una_via.csv`, `probabilistica.csv`, `sopravvivenza.csv`, `griglia_strutturale.csv` and the figures in `figures/`. |
| `model/tabelle_manoscritto.py` | Builds every table and number of the manuscript and supplement from the CSV files above, without recomputing the model. Writes `tabelle_manoscritto.md`. |
| `model/scarica_tavole.py` | Builds the life tables: 2024 Eurostat tables (`demo_mlifetable`, downloaded through the Eurostat API) and the Office for National Statistics tables for England 2022-2024 (read from the deposited workbook `ONS_national_life_tables_England_nlte198020223.xlsx`). Optional: its output, `tavole_mortalita_2024.csv`, is included, and the Eurostat values may have been revised since November 2026. |
| `model/*.csv`, `model/tabelle_manoscritto.md` | Outputs as used in the manuscript. |

## Running

Python 3 with the packages in `requirements.txt` (tested with Python 3.14). From the repository root:

```
pip install -r requirements.txt
python3 model/armonizzazione.py
python3 model/markov_comparatore.py
python3 model/ancore_ricalcolate.py
python3 model/fase4_sensibilita.py
python3 model/tabelle_manoscritto.py
```

Run in this order, the scripts reproduce the deposited CSV files byte for byte (checked with Python 3.14, numpy 2.5, scipy 1.18, pandas 3.0, matplotlib 3.11). The whole run takes about one minute.

## Notes

The inputs are written in `armonizzazione.py` rather than read from files: each value is followed by its source, and Supplementary Tables S1 and S2 of the article give for each country the document, the price year and whether the value was read or deduced. The source documents themselves (tariff lists, statistical yearbooks, guidelines) are not deposited.

Comments, variable names and console messages are in Italian; column names of the CSV files are in Italian or in the notation of the article (`stato` = country, ISO code; `s_dom`, `q_star`, `K`, `L`; `pubblica`/`totale` = public/total perspective; `continua`/`plateau`/`demenza` = course of the comparator after the first year). Figure texts and the tables in `tabelle_manoscritto.md` are in English.

## Licence

Code: MIT licence (`LICENSE`). Output files and life tables: Creative Commons Attribution 4.0 International (`LICENSE-DATA.md`); the life tables are derived from Eurostat and Office for National Statistics data, reused under their own open licences.

## Citation

Please cite the article and this deposit (see `CITATION.cff`; the DOI is given on the Zenodo record).
