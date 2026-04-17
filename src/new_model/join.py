#!/usr/bin/python3

import argparse
from tqdm import tqdm


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--cco', required=False)
    parser.add_argument('-m', '--mfo', required=False)
    parser.add_argument('-b', '--bpo', required=False)
    parser.add_argument('-t', '--thr', required=False, default=0.1)
    parser.add_argument('-o', '--output', required=True)

    return vars(parser.parse_args())


def update_preds(predict, infile, ont, thr):
    with open(infile, 'r') as fp:
        for line in fp:
            prot, go, score = line.strip().split('\t')
            if prot not in predict:
                predict[prot] = {}
            if ont not in predict[prot]:
                predict[prot][ont] = {}
            if float(score) > thr:
                predict[prot][ont][go] = float(score)


if __name__ == '__main__':
    args = get_args()
    cco_file = args['cco']
    mfo_file = args['mfo']
    bpo_file = args['bpo']
    thr = float(args['thr'])
    out_file = args['output']

    preds = {}
    if cco_file:
        print('Load cco...')
        update_preds(preds, cco_file, 'C', thr)

    if mfo_file:
        print('Load mfo...')
        update_preds(preds, mfo_file, 'F', thr)

    if bpo_file:
        print('Load bpo...')
        update_preds(preds, bpo_file, 'P', thr)

    with open(out_file, 'w') as fp:
        fp.write('Query_ID\tGO_ID\tOntology\tScore\n')
        with tqdm(preds.items(), total=len(preds)) as pbar:
            for prot, onts in pbar:
                for ont, gos in onts.items():
                    for go, score in gos.items():
                        fp.write(f'{prot}\t{go}\t{ont}\t{score}\n')
