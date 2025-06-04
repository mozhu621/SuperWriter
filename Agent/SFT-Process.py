import json
import random
random.seed(42)
import re
# Load your JSON file
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


import re

def clean_content(content):
    """
    清理content内容，根据以下规则：
    1. 如果最后10个字符中有"）"或")"，找到对应的"（"或"("并删除从该符号到结尾的所有内容
    2. 如果content以修改标记开头(如"**修改后的段落："等)，删除从开头到最近的冒号(:或：)
    3. 如果content包含字数指示(如"（字数：240字）")，删除从"（"或"("到结尾的内容
    4. 如果content包含修改说明(如"### 修改说明"或"### 修")，删除这部分内容以及前面直到找到的最近的句子结束符号
    5. 最后确保content以正常的句子结束符号结尾，如果不是则删除到上一个句子结束符号
    
    Args:
        content (str): 需要清理的内容
        
    Returns:
        str: 清理后的内容
    """
    if not content or not isinstance(content, str):
        return content
    
    # 情况1: 如果最后10个字符中有"）"或")"，删除从"（"或"("到结尾的内容
    last_10_chars = content[-10:] if len(content) >= 10 else content
    if "）" in last_10_chars or ")" in last_10_chars:
        # 查找最后的中文或英文开括号
        cn_opening_index = content.rfind("（")
        en_opening_index = content.rfind("(")
        
        # 取最后出现的开括号位置
        opening_index = max(cn_opening_index, en_opening_index)
        
        if opening_index != -1:
            content = content[:opening_index]
    
    # 情况2: 如果以修改标记开头，删除从开头到最近的冒号
    revision_indicators = [
        "**修改后的段落", "**### 修订后段落", "### 修订后段落", 
        "修改后的段落", "修订后段落", "修改", "修订"
    ]
    
    for indicator in revision_indicators:
        if content.startswith(indicator):
            # 寻找英文和中文冒号的位置
            en_colon_pos = content.find(":", len(indicator))
            zh_colon_pos = content.find("：", len(indicator))
            
            # 确定哪个冒号更近
            colon_positions = []
            if en_colon_pos != -1:
                colon_positions.append(en_colon_pos)
            if zh_colon_pos != -1:
                colon_positions.append(zh_colon_pos)
            
            if colon_positions:
                nearest_colon_pos = min(colon_positions)
                content = content[nearest_colon_pos + 1:].strip()
            break
    
    # 情况3: 检查字数指示并删除从该处到结尾的内容
    word_count_patterns = [
        r'[（(]字数[：:]\s*\d+\s*字[）)]',  # (字数：240字)
        r'[（(][字数]+[：:]\s*\d+[）)]',    # (字数：240)
        r'[（(]\d+\s*字[）)]',              # (240字)
        r'[（(][约有]?\s*\d+\s*[个]?字[）)]',  # (约240个字)
        r'[（(]字[：:]\s*\d+[）)]',         # (字：240)
        r'[（(][字数][：:]\s*\d+\s*[字数][）)]'  # (字：240字)
    ]
    
    for pattern in word_count_patterns:
        match = re.search(pattern, content)
        if match:
            content = content[:match.start()]
            break
    
    # 情况4: 检查修改说明，并找到前面的句子结束符
    explanation_patterns = [
        r'###\s*修改说明',
        r'修改说明',
        r'###\s*说明',
        r'###\s*修',  # 增加对 "### 修" 的支持
        r'---.*###',  # 处理 "---" 与 "###" 的组合
        r'---.*修改',
        r'---.*修订',
        r'\n\n---'
    ]
    
    for pattern in explanation_patterns:
        match = re.search(pattern, content)
        if match:
            # 找到匹配位置前的最后一个句子结束符（。！？.!?）
            text_before = content[:match.start()]
            
            # 查找最后一个句子结束符
            last_period = text_before.rfind('。')
            last_exclamation = text_before.rfind('！')
            last_question = text_before.rfind('？')
            last_en_period = text_before.rfind('.')
            last_en_exclamation = text_before.rfind('!')
            last_en_question = text_before.rfind('?')
            
            # 找出所有有效的句子结束符位置
            ending_positions = []
            if last_period != -1:
                ending_positions.append(last_period)
            if last_exclamation != -1:
                ending_positions.append(last_exclamation)
            if last_question != -1:
                ending_positions.append(last_question)
            if last_en_period != -1:
                ending_positions.append(last_en_period)
            if last_en_exclamation != -1:
                ending_positions.append(last_en_exclamation)
            if last_en_question != -1:
                ending_positions.append(last_en_question)
            
            if ending_positions:
                # 找到最后的句子结束符位置
                last_ending_pos = max(ending_positions)
                # 截断到最后句子结束符位置(包含该结束符)
                content = content[:last_ending_pos + 1]
            else:
                # 如果找不到句子结束符，直接从修改说明处截断
                content = content[:match.start()].strip()
            break
    
    # 情况5: 确保content以正常的句子结束符号结尾
    sentence_ending_chars = ['。', '！', '？', '.', '!', '?']
    
    # 首先检查是否已经以句子结束符结尾
    if content and content[-1] not in sentence_ending_chars:
        # 如果不是，则找到最后一个句子结束符位置
        last_period = content.rfind('。')
        last_exclamation = content.rfind('！')
        last_question = content.rfind('？')
        last_en_period = content.rfind('.')
        last_en_exclamation = content.rfind('!')
        last_en_question = content.rfind('?')
        
        # 找出所有有效的句子结束符位置
        ending_positions = []
        if last_period != -1:
            ending_positions.append(last_period)
        if last_exclamation != -1:
            ending_positions.append(last_exclamation)
        if last_question != -1:
            ending_positions.append(last_question)
        if last_en_period != -1:
            ending_positions.append(last_en_period)
        if last_en_exclamation != -1:
            ending_positions.append(last_en_exclamation)
        if last_en_question != -1:
            ending_positions.append(last_en_question)
        
        if ending_positions:
            # 找到最后的句子结束符位置
            last_ending_pos = max(ending_positions)
            # 截断到最后句子结束符位置(包含该结束符)
            content = content[:last_ending_pos + 1]
    
    return content
    
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

Think_tamplate = ""
# Think_tamplate = """First thinks about the thought process in the mind and then provides the user with the answer. The thought process and answer are enclosed within <think> </think> and <answer> </answer> tags, respectively, i.e., <think> thought process here </think> <answer> answer here </answer> \n"""# Process each element in the JSON data
def process_data(data):
    result = []
    num = 0
    i = 0
    stage3_num = 0
    for key, value in data.items():
        use_query = value.get('query', '')

        plan_query = Think_tamplate +  f"Superwrite-Stage-1: \n### User query: *** {use_query} ***. \nBased on the user query, please develop a detailed brainstorm and outline specifically addressing the task. The response should include the objective, target audience, key points, and structure in a clear and thorough manner. \n### Superwrite Answer:"
        write_query = f"Based on the Stage-1 Plan, carefully think through each paragraph of the outline, then generate the content for each paragraph one by one. \n### Superwrite Answer:"
        
        #refine_query = f"Based on the Stage-1 Plan and Stage-2 Write generated content, review and refine each paragraph individually. Improve clarity, coherence, and consistency, fix errors, and ensure smooth transitions between sections. After refining all paragraphs, compile the final polished version. Answer:"
        refine_query =  f"Based Stage-2 Write generated content, review and refine each paragraph individually. Improve clarity, coherence, and consistency, fix errors, and ensure smooth transitions between sections. After refining all paragraphs, compile the final polished version. \n### Superwrite Answer:"
      
        plan_output = '### Superwriter-Stage-1 Plan Start: '
        write_output = '###  Superwriter-Stage-2 Write Start: '
        refine_output = '###  Superwriter-Stage-3 Refine Start:'
        task_chain_of_thought = value.get('Task_Chain_of_thought', [])

       
        current_stage = 'Plan'  # 初始阶段为 Plan
        stage_descriptions_shown = {'Plan': False, 'Write': False, 'Refine': False}
        Paragraph_index = 0
        Paragraph_num = 0
       
        # stat
        stage1_flag = False
        BG_num = 0
        stage2_flag = 0
        for task in task_chain_of_thought:
            token = task.get('token', '')
            content = task.get('content', '')
            agent = task.get('agent', '')
            if agent == "ParagraphAgent":
                if token == "Paragraph_focus_think":
                    Paragraph_num  += 1
            if agent == "InitializationAgent_refine_outline":
                stage1_flag = True
            if agent == "RevisionAgent_modification":
                BG_num += 1
            if agent == "CheckLoopAgent" and "pass" in content.lower():
                stage2_flag += 1
   
         
        write_query_draft = ''
        check_query_draft = ''      
        token_exchange_str = ''
        check_query_draft_outline = ''
        # Generate the Train data
        Stage1_num = 0
        stage3_flag = False
        plan_output += f"<think>"
        for task in task_chain_of_thought:
            token = task.get('token', '')
            content = task.get('content', '')
            agent = task.get('agent', '')
    
            if agent == "ParagraphAgent" and stage_descriptions_shown['Write'] == False:
                current_stage = 'Write'
                write_input = Think_tamplate + f"Superwrite-Stage-2: \n### Stage-1 Plan: *** {write_query_draft}\n### Outline:{check_query_draft_outline} *** \n ### Task: {write_query}"
                stage_descriptions_shown['Write'] = True
            if agent == "CheckLoopAgent" and  stage_descriptions_shown['Refine'] == False:
                current_stage = 'Check'
                stage_descriptions_shown['Refine'] = True
                stage_descriptions_shown['Write'] = False
       
                if(Paragraph_index != Paragraph_num):
                    print("Broken: ",Paragraph_index)
                    print("Corrent: ",Paragraph_num)
                Paragraph_index = 0
                refine_input = Think_tamplate + f"Superwrite-Stage-3:  \n### Stage-2 Write generated content: *** {check_query_draft} *** \n ### Task: {refine_query}"
               
            
            if stage_descriptions_shown['Write'] == True:
                #print(agent)
                if token == "Paragraph_focus_think":
                    Paragraph_index += 1
                    Paragraph_num_str = "<think> Think Paragraph " + str(Paragraph_index) + " :"
                    token_exchange_str = "Now start generating paragraph "+str(Paragraph_index)+" based on the above thinking. "
                    write_output += f"\n{Paragraph_num_str} {content} {token_exchange_str} </think>"
                else:
                    
                    Paragraph_num_str = "\nWrite Paragraph " + str(Paragraph_index) + " :"
         
                    if(Paragraph_index != Paragraph_num):
                        token_exchange_str = f"### The generation of paragraph {Paragraph_index} is complete. A total of {Paragraph_num} paragraphs need to be generated. Since {Paragraph_index} is less than {Paragraph_num}, it's now time to focus on paragraph {Paragraph_index + 1}."
                    else:
                        
                        token_exchange_str = f"### {Paragraph_index} out of {Paragraph_num} paragraphs have been generated. Since {Paragraph_index} is equal to {Paragraph_num}, the Stage-2 write task is now complete."
                    
                    check_query_draft += f"Paragraph {Paragraph_index}: {content} \n"
                    #content = clean_content(content)
                    write_output += f" <answer> {content} </answer> {token_exchange_str} "

            elif (stage_descriptions_shown['Refine'] == True):
          
                if token == "Reflective":
                    Paragraph_index += 1
                    Paragraph_num_str = "\nCheck Paragraph " + str(Paragraph_index) + " :"
                    token_exchange_str = "### Now start refining paragraph "+str(Paragraph_index)+" based on the above thinking."
                    refine_output += f"\n<think> {Paragraph_num_str} {content} {token_exchange_str} </think>"
                    # 没有写死的check sry

                    if agent == "CheckLoopAgent" and "pass" in content.lower(): 
                        stage3_flag = True

                else:
                    Paragraph_num_str = "\nRefine Paragraph " + str(Paragraph_index) + " :"
                    if Paragraph_index != Paragraph_num:
                        token_exchange_str = f"### Paragraph {Paragraph_index} has been refined. A total of {Paragraph_num} paragraphs need to be refined, Since {Paragraph_index} is less than {Paragraph_num} and it's now time to focus on paragraph {Paragraph_index + 1}."
                    else:
                        token_exchange_str = f"### {Paragraph_index} out of {Paragraph_num} paragraphs have been refined. Since {Paragraph_index} is equal to {Paragraph_num}, the Stage-3 refinement task is now complete."
                    #content = clean_content(content)
                    refine_output += f"\n<answer> {content} \n </answer> {token_exchange_str} "
            else:

                if not stage_descriptions_shown['Plan']:
                    stage_descriptions_shown['Plan'] = True

                if stage1_flag == False:
                    if agent == "RevisionAgent_modification" and Stage1_num == 1: 
                        # print("======")  
                        # print("RevisionAgent_modification")
                        write_query_draft = content.replace("Revised", "")
                        plan_output += f"</think>\n### Based on the previous recommendations, the final brainstorm process has begun.\n <answer> {content} </answer>"
                        plan_output += "\n### The brainstorm part of Stage-1 is complete. Next, focus on outline part. <think>"
                    elif agent == "InitializationAgent_outline":
                        check_query_draft_outline = f"\n### Title and Outline: {content}\n"
                        plan_output += f"Based on the previous recommendations, we are now generating the final outline. </think> <answer> Title and Outline: {content} </answer>"
                    # elif agent == "InitializationAgent_refine_outline":
                    #     check_query_draft_outline = f"\n### Title and Outline: {content}\n"
                    #     check_query_draft_outline = check_query_draft_outline.replace("Revised", "")
                    #     plan_output += f"\n#*# Based on the previous recommendations, we are now generating the final outline.\n#*# Final Outline: {content}"
                    #     plan_output += "\n#*# The Final Outline part of Stage-1 is complete."
                    elif token == "Reflective":
                        plan_output += f"\n Reflective phase: {content} "

                    else:
                        if agent == "RevisionAgent_modification":
                            Stage1_num += 1
                        plan_output += f"\nStage-1 {token}: {content}"
                else:
                    
                    if agent == "RevisionAgent_modification" and Stage1_num == 1: 
                        # print("======")  
                        # print("RevisionAgent_modification")
                        write_query_draft = content.replace("Revised", "")
                        plan_output += f"\n</think> ### Based on the previous recommendations, the final brainstorm process has begun. \n<answer> {content} </answer>"
                        plan_output += "\n### The brainstorm part of Stage-1 is complete. Next, focus on outline part. <think>"
                    elif agent == "InitializationAgent_outline":
                        plan_output += f"\n### Outline initiation: {content}"
                    elif agent == "InitializationAgent_refine_outline":
                        check_query_draft_outline = f"\n### Title and Outline: {content}\n"
                        check_query_draft_outline = check_query_draft_outline.replace("Revised", "")
                        plan_output += f"\nBased on the previous recommendations, we are now generating the final outline.</think> <answer> Title and Outline: {content} </answer>"
                    elif token == "Reflective":
                        plan_output += f"\n Reflective phase: {content} "

                    else:
                        if agent == "RevisionAgent_modification":
                            Stage1_num += 1
                        plan_output += f"\nStage-1 {token}: {content}"




           
        plan_output += " #*# Superwriter-Stage-1 Plan END \n #*# finish."
        write_output += " #*# Superwriter-Stage-2 Write END \n #*# finish."  
        refine_output += " #*# Superwriter-Stage-3 Refine END \n #*# finish."  
        if len(extract_sections(plan_output)) != 2:
            print("Plan_output: ",len(extract_sections(plan_output)))
        if len(extract_sections(write_output)) != Paragraph_num:
            print("Write_output: ",len(extract_sections(write_output)))
        # if len(extract_sections(refine_output)) != Paragraph_num:
        #     print("Refine_output: ",len(extract_sections(refine_output)))

        result.append({
            "messages": [
                {"role": "user", "content": plan_query},
                {"role": "assistant", "content": plan_output}
            ]
        })
        #print(result[-1])
        if len(extract_sections(write_output)) != len(extract_sections_think(write_output)):
            print("stage2 error")
        result.append({
            "messages": [
                {"role": "user", "content": write_input},
                {"role": "assistant", "content": write_output}
            ]
        })
        #print(result[-1])
        if stage3_flag == False and len(extract_sections(refine_output)) == Paragraph_num:
            if len(extract_sections(refine_output)) != len(extract_sections_think(refine_output)):
                print("stage3 error")
               
            result.append({
                "messages": [
                    {"role": "user", "content": refine_input},
                    {"role": "assistant", "content": refine_output}
                ]
            })
        #print(result[-1])
        
        # if i < 1:
        #     i += 1
        # else:
        #     break

        
    return result


# Save the result to a JSONL file
def save_jsonl(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as outfile:
        for entry in data:
            json.dump(entry, outfile, ensure_ascii=False)
            outfile.write('\n')


# Main function to load, process, and save JSON data
def main():
    input_file_path = ''
    
    output_file_path = ''
   

    data = load_json(input_file_path)

    # print(type(data))
    # data = data[::10]
    print(len(data))
    result = process_data(data)
    random.shuffle(result)
    save_jsonl(result, output_file_path)
    import json

    input_file = ''
    output_file = ''
    

    with open(input_file, 'r', encoding='utf-8') as infile, open(output_file, 'w', encoding='utf-8') as outfile:
        for idx, line in enumerate(infile):
            try:
                json_obj = json.loads(line)
               
                json.dump(json_obj, outfile, ensure_ascii=False)
                outfile.write('\n')
            except json.JSONDecodeError as e:
                print(f"[ERROR] Skipping invalid JSON at line {idx}: {e}")

    print(f"[INFO] Cleaned data saved to {output_file}")


if __name__ == "__main__":
    main() 