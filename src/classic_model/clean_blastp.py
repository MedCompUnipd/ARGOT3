#!/usr/bin/python3

import argparse
import os


def get_args():
    parser = argparse.ArgumentParser(description='Clean DIAMOND output file')

    parser.add_argument('-i', '--input_file', metavar='INPUT_FILE', help='path to input file')
    parser.add_argument('-o', '--output_file', metavar='OUTPUT_FILE', help='path to output file')
    parser.add_argument('-t', '--thr', required=False, default=0.0, type=float)

    return vars(parser.parse_args())


def run(input_file, output_file, threshold):
    with open(output_file, 'w') as output:
        with open(input_file, 'r') as input:
            for line in input:
                data = line.split('\t')
                if '|' in data[0]:
                    data[0] = data[0].split('|')[1].strip()
                if '|' in data[1]:
                    data[1] = data[1].split('|')[1].strip()
                if float(data[2]) >= threshold:
                    output.write('\t'.join(data))


if __name__ == '__main__':
    args = get_args()
    in_file = args['input_file']
    out_file = args['output_file']
    th = args['thr']

    if not os.path.exists(in_file):
        raise argparse.ArgumentTypeError(f'Input file does not exist: {in_file}')
    if not os.access(in_file, os.R_OK):
        raise argparse.ArgumentTypeError(f'Input file is not readable: {in_file}')
    if os.path.exists(out_file):
        raise argparse.ArgumentTypeError(f'Output file already exists: {out_file}')

    if th < 0 or th > 100:
        raise ValueError('Expected threshold value: [0, 100]')

    run(in_file, out_file, th)
