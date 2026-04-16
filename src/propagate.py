#!/usr/bin/python3

from tqdm import tqdm
import argparse
from owlLibrary3 import GoOwl


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-g', '--owl', required=True)
    parser.add_argument('-p', '--pred', action='store_true')

    return vars(parser.parse_args())


def parse_prediction(infile, outfile, owl, obs):
    preds = {}
    with open(infile, 'r') as fp:
        for line in fp:
            if line.startswith('Query'):
                continue
            data = line.strip().split('\t')
            if len(data) == 3:
                prot, go, score = data
            else:
                continue
            score = float(score)
            if prot not in preds:
                preds[prot] = {}
            preds[prot][go] = score

    prop = {}
    with tqdm(preds.items(), total=len(preds), desc='Propagating...') as pbar:
        for prot, gos in pbar:
            prop[prot] = {}
            for go in gos.keys():
                prop[prot][go] = gos[go]
                ancestors = owl.get_ancestors_id(go.replace(':', '_'), by_ontology=True, valid_edges=True)
                for anc in ancestors:
                    if anc in prop[prot]:
                        prop[prot][anc] = max([prop[prot][anc], gos[go]])
                    elif anc in gos:
                        prop[prot][anc] = max([gos[anc], gos[go]])
                    else:
                        prop[prot][anc] = gos[go]

                    '''
                    if anc in gos:
                        if anc in prop[prot]:
                            prop[prot][anc] = max([gos[anc], gos[go], prop[prot][anc]])
                        else:
                            prop[prot][anc] = max([gos[anc], gos[go]])
                    else:
                        if anc in prop[prot]:
                            prop[prot][anc] = max([prop[prot][anc], gos[go]])
                        else:
                            prop[prot][anc] = gos[go]
                    '''

    with open(outfile, 'w') as out:
        for prot, gos in prop.items():
            for go in gos.keys():
                go_under = go.replace(':', '_')
                if go_under in ['GO_0005575', 'GO_0008150', 'GO_0003674']:
                    continue
                out.write(f'{prot}\t{go_under}\t{prop[prot][go]}\n')


def parse_groundtruth(infile, outfile, owl, obs):
    grt = {}
    with open(infile, 'r') as fp:
        for line in fp:
            prot, go = line.strip().split('\t')
            if prot not in grt:
                grt[prot] = set()
            grt[prot].add(go.replace(':', '_'))

    prop = {}
    for prot, gos in grt.items():
        propagation = gos.copy()
        for go in gos:
            ancestors = owl.get_ancestors_id(go, by_ontology=True, valid_edges=True)
            for anc in ancestors:
                propagation.add(anc)
        prop[prot] = propagation - obs

    with open(outfile, 'w') as out:
        for prot, gos in prop.items():
            for go in gos:
                if go in ['GO_0005575', 'GO_0008150', 'GO_0003674']:
                    continue
                out.write(f'{prot}\t{go}\n')


if __name__ == '__main__':
    args = get_args()
    annots_file = args['input']
    out_file = args['output']
    owl_file = args['owl']
    flag = args['pred']

    print('Parsing owl...')
    owl = GoOwl(owl_file)
    obsolete, deprecated = owl.get_obsolete_deprecated_list()
    bad_gos = set(obsolete.keys()) | set(deprecated.keys())

    if flag:
        parse_prediction(annots_file, out_file, owl, bad_gos)
    else:
        parse_groundtruth(annots_file, out_file, owl, bad_gos)
