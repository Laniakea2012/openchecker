import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Any

def shell_exec(shell_script, param=None):
    if param != None:
        process = subprocess.Popen(["/bin/bash", "-c", shell_script + " " + param], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    else:
        process = subprocess.Popen([shell_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    shell_output, error = process.communicate()

    if process.returncode == 0:
        return shell_output, None
    else:
        return None, error

def get_platform_type(url):
    """
    根据URL判断代码托管平台类型
    """
    if "github.com" in url:
        return "github"
    elif "gitee.com" in url:
        return "gitee"
    elif "gitcode.com" in url:
        return "gitcode"
    else:
        return "github"
    

def list_workflow_files(repo_path: str, platform_type: str) -> List[str]:
    """
    扫描并返回所有工作流文件路径
    
    Args:
        repo_path: 仓库根目录路径
        
    Returns:
        工作流文件路径列表
    """
    workflow_files = []
    if platform_type == "gitee":
        workflows_dir = Path(repo_path) / ".workflows"
    else:
        workflows_dir = Path(repo_path) / f".{platform_type}" / "workflows"
    if workflows_dir.exists():
        for file_path in workflows_dir.glob("*.yml"):
            workflow_files.append(str(file_path))
        for file_path in workflows_dir.glob("*.yaml"):
            workflow_files.append(str(file_path))
    
    return workflow_files