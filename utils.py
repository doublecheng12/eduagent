# https://platform.openai.com/docs/api-reference
# pip install openai
import os
import ast
import json
import openai

openai.api_base = "https://api.chatanywhere.tech/v1"


class ChatGPT:
    def __init__(self, apikey) -> None:
        openai.api_key = apikey

    def req(self, prompt):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            # model="gpt-4-8k",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        return response['choices'][0]['message']['content']
def get_knowledge_state(record,problems_detail):
    apikey = "sk-dRElekBr6bZzh7OKyHQsCvq9yzV3OIAA6UJN0OqFu1YcygAZ"  # bzr
    llm = ChatGPT(apikey)
    prompt = f"""
    你现在是一名教育诊断专家，需要你对我接下来给你的学生做题记录进行一段细粒度的描述，你需要描述这个学生的知识状态，描述学生在所做题目包含的知识点上的掌握情况，输出结果为一段文本词 + 知识点的熟练度估计值，每个熟练度估计值的范围为0-1，0表示不熟练，1表示熟练，请在标注熟练度时仔细思考，细粒度的标注。
    以下是学生的做题记录：
    "{record}".
    以及题目的详细对应信息:
    "{problems_detail}"
    请给这个学生生成一段描述词 + 知识点的熟练度估计值
    
    """
    return llm.req(prompt)

if __name__ == '__main__':
    # apikey = "sk-dRElekBr6bZzh7OKyHQsCvq9yzV3OIAA6UJN0OqFu1YcygAZ"  # bzr
    # llm = ChatGPT(apikey)
    # with open('problem.json', 'r', encoding='utf-8') as f:
    #     f = f.readlines()
    #     lines = [line for line in f]
    #     for line in lines:
    #         line = json.loads(line)
    #         line['detail'] = ast.literal_eval(line['detail'])
    #         print(line['detail']['content'], line['concepts'], line['cognitive_dimension'])
    #         prompt = f"""
    #         你现在是一名教育专家，需要对我接下来给你的题目进行一段细粒度的描述，你需要描述这道题目的知识点，难度，以及题目的内容。
    #         我会给你这个题目的知识点，认知维度，以及题目的内容，认知维度使用的是Bloom Cognitive Taxonomy to construct，共分为6级。
    #         以下是题目的内容：
    #         "{line['detail']['content']}"
    #         题目的知识点是：:
    #         "{line['concepts']}"
    #         题目的认知维度是：
    #         "{line['cognitive_dimension']}"
    #         请给这个题目生成一段描述词
    #         """
    #         res = llm.req(prompt)
    #         # 保存到文件
    #         with open('problem_description.json', 'a', encoding='utf-8') as f:
    #             problem = {}
    #             problem['problem_id'] = line['problem_id']
    #             problem['description'] = res
    #             f.write(json.dumps(problem, ensure_ascii=False) + '\n')
    record = "1.正确 2.错误 3.正确 4，正确 5，错误"
    problems_detail = """1编写一个简单的Python程序，打印出Hello, World!  知识点：Python基础
                         2解决一个关于二进制搜索的算法问题。  知识点：算法与数据结构
                         3.完成一个有关链表数据结构的编程作业。 知识点：算法与数据结构
                         4.学习如何使用Python处理文件操作，并编写一个简单的文件处理程序。 知识点：Python基础,文件操作
                         5.学习如何使用python画图，并画出一个简单的图形。 知识点：Python基础,画图
                       """
    print(get_knowledge_state(record,problems_detail))