from typing import Any
import json
import ast
import numpy as np
def prompts(name, description):
    def decorator(func):
        func.name = name
        func.description = description
        return func

    return decorator

def get_logs(user_id):
    with open('../data/student-problem-fine.json', 'r') as f:
        f = json.load(f)
        s = ''
        problem_ids = []
        for item in f:
            seq = item['seq']
            if seq[0]['user_id'] == user_id:
                s = item
        logs = s['seq']
        for log in logs:
            problem_ids.append(log['problem_id'])

    with open('../data/problem.json', 'r', encoding='utf-8') as f:
        f = f.readlines()
        problem_dict = {}
        problems = {}
        lines = [line for line in f]
        for line in lines:
            line = json.loads(line)
            if line['problem_id'] in problem_ids:
                key = line['problem_id']
                line['detail'] = ast.literal_eval(line['detail'])
                problem_dict[key] = line['detail']['content']
        return problem_dict


#将dict按0.8:0.2划分
def split_dict(d, ratio=0.8):
    train_dict = {}
    val_dict = {}
    for key in d:
        if np.random.random() < ratio:
            train_dict[key] = d[key]
        else:
            val_dict[key] = d[key]
    return train_dict, val_dict


class isQuestionSuitable:
    def __init__(self) -> None:
        pass
    @prompts(name='Decision-making Instructions',
             description="""This tool gives you a brief introduction about how to ensure that the problem you make is suitable for student. The input to this tool should be a string, which is ONLY the action name.""")
    def inference(self, action: str) -> str:
        return f"""To check problem suitable you should follow two steps:
        Step 1: You need to assess the students' knowledge level.Diagnose students' proficiency in different knowledge areas.
        Step 2:Assess the difficulty of different questions and select the ones that best match the students' current proficiency level to give them.
        Follow the instructions and remember to use the proper tools mentioned in the tool list once a time.
        """
