import pandas as pd
from DrissionPage import ChromiumPage, ChromiumOptions
import time
import random
import os
import re
import logging
from pathlib import Path
import sys
import urllib.parse
import traceback

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('match_chord_v08.log', encoding='utf-8')
    ]
)

# --- 常量定义 ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
]

def log(step, message, percentage):
    """
    输出带进度和中文描述的日志信息
    """
    logging.info(f"[{step}] {percentage}% - {message}")

def random_sleep(min_seconds=3, max_seconds=8):
    """
    随机延迟，模拟人类行为
    """
    sleep_time = random.uniform(min_seconds, max_seconds)
    log("等待", f"随机延迟 {sleep_time:.2f} 秒...", "...")
    time.sleep(sleep_time)

def sanitize_filename(name, max_length=200):
    """
    生成合法的文件名
    """
    name = re.sub(r'[\\/*?:"<>|]', '_', str(name))
    name = re.sub(r'[\s_]+', '_', name)
    name = name.strip('_')
    return name[:max_length] if name else "untitled"

def ensure_output_dir(directory):
    """
    确保输出目录存在
    """
    path = Path(directory)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise OSError(f"无法创建或写入目录 {directory}: {e}")

def save_page_content(browser, output_dir, filename):
    """
    下载并保存网页内容，注入Base标签
    """
    try:
        current_url = browser.url
        html_content = browser.html
        
        if "<base" not in html_content[:5000]: 
            head_match = re.search(r'<head.*?>', html_content, re.IGNORECASE)
            if head_match:
                insert_pos = head_match.end()
                base_tag = f'\n<base href="{current_url}">\n'
                html_content = html_content[:insert_pos] + base_tag + html_content[insert_pos:]
        
        out_path = ensure_output_dir(output_dir)
        final_path = out_path / f"{filename}.html"
        
        with open(final_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        return str(final_path)

    except Exception as e:
        log("错误", f"保存网页失败: {e}", 100)
        return None

def check_cloudflare(browser):
    """
    检查并尝试通过Cloudflare
    """
    if "Just a moment" in browser.title or "Cloudflare" in browser.title:
        log("反爬虫", "检测到Cloudflare验证，尝试等待...", 50)
        time.sleep(10)
        if "Just a moment" in browser.title:
            log("反爬虫", "仍处于验证页面，尝试刷新...", 50)
            browser.refresh()
            time.sleep(10)
        return True
    return False

def process_single_row(browser, row, index, total_rows, html_output_dir):
    """
    处理单行数据的核心逻辑
    """
    current_progress = int((index + 1) / total_rows * 100)
    artist = str(row['artist']).strip()
    title = str(row['title']).strip()
    rank = row['rank']
    
    log("开始", f"正在处理第 {index+1}/{total_rows} 行: {title} - {artist}", current_progress)
    
    # 1. 模拟用户行为：不清除Cookie，保持会话连续性
    # browser.set.cookies.clear() # 用户要求不要清除
    
    # 2. UA由浏览器自动管理，确保与版本匹配
    
    # 3. 打开首页 (模拟真实用户入口)
    log("导航", "正在打开首页...", current_progress)
    browser.get("https://www.ultimate-guitar.com/")
    random_sleep(3, 5)
    
    check_cloudflare(browser)
    
    # 4. 执行搜索
    search_query = f"{artist} {title}"
    encoded_query = urllib.parse.quote(search_query)
    # 模拟用户：从首页跳转到搜索页
    # 实际操作中，直接构造URL并带上Referer是比较稳妥的方式，或者找到搜索框输入
    # 为了稳定性，我们构造URL，但确保前一步是在首页
    search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={encoded_query}"
    
    log("搜索", f"正在搜索: {search_query}", current_progress)
    browser.get(search_url)
    random_sleep(4, 6)
    
    check_cloudflare(browser)
    
    # 5. 解析结果
    found_url = None
    links = browser.eles('tag:a')
    
    for link in links:
        href = link.attr('href')
        # 简单策略：找第一个 tab 链接
        if href and 'tabs.ultimate-guitar.com/tab/' in href:
            found_url = href
            break
            
    result_data = {
        'chords_URL': "Not Found",
        'chords_id': "Not Found",
        'saved_path': None
    }
    
    if found_url:
        log("解析", f"找到链接: {found_url}", current_progress)
        
        # 提取ID
        try:
            url_parts = found_url.rstrip('/').split('/')
            last_part = url_parts[-1]
            url_code = last_part
        except:
            url_code = "unknown"
            
        result_data['chords_URL'] = found_url
        result_data['chords_id'] = url_code
        
        # 6. 进入详情页
        log("抓取", "进入详情页下载...", current_progress)
        browser.get(found_url)
        random_sleep(3, 6)
        check_cloudflare(browser)
        
        # 7. 保存文件
        safe_title = sanitize_filename(title)
        safe_artist = sanitize_filename(artist)
        safe_code = sanitize_filename(url_code)
        try:
            rank_str = f"{int(rank):03d}"
        except:
            rank_str = "000"
            
        filename = f"{rank_str}_{safe_title}_by_{safe_artist}_{safe_code}"
        save_path = save_page_content(browser, html_output_dir, filename)
        
        if save_path:
            result_data['saved_path'] = save_path
            log("成功", "网页保存成功", current_progress)
    else:
        log("失败", "未找到搜索结果", current_progress)
        
    return result_data

def main():
    # --- 初始化 ---
    base_dir = Path(r"d:\Files\proj\coding\music_analysis02")
    excel_path = base_dir / "billboard_hot100_2025_v02.xlsx"
    csv_path = base_dir / "billboard_hot100_2025_v02.csv"
    html_output_dir = base_dir / "html_downloads"
    
    log("系统", "正在读取数据文件...", 0)
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        log("错误", f"读取Excel失败: {e}", 0)
        return

    # 初始化列
    if 'chords_URL' not in df.columns:
        df['chords_URL'] = None
    if 'chords_id' not in df.columns:
        df['chords_id'] = None
        
    total_rows = len(df)
    
    # --- 浏览器配置 ---
    co = ChromiumOptions()
    # 1. 使用默认UA，确保与浏览器版本完全匹配
    # co.set_user_agent(initial_ua) 
    co.headless(False)
    # 忽略证书错误
    co.ignore_certificate_errors(True)
    
    browser = ChromiumPage(co)
    
    log("提示", "程序已启动。如需中途停止，请按 Ctrl+C，程序将保存当前进度后安全退出。", 0)
    
    try:
        for index, row in df.iterrows():
            # 检查是否有中断信号文件 (可选的额外中断方式)
            if os.path.exists("stop.txt"):
                log("信号", "检测到 stop.txt 文件，正在停止...", 100)
                break
            current_progress = int((index + 1) / total_rows * 100)
            
            # 断点续传检查
            if pd.notna(row['chords_URL']) and str(row['chords_URL']).startswith('http'):
                log("跳过", f"第 {index+1} 行已存在数据", current_progress)
                continue
                
            # --- 重试机制 ---
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        log("重试", f"第 {attempt+1} 次尝试处理...", current_progress)
                        random_sleep(5, 10) # 重试前多等待
                    
                    # 执行单行处理逻辑
                    result = process_single_row(browser, row, index, total_rows, html_output_dir)
                    
                    # 更新数据
                    df.at[index, 'chords_URL'] = result['chords_URL']
                    df.at[index, 'chords_id'] = result['chords_id']
                    
                    success = True
                    break # 成功则跳出重试循环
                    
                except Exception as e:
                    log("异常", f"处理失败 (尝试 {attempt+1}/{max_retries}): {e}", current_progress)
                    traceback.print_exc()
                    # 遇到严重错误尝试重启浏览器标签页
                    try:
                        browser.close_tabs(others=False) # 关闭当前
                        browser.new_tab() # 新开一个
                    except:
                        pass
            
            if not success:
                log("失败", f"第 {index+1} 行处理最终失败，标记为Error", current_progress)
                df.at[index, 'chords_URL'] = "Error"
                df.at[index, 'chords_id'] = "Error"
            
            # --- 实时保存 ---
            if (index + 1) % 2 == 0: # 提高保存频率
                df.to_excel(excel_path, index=False)
                df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                log("保存", "数据已同步到磁盘", current_progress)
                
            # --- 任务间隔 ---
            random_sleep(3, 5)

    except KeyboardInterrupt:
        log("警告", "用户手动中断", 100)
    except Exception as e:
        log("错误", f"全局异常: {e}", 100)
    finally:
        log("结束", "正在保存最终结果并退出...", 100)
        try:
            df.to_excel(excel_path, index=False)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        except:
            pass
        if browser:
            browser.quit()

if __name__ == "__main__":
    main()
