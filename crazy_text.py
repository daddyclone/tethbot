import logging
import re

import markovify
import nltk


class POSifiedText(markovify.Text):

    def word_split(self, sentence):
        words = re.split(self.word_split_pattern, sentence)
        words = ["::".join(tag) for tag in nltk.pos_tag(words)]
        return words

    def word_join(self, words):
        sentence = " ".join(word.split("::")[0] for word in words)
        return sentence


class MarkovTeth(object):

    def __init__(self, corpus="teth_chat", state_size=3):
        with open(corpus) as f:
            text = f.read()
        logging.info(f"training model on {corpus}")
        self.model = POSifiedText(text, state_size)
        logging.info(f" done training model on {corpus}")


class Markov(object):

    def __init__(self, corpus="teth_chat", state_size=3):
        with open(corpus) as f:
            text = f.read()
        logging.info(f"training model on {corpus}")
        self.model = markovify.Text(text, state_size)
        logging.info(f" done training model on {corpus}")
