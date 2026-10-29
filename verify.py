"""Verify the published static artifact and browser behavior without a server."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit
import ast
import hashlib
import json
import mimetypes
import re

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
DOCS = ROOT/'docs'
OUT = ROOT/'test-results'
BASE = 'https://reader.test/langchain-empire-reader/'
PREFIX = 'langchain-empire-'


class PageLinks(HTMLParser):
    def __init__(self,path):
        super().__init__()
        self.links = []
        self.ids = set()
        self.duplicates = []
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self,tag,attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            if attrs['id'] in self.ids:
                self.duplicates.append(attrs['id'])
            self.ids.add(attrs['id'])
        if tag in ('a','link','script','img'):
            value = attrs.get('href') or attrs.get('src')
            if value:
                self.links.append(value)


def main():
    OUT.mkdir(exist_ok=True)
    book = json.loads((ROOT/'book.json').read_text(encoding='utf-8'))
    assert len(book['chapters']) == len(list(DOCS.glob('chapter-*.html'))) == 5
    audit = json.loads((ROOT/'CONTENT_REVIEW.json').read_text(encoding='utf-8'))
    assert audit['sha256'] == hashlib.sha256((ROOT/'source/langchain.original.md').read_bytes()).hexdigest()
    assert sum(len(c['blocks']) for c in audit['chapters']) == 130
    for chapter in (ROOT/'chapters').glob('[0-9][0-9].md'):
        source = chapter.read_text(encoding='utf-8')
        assert 'CODEBLOCKPLACEHOLDER' not in source
        assert '查看参考答案下一题' not in source
        for code in re.findall(r'```python\n(.*?)```',source,re.S):
            ast.parse(code)
    pages = sorted(DOCS.glob('*.html'))
    assert len(pages) == 8
    parsers = {p:PageLinks(p) for p in pages}
    for path,parser in parsers.items():
        assert not parser.duplicates,(path.name,parser.duplicates)
        source = path.read_text(encoding='utf-8')
        for residue in ('MATHTOKEN','katex-error','GitHub+','查看参考答案下一题'):
            assert residue not in source,(path.name,residue)
        for link in parser.links:
            target = urlsplit(urljoin(BASE+path.name,link))
            if target.netloc != 'reader.test' or not target.path.startswith('/langchain-empire-reader/'):
                continue
            file = DOCS/(unquote(target.path.removeprefix('/langchain-empire-reader/')) or 'index.html')
            assert file.is_file(),(path.name,link)
            if target.fragment and file.suffix == '.html':
                assert unquote(target.fragment) in parsers[file].ids,(path.name,link)
    search = json.loads((DOCS/'search.json').read_text(encoding='utf-8'))
    assert {r['chapter'] for r in search} == {1,2,3,4,5}
    for item in search:
        target = urlsplit(item['url'])
        if target.fragment:
            assert target.fragment in parsers[DOCS/target.path].ids,item['url']

    errors = []
    missing = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        def serve(route):
            target = urlsplit(route.request.url)
            if target.netloc != 'reader.test':
                route.abort()
                return
            if not target.path.startswith('/langchain-empire-reader/'):
                route.fulfill(body='Cross-project links verified by bookshelf/verify.py')
                return
            path = DOCS/(unquote(target.path.removeprefix('/langchain-empire-reader/')) or 'index.html')
            if not path.is_file():
                missing.append(target.path)
                route.fulfill(status=404,body='Missing file')
            else:
                route.fulfill(path=str(path),content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
        context = browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'],reduced_motion='reduce')
        context.route('**/*',serve)
        page = context.new_page()
        page.on('pageerror',lambda error:errors.append(str(error)))
        for width in (390,768,1440):
            page.set_viewport_size({'width':width,'height':1000})
            for path in pages:
                response = page.goto(BASE+path.name)
                assert response.status == 200
                expect(page.locator('h1')).to_have_count(1)
                expect(page.locator('.shelf-menu a')).to_have_count(9)
                assert page.locator('.shelf-home').get_attribute('href') == '/'
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),(path.name,width)
                page.locator('.shelf-switch summary').click()
                box = page.locator('.shelf-menu').bounding_box()
                assert box and box['x'] >= 0 and box['x']+box['width'] <= width,(path.name,width,box)
                page.locator('.shelf-switch summary').click()
                if path.name == 'index.html':
                    expect(page.locator('.card')).to_have_count(5)
                    expect(page.locator('#next-chapter')).to_contain_text('第六章待续')
                    page.screenshot(path=str(OUT/f'home-{width}.png'),full_page=True)
                if path.name == 'chapter-04.html':
                    assert page.locator('math').count() >= 5
                    page.screenshot(path=str(OUT/f'chapter-{width}.png'))
            if width == 390:
                page.goto(BASE+'chapter-03.html')
                page.locator('.mobile-toc summary').click()
                link = page.locator('.mobile-toc .toc a').nth(3)
                href = link.get_attribute('href')
                link.click()
                assert unquote(urlsplit(page.url).fragment) == unquote(href[1:])
        page.set_viewport_size({'width':1440,'height':1000})
        page.goto(BASE+'index.html')
        themes = set()
        for _ in range(3):
            page.locator('#theme').click()
            theme = page.locator('html').get_attribute('data-theme')
            themes.add(theme)
            page.reload()
            expect(page.locator('html')).to_have_attribute('data-theme',theme)
        assert themes == {'white','light','dark'}
        page.goto(BASE+'chapter-01.html')
        page.locator('#larger').click()
        size = page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--reading-size")')
        page.reload()
        assert page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--reading-size")') == size
        for _ in range(12):
            if page.locator('#larger').is_disabled():break
            page.locator('#larger').click()
        expect(page.locator('#larger')).to_be_disabled()
        assert page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--reading-size")') == '26px'
        for _ in range(12):
            if page.locator('#smaller').is_disabled():break
            page.locator('#smaller').click()
        expect(page.locator('#smaller')).to_be_disabled()
        page.locator('.copy-code').first.click()
        expect(page.locator('#toast')).to_have_text('代码已复制')
        expected = page.locator('.code-block pre').first.text_content()
        actual = page.evaluate('navigator.clipboard.readText()')
        assert actual.replace('\r\n','\n') == expected.replace('\r\n','\n'),(repr(actual[:100]),repr(expected[:100]))
        page.keyboard.press('/')
        expect(page.locator('#query')).to_be_focused()
        for term in ('工具调用','InMemorySaver','recursion_limit'):
            page.locator('#query').fill(term)
            expect(page.locator('.search-result').first).to_be_visible()
            expect(page.locator('#search-status')).to_contain_text('找到')
        page.locator('#query').fill('zzzz-unique-no-result')
        expect(page.locator('#search-status')).to_contain_text('未找到')
        page.locator('#query').fill('<img src=x onerror=alert(1)>')
        expect(page.locator('#search-status')).to_contain_text('未找到')
        assert page.locator('#search-results img').count() == 0
        page.locator('#query').fill('InMemorySaver')
        expect(page.locator('.search-result').first).to_be_visible()
        target = page.locator('.search-result').first.get_attribute('href')
        page.locator('.search-result').first.click()
        assert unquote(page.url).endswith(unquote(target))
        expect(page.locator('#search-dialog')).not_to_be_visible()
        page.goto(BASE+'chapter-02.html')
        page.evaluate('scrollTo(0,(document.documentElement.scrollHeight-innerHeight)*.37)')
        page.wait_for_function('JSON.parse(localStorage.getItem("langchain-empire-reading"))?.progress?.[2]?.fraction > .36')
        page.goto(BASE+'index.html')
        expect(page.locator('#resume')).to_contain_text('第 2 章')
        page.locator('#resume').click()
        page.wait_for_function('scrollY/(document.documentElement.scrollHeight-innerHeight)>.35')
        assert abs(page.evaluate('scrollY/(document.documentElement.scrollHeight-innerHeight)')-.37) < .02
        page.goto(BASE+'reading.html')
        expect(page.locator('#reading-progress')).to_contain_text('第 2 章')
        page.locator('.clear-records summary').click()
        page.locator('#clear-records').click()
        page.locator('#clear-no').click()
        assert page.locator('#clear-confirm').is_hidden()
        page.locator('#clear-records').click()
        page.locator('#clear-yes').click()
        expect(page.locator('#reading-progress')).to_contain_text('还没有阅读记录')
        page.goto(BASE+'index.html')
        expect(page.locator('#resume')).to_be_hidden()
        # Recover from a failed index fetch on the next query.
        page.route('**/search.json',lambda route:route.fulfill(status=503,body='Unavailable'),times=1)
        page.locator('#search-open').click()
        page.locator('#query').fill('RAG')
        expect(page.locator('#search-status')).to_contain_text('加载失败')
        page.locator('#query').fill('Memory')
        expect(page.locator('.search-result').first).to_be_visible()
        page.keyboard.press('Escape')
        expect(page.locator('#search-dialog')).not_to_be_visible()
        context.close()
        nojs = browser.new_context(java_script_enabled=False,viewport={'width':390,'height':900})
        nojs.route('**/*',serve)
        plain = nojs.new_page()
        plain.goto(BASE+'chapter-05.html')
        expect(plain.locator('article')).to_contain_text('StateGraph')
        expect(plain.locator('.chapter-nav a').last).to_contain_text('第六章待续')
        nojs.close()
        blocked = browser.new_context(viewport={'width':390,'height':900})
        blocked.route('**/*',serve)
        blocked.add_init_script('Storage.prototype.setItem=function(){throw new Error("Storage blocked")}')
        p = blocked.new_page()
        p.on('pageerror',lambda error:errors.append(str(error)))
        p.goto(BASE+'chapter-01.html')
        expect(p.locator('#toast')).to_contain_text('无法保存')
        p.locator('#theme').click()
        expect(p.locator('html')).to_have_attribute('data-theme','light')
        blocked.close()
        browser.close()
    assert not errors,errors
    assert not missing,missing
    print('PASS: 8 pages, 5 chapters, 130 code blocks, links/anchors/resources, 3 viewports, search/retry, clipboard, themes/font limits, progress/resume/clear, no-JS and blocked storage.')


if __name__ == '__main__':
    main()
