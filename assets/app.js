(() => {
  'use strict';
  const root = document.documentElement;
  const prefix = 'langchain-empire-';
  const chapter = Number(document.body.dataset.chapter) || 0;
  const total = 5;
  const $ = selector => document.querySelector(selector);
  const clamp = value => Math.max(0, Math.min(1, Number(value) || 0));
  const chapterURL = n => `chapter-${String(n).padStart(2, '0')}.html`;
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  let toastTimer;
  function toast(message) {
    $('#toast').textContent = message;
    $('#toast').classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 3000);
  }
  let state;
  try { state = JSON.parse(localStorage.getItem(prefix + 'reading')); } catch {}
  if (!state || state.version !== 1 || typeof state.progress !== 'object' || !state.progress) {
    state = {version: 1, last: 0, progress: {}};
  }
  for (const [key, progress] of Object.entries(state.progress)) {
    if (!Number.isInteger(Number(key)) || Number(key) < 1 || Number(key) > total || !progress || typeof progress !== 'object') delete state.progress[key];
    else { progress.fraction = clamp(progress.fraction); progress.maxPercent = Math.round(clamp(progress.maxPercent / 100) * 100); }
  }
  let storageFailed = false;
  function persist() {
    try { localStorage.setItem(prefix + 'reading', JSON.stringify(state)); }
    catch { if (!storageFailed) {storageFailed = true; toast('浏览器未允许本地存储，本次阅读进度无法保存。');} }
  }
  const themeNames = {white:'纯白', light:'米白', dark:'深色'};
  const themes = Object.keys(themeNames);
  function setTheme(theme) {
    theme = themes.includes(theme) ? theme : 'white';
    root.dataset.theme = theme;
    $('#theme').textContent = themeNames[theme];
    $('#theme').setAttribute('aria-label', '切换背景，当前' + themeNames[theme]);
    try { localStorage.setItem(prefix + 'theme', theme); } catch {}
  }
  setTheme(root.dataset.theme);
  $('#theme').addEventListener('click', () => setTheme(themes[(themes.indexOf(root.dataset.theme) + 1) % themes.length]));
  let size = 18;
  try { size = Math.max(16, Math.min(26, Number(localStorage.getItem(prefix + 'size')) || 18)); } catch {}
  function resize(delta) {
    size = Math.max(16, Math.min(26, size + delta));
    root.style.setProperty('--reading-size', size + 'px');
    $('#smaller').disabled = size <= 16;
    $('#larger').disabled = size >= 26;
    try { localStorage.setItem(prefix + 'size', String(size)); } catch {}
  }
  $('#smaller').addEventListener('click', () => resize(-1));
  $('#larger').addEventListener('click', () => resize(1));
  resize(0);

  const dialog = $('#search-dialog'), query = $('#query'), results = $('#search-results'), status = $('#search-status');
  let indexPromise = null, searchTimer, searchVersion = 0;
  const loadIndex = () => indexPromise || (indexPromise = fetch('search.json').then(response => {
    if (!response.ok) throw Error('Index unavailable');
    return response.json();
  }).catch(error => {indexPromise = null; throw error;}));
  function highlight(parent, text, word) {
    const at = text.toLocaleLowerCase().indexOf(word);
    if (at < 0) {parent.textContent = text; return;}
    parent.append(document.createTextNode(text.slice(0, at)), element('mark', text.slice(at, at + word.length)), document.createTextNode(text.slice(at + word.length)));
  }
  async function search() {
    const version = ++searchVersion;
    results.replaceChildren();
    const words = query.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    if (!words.length) {status.textContent = '输入关键词开始搜索'; return;}
    status.textContent = '正在搜索…';
    try {
      const data = await loadIndex();
      if (version !== searchVersion) return;
      const found = data.filter(item => words.every(word => (item.title + ' ' + item.section + ' ' + item.text).toLocaleLowerCase().includes(word)));
      status.textContent = found.length ? `找到 ${found.length} 个段落${found.length > 40 ? '，显示前 40 个' : ''}` : '未找到匹配内容，试试更短的关键词。';
      for (const item of found.slice(0, 40)) {
        const link = element('a', undefined, 'search-result');
        link.href = item.url;
        const title = element('strong'), snippet = element('p');
        highlight(title, `第${item.chapter}章 · ${item.section}`, words[0]);
        const at = Math.max(0, item.text.toLocaleLowerCase().indexOf(words[0]) - 55);
        highlight(snippet, (at ? '…' : '') + item.text.slice(at, at + 180) + '…', words[0]);
        link.append(title, snippet);
        results.append(link);
      }
    } catch {if (version === searchVersion) status.textContent = '搜索索引加载失败，请检查连接后重新输入。';}
  }
  function openSearch() { if (!dialog.open) dialog.showModal(); query.focus(); }
  $('#search-open').addEventListener('click', openSearch);
  $('#search-close').addEventListener('click', () => dialog.close());
  query.addEventListener('input', () => { ++searchVersion; clearTimeout(searchTimer); searchTimer = setTimeout(search, 120); });
  results.addEventListener('click', event => {if (event.target.closest('a')) dialog.close();});
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && dialog.open) {event.preventDefault(); dialog.close(); return;}
    if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(event.target.tagName) && !event.target.isContentEditable && !event.ctrlKey && !event.metaKey) {event.preventDefault(); openSearch();}
  });
  document.querySelectorAll('.copy-code').forEach(button => button.addEventListener('click', async () => {
    const text = button.closest('.code-block').querySelector('pre').textContent;
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const area = element('textarea', text);
        area.style.cssText = 'position:fixed;opacity:0';
        document.body.append(area);
        area.select();
        const copied = document.execCommand('copy');
        area.remove();
        if (!copied) throw Error('Clipboard denied');
      }
      toast('代码已复制');
    } catch {toast('复制未获浏览器允许，请选择代码后复制。');}
  }));

  const resume = $('#resume');
  if (resume && Number.isInteger(state.last) && state.last >= 1 && state.last <= total && state.progress[state.last]) {
    resume.href = chapterURL(state.last) + '?resume=1';
    resume.textContent = `继续第 ${state.last} 章 · 已读 ${state.progress[state.last].maxPercent}% →`;
    resume.hidden = false;
  }
  document.querySelectorAll('[data-chapter-progress]').forEach(node => {
    const progress = state.progress[node.dataset.chapterProgress];
    if (progress) node.textContent = ` · 已读 ${progress.maxPercent}%`;
  });
  if (chapter) {
    let ready = false, timer;
    const fraction = () => clamp(scrollY / Math.max(1, root.scrollHeight - innerHeight));
    function save() {
      if (!ready) return;
      const value = fraction(), previous = state.progress[chapter];
      state.last = chapter;
      state.progress[chapter] = {fraction: value, maxPercent: Math.max(previous?.maxPercent || 0, Math.round(value * 100)), updatedAt: Date.now()};
      persist();
    }
    function update() {
      if (!ready) return;
      const percent = Math.round(fraction() * 100);
      $('#progress').style.width = percent + '%';
      $('#read-status').textContent = `当前位置 ${percent}%`;
      clearTimeout(timer);
      timer = setTimeout(save, 150);
    }
    requestAnimationFrame(() => requestAnimationFrame(() => {
      if (!location.hash && new URLSearchParams(location.search).has('resume')) {
        const saved = state.progress[chapter];
        if (saved) scrollTo(0, saved.fraction * Math.max(0, root.scrollHeight - innerHeight));
      }
      ready = true;
      save(); update();
    }));
    window.addEventListener('scroll', update, {passive:true});
    window.addEventListener('resize', update);
    window.addEventListener('pagehide', save);
    document.addEventListener('visibilitychange', () => {if (document.visibilityState === 'hidden') save();});
  }
  if ($('#reading-progress')) {
    function showReading() {
      const parent = $('#reading-progress');
      parent.replaceChildren();
      for (const [n, progress] of Object.entries(state.progress).sort((a,b) => Number(a[0]) - Number(b[0]))) {
        const row = element('div', undefined, 'reading-item');
        const link = element('a', `第 ${n} 章 · ${progress.maxPercent >= 98 ? '已读完' : '已读 ' + progress.maxPercent + '%'}`);
        link.href = chapterURL(Number(n)) + '?resume=1';
        row.append(link, element('small', '继续上次位置 →'));
        parent.append(row);
      }
      if (!parent.children.length) parent.append(element('p', '还没有阅读记录，从第一章开始吧。'));
    }
    $('#clear-records').addEventListener('click', () => {$('#clear-confirm').hidden = false;});
    $('#clear-no').addEventListener('click', () => {$('#clear-confirm').hidden = true;});
    $('#clear-yes').addEventListener('click', () => {
      state = {version:1,last:0,progress:{}}; persist(); showReading();
      $('#clear-confirm').hidden = true; toast('本书阅读进度已清除');
    });
    showReading();
  }
})();
