/* ES: Expone categorías consentidas y retira preferencias locales revocadas. */
/* EN: Exposes consented categories and removes revoked local preferences. */

(function () {
  'use strict';

  const meta = document.querySelector('meta[name="vinova-cookie-consent"]');
  const state = Object.freeze({
    decided: Boolean(meta && meta.dataset.decided === '1'),
    preferences: Boolean(meta && meta.dataset.preferences === '1'),
    analytics: Boolean(meta && meta.dataset.analytics === '1'),
    externalMedia: Boolean(meta && meta.dataset.externalMedia === '1'),
    version: meta ? meta.dataset.version || '' : '',
  });

  window.VinovaConsent = Object.freeze({
    state,
    allows(category) {
      if (category === 'external_media') return state.decided && state.externalMedia;
      return state.decided && state[category] === true;
    },
  });

  if (!state.preferences) {
    try {
      Object.keys(window.localStorage).forEach((key) => {
        if (
          key === 'vinova-theme' ||
          key.startsWith('vinova-favorite-') ||
          key.startsWith('vinova:nav:') ||
          key.startsWith('vinova:filter-views:')
        ) {
          window.localStorage.removeItem(key);
        }
      });
    } catch (error) {
      /* ES: La página funciona sin storage. EN: The page remains usable without storage. */
    }
  }
})();
