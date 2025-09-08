# Core Architecture

> **Relevant source files**
> * [openchecker/agent.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py)
> * [openchecker/constans.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py)

This document describes the fundamental architecture of the OpenChecker system, focusing on the agent-based processing model, message queue integration, and core workflow execution. The architecture centers around asynchronous task processing where agents consume project analysis requests from message queues and execute various security, compliance, and quality checkers.

For specific platform integrations and external service configurations, see [External Service Configuration](/Laniakea2012/openchecker/5.2-external-service-configuration). For details about specific analysis tools and checkers, see [Analysis Tools and Checkers](/Laniakea2012/openchecker/4-analysis-tools-and-checkers).

## System Overview

The OpenChecker core architecture implements a distributed agent-worker pattern where multiple `openchecker-agent` instances process project analysis tasks asynchronously. The system is designed around message-driven processing with robust error handling and automatic retry mechanisms.

### Core Processing Flow

```mermaid
sequenceDiagram
  participant RabbitMQ
  participant opencheck queue
  participant openchecker-agent
  participant callback_func
  participant shell_script_handlers
  participant Checker Modules
  participant NFS Storage
  participant repos_dir
  participant callback_url

  RabbitMQ->>openchecker-agent: "consume message"
  openchecker-agent->>NFS Storage: "download project source"
  openchecker-agent->>shell_script_handlers: "execute shell commands"
  shell_script_handlers-->>openchecker-agent: "command results"
  openchecker-agent->>Checker Modules: "execute python checkers"
  Checker Modules-->>openchecker-agent: "analysis results"
  openchecker-agent->>NFS Storage: "cleanup project files"
  openchecker-agent->>callback_url: "POST scan_results"
  openchecker-agent->>RabbitMQ: "acknowledge message"
```

Sources: [openchecker/agent.py L197-L298](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L197-L298)

## Agent System Architecture

The agent system is built around the `callback_func` function which serves as the main message processor. Each agent instance can handle multiple project analysis tasks concurrently through the message queue system.

### Agent Component Interaction

```mermaid
flowchart TD

CallbackFunc["callback_func<br>(agent.py:197)"]
ConfigReader["read_config<br>(helper module)"]
Logger["get_logger<br>(logger module)"]
CommandSwitch["command_switch<br>(agent.py:368-400)"]
ShellScriptHandler["shell_script_handlers<br>(constans.py:126)"]
ShellExec["shell_exec<br>(common module)"]
BinaryChecker["binary_checker"]
SonarChecker["sonar_checker"]
ReleaseChecker["release_checker"]
DocumentChecker["document_checker"]
StandardChecker["standard_command_checker"]
DownloadProject["_download_project_source<br>(agent.py:301)"]
GenerateLock["_generate_lock_files<br>(agent.py:331)"]
CleanupProject["_cleanup_project_source<br>(agent.py:480)"]
ProcessResult["_process_command_result<br>(agent.py:448)"]
SendResults["_send_results<br>(agent.py:500)"]
PostWithBackoff["post_with_backoff<br>(exponential_backoff)"]

CallbackFunc --> CommandSwitch
CommandSwitch --> BinaryChecker
CommandSwitch --> SonarChecker
CommandSwitch --> ReleaseChecker
CommandSwitch --> DocumentChecker
CommandSwitch --> StandardChecker
CallbackFunc --> DownloadProject
CallbackFunc --> GenerateLock
CallbackFunc --> CleanupProject
CallbackFunc --> ProcessResult
CallbackFunc --> SendResults

subgraph subGraph4 ["Result Processing"]
    ProcessResult
    SendResults
    PostWithBackoff
    SendResults --> PostWithBackoff
end

subgraph subGraph3 ["Project Management"]
    DownloadProject
    GenerateLock
    CleanupProject
end

subgraph subGraph2 ["Checker Modules"]
    BinaryChecker
    SonarChecker
    ReleaseChecker
    DocumentChecker
    StandardChecker
end

subgraph subGraph1 ["Command Execution"]
    CommandSwitch
    ShellScriptHandler
    ShellExec
    CommandSwitch --> ShellScriptHandler
    ShellScriptHandler --> ShellExec
end

subgraph subGraph0 ["Agent Core"]
    CallbackFunc
    ConfigReader
    Logger
    CallbackFunc --> ConfigReader
    CallbackFunc --> Logger
end
```

Sources: [openchecker/agent.py L197-L298](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L197-L298)

 [openchecker/agent.py L368-L400](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L368-L400)

 [openchecker/constans.py L126-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L126-L139)

## Command Processing Framework

The system implements a flexible command routing mechanism that supports both shell script-based tools and Python-based checker modules. Commands are executed based on a dispatch table that maps command names to their respective handlers.

### Command Types and Handlers

| Command Category | Handler Type | Examples |
| --- | --- | --- |
| Shell Script Commands | `_handle_shell_script_command` | `osv-scanner`, `scancode`, `dependency-checker` |
| Python Checker Modules | Direct function calls | `binary-checker`, `release-checker`, `sonar-scanner` |
| Standard Commands | `standard_command_checker` | `criticality-score`, `scorecard-score`, `code-count` |

```mermaid
flowchart TD

CommandList["command_list<br>(from message)"]
CommandSwitch["command_switch<br>(agent.py:368)"]
OSVScanner["osv-scanner"]
Scancode["scancode"]
DependencyChecker["dependency-checker"]
LanguagesDetector["languages-detector"]
OATScanner["oat-scanner"]
BinaryChecker["binary_checker"]
ReleaseChecker["release_checker"]
URLChecker["url_checker"]
SonarChecker["sonar_checker"]
ShellScriptHandlers["shell_script_handlers<br>(constans.py:126)"]
HandleShellScript["_handle_shell_script_command<br>(agent.py:413)"]
ShellExec["shell_exec"]

CommandSwitch --> OSVScanner
CommandSwitch --> Scancode
CommandSwitch --> DependencyChecker
CommandSwitch --> BinaryChecker
CommandSwitch --> ReleaseChecker
CommandSwitch --> URLChecker
CommandSwitch --> SonarChecker
OSVScanner --> HandleShellScript
Scancode --> HandleShellScript
DependencyChecker --> HandleShellScript

subgraph subGraph3 ["Shell Script Framework"]
    ShellScriptHandlers
    HandleShellScript
    ShellExec
    HandleShellScript --> ShellScriptHandlers
    HandleShellScript --> ShellExec
end

subgraph subGraph2 ["Python Checkers"]
    BinaryChecker
    ReleaseChecker
    URLChecker
    SonarChecker
end

subgraph subGraph1 ["Shell Script Commands"]
    OSVScanner
    Scancode
    DependencyChecker
    LanguagesDetector
    OATScanner
end

subgraph subGraph0 ["Command Dispatch"]
    CommandList
    CommandSwitch
    CommandList --> CommandSwitch
end
```

Sources: [openchecker/agent.py L368-L400](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L368-L400)

 [openchecker/agent.py L413-L446](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L413-L446)

 [openchecker/constans.py L126-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L126-L139)

## Project Lifecycle Management

Each project analysis follows a standardized lifecycle that ensures proper resource management and consistent processing across different project types.

### Project Processing Lifecycle

```mermaid
stateDiagram-v2
    [*] --> MessageReceived : "callback_func triggered"
    MessageReceived --> ValidateInput : "parse message body"
    ValidateInput --> DownloadSource : "_download_project_source"
    DownloadSource --> GenerateLockFiles : "_generate_lock_files"
    GenerateLockFiles --> ExecuteCommands : "_execute_commands"
    ExecuteCommands --> ProcessResults : "_process_command_result"
    ProcessResults --> CleanupFiles : "_cleanup_project_source"
    CleanupFiles --> SendCallback : "_send_results"
    SendCallback --> AckMessage : "ch.basic_ack"
    AckMessage --> [*] : "Task Complete"
    ValidateInput --> ErrorHandling : "download failed"
    DownloadSource --> ErrorHandling : "download failed"
    ExecuteCommands --> ErrorHandling : "command failed"
    SendCallback --> ErrorHandling : "callback failed"
    ErrorHandling --> NackMessage : "_handle_error_and_nack"
    NackMessage --> [*] : "Task Failed"
```

Sources: [openchecker/agent.py L197-L298](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L197-L298)

 [openchecker/agent.py L301-L329](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L301-L329)

 [openchecker/agent.py L331-L348](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L331-L348)

## Shell Script Execution Framework

The system includes a comprehensive shell script framework for executing external analysis tools. Scripts are templated and dynamically populated with project-specific parameters.

### Shell Script Template System

The `shell_script_handlers` dictionary in `constans.py` provides templated shell scripts for various analysis tools. Each script follows a consistent pattern:

1. **Project Name Extraction**: `_get_project_name()` extracts the project name from the URL
2. **Repository Cloning**: `_clone_project()` handles git cloning with optional depth limiting
3. **Tool Execution**: Tool-specific commands with standardized output handling
4. **Cleanup**: Removal of temporary files and directories

Example shell script structure for OSV scanner:

```markdown
# Project name extraction
project_name=$(basename {project_url} | sed 's/\.git$//')

# Clone repository with depth=1
if [ ! -e "$project_name" ]; then
    GIT_ASKPASS=/bin/true git clone --depth=1 {project_url}
fi

# Execute OSV scanner
osv-scanner --format json -r $project_name > $project_name/result.json
cat $project_name/result.json
```

Sources: [openchecker/constans.py L1-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L1-L139)

## Error Handling and Reliability

The architecture incorporates multiple layers of error handling and reliability mechanisms:

### Error Handling Strategy

* **Message Acknowledgment**: Successful tasks are acknowledged (`ch.basic_ack`), failed tasks are negative acknowledged (`ch.basic_nack`)
* **Dead Letter Queue**: Failed messages are routed to dead letter queue for manual inspection
* **Exponential Backoff**: HTTP callbacks use exponential backoff retry mechanism via `post_with_backoff`
* **Working Directory Management**: Ensures proper cleanup and restoration of working directory state
* **Resource Cleanup**: Automatic cleanup of downloaded project files regardless of task outcome

For detailed information about specific reliability mechanisms, see [Reliability and Error Handling](/Laniakea2012/openchecker/2.4-reliability-and-error-handling). For message queue integration details, see [Message Queue Integration](/Laniakea2012/openchecker/2.2-message-queue-integration).

Sources: [openchecker/agent.py L519-L531](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L519-L531)

 [openchecker/agent.py L177-L194](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L177-L194)

 [openchecker/agent.py L289-L298](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L289-L298)