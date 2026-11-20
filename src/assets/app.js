/* ==========================================================================
   提示词库 — 前端交互
   数据内联，所有个人状态仅写入 localStorage。
   ========================================================================== */
(function () {
  'use strict';

  var DATA = JSON.parse(document.getElementById('prompt-data').textContent);
  var LS = {
    fav: 'plib.fav.v1', used: 'plib.used.v1', custom: 'plib.custom.v1',
    opts: 'plib.opts.v1', theme: 'plib.theme.v1', sort: 'plib.sort.v1', lang: 'plib.lang.v1'
  };
  var PAGE_SIZE = 24;

  var store = {
    get: function (k, d) {
      try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; }
      catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* 隐私模式或空间不足 */ }
    }
  };

  function isRecord(value) {
    return !!value && typeof value === 'object' && !Array.isArray(value);
  }

  var savedSort = store.get(LS.sort, 'default');
  var savedCustom = store.get(LS.custom, []);
  var savedFav = store.get(LS.fav, {});
  var savedUsed = store.get(LS.used, {});
  var savedOpts = store.get(LS.opts, {});
  if (!isRecord(savedOpts)) savedOpts = {};
  var savedPrefix = typeof savedOpts.prefix === 'string' ? savedOpts.prefix : (savedOpts.loop ? '/loop' : '');
  /* 多选版曾存 blocks 数组：回退单选时取第一个勾选的块，自定义文本不受影响 */
  var savedBlock = typeof savedOpts.block === 'string' ? savedOpts.block
    : (Array.isArray(savedOpts.blocks) && typeof savedOpts.blocks[0] === 'string' ? savedOpts.blocks[0] : '');
  var savedLanguage = store.get(LS.lang, 'zh');
  var state = {
    cat: 'all',
    q: '',
    lang: savedLanguage === 'en' ? 'en' : 'zh',
    usedSort: savedSort === 'used',
    fav: isRecord(savedFav) ? savedFav : {},
    used: isRecord(savedUsed) ? savedUsed : {},
    custom: Array.isArray(savedCustom) ? savedCustom : [],
    opts: {
      prefix: savedPrefix,
      block: savedBlock,
      customPrefix: typeof savedOpts.customPrefix === 'string' ? savedOpts.customPrefix : '',
      customBlock: typeof savedOpts.customBlock === 'string' ? savedOpts.customBlock : ''
    },
    editing: null,
    focusIndex: -1,
    focusId: null,   /* 当前选中的卡片 id：重绘后按它把焦点找回来 */
    limit: PAGE_SIZE
  };
  /* 「全部提示词」页随机序的种子：每次打开页面随机一副，页内保持不变，
     只有点「换一批」才换——否则从分类页返回时顺序全变，找不回刚才看到的位置 */
  var browseSeed = (Math.random() * 0xffffffff) >>> 0;

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var elSearch = $('#search'), elSearchClear = $('#search-clear'), elSearchKbd = $('.search-kbd');
  var elGrid = $('#grid'), elNav = $('#cat-nav'), elEmpty = $('#empty');
  var elStat = $('#stat-count'), elContext = $('#current-context');
  var elToast = $('#toast'), elSidebar = $('#sidebar'), elBackdrop = $('#sidebar-backdrop');
  var elBlock = $('#opt-block'), elPrefix = $('#opt-prefix'), elCopyPanel = $('#copy-panel');
  var elPrefixCustom = $('#opt-prefix-custom'), elBlockCustom = $('#opt-block-custom');
  var elExportPanel = $('#export-panel');
  var elModal = $('#modal'), elHelp = $('#help');
  var elLoadMore = $('#load-more');
  var elFilterBar = $('#filter-bar');
  var elTop = $('#btn-top');

  var index = {};
  var categories = [];
  var blockList = [];
  var lastFocused = null;
  var pendingRevealId = null;  /* 弹窗内导入时暂缓定位，关闭弹窗后再滚动背景 */
  var toastTimer;
  var searchTimer;

  /* 中文是源文案；英文界面从独立字典取值，参数统一用 {name} 替换。 */
  function t(key, vars) {
    var table = window.PLIB_I18N || {};
    var value = state.lang === 'en' && Object.prototype.hasOwnProperty.call(table, key) ? table[key] : key;
    if (vars) Object.keys(vars).forEach(function (name) {
      /* 用函数形式替换：字符串形式的替换里 $&、$`、$' 有特殊含义，
         分类名里出现这些符号会被吞掉或错位。 */
      value = value.replace(new RegExp('\\{' + name + '\\}', 'g'), function () { return String(vars[name]); });
    });
    return value;
  }

  function pText(p, key) {
    var translated = state.lang === 'en' && p.en && p.en[key];
    return typeof translated === 'string' ? translated : (p[key] || '');
  }

  function pTags(p) {
    return state.lang === 'en' && p.en && Array.isArray(p.en.tags) ? p.en.tags : (p.tags || []);
  }

  function catText(c, key) {
    var translated = state.lang === 'en' && c.en && c.en[key];
    return typeof translated === 'string' ? translated : (c.customCategory && key === 'desc' ? t(c[key]) : (c[key] || ''));
  }

  function sectionText(name) {
    var sections = DATA.en && DATA.en.sections;
    return state.lang === 'en' && sections && sections[name] ? sections[name] : t(name);
  }

  function icon(name) {
    return '<svg aria-hidden="true"><use href="#i-' + name + '"></use></svg>';
  }

  /* 只为三个固定入口保留图标；普通分类统一使用纯文字。 */
  var SIDEBAR_ICONS = { all: '✦', fav: '★', custom: '✚' };

  /* ---------- 数据模型 ---------- */
  function buildModel() {
    categories = DATA.categories.map(function (c) {
      var en = DATA.en && DATA.en.categories && DATA.en.categories[c.id];
      return Object.assign({}, c, { en: en || null, prompts: c.prompts.slice() });
    });

    /* 未分类的自定义条目归入内部兜底分类：只从侧栏「自定义」入口看，
       不在侧栏「我的分类」与「全部提示词」分组里单列；条目真带了自建分类名才建侧栏分类。 */
    var internal = {
      id: 'custom-我的自定义', name: '我的自定义', prompts: [], internal: true
    };

    state.custom.forEach(function (raw) {
      if (!raw || typeof raw.id !== 'string' || typeof raw.title !== 'string' ||
          typeof raw.content !== 'string' || !raw.id || !raw.title.trim() || !raw.content.trim()) return;
      /* 与库内 id 撞车的自建数据直接跳过：下面建索引时它会顶掉官方条目，
         官方那条在列表里凭空消失，自建那条还会在两个分类里各出现一次。
         正常路径（新建与导入）都会拦掉这种 id，这里兜住手改过的旧数据。 */
      if (isLibraryId(raw.id)) return;
      var catName = typeof raw.category === 'string' && raw.category.trim() ? raw.category.trim() : '我的自定义';
      var target = catName === '我的自定义' ? internal :
        categories.filter(function (c) { return c.name === catName; })[0];
      if (!target) {
        target = {
          id: 'custom-' + catName, name: catName,
          desc: '自己创建的提示词分类', section: '我的分类', order: 90, prompts: [], customCategory: true
        };
        categories.push(target);
      }
      target.prompts.push(Object.assign({}, raw, {
        custom: true, category: catName,
        short: typeof raw.short === 'string' ? raw.short : '',
        note: typeof raw.note === 'string' ? raw.note : '',
        tags: Array.isArray(raw.tags) ? raw.tags.filter(function (t) { return typeof t === 'string'; }) : []
      }));
    });

    /* 兜底分类只作数据归属（进搜索、收藏、计数与「自定义」页），不进侧栏分类列表 */
    if (internal.prompts.length) categories.push(internal);

    index = {};
    categories.forEach(function (c) {
      c.prompts.forEach(function (p) {
        /* 同一个 id 只留一条：库内条目先建索引，后来的自建条目不再覆盖它 */
        if (index[p.id]) return;
        /* 兜底分类的条目在卡片徽标上就写「自定义」，与侧栏「自定义」入口一致 */
        var badge = c.internal ? t('自定义') : catText(c, 'name');
        var en = DATA.en && DATA.en.prompts && DATA.en.prompts[p.id];
        index[p.id] = Object.assign({}, p, { en: en || null, catId: c.id, catName: badge });
      });
    });

    if (state.cat !== 'all' && state.cat !== 'fav' && state.cat !== 'custom' &&
        !categories.some(function (c) { return c.id === state.cat; })) {
      state.cat = 'all';
    }
  }

  function allPrompts() {
    var out = [];
    var seen = Object.create(null);
    categories.forEach(function (c) {
      c.prompts.forEach(function (p) {
        /* 同 id 只出一张卡：自建条目与库内条目撞车时不重复计数 */
        if (!index[p.id] || seen[p.id]) return;
        seen[p.id] = true;
        out.push(index[p.id]);
      });
    });
    return out;
  }

  function getCategory(id) {
    return categories.filter(function (c) { return c.id === id; })[0];
  }

  /* 库内条目的 id（不含用户自建条目）。判断「这是不是收藏导出文件」只能用库内 id：
     自建条目也会进 index，拿它去判会把「重复导入自定义」误报成「拿错了文件」。 */
  function isLibraryId(id) {
    return DATA.categories.some(function (c) {
      return c.prompts.some(function (p) { return p.id === id; });
    });
  }

  /* ---------- 分类导航 ---------- */
  function navLink(id, symbol, name, count, desc) {
    var on = state.cat === id;
    return '<button type="button" class="cat-link' + (on ? ' is-on' : '') + '" data-cat="' + esc(id) + '"' +
      (on ? ' aria-current="page"' : '') + (desc ? ' title="' + esc(desc) + '"' : '') + '>' +
      (symbol ? '<span class="ci" aria-hidden="true">' + esc(symbol) + '</span>' : '') +
      '<span class="cn">' + esc(name) + '</span><span class="cc">' + count + '</span></button>';
  }

  function renderNav() {
    var prompts = allPrompts();
    var visibleCats = categories.filter(function (c) { return !c.internal; });
    /* 引导区里的三个数字说的是这个库本身：用户自建的条目与自建分类不计入，
       否则本机攒了两条就变成 471 条，和 README 里写的条数对不上。 */
    $('#hero-total').textContent = DATA.categories.reduce(function (n, c) { return n + c.prompts.length; }, 0);
    $('#hero-cat').textContent = DATA.categories.length;
    $('#hero-section').textContent = (DATA.sections || []).length;
    var counts = {};
    prompts.forEach(function (p) { counts[p.catId] = (counts[p.catId] || 0) + 1; });
    var favCount = prompts.filter(function (p) { return state.fav[p.id]; }).length;
    var customCount = prompts.filter(function (p) { return p.custom; }).length;
    var html = '<div class="cat-group cat-group-primary">';
    html += navLink('all', SIDEBAR_ICONS.all, t('全部提示词'), prompts.length, t('浏览所有分类'));
    html += navLink('fav', SIDEBAR_ICONS.fav, t('我的收藏'), favCount, t('仅显示已收藏的提示词'));
    html += navLink('custom', SIDEBAR_ICONS.custom, t('自定义'), customCount, t('仅显示你自己创建的提示词'));
    html += '</div>';

    var byId = {};
    visibleCats.forEach(function (c) { byId[c.id] = c; });
    /* 有自建分类时放在库内分区前，让用户先看到自己的分类。 */
    var extra = visibleCats.filter(function (c) {
      return !(DATA.sections || []).some(function (s) { return (s.categories || []).indexOf(c.id) >= 0; });
    });
    if (extra.length) {
      var extraTotal = extra.reduce(function (n, c) { return n + (counts[c.id] || 0); }, 0);
      html += '<section class="cat-group"><h2 class="cat-head">' + t('我的分类') + '<span class="sec-n">' + extraTotal + '</span></h2>';
      extra.forEach(function (c) {
        html += navLink(c.id, '', catText(c, 'name'), counts[c.id] || 0, catText(c, 'desc'));
      });
      html += '</section>';
    }

    (DATA.sections || []).forEach(function (sec) {
      var ids = sec.categories || [];
      if (!ids.length) return;
      var total = ids.reduce(function (n, id) { return n + (counts[id] || 0); }, 0);
      html += '<section class="cat-group"><h2 class="cat-head">' + esc(sectionText(sec.name)) +
        '<span class="sec-n">' + total + '</span></h2>';
      ids.forEach(function (id) {
        var c = byId[id];
        if (c) html += navLink(c.id, '', catText(c, 'name'), counts[c.id] || 0, catText(c, 'desc'));
      });
      html += '</section>';
    });
    elNav.innerHTML = html;
    syncNav();
  }

  function syncNav() {
    $$('.cat-link', elNav).forEach(function (a) {
      var on = a.dataset.cat === state.cat;
      a.classList.toggle('is-on', on);
      if (on) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    var favActive = state.cat === 'fav';
    $('#btn-fav').setAttribute('aria-pressed', favActive ? 'true' : 'false');
    $('#btn-fav').setAttribute('aria-label', t(favActive ? '返回全部提示词' : '查看我的收藏'));
    $('#btn-fav').title = t(favActive ? '返回全部提示词' : '查看我的收藏');
  }

  /* ---------- 搜索、排序与渲染 ---------- */
  function queryTerms() {
    /* 关键词也可能是 constructor、toString 等对象原型字段名；
       普通对象会把它们误判为「已经见过」，导致整个搜索词被吞掉。 */
    var seen = Object.create(null);
    return state.q.trim().toLowerCase().split(/\s+/).filter(function (t) {
      if (!t || seen[t]) return false;
      seen[t] = true;
      return true;
    }).slice(0, 12);
  }

  function relevance(p, terms) {
    var title = pText(p, 'title').toLowerCase();
    var tags = pTags(p).join(' ').toLowerCase();
    var short = pText(p, 'short').toLowerCase();
    var content = pText(p, 'content').toLowerCase();
    var cat = p.catName.toLowerCase();
    var score = 0;
    terms.forEach(function (t) {
      if (title === t) score += 100;
      else if (title.indexOf(t) === 0) score += 35;
      else if (title.indexOf(t) >= 0) score += 24;
      if (tags.split(' ').indexOf(t) >= 0) score += 15;
      else if (tags.indexOf(t) >= 0) score += 9;
      if (cat.indexOf(t) >= 0) score += 6;
      if (short.indexOf(t) >= 0) score += 5;
      if (content.indexOf(t) >= 0) score += 2;
    });
    return score;
  }

  function filtered() {
    var list = allPrompts();
    var terms = queryTerms();
    /* 搜索默认全局：有搜索词时忽略分类范围，在全部条目里找；
       没有搜索词时才按当前分类（含收藏、自定义）过滤。 */
    if (!terms.length) {
      if (state.cat === 'fav') list = list.filter(function (p) { return state.fav[p.id]; });
      else if (state.cat === 'custom') list = list.filter(function (p) { return p.custom; });
      else if (state.cat !== 'all') list = list.filter(function (p) { return p.catId === state.cat; });
    }

    if (terms.length) {
      list = list.filter(function (p) {
        var haystack = (pText(p, 'title') + ' ' + pText(p, 'content') + ' ' + pText(p, 'short') + ' ' +
          pTags(p).join(' ') + ' ' + p.catName + ' ' + (p.note || '')).toLowerCase();
        return terms.every(function (t) { return haystack.indexOf(t) >= 0; });
      });
    }

    if (terms.length) {
      /* 搜索一律按相关度排：「按复制次数」是浏览全库时的排序，
         若拿它盖住相关度，搜「周报」最像的那条会被按复制次数（多半都是 0）
         排到后面去，等于白搜。 */
      list = list.map(function (p, i) { return { p: p, i: i, score: relevance(p, terms) }; })
        .sort(function (a, b) { return b.score - a.score || a.i - b.i; })
        .map(function (x) { return x.p; });
    } else if (state.usedSort) {
      /* 按复制次数排列：先比次数，次数相同保持库内原有顺序（sort 在现代引擎里是稳定的） */
      list.sort(function (a, b) { return (Number(state.used[b.id]) || 0) - (Number(state.used[a.id]) || 0); });
    } else if (state.cat === 'all') {
      list = browseSorted(list);
    }
    return list;
  }

  /* 「全部提示词」页的随机顺序：按 id 与种子算一个散列值来排。
     种子在一次浏览里固定，所以翻页、收藏、展开时卡片不会跳来跳去；
     点「换一批」换种子，就换一副顺序。 */
  function browseSeedOf(id, seed) {
    var h = seed >>> 0;
    for (var i = 0; i < id.length; i++) {
      h = (Math.imul(h, 31) + id.charCodeAt(i)) >>> 0;
    }
    return h >>> 0;
  }

  function browseSorted(list) {
    var seed = browseSeed;
    return list.map(function (p, i) { return { p: p, i: i, k: browseSeedOf(p.id, seed) }; })
      .sort(function (a, b) { return a.k - b.k || a.i - b.i; })
      .map(function (x) { return x.p; });
  }

  function contextName() {
    if (state.q.trim()) return t('搜索结果');
    if (state.cat === 'fav') return t('我的收藏');
    if (state.cat === 'custom') return t('自定义提示词');
    if (state.cat === 'all') return t('全部提示词');
    var c = getCategory(state.cat);
    return c ? catText(c, 'name') : t('全部提示词');
  }

  /* 当前生效的筛选条件：把「搜了什么 / 在哪个分类」直接摆在结果上方，
     滚远之后也能一眼看清当前范围，并且可以逐条撤掉。 */
  /* 空状态跟随当前范围给出不同说法，避免一律显示「没有找到相关提示词」。
     搜索是全局的：搜不到只与关键词有关，与进入页面时的分类无关。 */
  function renderEmptyState(count) {
    if (count) return;
    var title = $('#empty-title'), desc = $('#empty-desc'), reset = $('#empty-reset');
    var mark = $('#empty .empty-mark use');
    if (mark) mark.setAttribute('href', state.cat === 'fav' ? '#i-star' : (state.cat === 'custom' ? '#i-edit' : '#i-search'));
    if (queryTerms().length) {
      title.textContent = t('没有找到相关提示词');
      desc.textContent = t('在全部提示词里没搜到相关内容，换个关键词试试。');
      reset.textContent = t('清空搜索与筛选');
    } else if (state.cat === 'fav') {
      title.textContent = t('还没有收藏任何提示词');
      desc.textContent = t('在卡片右上角点星标即可收藏；收藏只保存在当前浏览器。');
      reset.textContent = t('去看全部提示词');
    } else if (state.cat === 'custom') {
      title.textContent = t('还没有自定义提示词');
      desc.textContent = t('点右上角「新建」写下一条自己的提示词，保存后只留在当前浏览器。');
      reset.textContent = t('去看全部提示词');
    } else if (state.cat === 'all') {
      /* 全部提示词有内容，正常情况下不会落到这里；仅防兜底误报 */
      title.textContent = t('没有找到相关提示词');
      desc.textContent = t('换个关键词，或清空分类与搜索条件后再试试。');
      reset.textContent = t('清空搜索与筛选');
    } else {
      title.textContent = t('这个分类暂时是空的');
      desc.textContent = t('换个分类看看，或者新建一条属于自己的提示词。');
      reset.textContent = t('查看全部提示词');
    }
  }

  function renderFilterBar() {
    var chips = [];
    var q = state.q.trim();
    if (q) chips.push({ key: 'q', label: t('关键词'), value: q });
    if (state.cat === 'fav') chips.push({ key: 'fav', label: t('范围'), value: t('我的收藏') });
    else if (state.cat === 'custom') chips.push({ key: 'custom', label: t('范围'), value: t('自定义提示词') });
    else if (state.cat !== 'all') {
      var c = getCategory(state.cat);
      if (c) chips.push({ key: 'cat', label: t('分类'), value: catText(c, 'name') });
    }
    if (!chips.length) {
      elFilterBar.hidden = true;
      elFilterBar.innerHTML = '';
      return;
    }
    var html = '<span class="filter-label" aria-hidden="true"><svg><use href="#i-filter"></use></svg>' + t('当前筛选') + '</span>';
    chips.forEach(function (chip) {
      html += '<button type="button" class="filter-chip" data-clear="' + chip.key + '" title="' + t('移除此条件') + '">' +
        '<span class="fk">' + esc(chip.label) + '</span><span class="fv">' + esc(chip.value) + '</span>' +
        '<svg class="fx" aria-hidden="true"><use href="#i-close"></use></svg>' +
        '<span class="sr-only">' + t('移除') + '</span></button>';
    });
    /* 一次只会有一条筛选：搜索是全局的，一有搜索词分类范围就退掉了，
       两个 chip 永远凑不到一起，「清除全部」也就没有出场的场合。 */
    elFilterBar.hidden = false;
    elFilterBar.innerHTML = html;
  }

  function clearFilter(key) {
    if (key === 'q') {
      clearTimeout(searchTimer);
      setSearch('', true);
    } else if (key === 'cat' || key === 'fav' || key === 'custom') {
      state.cat = 'all';
      resetView();
      render();
    }
  }

  function render(keepFocus) {
    var list = filtered();
    var terms = queryTerms();
    /* 重绘会整片换掉网格里的卡片节点，键盘用户刚选中的那张连同焦点一起没了：
       自动接续每扩一页就重画一次，方向键随即失灵（下次按键又从第一张开始）。
       所以重绘前先记住选中的卡片 id，画完再把它找回来。 */
    var keepId = keepFocus ? state.focusId : null;
    /* 「全部提示词」页：上面是全库目录，下面是随机顺序的卡片流。
       其余页面（分类、收藏、自定义、搜索）按库内顺序列，顺序本身有意义。
       随机序已在 filtered() 里排好，这里直接切前 N 条。 */
    var browse = state.cat === 'all' && !terms.length;
    var shown = list.slice(0, state.limit);
    elContext.textContent = contextName();

    /* 分类页先给一句「这一类管什么」：分类的 desc 原本只挂在侧栏与目录的
       悬停提示里，进分类页反而看不到，进来的人不知道该在这里找什么。 */
    var lead = '';
    if (!browse && !terms.length) {
      var cat = getCategory(state.cat);
      if (cat && !cat.internal && cat.desc) {
        lead = '<p class="cat-lead"><span class="cat-lead-label">' + t('这一类覆盖') + '</span>' +
          esc(catText(cat, 'desc')) + '</p>';
      }
    }

    elGrid.innerHTML = lead + (browse ? allMapHTML() + randomBarHTML() : '') + gridHTML(shown, terms);
    var shownCount = shown.length;
    elStat.innerHTML = t(terms.length ? '找到 {n} 条' : '共 {n} 条', { n: '<b>' + list.length + '</b>' }) +
      (shownCount < list.length ? t(' · 已显示 {n}', { n: shownCount }) : '');

    elEmpty.hidden = list.length > 0;
    elGrid.hidden = list.length === 0;
    renderFilterBar();
    renderEmptyState(list.length);
    updateExportNote();
    mountSentinel(list);

    var usedSortBtn = $('#btn-used-sort');
    usedSortBtn.classList.toggle('is-on', state.usedSort);
    usedSortBtn.setAttribute('aria-pressed', state.usedSort ? 'true' : 'false');
    /* 提示文字跟着状态走：开着时说明「再点一次关掉」，别让人猜这是个不可逆的开关。
       有搜索词时结果按相关度排，这个开关不参与——写明它管的是无搜索词时的顺序，
       否则会以为开关坏了。 */
    var usedSortLabel;
    /* 无障碍名必须包含按钮上看得见的文字（WCAG 2.5.3「标签含名称」）：
       读屏念出的名字里若没有「按复制次数排列」，语音控制用户按字面说
       「按复制次数排列」就找不到这个按钮。所以解释一律接在可见文字后面。 */
    if (terms.length) {
      usedSortLabel = t('按复制次数排列：搜索时按相关度排序，此开关在无搜索词时生效') +
        (state.usedSort ? t('（当前已开启）') : '');
    } else {
      usedSortLabel = state.usedSort
        ? t('按复制次数排列：关闭后恢复') + t(state.cat === 'all' ? '随机顺序' : '原有顺序')
        : t('按复制次数排列：把当前列表按复制次数从多到少排列');
    }
    usedSortBtn.title = usedSortLabel;
    usedSortBtn.setAttribute('aria-label', usedSortLabel);

    var remaining = Math.max(0, list.length - shownCount);
    elLoadMore.hidden = remaining === 0;
    if (remaining) {
      $('#btn-load-more').innerHTML = '<span>' + t('再显示 {n} 条', { n: Math.min(PAGE_SIZE, remaining) }) + '</span>' + icon('chevron');
      $('#load-more-count').textContent = t('还有 {n} 条未显示', { n: remaining });
    }
    /* 重绘后卡片都是新节点，原先持有焦点的元素已被销毁，选中态随之清空 */
    state.focusIndex = -1;
    if (keepId) restoreFocus(keepId);
    syncNav();
  }

  /* 重绘后把焦点还给原来那张卡：自动接续会重建整片网格，
     键盘用户不该因此被甩回列表开头。找不到（条目被换掉了）就不动。 */
  function restoreFocus(id) {
    var cards = $$('.card', elGrid);
    for (var i = 0; i < cards.length; i++) {
      if (cards[i].dataset.id === id) {
        setKbdCard(cards[i]);
        cards[i].focus({ preventScroll: true });
        return;
      }
    }
  }

  function gridHTML(items, terms) {
    if (!items.length) return '';
    return '<div class="grid">' + items.map(function (p) { return cardHTML(p, terms); }).join('') + '</div>';
  }

  /* 目录用：按分区把分类排好（含用户自建分类），只取分类，不做条目分组。
     分类页与「全部提示词」页首目录共用这一份清单。 */
  function sectionCats() {
    var byId = {};
    categories.forEach(function (c) { byId[c.id] = c; });
    var groups = [];
    (DATA.sections || []).forEach(function (sec) {
      var cats = (sec.categories || []).map(function (cid) { return byId[cid]; })
        .filter(function (c) { return c && !c.internal; });
      if (cats.length) groups.push({ name: sec.name, cats: cats });
    });
    var taken = {};
    groups.forEach(function (g) { g.cats.forEach(function (c) { taken[c.id] = true; }); });
    /* 用户自建分类不在内部分区里，单独一行并排在库内分区前 */
    var extra = categories.filter(function (c) {
      return !c.internal && !taken[c.id] && c.prompts.length;
    });
    if (extra.length) groups.unshift({ name: '我的分类', cats: extra });
    return groups;
  }

  /* 「全部提示词」页首的全库目录：所有分区与分类一览，点分类直达对应页。
     没有它，每个分类的入口只出现在侧栏里，不开侧栏就看不到、点不到。 */
  function allMapHTML() {
    var html = '<nav class="all-map" aria-label="' + t('全部分类目录') + '">';
    sectionCats().forEach(function (g) {
      var chips = g.cats.map(function (c) {
        return '<button type="button" class="map-chip" data-cat="' + esc(c.id) + '"' +
          (catText(c, 'desc') ? ' title="' + esc(catText(c, 'desc')) + '"' : '') + '>' +
          esc(catText(c, 'name')) + '<span class="cc">' + c.prompts.length + '</span></button>';
      }).join('');
      html += '<div class="all-map-row" data-section="' + esc(g.name) + '">' +
        '<span class="all-map-sec">' + esc(sectionText(g.name)) + '</span>' +
        '<div class="all-map-chips">' + chips + '</div></div>';
    });
    return html + '</nav>';
  }

  /* 目录下面接一句说明加一个「换一批」：这批卡片按随机顺序给，
     看腻了可以重换一副，不影响上面目录的定位。
     开了「按复制次数排列」时顺序由复制次数定，这行就只作说明——
     要写明是「全部条目」按次数排，否则会被当成只重排眼前这批随机卡片。 */
  function randomBarHTML() {
    var note = state.usedSort
      ? t('全部提示词按复制次数从多到少排列')
      : t('下面是随机顺序的提示词');
    var btn = state.usedSort ? '' :
      '<button type="button" class="text-btn" data-act="reshuffle">' + t('换一批') + '</button>';
    return '<div class="all-random"><span class="all-random-note">' + note + '</span>' + btn + '</div>';
  }

  function hasShort(p) {
    var short = pText(p, 'short'), content = pText(p, 'content');
    return !!(short && short.trim() && short.trim() !== content.trim());
  }

  function cardHTML(p, terms) {
    var used = state.used[p.id] || 0;
    var tags = pTags(p).map(function (tag) {
      return '<button type="button" class="tag" data-tag="' + esc(tag) + '" title="' + t('搜索标签：') + esc(tag) + '">' + hl(tag, terms) + '</button>';
    }).join('');
    var safeId = esc(p.id);
    var fav = !!state.fav[p.id];
    var variants = hasShort(p) ?
      '<section class="variant variant-short"><div class="variant-head">' +
      '<span class="variant-label">' + t('简洁表达') + '</span>' +
      '<div class="variant-actions"><button class="copy-btn" type="button" data-act="copy-short" aria-label="' + t('复制简洁表达') + '">' + icon('copy') + '<span>' + t('复制') + '</span></button></div></div>' +
      '<div class="variant-body">' + hl(pText(p, 'short'), terms) + '</div></section>' +
      '<section class="variant variant-full"><div class="variant-head">' +
      '<span class="variant-label">' + t('详细表达') + '</span>' +
      '<div class="variant-actions"><button class="copy-btn" type="button" data-act="copy" aria-label="' + t('复制详细表达') + '">' + icon('copy') + '<span>' + t('复制') + '</span></button></div></div>' +
      '<div class="variant-body">' + hl(pText(p, 'content'), terms) + '</div></section>' :
      '<section class="variant variant-single"><div class="variant-head">' +
      '<span class="variant-label">' + t('提示词正文') + '</span>' +
      '<div class="variant-actions"><button class="copy-btn" type="button" data-act="copy" aria-label="' + t('复制提示词') + '">' + icon('copy') + '<span>' + t('复制') + '</span></button></div></div>' +
      '<div class="variant-body">' + hl(pText(p, 'content'), terms) + '</div></section>';

    return '<article class="card" data-id="' + safeId + '" tabindex="-1" aria-labelledby="title-' + safeId + '">' +
      '<div class="card-top"><span class="card-category"><span class="category-name">' + esc(p.catName) + '</span></span><div class="card-tools">' +
      '<button class="card-tool" type="button" data-act="share" title="' + t('复制这条提示词的链接') + '" aria-label="' + t('复制链接') + '">' + icon('link') + '</button>' +
      '<button class="card-tool fav-btn' + (fav ? ' is-on' : '') + '" type="button" data-act="fav" title="' + t(fav ? '取消收藏' : '收藏') + '" aria-label="' + t(fav ? '取消收藏' : '收藏') + '" aria-pressed="' + fav + '">' + icon('star') + '</button>' +
      '</div></div>' +
      '<h3 class="card-title" id="title-' + safeId + '">' + hl(pText(p, 'title'), terms) + '</h3>' +
      (tags ? '<div class="tags">' + tags + '</div>' : '') +
      (p.note ? '<p class="card-note">' + t('备注：') + hl(p.note, terms) + '</p>' : '') +
      variants +
      '<div class="card-foot' + (p.custom || used ? '' : ' is-empty') + '">' +
      (p.custom ? '<button class="copy-btn edit-btn" type="button" data-act="edit">' + icon('edit') + t('编辑') + '</button>' +
        '<button class="copy-btn delete-btn" type="button" data-act="del">' + icon('trash') + t('删除') + '</button>' : '') +
      '<span class="used">' + (used ? t('已复制 {n} 次', { n: used }) : '') + '</span></div></article>';
  }

  function resetView() {
    state.focusIndex = -1;
    state.limit = PAGE_SIZE;
  }

  /* ---------- 滚动自动接续 ---------- */
  /* 网格末尾埋一个隐形哨兵，滚到附近就扩一页——插入点在视口边缘之外，
     上方内容不动，滚动位置不被顶走。「再显示」按钮保留，作为键盘用户与
     IntersectionObserver 不可用时的手动兜底。 */
  var sentinelTick = 0;   /* 回调节流与重入保护：一次触发处理完前不再响应 */
  var scrollObserver = null;
  /* 跳转锁：平滑滚动途中不能触发自动展开——
     哨兵一命中就重绘，目标节点会被销毁，滚动会停在过期坐标上。
     锁到滚动结束（连续一小段时间没有滚动事件）再放开。 */
  var jumpLock = false;
  var jumpUnlockTimer = 0;

  function lockJump() {
    jumpLock = true;
    clearTimeout(jumpUnlockTimer);
    /* 兜底：滚动事件没来（比如目标已在视口内）也要放开，否则自动展开会停摆 */
    jumpUnlockTimer = setTimeout(function () { jumpLock = false; }, 1200);
  }

  function unlockJumpOnIdle() {
    if (!jumpLock) return;
    clearTimeout(jumpUnlockTimer);
    jumpUnlockTimer = setTimeout(function () { jumpLock = false; }, 160);
  }

  function getScrollObserver() {
    if (scrollObserver || !('IntersectionObserver' in window)) return scrollObserver;
    scrollObserver = new IntersectionObserver(function (entries) {
      if (!entries.some(function (e) { return e.isIntersecting; })) return;
      if (jumpLock) return;
      if (sentinelTick) return;
      sentinelTick = setTimeout(function () {
        sentinelTick = 0;
        var hit = entries.filter(function (e) {
          return e.isIntersecting && e.target.isConnected && !e.target.hidden;
        })[0];
        if (!hit) return;
        state.limit += PAGE_SIZE;
        render(true);   /* 追加内容，保留键盘用户正在看的那张卡 */
      }, 90);
      /* rootMargin 只向下扩：视口上方的哨兵不触发，往回滚时不会在头顶插入内容 */
    }, { rootMargin: '0px 0px 600px 0px' });
    return scrollObserver;
  }

  /* 哨兵节点随 innerHTML 重绘一起被销毁，render 末尾统一重新挂载与观测 */
  var sentinelNodes = [];   /* 已观测的哨兵节点：重绘后旧节点已从 DOM 移除，
                              必须解除观测，否则观察器会一直攒着这些死节点 */
  function mountSentinel(list) {
    var observer = getScrollObserver();
    if (!observer) return;
    sentinelNodes.forEach(function (n) { observer.unobserve(n); });
    sentinelNodes = [];
    if (list.length > state.limit) {
      var node = document.createElement('div');
      node.className = 'load-sentinel';
      node.setAttribute('aria-hidden', 'true');
      elGrid.appendChild(node);
      sentinelNodes.push(node);
    }
    $$('.load-sentinel', elGrid).forEach(function (n) { observer.observe(n); });
  }

  function setSearch(value, global) {
    clearTimeout(searchTimer);
    state.q = value;
    elSearch.value = value;
    elSearchClear.hidden = !value;
    if (elSearchKbd) elSearchKbd.hidden = !!value;   /* 有内容时让位给清空按钮，两者重叠 */
    /* 搜索默认全局：设了搜索词就退出分类范围（global 参数保留给「手动清空」路径，
       清空时不强切页面，停留在当前分类）。 */
    if (global || value.trim()) state.cat = 'all';
    resetView();
    render();
    ensureContentVisible();
  }

  function preferredScrollBehavior() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  }

  function scrollToContent() {
    var headerOffset = $('.topbar').offsetHeight + 20;
    var top = $('#main').getBoundingClientRect().top + window.scrollY - headerOffset;
    window.scrollTo({ top: Math.max(0, top), behavior: preferredScrollBehavior() });
  }

  /* 「换一批」后回到随机条那一行：重排过的卡片要从头看起，
     不然视口停在原处，看着像什么都没换。 */
  function scrollToRandomBar() {
    var bar = $('.all-random');
    if (!bar) { scrollToContent(); return; }
    var headerOffset = $('.topbar').offsetHeight + 20;
    var top = bar.getBoundingClientRect().top + window.scrollY - headerOffset;
    window.scrollTo({ top: Math.max(0, top), behavior: preferredScrollBehavior() });
  }

  /* 内容整体被替换（搜索/清空/排序切换）后调用：视口若还停在旧内容的深处，
     用户看到的只是新结果的中段——拉回内容区顶部，从第一条开始看。
     视口在顶附近（正在打字补关键词）时不动作，不与用户抢滚动。 */
  function ensureContentVisible() {
    var mainTop = $('#main').getBoundingClientRect().top + window.scrollY;
    if (window.scrollY > mainTop + 120) scrollToContent();
  }

  function chooseCategory(id) {
    var drawerOpen = elSidebar.classList.contains('is-open');
    /* 点分类=离开搜索模式：搜索是全局的，不随分类收窄，
       留着搜索词会让框里的话与看到的结果对不上，所以一并清掉。 */
    if (state.q) {
      clearTimeout(searchTimer);
      state.q = '';
      elSearch.value = '';
      elSearchClear.hidden = true;
      if (elSearchKbd) elSearchKbd.hidden = false;
    }
    state.cat = id;
    resetView();
    closeSidebar(false);
    render();
    if (drawerOpen) elContext.focus({ preventScroll: true });
    scrollToContent();
  }

  /* ---------- 复制与分享 ---------- */
  function activePrefix() {
    if (state.opts.prefix === '__custom') return state.opts.customPrefix.trim();
    return state.opts.prefix;
  }

  /* 追加段 = 选中的指令块（若有）+ 自定义指令（若有），各占一段 */
  function activeBlocks() {
    var parts = [];
    var b = blockList.filter(function (x) { return x.id === state.opts.block; })[0];
    if (b) parts.push(pText(b, 'content'));
    return parts;
  }

  function activeCustomBlock() {
    /* 自定义文本始终是附加段：选库存块时叠加在块后面，选「自定义…」时它就是唯一附加段 */
    return state.opts.customBlock.trim();
  }

  function buildText(p, variant) {
    var body = variant === 'short' && hasShort(p) ? pText(p, 'short') : pText(p, 'content');
    var blocks = activeBlocks();
    var custom = activeCustomBlock();
    if (custom) blocks.push(custom);
    if (blocks.length) body += '\n\n' + blocks.join('\n\n');
    var prefix = activePrefix();
    return prefix ? prefix + ' ' + body : body;
  }

  function doCopy(p, card, variant) {
    copyText(buildText(p, variant)).then(function () {
      state.used[p.id] = (Number(state.used[p.id]) || 0) + 1;
      store.set(LS.used, state.used);
      var copiedLabel = hasShort(p) ? (variant === 'short' ? '简洁表达' : '详细表达') : '提示词';
      toast(t('已复制' + copiedLabel));
      var btn = card && card.querySelector(variant === 'short' ? '[data-act="copy-short"]' : '[data-act="copy"]');
      if (btn) {
        clearTimeout(btn._copyTimer);
        btn.innerHTML = icon('check') + '<span>' + t('已复制') + '</span>';
        btn.classList.add('is-done');
        btn._copyTimer = setTimeout(function () {
          btn.innerHTML = icon('copy') + '<span>' + t('复制') + '</span>';
          btn.classList.remove('is-done');
        }, 1500);
      }
      var used = card && card.querySelector('.used');
      if (used) {
        used.textContent = t('已复制 {n} 次', { n: state.used[p.id] });
        used.parentElement.classList.remove('is-empty');
      }
    }, function () { toast(t('复制失败，请手动选中文本复制')); });
  }

  function legacyCopy(text) {
    return new Promise(function (resolve, reject) {
      var active = document.activeElement;
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.cssText = 'position:fixed;left:-9999px;top:0;opacity:0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      if (active && active.isConnected && active.focus) {
        try { active.focus({ preventScroll: true }); } catch (e) { active.focus(); }
      }
      if (ok) resolve(); else reject(new Error('copy failed'));
    });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
    }
    return legacyCopy(text);
  }

  function sharePrompt(p) {
    var url = location.href.split('#')[0] + '#' + encodeURIComponent(p.id);
    copyText(url).then(function () { toast(t('链接已复制，可直达这条提示词')); }, function () { toast(t('链接复制失败')); });
  }

  /* ---------- 导出为文件 ---------- */
  function downloadFile(filename, text, mime) {
    var blob = new Blob([text], { type: mime + ';charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
  }

  function exportStamp() {
    var d = new Date();
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return '' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate());
  }

  /* 导出的是原始正文：不套用复制设置里的任务命令与指令块，
     这样存下来的文件是可以直接复用/再编辑的提示词本身。 */
  /* 未分类的自定义条目在卡片上显示「自定义」，但原始归属是「我的自定义」。
     导出必须写原始归属，否则从收藏文件恢复时会被建成一个新的自建分类。 */
  function exportCategory(p) {
    return p.custom && typeof p.category === 'string' && p.category.trim() ? p.category : p.catName;
  }

  function promptsToMarkdown(list) {
    var out = ['# ' + t('GUAN 提示词库导出'), '',
      '- ' + t('来源') + (state.lang === 'en' ? ': ' : '：') + 'https://prompt.guanjihuan.com',
      '- ' + t('导出时间') + (state.lang === 'en' ? ': ' : '：') + new Date().toLocaleString(state.lang === 'en' ? 'en-US' : 'zh-CN'),
      '- ' + t('条目数') + (state.lang === 'en' ? ': ' : '：') + list.length, ''];
    list.forEach(function (p) {
      out.push('## ' + pText(p, 'title'));
      out.push('');
      out.push('- ' + t('分类') + (state.lang === 'en' ? ': ' : '：') + exportCategory(p));
      if (pTags(p).length) out.push('- ' + t('标签') + (state.lang === 'en' ? ': ' : '：') + pTags(p).join(state.lang === 'en' ? ', ' : '、'));
      if (p.id) out.push('- id' + (state.lang === 'en' ? ': ' : '：') + p.id);
      if (p.note) out.push('- ' + t('备注') + (state.lang === 'en' ? ': ' : '：') + p.note);
      out.push('');
      out.push(pText(p, 'content'));
      if (hasShort(p)) {
        out.push('');
        /* 简洁表达允许换行；每一行都写成引用行，导入时才能与正文分清。
           单行条目的导出格式保持不变。 */
        out.push('> ' + t('简洁表达') + (state.lang === 'en' ? ': ' : '：') + pText(p, 'short').replace(/\r\n?|\n/g, '\n> '));
      }
      out.push('');
      out.push('---');
      out.push('');
    });
    return out.join('\n');
  }

  function promptsToJSON(list) {
    return JSON.stringify({
      version: 1,
      exported_at: new Date().toISOString(),
      source: 'https://prompt.guanjihuan.com',
      count: list.length,
      prompts: list.map(function (p) {
        return {
          id: p.id,
          title: pText(p, 'title'),
          category: exportCategory(p),
          tags: pTags(p),
          content: pText(p, 'content'),
          short: hasShort(p) ? pText(p, 'short') : '',
          note: p.note || ''
        };
      })
    }, null, 2);
  }

  /* 导出只覆盖两类内容：我的收藏、我的自定义。 */
  function exportFav(format) {
    var list = allPrompts().filter(function (p) { return state.fav[p.id]; });
    if (!list.length) { toast(t('还没有收藏任何提示词')); return; }
    var name = 'prompt-library-fav-' + exportStamp();
    if (format === 'json') {
      downloadFile(name + '.json', promptsToJSON(list), 'application/json');
    } else {
      downloadFile(name + '.md', promptsToMarkdown(list), 'text/markdown');
    }
    toast(t('已导出 {n} 条收藏', { n: list.length }));
  }

  function updateExportNote() {
    var favCount = allPrompts().filter(function (p) { return state.fav[p.id]; }).length;
    var customCount = state.custom.length;
    var note = $('#export-note');
    if (note) {
      note.textContent = t('我的收藏 {fav} 条、自定义 {custom} 条；导出的是原始正文，不含复制设置里的任务命令与指令块。', {
        fav: favCount, custom: customCount
      });
    }
  }

  function selectedBlockTitle() {
    if (state.opts.block === '__custom') return '';
    var b = blockList.filter(function (x) { return x.id === state.opts.block; })[0];
    return b ? pText(b, 'title').replace(/指令块$/, '').replace(/\s+Instruction Block$/i, '') : '';
  }

  function optionSummary() {
    var parts = [];
    var prefix = activePrefix();
    if (prefix) parts.push((state.opts.prefix === '__custom' ? t('自定义任务命令') + ' ' + prefix : prefix + ' ' + t('任务命令')));
    var title = selectedBlockTitle();
    if (title) parts.push(t('指令块「{title}」', { title: title }));
    if (activeCustomBlock()) parts.push(t('自定义指令'));
    return parts.length ? t('复制时将添加：{items}。', { items: parts.join(t('、')) }) : t('当前为原始复制，不加命令或指令块。');
  }

  function updateOptionSummary() {
    var command = elPrefix.options[elPrefix.selectedIndex];
    var customPrefix = state.opts.prefix === '__custom';
    var prefix = activePrefix();
    $('#command-preview').hidden = !prefix;
    $('#command-description').textContent = customPrefix
      ? (prefix ? t('将使用自定义任务命令：') + prefix : '')
      : (command && prefix ? command.dataset.desc : '');
    var blocks = activeBlocks();
    var custom = activeCustomBlock();
    $('#block-preview').hidden = !(blocks.length || custom);
    $('#block-preview-content').textContent = blocks.concat(custom ? [custom] : []).join('\n\n');
    $('#copy-mode').textContent = optionSummary();
    $('#copy-options-dot').hidden = !(prefix || blocks.length || custom);
  }

  function saveOptions() {
    state.opts.prefix = elPrefix.value;
    state.opts.block = elBlock.value;
    /* 存原文、使用时才 trim：回写 trim 值会吃掉正在输入的结尾空格 */
    if (state.opts.prefix === '__custom') state.opts.customPrefix = elPrefixCustom.value;
    state.opts.customBlock = elBlockCustom.value;
    store.set(LS.opts, state.opts);
    updateOptionSummary();
  }

  function syncCustomInputs() {
    elPrefixCustom.hidden = state.opts.prefix !== '__custom';
    elBlockCustom.hidden = state.opts.block !== '__custom';
    if (state.opts.prefix === '__custom' && !elPrefixCustom.value) elPrefixCustom.value = state.opts.customPrefix;
    if (state.opts.block === '__custom' && !elBlockCustom.value) elBlockCustom.value = state.opts.customBlock;
  }

  function renderBlockOptions() {
    elBlock.innerHTML = '';
    var empty = document.createElement('option');
    empty.value = '';
    empty.textContent = t('不附加');
    elBlock.appendChild(empty);
    blockList.forEach(function (b) {
      var option = document.createElement('option');
      option.value = b.id;
      option.textContent = pText(b, 'title');
      elBlock.appendChild(option);
    });
    var custom = document.createElement('option');
    custom.value = '__custom';
    custom.textContent = t('自定义…');
    elBlock.appendChild(custom);
    elBlock.value = state.opts.block === '__custom' || blockList.some(function (b) { return b.id === state.opts.block; })
      ? state.opts.block : '';
    state.opts.block = elBlock.value;
    syncCustomInputs();
  }

  /* ---------- 收藏 ---------- */
  function toggleFav(p) {
    var willFav = !state.fav[p.id];
    if (willFav) state.fav[p.id] = true;
    else delete state.fav[p.id];
    store.set(LS.fav, state.fav);
    renderNav();
    if (state.cat === 'fav') render();
    else {
      var card = $$('.card', elGrid).filter(function (c) { return c.dataset.id === p.id; })[0];
      var btn = card && card.querySelector('[data-act="fav"]');
      if (btn) {
        btn.classList.toggle('is-on', willFav);
        btn.setAttribute('aria-pressed', willFav ? 'true' : 'false');
        btn.setAttribute('aria-label', t(willFav ? '取消收藏' : '收藏'));
        btn.title = t(willFav ? '取消收藏' : '收藏');
      }
    }
    toast(t(willFav ? '已加入收藏' : '已取消收藏'));
  }

  /* ---------- 自定义提示词 ---------- */
  function uniqueCustomId() {
    return 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  }

  /* 自建分类不能借用库内分类名：同名会让 buildModel 把条目塞进官方分类，
     看起来像可编辑的官方条目。与导入路径用的是同一条规则。 */
  function safeCustomCategory(name) {
    var n = typeof name === 'string' ? name.trim().slice(0, 40) : '';
    if (!n || n === '我的自定义') return '我的自定义';
    var clash = DATA.categories.some(function (x) {
      var en = DATA.en && DATA.en.categories && DATA.en.categories[x.id];
      return x.name === n || (en && en.name === n);
    });
    return clash ? '我的自定义' : n;
  }

  /* 已有自建分类名：新建时作为候选填进 datalist */
  function customCategoryNames() {
    var names = [];
    state.custom.forEach(function (c) {
      var n = typeof c.category === 'string' ? c.category.trim() : '';
      if (n && n !== '我的自定义' && names.indexOf(n) < 0) names.push(n);
    });
    return names;
  }

  function openCustom(p) {
    var editing = !!(p && p.custom);
    state.editing = editing ? p.id : null;
    $('#cm-title').value = editing ? p.title : '';
    $('#cm-body').value = editing ? p.content : '';
    $('#cm-short').value = editing ? (p.short || '') : '';
    $('#cm-note').value = editing ? (p.note || '') : '';
    $('#cm-category').value = editing ? (p.category || '') : '';
    var list = $('#cm-category-list');
    if (list) {
      list.innerHTML = customCategoryNames().map(function (n) {
        return '<option value="' + esc(n) + '"></option>';
      }).join('');
    }
    $('#modal-title').textContent = t(editing ? '编辑提示词' : '新建提示词');
    $('#cm-save').textContent = t(editing ? '保存修改' : '保存提示词');
    renderCustomList();
    if (elModal.hidden) openOverlay(elModal);
    setTimeout(function () { $('#cm-title').focus(); }, 30);
  }

  function saveCustom(ev) {
    if (ev) ev.preventDefault();
    var title = $('#cm-title').value.trim();
    var body = $('#cm-body').value.trim();
    if (!title || !body) { toast(t('请填写标题和提示词正文')); return; }
    var id = state.editing || uniqueCustomId();
    var short = $('#cm-short').value.trim();
    if (short === body) short = '';
    var current = state.editing ? state.custom.filter(function (c) { return c.id === state.editing; })[0] : null;
    var item = {
      id: id,
      title: title,
      content: body,
      /* 编辑保留原标签（导入的条目可能带标签，弹窗里没有标签编辑框，不能静默清掉） */
      tags: (current && Array.isArray(current.tags)) ? current.tags : [],
      short: short,
      note: $('#cm-note').value.trim(),
      category: safeCustomCategory($('#cm-category').value)
    };
    if (state.editing) state.custom = state.custom.map(function (c) { return c.id === state.editing ? item : c; });
    else state.custom.unshift(item);
    store.set(LS.custom, state.custom);
    state.editing = null;
    /* 本次保存优先于弹窗里此前导入留下的待定位项，关闭后只定位刚保存的条目。 */
    pendingRevealId = null;
    closeOverlay(elModal);
    rebuild();
    revealPrompt(item.id);
    toast(item.category === '我的自定义' ? t('已保存到「自定义」') : t('已保存到「{category}」', { category: item.category }));
  }

  function removeCustom(p) {
    if (!confirm(t('删除这条自定义提示词？此操作无法撤销。'))) return;
    state.custom = state.custom.filter(function (c) { return c.id !== p.id; });
    delete state.fav[p.id];
    delete state.used[p.id];
    store.set(LS.custom, state.custom);
    store.set(LS.fav, state.fav);
    store.set(LS.used, state.used);
    if (state.editing === p.id) state.editing = null;
    if (pendingRevealId === p.id) pendingRevealId = null;
    rebuild();
    if (!elModal.hidden) renderCustomList();
    toast(t('已删除'));
  }

  function renderCustomList() {
    var box = $('#cm-list');
    $('#cm-count').textContent = state.custom.length;
    if (!state.custom.length) {
      box.innerHTML = '<p class="empty-note">' + t('还没有自定义提示词，保存后会显示在这里。') + '</p>';
      return;
    }
    box.innerHTML = state.custom.map(function (c) {
      return '<div class="row"><span class="nm">' + esc(c.title) + '</span>' +
        '<button class="copy-btn" type="button" data-edit="' + esc(c.id) + '">' + t('编辑') + '</button>' +
        '<button class="copy-btn delete" type="button" data-del="' + esc(c.id) + '">' + t('删除') + '</button></div>';
    }).join('');
    $$('[data-edit]', box).forEach(function (b) {
      b.addEventListener('click', function () {
        var c = state.custom.filter(function (x) { return x.id === b.dataset.edit; })[0];
        if (c) openCustom(Object.assign({ custom: true }, c));
      });
    });
    $$('[data-del]', box).forEach(function (b) {
      b.addEventListener('click', function () {
        var c = state.custom.filter(function (x) { return x.id === b.dataset.del; })[0];
        if (c) removeCustom(c);
      });
    });
  }

  function exportCustom() {
    if (!state.custom.length) { toast(t('还没有自定义提示词')); return; }
    var payload = { version: 1, exported_at: new Date().toISOString(), custom: state.custom };
    downloadFile('prompt-library-custom-' + exportStamp() + '.json', JSON.stringify(payload, null, 2), 'application/json');
    toast(t('已导出 {n} 条自定义提示词', { n: state.custom.length }));
  }

  function exportCustomMd() {
    if (!state.custom.length) { toast(t('还没有自定义提示词')); return; }
    var list = state.custom.map(function (c) {
      return Object.assign({}, c, { catName: c.category || '我的自定义' });
    });
    downloadFile('prompt-library-custom-' + exportStamp() + '.md', promptsToMarkdown(list), 'text/markdown');
    toast(t('已导出 {n} 条自定义提示词', { n: list.length }));
  }

  /* ---------- 导入 ---------- */
  /* 把一条外部条目加进「自定义」。返回 'added' / 'duplicate' / 'invalid'。
     条目自带 id 且已被占用 → 'duplicate'（说明导入过或与现有条目冲突，跳过防翻倍）；
     与库内 id 冲突尤其要拦：buildModel 建索引时自定义会顶掉库内条目。 */
  function addCustomEntry(c, tag) {
    if (!c || typeof c.title !== 'string' || typeof c.content !== 'string' || !c.title.trim() || !c.content.trim()) return 'invalid';
    if (typeof c.id === 'string' && c.id &&
        (index[c.id] || state.custom.some(function (x) { return x.id === c.id; }))) return 'duplicate';
    var tags = Array.isArray(c.tags) ? c.tags : (typeof c.tags === 'string' ? c.tags.split(/[,，、]/) : []);
    /* 自建分类不能借用库内分类名：同名会让 buildModel 把条目塞进官方分类，
       看起来像可编辑的官方条目。「我的自定义」也不算自建分类（它是未分类条目的
       内部归属，只在「自定义」页出现），第三方文件带这个名时同样归入兜底。 */
    var category = safeCustomCategory(c.category);
    state.custom.push({
      id: (typeof c.id === 'string' && c.id) ? c.id : uniqueCustomId() + (tag || 'x').toString(36),
      title: c.title.trim().slice(0, 80), content: c.content,
      short: typeof c.short === 'string' ? c.short : '',
      tags: tags.filter(function (t) { return typeof t === 'string'; }).map(function (t) { return t.trim(); }).filter(Boolean).slice(0, 12),
      note: typeof c.note === 'string' ? c.note : '',
      category: category
    });
    return 'added';
  }

  /* 导入「自定义导出」格式的 JSON：只收进自定义条目，不动收藏。 */
  function importCustomJSON(data) {
    var added = 0, dup = 0;
    data.custom.forEach(function (c) {
      var r = addCustomEntry(c);
      if (r === 'added') added++;
      else if (r === 'duplicate') dup++;
    });
    if (!added) {
      toast(t(dup ? '这些条目已经导入过，没有新增' : '文件中没有可导入的有效条目'));
      return;
    }
    store.set(LS.custom, state.custom);
    rebuild();
    renderCustomList();
    revealPrompt(state.custom[state.custom.length - added].id);
    toast(t('已导入 {n} 条提示词', { n: added }) + (dup ? t('，跳过 {n} 条已存在的', { n: dup }) : ''));
  }

  /* 导入「收藏导出」格式的 JSON：id 在库内的恢复收藏（id 是稳定身份，标题可能已被库更新），
     库外的条目转入自定义并同时恢复收藏标记（它出自收藏导出，多半是自定义条目的收藏）；
     没有 id 但有标题正文的也收进自定义。 */
  function importFavJSON(data) {
    var arr = Array.isArray(data) ? data : data.prompts;
    var restored = 0, added = 0, dup = 0;
    arr.forEach(function (p, i) {
      if (!p || typeof p.title !== 'string' || !p.title.trim()) return;
      if (typeof p.id === 'string' && p.id && index[p.id]) {
        state.fav[p.id] = true;
        restored++;
      } else {
        var r = addCustomEntry(p, i);
        if (r === 'added') {
          added++;
          /* 没有 id 的条目也会生成新 id；恢复收藏要标记实际入库的那一条。 */
          state.fav[state.custom[state.custom.length - 1].id] = true;
        } else if (r === 'duplicate') {
          dup++;
        }
      }
    });
    if (!restored && !added) {
      toast(t(dup ? '这些条目已经导入过，没有新增' : '文件中没有可导入的有效条目'));
      return;
    }
    store.set(LS.fav, state.fav);
    if (added) store.set(LS.custom, state.custom);
    rebuild();
    renderCustomList();
    toast(t('已恢复 {restored} 条收藏，新增 {added} 条自定义', { restored: restored, added: added }) +
      (dup ? t('，跳过 {n} 条已存在的', { n: dup }) : ''));
  }

  function isShortTrailer(lines, index) {
    /* 简洁表达是导出条目里的末尾附加段。正文中间也可能原样出现
       「> 简洁表达：…」，后面还有正文时不能把它抽走。
       多行简洁表达紧接着写为 > 续行；只有这一小段连续引用行可以跳过。 */
    var continuation = true;
    for (var i = index + 1; i < lines.length; i++) {
      if (continuation && /^>\s?/.test(lines[i])) continue;
      continuation = false;
      if (/^##\s+/.test(lines[i])) return true;
      if (/^\s*$/.test(lines[i]) || /^---+\s*$/.test(lines[i])) continue;
      return false;
    }
    return true;
  }

  /* 解析本站导出的 Markdown（promptsToMarkdown 的格式）：
     每个 `## 标题` 是一条，元信息取「- 分类/标签/id/备注：」行，正文到
     `> 简洁表达：` 或下一个 `## ` / 文件头元信息为止，`---` 只作分隔。
     代码块内的 `##` 与元信息样式的行都是正文：与 build.py 一样做 fence 感知，
     否则正文带代码块的条目导出后再导入会被拆成两条。
     宽松兼容：没有元信息行也能只按标题 + 正文导入。 */
  function parseMarkdownPrompts(text) {
    var lines = text.split(/\r?\n/);
    var entries = [], cur = null;
    var inHeader = true;   /* 第一个条目标题之前的部分是文件头，直接跳过 */
    var fence = null;      /* 当前所在代码块的围栏标记（``` 或 ~~~） */
    var metadataDone = false, sawMetadata = false, readingShort = false;
    lines.forEach(function (line, lineIndex) {
      var fm = line.match(/^\s*(```|~~~)/);
      if (fm) {
        if (!fence) { fence = fm[1]; }
        else if (fm[1] === fence) { fence = null; }
      } else if (!fence && /^##\s+/.test(line)) {
        inHeader = false;
        if (cur && cur.title.trim() && cur.content.trim()) entries.push(cur);
        cur = { title: line.replace(/^##\s+/, '').trim(), category: '', tags: [], id: '', short: '', note: '', content: '' };
        metadataDone = false;
        sawMetadata = false;
        readingShort = false;
        return;
      }
      if (inHeader || !cur) return;
      if (fence) {   /* 代码块内：整行原样进正文，元信息与分隔线都不生效 */
        if (cur.content) cur.content += '\n';
        cur.content += line;
        return;
      }
      var m;
      /* 多行简洁表达的后续行仍以 > 开头，只能紧跟首行连续出现；
         遇到空行、分隔线或普通正文后立即结束，不能吞进后面的引用。 */
      if (readingShort) {
        if ((m = line.match(/^>\s?(.*)$/))) {
          cur.short += '\n' + m[1];
          return;
        }
        readingShort = false;
      }
      /* 导出文件在最后一行元信息后垫一个空行，这就是元信息区的明确终点。
         没有它时，正文第一行若恰好像「- 分类：…」也会被误当成元信息。 */
      if (!metadataDone && !cur.content && sawMetadata && /^\s*$/.test(line)) metadataDone = true;
      /* 分类、标签等元信息只可能位于正文之前。正文一旦开始，同形行都是原文，
         不能再静默改写分类、标签、id，或把这些行从正文里删掉。 */
      if (!metadataDone && !cur.content) {
        if ((m = line.match(/^[-*]\s*(分类|类别|Category)\s*[：:]\s*(.+)$/i))) {
          sawMetadata = true; cur.category = m[2].trim(); return;
        }
        if ((m = line.match(/^[-*]\s*(标签|Tags)\s*[：:]\s*(.+)$/i))) {
          sawMetadata = true;
          cur.tags = m[2].split(/[、,，]/).map(function (tag) { return tag.trim(); }).filter(Boolean); return;
        }
        if ((m = line.match(/^[-*]\s*id\s*[：:]\s*(\S+)\s*$/i))) {
          sawMetadata = true; cur.id = m[1]; return;
        }
        if ((m = line.match(/^[-*]\s*(备注|Note)\s*[：:]\s*(.+)$/i))) {
          sawMetadata = true; cur.note = m[2].trim(); return;
        }
      }
      if (cur.content && /^>\s*(简洁表达|Short version)\s*[：:]/i.test(line) && isShortTrailer(lines, lineIndex)) {
        cur.short = line.replace(/^>\s*(简洁表达|Short version)\s*[：:]\s*/i, '').trim();
        readingShort = true;
        return;
      }
      /* 「---」在导出格式里只作条目分隔：前一行是空行（元信息或正文之后垫的空行）。
         正文行紧贴的「---」（前一行非空）属于内容本身，不能丢。 */
      if (/^---+\s*$/.test(line)) {
        if (!cur.content || /\n$/.test(cur.content)) return;
      }
      if (cur.content) cur.content += '\n';
      cur.content += line;
    });
    if (cur && cur.title.trim() && cur.content.trim()) entries.push(cur);
    return entries.map(function (e) {
      e.content = e.content.trim();
      e.short = e.short.trim();
      return e;
    }).filter(function (e) { return !!e.content; });
  }

  function importMarkdown(text, mode, name) {
    var added = 0, restored = 0, dup = 0;
    var entries = parseMarkdownPrompts(text);
    if (!entries.length) {
      toast(t('导入失败：{name} 里没有可识别的提示词条目', { name: name }));
      return;
    }
    /* 收藏导出与自定义导出的 Markdown 长一个样（都是 promptsToMarkdown 的格式），
       差别只在条目出处：含库内 id 的是收藏导出。custom 模式遇到库内 id 的条目，
       说明拿错了文件——库内条目收进自定义会顶掉官方条目，直接拦下提示换按钮。 */
    if (mode === 'custom' && entries.some(function (e) { return e.id && isLibraryId(e.id); })) {
      toast(t('这像是收藏导出文件，请用「导入收藏」按钮'));
      return;
    }
    entries.forEach(function (e, i) {
      /* fav 模式：id 在库内就按收藏恢复（id 是稳定身份）；其余收进自定义。
         custom 模式：一律收进自定义，不设收藏标记（能走到这里说明没有库内 id）。 */
      if (mode !== 'custom' && e.id && index[e.id]) {
        state.fav[e.id] = true;
        restored++;
      } else {
        var r = addCustomEntry(e, i);
        if (r === 'added') {
          added++;
          /* 与 JSON 收藏导入一致：只有「导入收藏」里的库外条目保留收藏；
             「导入自定义」只是新增条目，不能顺手把它标成收藏。 */
          if (mode !== 'custom') state.fav[state.custom[state.custom.length - 1].id] = true;
        } else if (r === 'duplicate') dup++;
      }
    });
    if (!restored && !added) {
      toast(t(dup ? '这些条目已经导入过，没有新增' : '文件中没有可识别的提示词条目'));
      return;
    }
    if (mode !== 'custom') store.set(LS.fav, state.fav);
    if (added) store.set(LS.custom, state.custom);
    rebuild();
    renderCustomList();
    if (mode === 'custom' && added) {
      /* 与 JSON 自定义导入一致：弹窗仍开着时先记待定位项，关闭后落到第一条新导入的卡片。 */
      revealPrompt(state.custom[state.custom.length - added].id);
    }
    if (mode === 'custom') {
      toast(t('已导入 {n} 条提示词', { n: added }) + (dup ? t('，跳过 {n} 条已存在的', { n: dup }) : ''));
    } else {
      toast(t('已恢复 {restored} 条收藏，新增 {added} 条自定义', { restored: restored, added: added }) +
        (dup ? t('，跳过 {n} 条已存在的', { n: dup }) : ''));
    }
  }

  /* 统一导入入口：按扩展名与内容分发到收藏或自定义。
     mode 是 'fav' 或 'custom'，两个导入按钮各认各的文件，选错会提示而不是静默混收。 */
  function importAny(file, mode) {
    if (file.size > 5 * 1024 * 1024) { toast(t('文件超过 5 MB，请选择较小的文件')); return; }
    var isJSON = /\.json$/i.test(file.name) || file.type === 'application/json';
    var reader = new FileReader();
    reader.onload = function () {
      /* 去掉 BOM：Windows 上不少编辑器保存的文本带 BOM，
         JSON.parse 会直接抛错，Markdown 也会多出一个看不见的首字符 */
      var text = String(reader.result || '').replace(/^\uFEFF/, '');
      var data = null;
      if (!isJSON) {
        /* 扩展名不是 .json 时按内容判断：能整体解析成 JSON 就按 JSON 走 */
        try {
          var maybe = JSON.parse(text);
          if (isRecord(maybe) || Array.isArray(maybe)) data = maybe;
        } catch (e) { /* 不是 JSON，按 Markdown 处理 */ }
      } else {
        try { data = JSON.parse(text); }
        catch (e) { toast(t('导入失败：文件格式不正确')); return; }
      }
      if (data !== null) { routeJSON(data, mode, file.name); return; }
      importMarkdown(text, mode, file.name);
    };
    reader.onerror = function () { toast(t('读取文件失败，请重试')); };
    reader.readAsText(file);
  }

  /* JSON 数据按 mode 分发：形状与按钮不匹配时明确提示选错文件。
     收藏导出（{prompts: [...]} 或裸数组）在 custom 模式下不收，
     自定义导出（{custom: [...]})在 fav 模式下提示走「导入自定义」。 */
  function routeJSON(data, mode, name) {
    var isFavShape = Array.isArray(data) || (isRecord(data) && Array.isArray(data.prompts));
    var isCustomShape = isRecord(data) && Array.isArray(data.custom);
    if (mode === 'custom') {
      if (isFavShape) { toast(t('这是收藏导出文件，请用「导入收藏」按钮')); return; }
      if (!isCustomShape) { toast(t('导入失败：{name} 不是自定义导出文件', { name: name })); return; }
      importCustomJSON(data);
    } else {
      if (isCustomShape) { toast(t('这是自定义导出文件，请用「导入自定义」按钮')); return; }
      if (!isFavShape) { toast(t('导入失败：{name} 不是收藏导出文件', { name: name })); return; }
      importFavJSON(data);
    }
  }

  function rebuild() {
    buildModel();
    renderNav();
    resetView();
    render();
  }

  /* 定位到某一条提示词：切到它所在的分类、清掉搜索，并把渲染上限扩到足够显示它。
     分享链接与「保存后自动定位」都走这里，避免目标落在分页之外而找不到卡片。 */
  function revealPrompt(id) {
    var prompt = index[id];
    if (!prompt) return false;
    /* 弹窗里导入时背景仍是 inert：此时滚动/聚焦卡片既看不见，也会破坏弹窗隔离。
       先记唯一一个待定位项，关闭弹窗后再执行；连续导入以最后一次为准。 */
    if ($$('.modal').some(function (m) { return !m.hidden; })) {
      pendingRevealId = id;
      return true;
    }
    clearTimeout(searchTimer);
    state.q = '';
    elSearch.value = '';
    elSearchClear.hidden = true;
    if (elSearchKbd) elSearchKbd.hidden = false;
    /* 未分类的自定义条目（internal 兜底分类）落在「自定义」页显示 */
    var targetCat = prompt.catId && prompt.catId !== 'all' && prompt.catId !== 'fav'
      ? (getCategory(prompt.catId) && getCategory(prompt.catId).internal ? 'custom' : prompt.catId)
      : (prompt.custom ? 'custom' : 'all');
    if (targetCat !== 'all') state.cat = targetCat;
    resetView();
    var position = filtered().findIndex(function (p) { return p.id === id; });
    if (position < 0) return false;
    if (position >= state.limit) state.limit = position + 1;
    render();
    var cards = $$('.card', elGrid);
    var card = cards.filter(function (c) { return c.dataset.id === id; })[0];
    if (!card) return false;
    setKbdCard(card);
    /* 平滑滚动途中不能触发自动展开（哨兵一命中就重绘，目标卡片被销毁，
       滚动会停在过期坐标上），所以加跳转锁；锁到滚动停下来才放开。 */
    lockJump();
    card.scrollIntoView({ block: 'center', behavior: preferredScrollBehavior() });
    card.focus({ preventScroll: true });
    return true;
  }

  /* ---------- 弹层与焦点 ---------- */
  /* 弹层（或手机端抽屉）打开时把背景移出焦点顺序与读屏导航，关闭后恢复。
     两者的处理范围不同：弹层盖住整页，抽屉只盖住侧栏那一侧，
     所以抽屉打开时只屏蔽顶栏、引导区与内容区，侧栏本身与遮罩仍可交互。 */
  function syncBackgroundInert() {
    var modalOpen = $$('.modal').some(function (m) { return !m.hidden; });
    var drawerOpen = elSidebar.classList.contains('is-open');
    /* 弹层盖住整页：回顶按钮与跳转链接是 body 的直属子元素，
       不在这几个选择器里，不设 inert 的话它们照样能点、能被 Tab 到。 */
    var blocked = modalOpen ? ['.topbar', '.hero', '.layout', '#btn-top', '.skip-link']
      : drawerOpen ? ['.topbar', '.hero', '.main']
      : [];
    ['.topbar', '.hero', '.layout', '.main', '#btn-top', '.skip-link'].forEach(function (sel) {
      var el = $(sel);
      if (el) el.inert = blocked.indexOf(sel) >= 0;
    });
  }

  function openOverlay(m) {
    lastFocused = document.activeElement;
    m.hidden = false;
    document.body.style.overflow = 'hidden';
    syncBackgroundInert();
    setTimeout(function () {
      var close = m.querySelector('.modal-head [data-close]');
      if (close && m !== elModal) close.focus();
    }, 30);
  }

  function closeOverlay(m) {
    if (!m || m.hidden) return;
    var revealId = pendingRevealId;
    pendingRevealId = null;
    m.hidden = true;
    if (m === elModal) state.editing = null;
    var anotherOpen = $$('.modal').some(function (x) { return !x.hidden; });
    if (!anotherOpen && !elSidebar.classList.contains('is-open')) document.body.style.overflow = '';
    syncBackgroundInert();
    if (lastFocused && lastFocused.isConnected && lastFocused.focus) lastFocused.focus();
    lastFocused = null;
    /* 先恢复背景可交互状态，再定位弹窗内导入的条目；焦点最终落在目标卡片上。 */
    if (revealId && !anotherOpen && !elSidebar.classList.contains('is-open')) revealPrompt(revealId);
  }

  function trapFocus(e, container) {
    if (e.key !== 'Tab') return;
    var f = $$('a[href],button:not([disabled]),input:not([type="hidden"]),select,textarea,[tabindex]:not([tabindex="-1"])', container)
      .filter(function (x) { return x.offsetParent !== null && !x.disabled; });
    if (!f.length) return;
    var first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* ---------- 主题与语言 ---------- */
  function applyTheme(theme, persist) {
    if (theme !== 'light' && theme !== 'dark') theme = 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    if (persist) store.set(LS.theme, theme);
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'light' ? '#f5f6f8' : '#111111');
    var button = $('#btn-theme');
    /* 主题按钮的文案走界面字典：三段拼起来，中文是「切换到深色主题」，
       英文是 'Switch to ' + 'dark' + ' theme'。原来这里写死两种语言，
       字典里的对应条目就成了没人用的死键。 */
    var label = t('切换到') + t(theme === 'light' ? '深色' : '浅色') + t('主题');
    button.setAttribute('aria-label', label);
    button.title = label;
    button.querySelector('use').setAttribute('href', theme === 'light' ? '#i-moon' : '#i-sun');
  }

  function applyStaticLanguage() {
    $$('[data-i18n]').forEach(function (node) {
      node.textContent = t(node.getAttribute('data-i18n'));
    });
    ['placeholder', 'aria-label', 'title'].forEach(function (attr) {
      $$('[data-i18n-' + attr + ']').forEach(function (node) {
        node.setAttribute(attr, t(node.getAttribute('data-i18n-' + attr)));
      });
    });
    $$('[data-i18n-desc]').forEach(function (node) {
      node.setAttribute('data-desc', t(node.getAttribute('data-i18n-desc')));
    });

    var titleKey = 'GUAN 提示词库 · 按场景分类的常用提示词';
    document.title = t(titleKey);
    var descriptions = {
      'meta[name="description"]': '个人整理的提示词库：从工程实现到学术写作，反复验证过的提示词按场景分类，支持多关键词搜索、一键复制、收藏与自定义，无需登录。',
      'meta[property="og:title"]': titleKey,
      'meta[property="og:description"]': '从工程实现到学术写作，反复验证过的提示词按场景分类，搜索即取、复制即用，无需登录。',
      'meta[property="og:image:alt"]': 'GUAN 提示词库 · 常用智能体提示词分类检索',
      'meta[name="twitter:title"]': titleKey,
      'meta[name="twitter:description"]': '从工程实现到学术写作，反复验证过的提示词按场景分类，搜索即取、复制即用，无需登录。'
    };
    Object.keys(descriptions).forEach(function (selector) {
      var node = $(selector);
      if (node) node.setAttribute('content', t(descriptions[selector]));
    });
    var locale = $('meta[property="og:locale"]');
    if (locale) locale.setAttribute('content', state.lang === 'en' ? 'en_US' : 'zh_CN');
    var keywords = $('meta[name="keywords"]');
    if (keywords) keywords.setAttribute('content', state.lang === 'en'
      ? 'prompt,prompt library,AI,agents,Claude,categories,copy'
      : '提示词,prompt,AI,智能体,Claude,分类,复制');
  }

  function applyLanguage(lang, persist) {
    state.lang = lang === 'en' ? 'en' : 'zh';
    if (persist) store.set(LS.lang, state.lang);
    document.documentElement.setAttribute('lang', state.lang === 'en' ? 'en' : 'zh-Hans');
    applyStaticLanguage();

    var button = $('#btn-language');
    var action = state.lang === 'en' ? '中文: ' + t('切换到中文') : 'EN: Switch to English';
    button.textContent = state.lang === 'en' ? '中文' : 'EN';
    button.setAttribute('lang', state.lang === 'en' ? 'zh-Hans' : 'en');
    button.setAttribute('aria-label', action);
    button.title = action;

    applyTheme(document.documentElement.getAttribute('data-theme'), false);
    buildModel();
    renderNav();
    render(true);
    renderBlockOptions();
    updateOptionSummary();
    if (!elModal.hidden) {
      var editing = !!state.editing;
      $('#modal-title').textContent = t(editing ? '编辑提示词' : '新建提示词');
      $('#cm-save').textContent = t(editing ? '保存修改' : '保存提示词');
      renderCustomList();
    }
  }

  /* ---------- 工具 ---------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function escapeRegExp(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  function hl(text, terms) {
    text = String(text == null ? '' : text);
    if (!terms.length) return esc(text);
    var pattern = terms.slice().sort(function (a, b) { return b.length - a.length; }).map(escapeRegExp).join('|');
    if (!pattern) return esc(text);
    var re = new RegExp(pattern, 'gi');
    var out = '', last = 0, match;
    while ((match = re.exec(text)) !== null) {
      out += esc(text.slice(last, match.index)) + '<mark>' + esc(match[0]) + '</mark>';
      last = match.index + match[0].length;
      if (match[0].length === 0) re.lastIndex++;
    }
    return out + esc(text.slice(last));
  }

  function toast(msg) {
    elToast.querySelector('span').textContent = msg;
    elToast.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { elToast.classList.remove('is-on'); }, 2000);
  }

  /* ---------- 移动端分类抽屉 ---------- */
  /* 回顶按钮与移动端抽屉互斥：抽屉打开时按钮悬在遮罩上方，点了会滚顶而抽屉不动。
     scroll 监听与抽屉开合两处都要刷新，所以定义在模块级。 */
  function syncTopBtn() {
    var show = window.scrollY > 700 && !elSidebar.classList.contains('is-open');
    elTop.hidden = !show;
    elTop.classList.toggle('is-on', show);
  }

  function syncSidebarAccessibility() {
    var mobile = window.innerWidth <= 1180;
    var open = mobile && elSidebar.classList.contains('is-open');
    elSidebar.inert = mobile && !open;
    if (mobile && !open) elSidebar.setAttribute('aria-hidden', 'true');
    else elSidebar.removeAttribute('aria-hidden');
    if (open) {
      elSidebar.setAttribute('role', 'dialog');
      elSidebar.setAttribute('aria-modal', 'true');
    } else {
      elSidebar.removeAttribute('role');
      elSidebar.removeAttribute('aria-modal');
    }
    /* 抽屉是模态层：背景（顶栏、引导区、内容区）同步移出焦点顺序与读屏导航 */
    syncBackgroundInert();
  }

  function openSidebar() {
    elSidebar.classList.add('is-open');
    elBackdrop.hidden = false;
    document.body.style.overflow = 'hidden';
    $('#btn-mobile-menu').setAttribute('aria-expanded', 'true');
    syncSidebarAccessibility();
    syncTopBtn();
    setTimeout(function () { $('#btn-sidebar-close').focus(); }, 30);
  }

  function closeSidebar(restoreFocus) {
    var wasOpen = elSidebar.classList.contains('is-open');
    elSidebar.classList.remove('is-open');
    elBackdrop.hidden = true;
    $('#btn-mobile-menu').setAttribute('aria-expanded', 'false');
    if (wasOpen && !$$('.modal').some(function (m) { return !m.hidden; })) document.body.style.overflow = '';
    /* 先解除顶栏 inert，再还焦点；顺序反过来时浏览器会拒绝聚焦菜单按钮。 */
    syncSidebarAccessibility();
    syncTopBtn();
    if (wasOpen && restoreFocus !== false) $('#btn-mobile-menu').focus();
  }

  /* ---------- 键盘 ---------- */
  /* 卡片高亮（is-kbd）始终跟随真实焦点：只有当前持有焦点的卡片才算「选中」。
     点击空白处后焦点离开网格，高亮随之消失，不会有一张卡片一直保持选中态。 */
  function setKbdCard(card) {
    var cards = $$('.card', elGrid);
    state.focusIndex = card ? cards.indexOf(card) : -1;
    state.focusId = card ? card.dataset.id : null;
    cards.forEach(function (c) { c.classList.toggle('is-kbd', c === card); });
  }

  /* 依据当前焦点重新同步高亮：焦点落在卡片上就高亮该卡片，
     焦点在卡片之外（含点空白处）就清掉高亮。 */
  function syncKbdCard() {
    var active = document.activeElement;
    var card = active && active.closest ? active.closest('.card') : null;
    if (!card || !elGrid.contains(card)) card = null;
    setKbdCard(card);
  }

  function focusCard(card) {
    var cards = $$('.card', elGrid);
    if (cards.indexOf(card) < 0) return;
    setKbdCard(card);
    card.focus({ preventScroll: true });
    card.scrollIntoView({ block: 'nearest', behavior: preferredScrollBehavior() });
  }

  function moveFocus(delta) {
    var cards = $$('.card', elGrid);
    if (!cards.length) return;
    var cur = focusedCard();
    var pos = cur ? cards.indexOf(cur) : state.focusIndex;
    if (pos < 0) pos = delta > 0 ? 0 : cards.length - 1;
    else pos = (pos + delta + cards.length) % cards.length;
    focusCard(cards[pos]);
  }

  /* 网格用 CSS Grid 排布，DOM 顺序与视觉行一致（先左右排满一行，再往下）。
     卡片高度不等，同一视觉行的卡片顶端对齐，所以按「顶端坐标」分行。
     鼠标停在某张卡上时它会整体上移 2px，顶端坐标不再与其他卡齐平——
     直接按坐标相等分组会把悬停的那张单拆成一行，方向键于是跳错行。
     所以留一点容差，把仍在同一视觉行的卡片算作一行。 */
  var ROW_TOLERANCE = 8;
  function gridRows(grid) {
    var rows = [];
    $$('.card', grid).forEach(function (c) {
      var top = Math.round(c.getBoundingClientRect().top);
      var row = null;
      for (var i = 0; i < rows.length; i++) {
        if (Math.abs(rows[i].top - top) <= ROW_TOLERANCE) { row = rows[i]; break; }
      }
      if (!row) { row = { top: top, items: [] }; rows.push(row); }
      row.items.push(c);
    });
    rows.sort(function (a, b) { return a.top - b.top; });
    rows.forEach(function (r) {
      r.items.sort(function (a, b) {
        return a.getBoundingClientRect().left - b.getBoundingClientRect().left;
      });
    });
    return rows;
  }

  /* 上下方向键：跳到相邻视觉行里横向位置最接近的那张卡 */
  function moveFocusRow(dir) {
    var cards = $$('.card', elGrid);
    if (!cards.length) return;
    var cur = focusedCard();
    if (!cur) { focusCard(cards[0]); return; }

    var grid = cur.closest('.grid') || elGrid;
    var rows = gridRows(grid);
    if (rows.length < 2) return;

    var ri = -1;
    rows.forEach(function (r, i) { if (r.items.indexOf(cur) >= 0) ri = i; });
    if (ri < 0) { focusCard(cur); return; }

    var target = rows[ri + dir];
    if (!target) return;                       /* 已到最上/最下一行，保持不动 */

    var curLeft = cur.getBoundingClientRect().left;
    var best = null, bestDist = Infinity;
    target.items.forEach(function (c) {
      var d = Math.abs(c.getBoundingClientRect().left - curLeft);
      if (d < bestDist) { bestDist = d; best = c; }
    });
    if (best) focusCard(best);
  }

  /* 左右方向键：在当前视觉行内左右移动；单列布局（手机）时按整体顺序前后走 */
  function moveFocusColumn(dir) {
    var cards = $$('.card', elGrid);
    if (!cards.length) return;
    var cur = focusedCard();
    if (!cur) { focusCard(cards[0]); return; }   /* 尚未选中任何卡片：从第一张进入 */

    var grid = cur.closest('.grid') || elGrid;
    var rows = gridRows(grid);
    if (rows.length < 1) return;

    var row = null;
    rows.forEach(function (r) { if (r.items.indexOf(cur) >= 0) row = r; });
    if (!row) { focusCard(cur); return; }

    if (row.items.length < 2) {                 /* 单列：上下即左右 */
      moveFocus(dir);
      return;
    }

    var ci = row.items.indexOf(cur);
    var target = row.items[ci + dir];
    if (!target) return;                       /* 已到本行最左/最右，保持不动 */
    focusCard(target);
  }

  function focusedCard() {
    var active = document.activeElement;
    if (active && active.closest) {
      var holder = active.closest('.card');
      if (holder && elGrid.contains(holder)) return holder;
    }
    var cards = $$('.card', elGrid);
    return state.focusIndex >= 0 && cards[state.focusIndex] ? cards[state.focusIndex] : null;
  }

  function clearSearch() {
    clearTimeout(searchTimer);
    setSearch('', false);
  }

  /* ---------- 事件绑定 ---------- */
  function bind() {
    elSearch.addEventListener('input', function () {
      state.q = elSearch.value;
      elSearchClear.hidden = !state.q;
      if (elSearchKbd) elSearchKbd.hidden = !!state.q;
      /* 搜索默认全局：一开始输入就退出分类/收藏/自定义范围，在全部条目里搜；
         清空搜索后停在「全部提示词」，需要再看某个分类时点侧栏即可。 */
      if (state.q.trim()) state.cat = 'all';
      resetView();
      clearTimeout(searchTimer);
      searchTimer = setTimeout(function () {
        render();
        ensureContentVisible();
      }, 120);
    });
    elSearchClear.addEventListener('click', function () { clearSearch(); elSearch.focus(); });
    $('#empty-reset').addEventListener('click', function () {
      state.cat = 'all';
      clearSearch();
    });

    elNav.addEventListener('click', function (ev) {
      var button = ev.target.closest('[data-cat]');
      if (button) chooseCategory(button.dataset.cat);
    });
    $('#btn-fav').addEventListener('click', function () {
      chooseCategory(state.cat === 'fav' ? 'all' : 'fav');
    });

    elFilterBar.addEventListener('click', function (ev) {
      var btn = ev.target.closest('[data-clear]');
      if (btn) clearFilter(btn.dataset.clear);
    });

    elTop.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: preferredScrollBehavior() });
    });
    /* 滚动接近文档底部的兜底推进：快速滚动/拖动滚动条时，中间的哨兵可能在
       预载线里停留过短被跳过、随后落在视口上方（rootMargin 只向下）而再无机会
       触发——这时靠「距底不足 4 屏」直接推进，滚动流不会卡住。
       scroll 事件是边沿驱动（瞬移只发一次，可能恰好落在哨兵回调的节流窗口里
       被丢弃），所以触发后短轮询几次把推进续上。 */
    var bottomTimer = 0;
    function nearBottom(screens) {
      var left = document.body.scrollHeight - window.innerHeight - window.scrollY;
      return left <= window.innerHeight * (screens || 4);
    }
    function bottomFallback() {
      state.limit += PAGE_SIZE;
      render(true);   /* 追加内容，保留键盘用户正在看的那张卡 */
    }
    function syncScroll() {
      syncTopBtn();
      /* 分区跳转的平滑滚动途中：不推进内容（会重绘、毁掉目标节点），
         滚动停下来后自动展开才恢复 */
      if (jumpLock) {
        unlockJumpOnIdle();
        clearInterval(bottomTimer);
        return;
      }
      if (elLoadMore.hidden || elSidebar.classList.contains('is-open') || !nearBottom()) {
        clearInterval(bottomTimer);
        return;
      }
      bottomFallback();
      var tries = 0;
      clearInterval(bottomTimer);
      bottomTimer = setInterval(function () {
        /* 每轮都重新量一次「距底」：推进会让文档变长、用户离新内容更远，
           这时若还连着补，用户会看到页面凭空长出几百张卡片（一次滚到底
           曾补到 216 张、页面长到四万多像素）。真正需要续推时，哨兵会在
           用户滚到新内容时接手，这里只在「仍贴着底」时再补一批。 */
        if (jumpLock || ++tries > 8 || elLoadMore.hidden ||
            elSidebar.classList.contains('is-open') || !nearBottom(1)) {
          clearInterval(bottomTimer);
          return;
        }
        bottomFallback();
      }, 140);
    }
    window.addEventListener('scroll', syncScroll, { passive: true });

    /* 卡片高亮跟随真实焦点：焦点进到某张卡片就选中它，焦点离开网格（例如点击空白区域）
       就取消选中，不会有一张卡片一直保持高亮。
       focusout 延到下一轮再读 activeElement，避免卡片被重绘移除时误判。 */
    elGrid.addEventListener('focusin', function () { syncKbdCard(); });
    elGrid.addEventListener('focusout', function () {
      setTimeout(syncKbdCard, 0);
    });

    elGrid.addEventListener('click', function (ev) {
      /* 页首目录的分类 chips：点进对应分类页（与侧栏点分类同一路径） */
      var chip = ev.target.closest('.map-chip[data-cat]');
      if (chip) { chooseCategory(chip.dataset.cat); return; }
      /* 「换一批」：换一副随机顺序，卡片整体重排 */
      var re = ev.target.closest('[data-act="reshuffle"]');
      if (re) {
        browseSeed = (Math.random() * 0xffffffff) >>> 0;
        resetView();
        render();
        scrollToRandomBar();
        return;
      }
      var card = ev.target.closest('.card');
      if (!card) return;
      var p = index[card.dataset.id];
      if (!p) return;
      var tag = ev.target.closest('[data-tag]');
      if (tag) {
        setSearch(tag.dataset.tag, true);
        scrollToContent();
        return;
      }
      var btn = ev.target.closest('[data-act]');
      if (!btn) return;
      var act = btn.dataset.act;
      if (act === 'copy') doCopy(p, card, 'full');
      else if (act === 'copy-short') doCopy(p, card, 'short');
      else if (act === 'fav') toggleFav(p);
      else if (act === 'share') sharePrompt(p);
      else if (act === 'edit') openCustom(p);
      else if (act === 'del') removeCustom(p);
    });

    $('#btn-used-sort').addEventListener('click', function () {
      state.usedSort = !state.usedSort;
      store.set(LS.sort, state.usedSort ? 'used' : 'default');
      resetView();
      render();
      ensureContentVisible();
    });

    $('#btn-load-more').addEventListener('click', function () {
      state.limit += PAGE_SIZE;
      render();
    });

    $('#btn-copy-options').addEventListener('click', function () {
      var opening = elCopyPanel.hidden;
      elCopyPanel.hidden = !opening;
      $('#btn-copy-options').setAttribute('aria-expanded', opening ? 'true' : 'false');
      if (opening && !elExportPanel.hidden) {
        elExportPanel.hidden = true;
        $('#btn-export').setAttribute('aria-expanded', 'false');
      }
    });
    elPrefix.addEventListener('change', function () {
      saveOptions();
      syncCustomInputs();
      if (state.opts.prefix === '__custom') elPrefixCustom.focus();
    });
    elBlock.addEventListener('change', function () {
      saveOptions();
      syncCustomInputs();
      if (state.opts.block === '__custom') elBlockCustom.focus();
    });
    elPrefixCustom.addEventListener('input', saveOptions);
    elBlockCustom.addEventListener('input', saveOptions);
    $('#btn-reset-options').addEventListener('click', function () {
      elPrefix.value = '';
      elBlock.value = '';
      elPrefixCustom.value = '';
      elBlockCustom.value = '';
      state.opts.prefix = '';
      state.opts.block = '';
      state.opts.customPrefix = '';
      state.opts.customBlock = '';
      saveOptions();
      syncCustomInputs();
      toast(t('已恢复默认复制方式'));
    });

    /* 导出面板与复制设置面板互斥，避免两个面板同时占据注意力 */
    $('#btn-export').addEventListener('click', function () {
      var opening = elExportPanel.hidden;
      elExportPanel.hidden = !opening;
      $('#btn-export').setAttribute('aria-expanded', opening ? 'true' : 'false');
      if (opening) {
        if (!elCopyPanel.hidden) {
          elCopyPanel.hidden = true;
          $('#btn-copy-options').setAttribute('aria-expanded', 'false');
        }
        updateExportNote();
      }
    });
    $('#btn-export-close').addEventListener('click', function () {
      elExportPanel.hidden = true;
      $('#btn-export').setAttribute('aria-expanded', 'false');
      $('#btn-export').focus();
    });
    $('#btn-export-fav-md').addEventListener('click', function () { exportFav('md'); });
    $('#btn-export-fav-json').addEventListener('click', function () { exportFav('json'); });
    $('#btn-export-custom-md').addEventListener('click', function () { exportCustomMd(); });
    $('#btn-export-custom').addEventListener('click', function () { exportCustom(); });
    $('#btn-import-fav').addEventListener('click', function () { $('#import-file-fav').click(); });
    $('#btn-import-custom').addEventListener('click', function () { $('#import-file-custom').click(); });
    $('#import-file-fav').addEventListener('change', function (e) {
      if (e.target.files && e.target.files[0]) importAny(e.target.files[0], 'fav');
      e.target.value = '';
    });
    $('#import-file-custom').addEventListener('change', function (e) {
      if (e.target.files && e.target.files[0]) importAny(e.target.files[0], 'custom');
      e.target.value = '';
    });

    $('#btn-custom').addEventListener('click', function () { openCustom(null); });
    $('#custom-form').addEventListener('submit', saveCustom);
    $('#cm-export').addEventListener('click', exportCustom);
    $('#cm-import').addEventListener('click', function () { $('#cm-file').click(); });
    $('#cm-file').addEventListener('change', function (e) {
      if (e.target.files && e.target.files[0]) importAny(e.target.files[0], 'custom');
      e.target.value = '';
    });

    $('#btn-language').addEventListener('click', function () {
      applyLanguage(state.lang === 'en' ? 'zh' : 'en', true);
    });
    $('#btn-theme').addEventListener('click', function () {
      applyTheme(document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light', true);
    });
    $('#btn-help').addEventListener('click', function () { openOverlay(elHelp); });
    $('#btn-mobile-menu').addEventListener('click', function () {
      if (elSidebar.classList.contains('is-open')) closeSidebar(); else openSidebar();
    });
    $('#btn-sidebar-close').addEventListener('click', function () { closeSidebar(); });
    elBackdrop.addEventListener('click', function () { closeSidebar(); });

    $$('[data-close]').forEach(function (b) {
      b.addEventListener('click', function () { closeOverlay(b.closest('.modal')); });
    });
    $$('.modal').forEach(function (m) {
      m.addEventListener('keydown', function (e) { trapFocus(e, m); });
    });
    elSidebar.addEventListener('keydown', function (e) {
      if (elSidebar.classList.contains('is-open')) trapFocus(e, elSidebar);
    });

    document.addEventListener('keydown', function (e) {
      var openModals = $$('.modal').filter(function (m) { return !m.hidden; });
      var openModal = openModals[openModals.length - 1];
      if (openModal) {
        if (e.key === 'Escape') {
          e.preventDefault();
          closeOverlay(openModal);
        }
        return;
      }
      /* 移动端抽屉是模态层：除 Esc（用于关闭抽屉）外不响应全局快捷键，
         免得焦点与复制/收藏动作落到抽屉背后看不见的卡片上。 */
      if (elSidebar.classList.contains('is-open') && e.key !== 'Escape') return;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        elSearch.focus();
        elSearch.select();
        return;
      }
      /* 其余带修饰键的组合（Ctrl+C / Ctrl+F 等）一律交还浏览器，
         避免劫持原生复制与查找。Shift 不在此列：? 本身就是 Shift+/。 */
      if (e.ctrlKey || e.metaKey || e.altKey) return;

      if (e.key === 'Escape') {
        if (elSidebar.classList.contains('is-open')) { closeSidebar(); return; }
        if (!elCopyPanel.hidden) {
          elCopyPanel.hidden = true;
          $('#btn-copy-options').setAttribute('aria-expanded', 'false');
          $('#btn-copy-options').focus();
          return;
        }
        if (!elExportPanel.hidden) {
          elExportPanel.hidden = true;
          $('#btn-export').setAttribute('aria-expanded', 'false');
          $('#btn-export').focus();
          return;
        }
        if (state.q || document.activeElement === elSearch) { clearSearch(); elSearch.blur(); }
        return;
      }

      var tag = (e.target.tagName || '').toLowerCase();
      var typing = tag === 'input' || tag === 'textarea' || tag === 'select' || e.target.isContentEditable;
      if (typing) return;
      var interactive = typing || tag === 'button' || tag === 'a';

      if (e.key === '/') { e.preventDefault(); elSearch.focus(); elSearch.select(); return; }
      if (e.key === '?') { e.preventDefault(); openOverlay(elHelp); return; }
      if (e.key === 'ArrowDown') { e.preventDefault(); moveFocusRow(1); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); moveFocusRow(-1); return; }
      if (e.key === 'ArrowRight') { e.preventDefault(); moveFocusColumn(1); return; }
      if (e.key === 'ArrowLeft') { e.preventDefault(); moveFocusColumn(-1); return; }
      if (interactive) return;
      var card = focusedCard();
      if (!card) return;
      var p = index[card.dataset.id];
      if (!p) return;
      if (e.key.toLowerCase() === 'c') { e.preventDefault(); doCopy(p, card, 'short'); }
      else if (e.key.toLowerCase() === 'f') { e.preventDefault(); toggleFav(p); }
    });

    window.addEventListener('resize', function () {
      if (window.innerWidth > 1180 && elSidebar.classList.contains('is-open')) closeSidebar(false);
      else { syncSidebarAccessibility(); syncTopBtn(); }
    });
    window.addEventListener('hashchange', openHash);
  }

  function openHash() {
    var hash = location.hash.slice(1);
    if (!hash) return;
    var id;
    try { id = decodeURIComponent(hash); } catch (e) { return; }
    /* 跳转主内容的页内锚点不是提示词分享链接；交给浏览器原生定位，
       否则按「跳到主要内容」后还会弹出一条链接失效的错误提示。 */
    if (id === 'main') return;
    /* 分享链接里的 id 找不到（条目被删、链接过期、抄错了）要说一声，
       否则页面停在首页，用户以为链接没生效。 */
    if (!revealPrompt(id)) toast(t('没有找到这条提示词，链接可能已失效'));
  }

  /* ---------- 初始化 ---------- */
  function init() {
    blockList = [];
    DATA.categories.forEach(function (c) {
      c.prompts.forEach(function (p) {
        if ((p.tags || []).indexOf('指令块') >= 0) {
          var en = DATA.en && DATA.en.prompts && DATA.en.prompts[p.id];
          blockList.push({ id: p.id, title: p.title, content: p.content, en: en || null });
        }
      });
    });

    applyTheme(store.get(LS.theme, 'dark'), false);
    /* 下拉值非法（如旧版本残留）时回退为不加命令；'__custom' 始终合法 */
    elPrefix.value = state.opts.prefix === '__custom' || Array.prototype.some.call(elPrefix.options, function (option) {
      return option.value === state.opts.prefix;
    }) ? state.opts.prefix : '';
    state.opts.prefix = elPrefix.value;
    elBlockCustom.value = state.opts.customBlock;
    renderBlockOptions();
    /* HTML 里 search-kbd 初始 hidden 防 JS 失效时与清空按钮重叠，这里按实际内容恢复显隐 */
    if (elSearchKbd) elSearchKbd.hidden = !!elSearch.value;

    /* 引导区的数字由 renderNav 按库里的真实条数写，这里不再重复设置 */

    applyLanguage(state.lang, false);
    syncSidebarAccessibility();
    bind();
    openHash();
  }

  init();
})();
