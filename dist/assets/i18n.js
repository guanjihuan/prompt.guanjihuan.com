/* 界面英文文案。键与中文源文案一致，缺键时回退中文，便于发现漏译。 */
window.PLIB_I18N = {
  '跳到主要内容': 'Skip to main content',
  'GUAN 提示词库': 'GUAN Prompt Library',
  '搜索全部提示词、标签或分类…': 'Search all prompts, tags, or categories…',
  '搜索全部提示词，多个关键词用空格分隔': 'Search all prompts; separate multiple keywords with spaces',
  '清空搜索': 'Clear search',
  '查看我的收藏': 'View my favorites',
  '返回全部提示词': 'Back to all prompts',
  '切换明暗主题': 'Toggle light or dark theme',
  '开发者：': 'Developer: ',
  '关济寰': 'Ji-Huan Guan',
  '键盘快捷键': 'Keyboard shortcuts',
  '打开分类导航': 'Open category navigation',
  '提示词工作台': 'PROMPT WORKSPACE',
  '需求即提示词': 'Your requirement is the prompt',
  '下一次对话，从一条好提示词开始': 'Start your next conversation with a better prompt',
  '把需求说清楚，提示词就写好了。从工程实现到学术写作，把反复验证过的提示词按场景归类整理。无需登录，复制即用。': 'State the requirement clearly and the prompt is ready. Explore field-tested prompts for everything from software engineering to academic writing, organized by scenario. No sign-in; just copy and use.',
  '内容统计': 'Library statistics',
  '条提示词': 'Prompts',
  '个分类': 'Categories',
  '个场景': 'Sections',
  '随时搜索': 'Search anytime',
  '收藏仅保存在本机': 'Favorites stay on this device',
  '分类导航': 'Category navigation',
  '浏览分类': 'Browse categories',
  '关闭分类导航': 'Close category navigation',
  '你的数据，留在本机': 'Your data stays on this device',
  '收藏、使用次数与自定义内容仅保存在当前浏览器。': 'Favorites, usage counts, and custom content are stored only in this browser.',
  '全部提示词': 'All prompts',
  '浏览所有分类': 'Browse every category',
  '我的收藏': 'My favorites',
  '仅显示已收藏的提示词': 'Show favorite prompts only',
  '自定义': 'Custom',
  '仅显示你自己创建的提示词': 'Show only prompts you created',
  '自定义提示词': 'Custom prompts',
  '我的自定义': 'My custom prompts',
  '我的分类': 'My categories',
  '自己创建的提示词分类': 'A category for prompts you created',
  '正在整理…': 'Loading…',
  '排序方式': 'Sort order',
  '按复制次数排列': 'Sort by copy count',
  '复制设置': 'Copy settings',
  '导入 / 导出': 'Import / Export',
  '导入与导出': 'Import and export',
  '新建': 'New',
  '当前筛选条件': 'Active filters',
  '复制时自动处理': 'Automatic copy options',
  '复制提示词时自动套用，保存在本机。': 'Applied when copying prompts and saved on this device.',
  '恢复默认': 'Reset defaults',
  '任务命令': 'Task command',
  '把 Claude Code 命令加在提示词前面': 'Prepend a Claude Code command to the prompt',
  '不加命令': 'No command',
  '/loop · 循环执行': '/loop · Run in a loop',
  '按默认节奏循环执行任务，直到完成或达到停止条件。': 'Run the task repeatedly at the default pace until it is complete or a stopping condition is met.',
  '/plan · 计划模式': '/plan · Plan mode',
  '进入计划模式并围绕所述任务制定实施方案。': 'Enter plan mode and develop an implementation plan for the task.',
  '/run · 运行验证': '/run · Run and verify',
  '启动并操作项目应用，验证提示词中描述的功能或改动。': 'Launch and use the project app to verify the feature or change described in the prompt.',
  '/deep-research · 深度研究': '/deep-research · Deep research',
  '围绕研究问题检索并交叉核验资料，生成带引用的报告。': 'Research the question, cross-check sources, and produce a cited report.',
  '自定义…': 'Custom…',
  '自定义命令，如 /mycmd': 'Custom command, e.g. /mycmd',
  '自定义任务命令': 'Custom task command',
  '附加指令块': 'Additional instruction block',
  '把一段工作指令追加到提示词后面': 'Append a block of working instructions to the prompt',
  '不附加': 'None',
  '自定义指令，与上方指令块可同时使用': 'Custom instructions; can be combined with the block above',
  '自定义指令块内容': 'Custom instruction block content',
  '这里只列出常用命令，是否可用取决于你的 Claude Code 版本与账号；选「自定义…」可填任意命令。': 'Only common commands are listed. Availability depends on your Claude Code version and account. Choose “Custom…” to enter any command.',
  '追加内容预览': 'Appended content preview',
  '当前为原始复制，不加命令或指令块。': 'Original prompt only; no command or instruction block is added.',
  '「我的收藏」与「自定义」可导出为 Markdown 或 JSON 文件，也能从文件导入回本机。': 'Export favorites and custom prompts as Markdown or JSON, or import them back onto this device.',
  '收起': 'Collapse',
  '收藏 · Markdown': 'Favorites · Markdown',
  '收藏 · JSON': 'Favorites · JSON',
  '自定义 · Markdown': 'Custom · Markdown',
  '自定义 · JSON': 'Custom · JSON',
  '从文件导入': 'Import from file',
  '收藏导出文件用「导入收藏」，自定义导出文件用「导入自定义」，选错会提示且不会导入；支持 JSON 与 Markdown': 'Use “Import favorites” for favorite exports and “Import custom” for custom exports. The wrong file type is rejected with a message. JSON and Markdown are supported.',
  '导入收藏': 'Import favorites',
  '导入自定义': 'Import custom prompts',
  '选择要导入的收藏文件（JSON 或 Markdown）': 'Select the favorites file to import (JSON or Markdown)',
  '选择要导入的自定义文件（JSON 或 Markdown）': 'Select the custom-prompt file to import (JSON or Markdown)',
  '导出的是原始正文，不含复制设置里的任务命令与指令块。': 'Exports contain the original prompt text without task commands or instruction blocks from copy settings.',
  '再显示 24 条': 'Show 24 more',
  '没有找到相关提示词': 'No matching prompts found',
  '换个关键词，或清空分类与搜索条件后再试试。': 'Try another keyword, or clear the category and search filters.',
  '清空搜索与筛选': 'Clear search and filters',
  '本站的提示词整理自个人工作习惯，已做脱敏与通用化处理，复制即可直接粘贴使用。': 'The prompts on this site come from personal working practices, with private details removed and wording generalized. Copy and paste them directly.',
  '主站：': 'Main site: ',
  '关于': 'About',
  '内容采用 CC BY 4.0 许可': 'Content licensed under CC BY 4.0',
  '回到顶部': 'Back to top',
  '本页需要 JavaScript 才能进行搜索与复制。提示词原文维护在仓库的': 'This page needs JavaScript for search and copying. The source prompts are maintained in the repository’s',
  '目录中。': 'directory.',
  '新建提示词': 'New prompt',
  '编辑提示词': 'Edit prompt',
  '保存到当前浏览器，随时编辑或导出。': 'Saved in this browser, ready to edit or export anytime.',
  '关闭': 'Close',
  '标题': 'Title',
  '必填': 'Required',
  '例如：生成项目周报': 'e.g., Generate a project weekly report',
  '简洁表达': 'Short version',
  '可选，仅在确有更短说法时填写': 'Optional; use only when a genuinely shorter version exists',
  '正文已经足够简洁时请留空…': 'Leave blank if the prompt is already concise…',
  '提示词正文': 'Prompt text',
  '完整的提示词正文…': 'Full prompt text…',
  '使用备注': 'Usage note',
  '可选，仅自己可见': 'Optional; visible only to you',
  '例如：使用前替换项目名与时间范围': 'e.g., Replace the project name and date range before use',
  '所属分类': 'Category',
  '可选，留空放进「我的自定义」': 'Optional; leave blank to keep it in “My custom prompts”',
  '管理已保存条目': 'Manage saved prompts',
  '导出': 'Export',
  '导入': 'Import',
  '选择要导入的 JSON 或 Markdown 文件': 'Choose a JSON or Markdown file to import',
  '取消': 'Cancel',
  '保存提示词': 'Save prompt',
  '保存修改': 'Save changes',
  '聚焦搜索框': 'Focus search',
  '关闭弹层 / 收起面板 / 清空搜索': 'Close dialogs / collapse panels / clear search',
  '打开关于面板': 'Open this panel',
  '在卡片行与行之间上下移动': 'Move between rows of cards',
  '在同一行卡片之间左右移动': 'Move between cards in the same row',
  '复制当前提示词（优先简洁版）': 'Copy current prompt (short version when available)',
  '收藏 / 取消收藏当前提示词': 'Favorite / unfavorite current prompt',

  '搜索结果': 'Search results',
  '在全部提示词里没搜到相关内容，换个关键词试试。': 'No matches in the full library. Try another keyword.',
  '还没有收藏任何提示词': 'No favorite prompts yet',
  '在卡片右上角点星标即可收藏；收藏只保存在当前浏览器。': 'Click the star in the upper-right corner of a card to favorite it. Favorites are stored only in this browser.',
  '去看全部提示词': 'Browse all prompts',
  '还没有自定义提示词': 'No custom prompts yet',
  '点右上角「新建」写下一条自己的提示词，保存后只留在当前浏览器。': 'Click “New” in the upper-right corner to write your own prompt. It is saved only in this browser.',
  '这个分类暂时是空的': 'This category is empty',
  '换个分类看看，或者新建一条属于自己的提示词。': 'Try another category or create your own prompt.',
  '查看全部提示词': 'View all prompts',
  '关键词': 'Keyword',
  '范围': 'Scope',
  '分类': 'Category',
  '当前筛选': 'Filters',
  '移除此条件': 'Remove this filter',
  '移除': 'Remove',
  '这一类覆盖': 'This category covers',
  '全部分类目录': 'All categories',
  '全部提示词按复制次数从多到少排列': 'All prompts sorted by copy count, highest first',
  '下面是随机顺序的提示词': 'Prompts below are in random order',
  '换一批': 'Shuffle',
  '复制': 'Copy',
  '已复制': 'Copied',
  '详细表达': 'Full version',
  '复制简洁表达': 'Copy short version',
  '复制详细表达': 'Copy full version',
  '复制提示词': 'Copy prompt',
  '复制这条提示词的链接': 'Copy a link to this prompt',
  '复制链接': 'Copy link',
  '收藏': 'Favorite',
  '取消收藏': 'Unfavorite',
  '备注：': 'Note: ',
  '编辑': 'Edit',
  '删除': 'Delete',
  '复制失败，请手动选中文本复制': 'Copy failed. Select the text and copy it manually.',
  '链接已复制，可直达这条提示词': 'Link copied. It opens directly to this prompt.',
  '链接复制失败': 'Could not copy the link',
  '已加入收藏': 'Added to favorites',
  '已取消收藏': 'Removed from favorites',
  '请填写标题和提示词正文': 'Enter a title and prompt text',
  '已删除': 'Deleted',
  '删除这条自定义提示词？此操作无法撤销。': 'Delete this custom prompt? This cannot be undone.',
  '还没有自定义提示词，保存后会显示在这里。': 'No custom prompts yet. Saved prompts will appear here.',
  '已恢复默认复制方式': 'Copy settings reset to defaults',
  '没有找到这条提示词，链接可能已失效': 'Prompt not found. The link may be out of date.',
  '文件超过 5 MB，请选择较小的文件': 'The file is larger than 5 MB. Choose a smaller file.',
  '读取文件失败，请重试': 'Could not read the file. Try again.',
  '导入失败：文件格式不正确': 'Import failed: invalid file format',
  '这是收藏导出文件，请用「导入收藏」按钮': 'This is a favorites export file. Use the “Import favorites” button.',
  '这是自定义导出文件，请用「导入自定义」按钮': 'This is a custom-prompt export file. Use the “Import custom prompts” button.',
  '这像是收藏导出文件，请用「导入收藏」按钮': 'This looks like a favorites export file. Use the “Import favorites” button.',
  '这些条目已经导入过，没有新增': 'These prompts were already imported; nothing new was added',
  '文件中没有可导入的有效条目': 'The file contains no valid prompts to import',
  '文件中没有可识别的提示词条目': 'The file contains no recognizable prompts',
  '已保存到「自定义」': 'Saved to “Custom”',
  '已保存到「{category}」': 'Saved to “{category}”',
  '已保存到「': 'Saved to “',
  '已复制简洁表达': 'Short version copied',
  '已复制详细表达': 'Full version copied',
  '已复制提示词': 'Prompt copied',
  '深色': 'dark',
  '浅色': 'light',
  '切换到': 'Switch to ',
  '主题': ' theme',

  'GUAN 提示词库 · 按场景分类的常用提示词': 'GUAN Prompt Library · Practical prompts organized by scenario',
  '个人整理的提示词库：从工程实现到学术写作，反复验证过的提示词按场景分类，支持多关键词搜索、一键复制、收藏与自定义，无需登录。': 'A curated prompt library covering software engineering through academic writing. Search field-tested prompts by scenario with multiple keywords, copy in one click, favorite, and customize. No sign-in required.',
  '从工程实现到学术写作，反复验证过的提示词按场景分类，搜索即取、复制即用，无需登录。': 'Field-tested prompts from software engineering to academic writing, organized by scenario. Search, copy, and use without signing in.',
  'GUAN 提示词库 · 常用智能体提示词分类检索': 'GUAN Prompt Library · Browse agent prompts by category',
  '页面不存在 · GUAN 提示词库': 'Page not found · GUAN Prompt Library',
  '这个地址没有对应的页面。回到提示词库继续搜索与复制。': 'There is no page at this address. Return to the prompt library to search and copy.',
  '这个地址没有对应的页面': 'There is no page at this address',
  '提示词库只有一个首页，搜索、分类与复制都在那里完成。回到首页，换个关键词就能继续找。': 'The prompt library has a single home page for search, categories, and copying. Return home and try another keyword.',
  '回到提示词库': 'Back to the prompt library',
  '在首页按': 'On the home page, press',
  '直接搜索；分享链接形如': 'to search. Share links look like',
  '，带 id 的地址能直接定位到那一条提示词。': '; a URL with an id opens that prompt directly.',
  '切换到中文': 'Switch to Chinese',
  'Switch to English': 'Switch to English',
  'Switch to Chinese': 'Switch to Chinese',
  '#条目 id': '#prompt id',

  /* 分区名：侧栏把分类按这几个分区归并（与 src/i18n/sections.json 保持一致） */
  '通用任务': 'General Tasks',
  '软件工程': 'Software Engineering',
  '界面与产品': 'Interface and Product',
  '文档与表达': 'Documents and Expression',
  '学术研究': 'Academic Research',
  '办公事务': 'Office Work',
  '智能体与指令': 'Agents and Instructions',

  /* 带数量的动态文案：{n} 由运行时填入 */
  '再显示 {n} 条': 'Show {n} more',
  '还有 {n} 条未显示': '{n} more not shown',
  ' · 已显示 {n}': ' · {n} shown',
  '找到 ': 'Found ',
  '共 ': 'Total ',
  ' 条': ' items',
  '找到 {n} 条': 'Found {n}',
  '共 {n} 条': 'Total {n}',
  '已导入 {n} 条提示词': 'Imported {n} prompts',
  '已导出 {n} 条自定义提示词': 'Exported {n} custom prompts',
  '已恢复 {restored} 条收藏，新增 {added} 条自定义': 'Restored {restored} favorites and added {added} custom prompts',
  '已恢复 ': 'Restored ',
  '导入失败：': 'Import failed: ',
  '导入失败：{name} 里没有可识别的提示词条目': 'Import failed: no recognizable prompts found in {name}',
  '导入失败：{name} 不是收藏导出文件': 'Import failed: {name} is not a favorites export file',
  '导入失败：{name} 不是自定义导出文件': 'Import failed: {name} is not a custom-prompt export file',
  '，跳过 {n} 条已存在的': ', skipping {n} existing prompts',
  /* 这两条跟在「关闭后恢复」后面拼成一句，英文要留一个空格，中文原文自带语义不留 */
  '原有顺序': ' the original order',
  '随机顺序': ' a random order',
  '已复制 {n} 次': 'Copied {n} times',
  '已导出 {n} 条收藏': 'Exported {n} favorites',
  '按复制次数排列：关闭后恢复': 'Sort by copy count: switch it off to restore',
  '按复制次数排列：把当前列表按复制次数从多到少排列': 'Sort by copy count: sort the current list by copy count, highest first',
  '按复制次数排列：搜索时按相关度排序，此开关在无搜索词时生效': 'Sort by copy count: search results stay ranked by relevance; this switch applies when no search term is present',
  '（当前已开启）': ' (currently on)',
  '搜索标签：': 'Search tags: ',

  /* 复制设置预览与导出说明 */
  '、': ', ',
  '复制时将添加：{items}。': 'The copy will include: {items}.',
  '将使用自定义任务命令：': 'Custom task command in use: ',
  '指令块「{title}」': 'Instruction block “{title}”',
  '自定义指令': 'Custom instructions',
  '我的收藏 {fav} 条、自定义 {custom} 条；导出的是原始正文，不含复制设置里的任务命令与指令块。': 'You have {fav} favorites and {custom} custom prompts; exports contain the original prompt text without the task commands or instruction blocks from copy settings.',

  /* 导出文件里的元信息字段 */
  'GUAN 提示词库导出': 'GUAN Prompt Library Export',
  '条目数': 'Item count',
  '导出时间': 'Exported at',
  '来源': 'Source',
  '标签': 'Tags',
  '备注': 'Note'
};

/* 静态文案的应用层：页面里标了 data-i18n 的元素按本机语言取值，缺键回退中文。
   只处理 HTML 里写死的文案；卡片等运行时生成的内容由 app.js 负责重绘。 */
(function () {
  var table = window.PLIB_I18N;
  var LANG_KEY = 'plib.lang.v1';

  function storedLang() {
    try {
      return JSON.parse(localStorage.getItem(LANG_KEY)) === 'en' ? 'en' : 'zh';
    } catch (e) {
      return 'zh';
    }
  }

  function translate(lang, key) {
    return lang === 'en' && Object.prototype.hasOwnProperty.call(table, key) ? table[key] : key;
  }

  function apply(lang) {
    document.documentElement.setAttribute('lang', lang === 'en' ? 'en' : 'zh-Hans');
    var nodes = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].textContent = translate(lang, nodes[i].getAttribute('data-i18n'));
    }
    ['placeholder', 'aria-label', 'title'].forEach(function (attr) {
      var targets = document.querySelectorAll('[data-i18n-' + attr + ']');
      for (var j = 0; j < targets.length; j++) {
        targets[j].setAttribute(attr, translate(lang, targets[j].getAttribute('data-i18n-' + attr)));
      }
    });
    /* 标题与描述：原文留一份中文，切回中文时照原文还原 */
    var title = document.querySelector('title');
    if (title) {
      if (!title.dataset.i18nOrigin) title.dataset.i18nOrigin = title.textContent.trim();
      title.textContent = translate(lang, title.dataset.i18nOrigin);
    }
    var desc = document.querySelector('meta[name="description"]');
    if (desc) {
      if (!desc.dataset.i18nOrigin) desc.dataset.i18nOrigin = desc.getAttribute('content') || '';
      desc.setAttribute('content', translate(lang, desc.dataset.i18nOrigin));
    }
    /* 顶栏语言按钮：中文界面提示切英文，英文界面提示切中文 */
    var btn = document.getElementById('btn-language');
    if (btn) {
      btn.textContent = lang === 'en' ? '中文' : 'EN';
      btn.setAttribute('lang', lang === 'en' ? 'zh-Hans' : 'en');
      btn.setAttribute('aria-label', lang === 'en' ? '中文: Switch to Chinese' : 'EN: Switch to English');
      btn.setAttribute('title', lang === 'en' ? 'Switch to Chinese' : 'Switch to English');
    }
  }

  window.PLIB_I18N_APPLY = apply;

  function init() {
    /* 首页由 app.js 一次性翻译并重绘动态区域；这里若再跑，会把结果计数等
       带 data-i18n 的节点还原成模板初始文案。静态初始化只服务独立的 404 页。 */
    if (document.getElementById('prompt-data')) return;
    var lang = storedLang();
    apply(lang);
    /* 语言变化时重绘运行时生成的内容，由 app.js 监听这个事件 */
    window.addEventListener('plib:langchange', function (ev) {
      apply(ev && ev.detail === 'en' ? 'en' : 'zh');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
