# Checker Framework and Execution

> **Relevant source files**
> * [openchecker/checkers/binary_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py)
> * [openchecker/checkers/changed_files_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py)
> * [openchecker/checkers/document_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py)
> * [openchecker/checkers/release_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py)
> * [openchecker/checkers/sonar_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py)
> * [openchecker/checkers/url_checker.py](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py)

This document covers the checker execution framework that runs individual analysis tools and Python modules within the OpenChecker agent system. It explains how commands are dispatched, how different types of checkers are executed, and how results are processed and aggregated.

For information about the container environment and tool installation, see [Container Environment and Tool Installation](/Laniakea2012/openchecker/4.1-container-environment-and-tool-installation). For details about specific security and compliance checkers, see [Security and Compliance Analysis](/Laniakea2012/openchecker/4.3-security-and-compliance-analysis).

## Checker Execution Framework Overview

The checker framework operates as a command dispatcher within the agent's message processing workflow. When a message is received from the RabbitMQ queue, the agent extracts a `command_list` and executes each checker sequentially, aggregating results into a unified response payload.

```

```

Sources: [openchecker/agent.py L351-L411](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L351-L411)

## Command Dispatch Mechanism

The core dispatcher uses a command switch dictionary that maps command names to their execution functions. This design allows for easy extension of new checkers while maintaining a consistent execution interface.

### Command Switch Dictionary

The `command_switch` dictionary in `_execute_commands` provides the mapping between command names and their execution functions:

| Command Type | Example Commands | Execution Method |
| --- | --- | --- |
| Python Functions | `binary-checker`, `release-checker`, `url-checker` | Direct function calls with lambda wrappers |
| Shell Scripts | `osv-scanner`, `scancode`, `dependency-checker` | `_handle_shell_script_command()` with command name |
| Specialized | `sonar-scanner`, `criticality-score` | Custom functions with configuration parameters |

```

```

Sources: [openchecker/agent.py L368-L400](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L368-L400)

## Python-Based Checkers

Python-based checkers are implemented as individual modules under the `checkers/` directory. Each checker follows a consistent interface pattern and directly manipulates the response payload.

### Checker Interface Pattern

All Python checkers follow this interface:

* **Function signature**: `checker_name(project_url: str, res_payload: dict, *optional_params)`
* **Result storage**: Updates `res_payload["scan_results"][command_name]` directly
* **Error handling**: Stores error information in the same result structure

### File Change Detection Checker

The `changed_files_detector` analyzes git history to identify file modifications since a specific commit:

```

```

Sources: [openchecker/checkers/changed_files_checker.py L10-L52](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/changed_files_checker.py#L10-L52)

### URL Accessibility Checker

The `url_checker` performs simple HTTP accessibility validation:

```mermaid
flowchart TD

UrlChecker["url_checker()"]
HttpRequest["requests.get(project_url, timeout=10)"]
CheckStatus["response.status_code == 200?"]
StoreSuccess["Store status_code and is_accessible=True"]
StoreFailure["Store status_code and is_accessible=False"]
UpdatePayload["Update res_payload['scan_results']['url-checker']"]

UrlChecker --> HttpRequest
HttpRequest --> CheckStatus
CheckStatus --> StoreSuccess
CheckStatus --> StoreFailure
StoreSuccess --> UpdatePayload
StoreFailure --> UpdatePayload
```

Sources: [openchecker/checkers/url_checker.py L8-L25](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/url_checker.py#L8-L25)

### Document Analysis with AI Integration

The document checker system includes sophisticated AI-powered analysis for documentation quality:

```mermaid
flowchart TD

DocChecker["Document Checker System"]
ApiDocChecker["api_doc_checker()"]
BuildDocChecker["build_doc_checker()"]
ReadmeChecker["readme_opensource_checker()"]
CheckDocContent["check_doc_content(project_url, 'api-doc')"]
CheckDocContent2["check_doc_content(project_url, 'build-doc')"]
CloneRepo["git clone project"]
FindDocs["Search doc/, docs/, and root for .md/.markdown"]
ChunkText["Split documents into 3000-char chunks"]
LLMAnalysis["completion_with_backoff() with AI templates"]
CheckResponse["AI response == 'YES'?"]
DocumentSatisfied["Add to satisfied_doc_file list"]
NextChunk["Process next chunk"]
CheckReadmeFile["Check README.OpenSource exists"]
ValidateJSON["json.load() and validate structure"]
CheckRequiredKeys["Validate required keys: Name, License, etc."]

DocChecker --> ApiDocChecker
DocChecker --> BuildDocChecker
DocChecker --> ReadmeChecker
ApiDocChecker --> CheckDocContent
BuildDocChecker --> CheckDocContent2
CheckDocContent --> CloneRepo
CheckDocContent --> FindDocs
FindDocs --> ChunkText
ChunkText --> LLMAnalysis
LLMAnalysis --> CheckResponse
CheckResponse --> DocumentSatisfied
CheckResponse --> NextChunk
ReadmeChecker --> CheckReadmeFile
CheckReadmeFile --> ValidateJSON
ValidateJSON --> CheckRequiredKeys
```

Sources: [openchecker/checkers/document_checker.py L11-L200](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/document_checker.py#L11-L200)

### Binary File Detection

The `binary_checker` identifies binary files and archives within projects:

```mermaid
flowchart TD

BinaryChecker["binary_checker()"]
GetScript["Get binary_checker.sh script path"]
ShellExec["shell_exec(script, project_url)"]
ParseOutput["Parse shell output"]
ProcessResults["Process binary_file_list and binary_archive_list"]
UpdatePayload["Update res_payload['scan_results']['binary-checker']"]
ErrorCheck["error is None?"]
ErrorResult["Store error in res_payload"]

BinaryChecker --> GetScript
GetScript --> ShellExec
ShellExec --> ParseOutput
ParseOutput --> ProcessResults
ProcessResults --> UpdatePayload
ShellExec --> ErrorCheck
ErrorCheck --> ErrorResult
ErrorCheck --> ProcessResults
```

Sources: [openchecker/checkers/binary_checker.py L9-L42](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/binary_checker.py#L9-L42)

### SonarQube Integration

The `sonar_checker` provides comprehensive code quality analysis through SonarQube integration:

```mermaid
flowchart TD

SonarChecker["sonar_checker()"]
ParseProjectUrl["platform_manager.parse_project_url()"]
CreateProjectName["Format: platform_organization_project"]
CheckProjectExists["_check_sonar_project_exists()"]
CreateProject["_create_sonar_project()"]
RunScanner["Execute sonar-scanner shell script"]
WaitProcessing["Wait 30 seconds for data processing"]
QueryMeasures["_query_sonar_measures()"]
GetMetrics["Get coverage, complexity, duplicated_lines_density, lines"]
UpdatePayload["Update res_payload['scan_results']['sonar-scanner']"]

SonarChecker --> ParseProjectUrl
ParseProjectUrl --> CreateProjectName
CreateProjectName --> CheckProjectExists
CheckProjectExists --> CreateProject
CheckProjectExists --> RunScanner
CreateProject --> RunScanner
RunScanner --> WaitProcessing
WaitProcessing --> QueryMeasures
QueryMeasures --> GetMetrics
GetMetrics --> UpdatePayload
```

Sources: [openchecker/checkers/sonar_checker.py L14-L173](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/sonar_checker.py#L14-L173)

### Release Content Analysis

The release checker demonstrates integration with platform adapters and complex result processing:

```mermaid
flowchart TD

ReleaseChecker["release_checker()"]
CheckNotes["check_release_contents('notes')"]
CheckSBOM["check_release_contents('sbom')"]
CheckSigned["check_signed_release()"]
PlatformAdapter["platform_manager.get_releases()"]
ProcessReleases["Process release data"]
DownloadZip["Download and analyze release archives"]
UpdateResults["Update res_payload['scan_results']['release-checker']"]

ReleaseChecker --> CheckNotes
ReleaseChecker --> CheckSBOM
ReleaseChecker --> CheckSigned
CheckNotes --> PlatformAdapter
CheckSBOM --> PlatformAdapter
CheckSigned --> PlatformAdapter
PlatformAdapter --> ProcessReleases
ProcessReleases --> DownloadZip
DownloadZip --> UpdateResults
```

Sources: [openchecker/checkers/release_checker.py L255-L282](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/checkers/release_checker.py#L255-L282)

## Shell Script Command Execution

External tools are executed via shell scripts defined in the `shell_script_handlers` dictionary. This approach provides flexibility for integrating diverse analysis tools with different command-line interfaces.

### Shell Script Handler Architecture

```mermaid
flowchart TD

HandleShellScript["_handle_shell_script_command()"]
LookupScript["shell_script_handlers[command]"]
FormatScript["Format script with project_url"]
ShellExec["shell_exec(shell_script)"]
ProcessResult["_process_command_result()"]
UpdatePayload["Update res_payload"]
ErrorCheck["error is None?"]
StoreError["Store error in res_payload"]

HandleShellScript --> LookupScript
LookupScript --> FormatScript
FormatScript --> ShellExec
ShellExec --> ProcessResult
ProcessResult --> UpdatePayload
ShellExec --> ErrorCheck
ErrorCheck --> StoreError
ErrorCheck --> ProcessResult
```

Sources: [openchecker/agent.py L413-L446](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L413-L446)

### Shell Script Templates

The shell scripts in `constans.py` use template strings with placeholders for dynamic values:

| Tool | Script Template | Key Operations |
| --- | --- | --- |
| `osv-scanner` | `osv_scanner_shell_script` | Clone, rename lock files, run scanner, output JSON |
| `scancode` | `scancode_shell_script` | Clone, run scancode with license detection, output JSON |
| `dependency-checker` | `dependency_checker_shell_script` | Clone, run ORT analyzer, output JSON |
| `oat-scanner` | `oat_scanner_shell_script` | Clone, run OAT tool, parse text report |

Sources: [openchecker/constans.py L37-L139](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/constans.py#L37-L139)

## Result Processing and Error Handling

Different command types require specialized result processing to handle various output formats and error conditions.

### Result Processing Flow

```mermaid
flowchart TD

ProcessCommandResult["_process_command_result()"]
CheckCommand["command type"]
ParseJSON["json.loads(result_str)"]
DependencyProcess["dependency_checker_output_process()"]
OATProcess["parse_oat_txt_to_json()"]
ReturnRaw["return result_str"]
HandleJSONError["JSONDecodeError?"]
ReturnParsed["return parsed JSON"]
RubyLicenses["ruby_licenses()"]
CategorizePackages["Categorize packages by license"]
RegexParsing["Parse OAT text with regex patterns"]
StructuredOutput["Return structured JSON"]

ProcessCommandResult --> CheckCommand
CheckCommand --> ParseJSON
CheckCommand --> DependencyProcess
CheckCommand --> OATProcess
CheckCommand --> ReturnRaw
ParseJSON --> HandleJSONError
HandleJSONError --> ReturnRaw
HandleJSONError --> ReturnParsed
DependencyProcess --> RubyLicenses
RubyLicenses --> CategorizePackages
OATProcess --> RegexParsing
RegexParsing --> StructuredOutput
```

Sources: [openchecker/agent.py L448-L477](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L448-L477)

### Specialized Processing: Dependency Checker

The dependency checker includes sophisticated post-processing for Ruby package licenses:

```mermaid
flowchart TD

DependencyOutput["dependency-checker raw output"]
ParseJSON["json.loads(output)"]
RubyLicenses["ruby_licenses()"]
CheckPackages["Iterate packages"]
CheckLicenses["declared_licenses empty?"]
CheckGitHub["GitHub URL available?"]
NextPackage["Next package"]
LicenseDetector["Run license-detector shell script"]
ParseLicenseJSON["Parse license JSON"]
UpdateLicenses["Update declared_licenses"]
CategorizePackages["Categorize by license status"]
FinalResult["packages_all, packages_with_license_detect, packages_without_license_detect"]

DependencyOutput --> ParseJSON
ParseJSON --> RubyLicenses
RubyLicenses --> CheckPackages
CheckPackages --> CheckLicenses
CheckLicenses --> CheckGitHub
CheckLicenses --> NextPackage
CheckGitHub --> LicenseDetector
CheckGitHub --> NextPackage
LicenseDetector --> ParseLicenseJSON
ParseLicenseJSON --> UpdateLicenses
UpdateLicenses --> NextPackage
NextPackage --> CategorizePackages
CategorizePackages --> FinalResult
```

Sources: [openchecker/agent.py L93-L174](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L93-L174)

## Error Handling and Resilience

The framework implements multiple layers of error handling to ensure robust operation even when individual checkers fail.

### Error Handling Layers

| Layer | Scope | Implementation | Recovery Action |
| --- | --- | --- | --- |
| Individual Checker | Single checker execution | Try-catch in `command_switch<FileRef file-url="https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/command" undefined  file-path="command">Hii</FileRef>` | Store error in `res_payload`, continue with next checker |
| Shell Command | Shell script execution | Error checking in `_handle_shell_script_command` | Store shell error output, mark command as failed |
| Message Processing | Entire message | Try-catch in `callback_func` | Send NACK to RabbitMQ, route to dead letter queue |
| Result Processing | Command result parsing | Try-catch in `_process_command_result` | Return raw output or error structure |

```mermaid
flowchart TD

ExecuteCommand["Execute command from command_list"]
TryCatch["try-catch wrapper"]
UpdateResults["Update res_payload with results"]
LogError["logger.error()"]
StoreError["res_payload['scan_results'][command] = {'error': str(e)}"]
NextCommand["Continue with next command"]
AllComplete["All commands done?"]
SendResults["Send results to callback_url"]
AckMessage["ch.basic_ack()"]

ExecuteCommand --> TryCatch
TryCatch --> UpdateResults
TryCatch --> LogError
LogError --> StoreError
UpdateResults --> NextCommand
StoreError --> NextCommand
NextCommand --> AllComplete
AllComplete --> ExecuteCommand
AllComplete --> SendResults
SendResults --> AckMessage
```

Sources: [openchecker/agent.py L402-L411](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L402-L411)

 [openchecker/agent.py L519-L531](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/openchecker/agent.py#L519-L531)