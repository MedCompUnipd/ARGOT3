#!/usr/bin/python3

import argparse
import zipfile
import os
from math import pow, isnan


#POINTS_ARGOT25 = [(0, 0), (100, 0.5), (200, 0.7), (10000, 1.0)]
POINTS_ARGOT25 = [(0, 0), (30, 0.5), (60, 0.7), (100, 1.0)]
POINTS_ARGOT3 = [(0, 0), (100, 0.5), (1000, 0.7), (10000, 1.0)]


def spline(x, points):
    for ((x1, y1), (x2, y2)) in zip(points, points[1:]):
        if x <= x2:
            return float(x - x1) / (x2 - x1) * (y2 - y1) + y1
    return points[-1][1]


def normalize(x, version, normalization, average):
    if x is None or isnan(x):
        return 0

    if normalization == 'in_house':
        points = POINTS_ARGOT25 if version == 'Argot2.5' else POINTS_ARGOT3
        return spline(x, points)

    x_0 = round(average)
    if normalization == 'log_logistic':
        b = 2
        return pow(x, b) / (pow(x, b) + pow(x_0, b)) if x > 0 else 0

    if normalization == 'ramp':
        low, high = 0, 300
        if x > high:
            return 1.0
        if x < low:
            return 0.0
        if low <= x <= high:
            return (x - low) / (high - low)


def read_input_file(input_file):
    preds = {}
    values = []
    with open(input_file) as fp:
        for line in fp:
            if line.startswith('#') or line.rstrip() == 'ID\tGOs\tScore Ratio\tZ score':
                continue
            f = line.split('\t')
            if '|' in f[0]:
                f[0] = f[0].split('|')[1]
            preds.setdefault(f[0], [])
            preds[f[0]].append((f[1], float(f[4]), float(f[5])))
            values.append(float(f[4]))
    average = sum(values) / len(values)
    return preds, average


def write_output_file(preds, version, normalization, average, output_path, filename):
    filename = f"{filename}_argot_out_in_cafa.txt"
    if output_path:
        os.makedirs(output_path, exist_ok=True)
        filename = os.path.join(output_path, filename)
    with open(filename, 'w') as fp_out:
        for pred in preds:
            for p in preds[pred]:
                fp_out.write(f"{pred}\t{p[0]}\t{max(0.01, normalize(p[1], version, normalization, average)):.2f}\n")
        fp_out.write("END\n")
    return filename


def main(args):
    preds, average = read_input_file(args.input_file)
    output_file = write_output_file(preds, args.version, args.normalization, average, args.output_path, args.filename)
    if args.compress:
        with zipfile.ZipFile(f"{output_file}.zip", 'w') as zip_file:
            zip_file.write(output_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert a file produced by Argot using a CAFA compatible format')

    parser.add_argument('-i', '--input-file', help='a file produced by Argot', metavar='ARGOT_OUTPUT', required=True, type=str)
    parser.add_argument('-z', '--compress', help='compress the result in a ZIP archive', action='store_true')
    parser.add_argument('-v', '--version', help='choose the Argot version', required=True, choices=['Argot2.5', 'Argot3'])
    parser.add_argument('-n', '--normalization', help='The normalization function to use', default='in_house', choices=['in_house', 'log_logistic', 'ramp'])
    parser.add_argument('-o', '--output-path', help='path where output files are saved', metavar='OUT_PATH', required=True, type=str)
    parser.add_argument('-f', '--filename', help='name of the final output file', metavar='FILENAME', required=True, type=str)

    args = parser.parse_args()

    main(args=args)
