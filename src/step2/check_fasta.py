#!/usr/bin/python3

import argparse
import re


# UniProt-like header:
# >sp|PROTID|rest of header
# >tr|PROTID|rest of header
uniprot_re = re.compile(r'^>(sp|tr)\|([A-Za-z0-9-_]+)\|(.+)$')

# "Universal" header:
# >PROTID rest of header
# (no pipes allowed anywhere)
universal_re = re.compile(r'^>([A-Za-z0-9_-]+)(?:\s+.*)?$')


def normalize_fasta_header(header):
    """
    Normalize a FASTA header:
      - UniProt (>sp|ID|stuff or >tr|ID|stuff) → >ID stuff
      - Already universal (>ID stuff, with no '|') → unchanged
      - Otherwise → raise ValueError
    """
    header = header.rstrip('\n\r')

    # 1. UniProt style?
    m = uniprot_re.match(header)
    if m:
        _db, prot_id, rest = m.groups()
        return f">{prot_id} {rest}"

    # 2. Already universal style? (must not contain '|')
    if '|' not in header:
        if universal_re.match(header):
            return header

    # 3. Anything else → error
    raise ValueError(f"Unsupported FASTA header format: {header!r}")

def get_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-f', '--fasta', required=True)
    parser.add_argument('-o', '--outfile', required=True)

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = get_args()
    fasta_file = args['fasta']
    out_file = args['outfile']

    with open(fasta_file, 'r') as fp, open(out_file, 'w') as out:
        for line in fp:
            if line.startswith('>'):
                h = normalize_fasta_header(line)
                out.write(f'{h}\n')
            else:
                out.write(line)
