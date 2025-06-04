import os
import re
import time
import json
import queue
import threading
import traceback
import requests
import concurrent.futures
from tqdm import tqdm

# ---- Configuration ----
MAX_CONCURRENT_REQUESTS = 1024  # 保持并发线程数接近1024
REQUEST_TIMEOUT = 1200          # 请求超时秒数
MAX_RETRIES = 5                # 请求最大重试次数
FILE_UPDATE_BATCH_SIZE = 10    # 批量更新阈值
FILE_UPDATE_FLUSH_INTERVAL = 5  # 批量更新最大等待秒数

# ---- Global Semaphores & Counters ----
request_semaphore = threading.Semaphore(MAX_CONCURRENT_REQUESTS)
counter_lock = threading.Lock()
processed_counter = 0
successful_counter = 0
failed_counter = 0

# ---- File Update Infrastructure ----
file_update_queue = queue.Queue()
file_update_workers_active = True
file_update_workers = []
file_locks = {}
file_locks_mutex = threading.Lock()

# ---- HTTP Session ----
session = requests.Session()


def get_file_lock(file_path):
    with file_locks_mutex:
        if file_path not in file_locks:
            file_locks[file_path] = threading.Lock()
        return file_locks[file_path]


def get_response(query, url="http://172.18.201.139:9999/v1/chat/completions", model="default"):
    
    messages = [{"role": "user", "content": query}]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.6,
        "top_p": 0.95,
        "max_tokens": 8192,
        "stop": ["<|user|>", "<|endoftext|>"]
    }

    with request_semaphore:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                content = data['choices'][0]['message']['content'].strip().split("</think>")[-1].strip()
                return content
            except Exception as e:
                if attempt == MAX_RETRIES:
                    print(f"Request failed after {MAX_RETRIES} attempts: {e}")
                # 立即重试，无延迟
    return ""


def clean_response(text):
    text = re.sub(r'Final answer: ?', '', text)
    text = re.sub(r'Refine Paragraph \d+ : ### \*\*Paragraph \d+: ?', '', text)
    text = re.sub(r'Refine Paragraph \d+ : ?', '', text)
    return text


def get_pending_tasks(folder_path):
    tasks = []
    for fname in os.listdir(folder_path):
        if not fname.endswith('.json'):
            continue
        path = os.path.join(folder_path, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'query' not in data or 'final_result' not in data:
                continue
            for idx, item in enumerate(data['final_result']):
                if str(idx) not in data.get('evaluate_result', {}):
                    tasks.append((path, data['query'], item, data.get('evaluate_standard', {}), idx))
        except Exception as e:
            print(f"Error reading {fname}: {e}")
    return tasks


def get_json(text):
    m = re.search(r'```json\n({.*?})\n```', text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def process_single_result(file_path, query, result_item, evaluate_standard, result_idx, format_eval):
    global processed_counter, successful_counter, failed_counter
    try:
        clean_res = clean_response(result_item.get('responese', ''))
        prompt = f"""
### Query: {query}

### Result: <start> {clean_res} <end>

### Evaluation Standard: {json.dumps(evaluate_standard, ensure_ascii=False)}

Based on the provided info, perform a rigorous evaluation. {format_eval}
"""
        successes = []
        attempt = 0
        while attempt < MAX_RETRIES and len(successes) < 3:
            attempt += 1
            ans = get_response(prompt)
            j = get_json(ans)
            if j:
                successes.append(j)
        if successes:
            final = {}
            for key in successes[0]:
                scores = [s[key]['Score'] for s in successes if key in s]
                final[key] = successes[0][key]
                final[key]['Score'] = sum(scores) / len(scores)
            total = sum(v['Score'] for v in final.values())
            final['total_score'] = total
            final.update({f'stage_{i}': result_item.get(f'stage_{i}') for i in (1,2,3)})
            successful = True
        else:
            final = {k: {'Score': 0, 'Analysis': 'Evaluation failed'} for k in evaluate_standard}
            final['total_score'] = 0
            final.update({f'stage_{i}': result_item.get(f'stage_{i}') for i in (1,2,3)})
            successful = False
        file_update_queue.put((file_path, result_idx, final))
        with counter_lock:
            processed_counter += 1
            if successful:
                successful_counter += 1
            else:
                failed_counter += 1
    except Exception:
        with counter_lock:
            processed_counter += 1
            failed_counter += 1
        traceback.print_exc()


def file_update_worker():
    pending = {}
    last_flush = time.time()
    while file_update_workers_active or not file_update_queue.empty():
        try:
            item = file_update_queue.get(timeout=1)
        except queue.Empty:
            if pending and time.time() - last_flush >= FILE_UPDATE_FLUSH_INTERVAL:
                _flush_updates(pending)
                pending.clear()
                last_flush = time.time()
            continue
        path, idx, data = item
        pending.setdefault(path, {})[str(idx)] = data
        if len(pending) >= FILE_UPDATE_BATCH_SIZE or time.time() - last_flush >= FILE_UPDATE_FLUSH_INTERVAL:
            _flush_updates(pending)
            pending.clear()
            last_flush = time.time()
        file_update_queue.task_done()
    if pending:
        _flush_updates(pending)


def _flush_updates(pending):
    for path, updates in pending.items():
        lock = get_file_lock(path)
        with lock:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                content.setdefault('evaluate_result', {})
                for idx, res in updates.items():
                    content['evaluate_result'][idx] = res
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error updating {path}: {e}")
                traceback.print_exc()

format_eval = """
The final output should be in JSON format, structured as follows:
```json
{
    \"Criterion 1\": {\n        \"Analysis\": \"...\",\n        \"Score\": X\n    },
    ...
}
```"""


def main():
    global file_update_workers_active
    folder = os.environ.get('DATA_FOLDER', '')
    tasks = get_pending_tasks(folder)
    total = len(tasks)
    print(f"Found {total} pending tasks.")
    if not total:
        return

    # 启动文件更新线程
    file_update_workers_active = True
    num_workers = min(64, os.cpu_count())
    for _ in range(num_workers):
        t = threading.Thread(target=file_update_worker, daemon=True)
        t.start()
        file_update_workers.append(t)

    with tqdm(total=total, desc="Processing tasks") as pb:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as executor:
            futures = [executor.submit(process_single_result, *t, format_eval) for t in tasks]
            for f in concurrent.futures.as_completed(futures):
                pb.update(1)

    file_update_workers_active = False
    file_update_queue.join()
    print(f"Done: {processed_counter} processed, {successful_counter} succeeded, {failed_counter} failed")

if __name__ == '__main__':
    main()
