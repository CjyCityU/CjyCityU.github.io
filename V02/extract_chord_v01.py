import pandas as pd
import os
import re
from bs4 import BeautifulSoup
import json
import sys
import traceback
import time
from zhipuai import ZhipuAI

def log_step(step_name, percentage, description):
    """
    输出当前执行步骤、进度和描述
    """
    print(f"[{percentage}%] {step_name}: {description}")

def call_glm_api(text_content):
    """
    调用智谱GLM接口提取和弦
    """
    api_key = "2444623d96b34ef5b852afb1cd8ea4ef.KD7BtW6xwDOJPcdZ"
    
    # 截断文本以避免超出Token限制（视具体模型限制而定，这里保守取前8000字符）
    truncated_text = text_content[:8000]
    
    try:
        client = ZhipuAI(api_key=api_key)
        response = client.chat.completions.create(
            model="glm-4-flash", # 使用较快且便宜的模型
            messages=[
                {
                    "role": "user",
                    "content": f"请从以下文本中按出现顺序提取所有吉他和弦，不要去重，保持它们在文本中的原始顺序，并以逗号分隔的格式返回（例如：G, C, D, G）。如果找不到和弦，请返回空字符串。不要返回任何其他解释性文字，只返回和弦列表。\n\n文本：\n{truncated_text}"
                }
            ],
            temperature=0.1 # 低温度以获得确定性结果
        )
        content = response.choices[0].message.content
        return content.strip()
    except Exception as e:
        print(f"Warning: GLM API Call Error: {e}")
        return None

def extract_data_from_html(file_path):
    """
    从HTML文件中提取 Tuning, Key, Capo, Chords, Lyrics
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'html.parser')
        
        data = {
            'Tuning': None,
            'Key': None,
            'Capo': None,
            'Chords': None,
            '歌词': None # 实际存储歌词与和弦
        }

        # 1. 提取 Metadata (Tuning, Key, Capo)
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            if not script.string:
                continue
            try:
                json_data = json.loads(script.string)
                if isinstance(json_data, dict):
                    if json_data.get('@type') == 'MusicComposition':
                        data['Key'] = json_data.get('musicalKey')
                        text_content = json_data.get('text', '')
                        if text_content:
                            tuning_match = re.search(r'Tuning:\s*(.*?)(?:\s+Key:|\s+Capo:|\s*$)', text_content)
                            if tuning_match:
                                data['Tuning'] = tuning_match.group(1).strip()
                            capo_match = re.search(r'Capo:\s*(.*?)(?:\s+Difficulty:|\s+Tuning:|\s*$)', text_content)
                            if capo_match:
                                data['Capo'] = capo_match.group(1).strip()
                        break
            except json.JSONDecodeError:
                continue
        
        # 2. 提取 Chords 和 歌词
        # 查找包含和弦的容器
        first_chord_span = soup.find('span', attrs={'data-name': True})
        
        if first_chord_span:
            content_container = first_chord_span.parent
            
            # 获取完整文本（包含和弦和歌词）
            full_text_content = content_container.get_text(separator='\n')
            
            # 保存完整文本到 '歌词' 列 (实际是 歌词与和弦)
            # 清理一下多余空行
            lines = [line.strip() for line in full_text_content.split('\n')]
            clean_lines = [line for line in lines if line]
            data['歌词'] = "\n".join(clean_lines)

            # --- 使用 GLM 提取和弦 ---
            # 调用 GLM API
            ai_chords = call_glm_api(full_text_content)
            
            if ai_chords:
                data['Chords'] = ai_chords
            else:
                # 如果 AI 失败，只报错，不回退
                print(f"Warning: AI无法返回结果或出错: {os.path.basename(file_path)}")
                data['Chords'] = None
            
        else:
            pass

        return data

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        traceback.print_exc()
        return None

def main():
    try:
        excel_path = r'd:\Files\proj\coding\music_analysis02\billboard_hot100_2025_v02.xlsx'
        html_dir = r'd:\Files\proj\coding\music_analysis02\html_downloads'
        
        log_step("初始化", 0, "开始程序，检查文件路径...")
        
        if not os.path.exists(excel_path):
            print(f"Excel文件不存在: {excel_path}")
            return
        if not os.path.exists(html_dir):
            print(f"HTML目录不存在: {html_dir}")
            return

        # 尝试以写入模式打开一次，检查文件是否被占用
        try:
            with open(excel_path, 'a'):
                pass
        except PermissionError:
             print(f"Error: Excel 文件 {excel_path} 被占用，请关闭文件后重试！")
             return

        log_step("读取Excel", 5, "正在加载 Excel 文件...")
        df = pd.read_excel(excel_path)
        
        # 更新列名需求：虽然代码里字典key是 '歌词'，但Excel里可以叫 '歌词与和弦'
        # 不过用户说 "歌词部分改为歌词与和弦列"，我们可以把 '歌词' 列重命名或者直接用新列名
        # 为了兼容之前的代码，我们先检查列。
        # 建议：如果 '歌词' 列存在，就用 '歌词'，内容改成完整文本。
        # 如果用户想改列名，我们可以最后 rename。
        
        target_columns = ['Tuning', 'Key', 'Capo', 'Chords', '歌词']
        for col in target_columns:
            if col not in df.columns:
                df[col] = None
                
        log_step("扫描文件", 10, "正在扫描 HTML 文件...")
        html_files = [f for f in os.listdir(html_dir) if f.endswith('.html')]
        total_files = len(html_files)
        
        processed_count = 0
        
        log_step("开始处理", 15, f"找到 {total_files} 个 HTML 文件，开始解析（AI 模式）...")
        
        for idx, filename in enumerate(html_files):
            file_path = os.path.join(html_dir, filename)
            
            try:
                rank_str = filename.split('_')[0]
                rank = int(rank_str)
            except ValueError:
                continue
                
            # 实时进度
            current_percent = 15 + int((processed_count / total_files) * 80)
            if processed_count % 5 == 0:
                log_step("处理中", current_percent, f"[{processed_count+1}/{total_files}] 正在处理 Rank {rank}...")
            
            extracted_data = extract_data_from_html(file_path)
            
            if extracted_data:
                mask = df['rank'] == rank
                if mask.any():
                    for key, value in extracted_data.items():
                        df.loc[mask, key] = value
                else:
                    pass
            
            processed_count += 1
            # 稍微延时避免 QPS 限制
            # time.sleep(0.2) 
        
        # 重命名列（如果需要）
        # df.rename(columns={'歌词': '歌词与和弦'}, inplace=True) 
        # 用户说 "歌词部分改为歌词与和弦列"，这里我们直接把内容写进 '歌词' 列，是否改名看用户意图
        # 为了清晰，我们可以把列名改成 '歌词与和弦'
        if '歌词' in df.columns:
             df.rename(columns={'歌词': '歌词与和弦'}, inplace=True)

        log_step("保存文件", 95, "正在保存 Excel 文件...")
        try:
            df.to_excel(excel_path, index=False)
            log_step("完成", 100, f"处理完成！成功更新 {processed_count} 条数据。")
        except PermissionError:
             print(f"保存失败: Excel 文件 {excel_path} 被占用，请关闭文件后重试！")

    except Exception as e:
        print(f"发生严重错误: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
