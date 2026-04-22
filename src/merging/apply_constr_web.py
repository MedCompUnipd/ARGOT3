#!/usr/bin/python3

import argparse
from taxonLibrary3 import Taxon
import os
from collections import defaultdict
from tqdm import tqdm


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-p', '--preds', required=True)
    parser.add_argument('-c', '--const', required=True)
    parser.add_argument('-t', '--taxa', required=True)
    parser.add_argument('-s', '--specie', required=True)
    parser.add_argument('-o', '--outfile', required=True)

    return vars(parser.parse_args())


def load_constr(dir):
    files = os.listdir(dir)
    constraints = {}
    for file in files:
        taxon = file.split('_')[0]
        constraints[taxon] = defaultdict(set)
        with open(os.path.join(dir, file), 'r') as fp:
            for line in fp:
                go, desc, ont = line.strip().split('\t')
                constraints[taxon][ont].add(go)

    return constraints


def load_preds(file):
    with open(file, 'r') as fp:
        preds = {}
        for line in fp:
            if line.startswith('Query'):
                header = line
                continue
            prot, go, score, ont, desc = line.split('\t')
            if prot not in preds:
                preds[prot] = {}
            if ont not in preds[prot]:
                preds[prot][ont] = {}
            preds[prot][ont][go] = (score, desc)

    return preds, header


def get_constr(taxa, constr, tax):
    if taxa in constr:
        return constr[taxa]

    father = tax.get_father(taxa)
    if not father:
        return None

    get_constr(father, constr, tax)


if __name__ == '__main__':
    args = get_args()
    constr_folder = args['const']
    taxa_folder = args['taxa']
    preds_file = args['preds']
    spec = args['specie']
    out_file = args['outfile']

    print('Load taxonomy...')
    tax = Taxon(os.path.join(taxa_folder, 'nodes.dmp'), os.path.join(taxa_folder, 'merged.dmp'), os.path.join(taxa_folder, 'names.dmp'))

    print('Loading the rest...')
    constraints = load_constr(constr_folder)

    print('Loading the preds...')
    preds_raw, header = load_preds(preds_file)

    preds_filt = {}
    with tqdm(preds_raw.items(), total=len(preds_raw), desc="Applying FunTaxIS...") as pbar, open(out_file, 'w') as fp:
        count = 0
        fp.write(header)
        for prot, onts in pbar:
            constr = get_constr(spec, constraints, tax)
            if constr is None:
                for ont, gos in onts.items():
                    for go, (score, desc) in gos.items():
                        fp.write(f'{prot}\t{go}\t{score}\t{ont}\t{desc}')
                continue
            for ont, gos in onts.items():
                for go, (score, desc) in gos.items():
                    if go in constr[ont]:
                        count += 1
                    else:
                        fp.write(f'{prot}\t{go}\t{score}\t{ont}\t{desc}')
    print(f'Done, filtered {count} annotations!')
