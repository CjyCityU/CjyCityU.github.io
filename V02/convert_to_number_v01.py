import pandas as pd
import sys
import signal
import traceback
import os
import music21
import re

# 全局变量控制运行状态
running = True

def signal_handler(sig, frame):
    """
    处理 Ctrl+C 中断信号
    """
    global running
    print("\n[中断] 接收到中断信号，正在安全退出...")
    running = False

def log_step(step_name, percentage, description):
    """
    输出当前执行步骤、进度和描述
    """
    print(f"[{percentage}%] {step_name}: {description}")

def convert_chord_to_number(chord_str, key_str):
    """
    使用 music21 将和弦转换为相对于 Key 的罗马数字/Nashville Number
    """
    if not chord_str or not key_str:
        return chord_str
    
    try:
        # 1. 解析 Key
        k_str = str(key_str).replace('min', 'm').replace('Min', 'm').replace('Minor', 'm').replace('Major', 'M')
        
        try:
            # music21 Key parsing is case sensitive and strict
            # Clean up: "C Major" -> "C" (music21 default major)
            # "A Minor" -> "a" or "Am"
            # 简单处理：如果是 "C", "C#", "Db" 这种，music21.key.Key('C') 默认是 C Major
            # 如果是 "Cm", "C min" -> music21.key.Key('c') (小写表示小调)
            
            # 我们先尝试解析出根音和模式
            key_match = re.match(r'^([A-G][#b]?)(.*)$', k_str, re.IGNORECASE)
            if key_match:
                root = key_match.group(1).title() # 首字母大写，如 C, C#
                suffix = key_match.group(2).lower()
                
                mode = 'major'
                if 'm' in suffix and 'aj' not in suffix: # 包含 m 但不是 maj -> minor
                    mode = 'minor'
                
                key_obj = music21.key.Key(root, mode)
            else:
                 return chord_str

        except Exception as e:
            # print(f"Key Error: {e}")
            return chord_str
            
        # 2. 解析 Chord
        c_str = chord_str.strip()
        
        try:
            # 尝试作为和弦符号解析 (比如 "Am7")
            c = music21.harmony.ChordSymbol(c_str)
        except:
            try:
                # 尝试作为普通和弦解析 (比如 "C-E-G") - 不太可能，这里通常是符号
                # 或者简单的 "C", "Am"
                # music21.chord.Chord("C") 会生成 C Major 和弦
                c = music21.chord.Chord(c_str)
            except:
                return chord_str
            
        # 3. 计算半音数
        try:
            # 获取和弦根音
            c_root = c.root()
            # 获取 Key 主音
            k_tonic = key_obj.tonic
            
            # 计算音程
            interval = music21.interval.Interval(k_tonic, c_root)
            semitones = interval.semitones % 12
        except Exception as e:
            # print(f"Interval Error: {e}")
            return chord_str

        mapping = {
            0: '1',
            1: 'b2',
            2: '2',
            3: 'b3',
            4: '3',
            5: '4',
            6: 'b5', 
            7: '5',
            8: 'b6',
            9: '6',
            10: 'b7',
            11: '7'
        }
        
        base_num = mapping.get(semitones, '?')
        
        # 提取后缀
        match = re.match(r'^([A-G][#b]?)(.*)$', chord_str)
        if match:
            original_suffix = match.group(2)
            return f"{base_num}{original_suffix}"
        else:
            return base_num

    except Exception as e:
        # print(f"Error converting {chord_str} in {key_str}: {e}")
        return chord_str

def process_row(row):
    """
    处理单行数据
    """
    key = row.get('Key')
    chords_str = row.get('Chords')
    
    if pd.isna(key) or pd.isna(chords_str):
        return None
        
    # 分割和弦
    chords = [c.strip() for c in str(chords_str).split(',') if c.strip()]
    
    converted_chords = []
    for chord in chords:
        num_chord = convert_chord_to_number(chord, key)
        converted_chords.append(num_chord)
        
    return ", ".join(converted_chords)

def main():
    global running
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    excel_path = r'd:\Files\proj\coding\music_analysis02\billboard_hot100_2025_v02.xlsx'
    
    try:
        log_step("初始化", 0, "正在检查文件...")
        if not os.path.exists(excel_path):
            print(f"Excel 文件不存在: {excel_path}")
            return

        # 检查文件占用
        try:
            with open(excel_path, 'a'):
                pass
        except PermissionError:
            print(f"错误: 文件 {excel_path} 被占用，请关闭后重试。")
            return

        log_step("读取数据", 10, "正在加载 Excel 文件...")
        df = pd.read_excel(excel_path)
        
        # 确保列存在
        if 'Chords-num' not in df.columns:
            df['Chords-num'] = None
            
        total_rows = len(df)
        log_step("开始处理", 20, f"共 {total_rows} 行数据，开始转换...")
        
        for index, row in df.iterrows():
            if not running:
                break
                
            # 进度显示
            if index % 10 == 0:
                percent = 20 + int((index / total_rows) * 70)
                log_step("转换中", percent, f"正在处理第 {index + 1}/{total_rows} 行...")
            
            try:
                converted = process_row(row)
                if converted:
                    df.at[index, 'Chords-num'] = converted
            except Exception as e:
                print(f"Warning: 行 {index + 1} 处理出错: {e}")
                continue
                
        if running:
            log_step("保存文件", 90, "正在保存结果...")
            try:
                df.to_excel(excel_path, index=False)
                log_step("完成", 100, "处理完成，结果已保存。")
            except PermissionError:
                print(f"保存失败: 文件 {excel_path} 被占用。")
        else:
            print("操作已取消，未保存更改。")

    except Exception as e:
        print(f"发生严重错误: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
