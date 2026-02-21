import sys
import os
import base64
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.comex_chart import ComexChartGenerator


def debug_chart():
    history_file = PROJECT_ROOT / "outputs" / "comex_history.json"
    if not history_file.exists():
        print(f"❌ 历史文件不存在: {history_file}")
        return

    generator = ComexChartGenerator(history_file)
    print("正在生成白银图表...")
    img_b64 = generator.generate_chart("silver")

    if not img_b64:
        print("❌ 图表生成失败")
        return

    print(f"✅ 图表生成成功!")
    print(f"Base64 长度: {len(img_b64)}")
    print(f"前 50 个字符: {img_b64[:50]}...")

    # 检查是否有换行符
    if "\n" in img_b64:
        print("⚠️ Base64 包含换_行符")
    else:
        print("ℹ️ Base64 不包含换行符")

    # 生成 HTML 测试文件
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>COMEX Chart Debug</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f0f0f0; }}
            .container {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            img {{ border: 1px solid #ccc; max-width: 100%; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>COMEX Silver Inventory Trend (Debug)</h1>
            <p>Generated at: {os.popen("date /t").read().strip()} {os.popen("time /t").read().strip()}</p>
            <hr>
            <h3>Image Tag:</h3>
            <img src="data:image/png;base64,{img_b64}" alt="Silver Chart">
            <hr>
            <h3>Raw Data URI Length: {len(img_b64)}</h3>
        </div>
    </body>
    </html>
    """

    output_path = PROJECT_ROOT / "tests" / "debug_chart.html"
    output_path.write_text(html_content, encoding="utf-8")
    print(f"✅ 测试 HTML 已生成: {output_path}")
    print("请在浏览器中打开此文件查看图片是否正常显示。")


if __name__ == "__main__":
    debug_chart()
