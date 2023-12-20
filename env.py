#!/usr/bin/python
# encoding: utf-8
import sys
sys.path.append('./envs/pre_train')
import numpy as np
import logger
from collections import OrderedDict
import math
from collections import Counter
import copy as cp
import json

import os
import yaml
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import roc_auc_score

# TODO:
class env(object):
    def __init__(self, args):
        logger.log("initialize environment")
        self.T = args.T
        self.data_name = args.data_name
        self.CDM = args.CDM
        self.rates = {}
        self.users = {}
        self.utypes = {}
        self.args = args
        self.device = torch.device('cuda')
        self.rates, self._item_num, self.know_map = self.load_data(os.path.join(self.args.data_path, args.data_name, "data/student-problem-fine.json"))
        logger.log("user number: " + str(len(self.rates) + 1))
        logger.log("item number: " + str(self._item_num + 1))
        self.setup_train_test()
        self.sup_rates, self.query_rates = self.split_data(ratio=0.5)

        print('loading CDM %s' % args.CDM)
        self.model, self.dataset = self.load_CDM()
        print(self.model)

    def split_data(self, ratio=0.5):
        sup_rates, query_rates = {}, {}
        for u in self.rates:
            all_items = list(self.rates[u].keys())
            np.random.shuffle(all_items)
            sup_rates[u] = {it: self.rates[u][it] for it in all_items[:int(ratio*len(all_items))]}
            query_rates[u] = {it: self.rates[u][it] for it in all_items[int(ratio*len(all_items)):]}
        return sup_rates, query_rates

    def re_split_data(self, ratio=0.5):
        self.sup_rates, self.query_rates = self.split_data(ratio)

    @property
    def candidate_items(self):
        return set(self.sup_rates[self.state[0][0]].keys())

    @property
    def user_num(self):
        return len(self.rates) + 1

    @property
    def item_num(self):
        return self._item_num + 1

    @property
    def utype_num(self):
        return len(self.utypes) + 1



    def setup_train_test(self):
        users = list(range(1, self.user_num))
        np.random.shuffle(users)
        self.training, self.validation, self.evaluation = np.split(np.asarray(users), [int(.8 * self.user_num - 1),
                                                                                       int(.9 * self.user_num - 1)])

    def load_data(self, path):

        with open(path, encoding='utf8') as i_f:
            stus = json.load(i_f) # list
        rates = {}
        items = set()
        user_cnt = 0
        know_map = {}

        for stu in stus:
            if stu['log_num'] < self.T * 2:
                continue
            user_cnt += 1
            rates[user_cnt] = {}
            for log in stu['logs']:
                rates[user_cnt][int(log['exer_id'])] = int(log['score'])
                items.add(int(log['exer_id']))
                know_map[int(log['exer_id'])] = log['knowledge_code']

        max_itemid = max(items)

        return rates, max_itemid, know_map

    def reset(self):
        self.reset_with_users(np.random.choice(self.training))

    def reset_with_users(self, uid):
        self.state = [(uid,1), []]
        self.short = {}
        return self.state

    def observation(self):

        return self.state
    def step(self, action):
        assert action in self.sup_rates[self.state[0][0]] and action not in self.short
        reward, ACC, AUC, rate = self.reward(action)

        if len(self.state[1]) < self.T - 1:
            done = False
        else:
            done = True

        self.short[action] = 1
        t = self.state[1] + [[action, reward, done]]
        info = {"ACC": ACC,
                "AUC": AUC,
                "rate":rate}
        self.state[1].append([action, reward, done, info])
        return self.state, reward, done, info
    def get_knowledge_state(self):

    def reward(self, action):

        self.dataset.clear()
        items = [state[0] for state in self.state[1]] + [action]
        correct = [self.rates[self.state[0][0]][it] for it in items]
        self.dataset.add_record([self.state[0][0]]*len(items), items, correct)
        self.model.update(self.dataset, self.args.learning_rate, epoch=1)

        item_query = list(self.query_rates[self.state[0][0]].keys())
        correct_query = [self.rates[self.state[0][0]][it] for it in item_query]
        loss, pred = self.model.cal_loss([self.state[0][0]]*len(item_query), item_query, correct_query, self.know_map)
        # ACC AUC
        pred_bin = np.where(pred > 0.5, 1, 0)
        ACC = np.sum(np.equal(pred_bin, correct_query)) / len(pred_bin)
        try:
            AUC = roc_auc_score(correct_query, pred)
        except ValueError:
            AUC = -1
        self.model.init_stu_emb()
        return -loss, ACC, AUC, correct[-1]




def split_data(rates, ratio=0.5):
    sup_rates, query_rates = {}, {}
    for u in rates:
        all_items = list(rates[u].keys())
        np.random.shuffle(all_items)
        sup_rates[u] = {it: rates[u][it] for it in all_items[:int(ratio*len(all_items))]}
        query_rates[u] = {it: rates[u][it] for it in all_items[int(ratio*len(all_items)):]}
    return sup_rates, query_rates


def load_data(length, path):
    with open(path, encoding='utf8') as i_f:
        stus = json.load(i_f) # list
    rates = {}
    items = set()
    user_cnt = 0
    know_map = {}

    for stu in stus:
        seq = stu['seq']
        stu['logs'] = seq
        stu['log_num'] = len(seq)
        if stu['log_num'] < length * 2:
            continue
        user_cnt += 1
        rates[user_cnt] = {}
        for log in stu['logs']:
            problem_id = log['problem_id'][3:]
            rates[user_cnt][int(problem_id)] = int(log['is_correct'])
            items.add(log['problem_id'])
    return rates
def reward(action, state, rates, model, args, know_map):


if __name__ == '__main__':
    # args = {'T':10, 'data_path': './data/data/'}
    # env(args)
    rates = load_data(5,'data/student-problem-fine.json')
    sup_rates, query_rates = split_data(rates, ratio=0.5)
    print(sup_rates)
    state = [(0,1)]


