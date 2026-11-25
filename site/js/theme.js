// Loaded in <head> so the page never flashes the wrong theme.
// Dark is the default even on a device set to light (see DESIGN.md). Dark and Light are the
// shared JPS themes (css/tokens.css); Night (red) is Lights Out's own (css/lightsout-tokens.css).
(function () {
  var t = 'dark';
  try { t = localStorage.getItem('lo-theme') || 'dark'; } catch (e) {}
  if (t === 'day') t = 'light';  // the Light theme was called Day before the shared tokens
  if (['dark', 'light', 'night'].indexOf(t) < 0) t = 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();
