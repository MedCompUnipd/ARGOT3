#!/usr/bin/python3

import argparse


def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-d', '--argot25', required=True)
    parser.add_argument('-t', '--argot3', required=True)
    parser.add_argument('-o', '--outfile', required=True)

    return vars(parser.parse_args())


def update_dict(data, descs, file, pos):
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
                data[prot][ont][go] = [0] if pos else []
            data[prot][ont][go].append(float(score))

    return header


if __name__ == '__main__':
    args = get_args()
    a25 = args['argot25']
    a30 = args['argot3']
    outfile = args['outfile']

    merge = {}
    descrs = {}
    header = update_dict(merge, descrs, a25, 0)
    header = update_dict(merge, descrs, a30, 1)

    with open(outfile, 'w') as fp:
        data = header.split('\t')
        data.insert(3, 'Score A3.0')
        data.insert(3, 'Score A2.5')
        data[2] = 'Score Merged'
        header = '\t'.join(data)
        fp.write(header)
        for prot, onts in merge.items():
            for ont, gos in onts.items():
                for go, score in gos.items():
                    while len(score) < 2:
                        score.append(0)
                    desc = descrs[go]
                    sm = max(score)
                    fp.write(f'{prot}\t{go}\t{sm:.2f}\t{score[0]:.2f}\t{score[1]:.2f}\t{ont}\t{desc}')
