# 内容说明与技术来源

《LangChain 帝国》以林远与周衡的故事讲解 AI 应用工程。现有正文五章，第六章《黑匣子审判——LangSmith 与 Agent 的可观测性》只有预告。项目不续写尚未提供的章节。

本次技术核验日期为 **2026 年 10 月 29 日**。以 LangChain v1 的高层 Agent API 为主要语境，区分 Python LangChain、LangGraph 与 Java LangChain4j；它们的版本、依赖与 API 不可直接混用。

## 第一章：模型调用与组件组合 {#chapter-1}

- 修复原文挤成一行的 Python 导入、注释、Prompt 与执行代码，恢复 `prompt | model | parser` 示例。
- `invoke`、`batch`、`stream` 是 Runnable 组合接口；链中的某个组件不支持逐块输出时，会影响流式结果的到达时机。
- 直接调用模型 API 与使用框架都可构建应用。框架提供抽象、组合和集成，业务鉴权、配额与质量保障仍需应用实现。
- `your-model-name` 是占位符；模型调用示例需要自行配置供应商密钥和有权访问的模型，不能把示例名称当作真实服务。

来源：[LangChain 概览](https://docs.langchain.com/oss/python/langchain/overview)、[Runnable API](https://reference.langchain.com/python/langchain-core/runnables/base/Runnable)、[LangChain4j 简介](https://docs.langchain4j.dev/intro/)。

## 第二章：工具调用与执行边界 {#chapter-2}

- 区分供应商原始响应中嵌套的 `function.arguments` 字符串，与 LangChain `AIMessage.tool_calls` 的 `name`、`args`、`id` 字段。
- 将原文的概念循环改为有函数边界的 Python 示例，使用 `model.bind_tools`、工具注册表、`BaseTool.invoke` 与带 `tool_call_id` 的 `ToolMessage`。外部传入的 `authorize` 回调负责业务授权；拒绝授权或工具异常时示例终止，不伪造成功结果。
- 示例按模型调用轮数设置上限。真实系统还应限制工具调用总数、单次输出、时间和成本，并设计异常反馈及取消机制。
- Java 类名搜索示例过滤解析后位于工作区之外的路径，并为高层 Agent 添加运行步数限制。路径检查属于演示约束，不能作为运行任意不可信仓库的沙箱证明。
- LangChain4j 的 `@Tool` 方法由应用侧执行层调用；`CodeSearchService`、`ChatModel` 等需由读者的应用提供。展示直接执行 Shell 的片段是原文中的危险反例。

来源：[LangChain Tools](https://docs.langchain.com/oss/python/langchain/tools)、[模型工具调用](https://docs.langchain.com/oss/python/langchain/models#tool-calling)、[LangChain4j Tools](https://docs.langchain4j.dev/tutorials/tools/)。

## 第三章：历史、记忆与持久化 {#chapter-3}

- 明确完整历史存档与当前记忆窗口的区别：`ChatMemoryStore` 持久化的是当前窗口，窗口淘汰会改变存储内容；它不是全量聊天历史的追加日志。
- `InMemorySaver` 与 `InMemoryStore` 是进程内演示实现，重启后不能保留数据。跨实例或重启恢复需要持久化后端与并发控制。
- `thread_id` 用于区分执行线程，不提供身份认证或租户隔离。应用必须把请求主体与有权访问的会话、任务或命名空间绑定。
- 修复过度转义的 Token 预算公式，将丢失滑块的内容改成可阅读的预算表：已分配 94,000 / 128,000，约 73.4%，剩余 34,000 Token。实际模型对上下文、输出和推理预算的限制需查对应供应商文档。
- 数据库代码保留为接口骨架；抛出 `UnsupportedOperationException` 的方法尚未实现。

来源：[LangChain 短期记忆](https://docs.langchain.com/oss/python/langchain/short-term-memory)、[LangGraph 持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[LangChain4j Chat Memory](https://docs.langchain4j.dev/tutorials/chat-memory/)。

## 第四章：检索与评测 {#chapter-4}

- 保留 `Document`、`RecursiveCharacterTextSplitter`、`InMemoryVectorStore` 与 Retriever 的基础工作流。默认字符切分的 `chunk_size` 不是 Token 数；按 Token 切分需要对应计数配置。
- 离线运行发现内存向量检索的余弦计算还需要 NumPy，已在安装命令和示例依赖中补齐。
- 向量相近不等于事实相同；关键词/BM25、向量召回与精排提供不同信号，不能保证叠加后必然优于任意基线。
- 修复余弦相似度、BM25、RRF、Recall@K 与 Precision@K 的公式转义，按教学简化公式呈现。
- 原文 A/B 控件缺少完整对照组。保留 86%、70%、145 ms 为**单组虚构数据**，删除据此宣称性能提升的表述。精排固定候选池不会改变池内相关文档总数，但可能改变最终 Top K 的召回。
- 库存扣减 SQL 需要正的扣减数量、影响行数检查与独立的业务幂等设计。它不是完整订单事务方案。
- RAG 最小示例依赖外部 Embedding 与聊天模型；内存向量库没有实现生产级索引、权限校验和文档更新生命周期。

来源：[LangChain 检索](https://docs.langchain.com/oss/python/langchain/retrieval)、[文本切分](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter)、[InMemoryVectorStore API](https://reference.langchain.com/python/langchain-core/vectorstores/in_memory/InMemoryVectorStore)、[LangChain4j RAG](https://docs.langchain4j.dev/tutorials/rag/)、[Elasticsearch BM25](https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity)、[Elasticsearch RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion)。

## 第五章：状态、恢复与审批 {#chapter-5}

- 保留无需模型即可运行的最小 StateGraph。第二次验证通过由示例代码人为设置，不代表实际修复 Bug。
- 统一次数语义：上限三次包含首次尝试，即最多再重试两次，避免把总尝试数与重试数混为一谈。
- Reducer 定义状态合并规则；列表追加不自动去重，也不保证符合业务要求的排序。
- 持久化恢复不等于任意外部副作用的 exactly-once。文件、数据库和 Git 等外部状态需额外进行幂等保护、版本检查与对账。
- `Command(resume=...)` 需关联同一线程中已存在的中断；恢复会重新进入节点，`interrupt()` 前的副作用可能再次执行。批准后还应核对实际操作与审批对象的一致性。
- 原文残缺的状态机与审批控件改为静态表格和流程说明。Java 部分是应用层接口设计，不能直接作为 Python LangGraph API 的 Java 用法。

来源：[LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)、[持久化](https://docs.langchain.com/oss/python/langgraph/persistence)、[中断与恢复](https://docs.langchain.com/oss/python/langgraph/interrupts)、[LangGraph4j 项目](https://github.com/langgraph4j/langgraph4j)。

## 整理方式与验证范围

保留人物、叙事顺序和五章主体。清除重复书名、对话分隔、引用图标、计数残留以及失效按钮文字。原文配图保留为可选链接，正文与公式阅读无需加载第三方图片。章末问题补充书面参考思路。

原始 Markdown 按字节保存在 `source/langchain.original.md`，源文件校验值与各代码块处理记录见仓库 `CONTENT_REVIEW.json`。维护章节时编辑 `chapters/01.md` 至 `05.md`，再生成静态网站。

网站检查覆盖搜索、代码复制、字号、三种主题、阅读进度、章节锚点及手机/平板/桌面布局。Python 示例的离线检查覆盖语法、工具调用与消息配对、进程内存储、切分检索、状态图分支及中断恢复；外部模型与 Embedding 服务未进行付费调用。Java 代码按官方 API 对照审阅，业务服务与数据库骨架未作为完整 Spring Boot 应用编译运行。

## 阅读记录

网站无需登录。主题、字号与阅读位置保存在当前浏览器，使用本书独立的存储前缀，不会跨设备同步。在“我的阅读”中可查看或清除本书进度。
