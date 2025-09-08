# Binary Analysis and Shell Script System

> **Relevant source files**
> * [scripts/binary_checker.sh](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh)

## Purpose and Scope

The Binary Analysis and Shell Script System provides automated detection of binary files within software projects and orchestrates shell script execution for various analysis tasks. This system is a core component of the OpenChecker analysis pipeline, responsible for identifying binary content that may indicate licensing, security, or compliance issues.

This document covers the binary file detection mechanisms and shell script execution framework. For information about the broader analysis tool orchestration, see [Checker Framework and Execution](/Laniakea2012/openchecker/4.2-checker-framework-and-execution). For details about the agent system that executes these scripts, see [Agent System and Message Processing](/Laniakea2012/openchecker/2.1-agent-system-and-message-processing).

## Binary Detection Framework

The binary detection system uses MIME type analysis to identify binary files and classify their content types. The core detection logic distinguishes between various binary formats including applications, images, audio, and video files.

### Binary File Classification

The `is_binary()` function in [scripts/binary_checker.sh L4-L10](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L4-L10)

 implements the primary binary detection logic:

```mermaid
flowchart TD

file_input["File Input"]
mime_check["file --mime-type -b"]
application_check["MIME type starts with<br>application/*?"]
image_check["MIME type starts with<br>image/*?"]
audio_check["MIME type starts with<br>audio/*?"]
video_check["MIME type starts with<br>video/*?"]
binary_result["Return 0 (Binary)"]
text_result["Return 1 (Text)"]

file_input --> mime_check
mime_check --> application_check
mime_check --> image_check
mime_check --> audio_check
mime_check --> video_check
application_check --> binary_result
image_check --> binary_result
audio_check --> binary_result
video_check --> binary_result
application_check --> text_result
image_check --> text_result
audio_check --> text_result
video_check --> text_result
```

**Sources:** [scripts/binary_checker.sh L4-L10](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L4-L10)

## Compressed File Analysis

The system provides deep analysis of compressed archives by extracting their contents and recursively scanning for binary files within them.

### Archive Format Support

The `check_compressed_binary()` function [scripts/binary_checker.sh L13-L69](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L13-L69)

 supports multiple compression formats:

| Format | MIME Type | Extraction Method | Nested Support |
| --- | --- | --- | --- |
| ZIP | `application/zip` | `unzip -qq -P ""` | No |
| TAR | `application/x-tar` | `tar -xf` | No |
| GZIP | `application/gzip` | `gunzip -c` | TAR detection |
| BZIP2 | `application/x-bzip2` | `bunzip2 -c` | TAR detection |

### Compression Processing Workflow

```mermaid
flowchart TD

compressed_file["Compressed File Input"]
temp_dir["mktemp -d"]
mime_detection["file --mime-type -b"]
zip_path["application/zip"]
tar_path["application/x-tar"]
gzip_path["application/gzip"]
bzip2_path["application/x-bzip2"]
unzip_extract["unzip -qq -P \"]
tar_extract["tar -xf"]
gunzip_extract["gunzip -c"]
bunzip2_extract["bunzip2 -c"]
inner_tar_check["Inner file is TAR?"]
unsupported_inner["Unsupported inner type"]
find_files["find temp_dir -type f -not -path '/.git/'"]
binary_scan["is_binary() on each file"]
cleanup["rm -rf temp_dir"]
unsupported_format["Unsupported file type"]

compressed_file --> temp_dir
temp_dir --> mime_detection
mime_detection --> zip_path
mime_detection --> tar_path
mime_detection --> gzip_path
mime_detection --> bzip2_path
zip_path --> unzip_extract
tar_path --> tar_extract
gzip_path --> gunzip_extract
bzip2_path --> bunzip2_extract
gunzip_extract --> inner_tar_check
bunzip2_extract --> inner_tar_check
inner_tar_check --> tar_extract
inner_tar_check --> unsupported_inner
unzip_extract --> find_files
tar_extract --> find_files
find_files --> binary_scan
binary_scan --> cleanup
unsupported_inner --> cleanup
mime_detection --> unsupported_format
unsupported_format --> cleanup
```

**Sources:** [scripts/binary_checker.sh L13-L69](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L13-L69)

## Shell Script Integration

The binary checker integrates with the broader OpenChecker system through shell script execution patterns that follow consistent interfaces for repository processing.

### Repository Processing Pipeline

The main script execution flow [scripts/binary_checker.sh L71-L93](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L71-L93)

 follows this pattern:

```mermaid
flowchart TD

script_start["binary_checker.sh execution"]
extract_name["basename $1 | sed 's/\.git$//"]
project_name["project_name variable"]
dir_check["Directory exists?"]
git_clone["GIT_ASKPASS=/bin/true git clone --depth=1"]
find_files["find project_name -type f"]
exclude_paths["Exclude .git/* and test/*"]
file_loop["For each file"]
file_exists["File exists?"]
continue_loop["Continue to next file"]
type_check["file --mime-type -b"]
compressed_check["Is compressed archive?"]
check_compressed_binary["check_compressed_binary()"]
is_binary_check["is_binary()"]
archive_result["Echo 'Binary archive found'"]
binary_result["Echo 'Binary file found'"]

script_start --> extract_name
extract_name --> project_name
project_name --> dir_check
dir_check --> git_clone
dir_check --> find_files
git_clone --> find_files
find_files --> exclude_paths
exclude_paths --> file_loop
file_loop --> file_exists
file_exists --> continue_loop
file_exists --> type_check
type_check --> compressed_check
compressed_check --> check_compressed_binary
compressed_check --> is_binary_check
check_compressed_binary --> archive_result
is_binary_check --> binary_result
archive_result --> continue_loop
binary_result --> continue_loop
continue_loop --> file_loop
```

**Sources:** [scripts/binary_checker.sh L71-L93](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L71-L93)

### File System Filtering

The system implements selective file scanning with specific exclusion patterns:

* **Git exclusion**: `*/.git/*` paths are skipped to avoid repository metadata
* **Test exclusion**: `*/test/*` paths are excluded to focus on production code
* **File existence check**: Validates file existence before processing to handle symlinks and race conditions

## Error Handling and Cleanup

The binary analysis system implements robust error handling and temporary resource management:

### Temporary Directory Management

Each compressed file analysis creates isolated temporary directories using `mktemp -d` [scripts/binary_checker.sh L14](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L14-L14)

 and ensures cleanup through `rm -rf "$temp_dir"` [scripts/binary_checker.sh L67](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L67-L67)

 regardless of processing outcome.

### Error Recovery Patterns

```mermaid
flowchart TD

decompress_start["Decompression attempt"]
success_check["Decompression successful?"]
process_contents["Process extracted contents"]
error_message["Echo error message"]
cleanup["rm -rf temp_dir"]
return_code["Return appropriate code"]
flag_1["Return 1 (Error/No binary)"]
flag_0["Return 0 (Binary found)"]

decompress_start --> success_check
success_check --> process_contents
success_check --> error_message
process_contents --> cleanup
error_message --> cleanup
cleanup --> return_code
return_code --> flag_1
return_code --> flag_0
```

**Sources:** [scripts/binary_checker.sh L28-L35](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L28-L35)

 [scripts/binary_checker.sh L44-L51](https://github.com/Laniakea2012/openchecker/blob/1dbd85d0/scripts/binary_checker.sh#L44-L51)