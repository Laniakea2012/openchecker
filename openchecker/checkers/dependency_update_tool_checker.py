import os
from platform_adapter import platform_manager
from typing import List, Optional, Dict, Any
from common import get_platform_type

COMMAND = 'dependency-update-tool-checker'


def get_dependency_update_tool_files(platform_type: str) -> Dict[str, Any]:
    # 依赖更新工具配置文件
    dependency_update_tool_files_map = {
        # Dependabot
        ".github/dependabot.yml": {
            "name": "Dependabot",
            "url": "https://github.com/dependabot",
            "desc": "Automated dependency updates built into GitHub"
        },
        ".github/dependabot.yaml": {
            "name": "Dependabot",
            "url": "https://github.com/dependabot",
            "desc": "Automated dependency updates built into GitHub"
        },
        # RenovateBot
        "renovate.json": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        "renovate.json5": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        f"{platform_type}/renovate.json": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        f"{platform_type}/renovate.json5": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        ".renovaterc": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        ".renovaterc.json": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        ".renovaterc.json5": {
            "name": "RenovateBot",
            "url": "https://github.com/renovatebot/renovate",
            "desc": "Automated dependency updates. Multi-platform and multi-language."
        },
        # PyUp
        ".pyup.yml": {
            "name": "PyUp",
            "url": "https://pyup.io/",
            "desc": "Automated dependency updates for Python."
        },
        # scala-steward
        ".scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
        "scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
        f"{platform_type}/.scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
        f"{platform_type}/scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
        ".config/.scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
        ".config/scala-steward.conf": {
            "name": "scala-steward",
            "url": "https://github.com/scala-steward-org/scala-steward",
            "desc": "Works with Maven, Mill, sbt, and Scala CLI."
        },
    }
    return dependency_update_tool_files_map


def create_tool(
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


def create_file(path: str, file_type: str = "source", offset: int = 0) -> Dict[str, Any]:
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


def _check_dependency_files(repo_path: str, platform_type: str) -> List[Dict[str, Any]]:
    """
    检查是否存在任何依赖更新工具配置文件。

    参数：
        repo_path: 仓库根目录的路径

    返回值：
        找到的工具列表
    """
    tools = []
    found_tool_names = set()

    for file_path, tool_info in get_dependency_update_tool_files(platform_type).items():
        full_path = os.path.join(repo_path, file_path)

        if os.path.exists(full_path):
            tool_name = tool_info["name"]

            # 避免重复 (仅添加每个工具的第一个出现)
            if tool_name not in found_tool_names:
                tool = create_tool(
                    name=tool_name,
                    url=tool_info["url"],
                    desc=tool_info["desc"],
                    files=[create_file(path=file_path, file_type="source", offset=0)]
                )
                tools.append(tool)
                found_tool_names.add(tool_name)

    return tools


    

def dependency_update_tool_checker(project_url: str, res_payload: dict) -> None:
    """
    依赖关系更新工具检查
    指标详情介绍 https://github.com/ossf/scorecard/blob/main/docs/checks.md#dependency-update-tool
    """
    
    owner_name, repo_path = platform_manager.parse_project_url(project_url)
    platform_type = get_platform_type(project_url)
    dependency_tools = _check_dependency_files(repo_path, platform_type)
    
    res_payload["scan_results"][COMMAND] = dependency_tools
