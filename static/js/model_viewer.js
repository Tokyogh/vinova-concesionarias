/* ES: Implementa interacción de navegador para static/js/model_viewer; backend conserva la autoridad. */
/* EN: Implements browser interaction for static/js/model_viewer; the backend remains authoritative. */
(function () {
  'use strict';

  const MODEL_VIEWER_SRC =
    'https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js';
  let injected = false;

  function injectModelViewer() {
    if (injected || window.customElements.get('model-viewer')) return;
    const script = document.createElement('script');
    script.type = 'module';
    script.src = MODEL_VIEWER_SRC;
    document.head.appendChild(script);
    injected = true;
  }

  function scan(container) {
    if (injected) return;
    if (container && container.querySelector) {
      const viewer = container.querySelector('model-viewer');
      if (viewer) injectModelViewer();
    }
  }

  function handleAddedNodes(node) {
    if (injected || !node || node.nodeType !== 1) return;
    if (node.tagName === 'MODEL-VIEWER') {
      injectModelViewer();
      return;
    }
    scan(node);
  }

  try {
    if (window.MutationObserver) {
      new MutationObserver(function (mutations) {
        for (let i = 0; i < mutations.length; i++) {
          const nodes = mutations[i].addedNodes;
          for (let j = 0; j < nodes.length; j++) handleAddedNodes(nodes[j]);
        }
      }).observe(document.documentElement, { childList: true, subtree: true });
    }
    scan(document);
  } catch (e) {
    return;
  }
})();
