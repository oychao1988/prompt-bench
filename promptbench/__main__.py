# promptbench/__main__.py
"""
PromptBench 包主入口点

支持 python -m promptbench 执行方式
"""

from promptbench.cli.main import CLI

if __name__ == "__main__":
    CLI.main()
