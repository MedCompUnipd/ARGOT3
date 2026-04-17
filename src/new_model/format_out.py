#!/usr/bin/python3

import argparse
from owlLibrary3 import GoOwl


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--infile', required=True)
    parser.add_argument('-g', '--owl', required=True)
    parser.add_argument('-o', '--outfile', required=True)

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = get_args()
    in_file = args['infile']
    out_file = args['outfile']
    owl_file = args['owl']

    owl = GoOwl(owl_file)

    with open(in_file, 'r') as fp:
        pred = {}
        for line in fp:
            if line.startswith('Query'):
                continue
            prot, go, _, score = line.strip().split('\t')
            ont = owl.go_single_details(go)['namespace']
            desc = owl.go_single_details(go)['descr']
            if prot not in pred:
                pred[prot] = {}
            if ont not in pred[prot]:
                pred[prot][ont] = {}
            pred[prot][ont][go.replace('_', ':')] = (score, desc)

    with open(out_file, 'w') as fp:
        fp.write('Query_ID\tGO_ID\tScore\tAspect\tDescription\n')
        for prot, onts in pred.items():
            for ont, gos in onts.items():
                for go, (score, desc) in gos.items():
                    fp.write(f'{prot}\t{go}\t{score}\t{ont}\t{desc}\n')
