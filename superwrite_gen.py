import os
import json
import time
import requests
import concurrent.futures
import re
from pathlib import Path
import threading
from tqdm import tqdm

def better_len(text):
    """
    统计字符串的"字数"：对于中文，按每个汉字计数；
    对于英文，按单词计数（英文单词由字母、数字、下划线构成）。
    """
    # 匹配所有中文汉字（Unicode 范围：\u4e00 到 \u9fff）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    
    # 去掉所有中文字符后，再匹配英文单词
    text_no_chinese = re.sub(r'[\u4e00-\u9fff]', '', text)
    english_words = re.findall(r'\b\w+\b', text_no_chinese)
    
    return len(chinese_chars) + len(english_words)

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
            f"Superwrite-Stage-3: "
            f"### Stage-2 Write generated content: *** {check_query_draft} *** \n"
            f"### Task: {refine_query}"
        )
    elif stage == "final":
        final_result = extract_sections(previous_output)
        check_query_draft = "\n".join(final_result)
        return (
            f"{check_query_draft}"
        )

def query_llm_with_retry(query, max_retries=3, url="http://172.20.76.62:9999/v1/chat/completions", model="default", api_key="None"):
    """
    Query the LLM API with retry mechanism to ensure both thinking and answer parts are extracted.
    """
    for retry in range(max_retries):
        try:
            messages = [{"role": "user", "content": query}]
            request_data = {
                "model": model,
                "messages": messages,
                "temperature": 0.6,
                "top_p": 0.95,
                "seed": 42,
                "max_tokens": 32768,
                "stop": ["<|user|>", "<|endoftext|>","#*# finish."],
            }
            
            response = requests.post(
                url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=1200
            )
            resp_json = response.json()
            content = resp_json['choices'][0]['message']['content'].strip()
            #content = content.split("</think>")[-1].strip()
            # Try to format the response
            formatted_content = content
            
            # If formatting succeeds (both think and answer parts found), return the result
            if formatted_content is not None:
                return formatted_content
         
        except Exception as e:
            print(f"Attempt {retry+1}/{max_retries} failed with error: {e}")
    
    return None  # Return None to indicate failure after all retries

class RealTimeSaver:
    """
    Helper class to manage real-time saving of results with option for immediate saving.
    """
    def __init__(self, output_path, batch_size=1):  # Default to 1 for real-time saving
        self.output_path = output_path
        self.batch_size = batch_size
        self.results_buffer = []
        self.lock = threading.Lock()
        self.total_saved = 0
        self.total_processed = 0
        
        # Create directory if not exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Initialize the output file (create or clear)
        with open(output_path, 'w', encoding='utf-8') as f:
            pass
    
    def save_result(self, result):
        """
        Save a single result, with option for immediate saving or batching.
        """
        if result is None:
            return
            
        with self.lock:
            self.results_buffer.append(result)
            self.total_processed += 1
            
            # Save immediately or when batch size is reached
            if len(self.results_buffer) >= self.batch_size:
                self._write_batch_to_file()
    
    def _write_batch_to_file(self):
        """
        Write the current batch to file and clear buffer.
        """
        if not self.results_buffer:
            return
            
        with open(self.output_path, 'a', encoding='utf-8') as f:
            for result in self.results_buffer:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        saved_count = len(self.results_buffer)
        self.total_saved += saved_count
        self.results_buffer = []
        
        # Only print for larger batches or periodically
        if saved_count > 1 or self.total_saved % 10 == 0:
            print(f"Saved: {saved_count} items (Total: {self.total_saved}/{self.total_processed})")
    
    def finalize(self):
        """
        Save any remaining results and return statistics.
        """
        with self.lock:
            if self.results_buffer:
                self._write_batch_to_file()
                print(f"Final batch saved. Total processed: {self.total_processed}, Total saved: {self.total_saved}")
            return self.total_saved, self.total_processed
        
def validate_plan_response(response):
    """
    Validate Stage 1 (Plan) response:
    - Word count should be between 500 and 22000
    - Response should have exactly 2 <answer> sections
    - Response should have either 1 or 2 <think> sections
    """
    
    if response is None:
        return False
    # print('='*50)
    word_count = better_len(response)
    # print(word_count)
    answer_sections = extract_sections(response)
    # print(len(answer_sections))
    think_sections = extract_sections_think(response)
    # print(len(think_sections))
    valid = (
        500 < word_count < 32000 and
        len(answer_sections) == 2 and
        (len(think_sections) == 2 or len(think_sections) == 1)
    )
    
    return valid

def validate_write_or_refine_response(response):
    """
    Validate Stage 2 (Write) or Stage 3 (Refine) response:
    - Word count should be between 1000 and 22000
    - Number of <answer> sections should be between 4 and 16 (inclusive)
    - Number of <think> sections should be between 4 and 16 (inclusive)
    - Number of <answer> and <think> sections should be equal
    """
    if response is None:
        return False
    
    word_count = better_len(response)
    answer_sections = extract_sections(response)
    think_sections = extract_sections_think(response)
    
    valid = (
        1000 < word_count < 32000 and
        4 <= len(answer_sections) <= 16 and
        4 <= len(think_sections) <= 16 and
        len(answer_sections) == len(think_sections)
    )
    
    return valid

def process_item_and_save(item_index, query, saver):
    """
    Process a single query through a 3-stage chained inference process and save the result.
    """
    max_retries = 10  # Maximum attempts per stage
    
    # Track success of each stage
    stage_results = {
        "plan": False,
        "write": False,
        "refine": False,
        "final": False
    }
    
    # Stage 1: Plan
    plan_response = None
    for attempt in range(max_retries):
        plan_prompt = generate_prompt("plan", use_query=query)
        curr_response = query_llm_with_retry(plan_prompt, max_retries=2)
        
        #print(f"Item {item_index}: {curr_response}")
    
        if validate_plan_response(curr_response):
            plan_response = curr_response
            stage_results["plan"] = True
            # print(f"Item {item_index}: Plan stage Done")
            break
        
        print(f"Item {item_index}: Plan stage attempt {attempt+1}/{max_retries} failed validation")
    
    if plan_response is None:
        # If all plan stage attempts fail, save what we have and return
        result = {
            "index": item_index,
            "query": query,
            "stage_results": stage_results,
            "response": None,
            "attempt_counts": {"plan": max_retries, "write": 0, "refine": 0}
        }
        saver.save_result(result)
        return False
    
    # Stage 2: Write
    write_response = None
    write_attempts = 0
    for attempt in range(max_retries):
        write_attempts += 1
        write_prompt = generate_prompt("write", use_query=query, previous_output=plan_response)
        curr_response = query_llm_with_retry(write_prompt, max_retries=2)
        
        if validate_write_or_refine_response(curr_response):
            write_response = curr_response
            stage_results["write"] = True
            break
        
        print(f"Item {item_index}: Write stage attempt {attempt+1}/{max_retries} failed validation")
    
    if write_response is None:
        # If all write stage attempts fail, save what we have and return
        result = {
            "index": item_index,
            "query": query,
            "stage_results": stage_results,
            "response": plan_response,
            "attempt_counts": {"plan": max_retries if plan_response is None else 1, 
                              "write": write_attempts, 
                              "refine": 0}
        }
        saver.save_result(result)
        return False
    
    # Stage 3: Refine
    refine_response = None
    refine_attempts = 0
    for attempt in range(max_retries):
        refine_attempts += 1
        refine_prompt = generate_prompt("refine", use_query=query, previous_output=write_response, final_outline=plan_response)
        curr_response = query_llm_with_retry(refine_prompt, max_retries=2)
        
        if validate_write_or_refine_response(curr_response):
            refine_response = curr_response
            stage_results["refine"] = True
            print(f"Item {item_index}: refine done !!!!! ")
            break
        
        print(f"Item {item_index}: Refine stage attempt {attempt+1}/{max_retries} failed validation")
   

    if refine_response is None:
        # If all refine stage attempts fail, save what we have and return
        result = {
            "index": item_index,
            "query": query,
            "stage_results": stage_results,
            "response": write_response,
            "attempt_counts": {"plan": max_retries if plan_response is None else 1, 
                              "write": write_attempts, 
                              "refine": refine_attempts}
        }
        saver.save_result(result)
        return False
    
    # Final stage: Compile final answer
    final_response = generate_prompt("final", previous_output=refine_response)
    print(f"Item {item_index}: final done !!!!! ")
    stage_results["final"] = True
    
    # Format the final result
    result = {
        "index": item_index,
        "query": query,
        "stage_results": stage_results,
        "response": final_response,
        # "intermediate_responses": {
        #     "plan": plan_response,
        #     "write": write_response,
        #     "refine": refine_response
        # },
        "attempt_counts": {
            "plan": max_retries if plan_response is None else 1, 
            "write": write_attempts, 
            "refine": refine_attempts
        }
    }
    
    # Save the result
    saver.save_result(result)
    return True

def process_jsonl_file(input_path, output_path, max_workers=128):
    """
    Process a single JSONL file with real-time saving.
    """
    # Initialize real-time saver
    saver = RealTimeSaver(output_path, batch_size=1)
    
    # Keep track of stage success statistics
    stage_stats = {
        "total": 0,
        "plan_success": 0,
        "write_success": 0,
        "refine_success": 0,
        "final_success": 0,
        "avg_plan_attempts": 0,
        "avg_write_attempts": 0,
        "avg_refine_attempts": 0
    }
    
    # Counters for attempts
    total_plan_attempts = 0
    total_write_attempts = 0
    total_refine_attempts = 0
    
    # Read all items first to allow concurrent processing
    items = []
    with open(input_path, 'r', encoding='utf-8') as f_in:
        for line in f_in:
            try:
                data = json.loads(line.strip())
                # Extract index and query from the input data
                item_index = data.get("index", None)
                query = data.get("query", "")
                
                if item_index is not None and query:
                    items.append((item_index, query))
            except json.JSONDecodeError:
                print(f"Failed to parse line: {line.strip()[:100]}...")
    
    print(f"Loaded {len(items)} items from {input_path}")
    stage_stats["total"] = len(items)
    
    # Process items concurrently with real-time saving
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Map function arguments for each item
        futures = {}
        for item_index, query in items:
            future = executor.submit(process_item_and_save, item_index, query, saver)
            futures[future] = item_index
        
        # Show progress with tqdm
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(items), desc=f"Processing {os.path.basename(input_path)}"):
            try:
                result = future.result()
                if isinstance(result, dict) and "stage_results" in result:
                    # Update statistics
                    if result["stage_results"]["plan"]:
                        stage_stats["plan_success"] += 1
                    if result["stage_results"]["write"]:
                        stage_stats["write_success"] += 1
                    if result["stage_results"]["refine"]:
                        stage_stats["refine_success"] += 1
                    if result["stage_results"]["final"]:
                        stage_stats["final_success"] += 1
                        
                    # Update attempt counts
                    if "attempt_counts" in result:
                        total_plan_attempts += result["attempt_counts"].get("plan", 0)
                        total_write_attempts += result["attempt_counts"].get("write", 0)
                        total_refine_attempts += result["attempt_counts"].get("refine", 0)
                        
                results.append(result)
            except Exception as e:
                print(f"Error processing item {futures[future]}: {e}")
    
    # Calculate average attempts
    if stage_stats["total"] > 0:
        stage_stats["avg_plan_attempts"] = total_plan_attempts / stage_stats["total"]
        stage_stats["avg_write_attempts"] = total_write_attempts / stage_stats["total"]
        stage_stats["avg_refine_attempts"] = total_refine_attempts / stage_stats["total"]
    
    # Finalize saving and get statistics
    total_saved, total_processed = saver.finalize()
    
    print(f"Completed processing {input_path}. Processed: {total_processed}, Saved: {total_saved}")
    print(f"Stage Success Statistics:")
    print(f"  Plan Stage: {stage_stats['plan_success']}/{stage_stats['total']} ({stage_stats['plan_success']/stage_stats['total']*100:.2f}%)")
    print(f"  Write Stage: {stage_stats['write_success']}/{stage_stats['total']} ({stage_stats['write_success']/stage_stats['total']*100:.2f}%)")
    print(f"  Refine Stage: {stage_stats['refine_success']}/{stage_stats['total']} ({stage_stats['refine_success']/stage_stats['total']*100:.2f}%)")
    print(f"  Final Stage: {stage_stats['final_success']}/{stage_stats['total']} ({stage_stats['final_success']/stage_stats['total']*100:.2f}%)")
    print(f"  Average Attempts:")
    print(f"    Plan: {stage_stats['avg_plan_attempts']:.2f}")
    print(f"    Write: {stage_stats['avg_write_attempts']:.2f}")
    print(f"    Refine: {stage_stats['avg_refine_attempts']:.2f}")
    
    return total_saved, stage_stats

def main(input_file, output_file, max_workers=64):
    """
    Process a JSONL file and save results in the specified format.
    """
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"Processing file: {input_file}")
    
    try:
        saved_count, stage_stats = process_jsonl_file(input_file, output_file, max_workers)
        print(f"Completed processing {input_file}. Total saved results: {saved_count}")
        
        # Save stage statistics to a separate file
        stats_file = f"{os.path.splitext(output_file)[0]}_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stage_stats, f, indent=2)
        print(f"Stage statistics saved to {stats_file}")
        
    except Exception as e:
        print(f"Error processing file {input_file}: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Process JSONL files with LLM using 3-stage chained inference")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file")
    parser.add_argument("--output", type=str, required=True, help="Output JSONL file")
    parser.add_argument("--max-workers", type=int, default=256, help="Maximum workers for concurrent processing")
    
    args = parser.parse_args()
    
    main(args.input, args.output, args.max_workers)