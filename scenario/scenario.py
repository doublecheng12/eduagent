from scenario.baseClass import Question,Student
from typing import List, Dict
from datetime import datetime
from rich import print
import sqlite3
import json
import os


class Scenario:
    def __init__(self, database: str = None) -> None:
        self.question: Dict[str, Question] = {}
        self.student: Dict[str, Student] = {}
        self.initStudent()

        if database:
            self.database = database
        else:
            self.database = datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.db'

        if os.path.exists(self.database):
            os.remove(self.database)

        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS stuINFO(
                frame INT,
                id TEXT,
                knowledge_state text,
                answer_experience text,
               
                PRIMARY KEY (frame, id));"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS decisionINFO(
                frame INT PRIMARY KEY,
                scenario TEXT,
                thoughtsAndActions TEXT,
                finalAnswer TEXT,
                outputParser TEXT);"""
        )
        conn.commit()
        conn.close()

        self.frame = 0



    def initStudent(self):
        uid = 'stu'
        self.student[uid] = Student(id=uid)

    def upateStudent(self, observation: List[List], frame: int):
        self.frame = frame
        conn = sqlite3.connect(self.database)
        cur = conn.cursor()
        knowledge_state,answer_experience = observation[0]
        uid = 'stu'
        veh = self.student[uid]
        veh.presence = True
        cur.execute(
            '''INSERT INTO stuINFO VALUES (?,?,?,?,?,?,?);''',
            (frame, uid, str(knowledge_state), str(answer_experience),
             )
        )

        conn.commit()
        conn.close()

    def export2json(self):
        scenario = {}
        scenario['questions'] = []
        scenario['student'] = []
        for qs in self.question.values():
            scenario['questions'].append(qs.export2json())
        scenario['stu_info'] = self.student['stu'].export2json()


        return json.dumps(scenario)