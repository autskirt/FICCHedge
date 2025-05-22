
import streamlit.web.cli as stcli
import sys
import os

if __name__ == '__main__':
    # 设置工作目录为 exe 文件所在目录
    if hasattr(sys, '_MEIPASS'):
        os.chdir(sys._MEIPASS)
    
    # 启动 Streamlit
    sys.argv = [
        "streamlit", 
        "run", 
        "app.py",
        "--server.port=8501",
        "--server.address=localhost",
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ]
    sys.exit(stcli.main())
