import os
from google import genai
from google.genai import types

# 1. 初始化客户端
# 请确保已设置环境变量 GEMINI_API_KEY，或直接在代码中填入 API Key
client = genai.Client(api_key="AIzaSyC7xL96L-9KICQPwvyqlAfNmXaE7rIxgaA")

def get_nasdaq_index():
    model_id = "gemini-2.0-flash"  # 使用支持搜索功能的模型
    
    # 2. 配置工具：启用 Google 搜索
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ],
        temperature=0.0  # 设置为 0 以获得更准确的事实性数据
    )

    prompt = "查询并告诉我当前纳斯达克综合指数 (NASDAQ Composite) 的最新数值及其变动情况。"

    try:
        # 3. 发送请求
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config
        )

        # 4. 输出结果
        print("-" * 30)
        print("查询结果：")
        print(response.text)
        
        # 5. (可选) 输出参考来源
        if response.candidates[0].grounding_metadata.search_entry_point:
            print("\n数据来源：Google Search")
            
    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    get_nasdaq_index()