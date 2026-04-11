from basic_pitch.inference import predict_and_save
from pathlib import Path

# 1. 配置路径
# 请确保你的 m4a 文件和脚本在同一文件夹，或者使用绝对路径
audio_path_list = [Path(r"D:\Download\temp\世界贈予我的.m4a")]
output_directory = Path(r"D:\Download\temp\midi_out")
# 2. 创建输出目录
output_directory.mkdir(exist_ok=True)

print("正在识别并转换中，这可能需要一点时间...")

try:
    # 3. 执行转换
    # save_midi: 是否保存为 midi
    # sonify_midi: 是否生成合成后的音频（可选）
    # save_model_outputs: 是否保存模型原始输出（可选）
    predict_and_save(
        audio_path_list=audio_path_list,
        output_directory=output_directory,
        save_midi=True,
        sonify_midi=False,
        save_model_outputs=False,
        save_notes=False
    )
    print(f"转换成功！MIDI 文件已保存在: {output_directory}")

except Exception as e:
    print(f"转换过程中出错: {e}")