# Irmia DevKit MCP 架构

## 入口与职责

平台启动脚本和 npm launcher 调用 Python bootstrap，bootstrap 管理隔离依赖环境，server.py 创建 FastMCP 并注册 60 个工具。tools/*.py 提供共享业务实现；tools/_registry.py 保留上游 AstrBot 注册信息，但不是 MCP 的公开入口。mcp_results.py 只修正共享核心返回的 file_diff 后续调用参数别名，不改变其他诊断数据。

## 编辑与语法检查

safe_edit、safe_write、multi_edit 共用 syntax_check.supports 调度表，覆盖代码与 JSON/TOML/YAML。精确匹配优先于行号剥除和缩进容错；多匹配返回证据供调用者消歧。单文件编辑先备份，语法失败恢复；新文件无旧版本时保留失败内容并提供诊断。多文件先规划和检查，再逐文件原子写，失败尝试恢复已修改文件，恢复状态必须真实报告。

syntax_check 使用不执行目标文件的解析/检查命令，关闭无输入需求检查器的 stdin，避免读取 MCP 协议流。Java 使用随包 IrmiaSyntaxParser.java，在临时目录构建解析辅助程序并调用 JavacTask.parse；支持 JDK 8 tools.jar 与新 JDK。PowerShell 调用 Parser.ParseFile，Shell 调用 -n。JSX/TSX 缺少独立解析器时跳过，不能误用 node --check。C/C++ 编译器可能要求项目 include 环境。

## 状态与边界

编辑备份默认 ~/.irmia/backups，可经配置改变，须放项目外并有正确权限；代码索引在项目 .codegraph 目录保存 SQLite/FTS，查询也可能初始化库，MCP annotations 不把这些入口标为只读。HTTP 分页缓存保留 TTL、headers 指纹隔离，网络校验保留 MCP 扩展的禁止网段与关闭隐式代理策略。数据库查询独立只读连接，不使用索引写连接。

MCP annotations 是宿主策略提示，不是操作系统沙箱或用户授权替代。本服务拥有启动用户的进程权限，用户必须选择可信宿主和工作区；需要更强边界时由宿主施加文件沙箱与审批。

## 分发和验证

npm 包包括 server.py、mcp_results.py、tools 与 Java 辅助源码；Python wheel 声明 tools/*.java 的 package-data。测试区分公开 MCP schema、工具结果、编辑恢复和保留的安全修复。共享夹具 tests/fixtures/alignment-scenes.json 可供原生 DSH 重写复用关键行为。测试备份与数据库在临时目录，不使用用户实际持久状态。
