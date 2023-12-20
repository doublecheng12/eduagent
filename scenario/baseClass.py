from typing import List, Dict, Tuple, Union
from dataclasses import dataclass, field

@dataclass
class Question:
    id: str
    difficulty: float
    topic: str
    required_knowledge: List[str] = field(default_factory=list)

    def export2json(self):
        return {
            'id': self.id,
            'difficulty': self.difficulty,
            'required knowledge': self.required_knowledge,
        }


@dataclass
class Student:
    id: str
    current_question: str = ''
    knowledge_level: str = ''
    answer_experience: str = ''
    has_attempted: bool = False

    def reset(self) -> None:
        self.current_question = ''
        self.knowledge_level = ''
        self.answer_experience = ''
        self.has_attempted = False

    def updateStatus(
        self, question: str, knowledge: str, experience: str
    ) -> None:
        self.current_question = question
        self.knowledge_level = knowledge
        self.answer_experience = experience



    def export2json(self) -> Dict:
        return {
            'id': self.id,
            'current question': self.current_question,
            'knowledge level': self.knowledge_level,
            'answer experience' : self.answer_experience
        }
