#!/usr/bin/python3

import math
import torch
import tensorflow as tf
import argparse
import sys
import os
import pickle
from tqdm import tqdm
import numpy as np


def get_args():
	parser = argparse.ArgumentParser()

	parser.add_argument('-e', '--embeddings', required=False, default='intermediate_files/prep_dataset/embeddings/')
	parser.add_argument('-o', '--output', required=False, default='intermediate_files/prep_dataset/tf/')

	return vars(parser.parse_args())


def convert_to_tf(embeds, prots, outpath):
	with tqdm(prots, total=len(prots)) as pbar:
		for prot in pbar:
			x = torch.load(os.path.join(embeds, prot + '.pt'))
			x = x['representations'][33]
			x = tf.reshape(tf.convert_to_tensor(x.numpy()), (x.shape[0], x.shape[1]))
			out_prot = os.path.join(outpath, f'{prot}.txt')
			tf.io.write_file(out_prot, tf.io.serialize_tensor(x))


if __name__ == '__main__':
	args = get_args()
	embed_path = args['embeddings']
	out_path = args['output']

	if os.path.exists(embed_path):
		prots = os.listdir(embed_path)
		prots = [prot.split('.')[0] for prot in prots]
		if not os.path.exists(out_path):
			print(f'Creating path {out_path}')
			os.mkdir(out_path)

		convert_to_tf(embed_path, prots, out_path)
	else:
		raise FileNotFoundError(f"File not found: {embed_path}")
