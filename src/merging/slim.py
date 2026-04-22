#!/usr/bin/python3

import argparse
from owlLibrary3 import GoOwl
from tqdm import tqdm

ont_to_ont = {'biological_process': 'P',
              'molecular_function': 'M',
              'cellular_component': 'C'}

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--infile', required=True)
    parser.add_argument('-g', '--owl', required=True)
    parser.add_argument('-s', '--outslim', required=True)
    parser.add_argument('-f', '--outfull', required=True)

    return vars(parser.parse_args())


def get_leaflike(gos, ancestors, descendants):
    gos = set([go.replace(':', '_') for go in gos])
    llike = set()
    while gos:
        go = gos.pop()
        if not descendants[go]:
            llike.add(go)
            for anc in ancestors[go]:
                gos.discard(anc)
        else:
            if not gos & descendants[go]:
                llike.add(go)
                for anc in ancestors[go]:
                    gos.discard(anc)

    return set([go.replace('_', ':') for go in llike])


if __name__ == '__main__':
    args = get_args()
    in_file = args['infile']
    out_slim = args['outslim']
    out_full = args['outfull']
    owl_file = args['owl']

    print('load go.owl...')
    owl = GoOwl(owl_file)

    print('load predictions...')
    with open(in_file, 'r') as fp:
        preds = {}
        gos = set()
        for line in fp:
            if line.startswith('Query'):
                continue
            query, go, score, ont, desc = line.strip().split('\t')
            gos.add(go.replace(':', '_'))
            if query not in preds:
                preds[query] = {}
            if ont not in preds[query]:
                preds[query][ont] = {}
            preds[query][ont][go] = (float(score), desc)

    print('precomputing ancestors and descendants...')
    descs = {}
    ancs = {}
    with tqdm(gos, total=len(gos)) as pbar:
        for go in pbar:
            descs[go] = owl.get_descendants_id(go, by_ontology=True, valid_edges=True)
            ancs[go] = owl.get_ancestors_id(go, by_ontology=True, valid_edges=True)

    print('fitler and write...')
    with open(out_slim, 'w') as s, open(out_full, 'w') as f:
        s.write('QueryID\tGO Term\tScore\tOntology\tName\tDescription\n')
        f.write('QueryID\tGO Term\tScore\tOntology\tName\tDescription\n')
        with tqdm(preds.items(), total=len(preds)) as pbar:
            for prot, onts in pbar:
                for ont, gos in onts.items():
                    selected = get_leaflike(gos, ancs, descs)
                    for go in gos:
                        (score, desc) = preds[prot][ont][go]
                        name = owl.go_single_details(go.replace(':', '_'))['name']
                        f.write(f'{prot}\t{go}\t{score}\t{ont_to_ont[ont]}\t{name}\t{desc}\n')
                        if go in selected:
                            s.write(f'{prot}\t{go}\t{score}\t{ont_to_ont[ont]}\t{name}\t{desc}\n')

