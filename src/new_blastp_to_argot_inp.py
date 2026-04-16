#!/usr/bin/python3

import argparse
import math
import pymongo
import csv

# Define the root GO terms
ROOT_TERMS = {'GO:0008150', 'GO:0003674', 'GO:0005575'}

def read_annotations_from_database(server, database, collection, proteins):
    """
    Reads GO annotations for a set of proteins from a MongoDB database.
    Returns a dictionary containing the annotations for each protein.
    """
    print('Reading GO annotations from MongoDB...')
    page_size = 10000
    proteins = list(proteins)
    go_annotations = {}
    client = pymongo.MongoClient(host=server, port=27017)
    db = client[database]
    collection = db[collection]
    for page in range(0, len(proteins), page_size):
        cursor = collection.aggregate([{'$match': {'uid': {'$in': list(proteins[page:page+page_size])}}}, {'$project': {'_id': 0, 'uid': 1, 'goids': 1}}])
        for record in cursor:
            go_annotations[record['uid']] = record['goids']
    print('Done')
    return go_annotations


def read_protein_ids_from_blastp_file(blastp_file):
    """
    Reads protein IDs from a BLASTP output file.
    Returns a set of protein IDs and the maximum e-value.
    """
    print('Reading protein IDs from BLASTP output...')
    protein_ids = {row[1] for row in csv.reader(open(blastp_file), delimiter='\t') if not row[0].startswith('#')}
    print('Done')
    return protein_ids


def generate_argot_input(server, database, collection, blastp_file, output_file):
    """
    Generates ARGOT2 input file from BLASTP output file and GO annotations in MongoDB.
    """
    protein_ids = read_protein_ids_from_blastp_file(blastp_file)

    go_annotations = read_annotations_from_database(server, database, collection, protein_ids)

    print('Writing ARGOT2 input file...')
    current_query_id = ''
    with open(output_file, 'w') as output_file_handle:
        with open(blastp_file, 'r') as blastp_file_handle:
            for line in blastp_file_handle:
                if line.startswith('#'):
                    continue

                data = line.strip().split('\t')
                query_protein_id = data[0]
                seq_protein_id = data[1]
                if seq_protein_id not in go_annotations:
                    continue
                if current_query_id != query_protein_id:
                    current_query_id = query_protein_id
                    output_file_handle.write('>{}\n'.format(query_protein_id))

                try:
                    log_evalue = min([-math.log(float(data[-2]), 10), 300])
                    if log_evalue <= 0:
                        log_evalue = 0.000001
                except ValueError:
                    log_evalue = 300

                # log_evalue = log_evalue * (300 / max_evalue)
                for go_term in go_annotations[seq_protein_id]:
                    output_file_handle.write('{}\t{}\t{}\t{}\n'.format(go_term, log_evalue, seq_protein_id, 0))
    print('Done')

def main(args):
    """
    Parses command line arguments and generates ARGOT2 input file.
    """
    generate_argot_input(args['mongo_server'], args['mongo_db'], args['mongo_collection'], args['blast_file'], args['argot_input'])


if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Convert Blast output file to Argot input file')
    parser.add_argument('-b', '--blast_file', metavar='BLAST_FILE', help='Blast output file', required=True)
    parser.add_argument('-m', '--mongo_server', metavar='MONGO_SERVER', help='MongoDB server name or IP address', required=True)
    parser.add_argument('-d', '--mongo_db', metavar='MONGO_DB', help='MongoDB database name', required=True)
    parser.add_argument('-c', '--mongo_collection', metavar='MONGO_COLLECTION', help='MongoDB collection name', required=True)
    parser.add_argument('-o', '--argot_input', metavar='ARGOT_INPUT', help='Argot input file to be generated', required=True)
    args = parser.parse_args()

    # Call the main function with parsed arguments
    main(vars(args))
