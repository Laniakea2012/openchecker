# 开源软件API图谱项目数据需求说明书

## 1. 项目概述

### 1.1 项目背景
随着开源软件在全球范围内的广泛应用，理解和评估开源软件、洞悉开源软件生态的结构与动态、识别高价值软件以及分析开源软件演进路径、进行开源软件供应链安全管理、为开发者提供智能软件/API推荐及生成等已成为关键需求。本项目旨在构建覆盖全面的开源软件API图谱，为开源生态评估、软件推荐、安全治理等应用场景提供数据支撑。

### 1.2 项目目标
- 构建开源软件API签名数据库，覆盖功能、参数类型、调用关系、来源三方库、编程语言、开源license等信息
- 建立开源软件生态图谱，支持采用率、代码质量、版本更新、供应链安全等维度的评估
- 实现相似开源软件的精准识别与推荐、基于功能的API查找、版本兼容性分析等功能

### 1.3 应用价值
- 提升软件开发效率，帮助开发者发现适用的开源资源
- 为开源项目的可持续发展提供数据支持和决策依据
- 支持开源软件安全治理和供应链风险管控

## 2. 数据需求概述

### 2.1 数据范围
本项目需要获取主流开源代码托管平台的源码数据，主要包括：

#### 2.1.1 目标平台详细规格
- **GitHub**（第一优先级）
  - 覆盖范围：所有公开仓库，重点关注Star数>100的项目
  - 数据更新频率：每月增量同步
  - 预期项目数量：80万+ 活跃项目
  
- **Gitee**（第二优先级）
  - 覆盖范围：中文开源项目重点覆盖
  - 数据更新频率：每月增量同步
  - 预期项目数量：5万+ 活跃项目

- **GitLab**（第三优先级）
  - 覆盖范围：GitLab.com公开仓库
  - 数据更新频率：每月全量同步
  - 预期项目数量：15万+ 活跃项目
  
- **其他平台**：Bitbucket、SourceForge、CodePlex等（按需采集）

#### 2.1.2 编程语言覆盖详细规格
- **Java**（优先级1）：Spring框架、Maven生态、Android开发相关
- **Python**（优先级1）：Django/Flask、NumPy/Pandas、机器学习库
- **JavaScript/TypeScript**（优先级1）：Node.js、React/Vue/Angular、npm生态
- **C/C++**（优先级2）：系统级软件、嵌入式、游戏引擎
- **Go**（优先级2）：云原生、微服务、DevOps工具
- **Rust**（优先级2）：系统编程、WebAssembly、区块链
- **C#**（优先级3）：.NET生态、Unity游戏开发
- **PHP**（优先级3）：Web开发、CMS系统
- **Ruby**（优先级3）：Rails框架、DevOps工具
- **其他语言**：Kotlin、Swift、Scala、R、Julia等（按需覆盖）

#### 2.1.3 项目筛选标准
- **活跃度要求**：最近12个月内有代码提交
- **规模要求**：代码行数 > 100行，文件数 > 5个
- **质量要求**：有完整的README文档，明确的许可证声明
- **语言比例**：主要编程语言占比 > 50% （待定）
- **排除标准**：Fork项目（除非有显著改进）、教程代码、个人练习项目

### 2.2 数据类型

#### 2.2.1 源代码文件（优先级1）
- **源码内容**：完整的项目源码文件，包含原始代码和注释
- **文件元信息**：文件路径、大小、修改时间、编码格式、Git哈希值
- **语法树数据**：抽象语法树(AST)、符号表、控制流图
- **代码指标**：复杂度度量、代码覆盖率、重复代码检测结果

#### 2.2.2 API结构数据（优先级1）
- **函数签名**：函数名、参数列表、返回类型、泛型信息
- **类结构**：类继承关系、接口实现、成员变量和方法
- **模块信息**：包结构、命名空间、导入导出关系
- **注解标记**：装饰器、属性标注、编译指令

#### 2.2.3 项目元数据（优先级1）
- **基础信息**：项目名称、描述、主页URL、克隆地址
- **统计指标**：代码行数、文件数量、贡献者数量、提交频次
- **质量评估**：代码质量评分、安全漏洞扫描结果、测试覆盖率
- **生态数据**：下载量、使用量、衍生项目数量

#### 2.2.4 版本演进数据（优先级2）
- **提交历史**：提交记录、变更差异、合并信息
- **发布版本**：版本号、发布说明、兼容性信息
- **分支信息**：分支结构、合并策略、开发流程

#### 2.2.5 依赖关系数据（优先级2）
- **直接依赖**：依赖库版本、依赖类型、约束条件
- **传递依赖**：依赖树结构、版本冲突解决
- **API调用关系**：跨项目API调用、内部模块调用

#### 2.2.6 开发者协作数据（优先级3）
- **贡献者档案**：用户信息、贡献统计、活跃度分析
- **协作模式**：代码审查流程、讨论记录、问题跟踪
- **社区活动**：问题报告、功能请求、文档贡献


### 3.1 源码数据需求

#### 3.1.1 源代码文件

**核心数据字段**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| file_path | String | 500字符 | 是 | 相对于项目根目录的文件路径 |
| file_name | String | 255字符 | 是 | 文件名（含扩展名） |
| file_content | Text | 10MB | 是 | 完整的源码内容（原始格式） |
| file_type | String | 20字符 | 是 | 文件类型标识（source/config/doc等） |
| language | String | 20字符 | 是 | 编程语言标识（java/python/javascript等） |
| file_size | Long | - | 是 | 文件大小（字节） |
| line_count | Integer | - | 是 | 代码行数（包含空行和注释） |
| effective_lines | Integer | - | 是 | 有效代码行数（不含空行和注释） |
| encoding | String | 20字符 | 是 | 字符编码格式（utf-8/gbk/ascii等） |
| created_at | DateTime | - | 是 | 文件创建时间（ISO 8601格式） |
| modified_at | DateTime | - | 是 | 最后修改时间（ISO 8601格式） |
| git_hash | String | 40字符 | 是 | Git文件哈希值（SHA-1） |
| git_blame | JSON | - | 否 | 代码行责任归属信息 |

**扩展数据字段**：
| 字段名称 | 数据类型 | 描述 |
|---------|---------|------|
| complexity_score | Float | 代码复杂度评分（McCabe复杂度） |
| maintainability_index | Float | 可维护性指数（0-100） |
| comment_ratio | Float | 注释率（注释行/总行数） |
| syntax_errors | JSON | 语法错误信息列表 |
| code_smells | JSON | 代码异味检测结果 |
| duplication_blocks | JSON | 重复代码块信息 |

**技术规格详细说明**：
- **支持的文件扩展名**：
  - Java: .java, .jsp, .jspx
  - Python: .py, .pyx, .pyi, .pyw
  - JavaScript/TypeScript: .js, .jsx, .ts, .tsx, .vue
  - C/C++: .c, .cpp, .cxx, .cc, .h, .hpp, .hxx
  - Go: .go
  - Rust: .rs
  - C#: .cs, .csx
  - PHP: .php, .phtml, .php3, .php4, .php5
  - Ruby: .rb, .rbw, .rake, .gemspec
  - 其他: .kt, .swift, .scala, .r, .jl, .m, .mm

- **文件大小限制**：
  - 单文件最大：10MB
  - 二进制文件：排除处理
  - 生成文件：自动识别并标记（如编译输出、构建产物等）

- **编码识别规则**：
  - 优先级1：BOM标识
  - 优先级2：文件头部编码声明
  - 优先级3：统计学方法检测
  - 备选方案：使用chardet等工具进行编码检测

- **文件内容预处理**：
  - 移除尾部空白字符
  - 统一换行符为LF(\n)
  - 保留原始缩进格式
  - 记录预处理操作日志

#### 3.1.2 API相关数据

**函数/方法定义数据结构**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| function_id | String | 64字符 | 是 | 函数唯一标识符（SHA-256哈希） |
| function_name | String | 255字符 | 是 | 函数/方法名称 |
| full_signature | String | 1000字符 | 是 | 完整函数签名 |
| return_type | String | 200字符 | 否 | 返回值类型 |
| parameters | JSON | - | 是 | 参数列表详细信息 |
| access_modifier | String | 20字符 | 否 | 访问修饰符（public/private/protected等） |
| is_static | Boolean | - | 是 | 是否为静态方法 |
| is_abstract | Boolean | - | 是 | 是否为抽象方法 |
| is_deprecated | Boolean | - | 是 | 是否已弃用 |
| class_name | String | 255字符 | 否 | 所属类名 |
| module_name | String | 255字符 | 否 | 所属模块/包名 |
| namespace | String | 500字符 | 否 | 命名空间 |
| start_line | Integer | - | 是 | 函数起始行号 |
| end_line | Integer | - | 是 | 函数结束行号 |
| complexity | Integer | - | 否 | 圈复杂度 |
| doc_string | Text | 5000字符 | 否 | 函数文档字符串 |
| annotations | JSON | - | 否 | 注解/装饰器信息 |

**参数详细结构（JSON格式）**：
```json
{
  "parameters": [
    {
      "name": "参数名",
      "type": "参数类型",
      "default_value": "默认值",
      "is_optional": true/false,
      "description": "参数描述",
      "annotations": ["注解列表"]
    }
  ]
}
```

**API调用关系数据结构**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| call_id | String | 64字符 | 是 | 调用关系唯一标识符 |
| caller_function | String | 64字符 | 是 | 调用方函数ID |
| callee_function | String | 64字符 | 是 | 被调用函数ID |
| call_type | String | 20字符 | 是 | 调用类型（direct/indirect/virtual等） |
| call_line | Integer | - | 是 | 调用所在行号 |
| call_context | String | 500字符 | 否 | 调用上下文代码片段 |
| arguments | JSON | - | 否 | 传递的参数信息 |
| is_external_call | Boolean | - | 是 | 是否为外部库调用 |
| target_library | String | 100字符 | 否 | 目标库名称（如果是外部调用） |
| exception_handling | JSON | - | 否 | 异常处理机制 |

**类/接口定义数据结构**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| class_id | String | 64字符 | 是 | 类唯一标识符 |
| class_name | String | 255字符 | 是 | 类名 |
| class_type | String | 20字符 | 是 | 类型（class/interface/abstract/enum等） |
| package_name | String | 255字符 | 否 | 包名 |
| superclass | String | 255字符 | 否 | 父类名 |
| interfaces | JSON | - | 否 | 实现的接口列表 |
| access_modifier | String | 20字符 | 否 | 访问修饰符 |
| is_final | Boolean | - | 是 | 是否为final类 |
| is_deprecated | Boolean | - | 是 | 是否已弃用 |
| methods | JSON | - | 是 | 方法列表 |
| fields | JSON | - | 是 | 成员变量列表 |
| annotations | JSON | - | 否 | 类注解信息 |
| inner_classes | JSON | - | 否 | 内部类列表 |

**API提取技术要求**：
- **Java语言**：使用Java Reflection API + AST解析（Eclipse JDT）
- **Python语言**：使用ast模块 + inspect模块
- **JavaScript/TypeScript**：使用Babel/TypeScript Compiler API
- **C/C++语言**：使用Clang AST解析器
- **Go语言**：使用go/ast + go/types标准库
- **其他语言**：使用相应的语言特定解析器

**API文档提取规则**：
- **JavaDoc格式**：@param, @return, @throws等标签解析
- **Python docstring**：Google/Numpy/Sphinx格式支持
- **JSDoc格式**：@param, @returns, @throws等标签解析
- **注释解析**：单行注释、多行注释、文档注释分类处理

#### 3.1.3 项目结构数据

**目录结构数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| directory_path | String | 500字符 | 是 | 目录相对路径 |
| directory_name | String | 255字符 | 是 | 目录名称 |
| parent_directory | String | 500字符 | 否 | 父目录路径 |
| subdirectories | JSON | - | 是 | 子目录列表 |
| file_count | Integer | - | 是 | 目录内文件数量 |
| total_size | Long | - | 是 | 目录总大小（字节） |
| directory_type | String | 50字符 | 否 | 目录类型（src/test/doc/config等） |

**构建配置文件数据**：
| 文件类型 | 文件名模式 | 提取内容 | 数据结构 |
|---------|-----------|----------|----------|
| Maven | pom.xml | 依赖、插件、属性 | XML解析后转JSON |
| Gradle | build.gradle, gradle.properties | 依赖、任务、配置 | Groovy/Kotlin AST解析 |
| NPM | package.json, package-lock.json | 依赖、脚本、配置 | 原生JSON |
| Python | requirements.txt, setup.py, pyproject.toml | 依赖、包信息 | 文本解析/TOML解析 |
| Go | go.mod, go.sum | 模块依赖 | Go mod文件解析 |
| Rust | Cargo.toml, Cargo.lock | 依赖、元数据 | TOML解析 |
| .NET | *.csproj, packages.config | 包引用、配置 | XML解析 |

**构建配置标准化格式**：
```json
{
  "build_tool": "maven/gradle/npm/pip等",
  "build_file": "构建文件路径",
  "dependencies": [
    {
      "name": "依赖名称",
      "version": "版本号",
      "scope": "compile/test/runtime等",
      "is_direct": true/false,
      "group_id": "组织ID（如适用）",
      "artifact_id": "构件ID（如适用）"
    }
  ],
  "plugins": [
    {
      "name": "插件名称",
      "version": "版本号",
      "configuration": "配置信息"
    }
  ],
  "properties": {
    "key": "value"
  },
  "scripts": {
    "script_name": "script_command"
  }
}
```

**文档文件数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| doc_type | String | 20字符 | 是 | 文档类型（readme/api/tutorial等） |
| file_path | String | 500字符 | 是 | 文档文件路径 |
| title | String | 200字符 | 否 | 文档标题 |
| content | Text | 100KB | 是 | 文档内容（Markdown/HTML/纯文本） |
| format | String | 20字符 | 是 | 文档格式（md/html/txt/rst等） |
| language | String | 10字符 | 否 | 文档语言（zh/en等） |
| sections | JSON | - | 否 | 文档章节结构 |
| links | JSON | - | 否 | 外部链接列表 |
| images | JSON | - | 否 | 图片引用列表 |

**配置文件和资源文件**：
- **配置文件类型**：
  - 应用配置：application.properties, config.json, settings.py
  - 环境配置：.env, development.yml, production.conf
  - 数据库配置：database.yml, persistence.xml
  - 服务配置：nginx.conf, docker-compose.yml, kubernetes.yaml
  
- **资源文件类型**：
  - 国际化：messages.properties, locale files
  - 静态资源：CSS, JavaScript, images
  - 模板文件：HTML templates, email templates
  - 数据文件：SQL scripts, test data

**项目元文件**：
- **许可证文件**：LICENSE, COPYING, COPYRIGHT
- **变更日志**：CHANGELOG.md, HISTORY.md, RELEASES.md
- **贡献指南**：CONTRIBUTING.md, CODE_OF_CONDUCT.md
- **CI/CD配置**：.github/workflows/, .gitlab-ci.yml, Jenkinsfile
- **IDE配置**：.vscode/, .idea/, .eclipse/

### 3.2 项目元数据需求

#### 3.2.1 基本信息

**项目标识数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| project_id | String | 64字符 | 是 | 项目全局唯一标识符 |
| repository_name | String | 255字符 | 是 | 仓库名称 |
| full_name | String | 500字符 | 是 | 完整项目名（owner/repo） |
| clone_url | String | 500字符 | 是 | Git克隆地址 |
| html_url | String | 500字符 | 是 | 项目主页URL |
| api_url | String | 500字符 | 是 | API访问地址 |
| homepage_url | String | 500字符 | 否 | 项目官网地址 |
| mirror_url | String | 500字符 | 否 | 镜像地址 |

**描述信息数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| description | Text | 1000字符 | 否 | 项目描述 |
| topics | JSON | - | 否 | 项目主题标签列表 |
| keywords | JSON | - | 否 | 关键词列表 |
| category | String | 50字符 | 否 | 项目分类 |
| readme_content | Text | 100KB | 否 | README文件内容 |
| documentation_url | String | 500字符 | 否 | 文档地址 |

**许可证信息数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| license_type | String | 50字符 | 否 | 许可证类型（MIT/Apache/GPL等） |
| license_name | String | 100字符 | 否 | 许可证全名 |
| license_url | String | 500字符 | 否 | 许可证文本URL |
| license_content | Text | 50KB | 否 | 许可证完整内容 |
| spdx_id | String | 20字符 | 否 | SPDX许可证标识符 |
| is_open_source | Boolean | - | 是 | 是否为开源许可证 |

**编程语言统计数据**：
```json
{
  "languages": {
    "Java": {
      "bytes": 1234567,
      "percentage": 45.2,
      "files_count": 156
    },
    "JavaScript": {
      "bytes": 987654,
      "percentage": 35.8,
      "files_count": 89
    }
  },
  "primary_language": "Java",
  "language_count": 5
}
```

#### 3.2.2 统计数据

**规模指标数据**：
| 字段名称 | 数据类型 | 是否必填 | 描述 |
|---------|---------|----------|------|
| total_lines | Long | 是 | 总代码行数（包含空行和注释） |
| code_lines | Long | 是 | 有效代码行数 |
| comment_lines | Long | 是 | 注释行数 |
| blank_lines | Long | 是 | 空行数 |
| file_count | Integer | 是 | 文件总数 |
| source_file_count | Integer | 是 | 源码文件数 |
| directory_count | Integer | 是 | 目录数量 |
| repository_size | Long | 是 | 仓库大小（KB） |
| binary_file_count | Integer | 是 | 二进制文件数 |

**活跃度指标数据**：
| 字段名称 | 数据类型 | 是否必填 | 描述 |
|---------|---------|----------|------|
| stars_count | Integer | 是 | 星标数量 |
| forks_count | Integer | 是 | Fork数量 |
| watchers_count | Integer | 是 | 关注者数量 |
| subscribers_count | Integer | 是 | 订阅者数量 |
| open_issues_count | Integer | 是 | 开放问题数量 |
| closed_issues_count | Integer | 否 | 已关闭问题数量 |
| network_count | Integer | 否 | 网络仓库数量 |

**贡献指标数据**：
| 字段名称 | 数据类型 | 是否必填 | 描述 |
|---------|---------|----------|------|
| contributors_count | Integer | 是 | 贡献者数量 |
| commits_count | Long | 是 | 提交总数 |
| commits_last_year | Integer | 否 | 过去一年提交数 |
| commits_last_month | Integer | 否 | 过去一月提交数 |
| pull_requests_count | Integer | 否 | Pull Request总数 |
| open_pull_requests | Integer | 否 | 开放的Pull Request数 |
| merged_pull_requests | Integer | 否 | 已合并的Pull Request数 |
| releases_count | Integer | 否 | 发布版本数量 |

**时间指标数据**：
| 字段名称 | 数据类型 | 是否必填 | 描述 |
|---------|---------|----------|------|
| created_at | DateTime | 是 | 项目创建时间 |
| updated_at | DateTime | 是 | 最后更新时间 |
| pushed_at | DateTime | 是 | 最后推送时间 |
| last_commit_at | DateTime | 否 | 最后提交时间 |
| first_commit_at | DateTime | 否 | 首次提交时间 |
| last_release_at | DateTime | 否 | 最后发布时间 |

#### 3.2.3 版本信息

**Release版本数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| release_id | String | 64字符 | 是 | 发布版本唯一标识 |
| tag_name | String | 100字符 | 是 | 版本标签名 |
| name | String | 200字符 | 否 | 发布版本名称 |
| body | Text | 10KB | 否 | 发布说明 |
| published_at | DateTime | - | 是 | 发布时间 |
| created_at | DateTime | - | 是 | 创建时间 |
| target_commitish | String | 40字符 | 是 | 目标提交哈希 |
| is_prerelease | Boolean | - | 是 | 是否为预发布版本 |
| is_draft | Boolean | - | 是 | 是否为草稿 |
| assets | JSON | - | 否 | 发布附件信息 |
| download_count | Integer | - | 否 | 下载次数 |

**分支信息数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| branch_name | String | 255字符 | 是 | 分支名称 |
| commit_sha | String | 40字符 | 是 | 最新提交哈希 |
| is_default | Boolean | - | 是 | 是否为默认分支 |
| is_protected | Boolean | - | 是 | 是否为保护分支 |
| ahead_by | Integer | - | 否 | 领先主分支的提交数 |
| behind_by | Integer | - | 否 | 落后主分支的提交数 |
| last_commit_date | DateTime | - | 否 | 最后提交时间 |

**Git标签数据**：
| 字段名称 | 数据类型 | 长度限制 | 是否必填 | 描述 |
|---------|---------|----------|----------|------|
| tag_name | String | 100字符 | 是 | 标签名称 |
| commit_sha | String | 40字符 | 是 | 关联的提交哈希 |
| tagger_name | String | 100字符 | 否 | 标签创建者 |
| tagger_email | String | 100字符 | 否 | 创建者邮箱 |
| tag_date | DateTime | - | 是 | 标签创建时间 |
| message | Text | 1000字符 | 否 | 标签消息 |
| is_signed | Boolean | - | 是 | 是否为签名标签 |

### 3.3 依赖关系数据

#### 3.3.1 直接依赖
- 依赖库名称和版本
- 依赖类型（运行时、开发时、测试）
- 依赖范围和约束条件

#### 3.3.2 传递依赖
- 间接依赖关系链
- 依赖树结构
- 版本冲突和解决方案

### 3.4 开发者数据

#### 3.4.1 贡献者信息
- 用户名和显示名称
- 邮箱地址（如公开）
- 贡献统计（提交数、代码行数）
- 活跃时间段

#### 3.4.2 维护者信息
- 项目角色和权限
- 维护活跃度
- 响应时间统计


## 4. 源图开源仓库数据需求

### 4.1 仓库基本信息

**必需的仓库元数据**：
| 数据字段 | 数据类型 | 示例值 | 说明 |
|---------|----------|--------|------|
| id | Integer | 1296269 | GitHub仓库唯一ID |
| name | String | "Hello-World" | 仓库名称 |
| full_name | String | "octocat/Hello-World" | 完整仓库名（所有者/仓库名） |
| owner | Object | {"login": "octocat", "id": 1} | 仓库所有者信息 |
| clone_url | String | "https://github.com/octocat/Hello-World.git" | Git克隆地址 |
| html_url | String | "https://github.com/octocat/Hello-World" | 仓库网页地址 |
| description | String | "This your first repo!" | 仓库描述 |
| language | String | "Java" | 主要编程语言 |
| created_at | DateTime | "2011-01-26T19:01:12Z" | 创建时间 |
| updated_at | DateTime | "2011-01-26T19:14:43Z" | 最后更新时间 |
| pushed_at | DateTime | "2011-01-26T19:06:43Z" | 最后推送时间 |
| default_branch | String | "main" | 默认分支名 |

**可选的统计信息**：
| 数据字段 | 数据类型 | 说明 |
|---------|----------|------|
| stargazers_count | Integer | 星标数量 |
| forks_count | Integer | Fork数量 |
| size | Integer | 仓库大小（KB） |
| open_issues_count | Integer | 开放Issue数量 |

### 4.2 源码文件数据

**需要提供的源码文件信息**：

#### 4.2.1 文件列表结构
```json
{
  "repository": {
    "id": 1296269,
    "full_name": "octocat/Hello-World"
  },
  "files": [
    {
      "path": "src/main/java/com/example/App.java",
      "name": "App.java",
      "type": "file",
      "size": 1024,
      "sha": "44b4fc6d56897b048c772eb4087f854f46256132",
      "content": "package com.example;\n\npublic class App {\n    public static void main(String[] args) {\n        System.out.println(\"Hello World!\");\n    }\n}"
    },
    {
      "path": "README.md",
      "name": "README.md", 
      "type": "file",
      "size": 256,
      "sha": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
      "content": "# Hello World\n\nThis is a sample repository."
    }
  ]
}
```

#### 4.2.2 文件包含范围
**包含的文件类型**：
- 所有源代码文件（.java, .py, .js, .ts, .cpp, .c, .h, .go, .rs, .cs, .php, .rb等）
- 配置文件（pom.xml, package.json, requirements.txt, go.mod, Cargo.toml等）
- 文档文件（README.md, CHANGELOG.md, LICENSE等）
- 构建脚本（Makefile, build.gradle, CMakeLists.txt等）

**排除的文件类型**：
- 二进制文件（.jar, .exe, .dll, .so等）
- 图片文件（.png, .jpg, .gif等）
- 压缩文件（.zip, .tar.gz等）
- 生成的文件（编译输出、缓存文件等）

#### 4.2.3 文件内容要求
- **编码格式**：UTF-8优先，其他编码需标注
- **文件大小**：单文件≤10MB（超过的文件可提供下载链接）
- **文件路径**：保持原始的相对路径结构
- **文件内容**：原始文本内容，保持格式和换行符

### 4.3 数据提供方式

#### 4.3.1 批量导出格式
推荐的数据打包方式：
```
repository_data/
├── metadata.json          # 仓库基本信息
└── files/
    ├── src/
    │   └── main/
    │       └── java/
    │           └── App.java
    ├── README.md
    ├── pom.xml
    └── .gitignore
```

#### 4.3.2 API接口访问
如果通过API提供，建议的接口格式：
```
GET /api/repositories/{repo_id}/metadata
GET /api/repositories/{repo_id}/files
GET /api/repositories/{repo_id}/files/{file_path}
```

### 4.4 数据更新频率
- **元数据更新**：每月同步
- **文件内容更新**：每月同步
- **增量更新**：基于仓库的`updated_at`时间戳判断是否需要重新获取
