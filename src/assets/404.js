/* 404 页独立于首页脚本：按本机语言偏好取文案，并提供语言切换。
   单独放一个外部文件而不是内联脚本：站点的 CSP 只放行哈希过的内联脚本，
   外部脚本走 'self' 即可，不必为每处内联脚本维护哈希。 */
(function () {
  var LANG_KEY = 'plib.lang.v1';
  var lang = 'zh';
  try {
    lang = JSON.parse(localStorage.getItem(LANG_KEY)) === 'en' ? 'en' : 'zh';
  } catch (e) { /* 读不到就按中文 */ }

  function apply() {
    if (window.PLIB_I18N_APPLY) window.PLIB_I18N_APPLY(lang);
  }

  apply();

  var btn = document.getElementById('btn-language');
  if (btn) btn.addEventListener('click', function () {
    lang = lang === 'en' ? 'zh' : 'en';
    try { localStorage.setItem(LANG_KEY, JSON.stringify(lang)); } catch (e) {}
    apply();
  });
})();
