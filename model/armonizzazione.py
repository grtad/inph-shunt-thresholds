"""Input armonizzati per contesto (anno di prezzo 2025).

Ogni valore porta la fonte in commento; il dettaglio (URL, letto/dedotto) e' nelle
Tabelle supplementari S1 e S2 dell'articolo. Output: input_armonizzati.csv
e tappa_A.csv nella stessa cartella. Uso: python3 model/armonizzazione.py
"""
import csv
from pathlib import Path

QUI = Path(__file__).parent

# Uso di assistenza per mRS, Lekander 2017 tab. 3, ictus ischemico, secondo anno
ORE_DOMICILIO = {"0-2": 26, "3": 571, "4": 1325, "5": 741}
GIORNI_RESIDENZA = {"0-2": 1, "3": 40, "4": 78, "5": 265}

# Revisioni: Andren 2018 (SHQR, 979 operati, fino a 10 anni): 410 reoperazioni in 257
# pazienti, 239 nel primo anno (verificato sul full text).
# Caso base: K conta le reoperazioni -> 0,244 per paziente il primo anno, 171/979 = 0,175
# negli anni 2-10 (0,0194 l'anno). Grezzo: niente morte competitiva.
P_REV_ANNO1 = 239 / 979
P_REV_ANNI_SUCC = 171 / 979 / 9
# Sensibilita': pazienti con almeno una reoperazione (26 %, 58 % nel primo anno)
P_REV_PAZIENTI = (0.26 * 0.58, 0.26 * 0.42 / 9)

# Parita' di potere d'acquisto 2025, PIL, valuta nazionale per PPS (Eurostat prc_ppp_ind_1)
PPP = {"SE": 13.4316, "DE": 1.11554, "FR": 1.06469, "ES": 0.897152, "PL": 3.09461}

STATI = {
    "SE": dict(
        valuta="SEK", sconto=0.03,
        # NordDRG A09E 2026: 1,480 x 81.142; prezzo 2026 assunto come 2025
        tariffa=120090, revisione=120090,  # revisione nello stesso gruppo: assunzione
        # Kolada 2025: N21006 / (N21826 x 12), ora concessa (dedotto)
        ora_tot=923.0, quota_pub_dom=1 - 0.069,
        # Kolada N23009 2025 / 365 (dedotto)
        giorno_tot=1125650 / 365, quota_pub_res=1 - 0.036,
        soglie={"classe alta, limite basso": 500000, "classe alta, limite alto": 1000000},
    ),
    "DE": dict(
        valuta="EUR", sconto=0.03,
        # aG-DRG 2025 B20D senza quota infermieristica (8.301); revisione B18B 2025, BR 1,979 x BBFW 4.394,22
        # = 8.696,16 (Fallpauschalen-Katalog 2025 r. 462)
        tariffa=8301, revisione=8696.16,
        # tariffa oraria contrattuale, cura alla persona, Baviera 2025 (regionale)
        ora_tot=67.68, quota_pub_dom=None,
        # pubblico domiciliare: massimale Pflegesachleistung 2026 (EUR/mese), con
        # mRS 0-2 -> PG2, 3 -> PG3, 4 -> PG4, 5 -> PG5 (assunzione)
        massimale_dom={"0-2": 796, "3": 1497, "4": 1859, "5": 2299},
        # residenza: SPV 30.767/anno per residente 2025 + quota utente vdek 3.364/mese 2026
        giorno_tot=(30767 + 3364 * 12) / 365, quota_pub_res=30767 / (30767 + 3364 * 12),
        soglie={"1 x PIL pro capite": 54240, "3 x PIL pro capite": 162720},
    ),
    "FR": dict(
        valuta="EUR", sconto=0.025,
        # GHS 26 (livello 1, GHM 01C04) 2026; revisione GHM 01C08 livello 1 2026
        tariffa=6594.38, revisione=2852.07,
        # tarif minimal national SAD 2026 (CNSA); quota utente domicile 5 % (DSS 2020)
        ora_tot=25.00, quota_pub_dom=0.95,
        # etablissement GIR1-4 CCSS 2019 34.900, x CP13302 2019->2025 1,1522, piu' gite et
        # couvert 781/mese x 12 (2019, stesso fattore); quota pubblica 63 % (DSS 2020)
        giorno_tot=(34900 + 781 * 12) * 1.1522 / 365, quota_pub_res=23500 / 37400,
        soglie={"1 x PIL pro capite": 43350, "3 x PIL pro capite": 130050},
    ),
    "ES": dict(
        valuta="EUR", sconto=0.03,
        # APR-GRD 022 2024 x CP063 2024->2025 (1/0,9774); revisione nello stesso GRD
        tariffa=11449.04 / 0.9774, revisione=11449.04 / 0.9774,
        # SAD 2024 17,31 EUR/h x CP13303 1,0265; quota utente 10,2 %
        ora_tot=17.31 * 1.0265, quota_pub_dom=1 - 0.102,
        # residencia concertada 2024 x CP13302 1,0476; quota utente 38,3 %
        giorno_tot=23609.41 * 1.0476 / 365, quota_pub_res=1 - 0.383,
        soglie={"limite basso": 20000, "limite alto": 25000},
    ),
    "PL": dict(
        valuta="PLN", sconto=0.05, sconto_esiti=0.035,  # 5 % costi, 3,5 % esiti (AOTMiT)
        # JGP A12 16.539 punti, revisione A13 11.959 punti; punto 1,96 zl (unico valore
        # ufficiale trovato, area parto 2025); in sensibilita' 1,00 zl
        tariffa=16539 * 1.96, revisione=11959 * 1.96,
        # solo quota della gmina: 30,21 zl/h 2024 x CP13303 1,1361; costo pieno non noto
        ora_tot=None, ora_pub=30.21 * 1.1361, quota_pub_dom=None,
        # DPS 7.023,74 zl/mese 2025; quota gmina 4.513 zl/mese 2024 x CP13302 1,1206
        giorno_tot=7023.74 * 12 / 365, quota_pub_res=4513 * 1.1206 / 7023.74,
        soglie={"soglia di legge (3 x PIL pc, GUS 2025)": 244821},
    ),
}


# ---------- Altri 16 Stati (21 in tutto) ----------
# Le fonti sono citate con il nome del documento e il numero di riga (r.); i percorsi fonti/XX/...
# indicano il documento di fonte per Stato, qui non riprodotto (dettaglio nelle Tabelle
# supplementari S1 e S2 dell'articolo).
# Forme: ora_pub senza ora_tot (PT, LV, BG, AT: prospettiva totale non calcolabile, come PL);
# giorno_pub senza giorno_tot (BG); massimale_ore_dom (SI: tetto in ore, la Germania lo ha in euro).

# Estonia (EE)
PPP["EE"] = 0.918465  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/EE/eurostat_prc_ppp_ind_1_EE_SE.json, agg. 9/7/2026)

STATI["EE"] = dict(
    valuta="EUR",
    sconto=0.035,  # 3,5 % costi ed esiti: TTH Eesti juhend 2024, cap. 2.3.1.9 (fonti/EE/tth_eesti_juhend_2024.txt r. 590-591)
    # NordDRG 001D, piirhind 2025: VV m. 19.03.2025 nr 20, par. 47 lg 1, in vigore 1/4-31/12/2025
    # (fonti/EE/RT_126032025011_TTL_2025_VVm20.txt r. 4724). Prezzo 2025. Kit 2702L dentro il DRG.
    # Pagamento effettivo 0,7 x piirhind + 0,3 x FFS (par. 47 lg 4-5): 4.653,69-10.484,63;
    # assunzione dichiarata: somma FFS media pari al piirhind.
    tariffa=5900.53,
    # Revisione (AAF20, proprieta' 01S28) nello stesso gruppo 001D: grouper EST2026PR1, drg_logic
    # 70100160000, caso di prova 54638 (fonti/EE/tervisekassa_norddrg_EST2026PR_grouper.xlsx)
    revisione=5900.53,
    # koduteenus 2025, S-veeb: 18,2 EUR/ora (Hooldereformi moju-analuus 2026, cap. 2.3;
    # fonti/EE/hooldereform_2026/02_hveeb_star_analyys.txt r. 300-301). Prezzo 2025.
    ora_tot=18.2,
    # KOV 15,29 / 18,2 = 0,840 (r. 305), sola quota comunale, prudente;
    # 1 - 2,1 / 18,2 = 0,885 (r. 303) in sensibilita'
    quota_pub_dom=15.29 / 18.2,
    # uldhooldus 2025 (STAR), 189 mln EUR a prezzo minimo del posto (sottostima)
    # / 130.700 mesi di servizio x 12 / 365 = 47,54 EUR/giorno (fonti/EE/hooldereform_2026/07_kulud_raport.txt
    # r. 638, tab. 7.4 r. 661). Prezzo 2025.
    giorno_tot=189e6 / 130700 * 12 / 365,
    # Spesa comunale effettiva, netokulu KOV 2025 103,1 mln (r. 815) / 189 = 0,546
    # (25,9 EUR pubblici al giorno); listino STAR, KOV 88 / 189 = 0,466 (r. 638), in sensibilita'
    quota_pub_res=103.1 / 189,
    # Soglie di prassi delle commissioni Tervisekassa
    soglie={"Tervisekassa, soglia abituale": 20000, "Tervisekassa, limite alto": 40000},
)

# Norvegia (NO)
PPP["NO"] = 14.8506  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/NO/Eurostat_prc_ppp_ind_1_NO_SE_GDP.json)

STATI["NO"] = dict(
    valuta="NOK",
    # Finansdepartementet R-109/2021 par. 6.2 (4,0 % anni 0-40) e DMP Submission guidelines 2026
    # par. 12.8 (4 % anni 0-39, costi ed effetti); orizzonte di 10 anni: 4 % costante
    sconto=0.04,
    # ISF-regelverk 2025, Vedlegg A1: DRG 1D kostnadsvekt 4,180 (fonti/NO/ISF-regelverk_2025.txt r. 3710)
    # x enhetspris somatikk 2025 54.412 NOK (r. 555) = 227.442 NOK, prezzo pieno (DMP par. 12.7). Prezzo 2025.
    tariffa=4.180 * 54412,
    # AAF20 con diagnosi principale G91.2 -> 1D, letto (DefinitionData DRG 2025 PR1d, drglogic r. 1580);
    # caso base: 1D; sensibilita': 443
    revisione=4.180 * 54412,
    # KOSTRA 2025: spesa lorda funzioni 257 + 258 (tav. 12362) 53.085.746 + 46.591.533 migliaia di NOK /
    # ore concesse 2025 ai servizi 01, 02, 03, 07, 11, 15 (tav. 11643) 114.497.346 = 870,6 NOK/ora, tutte le eta'
    ora_tot=(53085746 + 46591533) * 1000 / 114497346,
    # brukerbetalinger 257 + 258 (tav. 12367) 794.091 / 99.677.279 -> 0,992
    quota_pub_dom=1 - 794091 / 99677279,
    # KOSTRA 2025 tav. 12209 "Utgifter per oppholdsdogn i institusjon" 5.545 NOK (fonti/NO/SSB_KOSTRA_tabell_12209_Landet.csv r. 2)
    giorno_tot=5545,
    # brukerbetalinger 253 + 261 (tav. 12367) 8.679.906 / spesa lorda 253 + 261 74.554.997 -> 0,884
    quota_pub_res=1 - 8679906 / 74554997,
    # Alternativkostnad 275.000 NOK/QALY (testo HOD/DMP); gradini Magnussentrappen dalla figura 1
    soglie={"alternativkostnad": 275000, "Magnussentrappen APT 5-8 (figura)": 383000,
            "Magnussentrappen APT 9-12 (figura, massimo a 75 anni)": 493000},
)

# Irlanda (IE)
PPP["IE"] = 1.17981  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/IE/Eurostat_prc_ppp_ind_1_IE.json, agg. 9/7/2026)

STATI["IE"] = dict(
    valuta="EUR",
    sconto=0.04,  # HIQA Economic Evaluation Guidelines 2025, sez. 2.14: 4,0 % costi ed esiti (fonti/IE/HIQA_..._2025.txt r. 2246-2247)
    # ABF 2025 (HPO, AR-DRG v10.0), listino 1/7/2025-30/6/2026 (anno dall'etichetta del link HSE): B02C
    # "Cranial intervtn, minc", prezzo inlier medio nazionale 16.585, RV 4,634
    # (fonti/IE/HSE_HPO_ABF_2025_Admitted_Patient_Price_List_Inpatient.txt r. 22). Prezzo 2025/26 come 2025.
    tariffa=16585,
    # B01Z "Ventricular shunt rev", gruppo proprio (stesso listino r. 19)
    revisione=11650,
    # Core rate HSE ai fornitori di home support, in vigore dall'1/9/2025 (PQ 3909/26, r. 72-73)
    ora_tot=32.73,
    quota_pub_dom=1.0,  # servizio gratuito, senza prova dei mezzi (pagina HSE, r. 77)
    # NHSS: bilancio 2025 1.247,7 M (NSP 2026, App. 3 Tab. 1, r. 4473-4474) / 23.807 persone (outturn
    # proiettato 2025, r. 3894) / 365 = 143,59 EUR/giorno pubblici; totale = / (969 / 1.312), quota del
    # sostegno HSE con i prestiti sul costo totale (C&AG Special Report 110, dati 2018) -> 194,41
    giorno_tot=1247.7e6 / 23807 / 365 / (969 / 1312),
    quota_pub_res=918 / 1312,  # C&AG 2018: 70 % (r. 572-578); quota del 2018 applicata al 2025
    # HIQA 2025 sez. 2.19.3: riportare 20.000 e 45.000 EUR/QALY, "not derived empirically"
    soglie={"HIQA, riferimento basso": 20000, "HIQA, riferimento alto": 45000},
)

# Regno Unito, Inghilterra (UK)
PPP["UK"] = 1.06392  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, UK, 2025 (fonti/UK/Eurostat_prc_ppp_ind_1_GDP.json; OCSE concorde)

STATI["UK"] = dict(  # Inghilterra come riferimento (sanita' e social care devoluti)
    valuta="GBP",
    sconto=0.035,  # NICE PMG36 4.5.1: 3,5 % costi ed effetti (fonti/UK/nice_pmg36_ch4_economic_evaluation.md r. 368)
    # NHSPS 2025/26 (pay award), foglio "1 APC & OPROC" r. 76: AA52D Very Major Intracranial Procedures 19+,
    # CC 0-3, unit price elettivo/day case 8.064, prima dell'MFF (fonti/UK/NHSPS_2025-26_prices_workbook_pay_award.xlsx).
    # Prezzo 2025/26 assunto come 2025.
    tariffa=8064,
    # A14.1 e A14.2 (rinnovo e revisione dell'intero shunt) in AA52, letto (Code to Group 2025/26 r. 21285-21286)
    revisione=8064,
    # ASC-FR 2024/25 Table 51: home care esterna 23,5566 GBP/h (media pesata per popolazione, tutti gli adulti)
    # x CPI 12.4.0.3 (L7JB) 2025 / FY 2024/25 = 167,3 / 159,075 -> 24,77
    ora_tot=23.5566 * 167.3 / 159.075,
    # Quota sull'intera popolazione, con i self-funder (il modello applica i volumi a tutta la coorte).
    # Assistiti dei comuni: 1 - (199.698 + 840.269 x 3.235.738 / 4.853.398) / 3.235.738 = 0,7652 (ASC-FR data pack 2024/25)
    # x quota non self-funder della comunita' 65+ (1 - 0,284; ONS 2022-23, ONS_community_self_funders_2022-23.txt r. 112)
    # = 0,548
    quota_pub_dom=(1 - 0.2348) * (1 - 0.284),
    # ASC-FR 2024/25 Table 52: 65+ residential e nursing 1.019,31 GBP/sett. senza FNC; + FNC 2024/25 235,88
    # x quota delle settimane in nursing 0,3148 (2.578.488 / 8.191.318); / 7; x CPI 12.4.0.2 (L7J8) 172,2 / 164,033
    giorno_tot=(1019.31 + 0.3148 * 235.88) / 7 * 172.2 / 164.033,
    # Assistiti dei comuni 1 - 2.392.343 / (8.349.459 + 608.214) = 0,7329
    # (k GBP, 65+, nursing + residential) x quota non self-funder delle case per anziani (1 - 0,489; ONS 2022-23,
    # ONS_care_homes_self_funders_2022-23.txt r. 117) = 0,375
    quota_pub_res=(1 - 2392343 / (8349459 + 608214)) * (1 - 0.489),
    soglie={"NICE limite basso": 25000, "NICE limite alto": 35000},  # PMG36 6.3.4-6.3.8
)

# Danimarca (DK)
PPP["DK"] = 9.62319  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/DK/eurostat_prc_ppp_ind_1_2025_DK_AT.json)

STATI["DK"] = dict(
    valuta="DKK",
    # Finansministeriet, Noegletalskatalog giugno 2026: 3,5 % anni 0-35; Medicinraadet metodevejledning 6.9
    sconto=0.035,
    # DkDRG 2025 26MP19 "Hydrocephalus" 134.750 DKK, trimpunkt 11 (Takstsystem 2025 v1.2, Bilagstabel 5,
    # fonti/DK/sds_takstsystem_2025.txt r. 2574). Prezzo 2025.
    tariffa=134750,
    revisione=134750,  # stesso gruppo: assunzione dichiarata
    # DST REGK31 2024, bruttoudgifter meno entrate 7.7 da altri comuni: 5.30.26 (16.671.738 - 351.923) + 5.38.38
    # (1.851.471 - 69.928) migliaia di DKK / AED022 2024 visiterede timer pr. uge 476.833 x 365/7 = 728,0 DKK
    # per ora concessa (2024); x HICP CP13303 DK 2024->2025 (100/95,35) = 763,5
    ora_tot=(16671738 - 351923 + 1851471 - 69928) * 1000 / (476833 * 365 / 7) * 100 / 95.35,
    # REGKC 5.30.26 gruppo 92, netto 2024: 467.715 / 16.319.815 (sola 5.30.26)
    quota_pub_dom=1 - 467715 / (16671738 - 351923),
    # DST REGK31 2024 5.30.27 bruttoudgifter 32.889.491 meno 7.7 2.200.404 migliaia di DKK / 44.660 posti
    # (inizio 2024) / 365 = 1.882,7 (2024); x HICP CP13302 DK 2024->2025 (100/91,93) = 2.047,9.
    # Affitto della plejebolig escluso
    giorno_tot=(32889491 - 2200404) * 1000 / 44660 / 365 * 100 / 91.93,
    # REGKC 5.30.27 gruppi 93 + 94 + 96, netto 2024: 1.919.368 / 30.689.087
    quota_pub_res=1 - 1919368 / (32889491 - 2200404),
    # nessuna soglia ufficiale: 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 519.080 DKK)
    soglie={"1 x PIL pro capite": 519080, "3 x PIL pro capite": 1557240},
)

# Paesi Bassi (NL)
PPP["NL"] = 1.17334  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/NL/Eurostat_prc_ppp_ind_1_NL.json)

STATI["NL"] = dict(
    valuta="EUR",
    sconto=0.03, sconto_esiti=0.015,  # Kostenhandleiding 2024 (Zorginstituut), 2.6.1.2: 3 % costi, 1,5 % effetti
    # Media ponderata per paziente dei prodotti DBC con zorgactiviteit 030253 e diagnosi 1710,
    # anno DBC 2025 (Open DIS NZa, CSV completi 01_DBC e 02_DBC_PROFIEL), 379 pazienti su 423
    # con prezzo = 10.631,73. Prezzo 2025.
    tariffa=10631.73,
    # Media ponderata 030252, diagnosi 1710, 2025 = 9.805,88
    revisione=9805.88,
    # Wlz mpt 2025 (voorlopig), persoonlijke verzorging: 455.112 k EUR / 6.638 k ore = 68,56 (CBS MLZ 40079NED)
    ora_tot=455112 / 6638,
    # Quota coerente con la fonte del costo (Wlz mpt):
    # eigen bijdrage 48.450 persone x 60,30 EUR/mese x 12 / 1.000 = 35.058 k EUR su 2.101.447 k EUR -> 0,983 (CBS 40074NED)
    quota_pub_dom=1 - (48450 * 60.30 * 12 / 1000) / 2101447,
    # Wlz verblijf, totale zzp VV 2025 (voorlopig): 15.849.052 k EUR / 45.053 k giorni = 351,79 (40079NED)
    giorno_tot=15849052 / 45053,
    # eigen bijdrage media, eta' AOW, solo verblijf, 2025: 1.015,51 EUR/mese (40074NED, CAK) -> quota 0,905
    quota_pub_res=1 - (1015.51 * 12 / 365) / (15849052 / 45053),
    # Referentiewaarden Zorginstituut per classe di ziektelast (2015)
    soglie={"ziektelast 0,1-0,4": 20000, "ziektelast 0,41-0,7": 50000, "ziektelast 0,71-1,0": 80000},
)

# Portogallo (PT)
PPP["PT"] = 0.839373  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/PT/eurostat_prc_ppp_ind_1_PT_SE.json)

STATI["PT"] = dict(
    valuta="EUR",
    sconto=0.04,  # INFARMED, Orientacoes metodologicas 2019 (fonti/PT/INFARMED_orientacoes_2019.txt r. 291-292)
    # GDH APR36 022 "Procedimentos de shunt ventricular" SOI 1: 1,1268 x preco base 3.300 = 3.718,44
    # (Portaria 274/2026/1, Anexo II Tab. I, col. F; fonti/PT/portaria_274_2026_detalhe.md r. 559, 613).
    # In vigore dal 1/7/2026: prezzo 2026 assunto come 2025 (deviazione ammessa, come SE e PL)
    tariffa=3718.44,
    revisione=3718.44,  # stesso GDH 022: assunzione dichiarata (come ES e SE)
    # Importo pubblico per ora, con le ore dell'equivalente svedese.
    # Comparticipacao SS SAD 362,49 EUR/utente/mese 2025 (Compromisso 2025-2026, Anexo I punto 12, p. 48;
    # Adenda r. 399) x 12 = 4.349,88 / 417,24 ore annue (Kolada N21826 2025, 34,77 h/mese) = 10,43 EUR/ora.
    # Costo totale e ore non pubblicati: prospettiva totale non calcolabile (come PL)
    ora_tot=None, ora_pub=362.49 * 12 / (34.77 * 12), quota_pub_dom=None,
    # ERPI, custo medio real 2025 1.629,15 EUR/utente/mese (Compromisso Cl. XIX n. 1, p. 14) x 12 / 365 = 53,56
    giorno_tot=1629.15 * 12 / 365,
    # comparticipacao SS regular 666,90 (Anexo I punto 13, p. 48; Adenda r. 411) -> 0,409
    quota_pub_res=666.90 / 1629.15,
    # nessuna soglia di accettazione: 1 e 3 x PIL pro capite 2025 (Eurostat, provvisorio)
    soglie={"1 x PIL pro capite": 28560, "3 x PIL pro capite": 85680},
)

# Lettonia (LV)
PPP["LV"] = 0.792998  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/LV/eurostat_prc_ppp_ind_1_LV_SE.json)

STATI["LV"] = dict(
    valuta="EUR",
    sconto=0.05,  # 5 % costi e benefici: MK not. Nr. 899 (2006), 3. pielikums p. 17 (fonti/LV/likumi_MK899_2006.md r. 2494)
    # NordDRG 001D 2025, coefficiente 2,5118 (NVD, DRG raditaji; fonti/LV/nvd_drg_raditaji_2026.md r. 14).
    # Mediana dei tre prodotti 2025 per adulti = 2,5118 x base PSKUS 1.375,33
    # = 3.454,55 (r. 887-888). Basi 2025 gia' ridotte al finanziamento disponibile (nota **). Prezzo 2025.
    tariffa=2.5118 * 1375.33,
    revisione=2.5118 * 1375.33,  # AAF20 nello stesso gruppo: NordDRG comune (nat_ver "lat")
    # Importo pubblico per ora del solo comune di Riga (82 % della spesa comunale nazionale 2025).
    # (9.968.888 - 149.740) / (1.227.686 / 1,02) = 8,16 EUR/ora (T1 2025, stesso anno di prezzo;
    # fonti/LV/lvportals_389782_riga_aprupe_majas_2026Q1.txt r. 1659, 1668); 8,12-8,20 in sensibilita'
    ora_tot=None, ora_pub=(9968888 - 149740) / (1227686 / 1.02), quota_pub_dom=None,
    # centri comunali e di altri enti per adulti 2025 (LM, tab. 7.2, cod. 0721): 1.130,98 EUR/mese x 12 / 365 = 37,18
    # (fonti/LV/lm_1_ilgst_aprupe_sac_2025.md r. 3331)
    giorno_tot=1130.98 * 12 / 365,
    # entrate di Stato, comuni e dotazione statale / entrate totali 2025 (tab. 6.1, r. 2863) = 0,408
    quota_pub_res=49460952 / 121269462,
    # soglia di legge: ICER <= 3 x PIL pc dell'anno precedente (MK 899, p. 39 e 46.2); Eurostat 2025 23.560
    soglie={"soglia di legge (3 x PIL pc 2025, Eurostat)": 70680},
)

# Repubblica Ceca (CZ)
PPP["CZ"] = 20.4156  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/CZ/eurostat_prc_ppp_ind_1_CZ_SE.json)

STATI["CZ"] = dict(
    valuta="CZK",
    sconto=0.03,  # SUKL SP-CAU-028 v5 (in vigore 17/1/2022), r. 615-617: 3 % costi e benefici
    # CZ-DRG 01-I07-03 2025 (vyhlaska 314/2024 Sb., Priloha 10 cast E): peso 2,64740 x CZS 81.000 = 214.439 Kc;
    # gruppo misto, CC 0-3 (fonti/CZ/vyhlaska_314_2024_uhradova_2025_extract.md r. 14, 22). Prezzo 2025.
    tariffa=2.64740 * 81000,
    # stesso výkon 56125 "operacni revize nebo zavedeni", stessa base 01-I07, letto (materiali CZ-DRG v2026,
    # priloha 31 r. 2031)
    revisione=2.64740 * 81000,
    # Metodo CSU: pecovatelska sluzba 2025 (MPSV rocenka 2025, fogli 5.7 e 5.6, Celkem CR): spesa
    # 6.563.775 tis. Kc / ore stimate = uhrady 1.353.149 tis. / 165 Kc (vyhl. 195/2024) -> 800,4 Kc/h
    ora_tot=6563775e3 / (1353149e3 / 165),
    # 1 - uhrady / spesa = 0,794, limite inferiore dichiarato (prispevek contato come spesa
    # dell'utente), con l'asimmetria rispetto alla residenza (dove il prispevek conta pubblico) dichiarata
    quota_pub_dom=1 - 1353149 / 6563775,
    # DS + DZR 2025: spesa 44.542.407,382 tis. Kc (foglio 5.7 r. 36) / residenti medi 59.703,3 / 365 = 2.044,0 Kc/giorno
    giorno_tot=44542407.382e3 / 59703.3 / 365,
    # Prispevek pubblico: 1 - tetto alloggio e vitto 2025 (560 x 59 + 575 x 306; vyhl. 48/2025 dal 1/3/2025)
    # / costo per residente = 0,720 (limite basso)
    quota_pub_res=1 - (560 * 59 + 575 * 306) / (44542407.382e3 / 59703.3),
    # soglia SUKL applicata, 1,2 mln Kc/QALY (SP-CAU-028 r. 1067-1068)
    soglie={"SUKL, soglia applicata": 1200000},
)

# Slovacchia (SK)
PPP["SK"] = 0.804917  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/SK/eurostat_prc_ppp_ind_1_SK_RO_BG_SE.json)

STATI["SK"] = dict(
    valuta="EUR",
    sconto=0.05,  # vyhlaska 422/2011 Z. z. par. 1 ods. 1 g) (znenie 1.6.2021): 5 % costi e benefici
    # SK-DRG 2025 B20D RV 2,463 (fonti/SK/cksdrg_KPP_2025_v3.xlsx r. 82) x Celoslovenska referencna zakladna
    # sadzba 2025 3.269 EUR (fonti/SK/cksdrg_Zakladne_sadzby_2025.txt r. 247) = 8.051,5.
    # Nel 2025 B20 non e' pagato a caso (vyhl. 62/2025): prezzo di catalogo. Valvola nel DRG. Prezzo 2025.
    tariffa=2.463 * 3269,
    # B18Z RV 1,5756 (KPP 2025 r. 78) x 3.269 = 5.150,6
    revisione=1.5756 * 3269,
    # opatrovatel'ska sluzba 2024 (Sprava SoS 2024, tab. 37 e p. 129-130): 83.686.317 EUR / 7.805.255 ore = 10,72
    # x HICP CP00 SK 2025/2024 = 149,23 / 143,17 -> 11,18
    ora_tot=83686317 / 7805255 * (149.23 / 143.17),
    quota_pub_dom=1 - 12920887 / 83686317,  # uhrady 12.920.887 (tab. 36) / spesa; fondi UE contati pubblici
    # zariadenie pre seniorov 2024: EON 1.404 EUR/posto/mese (tab. 32) x 12 / 365 x HICP CP00 SK -> 48,11
    giorno_tot=1404 * 12 / 365 * (149.23 / 143.17),
    quota_pub_res=225649042 / 356946580,  # entrate pubbliche / entrate totali ZpS 2024 (tab. 31) = 0,632
    # soglia di legge: 2 o 3 x PIL pro capite secondo il guadagno di QALY (zakon 363/2011 par. 7, vyhl. 298/2022
    # par. 1); PIL pc 2025 Eurostat 25.470
    soglie={"2 x PIL pc (di legge)": 2 * 25470, "3 x PIL pc (di legge)": 3 * 25470},
)

# Bulgaria (BG)
PPP["BG"] = 0.637453  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025, EUR per PPS (fonti/BG/eurostat_prc_ppp_ind_1_SK_RO_BG_SE.json)

STATI["BG"] = dict(
    valuta="EUR",  # importi 2025 in leva convertiti a 1,95583 (Reg. UE 2025/1409)
    sconto=0.035,  # PMS 56/2019 (fonti/BG/dv_136245.txt r. 497-498) e Naredba 7/2021 (dv_166133.txt r. 192)
    # KP 207 2025: 3.590 lv (NRD 2023-2025 mod. 22/5/2025, chl. 368b; nzok_NRD_..._2025-05-22.txt r. 1657)
    # + valvola gruppo 11 pagata dalla NZOK fuori dal prezzo fino a 1.080 lv (Spisak MI NZOK dal 1/1/2025, r. 1268-1307;
    # nomenklatura 21/7/2025 r. 1832) = 4.670 lv = 2.387,73 EUR
    tariffa=(3590 + 1080) / 1.95583,
    # 40009-00 in KP 207 con gruppo 11 (nomenklatura r. 1838): con valvola
    revisione=(3590 + 1080) / 1.95583,
    # Importo pubblico per ora: asistentska podkrepa, standard statale
    # 8.096 lv/utente 2025 (RMS 93/2025, all. 4, r. 854-856) / 417,24 ore (Kolada N21826 2025) = 19,40 lv/ora
    # = 9,92 EUR/ora. Solo prospettiva pubblica
    ora_tot=None, ora_pub=8096 / 1.95583 / (34.77 * 12), quota_pub_dom=None,
    # Dom za stari hora, standard statale 23.028 lv/posto 2025 (RMS 93/2025, all. 4, r. 764-766) / 365
    # = 63,09 lv = 32,26 EUR/giorno pubblici; costo totale non noto.
    giorno_tot=None, giorno_pub=23028 / 365 / 1.95583, quota_pub_res=None,
    # nessuna soglia ufficiale: 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 18.120 EUR)
    soglie={"1 x PIL pro capite": 18120, "3 x PIL pro capite": 54360},
)

# Svizzera (CH)
PPP["CH"] = 1.46241  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/CH/Eurostat_prc_ppp_ind_1_CH_SE_GDP.json)

STATI["CH"] = dict(
    valuta="CHF",
    # Nessun tasso ufficiale (BAG, Operationalisation EAE 2022); 3 % = prassi
    # dei rapporti HTA commissionati dal BAG (h0068 2024, h0076 2024, RSVpreF 2025; fonti/CH/sconto/)
    sconto=0.03,
    # SwissDRG 14.0 (2025) B09C, peso 1,627 (fonti/CH/swissdrg_fpk_14_abrechnung.txt r. 500-502). Baserate =
    # media delle tariffe di riferimento 2025 di Berna (9.940 e 11.267) e Zurigo (9.990 e 11.000) = 10.549,25 CHF
    # (be_referenztarife_2025.txt r. 23-26; zh_referenztarife_ab_2025.txt r. 174-176). Prezzo 2025.
    tariffa=1.627 * 10549.25,
    revisione=1.627 * 10549.25,  # sostituzione 02.42.x in tab. B09-5: B09C, letto
    # ora di cura KVG a domicilio 2024 (dedotto): OKP 59 (BFS, media 2022, tariffe KLV 7a ferme dal 2020) + residuo
    # Cantoni e Comuni 43,06 (INFRAS tab. 7) + sussidi 0,191 mld + pazienti/EL 0,137 mld (INFRAS tab. 10) su 25,6 mln
    # di ore (BFS 2024) = 114,87; x HICP CP13303 CH 2024->2025 (100/98,96) = 116,08
    ora_tot=(59 + 43.06 + 0.191e9 / 25.6e6 + 0.137e9 / 25.6e6) * 100 / 98.96,
    quota_pub_dom=1 - (0.137e9 / 25.6e6) / (59 + 43.06 + 0.191e9 / 25.6e6 + 0.137e9 / 25.6e6),  # 0,953
    # Pflegeheim 2024: 362,52 CHF/giorno (Curaviva su BFS SOMED 2024; curaviva_pflegefinanzierung_2025.txt r. 11-15)
    # x HICP CP13303 CH (CP13302 senza valori per CH) = 366,33
    giorno_tot=362.52 * 100 / 98.96,
    # pubblico = cura KVG 158,44 - partecipazione 0,660 mld / 33.277.724 giorni (19,83) + altri costi OKP 5,31 -> 0,397
    quota_pub_res=(158.44 - 0.660e9 / 33277724 + 5.31) / 362.52,
    # nessuna soglia (BAG 2022): 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 95.380 CHF)
    soglie={"1 x PIL pro capite": 95380, "3 x PIL pro capite": 286140},
)

# Austria (AT)
PPP["AT"] = 1.13969  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/AT/eurostat_prc_ppp_ind_1_2025_DK_AT.json)

STATI["AT"] = dict(
    valuta="EUR",
    # GOEG Methodenhandbuch HTA 1.2012, 8.4.2.11 (3 %), non vincolante (AIHTA 2026).
    # Walter e Zehetmayr 2006 (consenso IPF, Wien Med Wochenschr 156:628-632, sez. 10, p. 632) raccomanda 5 %:
    # 3 % nel caso base, 5 % come estremo alto della sensibilita' 0-5 %
    sconto=0.03,
    # Punti LKF letti nelle edizioni 2026 e 2027 e applicati al 2025 (MEL01.02 assente dalle modifiche 2026, base
    # di costo 2022 invariata): impianto AC020 -> MEL01.02 B 14.604 punti (bmsgpk_2026_anlage4_ldf_tabellen.txt r. 1329).
    # Euro per punto 2025: mediana 1,80 dei cinque ospedali
    # centrali, Graz 2,09, Salzburg CDK 2,01, Klagenfurt 1,80 (LKF-Gebuehr), Feldkirch 1,78, Innsbruck 1,61
    # (LGBl dei Laender 2024-2025); insieme allargato 1,61-2,41 in sensibilita'
    tariffa=14604 * 1.80,
    revisione=7964 * 1.80,  # AC030 -> MEL01.02 D 7.964 punti (r. 1333)
    # solo importo pubblico per ora (forma della Polonia): Statistik Austria 2024, mobile Dienste,
    # (Bruttoausgaben 855.068.860,75 - Beitraege und Ersaetze 150.231.325,09) / Leistungsstunden 15.393.520,39
    # = 45,79 (2024); x HICP CP13303 AT 2024->2025 (100/93,95) = 48,74
    ora_tot=None, ora_pub=(855068860.75 - 150231325.09) / 15393520.39 * 100 / 93.95, quota_pub_dom=None,
    # Statistik Austria 2024, stationaere Dienste: Bruttoausgaben 4.698.041.915,47 / Bewohntage 25.367.976 = 185,20;
    # x HICP CP13302 AT 2024->2025 (100/94,97) = 195,00
    giorno_tot=4698041915.47 / 25367976 * 100 / 94.97,
    # (Nettoausgaben 2.818.822.232,94 + sonstige Einnahmen 140.528.812,68) / Brutto = 0,630 (Pflegegeld del residente)
    quota_pub_res=(2818822232.94 + 140528812.68) / 4698041915.47,
    # nessuna soglia: 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 56.300 EUR)
    soglie={"1 x PIL pro capite": 56300, "3 x PIL pro capite": 168900},
)

# Finlandia (FI)
PPP["FI"] = 1.18501  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/FI/Eurostat_prc_ppp_ind_1_FI_SE_GDP.json)

STATI["FI"] = dict(
    valuta="EUR",
    sconto=0.03,  # Hila, Hakemusohje TTS 1.7.2026, par. 2.9 (fonti/FI/hila_hakemusohje_TTS_010726.txt r. 444)
    # Costo medio nazionale THL 2017 per
    # NordDRG 001D, 8.652,6 EUR per episodio su 720 casi (fonti/FI/TYO 2020_21_Liitetaulukot 1-4.xlsx.txt r. 182,
    # Liitetaulukko 4), x KHI 2015=100, 2025 / 2017 = 122,74 / 101,10 (fonti/FI/statfin_khi_11xc_2015-2025.csv r. 12, 4;
    # rivalutazione con il KHI prescritta da Hila, hila_hakemusohje_TTS_010726.txt r. 290) = 10.504,65.
    # Listino KYS 2025 7.700 (kys_kliiniset_hinnat_2025.md r. 381) in sensibilita'
    tariffa=8652.6 * 122.74 / 101.10,
    revisione=8652.6 * 122.74 / 101.10,  # stesso gruppo: assunzione dichiarata
    # Sotkanet 5800 (classe 2235, Koko maa, 2025) 1.760.208 k EUR / (THL kotihoito 2025: 38.044.782 visite x 21 min / 60)
    # = 132,19 EUR per ora di visita (visite di tutte le eta', costi dei soli anziani)
    ora_tot=1760208000 / (38044782 * 21 / 60),
    # limite inferiore: 1 - ricavi 5801 / costi 5800 = 1 - 316.845 / 1.760.208 = 0,820
    quota_pub_dom=1 - 316845 / 1760208,
    # THL costo unitario 2024, palveluasuminen 24h anziani, 200 EUR/giorno (thl_yksikkokustannukset.md r. 130)
    # x KHI 2025/2024 = 122,74 / 122,33 -> 200,67
    giorno_tot=200 * 122.74 / 122.33,
    quota_pub_res=1 - 822836 / 3752383,  # limite inferiore: 1 - ricavi 4693 / costi 4686, 2025 = 0,781
    # nessuna soglia ufficiale: 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 49.870 EUR)
    soglie={"1 x PIL pro capite": 49870, "3 x PIL pro capite": 149610},
)

# Lituania (LT)
PPP["LT"] = 0.8063  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/LT/Eurostat_prc_ppp_ind_1_LT_SE_GDP.json)

STATI["LT"] = dict(
    valuta="EUR",
    sconto=0.035,  # SAM isakymas Nr. 159, p. 153 (fonti/LT/etar_kompensavimo_sarasai_tvarka_159.md r. 3866)
    # VLK, prezzo del caso di durata media dal 1/1/2026 (fonti/LT/vlk_stacionaro_drg_kainos_2026.md r. 25):
    # B02C "Kaukoles proceduros, nesudetinga" 5.089,85; prezzo 2026 assunto come 2025 (deviazione ammessa)
    tariffa=5089.85,
    revisione=2933.30,  # B01B "Skilvelio sunto revizija, nesudetinga", gruppo proprio (r. 22)
    # SPPD, "Pagalba i namus" anziani (310), media nazionale dei comuni, 12 mesi fino al 1/2/2026: 12,09 EUR/h
    # (fonti/LT/sppd_vidutines_kainos_iki_2026-02-01.md r. 129)
    ora_tot=12.09,
    # 1,0, limite superiore
    # (il comune paga il prezzo, l'utente contribuisce fino al 20 % del reddito); non e' un valore letto
    quota_pub_dom=1.0,
    # Coppia coerente dei residenti
    # con grave disabilita', 1.865,99 EUR/mese (r. 302) x 12 / 365 = 61,35; dotazione statale massima 1.169 EUR/mese
    # (A1-426 in vigore dal 1/1/2026, r. 283) / 1.865,99 = 0,6265
    giorno_tot=1865.99 * 12 / 365,
    quota_pub_res=1169 / 1865.99,
    # SAM, opuscolo: 1, 3 o 5 x PIL pro capite secondo la gravita'; Eurostat 2025 29.460 EUR
    soglie={"1 x PIL pro capite": 29460, "3 x PIL pro capite": 88380, "5 x PIL pro capite": 147300},
)

# Slovenia (SI)
PPP["SI"] = 0.877224  # Eurostat prc_ppp_ind_1, PPP_EU27_2020, GDP, 2025 (fonti/SI/eurostat_prc_ppp_ind_1_SI.json)

STATI["SI"] = dict(
    valuta="EUR",
    # Pravilnik ZZZS o razvrscanju zdravil, 12. clen (2): 3-5 %; usato 4 %, centro dell'intervallo
    sconto=0.04,
    # SPP 2026 (ZZZS, Priloga 1.1, Sklep 8.4.2026, foglio 1.1 r. 19): B02C peso 4,29 x 1.912,17 EUR (Uredba 2026, Z0034,
    # uredba2026_priloga1.txt r. 16) = 8.203,21; prezzo "brez LZM in dodatkov". Prezzo 2026 assunto come 2025
    tariffa=4.29 * 1912.17,
    revisione=3.00 * 1912.17,  # B01Z "Revizija ventrikularnega santa", peso 3 (r. 16) -> 5.736,51
    # DO na domu, sklop A: 32,93 EUR/h, prezzo unico nazionale (prirocnik MSP luglio 2025, r. 1220-1240); prezzo 2025.
    # Nessuna partecipazione dell'utente prima del 1/1/2028 (r. 1187-1190)
    ora_tot=32.93,
    quota_pub_dom=1.0,
    # massimali pubblici mensili in ore della categoria (20, 60, 80, 110; r. 296-300), pagate a ora_tot, con mRS 0-2 ->
    # cat. 1, 3 -> cat. 3, 4 -> cat. 4, 5 -> cat. 5 (assunzione dichiarata, come per la Germania). In ore e non in euro:
    # il tetto segue il prezzo orario nella sensibilita' (il massimale tedesco e' invece un importo di legge in euro)
    massimale_ore_dom={"0-2": 20, "3": 60, "4": 80, "5": 110},
    # residenza: DO ZZZS pagamenti giu-set 2026 (servizi apr-lug, ritardo di due mesi assunto) 101.695.500,19 /
    # (122 giorni x 20.042 residenti al 16/1/2026) = 41,59 + nega ZZZS 2025 246,25 mln / 8.282.627 giorni pagati = 29,73
    # + quota del residente 738,49 x 12 / 365 = 24,28 (calcolatore MSP, ott. 2025) = 95,60
    giorno_tot=41.59 + 29.73 + 738.49 * 12 / 365,
    # limite inferiore (quota dei comuni per gli indigenti non separabile): 0,746
    quota_pub_res=(41.59 + 29.73) / (41.59 + 29.73 + 738.49 * 12 / 365),
    # nessuna soglia: 1 e 3 x PIL pro capite 2025 (Eurostat nama_10_pc, 33.380 EUR)
    soglie={"1 x PIL pro capite": 33380, "3 x PIL pro capite": 100140},
)


def costo_atteso_trattamento(s):
    """K grezzo: intervento + revisioni attese in 10 anni, scontate, senza morte competitiva."""
    r = s["sconto"]
    succ = sum(P_REV_ANNI_SUCC / (1 + r) ** t for t in range(1, 10))
    return s["tariffa"] + s["revisione"] * (P_REV_ANNO1 + succ)


def costo_annuo_per_mrs(s, prospettiva, ore=None, giorni=None):
    """ore, giorni: volumi per mRS; di default quelli di Lekander 2017 (sensibilita')."""
    ore = ore or ORE_DOMICILIO
    giorni = giorni or GIORNI_RESIDENZA
    out = {}
    for k in ore:
        if prospettiva == "totale":
            ora = s["ora_tot"]
            giorno = s["giorno_tot"]
        else:
            ora = s.get("ora_pub") or (s["ora_tot"] * s["quota_pub_dom"] if s["quota_pub_dom"] else None)
            # giorno_pub: solo l'importo pubblico per giorno (Bulgaria), come ora_pub per la Polonia
            giorno = s.get("giorno_pub") or s["giorno_tot"] * s["quota_pub_res"]
        if prospettiva == "pubblica" and ("massimale_dom" in s or "massimale_ore_dom" in s):
            # massimale_dom: euro al mese (DE); massimale_ore_dom: ore al mese pagate a ora_tot (SI)
            tetto = (s["massimale_dom"][k] if "massimale_dom" in s
                     else s["massimale_ore_dom"][k] * s["ora_tot"])
            dom = min(ore[k] * s["ora_tot"], tetto * 12)
            out[k] = dom + giorni[k] * giorno
            continue
        if ora is None or giorno is None:
            out[k] = None
            continue
        out[k] = ore[k] * ora + giorni[k] * giorno
    return out


# Mix di dipendenza alla diagnosi per l'indicatore di tappa_A.csv (assunzione dichiarata:
# 55 % mRS 0-2 da Andren 2014; il resto ripartito 2:1 fra mRS 3 e 4, nessun mRS 5)
MIX_DIAGNOSI = {"0-2": 0.55, "3": 0.30, "4": 0.15, "5": 0.0}


def main():
    righe, tappa = [], []
    for st, s in STATI.items():
        K = costo_atteso_trattamento(s)
        pub = costo_annuo_per_mrs(s, "pubblica")
        assist_anno = sum(MIX_DIAGNOSI[k] * pub[k] for k in pub)
        print(f"{st}: K {K:,.0f} {s['valuta']}; assistenza pubblica annua al mix di diagnosi "
              f"{assist_anno:,.0f}; anni di assistenza che pagano l'intervento {K / assist_anno:.2f}")
        for prosp in ("pubblica", "totale"):
            for mrs, c in costo_annuo_per_mrs(s, prosp).items():
                righe.append(dict(stato=st, valuta=s["valuta"], prospettiva=prosp, mrs=mrs,
                                  costo_annuo=None if c is None else round(c),
                                  costo_annuo_eur_pps=None if c is None else round(c / PPP[st])))
        for nome, lam in s["soglie"].items():
            tappa.append(dict(stato=st, valuta=s["valuta"], K=round(K), K_eur_pps=round(K / PPP[st]),
                              soglia=nome, lambda_=lam, q_star=round(K / lam, 3)))
    with open(QUI / "input_armonizzati.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(righe[0]))
        w.writeheader(); w.writerows(righe)
    with open(QUI / "tappa_A.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tappa[0]))
        w.writeheader(); w.writerows(tappa)
    for r in tappa:
        print(r)
    for r in righe:
        print(r)


if __name__ == "__main__":
    main()
