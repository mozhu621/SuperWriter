#!/usr/bin/env python
# coding: utf-8

# In[5]:


think_template = """
1. Define the Purpose and Type of Writing
   - Purpose: Clearly establish the objective of the piece (e.g., to inform, persuade, or inspire), setting the tone and direction accordingly.
   - Type: Choose an appropriate writing style (e.g., argumentative, expository, or business writing) that aligns with the intended format and structure. Clearly identify the genre and describe its stylistic characteristics.

2. Plan Content and Structure
   - Key Points: Outline the essential information to ensure a clear and focused topic.
   - Structure: Develop a coherent framework that maintains a logical flow throughout the piece.

3. Characters and Plot (for Narrative Writing)
   - Character Development: Define the traits and motivations of all characters. Provide detailed descriptions, including specifics such as names, gender, and relationships.
   - Plot Development: Establish pivotal plot points and emotional cues to drive the narrative. Offer a detailed explanation based on the chosen structure.

4. Additional Guidelines
   - Formatting Requirements: Automatically select an appropriate output format (e.g., Markdown, bullet points) based on content and presentation needs to enhance visual clarity and appeal.
   - Other Key Elements: Include any genre- or task-specific components. For instance, in summaries, a step-by-step approach is sufficient due to their simpler logic.
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
model_path = 'gpt-4o-2024-08-16'
api_key=''

def extract_info(pattern, text):
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1)
    else:
        return None


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


# 基于请求函数的 Agent 框架
class ChatAgent:
    def __init__(self):
        self.session_history = []  # 用于存储会话历史
        self.active = True         # 标志 Agent 是否在运行

    def start(self):
        logging.info("Agent 已启动，输入 'exit' 以退出对话")
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
        logging.info("Agent 即将停止...")
        self.active = False
        time.sleep(1)  # 停止前的短暂等待，方便用户看到提示
        logging.info("Agent 已停止")

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
            f"Thoroughly understand the task design of {task_define_result}."
            " Based on the task design, determine a suitable article title and generate a detailed, structured outline."
            " The outline should not exceed 10 paragraphs, and each paragraph must include a detailed description along with a specific word count."
            " The total word count should be appropriate for the task but must not exceed 8,000 words."
            " Allocate the total word count to each paragraph according to the complexity of the task."
            " Then, provide the full outline along with the word count for each paragraph."
            f" Ensure that each paragraph description includes the expected content, maintains clear logic, and aligns with the user's objective: {topic}."
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
        logging.info("检查大纲")
        prompt = (
            f"You are a reviewer. Your task is to evaluate the following outline and assess whether its logical structure is complete and aligned with the intended objectives.###\n"
            f"### Task Design:\n{task_define_result}### Outline:\n{self.outline}\n"
            "Please provide detailed feedback, pointing out any logical gaps or missing elements."
        )


      
        return get_response(prompt)

    def refine_outline(self, check_output):
        logging.info("根据检查结果修改大纲")
        prompt = (
            f"You are a professional outline editor. Based on the following feedback, revise the outline to ensure it includes all necessary components:\n"
            f"### Feedback: {check_output}\n### Current Outline: {self.outline}. "
            "Please provide the revised article title and the updated outline content:"
        )

        self.outline = get_response(prompt)
        #print(self.outline)

    
    def task_define_agent(self,topic, Task_Chain_of_thought):
        logging.info("确定大纲任务")
        prompt = (
        f"You are a professional writer responsible for creating an initial design based on the thinking template below."
        f" Please use the template to thoroughly analyze and develop a detailed preliminary plan for the task '{topic}'."
        f" Carefully examine each point in the template to ensure all aspects are fully considered, providing a comprehensive and complete writing plan with no vague information."
        f" At the same time, make sure the structure remains manageable and not overly complex."
        f" Thinking Template: {think_template}. At this stage, you do not need to provide an outline—just complete the in-depth thinking required for task design. Please respond:"
    )


        task_define_result = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'InitializationAgent_task_define',
            'token': 'Main_Outline_think',
            'content': task_define_result
        })
        return task_define_result,Task_Chain_of_thought

    def questioner_agent(self,topic, task_output, Task_Chain_of_thought):
        logging.info("提问者检查任务并给出反馈")
        prompt = (
            f"You are a critical reviewer, specializing in identifying issues and flaws in task design."
            f" Please evaluate the following task design and raise at least two questions to ensure it meets the requirements of '{topic}'."
            f" These questions should be carefully considered and clarified before the actual writing begins, highlighting any logical flaws, ambiguities, or areas that might confuse the reader."
            f" Depending on the type of task, you will analyze it from various angles—for example, whether a speech is engaging, a story is original, or an academic paper is rigorous."
            f" Task Topic: {topic}. Task Design: {task_output}."
            f" Provide detailed questions along with specific and practical suggestions for improving the task design:"
        )


        feedback_result = get_response(prompt)
        Task_Chain_of_thought.append({
            'agent': 'QuestionerAgent_feedback',
            'token': 'Reflective',
            'content': feedback_result
        })
        return feedback_result, Task_Chain_of_thought

    def revision_agent(self,task_output, feedback, Task_Chain_of_thought):
        logging.info("根据提问者的反馈修改任务")
        prompt = (
            f"You are an experienced editor responsible for revising the task based on the reviewer’s feedback."
            
            f"Original Task Design: {task_output}. Feedback: {feedback}. Using this feedback, provide a detailed and specific revision of the current task design. "
            f"Apply your own judgment rather than simply implementing the feedback verbatim to address all identified issues. If necessary, rewrite the original task design entirely. "
            f"Please provide the revised task design:"
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
            logging.info(f"\n\nIteration {i + 1} of task refinement")
            
            # Step 2: Questioner provides feedback
            feedback,Task_Chain_of_thought = self.questioner_agent(topic, task_output, Task_Chain_of_thought)
            #print(feedback)
            # Step 3: Revision Agent modifies the task output
            revised_task_output,Task_Chain_of_thought = self.revision_agent(task_output, feedback, Task_Chain_of_thought)
            #print(revised_task_output)
            # Update task_output for next iteration
            task_output = revised_task_output

        return task_output, Task_Chain_of_thought
        

# Paragraph Extraction Agent
class ParagraphExtractionAgent:
    def extract_key_points(self, outline):
        logging.info("提取大纲中的段落描述和标题")
        prompt = (
            f"""
            Extract the article title and the description and word count requirement for each paragraph from the following outline:
            {outline}
            Please ensure the returned content is formatted as follows in JSON format:
            {{
                "title": "[Title]",
                "paragraphs": [
                    {{"content": "[Description for Paragraph 1]", "word_count": 200}},
                    {{"content": "[Description for Paragraph 2]", "word_count": 250}},
                    ...
                ]
            }}
            """
        )
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
        
        # print(response)
        title = response_json.get("title", "")
        paragraphs = response_json.get("paragraphs", [])
        key_points = [
            f"paragraph_{i+1}: {paragraph.get('content', '')}, {paragraph.get('word_count', 0)} words"
            for i, paragraph in enumerate(paragraphs)
        ]
        
        return title, key_points


def extract_content(text):
    match = re.search(r'\$\$(.*?)\$\$', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None

class ParagraphAgent:
    def generate_paragraph(self, outline, key_point, previous_paragraphs, Task_Chain_of_thought):
        # Step 1: Thought Generation (思考阶段)
        logging.info(f"生成段落:")
        thought_prompt = (
            f"You are a writing expert skilled in thoughtful planning before generating each paragraph.### Outline: {outline}\n### Previous Paragraphs: {previous_paragraphs}\n### Key Point for the Current Paragraph: {key_point}\n"
            "Please carefully develop a writing plan for the new paragraph. You may consider the following aspects:\n"
            "1. Purpose: What is the main objective of this paragraph? What message or emotion should it convey?\n"
            "2. Structure: How should the content of this paragraph be organized? What logical sequence would best ensure clarity and coherence, and how will it connect tightly with the previous content?\n"
            "3. Transitions: How will this paragraph naturally link to the one before it? Are there specific transition sentences or bridging techniques that can be used?\n"
            "4. Details and Examples: What details, facts, or examples are needed to support the main idea? How should these be arranged for maximum impact?\n"
            "5. Language Style and Techniques: What kind of language style should be used to achieve the goal? Are there rhetorical devices (such as metaphors or analogies) that could enhance the paragraph’s impact—while still being clear, readable, and easy to understand for the audience?\n"
            "6. Markdown Format: Use Markdown to structure the output neatly, including headings, bullet points, or bold text to improve readability.\n"
            "Based on the outline and the key point for this paragraph, construct a detailed writing plan. Add any other relevant considerations as needed, and keep the word count requirements in mind. Only the thought process behind the paragraph is needed, not the paragraph itself."
        )


        thought_response = get_response(thought_prompt)
        # print('Thought Process:', thought_response)

        # Append thought process to the Task_Chain_of_thought
        Task_Chain_of_thought.append({
            'agent': 'ParagraphAgent',
            'token': 'Paragraph_focus_think',
            'content': thought_response
        })

        # Step 2: Paragraph Generation (写作阶段)
        writing_prompt = (
            f"You are an exceptional writing expert, skilled at completing writing tasks in a clear, accessible, and logically sound manner.### Outline: {outline}\n### Previous Paragraphs: {previous_paragraphs}\n### Key Point for the New Paragraph: {key_point}\n"
            f"### Thought Process: {thought_response}\n"
            "Based on the thought process above and the existing paragraphs, write the next paragraph, ensuring it meets the word count requirement. Only provide the full content of the new paragraph. Enclose the paragraph content with $$ $$, like: $$content$$. "
        )


        paragraph_response = get_response(writing_prompt)
        # print('Paragraph Generation:', paragraph_response)
        paragraph_response = extract_content(paragraph_response)
        # print("done"*20)
        # print(paragraph_response)

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
        logging.info(f"检查段落: {paragraph_id}")
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
        logging.info("决策代理正在分析检查结果")
        return "pass" if "pass" in check_result.lower() else "rewrite"

# Feedback Loop Agent
class FeedbackLoopAgent:
    def feedback_loop(self, paragraph_id, paragraph, check_output, previous_paragraphs,Task_Chain_of_thought):
        logging.info(f"分析反馈: {paragraph_id}")
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
        logging.info("进行逐段审查并修改")
        updated_document = current_document.copy()

        for idx in range(len(current_document)):
            # Step 1: Combine current document into a complete text with paragraph labels
            combined_document = "\n".join([f"段落 {i+1}: {para}" for i, para in enumerate(updated_document)])
            prompt = (
            f"As a meticulous document reviewer, your task is to carefully read the entire document, understand its overall structure and logic, and then conduct a detailed review of paragraph {idx + 1}, providing revision suggestions:\n{combined_document}\n"
            f"When reviewing paragraph {idx + 1}, you may refer to the following points:\n"
            f"1. Logical Consistency: Is this paragraph logically consistent with the rest of the document? Are there any illogical transitions or abrupt shifts?\n"
            f"2. Completeness: Does this paragraph provide enough information to support its main idea? Are there any important missing details?\n"
            f"3. Coherence: Does this paragraph connect smoothly with the surrounding paragraphs? Would transitional sentences help improve the flow?\n"
            f"Please provide at least two specific improvement suggestions.\n"
            f"Focus on offering detailed revision suggestions for paragraph {idx + 1}. Only provide suggestions and possible ways to improve—do not rewrite the paragraph itself. Suggestions for improvement:"
        )


            review_feedback = get_response(prompt)
            Task_Chain_of_thought.append({
                'agent': 'CheckLoopAgent',
                'token': 'Reflective',
                'content':review_feedback
            })

            # Step 2: Modify the paragraph based on feedback using another agent
        
            modification_prompt = (
                f"As a text editor, your task is to revise the paragraph based on the following feedback:\n{review_feedback}\n"
                f"Original Paragraph:\n{updated_document[idx]}\n"
                "Ensure the revision strictly follows the specific suggestions in the feedback. Only provide the revised paragraph. Enclose the paragraph content with $$, like: $$content$$ Revised Paragraph:"
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
        word_count = len(self.document.split())

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

def run_agent_in_parallel(prompts, output_file='generated_documents_en_final.json'):
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
    
    run_agent_in_parallel(prompts)
