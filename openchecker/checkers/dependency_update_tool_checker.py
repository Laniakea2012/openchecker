import os
from platform_adapter import platform_manager
from typing import List, Optional, Dict, Any

COMMAND = 'dependency-update-tool-checker'

# 文件名到工具的映射
_FILE_TOOL_MAP = {
    "dependabot.yml": "Dependabot",
    "dependabot.yaml": "Dependabot",
    "renovate.json": "RenovateBot",
    "renovate.json5": "RenovateBot",
    ".renovaterc": "RenovateBot",
    ".renovaterc.json": "RenovateBot",
    ".renovaterc.json5": "RenovateBot",
    ".pyup.yml": "PyUp",
    ".scala-steward.conf": "scala-steward",
    "scala-steward.conf": "scala-steward",
}

# 工具信息表：统一管理所有工具的基本信息
_TOOL_INFOS = {
    "Dependabot": {
        "name": "Dependabot",
        "url": "https://github.com/dependabot",
        "desc": "Automated dependency updates built into GitHub"
    },
    "RenovateBot": {
        "name": "RenovateBot",
        "url": "https://github.com/renovatebot/renovate",
        "desc": "Automated dependency updates. Multi-platform and multi-language."
    },
    "PyUp": {
        "name": "PyUp",
        "url": "https://pyup.io/",
        "desc": "Automated dependency updates for Python."
    },
    "scala-steward": {
        "name": "scala-steward",
        "url": "https://github.com/scala-steward-org/scala-steward",
        "desc": "Works with Maven, Mill, sbt, and Scala CLI."
    }
}

# 动态生成最终的文件映射表
DEPENDENCY_UPDATE_TOOL_FILES = {
    filename: _TOOL_INFOS[tool_key]
    for filename, tool_key in _FILE_TOOL_MAP.items()
}



def _create_tool(
    name: str,
    url: Optional[str] = None,
    desc: Optional[str] = None,
    files: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    创建工具对象。
    
    参数：
        name: 工具名称
        url: 工具 URL
        desc: 工具描述
        files: 文件列表
        
    返回值：
        工具字典
    """
    return {
        "name": name,
        "url": url,
        "desc": desc,
        "files": files or []
    }


def _create_file(path: str, file_type: str = "source", offset: int = 0) -> Dict[str, Any]:
    """
    创建文件对象。
    
    参数：
        path: 文件路径
        file_type: 文件类型
        offset: 偏移量
        
    返回值：
        文件字典
    """
    return {
        "path": path,
        "file_type": file_type,
        "offset": offset
    }


def _normalize_filename(file_path: str) -> str:
    """规范化文件路径，只返回文件名部分。
    
    参数：
        file_path: 文件的完整路径或相对路径
        
    返回值：
        规范化后的文件名（仅文件名部分）
    """
    return os.path.basename(file_path)


def _check_dependency_files(repo_path: str) -> List[Dict[str, Any]]:
    """
    检查是否存在任何依赖更新工具配置文件。
    自动遍历仓库中的所有文件（包括深层文件夹），通过文件名匹配工具。
    同一工具的多个配置文件都会被记录。

    参数：
        repo_path: 仓库根目录的路径

    返回值：
        找到的工具列表
    """
    tools_dict = {}  
    
    if not os.path.isdir(repo_path):
        return []
    
    # 遍历仓库中的所有文件和文件夹，os.walk 会自动递归遍历所有深层目录
    for root, dirs, files in os.walk(repo_path):
        # 排除 .git 目录
        if '.git' in dirs:
            dirs.remove('.git')
        
        for file in files:
            normalized_filename = _normalize_filename(file)
            
            if normalized_filename in DEPENDENCY_UPDATE_TOOL_FILES:
                tool_info = DEPENDENCY_UPDATE_TOOL_FILES[normalized_filename]
                tool_name = tool_info["name"]
                
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                if tool_name not in tools_dict:
                    tools_dict[tool_name] = {
                        "info": tool_info,
                        "files": []
                    }
                
                tools_dict[tool_name]["files"].append(
                    _create_file(path=relative_path, file_type="source", offset=0)
                )
    
    tools = []
    for tool_name, data in tools_dict.items():
        tool_info = data["info"]
        tool = _create_tool(
            name=tool_name,
            url=tool_info["url"],
            desc=tool_info["desc"],
            files=data["files"]
        )
        tools.append(tool)
    
    print(tools)
    
    return tools


    

def dependency_update_tool_checker(project_url: str, res_payload: dict) -> None:
    """
    依赖关系更新工具检查
    指标详情介绍 https://github.com/ossf/scorecard/blob/main/docs/checks.md#dependency-update-tool
    """
    
    owner_name, repo_path = platform_manager.parse_project_url(project_url)
    dependency_tools = _check_dependency_files(repo_path)
    
    res_payload["scan_results"][COMMAND] = dependency_tools
