// Loaded in <head> so the page never flashes the wrong theme.
// Dark is the default even on a device set to light (see DESIGN.md).
(function () {
  var t = 'dark';
  try { t = localStorage.getItem('lo-theme') || 'dark'; } catch (e) {}
  if (['dark', 'day', 'night'].indexOf(t) < 0) t = 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();
