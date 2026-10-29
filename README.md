# LangChain 帝国

五章小说式 AI 应用工程阅读，沿用 AI 纪元的阅读样式，支持手机与桌面。第一卷连载，第六章仅有预告。

- [在线阅读](https://wupzl.github.io/langchain-empire-reader/)
- [学习书架](https://wupzl.github.io/)
- [全书 Markdown 导航](chapters/00-全书导航.md)
- [技术修订与官方来源](EDITORIAL.md)

## 阅读功能

章内目录、上下章切换、全书搜索、代码高亮与复制、字号调整、纯白/米白/深色主题、阅读进度记忆及继续阅读。无需登录和后端；记录保存在当前浏览器。

## 构建与预览

需要 Python 3.10+ 与 Node.js。公式在构建时用仓库内的 KaTeX 生成 MathML，无需浏览器加载外部 CDN。

```bash
python -m pip install -r requirements.txt
python build.py
python -m http.server 4176 --directory docs --bind 127.0.0.1
```

访问 `http://127.0.0.1:4176/`。跨项目根路径由学习书架的验收脚本映射。

## 内容维护

修改 `chapters/01.md` 至 `05.md`，章节信息同步更新 `book.json`，运行 `python build.py` 并提交源文件与 `docs/`。第六章只有预告，不计入正文数量。

`source/langchain.original.md` 保留原文，`CONTENT_REVIEW.json` 记录 SHA-256 与代码块分类。`scripts/prepare_content.py` 是一次性导入工具，会覆盖维护后的章节，常规构建不调用它。

## 验证

```bash
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python verify.py
```

检查全部页面的本地链接、锚点、资源和 390/768/1440px 布局，以及搜索、代码复制、主题/字号持久化、继续阅读、清除记录与无 JavaScript 正文。截图保存在忽略的 `test-results/`。

离线 Python 示例：在独立环境安装 `requirements-examples.txt`，运行 `python scripts/verify_examples.py`。不调用外部模型或 Embedding 服务。Java 片段按官方文档审阅，业务服务和数据库实现骨架没有作为完整应用编译运行。

## 发布与书架

公开仓库 `wupzl/langchain-empire-reader`，GitHub Pages 从 `main` 分支的 `/docs` 发布。所有页面含学习书架入口和九项目切换菜单。`scripts/integrate_bookshelf.py` 更新同级八个阅读站的已生成页面、源生成器，以及书架首页与验收配置；脚本本身不提交或推送。

第三方 KaTeX 许可证见 `vendor/KaTeX-LICENSE.txt`。
