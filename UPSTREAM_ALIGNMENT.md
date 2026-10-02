# 上游对齐基线

Open 基线：98402645c99638a3e8c7d98ef2236ebfd1809194（新增多语言语法检查）；MCP 改动前基线：73913520f1e4461f173fdb05d03c6b7bbbaa31f8。当前工作树按 v2.7.3 更新，尚未发布。

## 合并与修正

合并新语言检查路由；编辑、覆盖和批量编辑使用同一后缀判断。skipped 优先于 ok，syntax_ok=null 表示未检查。保留 JSX/TSX 的合法文件跳过保护。Java 改用 JavacTask.parse，修正上游 javac 内部选项在 JDK 8 仍检查类名和依赖的误报；辅助源码作为 npm/wheel 资产分发。Python 仅 ast.parse，不通过 py_compile 生成目标编译产物。

MCP 公开参数补齐 safe_edit 行号模式/align_whitespace、file_patch/file_preview occurrence/preserve_inner_indent、safe_read line_numbers。include_metadata 默认 false。file_zip 增加列表来源并保留 source，http_post 允许对象；下载文案说明固定落点。后续 file_diff 参数映射到 MCP file1/file2。

## 保留 fork 修复

没有覆盖 MCP 的 GBK 探测、Windows 路径标准化、HTTP 扩展网段与隐式代理关闭、索引全量版本地图和 BFS 深度、查询型 PRAGMA、搜索二进制/Everything 回退、删除确认/批量重名、Git 参数校验、测试进程树与 stdin 隔离、尾部读取行号和截断分页修复。

当前入口仍是 60 个合并工具，不为对齐 Open 的 65 个数字拆分 github/csv_tool/git_info。safe_read 当前不提供目录递归参数，历史文案不能用作运行时接口依据。

## DSH 重写交接

使用当前 server.py 的参数与关键结果字段，以及 tests/fixtures/alignment-scenes.json 和 tests/test_alignment_contracts.py。原生 DSH 只选旧9工具加独立 syntax_check，不移植全部60工具。未提交时交接使用原基线 SHA、diff 与文件哈希，不擅自生成 commit。
