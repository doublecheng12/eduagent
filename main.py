import os
import yaml
import numpy as np
from langchain.chat_models import AzureChatOpenAI, ChatOpenAI
import gymnasium as gym
from gymnasium.wrappers import RecordVideo
from scenario.scenario import Scenario
from agent import EduAgent
from agent.outAgent import OutputParser
from agent.customTools import (
    isQuestionSuitable
)
env = gym.make('highway-v0', render_mode="rgb_array")
OPENAI_CONFIG = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)

if OPENAI_CONFIG['OPENAI_API_TYPE'] == 'azure':
    os.environ["OPENAI_API_TYPE"] = OPENAI_CONFIG['OPENAI_API_TYPE']
    os.environ["OPENAI_API_VERSION"] = OPENAI_CONFIG['AZURE_API_VERSION']
    os.environ["OPENAI_API_BASE"] = OPENAI_CONFIG['AZURE_API_BASE']
    os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['AZURE_API_KEY']
    llm = AzureChatOpenAI(
        deployment_name=OPENAI_CONFIG['AZURE_MODEL'],
        temperature=0,
        max_tokens=1024,
        request_timeout=60
    )
elif OPENAI_CONFIG['OPENAI_API_TYPE'] == 'openai':
    os.environ["OPENAI_API_KEY"] = OPENAI_CONFIG['OPENAI_KEY']
    llm = ChatOpenAI(
        temperature=0,
        model_name='gpt-3.5-turbo-1106', # or any other model with 8k+ context
        max_tokens=1024,
        request_timeout=60
    )


# base setting
vehicleCount = 15

# environment setting
config = {
    "observation": {
        "type": "Kinematics",
        "features": ["presence", "x", "y", "vx", "vy"],
        "absolute": True,
        "normalize": False,
        "vehicles_count": vehicleCount,
        "see_behind": True,
    },
    "action": {
        "type": "DiscreteMetaAction",
        "target_speeds": np.linspace(0, 32, 9),
    },
    "duration": 40,
    "vehicles_density": 2,
    "show_trajectories": True,
    "render_agent": True,
}




# scenario and driver agent setting
if not os.path.exists('results-db/'):
    os.mkdir('results-db')
database = f"results-db/highwayv0.db"
sce = Scenario(vehicleCount, database)
toolModels = [
    isQuestionSuitable
]
CAT = EduAgent(llm, toolModels, sce, verbose=True)
outputParser = OutputParser(sce, llm)
output = None
done = truncated = False
frame = 0
try:
    while not (done or truncated):
        sce.upateStudent(obs, frame)
        CAT.agentRun(output)
        da_output = CAT.exportThoughts()
        output = outputParser.agentRun(da_output)
        env.render()
        env.unwrapped.automatic_rendering_callback = env.video_recorder.capture_frame()
        obs, reward, done, info, _ = env.step(output["action_id"])
        print(output)
        frame += 1
finally:
    env.close()