# Agent System and Message Processing

> **Relevant source files**
> * [openchecker/agent.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py)
> * [openchecker/constans.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py)
> * [scripts/binary_checker.sh](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh)

This document covers the core agent system that processes project analysis tasks through asynchronous message consumption. The agent system is responsible for receiving project check requests from the message queue, executing various analysis tools and checkers, and returning results via callbacks. This includes the message processing workflow, shell script execution framework, and project source management.

For information about the message queue infrastructure and RabbitMQ configuration, see [Message Queue Integration](/Laniakea2012/openchecker/2.2-message-queue-integration). For details on the REST API that publishes tasks to the queue, see [REST API Server](/Laniakea2012/openchecker/3.1-rest-api-server).

## Agent Architecture Overview

The agent system is built around a central callback function that processes messages from RabbitMQ and orchestrates the execution of various analysis tools.

```mermaid
flowchart TD

consumer["message_queue.consumer()"]
callback_func["callback_func()"]
command_switch["command_switch{}"]
shell_script_handlers["shell_script_handlers{}"]
download["_download_project_source()"]
generate_lock["_generate_lock_files()"]
cleanup["_cleanup_project_source()"]
process_result["_process_command_result()"]
send_results["_send_results()"]
request_url["request_url()"]
rabbitmq["RabbitMQ opencheck queue"]
callback_url["callback_url endpoint"]
git_repos["Git Repositories"]
python_checkers["Python Checkers"]
shell_scripts["Shell Script Tools"]

rabbitmq --> consumer
command_switch --> python_checkers
shell_script_handlers --> shell_scripts
request_url --> callback_url
download --> git_repos

subgraph subGraph5 ["Analysis Tools"]
    python_checkers
    shell_scripts
end

subgraph subGraph4 ["External Systems"]
    rabbitmq
    callback_url
    git_repos
end

subgraph subGraph3 ["Agent Process"]
    consumer
    callback_func
    consumer --> callback_func
    callback_func --> download
    callback_func --> generate_lock
    callback_func --> command_switch
    callback_func --> process_result
    callback_func --> send_results
    callback_func --> cleanup

subgraph subGraph2 ["Result Processing"]
    process_result
    send_results
    request_url
    send_results --> request_url
end

subgraph subGraph1 ["Project Management"]
    download
    generate_lock
    cleanup
end

subgraph subGraph0 ["Command Execution Engine"]
    command_switch
    shell_script_handlers
    command_switch --> shell_script_handlers
end
end
```

Sources: [openchecker/agent.py L197-L581](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L197-L581)

 [openchecker/agent.py L53](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L53-L53)

 [openchecker/constans.py L126-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L126-L139)

## Message Processing Workflow

The `callback_func` serves as the main entry point for processing project analysis requests from the message queue.

```mermaid
sequenceDiagram
  participant RabbitMQ
  participant callback_func
  participant Project Management
  participant Command Execution
  participant Result Processing
  participant callback_url

  RabbitMQ->>callback_func: "message body with project_url, command_list"
  callback_func->>callback_func: "json.loads(body.decode('utf-8'))"
  callback_func->>Project Management: "_download_project_source(project_url, version_number)"
  Project Management-->>callback_func: "download success/failure"
  loop ["for command in command_list"]
    callback_func->>Project Management: "_generate_lock_files(project_url)"
    callback_func->>Command Execution: "_execute_commands(command_list, project_url, res_payload)"
    Command Execution->>Command Execution: "command_switch<FileRef file-url='https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/command' undefined  file-path='command'>Hii</FileRef>"
    callback_func->>Result Processing: "_process_command_result(command, result)"
    callback_func->>Project Management: "_cleanup_project_source(project_url)"
    callback_func->>Result Processing: "_send_results(callback_url, res_payload)"
    Result Processing->>callback_url: "post_with_backoff(url, json=payload)"
    callback_func->>RabbitMQ: "ch.basic_ack(delivery_tag=method.delivery_tag)"
    callback_func->>callback_func: "_handle_error_and_nack(ch, method, body, error_msg)"
    callback_func->>RabbitMQ: "ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)"
  end
```

Sources: [openchecker/agent.py L197-L299](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L197-L299)

 [openchecker/agent.py L351-L411](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L351-L411)

 [openchecker/agent.py L519-L531](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L519-L531)

## Shell Script Handler System

The agent system uses a template-based shell script framework defined in `constans.py` to execute external analysis tools consistently.

| Handler Name | Purpose | Shell Script Template |
| --- | --- | --- |
| `download-checkout` | Download and checkout project source | `download_checkout_shell_script` |
| `generate-lock_files` | Generate package lock files | `generate_lock_files_shell_script` |
| `osv-scanner` | Vulnerability scanning | `osv_scanner_shell_script` |
| `scancode` | License analysis | `scancode_shell_script` |
| `dependency-checker` | Dependency analysis | `dependency_checker_shell_script` |
| `oat-scanner` | OpenHarmony audit | `oat_scanner_shell_script` |
| `remove-source-code` | Cleanup project files | `remove_source_code_shell_script` |

The shell script handlers use a base script template that includes project name extraction and git cloning:

```mermaid
flowchart TD

shell_script_handlers["shell_script_handlers{}"]
BASE_SCRIPT["BASE_SCRIPT template"]
format_operation[".format(project_url=project_url)"]
get_project_name["_get_project_name()"]
clone_project["_clone_project()"]
tool_specific["Tool-specific commands"]
shell_exec["shell_exec()"]
result_processing["Result processing"]

BASE_SCRIPT --> get_project_name
BASE_SCRIPT --> clone_project
format_operation --> tool_specific
tool_specific --> shell_exec

subgraph Execution ["Execution"]
    shell_exec
    result_processing
    shell_exec --> result_processing
end

subgraph subGraph1 ["Script Components"]
    get_project_name
    clone_project
    tool_specific
end

subgraph subGraph0 ["Shell Script Generation"]
    shell_script_handlers
    BASE_SCRIPT
    format_operation
    shell_script_handlers --> format_operation
end
```

Sources: [openchecker/constans.py L1-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L1-L139)

 [openchecker/agent.py L413-L446](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L413-L446)

 [openchecker/agent.py L48](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L48-L48)

## Command Execution Framework

The agent uses a command switch dictionary to map command names to their corresponding execution functions, supporting both Python-based checkers and shell script handlers.

```mermaid
flowchart TD

command_switch["command_switch = {}"]
binary_checker["binary_checker()"]
release_checker["release_checker()"]
url_checker["url_checker()"]
sonar_checker["sonar_checker()"]
api_doc_checker["api_doc_checker()"]
criticality_score_checker["criticality_score_checker()"]
handle_shell_script["_handle_shell_script_command()"]
osv_scanner["osv-scanner"]
scancode["scancode"]
dependency_checker["dependency-checker"]
oat_scanner["oat-scanner"]

command_switch --> binary_checker
command_switch --> release_checker
command_switch --> url_checker
command_switch --> sonar_checker
command_switch --> api_doc_checker
command_switch --> criticality_score_checker
command_switch --> handle_shell_script

subgraph subGraph2 ["Shell Script Handlers"]
    handle_shell_script
    osv_scanner
    scancode
    dependency_checker
    oat_scanner
    handle_shell_script --> osv_scanner
    handle_shell_script --> scancode
    handle_shell_script --> dependency_checker
    handle_shell_script --> oat_scanner
end

subgraph subGraph1 ["Python Checkers"]
    binary_checker
    release_checker
    url_checker
    sonar_checker
    api_doc_checker
    criticality_score_checker
end

subgraph subGraph0 ["Command Router"]
    command_switch
end
```

The command execution loop processes each command in the `command_list` and handles exceptions gracefully:

```xml
for command in command_list:
    if command in command_switch:
        try:
            command_switch<FileRef file-url="https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/command" undefined  file-path="command">Hii</FileRef>
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            res_payload["scan_results"][command] = {"error": str(e)}
    else:
        logger.warning(f"Unknown command: {command}")
```

Sources: [openchecker/agent.py L368-L411](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L368-L411)

 [openchecker/agent.py L413-L446](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L413-L446)

## Project Source Management

The agent manages project source code through a three-phase lifecycle: download, processing, and cleanup.

### Download Phase

The `_download_project_source` function uses the `download-checkout` shell script template to clone repositories and optionally checkout specific versions:

```
shell_script = shell_script_handlers["download-checkout"].format(
    project_url=project_url, 
    version_number=version_number
)
result, error = shell_exec(shell_script)
```

### Lock File Generation

The `_generate_lock_files` function creates package lock files for Node.js and OpenHarmony projects:

* Detects `package.json` and generates `package-lock.json` via `npm install`
* Detects `oh-package.json5` and generates `oh-package-lock.json5` via `ohpm install`

### Cleanup Phase

The `_cleanup_project_source` function removes project directories after analysis completion using the `remove-source-code` shell script template.

Sources: [openchecker/agent.py L301-L329](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L301-L329)

 [openchecker/agent.py L331-L349](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L331-L349)

 [openchecker/agent.py L480-L498](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L480-L498)

 [openchecker/constans.py L12-L35](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L12-L35)

## Result Processing and Callbacks

The agent processes command results based on the command type and sends formatted results to the callback URL.

### Result Processing Pipeline

```mermaid
flowchart TD

raw_result["Raw command result"]
process_command_result["_process_command_result()"]
json_commands["JSON commands check"]
dependency_processor["dependency_checker_output_process()"]
oat_parser["parse_oat_txt_to_json()"]
default_return["Return raw string"]
json_output["JSON output"]
processed_deps["Processed dependencies"]
oat_json["OAT JSON format"]
string_output["String output"]

json_commands --> json_output
dependency_processor --> processed_deps
oat_parser --> oat_json
default_return --> string_output

subgraph subGraph2 ["Output Formats"]
    json_output
    processed_deps
    oat_json
    string_output
end

subgraph subGraph1 ["Result Processing"]
    raw_result
    process_command_result
    raw_result --> process_command_result
    process_command_result --> json_commands
    process_command_result --> dependency_processor
    process_command_result --> oat_parser
    process_command_result --> default_return

subgraph subGraph0 ["Processing Logic"]
    json_commands
    dependency_processor
    oat_parser
    default_return
end
end
```

### Callback Mechanism

Results are sent to the `callback_url` using exponential backoff retry logic:

```python
def _send_results(callback_url: str, res_payload: Dict[str, Any]) -> None:
    if callback_url:
        try:
            response, err = request_url(callback_url, res_payload)
            if err is None:
                logger.info("Results sent successfully")
            else:
                logger.error(f"Failed to send results: {err}")
```

The `request_url` function wraps `post_with_backoff` for reliable HTTP delivery.

Sources: [openchecker/agent.py L448-L478](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L448-L478)

 [openchecker/agent.py L500-L517](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L500-L517)

 [openchecker/agent.py L177-L194](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L177-L194)

 [openchecker/agent.py L138-L175](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L138-L175)