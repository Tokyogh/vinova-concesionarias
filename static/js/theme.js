/* ES: Implementa interacción de navegador para static/js/theme; backend conserva la autoridad. */
/* EN: Implements browser interaction for static/js/theme; the backend remains authoritative. */
  /* ES: El tema combina preferencia local y sistema; fallos de storage mantienen una experiencia funcional. */
  /* EN: Theme state combines local and system preference; storage failures keep the experience functional. */
(function () {
  'use strict';

  const THEME_KEY = 'vinova-theme';
  /* ES: El tema combina preferencia local y sistema; fallos de storage mantienen una experiencia funcional. */
  /* EN: Theme state combines local and system preference; storage failures keep the experience functional. */

  function preferencesAllowed() {
    return Boolean(window.VinovaConsent && window.VinovaConsent.allows('preferences'));
  }

  function getSystemTheme() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function getStoredTheme() {
    if (!preferencesAllowed()) return null;
    try { return localStorage.getItem(THEME_KEY) || null; } catch (e) { return null; }
  }

  function setStoredTheme(theme) {
    if (!preferencesAllowed()) return;
    try {
      if (theme === 'system') localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, theme);
    } catch (e) {}
  }

  function currentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  }

  function toggleLabel(resolved) {
    return resolved === 'dark' ? 'Cambiar a modo claro' : 'Cambiar a modo oscuro';
  }

  function refreshToggleLabels() {
    const resolved = currentTheme() === 'dark' ? 'dark' : 'light';
    const label = toggleLabel(resolved);
    document.querySelectorAll('[data-theme-toggle]').forEach(function (toggle) {
      toggle.setAttribute('aria-label', label);
      toggle.setAttribute('title', label);
    });
  }

  function applyTheme(theme) {
    const resolved = theme === 'dark' || theme === 'light' ? theme : getSystemTheme();
    document.documentElement.setAttribute('data-theme', resolved);
    setStoredTheme(theme === 'dark' || theme === 'light' ? theme : 'system');
    refreshToggleLabels();
  }

  function init() {
    applyTheme(getStoredTheme() || 'system');
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', refreshToggleLabels);
    } else {
      refreshToggleLabels();
    }
  }

  function syncWithSystem() {
    if (!getStoredTheme()) applyTheme('system');
  }

  document.addEventListener('click', function (event) {
    const toggle = event.target.closest('[data-theme-toggle]');
    if (!toggle) return;
    applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
  });

  if (window.matchMedia) {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', syncWithSystem);
    } else if (typeof mediaQuery.addListener === 'function') {
      mediaQuery.addListener(syncWithSystem);
    }
  }

  init();
})();
