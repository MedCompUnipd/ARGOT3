#!/usr/bin/python3

from models import *
import math
import os
import sys
from tqdm import tqdm
import argparse
import tensorflow as tf
import numpy as np


# Enable GPU memory growth
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'
gpus = tf.config.experimental.list_physical_devices('GPU')
for gpu in gpus:
    tf.config.experimental.set_memory_growth(gpu, True)

strategy = tf.distribute.MirroredStrategy()
print("Number of devices:", strategy.num_replicas_in_sync)

ONT_LENS = {'bpo': 26090,
            'cco': 4021,
            'mfo': 10153}


def get_args():
    # Define an ArgumentParser object
    parser = argparse.ArgumentParser()

    # Add optional command-line argument
    parser.add_argument('-l', '--list', required=True)
    parser.add_argument('-b', '--batch', required=False, default=64)
    parser.add_argument('-e', '--embeddings', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-g', '--ontology', required=False, default='')
    parser.add_argument('-s', '--structure', required=False, default='input/structure/')
    parser.add_argument('-w', '--weights', required=False, default='input/weights/')

    # Parse the command-line arguments and return them as a dictionary
    return vars(parser.parse_args())


def retrieve_model(ont, out_channels, print_summary=False):
    if ont == 'cco':
        model = get_model_cco(out_channels)
    elif ont == 'mfo':
        model = get_model_mfo(out_channels)
    elif ont == 'bpo':
        model = get_model_bpo(out_channels)

    def myprint(s):
        with open('modelsummary.txt','a') as f:
            print(s, file=f)

    if print_summary:
        model.summary(print_fn=myprint)

    return model


def get_order(ontology):
    with open(ontology, 'r') as fp:
        return [x.strip() for x in fp.readlines()]


if __name__ == '__main__':
    # Parsing arguments
    args = get_args()
    prots_list = args['list']
    embed_path = args['embeddings']
    ont = args['ontology']
    order_folder = args['structure']
    weights_folder = args['weights']
    pred_dir = args['output']
    batch_size = args['batch']

    ont_weigths = {'cco': os.path.join(weights_folder, 'cco.h5'),
                   'mfo': os.path.join(weights_folder, 'mfo.h5'),
                   'bpo': os.path.join(weights_folder, 'bpo.h5')}

    ont_orders = {'cco': get_order(os.path.join(order_folder, 'CCO_order.txt')),
                  'mfo': get_order(os.path.join(order_folder, 'MFO_order.txt')),
                  'bpo': get_order(os.path.join(order_folder, 'BPO_order.txt'))}

    with open(prots_list, 'r') as fp:
        prots = [x.strip() for x in fp.readlines()]

    preds = {}
    onts = [ont] if ont else ['cco', 'mfo', 'bpo']
    for ont in onts:
        preds[ont] = {}
        model = retrieve_model(ont, ONT_LENS[ont])
        model.load_weights(ont_weigths[ont])

        BATCH_SIZE = int(batch_size)

        def load_tensor_from_file(prot_id):
            prot_file = tf.strings.join([embed_path, "/", prot_id, ".txt"])
            raw = tf.io.read_file(prot_file)
            tensor = tf.io.parse_tensor(raw, out_type=tf.float32)
            return tensor, prot_id

        # Create dataset of protein names
        prot_ds = tf.data.Dataset.from_tensor_slices(prots)

        # Map to (embedding_tensor, protein_id)
        parsed_ds = prot_ds.map(
            load_tensor_from_file,
            num_parallel_calls=tf.data.AUTOTUNE
        )

        # Pad sequences and batch
        batched_ds = parsed_ds.padded_batch(
            BATCH_SIZE,
            padded_shapes=([None, None], [])  # ([seq_len, feat_dim], prot_id)
        ).prefetch(tf.data.AUTOTUNE)

        # Model prediction loop
        preds[ont] = {}
        for batch, prot_ids in tqdm(batched_ds, desc=f'Predicting {ont}'):
            batch_preds = model.predict(batch, verbose=0)
            for i, prot in enumerate(prot_ids.numpy()):
                preds[ont][prot.decode()] = batch_preds[i:i+1]

        with open(os.path.join(pred_dir, f'{ont}_batch.txt'), 'w') as fp:
            for prot in tqdm(preds[ont], desc=f'Writing {ont}_batch.txt (original)'):
                pred = preds[ont][prot]
                for go, score in zip(ont_orders[ont], pred.flatten()):
                    if float(score) > 0.01:
                        fp.write(f'{prot}\t{go}\t{score:.2f}\n')
