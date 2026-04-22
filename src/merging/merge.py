#!/usr/bin/python3

import argparse


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--argot25', required=True)
    parser.add_argument('-t', '--argot3', required=True)
    parser.add_argument('-o', '--outfile', required=True)

    return vars(parser.parse_args())


def update_dict(data, descs, file):
    with open(file, 'r') as fp:
        for line in fp:
            if line.startswith('Query'):
                header = line
                continue
            prot, go, score, ont, desc = line.split('\t')
            if go not in descs:
                descs[go] = desc
            if prot not in data:
                data[prot] = {}
            if ont not in data[prot]:
                data[prot][ont] = {}
            if go not in data[prot][ont]:
                data[prot][ont][go] = float(score)
            else:
                newscore = max([float(score), data[prot][ont][go]])
                data[prot][ont][go] = newscore

    return header


if __name__ == '__main__':
    args = get_args()
    a25 = args['argot25']
    a30 = args['argot3']
    outfile = args['outfile']

    merge = {}
    descrs = {}
    header = update_dict(merge, descrs, a25)
    header = update_dict(merge, descrs, a30)

    with open(outfile, 'w') as fp:
        fp.write(header)
        for prot, onts in merge.items():
            for ont, gos in onts.items():
                for go, score in gos.items():
                    desc = descrs[go]
                    fp.write(f'{prot}\t{go}\t{score:.2f}\t{ont}\t{desc}')
