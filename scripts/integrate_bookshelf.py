"""Connect this book to sibling readers and the shelf. Does not commit or push."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[2]
BOOK = ROOT / 'langchain-empire-reader'
SLUG = BOOK.name
READERS = ['pytorch-apprentice','ai-era-reader','data-empire-reader','rag-empire-reader','system-design-reader','online-troubleshooting-reader','coding-agent-reader','interview-proof-reader']
CHANGED = {}
LINK = f'<a href="/{SLUG}/">LangChain 帝国</a>'


def edit(path, transform):
    old = path.read_text(encoding='utf-8')
    new = transform(old)
    if old != new:
        path.write_text(new,encoding='utf-8')
        repo = path.relative_to(ROOT).parts[0]
        CHANGED.setdefault(repo,[]).append(path.relative_to(ROOT/repo).as_posix())


def menus(text):
    return re.sub(r'<div class="shelf-menu">(.*?)</div>',lambda m:m[0] if f'/{SLUG}/' in m[1] else f'<div class="shelf-menu">{m[1]}{LINK}</div>',text,flags=re.S)


def generator(text):
    if f"('{SLUG}'" in text:
        return text
    pattern = r"\('interview-proof-reader',\s*'面试官的审判'\)"
    text,count = re.subn(pattern,lambda m:m[0]+f", ('{SLUG}', 'LangChain 帝国')",text,count=1)
    assert count == 1, 'Could not find project list in source generator'
    return text


def main():
    for slug in READERS:
        repo = ROOT/slug
        for page in (repo/'docs').glob('*.html'):
            edit(page,menus)
        if (repo/'build.py').is_file():
            edit(repo/'build.py',menus if slug=='pytorch-apprentice' else generator)
        edit(repo/'README.md',lambda text:text if 'langchain-empire-reader' in text else text+'\n\n项目切换菜单已接入 [LangChain 帝国](https://wupzl.github.io/langchain-empire-reader/)，五章正文，第六章待续。\n')
        if (repo/'verify.py').is_file():
            edit(repo/'verify.py',lambda text:text.replace("page.locator('.shelf-menu a').count() == 8","page.locator('.shelf-menu a').count() == 9").replace("expect(page.locator('.shelf-menu a')).to_have_count(8)","expect(page.locator('.shelf-menu a')).to_have_count(9)"))
    shelf = ROOT/'bookshelf'
    card = '''<a class="project green" href="/langchain-empire-reader/"><div class="cover" aria-hidden="true"><span class="volume">09 / THE LANGCHAIN EMPIRE</span><strong>LangChain<span class="cover-subtitle">帝国</span></strong><span class="symbol">L</span><span class="cover-foot">工具 · 记忆 · 知识 · 执行</span></div><div class="project-copy"><p class="category">LANGCHAIN · 技术小说</p><h3>LangChain 帝国</h3><p>跟随林远与周衡，从失控的 API 走向工具调用、记忆、RAG 与 LangGraph，在故事里理解可靠的智能体工程。</p><div class="tags"><span>5 章 · 第六章待续</span><span class="project-status">连载</span><span>Python 与 Java 应用工程</span></div><span class="enter">进入阅读 <span aria-hidden="true">↗</span></span></div></a>'''
    def home(text):
        if f'/{SLUG}/' not in text:
            marker = '</div><div class="shelf-note">'
            assert marker in text
            text = text.replace(marker,card+marker,1)
        return text.replace('08 / 持续更新','09 / 持续更新')
    edit(shelf/'index.html',home)
    def verifier(text):
        if f"'{SLUG}':" not in text:
            text = text.replace("    'interview-proof-reader': '连载',","    'interview-proof-reader': '连载',\n    'langchain-empire-reader': '连载',")
        marker = "            assert '第八章待续' in page.locator('.project[href=\"/interview-proof-reader/\"] .tags').inner_text()"
        if "assert '第六章待续'" not in text:
            assert marker in text
            text = text.replace(marker,marker+"\n            assert '第六章待续' in page.locator('.project[href=\"/langchain-empire-reader/\"] .tags').inner_text()")
        return re.sub(r'\beight\b','nine',text)
    edit(shelf/'verify.py',verifier)
    def workflow(text):
        if f'repository: wupzl/{SLUG}' not in text:
            marker = '      - uses: actions/setup-python@v5'
            assert marker in text
            text = text.replace(marker,f'      - uses: actions/checkout@v4\n        with:\n          repository: wupzl/{SLUG}\n          ref: main\n          path: {SLUG}\n'+marker,1)
            marker = '      - name: Verify system design reader'
            text = text.replace(marker,'      - name: Verify LangChain reader features\n        run: python langchain-empire-reader/verify.py\n'+marker,1)
            text = text.replace('            interview-proof-reader/test-results/','            interview-proof-reader/test-results/\n            langchain-empire-reader/test-results/')
        return text.replace('all eight readers','all nine readers')
    edit(shelf/'.github/workflows/verify-readers.yml',workflow)
    edit(shelf/'README.md',lambda text:text.replace('面试官的审判八个阅读项目','面试官的审判和 LangChain 帝国九个阅读项目').replace('其余八个仓库','其余九个仓库').replace('八项目切换菜单','九项目切换菜单').replace('八个阅读仓库','九个阅读仓库').replace('`interview-proof-reader/` 目录中','`interview-proof-reader/`、`langchain-empire-reader/` 目录中').replace('面试官的审判 7 章（连载，第八章待续）。','面试官的审判 7 章（连载，第八章待续）、LangChain 帝国 5 章（连载，第六章待续）。')+ ('\nLangChain 帝国完整阅读验收：`python langchain-empire-reader/verify.py`。\n' if 'LangChain 帝国完整阅读验收' not in text else ''))
    manifest = BOOK/'integration-files.json'
    prior = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    for name,paths in CHANGED.items():
        prior[name] = sorted(set(prior.get(name,[])+paths))
    manifest.write_text(json.dumps(prior,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Integrated {len(READERS)} readers and bookshelf; changed {sum(map(len,CHANGED.values()))} files.')


if __name__ == '__main__':
    main()
