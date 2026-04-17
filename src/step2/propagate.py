#!/usr/bin/python3

from tqdm import tqdm
import argparse
from owlLibrary3 import GoOwl


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-g', '--owl', required=True)

    return vars(parser.parse_args())


def parse_prediction(infile, outfile, owl, obs):
    preds = {}
    with open(infile, 'r') as fp:
        for i, line in enumerate(fp):
            if line.startswith('Query'):
                continue
            if (i % 1000 == 0):
                print(f'Line {i}...', end='\r')
            data = line.strip().split('\t')
            prot, go, ont, score = data
            score = float(score)

            if prot not in preds:
                preds[prot] = {}
            preds[prot][go] = [score, ont]

    prop = {}
    all_uniq_gos = set(go for gos in preds.values() for go in gos)
    print(f'Found {len(all_uniq_gos)} unique GO terms')
    go2anc = {go: owl.get_ancestors_id(go.replace(':', '_'), by_ontology=True, valid_edges=True) for go in tqdm(all_uniq_gos, desc="Precomputing ancestors")}
    with tqdm(preds.items(), total=len(preds), desc='Propagating...') as pbar:
        for prot, gos in pbar:
            prop[prot] = {}
            for go in gos.keys():
                prop[prot][go] = gos[go]
                ancestors = go2anc[go.replace(':', '_')]
                for anc in ancestors:
                    if anc in prop[prot]:
                        score = max([prop[prot][anc][0], gos[go][0]])
                        prop[prot][anc] = [score, gos[go][1]]
                    elif anc in gos:
                        score = max([gos[anc][0], gos[go][0]])
                        prop[prot][anc] = [score, gos[go][1]]
                    else:
                        prop[prot][anc] = gos[go]

    with open(outfile, 'w') as out:
        for prot, gos in prop.items():
            for go, [score, ont] in gos.items():
                go = go.replace(':', '_')
                if go in ['GO_0005575', 'GO_0008150', 'GO_0003674']:
                    continue
                out.write(f'{prot}\t{go}\t{ont}\t{score}\n')


if __name__ == '__main__':
    args = get_args()
    annots_file = args['input']
    out_file = args['output']
    owl_file = args['owl']

    print('Parsing owl...')
    owl = GoOwl(owl_file)
    obsolete, deprecated = owl.get_obsolete_deprecated_list()
    bad_gos = set(obsolete.keys()) | set(deprecated.keys())

    parse_prediction(annots_file, out_file, owl, bad_gos)
