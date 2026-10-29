"""One-time manuscript import. Run before editing chapters, never during normal builds."""
from pathlib import Path
import ast
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
TITLES = [
    '失控的 API——当大模型不再只是聊天',
    '工具觉醒——让大模型拥有双手',
    '记忆迷宫——当 Agent 开始遗忘',
    '知识图书馆——当 Agent 学会检索世界',
    '命运之图——LangGraph 与 Agent 的执行法则',
]
TOPICS = [
    '模型抽象 · LCEL · LangChain4j',
    'Tool Calling · ReAct · Agent Loop',
    'Chat History · Memory · Checkpoint',
    'RAG · 混合检索 · 精排与评测',
    'StateGraph · Reducer · Interrupt',
]
NOTES = [
    '本书以 LangChain v1 的 Agent API 为主要语境，保留 LCEL 的组合思想。Java 与 Python 属于不同生态。模型名为占位符，使用前请按供应商配置密钥及可用模型。',
    '工具调用是行动请求，由应用运行时执行。示例区分供应商原始 JSON 与 LangChain 标准化 tool_calls；工具白名单不能替代租户授权、执行隔离或预算控制。',
    'ChatMemory 保存当前窗口，不等于完整历史。InMemorySaver 与 InMemoryStore 仅保存在进程内；重启恢复需要持久化后端，thread_id 不能替代身份和权限校验。',
    'RAG 不会自动保证事实正确。示例中的向量库保存在内存，未实现多租户权限与生产索引。公式和评测数字均为教学示例，线上应以自己的数据集验证。',
    '最小 StateGraph 示例不调用模型，第二次通过是人为设定的测试结果。Checkpoint 不会回滚外部世界；审批恢复需要同一 Thread、可靠持久化及副作用幂等处理。',
]

REPAIRS = {
    7: '''from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. 初始化模型；先配置 OPENAI_API_KEY，并替换为可用模型名。
model = ChatOpenAI(model="your-model-name", temperature=0.2)

# 2. 创建 Prompt 模板。
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一名资深软件架构师。"),
    ("human", "请分析以下需求：{requirement}"),
])

# 3. 创建输出解析器并组合可运行组件。
parser = StrOutputParser()
chain = prompt | model | parser

# 4. 执行。
result = chain.invoke({"requirement": "开发一个企业级 RAG 系统"})
print(result)
''',
    11: '''for chunk in chain.stream(input_data):
    print(chunk, end="", flush=True)
''',
    19: '''from langchain_core.messages import HumanMessage, ToolMessage

def run_agent(model, tools, question, authorize, max_steps=8):
    """authorize(name, args) 由应用实现；未授权时必须抛出异常。"""
    registry = {tool.name: tool for tool in tools}
    bound_model = model.bind_tools(tools)
    messages = [HumanMessage(content=question)]

    for _ in range(max_steps):
        response = bound_model.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content

        for call in response.tool_calls:
            # 这里使用 LangChain 标准化字典，而非供应商的 function JSON。
            name, args = call["name"], call["args"]
            if name not in registry:
                raise ValueError(f"Unknown tool: {name}")
            authorize(name, args)
            # BaseTool.invoke 校验工具输入；错误在本示例中向外抛出并终止。
            result = registry[name].invoke(args)
            messages.append(ToolMessage(
                content=str(result), tool_call_id=call["id"]
            ))

    raise RuntimeError("Agent step budget exhausted")
''',
}


def language(code, index):
    if index == 75:
        return 'markdown'
    if index == 107 or index in {108, 109, 112, 113, 114, 115, 118, 119, 120, 121, 124, 125}:
        return 'python'
    if re.search(r'^(from |import (?:os|operator)|def |for chunk|chain =|result =|results =|agent\.|other_config|store =|namespace =|chunks =|embeddings =|vector_store|retriever =|prompt =|model =|answer =|docs =|chunk_size|chunk_overlap|document =)', code, re.M):
        return 'python'
    if re.search(r'^(@\w+|public |private |import dev\.|var |CodingAssistant |KnowledgeAssistant |ContentRetriever |String answer|assistant\.|System\.out)', code, re.M):
        return 'java'
    if code.strip().startswith(('{', '[')):
        try:
            json.loads(code)
            return 'json'
        except ValueError:
            pass
    if re.match(r'(CREATE TABLE|ALTER TABLE|UPDATE inventory)', code):
        return 'sql'
    if code.startswith('pip install'):
        return 'bash'
    return 'text'


def clean_prose(prose, chapter):
    prose = re.sub(r'^\[image\]\(https://www\.google\.com/[^\n]+\)\s*$', '', prose, flags=re.M)
    prose = re.sub(r'^(?:GitHub|LangChain4j)\+\d+\s*$', '', prose, flags=re.M)
    prose = re.sub(r'^\d{1,2}\s*$', '', prose, flags=re.M)
    prose = prose.replace('&#x20;', '').replace(r'\@', '@').replace(r'\&', '&')
    prose = prose.replace('?utm_source=chatgpt.com', '')
    # Preserve source media as optional links, rather than relying on temporary image URLs.
    prose = re.sub(r'^\[([^\]]+)\]\((https://images\.openai\.com/[^\n]+)\)\s*$', r'[原文配图：\1](\2)', prose, flags=re.M)
    prose = re.sub(r'\\{2,}([\[\]()|])', lambda m: '\\' + m[1], prose)
    prose = prose.replace(r'\_', '_')
    prose = re.sub(r'^# 《LangChain 帝国》\s*$', '', prose, flags=re.M)
    prose = re.sub(r'^第一卷：[^\n]+\n', '', prose, flags=re.M)
    prose = re.sub(r'^下一章。\s*$', '', prose, flags=re.M)
    prose = re.sub(r'^第[一二三四五]章，完。\s*$', '', prose, flags=re.M)
    prose = re.sub(r'^模拟技术面试[^\n]*\n\s*基础理解\s*', '', prose, flags=re.M)
    prose = prose.replace('查看参考答案下一题', '')
    prose = prose.replace('周衡在白板上写下了一段伪代码。', '周衡写下一段简化的 Python 工具循环。`authorize` 由应用提供，用于校验当前主体是否允许执行具体操作；异常在这个示例中直接终止任务。')
    prose = prose.replace('“那你需要另外设计持久化存储。”', '“完整历史需要独立的追加存档；ChatMemoryStore 负责持久化当前记忆窗口，窗口淘汰也会影响存储内容，不能用它替代全量历史。”')
    prose = prose.replace('“注意这里的 Redis。”', '“我们还可以考虑 Redis。”')
    if chapter == 3:
        prose = re.sub(r'### 交互实验：分配上下文预算.*?(?=这是用于理解预算)', '''### 上下文预算示例

| 用途 | Token 预算 |
| --- | ---: |
| 历史对话 | 40,000 |
| 检索文档 | 30,000 |
| 工具与系统开销 | 8,000 |
| 输出预留 | 16,000 |
| 已分配 | 94,000（约 73.4%） |
| 剩余容量 | 34,000 |

总容量假设为 128,000 Token。

''', prose, flags=re.S)
        prose = prose.replace('林远拖动了滑块。', '林远调整了表中的预算。')
    if chapter == 4:
        prose = re.sub(r'二维语义空间示意.*?(?=林远看着屏幕)', '''向量空间可以帮助理解“语义邻近”：库存超卖、JWT 认证和慢 SQL 是不同的查询方向；同义表达可能靠近，但这不代表两个文本拥有相同的事实判断。

这里是概念说明，没有实际 Embedding 坐标或检索结果。

''', prose, flags=re.S)
        prose = re.sub(r'### 一场 A/B 实验.*?(?=林远看完后说道)', '''### 如何报告一场检索实验

原文导出的实验控件只保留了一个结果面板，缺少完整的对照组，不能据此宣称性能提升。

| 教学示例中的单组指标 | 假设值 |
| --- | ---: |
| Recall@5 | 86% |
| Precision@5 | 70% |
| 检索延迟 | 145 ms |

这些是用于讨论取舍的虚构数字。要做有效比较，应在同一标注数据集上分别报告纯向量、混合检索、混合检索加精排的逐题结果、平均指标、延迟分位数及成本。精排只重排固定候选池时，不会增加该候选池包含的相关文档，但可能改变最终 Top K 的召回率。

''', prose, flags=re.S)
        prose = prose.replace('SET stock = stock - :quantity', 'SET stock = stock - :quantity')
    if chapter == 5:
        prose = re.sub(r'### 交互实验：Bug 修复状态机.*?(?=林远看着第三次失败)', '''### Bug 修复状态机示例

| 当前结果 | 下一条路径 |
| --- | --- |
| 验证通过 | 结束并保存证据 |
| 验证失败，累计尝试小于 3 次 | 分析失败，再生成候选修复 |
| 验证失败，累计尝试达到 3 次 | 停止自动修复并报告失败 |

这里的三次是总尝试上限（包含首次尝试），即最多再重试两次。真实系统还需区分模型失败、构建环境失败和测试失败，并独立设置时间与成本预算。

''', prose, flags=re.S)
        prose = re.sub(r'### 人工审批演示.*?(?=林远问：)', '''### 人工审批示例

待审批的候选操作是在 `inventory` 表中新增 `version` 字段。应用应记录补丁摘要、目标版本、审批身份与决定；拒绝时终止这条变更路径，批准后仍须重新检查权限、补丁版本及执行条件。

这里未连接数据库，也未执行 Schema 变更。

''', prose, flags=re.S)
    # Demote duplicate book/preview headings, preserving prose outside code fences.
    prose = re.sub(r'^# (.+)$', r'### \1', prose, flags=re.M)
    return prose


def main():
    (ROOT / 'source').mkdir(exist_ok=True)
    (ROOT / 'chapters').mkdir(exist_ok=True)
    original = ROOT / 'source/langchain.original.md'
    if not original.exists():
        shutil.copyfile(ROOT.parent / 'langchain.md', original)
    source = original.read_text(encoding='utf-8-sig')
    # Identify actual chapter starts, ignoring code headings and next-chapter previews.
    starts = [source.index('# 第一章：'), source.index('# 第二章：')]
    for title in TITLES[2:]:
        starts.append(source.index('# ' + title))
    all_blocks = list(re.finditer(r'```([^\n]*)\n(.*?)```', source, re.S))
    index_by_start = {m.start(): i for i, m in enumerate(all_blocks, 1)}
    report = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(source)
        text = source[start:end].split('\n', 1)[1]
        # Strip the appended next chapter's repeated book/volume header.
        text = re.sub(r'\n# 《LangChain 帝国》\s*第一卷：[^\n]+\s*$', '', text)
        blocks = []
        def stash(match):
            # Locate globally by monotonically walked block positions, never body text.
            absolute = next(m for m in all_blocks if start <= m.start() < end and m[0] == match[0] and m.start() not in used)
            used.add(absolute.start())
            number = index_by_start[absolute.start()]
            body = REPAIRS.get(number, match[2]).strip() + '\n'
            if number == 21:
                body = body.replace('if p.is_file()', 'if p.is_file() and p.resolve().is_relative_to(WORKSPACE)')
            if number == 22:
                body = body.replace('result = agent.invoke({', 'result = agent.invoke({').replace('\n})\n\nprint', '\n}, config={"recursion_limit": 12})\n\nprint')
            if number == 88:
                body = body.rstrip() + ' numpy\n'
            if number == 101:
                body += '\n-- :quantity 必须为正数；检查影响行数，并另行实现订单级幂等。\n'
            lang = language(body, number)
            if lang == 'python':
                ast.parse(body)
            blocks.append({'number':number, 'language':lang, 'code':body})
            return f'\nCODEBLOCKPLACEHOLDER{len(blocks)-1}END\n'
        used = set()
        text = re.sub(r'```([^\n]*)\n(.*?)```', stash, text, flags=re.S)
        text = clean_prose(text, i+1)
        # Replace exported multiple-choice controls with an actual written explanation.
        answers = [
            ('LangChain 和直接调用大模型 API 有什么区别？', '直接调用 API 获取模型能力；LangChain 为模型、消息、工具、检索和 Agent 提供统一抽象与组合方式。鉴权、限流、业务数据和质量验证仍需应用负责。'),
            ('模型返回一个 tool_call 后，究竟是谁执行 Java 方法？', '执行 Java 方法的是应用侧 Runtime 或 LangChain4j AI Services 的工具执行层。模型只返回调用意图；运行时需校验参数和权限，执行方法后再把结果交回模型。'),
            ('MySQL 保存了全部历史消息，为什么模型仍然可能忘记早期信息？', '持久化不等于上下文注入。模型只能使用本次请求提供的消息与证据；应用需要按分支选择、预算裁剪、摘要或检索历史，并保留完整的工具调用与结果配对。'),
            ('如果文档里有精确错误码 ORDER-INV-4096，哪种检索能力尤其值得加入？', '关键词或 BM25 检索能直接利用精确错误码等词项信号。可以与向量检索融合，再用同一测试集验证召回、排序质量与延迟。'),
            ('LangGraph 相比普通顺序 Chain，最核心的工程优势是什么？', 'LangGraph 显式管理状态、节点与路径，支持条件分支、循环、并行、检查点和中断恢复。是否值得使用取决于流程复杂度，并不意味着顺序任务必须改成图。'),
        ]
        question, answer = answers[i]
        marker = '## ' + question
        if marker in text:
            tail = text.index(marker) + len(marker)
            next_section = text.find('\n## ', tail)
            if next_section == -1:
                next_section = len(text)
            text = text[:tail] + '\n\n**参考思路：**' + answer + '\n\n' + text[next_section:]
        for j, block in enumerate(blocks):
            text = text.replace(f'CODEBLOCKPLACEHOLDER{j}END', f'```{block["language"]}\n{block["code"]}```')
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        text = '# 第' + '一二三四五'[i] + '章：' + TITLES[i] + '\n\n' + text + '\n'
        (ROOT / 'chapters' / f'{i+1:02}.md').write_text(text, encoding='utf-8')
        report.append({'chapter':i+1,'characters':len(text),'blocks':[{'source_index':b['number'],'language':b['language'],'repaired':b['number'] in REPAIRS or b['number'] in (21,22,88,101)} for b in blocks]})
    book = {'title':'LangChain 帝国','slug':'langchain-empire-reader','status':'连载','nextChapter':6,'chapters':[{'number':i+1,'title':t,'topics':TOPICS[i],'note':NOTES[i]} for i,t in enumerate(TITLES)]}
    (ROOT / 'book.json').write_text(json.dumps(book, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    audit = {'source':'source/langchain.original.md','sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'chapterCount':5,'nextChapter':'黑匣子审判——LangSmith 与 Agent 的可观测性（仅预告）','reviewDate':'2026-10-29','chapters':report}
    (ROOT / 'CONTENT_REVIEW.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Prepared five chapters; original manuscript preserved byte for byte.')


if __name__ == '__main__':
    main()
