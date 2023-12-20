import pandas as pd
import numpy as np
import json
import ast
from typing import Any
problem_ids = []
def prompts(name, description):
    def decorator(func):
        func.name = name
        func.description = description
        return func

    return decorator
with open('data/student-problem-fine.json', 'r') as f:
    f = json.load(f)
    s = ''
    user_id = 'U_29242213'
    for item in f:
        seq = item['seq']
        if seq[0]['user_id'] == user_id:
            s = item
    logs = s['seq']
    for log in logs:
        print(log['problem_id'])
        problem_ids.append(log['problem_id'])

with open('data/problem.json','r',encoding='utf-8') as f:
    f = f.readlines()
    lines = [line for line in f]
    for line in lines:
        line = json.loads(line)
        if line['problem_id'] in problem_ids:
            line['detail'] = ast.literal_eval(line['detail'])
            print(line['problem_id'],line['detail']['content'])





