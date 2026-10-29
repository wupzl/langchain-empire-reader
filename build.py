"""Build a standalone static reader. Builds never re-import or modify the manuscript."""
from pathlib import Path
import html
import json
import re
import shutil
import subprocess

import markdown
from pygments.formatters import HtmlFormatter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'docs'
BOOK = json.loads((ROOT / 'book.json').read_text(encoding='utf-8'))
CHAPTERS = BOOK['chapters']
PROJECTS = [('pytorch-apprentice','PyTorch：炼金术士的学徒'),('ai-era-reader','AI 纪元'),('data-empire-reader','数据帝国'),('rag-empire-reader','RAG 帝国'),('system-design-reader','系统设计'),('online-troubleshooting-reader','生产环境'),('coding-agent-reader','Agent 帝国'),('interview-proof-reader','面试官的审判'),('langchain-empire-reader','LangChain 帝国')]


def page(title, body, chapter=0):
    menu = ''.join(f'<a href="/{slug}/"'+(' aria-current="page"' if slug == BOOK['slug'] else '')+f'>{label}</a>' for slug,label in PROJECTS)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><meta name="description" content="LangChain 帝国：五章小说式工程阅读，从模型调用走向 Tools、Memory、RAG 与 LangGraph。"><title>{html.escape(title)} · LangChain 帝国</title><script>try{{let t=localStorage.getItem('langchain-empire-theme');document.documentElement.dataset.theme=['white','light','dark'].includes(t)?t:'white';document.documentElement.style.setProperty('--reading-size',Math.max(16,Math.min(26,Number(localStorage.getItem('langchain-empire-size'))||18))+'px')}}catch(e){{}}</script><link rel="icon" href="favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="shelf-nav.css"><link rel="stylesheet" href="reader.css"><link rel="stylesheet" href="syntax.css"><script src="app.js" defer></script></head>
<body data-chapter="{chapter}"><a class="skip" href="#main">跳到正文</a><div id="progress" aria-hidden="true"></div><header><a class="brand" href="index.html">LangChain 帝国<span>THE LANGCHAIN EMPIRE</span></a><nav class="shelf-nav" aria-label="学习项目导航"><a class="shelf-home" href="/">← 学习书架</a><details class="shelf-switch"><summary>切换项目 ▾</summary><div class="shelf-menu">{menu}</div></details></nav><div class="controls"><button id="search-open" aria-label="搜索全书" title="搜索全书（/）">搜索</button><button id="smaller" aria-label="缩小字号">A−</button><button id="larger" aria-label="增大字号">A＋</button><button id="theme" aria-label="切换阅读背景">纯白</button></div></header>
{body}<footer><a href="index.html">LangChain 帝国</a> · 五章正文 · 第六章待续<br><a href="reading.html">我的阅读</a> · <a href="editorial.html">内容说明与技术来源</a> · <a href="https://github.com/wupzl/langchain-empire-reader">项目源码 ↗</a><br><small>小说式工程学习 · 无需登录 · 阅读进度保存在当前浏览器</small></footer>
<dialog id="search-dialog" aria-labelledby="search-title"><div class="dialog-heading"><h2 id="search-title">搜索全书</h2><button id="search-close" aria-label="关闭搜索">×</button></div><label for="query">关键词或代码，例如 工具调用、Checkpoint、InMemorySaver</label><input id="query" type="search" placeholder="搜索五章正文…" autocomplete="off"><p id="search-status" role="status">输入关键词开始搜索</p><div id="search-results"></div></dialog><div id="toast" role="status" aria-live="polite"></div></body></html>'''


def render(source):
    formulas = []
    def stash(match):
        formulas.append({'tex':match[1] if match[1] is not None else match[2], 'display':match[1] is not None})
        return f'MATHTOKEN{len(formulas)-1}END'
    pieces = re.split(r'(```.*?```|`[^`\n]+`)', source, flags=re.S)
    for i in range(0,len(pieces),2):
        # Markdown raw HTML is text; only our renderer produces page markup.
        pieces[i] = pieces[i].replace('<','&lt;')
        pieces[i] = re.sub(r'\\\[(.*?)\\\]|\\\((.*?)\\\)', stash, pieces[i], flags=re.S)
    md = markdown.Markdown(extensions=['fenced_code','tables','toc','sane_lists','codehilite','attr_list'], extension_configs={'toc':{'toc_depth':'2-3'},'codehilite':{'guess_lang':False}})
    rendered = md.convert(''.join(pieces))
    if formulas:
        run = subprocess.run(['node',str(ROOT/'render-math.cjs')],input=json.dumps(formulas),capture_output=True,text=True,encoding='utf-8',check=True)
        for i,value in enumerate(json.loads(run.stdout)):
            if 'katex-error' in value:
                raise ValueError(f'Invalid TeX: {formulas[i]["tex"]}')
            rendered = rendered.replace(f'MATHTOKEN{i}END',value)
    rendered = re.sub(r'<div class="codehilite">.*?</div>',lambda m:'<div class="code-block"><button class="copy-code" type="button">复制代码</button>'+m[0]+'</div>',rendered,flags=re.S)
    rendered = re.sub(r'<p><a href="https://images\.openai\.com/.*?</p>',lambda m:'<details class="source-media"><summary>原文配图链接（可选）</summary>'+m[0]+'</details>',rendered,flags=re.S)
    # Preserve wide tables while giving them keyboard access.
    rendered = rendered.replace('<table>', '<div class="table-scroll" tabindex="0" role="region" aria-label="可横向滚动的数据表"><table>').replace('</table>','</table></div>')
    return rendered, md.toc


def main():
    OUT.mkdir(exist_ok=True)
    search = []
    metadata = []
    for item in CHAPTERS:
        n = item['number']
        source = (ROOT/'chapters'/f'{n:02}.md').read_text(encoding='utf-8').split('\n',1)[1]
        rendered,toc = render(source)
        url = f'chapter-{n:02}.html'
        minutes = max(5,round(len(re.sub(r'```.*?```','',source,flags=re.S))/450))
        metadata.append({**item,'url':url,'minutes':minutes})
        booknav = ''.join(f'<a href="chapter-{c["number"]:02}.html"'+(' aria-current="page"' if c['number']==n else '')+f'><span>{c["number"]:02}</span> {html.escape(c["title"])}</a>' for c in CHAPTERS)
        prev = f'<a href="chapter-{n-1:02}.html">← 上一章</a>' if n>1 else '<a href="index.html">← 全书目录</a>'
        nxt = f'<a href="chapter-{n+1:02}.html">下一章 →</a>' if n<len(CHAPTERS) else '<a href="index.html#next-chapter">第六章待续 →</a>'
        body = f'''<div class="reader-layout"><aside><a href="index.html">← 全书导航</a><details class="book-toc"><summary>五章工程旅程</summary><nav aria-label="全书章节">{booknav}</nav></details><p class="eyebrow">本章目录</p>{toc}<a href="reading.html">我的阅读进度 →</a></aside><main id="main" class="chapter-main"><div class="chapter-heading"><p class="eyebrow">CHAPTER {n:02} / 05 · 约 {minutes} 分钟</p><h1>{html.escape(item['title'])}</h1><p>{html.escape(item['topics'])}</p><div class="chapter-tools"><a href="reading.html">我的阅读 →</a><span id="read-status" role="status"></span></div></div><details class="mobile-toc"><summary>章节与本章目录</summary><nav class="book-links">{booknav}</nav>{toc}</details><details class="editor-note"><summary>本章阅读提示</summary><p>{html.escape(item['note'])}</p><a href="editorial.html#chapter-{n}">查看本章技术修订与来源 →</a></details><article>{rendered}</article><nav class="chapter-nav" aria-label="上下章">{prev}{nxt}</nav></main></div>'''
        (OUT/url).write_text(page(item['title'],body,n),encoding='utf-8')
        anchor = ''
        heading = '故事开始'
        for part in re.split(r'(<h[23] id="[^"]+">.*?</h[23]>)',rendered,flags=re.S):
            match = re.fullmatch(r'<h[23] id="([^"]+)">(.*?)</h[23]>',part,flags=re.S)
            if match:
                anchor = match[1]
                heading = html.unescape(re.sub('<[^>]+>','',match[2]))
                continue
            # Exclude copy-control labels and optional illustration URLs from search.
            part = re.sub(r'<button.*?</button>','',part,flags=re.S)
            text = html.unescape(re.sub('<[^>]+>',' ',part))
            text = re.sub(r'\s+',' ',text).strip()
            if text:
                search.append({'chapter':n,'title':item['title'],'section':heading,'url':url+('#'+anchor if anchor else ''),'text':text})
    cards = ''.join(f'<a class="card" href="{c["url"]}"><span class="number">{c["number"]:02}</span><div><h3>{html.escape(c["title"])}</h3><p>{c["topics"]}</p><small>约 {c["minutes"]} 分钟 <span data-chapter-progress="{c["number"]}"></span></small></div><span class="arrow" aria-hidden="true">↗</span></a>' for c in metadata)
    home = f'''<main class="home" id="main"><section class="hero"><p class="eyebrow">一本写给 AI 应用开发者的技术小说</p><h1>从一次模型调用，<br>走向<span>智能体工程。</span></h1><p class="intro">一个会回答问题的模型，距离可靠的应用还有多远？<br>跟随林远与周衡，从失控的 API 出发，走过工具、记忆、知识检索与状态化工作流，在故事里理解 LangChain。</p><a class="start" href="chapter-01.html">从第一章开始阅读 <span>→</span></a><a class="resume" id="resume" hidden href="chapter-01.html">继续上次阅读 →</a><div class="book-mark" aria-hidden="true">LangChain<span>帝 国</span><small>工具 · 记忆 · 知识 · 执行</small></div><p class="hero-note">第一卷：大模型应用的崛起 · 五章正文 · 第六章待续</p></section><nav class="home-links" aria-label="阅读工具"><a href="reading.html">我的阅读进度 ↗</a><a href="editorial.html">内容说明与技术来源 ↗</a></nav><section class="catalog" id="catalog"><div class="section-title"><h2>全书导航</h2><span>5 章 · 按顺序阅读，也可自由探索</span></div><div class="cards">{cards}</div><section id="next-chapter" class="next-chapter"><p class="eyebrow">NEXT CHAPTER · 第六章待续</p><h3>黑匣子审判——LangSmith 与 Agent 的可观测性</h3><p>原文仅提供预告：接下来将走进 Trace、Span、Token 用量、可观测性与 Agent 评测。正文尚未提供。</p></section></section></main>'''
    (OUT/'index.html').write_text(page('全书导航',home),encoding='utf-8')
    reading = '''<main id="main" class="standalone"><p class="eyebrow">YOUR READING DESK</p><h1>我的阅读</h1><p class="intro">进度保存在当前浏览器，可从上次停下的位置继续阅读。</p><section class="reading-section"><h2>阅读进度</h2><div id="reading-progress"></div></section><details class="clear-records"><summary>管理阅读记录</summary><p>清除后无法恢复；字号与主题设置会保留。</p><button id="clear-records" type="button">清除本书阅读记录</button><div id="clear-confirm" hidden><p>确认清除当前浏览器内本书的全部阅读进度？</p><button id="clear-yes" type="button">确认清除</button><button id="clear-no" type="button">取消</button></div></details></main>'''
    (OUT/'reading.html').write_text(page('我的阅读',reading),encoding='utf-8')
    editorial,_ = render((ROOT/'EDITORIAL.md').read_text(encoding='utf-8'))
    (OUT/'editorial.html').write_text(page('内容说明与技术来源','<main id="main" class="standalone"><article>'+editorial+'</article></main>'),encoding='utf-8')
    for name,data in [('chapters.json',metadata),('search.json',search)]:
        (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'syntax.css').write_text(HtmlFormatter(style='monokai').get_style_defs('.codehilite'),encoding='utf-8')
    for asset in (ROOT/'assets').iterdir():
        if asset.is_file():
            shutil.copyfile(asset,OUT/asset.name)
    (OUT/'.nojekyll').touch()
    nav = '# 全书导航\n\n《LangChain 帝国》 · 五章正文 · 第六章待续\n\n'+'\n'.join(f'- [第{c["number"]}章：{c["title"]}]({c["number"]:02}.md)' for c in CHAPTERS)+'\n'
    (ROOT/'chapters/00-全书导航.md').write_text(nav,encoding='utf-8')
    print(f'Built {len(CHAPTERS)+3} pages and {len(search)} searchable sections.')


if __name__ == '__main__':
    main()
