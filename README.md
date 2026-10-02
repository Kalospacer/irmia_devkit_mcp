# Irmia DevKit MCP

为编码 Agent 提供 60 个 MCP 开发工具：安全编辑、文件搜索、语义索引、HTTP、SQLite 只读查询、Git/GitHub 和系统检查。当前 fork 基于 [irmia2026/irmia_devkit_open](https://github.com/irmia2026/irmia_devkit_open)，使用 AGPL-3.0，保留原作者归属。

这不是 AstrBot 插件的安装入口。完整中文说明、MCP 配置、依赖与工具列表见 [README.zh-CN.md](README.zh-CN.md)。

## 启动

需要 Python >=3.10。npm launcher 需要 Node，用于定位 Python 并调用 bootstrap；首次运行创建本地隔离环境并安装依赖。已有依赖环境可直接运行：

```sh
python server.py
```

默认使用 stdio；日志写 stderr，不占用协议 stdout。HTTP 启动参数与绑定限制见中文说明。不要把本地工具服务未经额外访问控制暴露到公网。

## 当前接口

- safe_edit 支持精确替换、发生次数消歧、行号插入/删除、备份和失败恢复；new 空串是合法删除内容。
- 新语言语法检查与 safe_edit/safe_write/multi_edit 共用调度；缺少检查器明确 skipped，不报假通过。
- safe_read 默认有行号、无额外元数据；file_patch/file_preview 公开缩进和 occurrence 参数。
- HTTP 支持有界解压、编码检测、有限 GET 重试、分页缓存和 SSRF 过滤，POST 不重试。
- 代码索引保留增量删除一致性、FTS、真实反向 BFS 深度；静态调用图不是运行时的完整调用关系。
- 数据库查询有引擎层只读、绑定参数与行数上限；Git/GitHub 不自动获得提交/推送授权。

## 维护

- [架构](ARCHITECTURE.md)
- [上游对齐](UPSTREAM_ALIGNMENT.md)
- [更新记录](CHANGELOG.md)
- [贡献指南](CONTRIBUTING.md)

本仓库工具共享实现保留上游模块；实际 MCP 工具 schema 由 server.py 定义，不能用 AstrBot 注册表或历史工具计数代替公开接口测试。
