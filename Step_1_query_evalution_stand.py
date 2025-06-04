evaluation_criteria =  f"""
Evaluation Criteria

## 1. General Criteria (Applicable to All Genres)

### 1.1 Relevance
- **Definition**: How well the content matches the user’s request, and whether it addresses the intended purpose or topic.
- **Standards**:
  - **10**: Fully aligned with the user’s needs, highly relevant to the request.
  - **7-9**: Mostly relevant, with some minor deviations or less-than-perfect alignment.
  - **4-6**: Partially relevant, with the majority of the content not matching the user’s request.
  - **1-3**: Completely irrelevant, fails to meet the user’s needs.


### 1.2 Coherence
- **Definition**: The clarity of the structure, and the logical flow of ideas and transitions between paragraphs and sentences.
- **Standards**:
  - **10**: Clear structure, strong logical progression, and smooth flow of content with natural transitions.
  - **7-9**: Mostly coherent, with minor lapses or jumps in logic.
  - **4-6**: Structure is somewhat unclear, and there are noticeable gaps or jumps in logic.
  - **1-3**: Disorganized and confusing, with no clear structure or logical connections.

### 1.3 Clarity
- **Definition**: How clear and easy the content is to understand, and whether it includes sufficient detail.
- **Standards**:
  - **10**: Clear expression, rich in detail, and easy to understand.
  - **7-9**: Mostly clear, but may have some lengthy or unclear parts.
  - **4-6**: Expression is somewhat muddled, lacks detail, and is difficult to understand.
  - **1-3**: Extremely vague, minimal information, and difficult to comprehend.

## 2. Special Criteria (Applicable to Specific Genres)

### 2.1 Creativity and Uniqueness
- **Definition**: Whether the content is innovative, offering new perspectives, or showcasing original expression.
- **Standards**:
  - **10**: Highly creative and unique, presenting entirely new or unconventional ideas or perspectives.
  - **7-9**: Creative, but some parts are more conventional or lack originality.
  - **4-6**: Limited creativity, mostly traditional content with little innovation.
  - **1-3**: Lacks creativity, offering conventional or uninspired content.

### 2.2 Depth of Argumentation
- **Definition**: How deeply and comprehensively the content explores the topic, providing strong arguments and supporting evidence.
- **Standards**:
  - **10**: Thorough and deep exploration of the topic with ample supporting evidence and data.
  - **7-9**: Solid argumentation, but some aspects may be underdeveloped or lacking in evidence.
  - **4-6**: Basic analysis with weak or insufficient evidence, lacking in depth.
  - **1-3**: Shallow argumentation, no clear analysis or supporting evidence.

### 2.3 Emotional Conveyance
- **Definition**: Whether the content conveys emotion, attitude, or mood effectively and resonates emotionally with the reader.
- **Standards**:
  - **10**: Rich and profound emotional conveyance, evoking strong emotional resonance from the reader.
  - **7-9**: Adequate emotional conveyance, able to stir some emotion but may seem slightly flat.
  - **4-6**: Weak emotional impact, difficult for the reader to connect emotionally, with little emotional depth.
  - **1-3**: Lacks emotional depth, failing to evoke any emotional response from the reader.

### 2.4 Readability and Engagement
- **Definition**: Whether the content is engaging, easy to read, and can maintain the reader's interest.
- **Standards**:
  - **10**: Highly engaging, vivid, and expressive, maintaining the reader’s attention throughout.
  - **7-9**: Mostly engaging, though some parts may feel a bit repetitive or less interesting.
  - **4-6**: Somewhat dry, lacking engagement, and may cause the reader to lose interest.
  - **1-3**: Boring, unengaging, and fails to hold the reader’s attention.

### 2.5 Interactivity (For Genres that Emphasize Interaction)
- **Definition**: Whether the content prompts reader interaction, such as comments, shares, or discussions, especially relevant for social media, advertising, or interactive content.
- **Standards**:
  - **10**: Highly interactive, generating significant user participation and discussion.
  - **7-9**: Somewhat interactive, able to prompt some reader engagement, but not on a large scale.
  - **4-6**: Minimal interaction, with limited reader participation.
  - **1-3**: No interaction, fails to encourage engagement from readers.

### 2.6 Contextual Appropriateness
- **Definition**: How well the content aligns with the intended context, background, and target audience, making sure it fits the context in which it is used.
- **Standards**:
  - **10**: Perfectly suited to the context, accurately conveys the intended message and meets the needs of the target audience.
  - **7-9**: Generally appropriate for the context, but minor deviations or slight mismatches may exist.
  - **4-6**: Somewhat off-target, not entirely fitting for the intended audience or situation.
  - **1-3**: Completely misaligned with the context, failing to meet audience or situational needs.
"""


import time, re, openai, requests
from transformers import AutoTokenizer
import json


def get_response(query, url="http://172.18.201.139:9999/v1/chat/completions", model="default", api_key="None"):
    """
    Query the LLM API and return the response.
    """
    messages = [{"role": "user", "content": query}]
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 8192,
        "stop": ["<|user|>", "<|endoftext|>"]
    }
    
    for attempt in range(3):
        try:
            response = requests.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=1800
            )
            resp_json = response.json()
            content = resp_json['choices'][0]['message']['content'].strip()
            # Remove thinking section if present
            content = content.split("</think>")[-1].strip()
            return content
        except Exception as e:
            print(f"Attempt {attempt+1}/3 failed: {e}")
            # time.sleep(2 ** attempt)
    
    print("Failed to get a response after 3 attempts")
    return ""



format_eval  = f"""
The final output should be in JSON format, structured as follows: ```json
{{
    "Criterion 1": {{
        "Analysis": "Analysis content",
        "Score": X
    }},
    "Criterion 2": {{
        "Analysis": "Analysis content",
        "Score": X
    }},
    ...
}}
"""

format_query  = f"""
After think give final answer in JSON format. structured as follows: ```json
{{
    "Selected Criterion 1": {{
        "Definition": "Criterion definition",
        "Standards": "Scoring standards for the query, give a simple rubric from 1 to 10, 10: ..., 7-9: ..., 4-6: ..., 1-3: ...",
    }},
    "Selected Criterion 2": {{
        "Definition": "Criterion definition",
        "Standards": "...",
    }},
    ...

}}
"""

# prompt = f"""
# Please refer to the evaluation criteria outlined below:

# {evaluation_criteria}

# ## Task:

# You are tasked with evaluating the query `{query}`. From the "Special Criteria" section, select 3 relevant criteria, and from the "General Criteria" section, select all criteria (Relevance, Coherence, Clarity) , for a total of 6 criteria. 

# Be sure to:

# 1. Think step-by-step about why each criterion is relevant to the query.
# 2. Think step-by-step through the query and how each criterion applies.
# 3. Provide a brief analysis for each selected criterion on how it applies to the query.
# 4. Integrate the above reasoning into the Definition and Standards sections of each criterion.

# {format_query}
# """

import json
import pandas as pd
import requests
import time
import os
import traceback
from openai import OpenAI
import concurrent.futures
import tiktoken
from transformers import AutoTokenizer
import re


import os
import json

def get_queries_from_json_files(folder_path):
    queries = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(folder_path, filename)
            with open(file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                except:
                    print(f'Error loading JSON file: {file_path}')
                    continue
                # if 'query' in data and ('evaluate_standard' not in data or data['evaluate_standard'] is None):
                #     queries.append((file_path, data['query']))
                if 'query' in data :
                    queries.append((file_path, data['query']))
    return queries

def get_json(text):
    json_pattern = r'```json\n({.*})\n```' 
    json_match = re.search(json_pattern, text, re.DOTALL)
    if json_match:
        json_data = json_match.group(1)  # 提取 JSON 数据部分
        parsed_json = json.loads(json_data)
        return parsed_json
    return None

# 获取所有JSON文件中的query部分

queries = get_queries_from_json_files(folder_path)
print(f'Found {len(queries)} queries to process.')


def process_query(file_path, query):
    prompt = f"""
    Please refer to the evaluation criteria outlined below:

    {evaluation_criteria}

    ## Task:

    You are tasked with evaluating the query: `{query}`. From the "Special Criteria" section, select 3 relevant criteria, and from the "General Criteria" section, select all criteria (Relevance, Coherence, Clarity) , for a total of 6 criteria. 

    Be sure to:
    1. Think step-by-step about why each criterion is relevant to the query.
    2. Think step-by-step through the query and how each criterion applies.
    3. Provide a brief analysis for each selected criterion on how it applies to the query.
    4. Integrate the above reasoning into the Definition and Standards sections of each criterion.

    {format_query}
    """
    # print(prompt)
    # 获取响应
    # print(len(prompt))
    answer= get_response(prompt)
    # print("+"*10)
    # print(answer)
    # 获取 JSON 数据
    parsed_json = get_json(answer)

    
    if parsed_json:
        # 读取原始 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 添加 evaluate_standard 部分
        data['evaluate_standard'] = parsed_json
        # print("done")
        
        # 保存回原 JSON 文件
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

# 使用多线程并行处理每个query
with concurrent.futures.ThreadPoolExecutor(max_workers=512) as executor:
    futures = [executor.submit(process_query, file_path, query) for file_path, query in queries]
    concurrent.futures.wait(futures)
