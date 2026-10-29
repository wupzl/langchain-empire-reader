"""Run manuscript examples with installed frameworks and no external services."""
from pathlib import Path
from contextlib import redirect_stdout
from tempfile import TemporaryDirectory
import ast
import importlib.metadata
import io
import json
import os
import re
import socket

ROOT = Path(__file__).resolve().parents[1]
os.environ['LANGSMITH_TRACING'] = 'false'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'


def main():
    def deny_network(*args,**kwargs):
        raise AssertionError('Offline example attempted a network connection')
    socket.socket.connect = deny_network
    audit = json.loads((ROOT/'CONTENT_REVIEW.json').read_text(encoding='utf-8'))
    codes = {}
    python_count = 0
    for item in audit['chapters']:
        chapter = ROOT/'chapters'/f'{item["chapter"]:02}.md'
        matches = re.findall(r'```([^\n]*)\n(.*?)```',chapter.read_text(encoding='utf-8'),re.S)
        assert len(matches) == len(item['blocks'])
        for info,(lang,code) in zip(item['blocks'],matches):
            codes[info['source_index']] = code
            if lang == 'python':
                ast.parse(code)
                python_count += 1

    from langchain_core.language_models.fake_chat_models import FakeListChatModel
    from langchain_core.messages import AIMessage, ToolMessage
    from langchain.tools import tool
    from langchain_core.embeddings import Embeddings
    from langchain_core.vectorstores import InMemoryVectorStore
    from langgraph.graph import StateGraph,START,END
    from langgraph.checkpoint.memory import InMemorySaver
    from langgraph.types import Command

    namespace = {}
    lcel = re.sub(r'^model = ChatOpenAI\([^\n]+\)', 'model = FakeListChatModel(responses=["离线架构分析"])', codes[7], flags=re.M)
    namespace['FakeListChatModel'] = FakeListChatModel
    with redirect_stdout(io.StringIO()):
        exec(compile(lcel,'chapter-1-lcel','exec'),namespace)
    assert namespace['result'] == '离线架构分析'

    namespace = {}
    exec(codes[19],namespace)
    @tool
    def add(left:int,right:int)->int:
        """Add two integers."""
        return left+right
    class ScriptedModel:
        def __init__(self,loop=False):
            self.calls = 0
            self.loop = loop
            self.messages = None
        def bind_tools(self,tools):
            assert tools == [add]
            return self
        def invoke(self,messages):
            self.calls += 1
            self.messages = messages[:]
            if self.calls == 1 or self.loop:
                return AIMessage(content='',tool_calls=[{'name':'add','args':{'left':2,'right':3},'id':f'call-{self.calls}','type':'tool_call'}])
            assert isinstance(messages[-1],ToolMessage)
            assert messages[-1].tool_call_id == 'call-1'
            assert messages[-1].content == '5'
            return AIMessage(content='5')
    allowed = []
    model = ScriptedModel()
    assert namespace['run_agent'](model,[add],'2+3',lambda name,args:allowed.append(name)) == '5'
    assert allowed == ['add'] and model.calls == 2
    def denied(name,args):
        raise PermissionError('Denied by application')
    try:
        namespace['run_agent'](ScriptedModel(),[add],'2+3',denied)
        raise AssertionError('Authorization refusal was ignored')
    except PermissionError:
        pass
    try:
        namespace['run_agent'](ScriptedModel(loop=True),[add],'2+3',lambda name,args:None,max_steps=2)
        raise AssertionError('Budget did not terminate the loop')
    except RuntimeError as error:
        assert 'budget' in str(error)
    with TemporaryDirectory() as directory:
        workspace = Path(directory)/'demo-project'
        workspace.mkdir()
        (workspace/'UserService.java').write_text('class UserService {}',encoding='utf-8')
        source = re.sub(r'^WORKSPACE = .+$','WORKSPACE = Path(workspace_path)',codes[21],flags=re.M)
        namespace = {'workspace_path':str(workspace)}
        exec(source,namespace)
        assert namespace['list_java_files'].invoke({}) == 'UserService.java'
        assert namespace['search_class'].invoke({'class_name':'UserService'}) == 'UserService.java'
        assert namespace['search_class'].invoke({'class_name':'../outside'}) == 'Invalid class name'

    # Construct the high-level agent with an inert model; no provider request is made.
    from langchain.agents import create_agent
    from langchain_openai import ChatOpenAI
    agent = create_agent(model=ChatOpenAI(model='offline-placeholder',api_key='offline-placeholder'),tools=[add])
    assert agent is not None
    namespace = {}
    with redirect_stdout(io.StringIO()):
        exec(codes[62],namespace)
    assert namespace['memory'].value['language'] == 'Java'
    from langgraph.store.memory import InMemoryStore
    assert InMemoryStore().get(('projects','order-service'),'coding-rules') is None

    # Use deterministic local vectors to test the real vector-store API.
    class KeywordEmbeddings(Embeddings):
        def embed_documents(self,texts):
            return [self.embed_query(text) for text in texts]
        def embed_query(self,text):
            return [float('库存' in text),float('认证' in text),0.1]
    namespace = {}
    with redirect_stdout(io.StringIO()):
        exec(codes[83],namespace)
    assert namespace['chunks'] and all(c.metadata['source']=='inventory_rules.md' for c in namespace['chunks'])
    store = InMemoryVectorStore(embedding=KeywordEmbeddings())
    store.add_documents(namespace['chunks'])
    retrieved = store.as_retriever(search_kwargs={'k':1}).invoke('库存扣减')
    assert len(retrieved) == 1 and retrieved[0].metadata['source']=='inventory_rules.md'

    for condition,attempts,label in [('>= 2',2,'候选修复通过模拟测试'),('>= 1',1,'候选修复通过模拟测试'),('>= 99',3,'超过最大自动修复次数')]:
        namespace = {}
        with redirect_stdout(io.StringIO()):
            exec(codes[115].replace('>= 2',condition),namespace)
        assert namespace['result']['attempts'] == attempts,namespace['result']
        assert namespace['result']['result'] == label
    # The same actual interrupt node handles approve and refuse on isolated threads.
    namespace = {}
    exec(codes[124],namespace)
    builder = StateGraph(dict)
    builder.add_node('approval',namespace['approve_patch'])
    builder.add_edge(START,'approval')
    builder.add_edge('approval',END)
    graph = builder.compile(checkpointer=InMemorySaver())
    for approved in (True,False):
        config = {'configurable':{'thread_id':f'offline-approval-{approved}'}}
        first = graph.invoke({'task_id':'test','patch':'candidate'},config)
        assert first.get('__interrupt__')
        resumed = graph.invoke(Command(resume={'approved':approved}),config)
        assert resumed['approved'] is approved

    versions = {name:importlib.metadata.version(name) for name in ['langchain','langchain-core','langgraph','langchain-openai','langchain-text-splitters']}
    print(json.dumps({'status':'PASS','python_blocks_parsed':python_count,'checks':['LCEL composition','tool arguments/results/call IDs','authorization rejection','step budget','Java class search tool','agent API construction','in-memory Store','splitter metadata','vector retrieval','graph success/retry/exhaustion','interrupt approve/refuse'],'versions':versions},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
