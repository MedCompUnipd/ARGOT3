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
    parser.add_argument('-l', '--taxlist', required=True)
    parser.add_argument('-t', '--taxa', required=True)
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


def load_tax(taxon_list):
    with open(taxon_list, 'r') as fp:
        prot_tax = {}
        for line in fp:
            prot, taxon = line.strip().split('\t')
            prot_tax[prot] = taxon

    return prot_tax


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


def get_constr(taxa, constr, cache, tax):
    if taxa in cache:
        return cache[taxa]

    roots = list(constr.keys())
    if taxa in roots:
        cache[taxa] = constr[taxa]
        return cache[taxa]

    father = tax.get_father(taxa)
    #print(f'{taxa} -> {father}')
    if not father:
        print(f'Something went wrong with tax: {taxa}...')
        cache[taxa] = None
        return None

    result = get_constr(father, constr, cache, tax)
    cache[father] = result
    return result


if __name__ == '__main__':
    args = get_args()
    constr_folder = args['const']
    taxa_folder = args['taxa']
    taxon_list = args['taxlist']
    preds_file = args['preds']
    out_file = args['outfile']

    print('Load taxonomy...')
    tax = Taxon(os.path.join(taxa_folder, 'nodes.dmp'), os.path.join(taxa_folder, 'merged.dmp'), os.path.join(taxa_folder, 'names.dmp'))

    print('Loading the rest...')
    constraints = load_constr(constr_folder)
    prot_tax = load_tax(taxon_list)

    print('Loading the preds...')
    preds_raw, header = load_preds(preds_file)

    preds_filt = {}
    constr_map = {}
    with tqdm(preds_raw.items(), total=len(preds_raw), desc="Applying FunTaxIS...") as pbar, open(out_file, 'w') as fp:
        count = 0
        fp.write(header)
        for prot, onts in pbar:
            taxon = prot_tax[prot]
            constr = get_constr(taxon, constraints, constr_map, tax)
            if constr is None:
                continue
            for ont, gos in onts.items():
                for go, (score, desc) in gos.items():
                    if go in constr[ont]:
                        count += 1
                    else:
                        fp.write(f'{prot}\t{go}\t{score}\t{ont}\t{desc}')
    print(f'Done, filtered {count} annotations!')
