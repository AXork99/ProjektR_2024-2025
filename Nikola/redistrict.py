#!/bin/python3
import numpy as np
import pandas as pd
import os
import sys
from openpyxl import load_workbook
from splitCoalitionVotes import *

PARTITION_PATH = "partition"
ELECTION_RESULTS_FOLDER = "Nikola/rezultati/parlamentarni 2024 XLSX"
ASSUME_MAX_CANDIDATES = False # pretpostavlja li da svaka lista ima točno 14 kandidata (ubrzava učitavanje podataka)
# boje za ispis
OK = '\033[92m'
WARN = '\033[93m'
ERR = '\033[91m'
END = '\033[0m'

def Gallagher_index(votes, mandates):
    vote_percent = votes / np.sum(votes)
    mandates_percent = mandates / np.sum(mandates)
    return 100 * np.sqrt(0.5*np.sum((vote_percent - mandates_percent)*(vote_percent - mandates_percent)))

def Sainte_Lague_index(votes, mandates):
    vote_percent = votes / np.sum(votes)
    mandates_percent = mandates / np.sum(mandates)
    return np.sum((mandates_percent-vote_percent) * (mandates_percent-vote_percent) / vote_percent) 

# mjera koncentracije, inače u ekonomiji za mjerenje razine koncentracije tržišta
def HH_index(shares):
    shares_percent = shares / sum(shares)
    return sum(shares_percent*shares_percent)

# votes: numpy array s brojevima glasova za stranke 0,1,2,...
# step: korak u aritmetičkom nizu djelitelja (npr. 1 za D'Hondtovu metodu, 2 za Sainte Lagueovu)
# total: ukupno mandata za podijeliti
# return: numpy array s mandatima
def DHondt_like(votes, step, total):
    votes_tmp = np.copy(votes)
    mandates = np.zeros(np.size(votes), dtype=int)
    while total > 0:
        index = np.argmax(votes_tmp)
        mandates[index] += 1
        votes_tmp[index] = votes[index] / (step * mandates[index] + 1)
        total -= 1
    return mandates
    # primjer direktne primjene DH i SL
        # votes = np.array([49202, 38701, 36702, 15586, 14134, 11039])
        # rez = DHondt_like(votes, 1, 14)
        # print(rez)
        # rez = DHondt_like(votes, 2, 14)
        # print(rez)

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

def load_partition(file):
    partition_file =  open(file, "r")
    return np.array([int(line[:-1]) for line in partition_file.readlines()])

def main():
    jedinice_bm = load_partition(PARTITION_PATH)
    names = []
    paths = []
    stranke = set()
    liste = set()
    popisi_lista_po_IJ = []
    all_dfs = []
    for file in os.scandir(ELECTION_RESULTS_FOLDER):
        if file.is_file() and (file.name.endswith(".xlsx") or file.name.endswith(".xls")):
            df = pd.read_excel(file.path)
            all_dfs.append(df)
            names.append(file.name)
            paths.append(file.path)
            if ASSUME_MAX_CANDIDATES: # pretpostavlja da svaka lista ima naziv i 14 kandidata 
                # (smisleno, jer je listama u interesu da predlože maksimalan dozvoljen broj kandidata)
                list_indices = list(range(15, len(df.columns), 15))
            else:
                # po narančastoj boji ćelija prepoznaje imena lista
                # sporije od pandasa jer učitava cijele Excel datoteke
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
    n_IJ_original = len(all_dfs)
    n_IJ_novi = np.max(jedinice_bm) + 1
    komponente_lista = list(max_joint_coalition_components(liste.copy()))
    # for i in liste: print(i)
    # print("----------------------------")
    # for i in komponente_lista: print("-", i)
    # for i, popis in enumerate(popisi_lista_po_IJ):
    #     print(i, ":", popis)
    
    coalition_splitter = SplitCoalitionVotes(komponente_lista)
    coalition_splitter.add_rules([
        LargestPartyComponentRule.from_file("Nikola/parties_by_size.txt"),
        EqualRule()
    ])

    # preracun glasova na nove jedinice
    glasovi = np.zeros((n_IJ_novi, len(komponente_lista))) # broj IJ * broj komponenata listi
    bm_offset = 0
    for i in range(n_IJ_original):
        for lista in popisi_lista_po_IJ[i]:
            osvojeni_glasovi = all_dfs[i][", ".join(lista)]
            res = coalition_splitter(lista)
            for j in range(len(all_dfs[i])):
                for comp, percent in res.items():
                    glasovi[jedinice_bm[bm_offset + j]][komponente_lista.index(comp)] += percent * osvojeni_glasovi[j]
        bm_offset += len(all_dfs[i])
        print(len(all_dfs[i]))
    print(glasovi)


# parsiranje argumenata
if __name__ == "__main__":
    args_ok = True
    if "--help" in sys.argv:
        print("help")
    else:
        if "--fast" in sys.argv:
            print("Fast mode is on. Try removing the --fast option if the results are nonsensible.")
            ASSUME_MAX_CANDIDATES = True
        if "--dir" in sys.argv:
            try: 
                ELECTION_RESULTS_FOLDER = sys.argv[sys.argv.index("--dir") + 1]
            except IndexError:
                print(f"with {ERR}\"--dir\"{END} option, directory path must be given")
                args_ok = False
        if "--part" in sys.argv:
            try: 
                PARTITION_PATH = sys.argv[sys.argv.index("--part") + 1]
            except IndexError:
                print(f"with {ERR}\"--part\"{END} option, partition file path must be given")
                args_ok = False
        if args_ok:
            main()