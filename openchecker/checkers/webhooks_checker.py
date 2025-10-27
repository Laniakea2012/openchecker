import re
import requests
import os
from typing import Any, List, Dict


COMMAND = 'webhooks-checker'


def get_webhooks(project_url, access_token):
    """
    获取所有仓库webhooks, 支持github.com, gitee.com, gitcode.com。
    """

    owner_name = re.match(r"https://(?:github|gitee|gitcode).com/([^/]+)/", project_url).group(1)
    repo_name = re.sub(r'\.git$', '', os.path.basename(project_url))

    if "github.com" in project_url:
        url = f"https://api.github.com/repos/{owner_name}/{repo_name}/hooks?&page=1&per_page=100"
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': f'token {access_token}'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                hooks = response.json()
                return hooks, None
            else:
                return [], "token invalid"
        except Exception as e:
            return [], "token invalid"

    elif "gitee.com" in project_url or "gitcode.com" in project_url:
        if "gitee.com" in project_url:
            url = f"https://gitee.com/api/v5/repos/{owner_name}/{repo_name}/hooks?access_token={access_token}&page=1&per_page=100"
        else:
            url = f"https://api.gitcode.com/api/v5/repos/{owner_name}/{repo_name}/hooks?access_token={access_token}&page=1&per_page=100"
        try:
            headers = {
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                hooks = response.json()
                return hooks, None
            else:
                return [], "token invalid"
        except Exception as e:
            return [], "token invalid"

    else:
        return [], "Not supported platform."


def webhooks_checker(project_url: str, res_payload: dict, access_token: str) -> None:
    """
    检查项目webhooks,
    指标详情介绍 https://github.com/ossf/scorecard/blob/main/docs/checks.md#webhooks
    """
    
    webhooks_hooks = []
    error_msg = None
    
    if access_token:
        hooks, error_msg = get_webhooks(project_url, access_token)
        if error_msg is None:
            webhooks_hooks = [
                {**hook, "password": "******"} 
                if hook.get("password") else hook for hook in hooks
            ]
    
    res_payload["scan_results"][COMMAND] = {
        "access_token": True if access_token else False,
        "error_msg": error_msg,
        "webhooks_hooks": webhooks_hooks
    }