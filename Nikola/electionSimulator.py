import numpy as np
import pandas as pd
import sys

VOTES_INPUT_FILE = "preracunati_glasovi_2024"
N_MANDATES = 140

# boje za ispis
OK = '\033[92m'
WARN = '\033[93m'
ERR = '\033[91m'
END = '\033[0m'

def Gallagher_index(votes, mandates):
    vote_percent = votes / np.sum(votes)
    mandates_percent = mandates / np.sum(mandates)
    diff = vote_percent - mandates_percent
    return 100 * np.sqrt(0.5*np.sum(diff*diff))

def Sainte_Lague_index(votes, mandates):
    vote_percent = votes / np.sum(votes)
    mandates_percent = mandates / np.sum(mandates)
    diff = mandates_percent-vote_percent
    return np.sum(np.divide(diff*diff, vote_percent, out = np.zeros_like(vote_percent), where=vote_percent != 0)) 

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

# izborni prag
def treshold(votes, percent):
    min_votes = percent*votes.sum()
    return votes * (votes >= min_votes)

def main():
    # učita glasove po izbornim jedinicama
    votes_df = pd.read_csv(VOTES_INPUT_FILE, sep=";")
    votes_total = votes_df.to_numpy().sum(axis=0)
    # dodjela mandata
    mandates_total = DHondt_like(votes=votes_total, total=N_MANDATES, step=1)
    # izračun indeksa
    print(f"HH: {HH_index(mandates_total)}, LSq: {Gallagher_index(votes_total, mandates_total)}, SL: {Sainte_Lague_index(votes_total, mandates_total)}")

# parsiranje argumenata
if __name__ == "__main__":
    args_ok = True
    if "--help" in sys.argv:
        print("help")
    else:
        if "--vote" in sys.argv:
            try: 
                VOTES_INPUT_FILE = sys.argv[sys.argv.index("--vote") + 1]
            except IndexError:
                print(f"with {ERR}\"--vote\"{END} option, path to a .npy file containing votes for each component in each partition must be given")
                raise
        if "--names" in sys.argv:
            try: 
                COALITION_COMPONENTS_INPUT_FILE = sys.argv[sys.argv.index("--names") + 1]
            except IndexError:
                print(f"with {ERR}\"--names\"{END} option, path to a .csv file containing names of coalition components (a header for the votes file) must be given")
                raise
        main()