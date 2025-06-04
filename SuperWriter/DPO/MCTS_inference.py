#!/usr/bin/env python
# coding: utf-8

# # 读取数据，并创建jsonl的文件夹

# In[1]:


import os
import json


# # Define the input file path and output directory
# input_file_path = '/mnt/yuhao/LongWriter/Data_pre/Query_data/filtered_inference_results_step_2.jsonl'
# output_dir = 'MCTS_result_test'

# # Create the output directory if it doesn't exist
# os.makedirs(output_dir, exist_ok=True)

# # Read the lines of the JSONL file starting from the 100th line and process each line
# with open(input_file_path, 'r') as infile:
#     for i, line in enumerate(infile):
#         # if i < 99:
#         #     continue
#         if i >= 32:  # Read only 10 lines starting from the 100th line
#             break
#         data = json.loads(line)
#         query_content = data.get('query', '')

#         # Define the output file path
#         output_file_path = os.path.join(output_dir, f'query_{i+1}.json')

#         # Save the query content as a JSON file
#         with open(output_file_path, 'w') as outfile:
#             json.dump({'query': query_content}, outfile, ensure_ascii=False, indent=4)


# #  启动 服务器

# In[2]:


import json
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import time
import os
import traceback
import concurrent.futures
import tiktoken
from transformers import AutoTokenizer
import multiprocessing
from multiprocessing import Lock
import requests
import re
def better_len(text):
    """
    统计字符串的“字数”：对于中文，按每个汉字计数；
    对于英文，按单词计数（英文单词由字母、数字、下划线构成）。
    """
    # 匹配所有中文汉字（Unicode 范围：\u4e00 到 \u9fff）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    
    # 去掉所有中文字符后，再匹配英文单词
    text_no_chinese = re.sub(r'[\u4e00-\u9fff]', '', text)
    english_words = re.findall(r'\b\w+\b', text_no_chinese)
    
    return len(chinese_chars) + len(english_words)

# client = OpenAI(
#     base_url="http://172.18.197.124:8000/v1",
#     api_key='token-abc123'
# )
import random
# 定义查询 LLM 的函数

def query_llm(query, url="XXXX", model="default", api_key="None"):
    """
    Query the LLM API and return the response.
    """
    messages = [{"role": "user", "content": query}]
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 32768,
        "stop": ["<|user|>", "<|endoftext|>", "#*# finish."]
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
            #content = content.split("</think>")[-1].strip()
            return content
        except Exception as e:
            print(f"Attempt {attempt+1}/3 failed: {e}")
            
    
    print("Failed to get a response after 3 attempts")
    return ""


# In[ ]:





# In[3]:


def extract_sections(text, start_marker="<answer>", end_marker="</answer>"):
    sections = []
    start_idx = 0
    while True:
        start_idx = text.find(start_marker, start_idx)
        if start_idx == -1:
            break
        start_idx += len(start_marker)
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
            break
        sections.append(text[start_idx:end_idx].strip())
        start_idx = end_idx + len(end_marker)
    return sections
    # Example usage
   


# In[4]:


def extract_sections_think(text, start_marker="<think>", end_marker="</think>"):
    sections = []
    start_idx = 0
    while True:
        start_idx = text.find(start_marker, start_idx)
        if start_idx == -1:
            break
        start_idx += len(start_marker)
        end_idx = text.find(end_marker, start_idx)
        if end_idx == -1:
            break
        sections.append(text[start_idx:end_idx].strip())
        start_idx = end_idx + len(end_marker)
    return sections
    # Example usage


# In[ ]:


import logging
import time
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s',filename='MCTS_inference_3.log', filemode='w')

def log_time_taken(stage_name, start_time):
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.warning(f"{stage_name} took {elapsed_time:.2f} seconds")


log_time_taken("Start!!!", time.time())


# In[5]:


#Think_tamplate = """First thinks about the thought process in the mind and then provides the user with the answer. The thought process and answer are enclosed within <think> </think> and <answer> </answer> tags, respectively, i.e., <think> thought process here </think> <answer> answer here </answer> \n"""# Process each element in the JSON data
Think_tamplate = ""
def generate_prompt(stage, use_query=None, previous_output=None, final_outline=None):
    if stage == "plan":
        return (
            f"Superwrite-Stage-1: \n### User query: *** {use_query} ***. \n"
            f"Based on the user query, please develop a detailed brainstorm and outline specifically addressing the task. "
            f"The response should include the objective, target audience, key points, and structure in a clear and thorough manner. \n"
            f"### Superwrite Answer:"
        )
    elif stage == "write":
        final_think = extract_sections(previous_output)
        write_query_draft = "\n### Outline:".join(final_think)
        write_query = (
            "Based on the Stage-1 Plan, carefully think through each section of the outline, "
            "then generate the content for each paragraph one by one. \n### Superwrite Answer:"
        )
        return (
            f"Superwrite-Stage-2: \n### Stage-1 Plan: *** {write_query_draft} *** \n"
            f"### Task: {write_query}"
        )
    elif stage == "refine":
        final_result = extract_sections(previous_output)
        check_query_draft = "\n".join(final_result)
        refine_query = (
            "Based Stage-2 Write generated content, review and refine each paragraph individually. "
            "Improve clarity, coherence, and consistency, fix errors, and ensure smooth transitions between sections. "
            "After refining all paragraphs, compile the final polished version. \n### Superwrite Answer:"
        )
        return (
            # f"{Think_tamplate} Superwrite-Stage-3: \n### Stage-1 Plan: {final_outline} \n"
            f"Superwrite-Stage-3: "
            f"### Stage-2 Write generated content: *** {check_query_draft} *** \n"
            f"### Task: {refine_query}"
        )
    elif stage == "final":
        final_result = extract_sections(previous_output)
        check_query_draft = "\n".join(final_result)
        return (
            f"Final answer: {check_query_draft}"
        )


# In[1]:




# In[ ]:





# # Stage 1 Plan

# In[ ]:


import os
import json
from tqdm import tqdm
import concurrent.futures

# Define the directory containing the JSON files
# json_dir = '/mnt/yuhao/LongWriter/Data_pre/DPO_data/Final_DPO_query/Final_version_1'
json_dir = '/mnt/yuhao/SuperWrite/Data/DPO-data/Final_version_inference_qwen'

# Function to read and process a single JSON file
def process_json_file(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        use_query = data.get('query', '')
        # print(f"Processing query: {use_query}")
        prompt = generate_prompt("plan", use_query)
        
        responses = []
        word_count = []
        Stage_2_input = []
        flag = 0
        # flag set 5 stage need at least 5 result
        num  = 0 
        while flag < 5 and num < 10:
            # print(f"falg: {flag}")
            # print(f"num:  {num}")
            
            response = query_llm(prompt)
            #print(f"Response: {response}")
            #logging.warning(f"Response: {response} ")
            word_count = better_len(response)
            #print(f"Word Count: {word_count}")
            num += 1
            if 500 < word_count < 22000:
                #print(f"Response: {response}")
                #logging.warning(f"Response: {response} ")
                extract_response = generate_prompt("write", use_query ,response)
                #print(f"extract_response: {extract_response}")
                # print(len(extract_sections(response)))
                if len(extract_sections(response)) == 2 and (len(extract_sections_think(response)) == 2 or len(extract_sections_think(response)) == 1):
                    flag += 1
                    #print(f"success, flag: {flag}")
                    Stage_2_input.append({'responese': extract_response,  'stage_1': flag})
                    responses.append({'response': response, 'word_count': word_count,'flag': "finish", 'stage_1': flag})
                else:
                    responses.append({'response': response, 'word_count': word_count,'flag': "think_bad"})
            else:
                responses.append({'response': response, 'word_count': word_count,'flag': f"word_bad Word Count: {word_count}"})
            #print(f"Response: {response}\nWord Count: {word_count}")
        data['Stage_1_stat'] = {"flag": flag, "num": num, "Finish_rate": flag/num}
        data['Stage_1_input'] = generate_prompt("plan", use_query)
        # Add the responses to the original data
        data['Stage_1_output'] = responses
        data['Stage_2_input'] = Stage_2_input
        # Save the updated data back to the original JSON file
        logging.warning(f"{f} stage1—done")

        with open(file_path, 'w') as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)

# Get a list of all JSON files in the directory
json_files = [os.path.join(json_dir, file) for file in os.listdir(json_dir) if file.endswith('.json')]
# json_files = json_files[:32]
# Process the JSON files in parallel with 8 threads
# Process the JSON files in parallel with 8 threads and show progress bar
start_time = time.time()

with concurrent.futures.ThreadPoolExecutor(max_workers=512) as executor:
    list(tqdm(executor.map(process_json_file, json_files), total=len(json_files)))

log_time_taken("Stage_1", start_time)


# # stage 2

# In[ ]:



# Function to read and process a single JSON file
def process_Stage_2(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
     
        query = data.get('Stage_2_input', '')
        #print(f"Processing query: {query }")
        #print(query[1]['responese'])
        responses = []
        word_count = []
        Stage_3_input = []
        flag_all = 0
        num_all = 0
        # print(len(query))
        # print(len(query))
        for i in range(len(query)):
            use_query = query[i]['responese']
           
            # print("=="*20)
            Node_1 = query[i]['stage_1']
          
            flag = 0
            num = 0
            # flag set 4 stage_2 need at least 4 result
            while flag < 4 and num < 8:
                # print("flag",flag)
                # print("num",num)
                response = query_llm(use_query)
                #print(f"Response: {response}")
                num += 1
                #print(f"Response: {response}")
                word_count = better_len(response)
                # print(f"Word Count: {word_count}")
                if 1000 < word_count < 22000:
                    # print(f"Word Count: {word_count}")
                    #print(f"Response: {response}")

                    extract_response = generate_prompt("refine",use_query,response)
                    #print(f"extract_response: {extract_response}")
                    length = len(extract_sections(response))
                    length_think = len(extract_sections_think(response))
                    # print(f"length: {length}")
                    # print(f"length_think: {length_think}")
                    if length > 3 and length <= 12 and length_think > 3 and length_think <= 12 and (length == length_think ): 
                        flag += 1
                        # print(f"success, flag: {flag}")
                        Stage_3_input.append({'responese': extract_response, 'stage_1': Node_1, 'stage_2': flag})
                        responses.append({'response': response, 'word_count': word_count,'flag': "finish",'stage_1': Node_1, 'stage_2': flag})
                    else:
                        responses.append({'response': response, 'word_count': word_count,'flag': "think_format_bad",'stage_1': Node_1, })
                else:
                    responses.append({'response': response, 'word_count': word_count,'flag': "Word_bad",'stage_1': Node_1})
        # Add the responses to the original data
            flag_all += flag
            num_all += num
        # print(f"flag_all: {flag_all}, num_all: {num_all}")
        data['Stage_2_stat'] = {"flag": flag_all, "num": num_all, "Finish_rate": flag_all/num_all}
        
        data['Stage_2_output'] = responses
        data['Stage_3_input'] = Stage_3_input
        # Save the updated data back to the original JSON file
        logging.warning(f"{f} stage2—done")
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)
        #print(f"Finish: {file_path}")

# Get a list of all JSON files in the directory
json_files = [os.path.join(json_dir, file) for file in os.listdir(json_dir) if file.endswith('.json')]
# json_files = json_files[:1]
# Process the JSON files in parallel with 8 threads

# with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
#     list(tqdm( executor.map(process_Stage_2, json_files), total=len(json_files)))

start_time = time.time()
with concurrent.futures.ThreadPoolExecutor(max_workers=512) as executor:
    executor.map(process_Stage_2, json_files)


log_time_taken("Stage_2", start_time)


# # stage 3 refine

# In[25]:



# Function to read and process a single JSON file
def process_Stage_3(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        query = data.get('Stage_3_input', '')
        responses = []
        word_count = []
        final_answer = []
        flag_all = 0
        num_all = 0
        for i in range(len(query)):
            use_query = query[i]['responese']

            
            Node_1 = query[i]['stage_1']
            Node_2 = query[i]['stage_2']
            flag = 0
            num = 0
            # flag set 4 stage_2 need at least 4 result
            while flag < 2 and num < 6:
                response = query_llm(use_query)
                
                num += 1
                word_count = better_len(response)
                
                # print(f"Word Count: {word_count}")
                if 1000 < word_count < 22000:
                    # print(f"Word Count: {word_count}")
                    extract_response = generate_prompt("final",use_query,response)
                    length = len(extract_sections(response))
                    length_think = len(extract_sections_think(response))
                    if length > 3 and length <= 12 and length_think > 3 and length_think <= 12 and (length == length_think ):
                        flag += 1
                        # print(f"success, flag: {flag}")
                        final_answer.append({'responese': extract_response, 'stage_1': Node_1, 'stage_2': Node_2, 'stage_3': flag})
                        responses.append({'response': response, 'word_count': word_count,'flag': "finish",'stage_1': Node_1, 'stage_2': Node_2, 'stage_3': flag})
                    else:
                        responses.append({'response': response, 'word_count': word_count,'flag': "think_format_bad",'stage_1': Node_1, 'stage_2': Node_2})
                else:
                    responses.append({'response': response, 'word_count': word_count,'flag': "Word_bad",'stage_1': Node_1, 'stage_2': Node_2})
            flag_all += flag
            num_all += num    
        # Add the responses to the original data
        data['Stage_3_stat'] = {"flag": flag_all, "num": num_all, "Finish_rate": flag_all/num_all}
        data['Stage_3_output'] = responses
        data['final_result'] = final_answer
        # Save the updated data back to the original JSON file
        logging.warning(f"{f} stage3—done")
        with open(file_path, 'w') as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)

# Get a list of all JSON files in the directory
json_files = [os.path.join(json_dir, file) for file in os.listdir(json_dir) if file.endswith('.json')]

start_time = time.time()
# Process the JSON files in parallel with 8 threads
with concurrent.futures.ThreadPoolExecutor(max_workers=512) as executor:
    executor.map(process_Stage_3, json_files)

log_time_taken("Stage_3", start_time)




