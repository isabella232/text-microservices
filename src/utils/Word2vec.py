#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import numpy as np
from collections import defaultdict
from FifoCache import FifoCache

logger = logging.getLogger(__name__)

class Word2vec(object):
    """Word2vec loader and getter

    Arguments:
        cache_size: the size of vector cache
        vocab_path: path of vocabulary
        vec_path: path of vector
        check_len: the length of each vector in file
        most_words: read top K words only (assume the vocab file are sorted by frequency)

    Properties:
        words: word set for fast search
        word2idx: inverse vocab(dict)
        vec_path: the path of vector file
        cache: a fifo cache for vectors
        line_offset: index for each line of vector, for fast reading from file
        skip_first_col: whether skip first column of vector file
    """
    def __init__(self, cache_size=1000, vocab_path=None, vec_path=None, check_len=300, most_words=1000000, skip_first_col=True):
        cur_path = os.path.abspath(os.path.dirname(__file__))

        if vocab_path is None:
            self.vocab_path = os.path.join(cur_path, "../../models/cbow/glove.840B.300d.vocab.txt")
        else:
            self.vocab_path = vocab_path
        if vec_path is None:
            self.vec_path = os.path.join(cur_path, "../../models/cbow/glove.840B.300d.txt")
        else:
            self.vec_path = vec_path
        self.check_len = check_len
        self.skip_first_col = skip_first_col

        # load vocab into memory
        logger.info('loading %s...', self.vocab_path)
        idx2word = []
        with open(self.vocab_path) as f:
            idx2word = [w.strip().decode('utf-8') for w in f.readlines()][:most_words]
        self.word2idx = dict([(w,idx)for idx,w in enumerate(idx2word)])
        self.words = set(idx2word)
        logger.info("Load done. Vocab size: %d", len(idx2word))

        # cache the offset of each line
	# Read in the file once and build a list of line offsets
        self.line_offset = []
        offset = 0
        with open(self.vec_path) as fp:
            for line in fp:
                self.line_offset.append(offset)
                offset += len(line)
                if len(self.line_offset) == most_words:
                    break
        # make sure vector number equal vocab size
        if len(self.line_offset) != len(idx2word):
            raise Exception('Line number of vocab and vector are not equal!')

        # init a cache for vectors
        self.cache = FifoCache(cache_size)

    def get_vec(self, sent):
	"""Get vectors of words in sentence

	Arguments:
	    sentence: a list of word
	Returns:
	    2-D array, each line is the vector of the each word, but out-of-vocab word will be None
      	"""
        result = [None] * len(sent)

        # return a random vector if not found, otherwise convert to idx
        w_not_hit = defaultdict(list) # there may be repeat words, so we use list
        for idx,w in enumerate(sent):
            try:
                w = w.decode('utf-8')
            except:
                pass

            if w not in self.words:
                # we simply ignore words not in vocab for the moment.
                continue
            else:
                w = self.word2idx[w] # convert word to idx now
                # find in cache firstly, record idx if not found
                if self.cache.has_key(w):
                    result[idx] = self.cache[w]
                else:
                    w_not_hit[w].append(idx)

        # some words not hit in cache, find in file
        with open(self.vec_path) as fp:
            for line_num in w_not_hit.keys():
                fp.seek(self.line_offset[line_num])
                line = fp.readline()
                if self.skip_first_col:
                    vec = np.array([round(float(num), 4) for num in line.split(' ')[1:]])
                else:
                    vec = np.array([round(float(num), 4) for num in line.split(' ')])
                if len(vec) != self.check_len:
                    vec = np.random.rand(self.check_len)
                self.cache[line_num] = vec # put into cache
                for idx in w_not_hit[line_num]: # put into result
                    result[idx] = vec
                w_not_hit.pop(line_num) # remove from candidate
                if len(w_not_hit) == 0: # stop search if all vector found
                    break

        return result

if __name__=='__main__':
    from helper import vec_sim
    w2v = Word2vec(cache_size=11)

    test1 = ['man', 'woman']
    vec = w2v.get_vec(test1)
    print(test1, vec_sim(vec[0], vec[1]))

    test1 = ['man', 'apple']
    vec = w2v.get_vec(test1)
    print(test1, vec_sim(vec[0], vec[1]))

    test1 = ['dog', 'sunny']
    vec = w2v.get_vec(test1)
    print(test1, vec_sim(vec[0], vec[1]))

    test1 = ['rain', 'sunny']
    vec = w2v.get_vec(test1)
    print(test1, vec_sim(vec[0], vec[1]))
