#!/bin/python3
import numpy as np
import pandas as pd
import os
import sys
from openpyxl import load_workbook
from splitCoalitionVotes import *

ELECTION_RESULTS_FOLDER = "Nikola/rezultati/parlamentarni 2024 XLSX"
PARTITION_SOURCE = "data/zupanija_144.part"
MASTER_BM_FILE = "Mislav/geocoded/02_all_geocoded.xlsx"
VOTES_OUTPUT_FILE = "preracunati_glasovi_2024"

PARTIES_BY_SIZE_FILE = "Nikola/parties_by_size.txt"
RELATIVE_PARTY_SIZES_FILE = "Nikola/IPSOS_crobarometar/anketa_2024_3_25.txt"

ASSUME_MAX_CANDIDATES = False # pretpostavlja li da svaka lista ima točno 15 kandidata (ubrzava učitavanje podataka)

# boje za ispis
OK = '\033[92m'
WARN = '\033[93m'
ERR = '\033[91m'
END = '\033[0m'

ID_mapping = {}

def get_intresecting_nonsubsets(liste):
    nonsubsets = []
    for l_i in liste:
        for l_j in liste:
            sl_i = set(l_i); sl_j = set(l_j)
            if sl_i & sl_j  and sl_i - sl_j and sl_j - sl_i:
                nonsubsets.append((sl_i, sl_j))
    return nonsubsets

def max_joint_coalition_components(liste):
    # razdvaja koalicije u podskupove sačinjene od stranaka koje su u svim izbornim jedinicama zajedno u koaliciji
    # VAŽNO: mijenja ulazni set "liste"
    liste2 = set()
    while True:
        for l1 in liste:
            l1 = frozenset(l1)
            inter = False
            for l2 in liste:
                l2 = frozenset(l2)
                if l1 != l2 and l1 & l2:
                    inter = True
                    liste2.add(l1 & l2)
                    if l1 - l2:
                        liste2.add(l1 - l2)
                    if l2 - l1:
                        liste2.add(l2 - l1)
            if not inter:
                liste2.add(l1)
        if liste == liste2:
            break
        liste = liste2.copy()
        liste2 = set()
    return liste

def load_partition(partition_source, n_BM):
    partition = np.zeros(n_BM, dtype=int)
    # UCITAVANJE IZ JEDNE DATOTEKE
    if os.path.isfile(partition_source):
        if partition_source.endswith(".part"):
            partition_file = open(partition_source, "r")
            try:
                for line in partition_file:
                    ID_bm, ID_ij = map(int, line[:-1].split(" : "))
                    partition[ID_bm] = ID_ij
            except:
                print(f"{ERR + partition_source + END} could not be loaded")
                raise sys.exception()
            print(f"loaded partition info from {partition_source} {OK}OK{END}")
        else: 
            print(f"{ERR + partition_source + END} is not a \".part\" file, contents are not loaded")
    # UCITAVANJE IZ DATOTEKA PO ZUPANIJAMA
    else:
        for file in os.scandir(partition_source):
            if file.is_file() and file.name.endswith(".part"):
                i_zup = int(file.name.split(".")[0].rsplit("_")[1])
                part_file = open(file, "r")
                try:
                    for line in part_file:
                        ID_u_zup, ID_ij = map(int, line[:-1].split(" : "))
                        partition[ID_mapping[(i_zup, ID_u_zup)]] = ID_ij
                except:
                    print(f"{ERR + file.name + END} could not be loaded")
                    raise sys.exception()
                print(f"loaded partition info from {file.name} {OK}OK{END}")
            elif file.is_file():
                print(f"{WARN + file.name + END} is not a \".part\" file, contents are not loaded")
    return partition

def main():
    # učitava popis stranaka, izbornih listi i izbornih isti za svaku teritorijalnu izbornu jedinicu u trenutnom sustavu 
    stranke = set()
    liste = set()
    popisi_lista_po_IJ = []
    all_dfs = []
    n_BM = 0
    for file in os.scandir(ELECTION_RESULTS_FOLDER):
        if file.is_file() and (file.name.endswith(".xlsx") or file.name.endswith(".xls")):
            df = pd.read_excel(file.path)
            all_dfs.append(df)
            n_BM += len(df)
            if ASSUME_MAX_CANDIDATES: # pretpostavlja da svaka lista ima naziv i 14 kandidata 
                # (smisleno, jer je listama u interesu da predlože maksimalan dozvoljen broj kandidata)
                list_indices = list(range(15, len(df.columns), 15))
            else:
                # po narančastoj boji ćelija raspoznaje imena lista od imena kandidata
                # sporije nego pandas jer učitava podatke o formatiranju Excel datoteke
                workbook = load_workbook(file.path, data_only = True)
                header = workbook['rezultati'][1]
                list_indices = [i for i in range(len(header)) if header[i].fill.start_color.index == 9]
            for i in list_indices:
                stranke = stranke | set(df.columns[i].split(", "))
            nove_liste = set(tuple(df.columns[i].split(", ")) for i in list_indices)
            liste = liste | nove_liste
            popisi_lista_po_IJ.append(nove_liste)
            print(f"loaded file {file.name} {OK}OK{END}" )
        elif file.is_dir():
            print(f"{WARN + file.name + END} is a directory, contents are not loaded")
        else:
            print(f"{WARN + file.name + END} is not xlsx or xls, contents are not loaded")

    # mapira ID unutar županije na globalni ID
    master_BM_df = pd.read_excel(MASTER_BM_FILE)
    for i, row in master_BM_df.iterrows():
        ID_mapping[(row["Rbr.županije"], row["ID_u_zupaniji"])] = row["ID_global"]
    
    # nova raspodjela BM u izborne jedinice
    jedinice_bm = load_partition(PARTITION_SOURCE, n_BM)
    # nadopuna raspodjele biračkim mjestima bez dodijeljene jedinice, a koja imaju jednake geografske koordinate kao neko od raspodijeljenih
    print("inferring which partition remaining BMs belong to...")
    long_series = master_BM_df["Longitude"]
    lat_series = master_BM_df["Latitude"]
    for i in range(n_BM):
        if jedinice_bm[i] == 0:
            longitude = long_series[i]
            latitude = lat_series[i]
            for j in range(n_BM):
                if long_series[j] == longitude and lat_series[j] == latitude and jedinice_bm[j] != 0:
                    jedinice_bm[i] = jedinice_bm[j]
                    break
            else:
                raise RuntimeError(f"Could not deduce partition for BM with ID_global = {i}")

    n_IJ_original = len(all_dfs)
    n_IJ_novi = np.max(jedinice_bm) + 1
    komponente_lista = list(max_joint_coalition_components(liste.copy()))
    print(len(komponente_lista))
    # for i in liste: print(i)
    # for i in komponente_lista: print("-", i)
    # for i, popis in enumerate(popisi_lista_po_IJ):
    #     print(i, ":", popis)
    
    # dijeli izborne liste na najveće komponente sačinjene od stranaka koje su u svim izbornim jedinicama izašle zajedno
    coalition_splitter = SplitCoalitionVotes(komponente_lista)
    coalition_splitter.add_rules([
        ProportionalToWeightRule.from_file(RELATIVE_PARTY_SIZES_FILE, sep=":"),
        LargestPartyComponentRule.from_file(PARTIES_BY_SIZE_FILE),
        EqualRule()
    ])

    # preracun glasova na nove jedinice
    glasovi = np.zeros((n_IJ_novi, len(komponente_lista)), dtype=int) # broj IJ * broj komponenata listi
    bm_offset = 0
    for i in range(n_IJ_original):
        for lista in popisi_lista_po_IJ[i]:
            osvojeni_glasovi = all_dfs[i][", ".join(lista)]
            res = coalition_splitter(lista)
            print(res)
            for j in range(len(all_dfs[i])):
                for comp, percent in res.items():
                    glasovi[jedinice_bm[bm_offset + j]][komponente_lista.index(comp)] += percent * osvojeni_glasovi[j]
        bm_offset += len(all_dfs[i])
    glasovi_df = pd.DataFrame(glasovi, columns=[", ".join(comp) for comp in komponente_lista])
    print(glasovi_df)
    glasovi_df.to_csv(VOTES_OUTPUT_FILE, sep=";")


# parsiranje argumenata
if __name__ == "__main__":
    if "--help" in sys.argv:
        print("help")
    else:
        if "--fast" in sys.argv:
            print("Fast mode is on. Try removing the --fast option if the results are nonsensible.")
            ASSUME_MAX_CANDIDATES = True
        if "--elect_dir" in sys.argv:
            try: 
                ELECTION_RESULTS_FOLDER = sys.argv[sys.argv.index("--elect_dir") + 1]
            except IndexError:
                print(f"with {ERR}\"--elect_dir\"{END} option, path to a directory containing election results in .xlsx files must be given")
                raise
        if "--part" in sys.argv:
            try: 
                PARTITION_SOURCE = sys.argv[sys.argv.index("--part") + 1]
            except IndexError:
                print(f"with {ERR}\"--part\"{END} option, path to .part partitoning info file or a directory containing multiple such files must be given")
                raise
        # if "--part" in sys.argv:
        #     try: 
        #         PARTITION_PATH = sys.argv[sys.argv.index("--part") + 1]
        #     except IndexError:
        #         print(f"with {ERR}\"--part\"{END} option, partition file path must be given")
        #         
        if "--BM" in sys.argv:
            try: 
                MASTER_BM_FILE = sys.argv[sys.argv.index("--BM") + 1]
            except IndexError:
                print(f"with {ERR}\"--BM\"{END} option, path to an .xlsx file containing BM IDs and locations must be given")
                raise
        if "--OUT" in sys.argv:
            try: 
                VOTES_OUTPUT_FILE = sys.argv[sys.argv.index("--OUT") + 1]
            except IndexError:
                print(f"with {ERR}\"--OUT\"{END} option, output file path for storing recalculated votes must be given")
                raise
        main()