import os
import io
import sys
import logging
import argparse
import time
import json
import pandas as pd
import numpy as np
import tqdm
import random
import pdb
import torch
import torch.utils.data as Data
from torch.utils.data import TensorDataset, DataLoader
import csv


from EduCDM import MIRT

from load_data import DATA, PID_DATA

from models.NCD import NCDM



def parse_all_seq(args, students, data, questions, skills=None):
    all_sequences = []
    for student_id in tqdm.tqdm(students, 'parse student sequence:\t'):
        if args.models == 'DKVMN':
            student_sequence = parse_student_seq2(data[data.user_id == student_id], questions, skills)
        else:
            student_sequence = parse_student_seq1(data[data.user_id == student_id], questions)
        all_sequences.extend([student_sequence])
    return all_sequences


def parse_student_seq1(student, questions):
    seq = student.sort_values('submit_time')
    p = [questions[q] for q in seq.problem_id.tolist()]
    a = seq.is_correct.tolist()
    return p, a


def parse_student_seq2(student, problems, skills):
    seq = student.sort_values('submit_time')
    s = [skills[q] for q in seq.skill_id.tolist()]
    p = [problems[q] for q in seq.problem_id.tolist()]
    a = seq.is_correct.tolist()
    return s, p, a


def train_test_split(data, train_size=.7, shuffle=True):
    if shuffle:
        random.shuffle(data)
    boundary = round(len(data) * train_size)
    return data[: boundary], data[boundary:]


def sequences2tl(args, sequences, trgpath):
    with open(trgpath, 'w', encoding='utf8') as f:
        for seq in tqdm.tqdm(sequences, 'write into file: '):
            if args.models == 'DKVMN':
                skills, problems, answers = seq
                seq_len = len(skills)
                f.write(str(seq_len) + '\n')
                f.write(','.join([str(q) for q in problems]) + '\n')
                f.write(','.join([str(q) for q in skills]) + '\n')
                f.write(','.join([str(a) for a in answers]) + '\n')
            else:
                questions, answers = seq
                seq_len = len(questions)
                f.write(str(seq_len) + '\n')
                f.write(','.join([str(q) for q in questions]) + '\n')
                f.write(','.join([str(a) for a in answers]) + '\n')


def encode_onehot(sequences, max_step, num_questions):
    result = []

    for q, a in tqdm.tqdm(sequences, 'convert to one-hot format: '):
        length = len(q)
        # append questions' and answers' length to an integer multiple of max_step
        mod = 0 if length % max_step == 0 else (max_step - length % max_step)
        onehot = np.zeros(shape=[length + mod, 2 * num_questions])
        for i, q_id in enumerate(q):
            index = int(q_id if a[i] > 0 else q_id + num_questions)
            onehot[i][index] = 1
        result = np.append(result, onehot)
    return result.reshape(-1, max_step, 2 * num_questions)


def config():
    parser = argparse.ArgumentParser()

    # data process
    parser.add_argument("--data_dir", type=str, default='data/student-problem-fine.json')
    parser.add_argument("--data_problem_detail", type=str, default='data/problem.json')
    parser.add_argument("--data_process", action="store_true")
    parser.add_argument("--data_split", type=float, default=0.8)
    parser.add_argument("--data_shuffle", action="store_true")
    parser.add_argument("--saved_train_dir", type=str, default='../data/ktbd/train.txt')
    parser.add_argument("--saved_dev_dir", type=str, default='../data/ktbd/dev.txt')
    parser.add_argument("--saved_test_dir", type=str, default='../data/ktbd/test.txt')
    parser.add_argument("--encoded_train_dir", type=str, default='../data/DKT/train_data.npy')
    parser.add_argument("--encoded_test_dir", type=str, default='../data/DKT/test_data.npy')

    # baseline models
    parser.add_argument("--models", type=str, default="NCDM")
    parser.add_argument("--model_path", type=str, default="../data/DKT/dkt.params")

    # DKT parameters
    parser.add_argument("--max_step", type=int, default=50)
    parser.add_argument("--num_questions", type=int)
    parser.add_argument("--num_skills", type=int)

    parser.add_argument("--hidden_size", type=int, default=10)
    parser.add_argument("--num_layers", type=int, default=1)

    # cognitive diagnosis benchmark dataset
    parser.add_argument("--num_concept", type=int)
    parser.add_argument("--saved_item_dir", type=str, default='../data/cdbd/')

    # cognitive feature add
    parser.add_argument("--num_cognitive", type=int)
    parser.add_argument("--saved_cog_dir", type=str, default='../data/cdbd/')

    # training parameters
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--epoch", type=int, default=10)

    # logging parameters
    parser.add_argument("--logger_dir", type=str, default='../data')

    args = parser.parse_args()

    return args


def set_logger(args):
    logger = logging.getLogger(__name__)
    logger.setLevel(level=logging.INFO)
    now = time.strftime("%Y-%m-%d-%H_%M_%S", time.localtime(time.time()))
    handler = logging.FileHandler(os.path.join(args.logger_dir+ "log.txt"))

    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    logger.addHandler(handler)
    logger.addHandler(console)

    logger.info(args)

    return logger


def DKT_data_helper(args, logger):
    # 1. read the original file
    with open(args.data_dir, 'r', encoding='utf-8') as f_in:
        json_data = json.loads(f_in.read())
        # for line in f_in.readlines():
        #     dic = json.loads(line)
        #     json_data.append(dic)

    df_nested_list = pd.json_normalize(json_data, record_path=['seq'])

    # 2. define skills
    raw_question = df_nested_list.problem_id.unique().tolist()
    num_skill = len(raw_question)
    # question id from 0 to (num_skill - 1)
    questions = {p: i for i, p in enumerate(raw_question)}
    logger.info("number of skills: %d" % num_skill)
    args.num_questions = num_skill

    # 3. q-a list
    # [(question_sequence_0, answer_sequence_0), ..., (question_sequence_n, answer_sequence_n)]
    sequences = parse_all_seq(args, df_nested_list.user_id.unique(), df_nested_list, questions)



    # 4. split dataset
    train_sequences, test_sequences = train_test_split(sequences, args.data_split, args.data_shuffle)
    logger.info("data split with ratio {} and shuffle {}".format(args.data_split, args.data_shuffle))

    # 5. save triple line format for other tasks
    sequences2tl(args, train_sequences, args.saved_train_dir)
    sequences2tl(args, test_sequences, args.saved_test_dir)
    logger.info("triple line format trainset saved at {}".format(args.saved_train_dir))
    logger.info("triple line format testset saved at {}".format(args.saved_test_dir))

    # 6. onehot encode
    # reduce the amount of data for example running faster
    percentage = 1
    train_data = encode_onehot(train_sequences[: int(len(train_sequences) * percentage)], args.max_step, num_skill)
    test_data = encode_onehot(test_sequences[: int(len(test_sequences) * percentage)], args.max_step, num_skill)

    # save onehot data
    np.save(args.encoded_train_dir, train_data)
    np.save(args.encoded_test_dir, test_data)

    logger.info("data process done.")


def get_data_loader(data_path, batch_size, shuffle=False):
    data = torch.FloatTensor(np.load(data_path))
    data_loader = Data.DataLoader(data, batch_size=batch_size, shuffle=shuffle)
    return data_loader





def three_line_format_into_json(args, train_txt='../data/DKT/train.txt', test_txt='../data/DKT/test.txt'):
    # turn three line format into json:
    with open(train_txt) as f, io.open(args.saved_train_dir, "w", encoding="utf-8") as wf:
        for _ in tqdm.tqdm(f):
            exercise_tags = f.readline().strip().strip(",").split(",")
            response_sequence = f.readline().strip().strip(",").split(",")
            exercise_tags = list(map(int, exercise_tags))
            response_sequence = list(map(int, response_sequence))
            responses = list(zip(exercise_tags, response_sequence))
            print(json.dumps(responses), file=wf)

    with open(test_txt) as f, io.open(args.saved_test_dir, "w", encoding="utf-8") as wf:
        for _ in tqdm.tqdm(f):
            exercise_tags = f.readline().strip().strip(",").split(",")
            response_sequence = f.readline().strip().strip(",").split(",")
            exercise_tags = list(map(int, exercise_tags))
            response_sequence = list(map(int, response_sequence))
            responses = list(zip(exercise_tags, response_sequence))
            print(json.dumps(responses), file=wf)


def CDBD_data_helper(args, logger):
    # 1. read the original file
    with open(args.data_dir, 'r', encoding='utf-8') as f_in:
        json_data = json.loads(f_in.read())
        # for line in f_in.readlines():
        #     dic = json.loads(line)
        #     json_data.append(dic)

    df_nested_list = pd.json_normalize(json_data, record_path=['seq'])
    raw_question = df_nested_list.problem_id.unique().tolist()
    num_skill = len(raw_question)
    # problem map: (start from 1)
    map_problems = {p: i + 1 for i, p in enumerate(raw_question)}
    #保存map_problems
    with open('data/cdbd/map_problems.json', 'w') as f:
        json.dump(map_problems, f)
    logger.info("number of skills: %d" % num_skill)
    args.num_questions = num_skill

    # 2. read the problem detail file
    with open(args.data_problem_detail, 'r', encoding='utf-8') as f_in:
        problem_data = []
        for line in f_in.readlines():
            dic = json.loads(line)
            problem_data.append(dic)

    df_problem_detail = pd.json_normalize(problem_data)

    df_problem_detail_sub = df_problem_detail[df_problem_detail.problem_id.isin(raw_question)]
    # raw_concept = set()
    # for c in df_problem_detail_sub.concepts.tolist():
    #     raw_concept.add(c)
    # num_concept = len(raw_concept)
    # # concept map: (start from 1)
    # map_concepts = {c:i+1 for i, c in enumerate(raw_concept)}
    # logger.info("number of concepts: %d" % num_concept)
    # args.num_concept = num_concept

    # we map to course_id
    raw_concept = set()
    for c in df_problem_detail_sub.exercise_id.tolist():
        raw_concept.add(c)
    num_concept = len(raw_concept)
    print(raw_concept)
    # concept map: (start from 1)
    map_concepts = {c: i + 1 for i, c in enumerate(raw_concept)}

    logger.info("number of concepts: %d" % num_concept)
    args.num_concept = num_concept



    # 3. build item_id->knowledge_code
    item2knowledge = {}
    for index, row in tqdm.tqdm(df_problem_detail_sub.iterrows()):
        problem_id = row['problem_id']
        item2knowledge[map_problems[problem_id]] = []

        # concepts = row['concepts']
        # for per_concept in concepts:
        #     item2knowledge[map_problems[problem_id]].append(map_concepts[per_concept])

        concept = row['exercise_id']
        item2knowledge[map_problems[problem_id]].append(map_concepts[concept])

        # saved
    item_df = pd.DataFrame({'item_id': item2knowledge.keys(), 'knowledge_code': item2knowledge.values()})
    item_df.to_csv(args.saved_item_dir, sep=',', index=False, header=True)
    logger.info("item.csv saved!")

    # same way build item2cognitive
    raw_cognitive = set()
    for cog in df_problem_detail_sub.cognitive_dimension.tolist():
        raw_cognitive.add(cog)
    num_cognitive = len(raw_cognitive)
    map_cognitives = {c: i + 1 for i, c in enumerate(raw_cognitive)}
    logger.info("number of cognitive: %d" % num_cognitive)
    args.num_cognitive = num_cognitive

    # build item_id->cognitive_dimension
    item2cognitive = {}
    for index, row in tqdm.tqdm(df_problem_detail_sub.iterrows()):
        problem_id = row['problem_id']
        cog = row['cognitive_dimension']
        item2cognitive[map_problems[problem_id]] = map_cognitives[cog]

    # saved
    item_df = pd.DataFrame({'item_id': item2cognitive.keys(), 'cognitive_dimension': item2cognitive.values()})
    item_df.to_csv(args.saved_cog_dir, sep=',', index=False, header=True)
    logger.info("cog.csv saved!")

    # 4. build user map
    raw_users = df_nested_list.user_id.unique().tolist()
    num_users = len(raw_users)
    # users map: (start from 1)
    map_users = {u: i + 1 for i, u in enumerate(raw_users)}
    #保存map_users
    with open('data/cdbd/map_users.json', 'w') as f:
        json.dump(map_users, f)
    logger.info("number of users: %d" % num_users)
    args.num_questions = num_users

    # 5. build dataset
    dataset = df_nested_list[['user_id', 'problem_id', 'is_correct']]
    dataset['user_id'] = dataset['user_id'].map(map_users)
    dataset['problem_id'] = dataset['problem_id'].map(map_problems)
    dataset['cognitive_dimension'] = dataset['problem_id'].map(item2cognitive)

    # 6. split dataset
    if args.data_shuffle:
        dataset = dataset.sample(frac=1)
        boundary = round(len(dataset) * args.data_split)
    train_df = dataset[:boundary]
    test_df = dataset[boundary:]
    boundary = round(len(test_df) * 0.5)
    dev_df = test_df[:boundary]
    test_df = test_df[boundary:]

    # saved train and test csv
    train_df.to_csv(args.saved_train_dir, sep=',', index=False, header=True)
    test_df.to_csv(args.saved_test_dir, sep=',', index=False, header=True)
    dev_df.to_csv(args.saved_dev_dir, sep=',', index=False, header=True)
    logger.info("data process done!")


def transform1(user, item, item2knowledge, score, batch_size, knowledge_n, item2cognitive, cognitive_n):
    knowledge_emb = torch.zeros((len(item), knowledge_n))
    for idx in range(len(item)):
        knowledge_emb[idx][np.array(item2knowledge[item[idx]]) - 1] = 1.0

    cognitive_emb = torch.zeros((len(item), cognitive_n))
    for idx in range(len(item)):
        cognitive_emb[idx][np.array(item2cognitive[item[idx]]) - 1] = 1.0

    data_set = TensorDataset(
        torch.tensor(user, dtype=torch.int64) - 1,  # (1, user_n) to (0, user_n-1)
        torch.tensor(item, dtype=torch.int64) - 1,  # (1, item_n) to (0, item_n-1)
        knowledge_emb,
        cognitive_emb,
        torch.tensor(score, dtype=torch.float32)
    )
    return DataLoader(data_set, batch_size=batch_size, shuffle=True)


def transform2(x, y, z, batch_size, item2cognitive, cognitive_n, **params):
    cognitive_emb = torch.zeros((len(y), cognitive_n))
    for idx in range(len(y)):
        cognitive_emb[idx][np.array(item2cognitive[y[idx]]) - 1] = 1.0

    dataset = TensorDataset(
        torch.tensor(x, dtype=torch.int64),
        torch.tensor(y, dtype=torch.int64),
        cognitive_emb,
        torch.tensor(z, dtype=torch.float)
    )
    return DataLoader(dataset, batch_size=batch_size, **params)


def CDBD_Baseline(args, logger):
    if (not os.path.exists(args.saved_train_dir)) or (not os.path.exists(args.saved_test_dir)):
        sys.exit()
    train_data = pd.read_csv(args.saved_train_dir)
    test_data = pd.read_csv(args.saved_test_dir)
    dev_data = pd.read_csv(args.saved_dev_dir)
    df_item = pd.read_csv(args.saved_item_dir)
    df_cog = pd.read_csv(args.saved_cog_dir)

    item2knowledge = {}
    knowledge_set = set()

    for i, s in df_item.iterrows():
        item_id, knowledge_codes = s['item_id'], list(set(eval(s['knowledge_code'])))
        item2knowledge[item_id] = knowledge_codes
        knowledge_set.update(knowledge_codes)

    item2cognitive = {}
    cognitive_set = set()

    for i, s in df_cog.iterrows():
        item_id, cognitive_dimension = s['item_id'], s['cognitive_dimension']
        item2cognitive[item_id] = cognitive_dimension
        cognitive_set.add(cognitive_dimension)

    user_n = np.max(train_data['user_id'])

    item_n = np.max([np.max(train_data['problem_id']), np.max(dev_data['problem_id']), np.max(test_data['problem_id'])])
    knowledge_n = np.max(list(knowledge_set))
    cognitive_n = np.max(list(cognitive_set))
    logger.info('user_n: {}\n item_n: {}\n knowledge_n: {}\n cognitive_n: {}\n'.format(user_n, item_n, knowledge_n,
                                                                                       cognitive_n))

    if args.models == 'NCDM':
        train_set, valid_set, test_set = [
            transform1(data["user_id"], data["problem_id"], item2knowledge, data["is_correct"], args.batch_size,
                       knowledge_n, item2cognitive, cognitive_n)
            for data in [train_data, dev_data, test_data]
        ]

        cdm = NCDM(knowledge_n, item_n, user_n, cognitive_n)
    elif args.models == 'MIRT' or args.models == 'GDIRT':
        train_set, valid_set, test_set = [
            transform2(data["user_id"], data["problem_id"], data["is_correct"], args.batch_size, item2cognitive,
                       cognitive_n)
            for data in [train_data, dev_data, test_data]
        ]
        cdm = MIRT(user_n + 1, item_n + 1, knowledge_n)

    cdm.train(train_set, valid_set, epoch=args.epoch, device="cuda", lr=0.0003)

    cdm.save(args.model_path)
    logger.info("{} model saved!".format(args.models))

    cdm.load(args.model_path)
    auc, accuracy = cdm.eval(test_set)
    logger.info("auc: %.6f, accuracy: %.6f" % (auc, accuracy))

def CDBD_test(args, logger):
    if (not os.path.exists(args.saved_train_dir)) or (not os.path.exists(args.saved_test_dir)):
        sys.exit()
    train_data = pd.read_csv(args.saved_train_dir)
    test_data = pd.read_csv(args.saved_test_dir)
    dev_data = pd.read_csv(args.saved_dev_dir)
    df_item = pd.read_csv(args.saved_item_dir)
    df_cog = pd.read_csv(args.saved_cog_dir)

    item2knowledge = {}
    knowledge_set = set()

    for i, s in df_item.iterrows():
        item_id, knowledge_codes = s['item_id'], list(set(eval(s['knowledge_code'])))
        item2knowledge[item_id] = knowledge_codes
        knowledge_set.update(knowledge_codes)

    item2cognitive = {}
    cognitive_set = set()

    for i, s in df_cog.iterrows():
        item_id, cognitive_dimension = s['item_id'], s['cognitive_dimension']
        item2cognitive[item_id] = cognitive_dimension
        cognitive_set.add(cognitive_dimension)

    user_n = np.max(train_data['user_id'])

    item_n = np.max([np.max(train_data['problem_id']), np.max(dev_data['problem_id']), np.max(test_data['problem_id'])])
    knowledge_n = np.max(list(knowledge_set))
    cognitive_n = np.max(list(cognitive_set))
    logger.info('user_n: {}\n item_n: {}\n knowledge_n: {}\n cognitive_n: {}\n'.format(user_n, item_n, knowledge_n,
                                                                                       cognitive_n))

    if args.models == 'NCDM':
        train_set, valid_set, test_set = [
            transform1(data["user_id"], data["problem_id"], item2knowledge, data["is_correct"], args.batch_size,
                       knowledge_n, item2cognitive, cognitive_n)
            for data in [train_data, dev_data, test_data]
        ]

        cdm = NCDM(knowledge_n, item_n, user_n, cognitive_n)

    # cdm.train(train_set, valid_set, epoch=args.epoch, device="cuda", lr=0.0003)

    # cdm.save(args.model_path)
    # logger.info("{} model saved!".format(args.models))

    cdm.load(args.model_path)
    auc, accuracy = cdm.eval(test_set)
    logger.info("auc: %.6f, accuracy: %.6f" % (auc, accuracy))

if __name__ == '__main__':
    args = config()
    logger = set_logger(args)
    # CDBD_test(args, logger)
    #
    if args.models == 'NCDM' or args.models == 'MIRT' or args.models == 'GDIRT':
        CDBD_data_helper(args, logger)
    #
    # if args.models == 'NCDM' or args.models == 'MIRT' or args.models == 'GDIRT':
    #     CDBD_Baseline(args, logger)




