#!/usr/bin/env python
# coding: utf-8

# In[5]:


think_template = """
1. 定义写作目的和类型
   - 目的：明确设定文章目标（如：信息传递、说服或启发），确立基调和方向。
   - 类型：选择合适的写作风格（如：论证型、说明型或商务写作），以支持预期的形式和结构。明确识别写作类型并描述该体裁的风格特点。

2. 规划内容和结构
   - 核心要点：概述关键信息以确保主题清晰，和给出的任务结合紧密。
   - 结构：创建组织良好的框架，确保逻辑流畅。

3. 角色与情节（如果为叙事写作）
   - 角色发展：定义所有角色的特质和动机。提供详细描述，包括具体细节（姓名、性别等）和关系。
   - 情节发展：设定关键情节点和情感线索以推动故事发展。根据结构提供详细解释。

4. 其他建议
   - 格式要求：根据内容需求和呈现方式自动选择合适的输出格式（如Markdown、项目符号等），以增强视觉吸引力和清晰度。
   - 其他关键要素：添加特定于当前题材或任务的其他要点。

"""


# In[ ]:


import time
import logging
from openai import OpenAI  # 假设 openai 包可用并导入
# 配置日志记录
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
import threading
lock = threading.Lock()
import re
import pandas as pd
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 请求函数

def get_response(query, api_key):
 
    if api_key is None:
        raise ValueError("An OpenAI API key must be provided via the api_key parameter.")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "4o-0816",
        "messages": [
            {"role": "user", "content": query}
        ],
        "temperature": 0.6,
        "top_p": 1,
        "max_tokens": 16384
    }

    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=1800)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Attempt {attempt + 1}/3 failed: {e}")
    print("Failed to get a response after 3 attempts")
    return ""

def extract_info(pattern, text):
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None

#
# 基于请求函数的 Agent 框架
class ChatAgent:
    def __init__(self):
        self.session_history = []  # 用于存储会话历史
        self.active = True         # 标志 Agent 是否在运行

    def start(self):
        # logging.info("Agent 已启动，输入 'exit' 以退出对话")
        while self.active:
            user_input = input("用户: ")
            if user_input.strip().lower() == 'exit':
                self.stop()
            else:
                self.session_history.append({'role': 'user', 'content': user_input})
                response = get_response(user_input)
                #print(f"Agent: {response}")
                self.session_history.append({'role': 'agent', 'content': response})

    def stop(self):
        # logging.info("Agent 即将停止...")
        self.active = False
        time.sleep(1)  # 停止前的短暂等待，方便用户看到提示
        # logging.info("Agent 已停止")

# Initialization and Topic Setting Agent
class InitializationAgent:
    def __init__(self):
        self.outline = None
        self.iteration_count = 0

    def generate_outline(self, topic,Task_Chain_of_thought):
        task_define_result,Task_Chain_of_thought = self.iterative_task_definition(topic,2,Task_Chain_of_thought)

        #print(task_define_result)
    
        logging.info(f"生成初步大纲: {topic}, 第 {self.iteration_count + 1} 次迭代")
        prompt = (
            f"现在用户需求为 ### {topic}，请充分理解任务设计 ### {task_define_result}。"
            "根据任务设计，确定一个适当的文章标题并生成一个详细且结构化的大纲。"
            "大纲最好不超过20个段落，每个段落都应包含详细描述和具体字数要求。"
            "请合理规划字数范围，需要思考完成用户目标所需要的字数范围。如果用户有明确需求使用用户需求"
            "再根据任务难度设定适当的总体字数（不超过16000字），并将其分配到每个段落。"
            "然后，提供大纲以及每个段落相应的字数要求。"
            "确保每个段落描述都包含预期内容，保持清晰的逻辑性，并与用户目标保持一致。"
        )

        self.outline = get_response(prompt)
        Task_Chain_of_thought.append({
                'agent': 'InitializationAgent_outline',
                'token': 'Gen_ouline',
                'content':self.outline
            })
        #print("outline:",self.outline)
        check_result = self.check_outline(task_define_result)
        Task_Chain_of_thought.append({
                'agent': 'InitializationAgent_check_outline',
                'token': 'Reflective',
                'content':check_result
            })
        self.iteration_count += 1
        if "pass" in check_result.lower() and self.iteration_count > 1:
            return task_define_result+self.outline, Task_Chain_of_thought
        else:
            self.refine_outline(check_output=check_result)
            Task_Chain_of_thought.append({
                'agent': 'InitializationAgent_refine_outline',
                'token': 'Refine',
                'content':self.outline
            })
        return task_define_result,self.outline, Task_Chain_of_thought

    def check_outline(self,task_define_result):
        # logging.info("检查大纲")
        prompt = (
            f"您是一位优秀的大纲审核专家。现在，您将审查以下大纲，并根据当前文章框架验证其逻辑结构是否完整并与主题目标一致。###\n"
            f"### 任务设计:\n{task_define_result}### 大纲:\n{self.outline}\n"
            "请提供详细反馈，指出任何逻辑缺口或缺失要素。"
        )

      
        return get_response(prompt)

    def refine_outline(self, check_output):
        # logging.info("根据检查结果修改大纲")
        prompt = (
            f"您是一位专业的大纲编辑。根据以下反馈，改进大纲以确保其包含所有必要部分并保持逻辑连贯性：\n"
            f"### 反馈: {check_output}\n### 当前大纲: {self.outline}。 "
            "请提供修订后的文章标题和大纲的内容："
        )
        self.outline = get_response(prompt)
        #print(self.outline)

    
    def task_define_agent(self,topic, Task_Chain_of_thought):
        logging.info("确定大纲任务")
        prompt = (
            f"您是一位精通各类写作任务的专业作家，负责根据以下思维模板创建初始设计。"
            f"请使用下面的思维模板深入分析并为### 用户需求:{topic}。制定详细的初步设计方案。"
            f"仔细审查模板中的每个要点，确保所有细节和逻辑链条都被充分考虑，提供全面完整的写作计划，避免模糊信息，同时需要便于读者理解。"
            f"同时，确保结构不过于复杂，内容可以在不超过16000字内完成。"
            f"### 思维模板：{think_template}。这个阶段不需要给出大纲，只需完成仔细思考以完成任务设计。请给出任务设计的规划，并注意贴合用户需求不要偏离："
        )

        task_define_result = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'InitializationAgent_task_define',
            'token': 'Main_Outline_think',
            'content': task_define_result
        })
        return task_define_result,Task_Chain_of_thought

    def questioner_agent(self,topic, task_output, Task_Chain_of_thought):
        # logging.info("提问者检查任务并给出反馈")
        prompt = (
            f"您是一位高度批判性的审核者，专长于识别任务设计中的问题和缺陷。"
            f"请审查以下任务设计，并提出至少3个问题，以确保它满足用户需求的要求。需要保证充足的易读性。"
            f"这些问题应在正式写作前经过仔细考虑和澄清，指出任何逻辑缺陷、模糊之处或可能使读者感到困惑的地方。"
            f"对于不同类型的任务，您将从各种角度进行分析，例如演讲是否引人入胜，小说是否创新，或学术论文是否严谨。"
            f"用户需求：{topic}。任务设计：{task_output}。"
            f"请提供详细问题以及具体而实用的建议来改进任务设计："
        )

        feedback_result = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'QuestionerAgent_feedback',
            'token': 'Reflective',
            'content': feedback_result
        })
        return feedback_result, Task_Chain_of_thought

    def revision_agent(self,task_output, feedback, Task_Chain_of_thought):
        # logging.info("根据提问者的反馈修改任务")
        prompt = (
            f"您是一位经验丰富的作家，专注于改进任务设计，负责根据审核者的反馈修改任务。"
            
            f"原始任务设计：{task_output}。反馈：{feedback}。利用这些反馈，您将对当前任务设计进行详细而具体的修改，通过您自己的见解来解决所有不足。"
        )

        revision_result = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'RevisionAgent_modification',
            'token':'Refine',
            'content': revision_result
        })
        return revision_result, Task_Chain_of_thought

    def iterative_task_definition(self,topic, iterations=3, Task_Chain_of_thought=[]):
        
        # Step 1: Initial Task Definition
        task_output = self.task_define_agent(topic, Task_Chain_of_thought)
        #print(task_output)

        for i in range(iterations):
            # logging.info(f"\n\nIteration {i + 1} of task refinement")
            
            # Step 2: Questioner provides feedback
            feedback,Task_Chain_of_thought = self.questioner_agent(topic, task_output, Task_Chain_of_thought)
            #print(feedback)
            # Step 3: Revision Agent modifies the task output
            revised_task_output,Task_Chain_of_thought = self.revision_agent(task_output, feedback, Task_Chain_of_thought)
            #print(revised_task_output)
            # Update task_output for next iteration
            task_output = revised_task_output

        return task_output, Task_Chain_of_thought
        


def extract_content(text):
    match = re.search(r'\$\$(.*?)\$\$', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
# Paragraph Extraction Agent
class ParagraphExtractionAgent:
    def extract_key_points(self, outline):
        # logging.info("提取大纲中的段落描述和标题")
        prompt = (
            f"""
            从以下大纲中提取文章标题以及每个段落的描述和字数要求：
            {outline}
            请确保返回的内容按照以下JSON格式：
            {{
                "title": "[标题]",
                "paragraphs": [
                    {{"content": "[第1段描述]", "word_count": 200}},
                    {{"content": "[第2段描述]", "word_count": 250}},
                    ...
                ]
            }}
            """
        )

        # response = get_response(prompt)
        #print('Extraction', response)
        for i in range(3):
            response = get_response(prompt)
            #print('Extraction', response)
            try:
                # Handle response that may contain JSON wrapped in ```json code block
                if '```json' in response:
                    response = extract_info(r'```json\n(.*?)\n```', response)
                response = response.replace('\n', '')
                response_json = json.loads(response)
                break
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response: {e}")
                response_json = {}
        
        
        title = response_json.get("title", "")
        paragraphs = response_json.get("paragraphs", [])
        key_points = [
            f"paragraph_{i+1}: {paragraph.get('content', '')}, {paragraph.get('word_count', 0)} words"
            for i, paragraph in enumerate(paragraphs)
        ]
        
        return title, key_points


class ParagraphAgent:
    def generate_paragraph(self, outline, key_point, previous_paragraphs, Task_Chain_of_thought):
        # Step 1: Thought Generation (思考阶段)
        # logging.info(f"生成段落:")
        thought_prompt = (
            f"您是一位优秀的写作专家，善于在生成每个段落前进行周密的规划。### 大纲: {outline}\n### 前面的段落: {previous_paragraphs}\n### 当前段落的关键点: {key_point}\n"
            "请为新段落仔细制定一个写作计划。您可以考虑以下几点但不限于下面几点：\n"
            "1. 目标：这个段落的主要目标是什么？它应传达什么信息或情感？要写多少字数\n"
            "2. 结构：这个段落的内容应如何组织？什么样的逻辑顺序最能确保理解顺畅，以及它将如何紧密连接到前面的内容？是否过于复杂，不便于阅读\n"
            "3. 过渡：这个段落如何自然地与前一段连接？有哪些特定的过渡句或衔接技巧可以使用？\n"
            "4. 细节和例子：需要哪些细节、事实或例子来支持主要观点？这些应该如何安排？\n"
            "5. 语言风格和技巧：为了达到目标，应使用什么样的语言风格？是否有特定的修辞手法（如隐喻或类比）可以增强段落的冲击力？但又不会过于浮夸\n"
            "6. Markdown格式：使用Markdown整齐地构建输出，根据需要提供标题、项目符号或粗体文本，以增强可读性。\n"
            "根据大纲的具体内容和这个段落的关键点，构建一个详细的写作计划，根据需要添加其他必要的考虑因素，并牢记字数要求。这里只需要提供生成新的下一个段落的背后的思考过程，而不非段落本身。"
        )

        thought_response = get_response(thought_prompt)
        #print('Thought Process:', thought_response)

        # Append thought process to the Task_Chain_of_thought
        Task_Chain_of_thought.append({
            'agent': 'ParagraphAgent',
            'token': 'Paragraph_focus_think',
            'content': thought_response
        })

        # Step 2: Paragraph Generation (写作阶段)
        writing_prompt = (
            f"您是一位优秀的写作专家，善于使用合适的方式完成写作任务，并保证简单易懂，可读性高，逻辑严密。### 大纲: {outline}\n### 前面的段落: {previous_paragraphs}\n### 新段落的关键点: {key_point}\n"
            f"### 思考内容: {thought_response}\n"
            "基于上述思考内容和现有段落，撰写新的一个段落。仅提供新段落的完整内容，生成的段落内容用$$包裹，例如: $$内容$$。新段落："
        )

        paragraph_response = get_response(writing_prompt)
        paragraph_response = extract_content(paragraph_response)
        Task_Chain_of_thought.append({
            'agent': 'ParagraphAgent',
            'token' :'Generation',
            'content': paragraph_response
        })

        #print('Generated Paragraph:', paragraph_response)

        return paragraph_response, Task_Chain_of_thought



# Check Agent (Language Optimization + Logic and Coherence Check)
class CheckAgent:
    def check_paragraph(self, paragraph_id, paragraph,Task_Chain_of_thought):
        # logging.info(f"检查段落: {paragraph_id}")
        prompt = (
            f"检查以下段落的语法、风格、逻辑和连贯性:\n### 段落内容: {paragraph}\n"
            "请提供详细反馈，指出需要改进的部分。如果段落符合标准，给出理由，并返回 'pass'。"
        )
        response = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'CheckAgent',
            'content':response
        })
        return response, Task_Chain_of_thought

# Decision Agent
class DecisionAgent:
    def decide_action(self, check_result):
        # logging.info("决策代理正在分析检查结果")
        return "pass" if "pass" in check_result.lower() else "rewrite"

# Feedback Loop Agent
class FeedbackLoopAgent:
    def feedback_loop(self, paragraph_id, paragraph, check_output, previous_paragraphs,Task_Chain_of_thought):
        # logging.info(f"分析反馈: {paragraph_id}")
        if paragraph_id == "final":
            prompt = (
                f"根据以下反馈对整篇文档进行改进:  \n### 当前文档: {paragraph} \n### 反馈: {check_output}"
                "请确保改写后的文档在逻辑、语言风格和整体一致性方面达到高标准。规范行文，确保每个段落之间的衔接自然。请仔细思考明确修改内容，并给出构思如何修改，这一部分属于模型思考需要使用[think]包围输出。例如,[think]根据反馈....[think]，然后给出最终的修改后的版本。现在开始思考并生成: [think]"
            )
            response = get_response(prompt)
            print('\nresponese:',response)
        else:
            prompt = (
                f"根据以下反馈对段落进行改写: \n### 之前的段落: {previous_paragraphs} \n### 当前需要修改的段落: {paragraph} \n###反馈: {check_output}"
                "\n请仔细思考明确修改内容，并给出构思如何修改，这一部分属于模型思考需要使用[think_start]和[think_end]包围输出。例如,[think_start]根据反馈....[think_end]。然后给出修改后的当前需要修改的段落。现在开始思考并生成: [think_start]"
            )
            response = get_response(prompt)
            print('\nresponese:',response)
        Task_Chain_of_thought.append({
            'agent': 'FeedbackLoopAgent',
            'content':response
        })
        if "[think_end]" in response:
            response = response.split("[think_end]")[-1].strip()
        return response,Task_Chain_of_thought


# Comprehensive Review Agent
class ComprehensiveReviewAgent:
    def review_document(self, current_document,Task_Chain_of_thought):
        # logging.info("进行逐段审查并修改")
        updated_document = current_document.copy()

        for idx in range(len(current_document)):
            # Step 1: Combine current document into a complete text with paragraph labels
            combined_document = "\n".join([f"段落 {i+1}: {para}" for i, para in enumerate(updated_document)])
            prompt = (
                f"作为一位细致的文档审查者，您的任务是仔细阅读整篇文档，理解其整体结构和逻辑，然后对第{idx + 1}段进行详细审查，提供修改建议：\n{combined_document}\n"
                f"在审查第{idx + 1}段时，请考虑可以参考但不限于以下几点：\n"
                f"1. 逻辑一致性：该段落是否与文档其余部分在逻辑上保持一致？是否存在不合逻辑或突兀的过渡？\n"
                f"2. 完整性：该段落是否提供了足够的信息来支持其主要观点？是否有重要的缺失细节？\n"
                f"3. 连贯性：该段落与周围段落之间是否有平滑的连接？\n"
                f"请提供具体的改进建议。\n"
                f"专注于为第{idx + 1}段提供详细的改进建议，包括提升逻辑流程、完整性和整体连贯性的方法。只提供修改建议和可能的修改方法，而不是重写的段落。"
            )

            review_feedback = get_response(prompt)
            Task_Chain_of_thought.append({
                'agent': 'CheckLoopAgent',
                'token': 'Reflective',
                'content':review_feedback
            })

            # Step 2: Modify the paragraph based on feedback using another agent
            # if "pass" not in review_feedback.lower():
            modification_prompt = (
                f"作为一位细致的文本编辑，您的任务是根据以下反馈提供段落的修订版本：\n{review_feedback}\n"
                f"原始段落：\n{updated_document[idx]}\n"
                "确保修改遵循反馈中的具体建议，改善段落的逻辑流程、叙事质量和连贯性。仅提供修改后的段落,生成的段落内容用$$包裹，例如: $$内容$$。请保证字数和之前几乎相同，不要过多延长。"
            )
            revised_paragraph = get_response(modification_prompt)
            revised_paragraph = extract_content(revised_paragraph)
            Task_Chain_of_thought.append({
                'agent': 'refine_LoopAgent',
                'token': 'Refine',
                'content':revised_paragraph
            })
           
            # Step 3: Replace the original paragraph with the revised version
            updated_document[idx] = revised_paragraph


        return updated_document,Task_Chain_of_thought


# Document Organization Agent
class DocumentOrganizationAgent:
    def organize_document(self, current_document, new_paragraph):
        # logging.info("使用模型组织完整的完整的文章")
        # prompt = (
        #     f"###新段落:\n{new_paragraph} 请从上述模型输出中直接提取"
        #     "请直接返回更新后的文章结果:"
        # )
        current_document.append(new_paragraph)
        return current_document

# Main Agent


# In[ ]:


class MainAgent:
    def __init__(self):
        self.initialization_agent = InitializationAgent()
        self.paragraph_extraction_agent = ParagraphExtractionAgent()
        self.paragraph_agent = ParagraphAgent()
        # self.check_agent = CheckAgent()
        # self.feedback_agent = FeedbackLoopAgent()
        self.review_agent = ComprehensiveReviewAgent()
        self.organization_agent = DocumentOrganizationAgent()
        # self.decision_agent = DecisionAgent()
        self.document = ""

    def run(self, topic):
        # Step 1: Generate and refine outline
        Task_Chain_of_thought = []
        current_document= []

        ### think and outline design
        task_define_result,outline,Task_Chain_of_thought= self.initialization_agent.generate_outline(topic,Task_Chain_of_thought)
        #print('outline:',outline)
        # Step 2: Extract title and key points for each paragraph
        title, key_points = self.paragraph_extraction_agent.extract_key_points(outline)
        #print('key_points:',key_points)
        outline = task_define_result + outline

        ### write paragraph one by one
        for idx,key_point in enumerate(key_points):
            if key_point.strip():
                previous_paragraphs = self.document
                paragraph,Task_Chain_of_thought= self.paragraph_agent.generate_paragraph(outline, key_point, previous_paragraphs,Task_Chain_of_thought)

                current_document.append(paragraph)
                self.document = "\n".join(current_document) 
       
        ### review_paragraph one by one
        current_document,Task_Chain_of_thought= self.review_agent.review_document(current_document,Task_Chain_of_thought)
        self.document = f"Title: {title}\n\n"
        self.document += "\n".join(current_document) 
# Calculate word count for the entire document
        word_count = len(self.document)
        if word_count < 400:
            self.document = "Wrong! The word count is too low. Please try again."
        # Calculate word count for "content" in Task_Chain_of_thought
        task_chain_word_count = sum(len(task.get("content", "").split()) for task in Task_Chain_of_thought)

        # 构建输出数据，包括字数统计
        output_data = {
            "query": topic,
            "title": title,
            "outline": outline,
            "final_document": self.document,
            "Task_Chain_of_thought": Task_Chain_of_thought,
            "word_count": word_count,  # 添加字数统计结果
            "task_chain_word_count": task_chain_word_count  # 添加 Task_Chain_of_thought 中 "content" 的字数统计结果
        }
        return output_data
def save_result(result, output_file):
    with lock:
        try:
            with open(output_file, 'r+', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
                result_id = result["id"]
                data[result_id] = result
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.truncate()
                logging.info(f"Generated document with ID '{result_id}' has been saved to '{output_file}'")
        except FileNotFoundError:
            with open(output_file, 'w', encoding='utf-8') as f:
                data = {result["id"]: result}
                json.dump(data, f, ensure_ascii=False, indent=4)
                logging.info(f"Generated document with ID '{result_id}' has been saved to '{output_file}'")

def run_agent_in_parallel(prompts, output_file='/mnt/yuhao/SuperWrite/Agent/generated_documents_zh_final.json'):
    agents = [MainAgent() for _ in prompts]

    with ThreadPoolExecutor(max_workers=48) as executor:
        futures = {executor.submit(agent.run, prompt): prompt for agent, prompt in zip(agents, prompts)}
        for future in as_completed(futures):
            prompt = futures[future]
            try:
                result = future.result()
                result_id = str(uuid.uuid4())  # Assign a unique ID to each result
                result["id"] = result_id
                save_result(result, output_file)
            except Exception as e:
                logging.error(f"An error occurred for prompt '{prompt}': {e}")

if __name__ == "__main__":

    
    prompts = []
    file_path = ""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():  # 确保行不为空
                try:
                    data = json.loads(line)
                    original_query = data.get("query", "")
                    if original_query:  # 确保query不为空
                        prompts.append(original_query)
                except json.JSONDecodeError as e:
                    logging.error(f"无法解析JSON行: {line}. 错误: {e}")
    #prompts = prompts[256:]
    run_agent_in_parallel(prompts)