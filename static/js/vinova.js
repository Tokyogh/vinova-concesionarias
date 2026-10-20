/* ES: Implementa interacción de navegador para static/js/vinova; backend conserva la autoridad. */
/* EN: Implements browser interaction for static/js/vinova; the backend remains authoritative. */
(function () {
  'use strict';

  function normalize(value) {
    return (value || '')
      .toString()
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '');
  }

  function enhanceSelect(select) {
    if (!select || select.dataset.enhancedSearch === 'true') return;
    select.dataset.enhancedSearch = 'true';

    const wrapper = document.createElement('div');
    wrapper.className = 'searchable-select-wrap';

    const input = document.createElement('input');
    input.type = 'search';
    input.className = 'form-control searchable-select-input';
    input.placeholder = select.dataset.searchPlaceholder || 'Buscar en la lista...';
    input.autocomplete = 'off';
    input.setAttribute('aria-label', input.placeholder);

    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(select);

    const original = [...select.options].map((option) => ({
      value: option.value,
      text: option.text,
      option,
    }));

    original.forEach(({ option }) => {
      if (option.disabled) option.dataset.originalDisabled = 'true';
    });

    function filter() {
      const query = normalize(input.value);
      let visible = 0;
      original.forEach(({ option, text, value }) => {
        const keep = !query || normalize(text).includes(query) || normalize(value).includes(query);
        option.hidden = !keep;
        option.disabled = option.dataset.originalDisabled === 'true';
        if (keep) visible += 1;
      });
      wrapper.dataset.empty = visible ? 'false' : 'true';
    }

    input.addEventListener('input', filter);
    if (select.multiple) {
      const help = document.createElement('small');
      help.className = 'searchable-select-help';
      help.textContent = 'Puedes mantener Ctrl presionado para seleccionar varios elementos.';
      wrapper.appendChild(help);
    }
  }

  function bootSearchableSelects(scope) {
    (scope || document)
      .querySelectorAll('select[data-searchable-select="true"]')
      .forEach(enhanceSelect);
  }

  function bootFilterPanels(scope) {
    (scope || document).querySelectorAll('[data-filter-panel]').forEach((panel) => {
      if (panel.dataset.filterPanelReady === 'true') return;
      panel.dataset.filterPanelReady = 'true';

      const more = panel.querySelector('[data-filter-more]');
      const advanced = more ? document.getElementById(more.getAttribute('aria-controls')) : null;
      if (more && advanced) {
        more.addEventListener('click', () => {
          const expanded = more.getAttribute('aria-expanded') !== 'true';
          more.setAttribute('aria-expanded', expanded ? 'true' : 'false');
          advanced.hidden = !expanded;
          if (expanded) {
            const firstControl = advanced.querySelector('input, select, button');
            if (firstControl) firstControl.focus();
          }
        });
      }

      const savedRoot = panel.querySelector('[data-saved-views]');
      if (!savedRoot) return;
      const select = savedRoot.querySelector('[data-saved-view-select]');
      const save = savedRoot.querySelector('[data-saved-view-save]');
      const remove = savedRoot.querySelector('[data-saved-view-delete]');
      const key = `vinova:filter-views:${panel.dataset.filterUser || '0'}:${panel.dataset.filterNamespace}`;
      const read = () => {
        if (!window.VinovaConsent || !window.VinovaConsent.allows('preferences')) return [];
        try {
          const value = JSON.parse(window.localStorage.getItem(key) || '[]');
          return Array.isArray(value) ? value.filter((view) => (
            view && typeof view.id === 'string' && typeof view.name === 'string' &&
            typeof view.url === 'string' &&
            (view.url === window.location.pathname || view.url.startsWith(`${window.location.pathname}?`))
          )) : [];
        } catch (error) {
          return [];
        }
      };
      const write = (views) => {
        if (!window.VinovaConsent || !window.VinovaConsent.allows('preferences')) return;
        try { window.localStorage.setItem(key, JSON.stringify(views)); } catch (error) { /* Sin persistencia local. */ }
      };
      const render = () => {
        const selected = select.value;
        select.innerHTML = '<option value="">Vistas guardadas</option>';
        read().forEach((view) => {
          const option = document.createElement('option');
          option.value = view.id;
          option.textContent = view.name;
          select.appendChild(option);
        });
        if ([...select.options].some((option) => option.value === selected)) select.value = selected;
        remove.disabled = !select.value;
      };
      select.addEventListener('change', () => {
        remove.disabled = !select.value;
        const view = read().find((item) => item.id === select.value);
        if (view) window.location.assign(view.url);
      });
      save.addEventListener('click', () => {
        const name = window.prompt('Nombre de la vista');
        if (!name || !name.trim()) return;
        const views = read();
        const normalized = name.trim().slice(0, 60);
        const existing = views.find((view) => view.name.toLowerCase() === normalized.toLowerCase());
        const record = { id: existing ? existing.id : `${Date.now()}`, name: normalized, url: `${window.location.pathname}${window.location.search}` };
        write(existing ? views.map((view) => view.id === existing.id ? record : view) : views.concat(record).slice(-12));
        render();
        select.value = record.id;
        remove.disabled = false;
      });
      remove.addEventListener('click', () => {
        if (!select.value) return;
        write(read().filter((view) => view.id !== select.value));
        render();
      });
      render();
    });
  }

  function bootImportForm(scope) {
    const root = scope || document;
    const typeSelect = root.querySelector('#id_import_type') || document.getElementById('id_import_type');
    if (!typeSelect || typeSelect.dataset.vinovaImportReady === 'true') return;
    typeSelect.dataset.vinovaImportReady = 'true';

    const form = typeSelect.closest('form') || document;
    const vehicleFields = form.querySelectorAll('.vehicle-only-field');
    function updateVehicleFields() {
      const visible = typeSelect.value === 'vehicles';
      vehicleFields.forEach((field) => {
        field.hidden = !visible;
        const checkbox = field.querySelector('input[type="checkbox"]');
        if (checkbox && !visible) checkbox.checked = false;
      });
    }
    typeSelect.addEventListener('change', updateVehicleFields);
    updateVehicleFields();
  }

  function modalRoot() {
    return document.getElementById('modal-root');
  }

  let drawerReturnFocus = null;

  function drawerUsesOverlay(drawer) {
    return window.matchMedia(drawer.dataset.drawerQuery || '(max-width: 900px)').matches;
  }

  function drawerOverlay(drawer) {
    return document.querySelector(`[data-drawer-overlay="${drawer.id}"]`);
  }

  function updateDrawerScrollLock() {
    document.body.classList.toggle('drawer-open', Boolean(document.querySelector('[data-drawer].is-open')));
  }

  function closeDrawer(drawer, restoreFocus) {
    if (!drawer) return;
    drawer.classList.remove('is-open');
    const overlay = drawerOverlay(drawer);
    if (overlay) overlay.classList.remove('is-active');
    document.querySelectorAll(`[data-drawer-open="${drawer.id}"]`).forEach((trigger) => {
      trigger.setAttribute('aria-expanded', 'false');
    });
    if (drawerUsesOverlay(drawer)) drawer.setAttribute('aria-hidden', 'true');
    else drawer.removeAttribute('aria-hidden');
    updateDrawerScrollLock();
    if (restoreFocus && drawerReturnFocus && document.contains(drawerReturnFocus)) drawerReturnFocus.focus();
    drawerReturnFocus = null;
  }

  function openDrawer(drawer, trigger) {
    if (!drawer || !drawerUsesOverlay(drawer)) return;
    document.querySelectorAll('[data-drawer].is-open').forEach((open) => closeDrawer(open, false));
    drawerReturnFocus = trigger;
    drawer.classList.add('is-open');
    drawer.setAttribute('aria-hidden', 'false');
    const overlay = drawerOverlay(drawer);
    if (overlay) overlay.classList.add('is-active');
    document.querySelectorAll(`[data-drawer-open="${drawer.id}"]`).forEach((button) => {
      button.setAttribute('aria-expanded', 'true');
    });
    updateDrawerScrollLock();
    const first = drawer.querySelector('[data-drawer-close], a[href], button:not([disabled])');
    if (first) first.focus();
  }

  function syncDrawers() {
    document.querySelectorAll('[data-drawer]').forEach((drawer) => {
      if (drawerUsesOverlay(drawer)) {
        if (!drawer.classList.contains('is-open')) drawer.setAttribute('aria-hidden', 'true');
      } else {
        closeDrawer(drawer, false);
        drawer.removeAttribute('aria-hidden');
      }
    });
  }

  function trapDrawerFocus(event, drawer) {
    if (event.key !== 'Tab') return;
    const focusable = [...drawer.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )].filter((element) => element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function bootDrawers() {
    if (document.documentElement.dataset.vinovaDrawersReady === 'true') return;
    document.documentElement.dataset.vinovaDrawersReady = 'true';
    syncDrawers();
    window.addEventListener('resize', syncDrawers);
  }

  function closeModal() {
    const root = modalRoot();
    if (!root) return;
    const returnFocusId = root.dataset.returnFocusId;
    root.innerHTML = '';
    document.body.classList.remove('modal-open');
    if (returnFocusId) {
      const trigger = document.getElementById(returnFocusId);
      if (trigger) trigger.focus();
    }
    delete root.dataset.returnFocusId;
  }

  function activateModalTab(modal, tabName) {
    modal.querySelectorAll('[data-modal-tab]').forEach((button) => {
      const selected = button.dataset.modalTab === tabName;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-selected', selected ? 'true' : 'false');
      button.tabIndex = selected ? 0 : -1;
    });
    modal.querySelectorAll('[data-modal-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.modalPanel !== tabName;
    });
  }

  function activateGalleryImage(modal, selectedIndex) {
    const images = [...modal.querySelectorAll('[data-gallery-image]')];
    const buttons = [...modal.querySelectorAll('[data-gallery-thumb]')];
    images.forEach((image, index) => {
      image.hidden = index !== selectedIndex;
    });
    buttons.forEach((button, index) => {
      const selected = index === selectedIndex;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-current', selected ? 'true' : 'false');
    });
  }

  function trapModalFocus(event, modal) {
    if (event.key !== 'Tab') return;
    const focusable = [...modal.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )].filter((element) => !element.hidden && element.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function bootVehicleModal(scope) {
    const root = modalRoot();
    const modal = (scope || document).querySelector('[data-vinova-modal]')
      || (root && root.querySelector('[data-vinova-modal]'));
    if (!modal || modal.dataset.vinovaModalReady === 'true') return;
    modal.dataset.vinovaModalReady = 'true';
    document.body.classList.add('modal-open');

    activateModalTab(modal, 'gallery');
    activateGalleryImage(modal, 0);

    modal.addEventListener('click', (event) => {
      const closeButton = event.target.closest('[data-modal-close]');
      if (closeButton) {
        closeModal();
        return;
      }
      const tabButton = event.target.closest('[data-modal-tab]');
      if (tabButton) {
        activateModalTab(modal, tabButton.dataset.modalTab);
        tabButton.focus();
        return;
      }
      const thumb = event.target.closest('[data-gallery-thumb]');
      if (thumb) {
        const buttons = [...modal.querySelectorAll('[data-gallery-thumb]')];
        activateGalleryImage(modal, buttons.indexOf(thumb));
      }
    });

    modal.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closeModal();
        return;
      }
      const selectedTab = event.target.closest('[data-modal-tab]');
      if (selectedTab && ['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
        event.preventDefault();
        const tabs = [...modal.querySelectorAll('[data-modal-tab]')];
        const current = tabs.indexOf(selectedTab);
        let next = current;
        if (event.key === 'ArrowRight') next = (current + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        activateModalTab(modal, tabs[next].dataset.modalTab);
        tabs[next].focus();
        return;
      }
      trapModalFocus(event, modal);
    });

    const backdrop = modal.closest('.modal-backdrop');
    if (backdrop) {
      backdrop.addEventListener('mousedown', (event) => {
        if (event.target === backdrop) closeModal();
      });
    }

    const closeButton = modal.querySelector('[data-modal-close]');
    if (closeButton) closeButton.focus();
  }

  function bootAutoSubmit(scope) {
    (scope || document).querySelectorAll('[data-auto-submit]').forEach((control) => {
      if (control.dataset.autoSubmitReady) return;
      control.dataset.autoSubmitReady = '1';
      control.addEventListener('change', () => {
        const form = control.form || control.closest('form');
        if (form) form.requestSubmit();
      });
    });
  }

  function bootFavorites(scope) {
    (scope || document).querySelectorAll('[data-favorite]').forEach((button) => {
      if (button.dataset.favoriteReady) return;
      button.dataset.favoriteReady = '1';
      const key = `vinova-favorite-${button.dataset.favoriteKey || button.closest('[data-vehicle]')?.dataset.vehicle || button.id}`;
      const preferencesAllowed = window.VinovaConsent && window.VinovaConsent.allows('preferences');
      try {
        if (preferencesAllowed && window.localStorage.getItem(key) === '1') {
          button.setAttribute('aria-pressed', 'true');
        }
      } catch (error) {
        /* Almacenamiento no disponible: el control queda solo como estado visual. */
      }
      button.addEventListener('click', () => {
        const next = button.getAttribute('aria-pressed') !== 'true';
        button.setAttribute('aria-pressed', next ? 'true' : 'false');
        if (!preferencesAllowed) return;
        try {
          if (next) window.localStorage.setItem(key, '1');
          else window.localStorage.removeItem(key);
        } catch (error) {
          /* Estado visual sin persistencia. */
        }
      });
    });
  }

  function activateDetailTab(root, tabName) {
    root.querySelectorAll('[data-detail-tab]').forEach((button) => {
      const selected = button.dataset.detailTab === tabName;
      button.setAttribute('aria-selected', selected ? 'true' : 'false');
      button.tabIndex = selected ? 0 : -1;
    });
    root.querySelectorAll('[data-detail-panel]').forEach((panel) => {
      panel.hidden = panel.dataset.detailPanel !== tabName;
    });
  }

  function bootVehicleDetail(scope) {
    (scope || document).querySelectorAll('[data-detail-tabs]').forEach((root) => {
      if (root.dataset.detailTabsReady === '1') return;
      root.dataset.detailTabsReady = '1';

      root.addEventListener('click', (event) => {
        const tab = event.target.closest('[data-detail-tab]');
        if (tab && root.contains(tab)) activateDetailTab(root, tab.dataset.detailTab);
      });

      root.addEventListener('keydown', (event) => {
        const tab = event.target.closest('[data-detail-tab]');
        if (!tab || !['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(event.key)) return;
        const tabs = [...root.querySelectorAll('[data-detail-tab]')];
        const index = tabs.indexOf(tab);
        let next = index;
        if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = tabs.length - 1;
        event.preventDefault();
        activateDetailTab(root, tabs[next].dataset.detailTab);
        tabs[next].focus();
      });
    });

    (scope || document).querySelectorAll('[data-gallery-stage]').forEach((stage) => {
      if (stage.dataset.galleryStageReady === '1') return;
      stage.dataset.galleryStageReady = '1';
      const rail = stage.closest('.vehicle-gallery');
      if (!rail) return;

      const select = (index) => {
        [...stage.querySelectorAll('[data-gallery-image]')].forEach((image, position) => {
          image.hidden = position !== index;
        });
        [...rail.querySelectorAll('[data-gallery-thumb]')].forEach((button, position) => {
          const active = position === index;
          button.classList.toggle('is-active', active);
          button.setAttribute('aria-current', active ? 'true' : 'false');
        });
      };

      rail.addEventListener('click', (event) => {
        const thumb = event.target.closest('[data-gallery-thumb]');
        if (!thumb || !rail.contains(thumb)) return;
        select([...rail.querySelectorAll('[data-gallery-thumb]')].indexOf(thumb));
      });

      const toggle = rail.querySelector('[data-stage-toggle="3d"]');
      const model = rail.querySelector('[data-stage-3d]');
      if (toggle && model) {
        toggle.addEventListener('click', () => {
          const next = toggle.getAttribute('aria-pressed') !== 'true';
          toggle.setAttribute('aria-pressed', next ? 'true' : 'false');
          model.hidden = !next;
          const media = rail.querySelector('[data-gallery-stage]');
          if (media) media.hidden = next;
        });
      }
    });
  }

  function boot(scope) {
    bootDrawers();
    bootSearchableSelects(scope);
    bootFilterPanels(scope);
    bootImportForm(scope);
    bootVehicleModal(scope);
    bootAutoSubmit(scope);
    bootFavorites(scope);
    bootVehicleDetail(scope);
    bootNavShell(scope);
    bootCommandPalette(scope);
  }

  /* --- Shell staff: favoritos, recientes, grupos colapsables y paleta Ctrl+K --- */

  function navData() {
    const element = document.getElementById('staff-nav-data');
    if (!element) return null;
    try {
      return JSON.parse(element.textContent);
    } catch (error) {
      return null;
    }
  }

  function navStore(userId, kind) {
    const key = `vinova:nav:${kind}:${userId}`;
    function read() {
      if (!window.VinovaConsent || !window.VinovaConsent.allows('preferences')) return [];
      try {
        const raw = window.localStorage.getItem(key);
        const value = raw ? JSON.parse(raw) : null;
        return Array.isArray(value) ? value : [];
      } catch (error) {
        return [];
      }
    }
    function write(value) {
      if (!window.VinovaConsent || !window.VinovaConsent.allows('preferences')) return;
      try {
        window.localStorage.setItem(key, JSON.stringify(value));
      } catch (error) {
        /* Persistencia no disponible. */
      }
    }
    return { read, write };
  }

  function bootNavShell(bootScope) {
    const data = navData();
    if (!data || document.documentElement.dataset.vinovaNavReady === 'true') return;
    document.documentElement.dataset.vinovaNavReady = 'true';

    const scope = bootScope || document;
    const favoritesSection = scope.querySelector('[data-nav-favorites]');
    const favoritesList = scope.querySelector('[data-nav-favorites-list]');
    const recentsSection = scope.querySelector('[data-nav-recents]');
    const recentsList = scope.querySelector('[data-nav-recents-list]');
    if (!favoritesSection || !favoritesList || !recentsSection || !recentsList) return;

    const userId = data.userId || '0';
    const destinationsByKey = new Map((data.destinations || []).map((destination) => [destination.key, destination]));
    const favorites = navStore(userId, 'favs');
    const recents = navStore(userId, 'recents');
    const collapsed = navStore(userId, 'collapsed');

    const authorized = new Set((data.destinations || []).map((destination) => destination.key));

    function sourceLink(key) {
      return scope.querySelector(`.side-nav-link[data-nav-key="${key}"]`);
    }

    function cloneLink(key) {
      const source = sourceLink(key);
      if (!source) return null;
      const clone = source.cloneNode(true);
      clone.removeAttribute('aria-current');
      return clone;
    }

    function renderList(list, keys, section) {
      list.innerHTML = '';
      let added = 0;
      keys.forEach((key) => {
        const link = cloneLink(key);
        if (!link) return;
        const item = document.createElement('div');
        item.className = 'side-nav-row';
        item.appendChild(link);
        list.appendChild(item);
        added += 1;
      });
      if (section) section.hidden = added === 0 || list.children.length === 0;
    }

    function renderFavorites() {
      const keys = favorites.read().filter((key) => authorized.has(key));
      renderList(favoritesList, keys, favoritesSection);
      scope.querySelectorAll('[data-nav-star]').forEach((star) => {
        const pressed = keys.includes(star.dataset.navStar);
        const destination = destinationsByKey.get(star.dataset.navStar);
        star.setAttribute('aria-pressed', pressed ? 'true' : 'false');
        if (destination) star.setAttribute('aria-label', `${pressed ? 'Quitar' : 'Agregar'} ${destination.title} ${pressed ? 'de' : 'a'} favoritos`);
      });
    }

    function renderRecents() {
      const keys = recents.read().filter((key) => authorized.has(key));
      renderList(recentsList, keys, recentsSection);
    }

    scope.querySelectorAll('[data-nav-star]').forEach((star) => {
      if (star.dataset.navStarReady === 'true') return;
      star.dataset.navStarReady = 'true';
      star.addEventListener('click', () => {
        const key = star.dataset.navStar;
        let keys = favorites.read().filter((k) => k !== key);
        if (star.getAttribute('aria-pressed') !== 'true') keys = [key].concat(keys);
        star.setAttribute('aria-pressed', keys.includes(key) ? 'true' : 'false');
        favorites.write(keys);
        renderFavorites();
      });
    });

    scope.querySelectorAll('[data-nav-group]').forEach((group) => {
      const toggle = group.querySelector('[data-nav-group-toggle]');
      if (!toggle) return;
      const key = group.dataset.navGroup;
      let collapsedKeys = collapsed.read();
      if (collapsedKeys.includes(key)) {
        group.classList.add('is-collapsed');
        toggle.setAttribute('aria-expanded', 'false');
      }
      toggle.addEventListener('click', () => {
        const isCollapsed = group.classList.toggle('is-collapsed');
        toggle.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
        let keys = collapsed.read().filter((k) => k !== key);
        if (isCollapsed) keys = keys.concat(key);
        collapsed.write(keys);
      });
    });

    if (authorized.has(data.currentKey)) {
      const keys = [data.currentKey].concat(recents.read().filter((k) => k !== data.currentKey)).slice(0, 8);
      recents.write(keys);
    }

    renderFavorites();
    renderRecents();
  }

  function paletteIcon(iconHolder, sourceAnchor) {
    if (!sourceAnchor) return;
    const icon = sourceAnchor.querySelector('svg');
    if (!icon) return;
    iconHolder.appendChild(icon.cloneNode(true));
  }

  function bootCommandPalette(bootScope) {
    const data = navData();
    if (!data) return;
    const scope = bootScope || document;
    const trigger = scope.querySelector('[data-command-palette-trigger]');
    const palette = scope.querySelector('[data-command-palette]');
    if (!trigger || !palette) return;

    const input = palette.querySelector('#command-palette-input');
    const results = palette.querySelector('#command-palette-results');
    const empty = palette.querySelector('[data-command-palette-empty]');
    const assist = palette.querySelector('[data-command-palette-assist]');
    const assistAnswer = palette.querySelector('[data-command-palette-answer]');
    if (!input || !results || !empty) return;
    if (palette.dataset.vinovaPaletteReady === 'true') return;
    palette.dataset.vinovaPaletteReady = 'true';
    const sources = new Map((data.destinations || []).map((destination) => {
      const source = scope.querySelector(`.side-nav-link[data-nav-key="${destination.key}"]`);
      return [destination.key, source];
    }));

    function buildOption(destination, index) {
      const item = document.createElement('li');
      item.className = 'command-palette-option';
      item.setAttribute('role', 'option');
      item.setAttribute('id', `command-palette-option-${index}`);
      item.dataset.key = destination.key;
      item.dataset.href = destination.url;
      const icon = document.createElement('span');
      icon.className = 'command-palette-option-icon';
      paletteIcon(icon, sources.get(destination.key));
      const label = document.createElement('span');
      label.className = 'command-palette-option-copy';
      const title = document.createElement('strong');
      title.textContent = destination.title;
      label.appendChild(title);
      if (destination.description) {
        const description = document.createElement('small');
        description.textContent = destination.description;
        label.appendChild(description);
      }
      item.appendChild(icon);
      item.appendChild(label);
      item.addEventListener('click', () => {
        closePalette();
        window.location.href = destination.url;
      });
      return item;
    }

    let options = [];
    let optionMetadata = new Map();
    function populate(entries) {
      const sourceEntries = entries || data.destinations || [];
      results.innerHTML = '';
      optionMetadata = new Map(sourceEntries.map((destination) => [destination.key, destination]));
      options = sourceEntries.map(buildOption);
      options.forEach((option) => results.appendChild(option));
    }

    let activeIndex = -1;

    function filter(query) {
      const normalized = normalize(query);
      let visible = 0;
      options.forEach((option) => {
        const destination = optionMetadata.get(option.dataset.key);
        const haystack = [destination.title, destination.area].concat(destination.keywords || []).join(' ');
        const keep = !normalized || normalize(haystack).includes(normalized);
        option.hidden = !keep;
        if (keep) visible += 1;
      });
      if (visible === 0) {
        empty.hidden = false;
        activeIndex = -1;
        input.removeAttribute('aria-activedescendant');
      } else {
        empty.hidden = true;
        activate(0);
      }
    }

    function visibleOptions() {
      return options.filter((option) => !option.hidden);
    }

    function activate(index) {
      const visible = visibleOptions();
      activeIndex = index;
      visible.forEach((option, position) => {
        const active = position === index;
        option.classList.toggle('is-active', active);
        option.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      const target = visible[index];
      if (target) {
        input.setAttribute('aria-activedescendant', target.id);
        target.scrollIntoView({ block: 'nearest' });
      }
    }

    function openPalette() {
      populate();
      input.value = '';
      if (assist) assist.hidden = true;
      palette.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      input.setAttribute('aria-expanded', 'true');
      filter('');
      input.focus();
    }

    function closePalette() {
      window.clearTimeout(assistTimer);
      if (assistAbort) assistAbort.abort();
      palette.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      trigger.focus();
    }

    function currentHref() {
      const visible = visibleOptions();
      const option = visible[activeIndex];
      return option ? option.dataset.href : null;
    }

    trigger.addEventListener('click', () => {
      if (palette.hidden) openPalette();
      else closePalette();
    });
    palette.querySelectorAll('[data-command-palette-close]').forEach((closer) => closer.addEventListener('click', closePalette));

    palette.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        closePalette();
        return;
      }
      if (event.key !== 'Tab') return;
      const focusable = [...palette.querySelectorAll('input, button, [href], [tabindex]:not([tabindex="-1"])')]
        .filter((element) => !element.hidden && !element.disabled);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });

    let assistTimer = null;
    let assistAbort = null;
    function requestAssist(query) {
      window.clearTimeout(assistTimer);
      if (assistAbort) assistAbort.abort();
      const trimmed = query.trim();
      if (trimmed.length < 2 || (!palette.dataset.assistUrl && !palette.dataset.searchUrl)) {
        populate();
        filter(trimmed);
        if (assist) assist.hidden = true;
        return;
      }
      populate();
      filter(trimmed);
      assistTimer = window.setTimeout(async () => {
        assistAbort = new AbortController();
        try {
          const requestJson = async (baseUrl) => {
            if (!baseUrl) return null;
            const response = await window.fetch(`${baseUrl}?q=${encodeURIComponent(trimmed)}`, {
              credentials: 'same-origin',
              signal: assistAbort.signal,
            });
            return response.ok ? response.json() : null;
          };
          // Mantener las lecturas en serie evita competir por la misma sesión/DB
          // y conserva un único flujo cancelable al escribir rápidamente.
          const searchPayload = await requestJson(palette.dataset.searchUrl);
          const assistPayload = await requestJson(palette.dataset.assistUrl);
          if (input.value.trim() !== trimmed) return;
          const combined = [
            ...((searchPayload && searchPayload.results) || []),
            ...((assistPayload && assistPayload.results) || []),
          ];
          populate(combined);
          if (options.length) {
            empty.hidden = true;
            activate(0);
          } else {
            empty.hidden = false;
            activeIndex = -1;
            input.removeAttribute('aria-activedescendant');
          }
          if (assist && assistAnswer) {
            const assistResults = (assistPayload && assistPayload.results) || [];
            const entityResults = (searchPayload && searchPayload.results) || [];
            assistAnswer.textContent = (!entityResults.length || assistResults.length)
              ? ((assistPayload && assistPayload.answer) || '')
              : '';
            assist.hidden = !assistAnswer.textContent;
          }
        } catch (error) {
          if (error.name !== 'AbortError') {
            populate();
            filter(trimmed);
          }
        }
      }, 180);
    }

    input.addEventListener('input', () => requestAssist(input.value));

    input.addEventListener('keydown', (event) => {
      const visible = visibleOptions();
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        activate(Math.min((activeIndex < 0 ? -1 : activeIndex) + 1, visible.length - 1));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        activate(Math.max((activeIndex <= 0 ? visible.length : activeIndex) - 1, 0));
      } else if (event.key === 'Enter') {
        const href = currentHref();
        if (href) {
          event.preventDefault();
          closePalette();
          window.location.href = href;
        }
      }
    });

    if (!document.documentElement.dataset.vinovaPaletteReady) {
      document.documentElement.dataset.vinovaPaletteReady = 'true';
      document.addEventListener('keydown', (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
          event.preventDefault();
          if (palette.hidden) openPalette();
          else closePalette();
        }
      });
    }
  }

  document.addEventListener('click', (event) => {
    const drawerTrigger = event.target.closest('[data-drawer-open]');
    if (drawerTrigger) {
      openDrawer(document.getElementById(drawerTrigger.dataset.drawerOpen), drawerTrigger);
      return;
    }

    const drawerClose = event.target.closest('[data-drawer-close]');
    if (drawerClose) {
      closeDrawer(drawerClose.closest('[data-drawer]'), true);
      return;
    }

    const overlay = event.target.closest('[data-drawer-overlay]');
    if (overlay) {
      closeDrawer(document.getElementById(overlay.dataset.drawerOverlay), true);
      return;
    }

    const drawerLink = event.target.closest('[data-drawer] a[href]');
    if (drawerLink) {
      const drawer = drawerLink.closest('[data-drawer]');
      if (drawerUsesOverlay(drawer)) closeDrawer(drawer, false);
    }

    const printButton = event.target.closest('[data-print-page]');
    if (printButton) {
      window.print();
      return;
    }

    const modalTrigger = event.target.closest('[hx-target="#modal-root"]');
    if (modalTrigger) {
      if (!modalTrigger.id) modalTrigger.id = `vinova-modal-trigger-${Date.now()}`;
      const root = modalRoot();
      if (root) root.dataset.returnFocusId = modalTrigger.id;
    }
  });

  document.addEventListener('submit', (event) => {
    const submittedForm = event.target.closest('form');
    if (submittedForm) {
      try {
        const action = new URL(submittedForm.action, window.location.href);
        if (action.origin === window.location.origin && action.pathname.endsWith('/accounts/logout/')) {
          Object.keys(window.localStorage).forEach((key) => {
            if (key.startsWith('vinova:nav:') || key.startsWith('vinova:filter-views:')) {
              window.localStorage.removeItem(key);
            }
          });
        }
      } catch (error) {
        /* ES: El logout continúa si el storage no está disponible. EN: Logout continues if storage is unavailable. */
      }
    }
    const form = event.target.closest('form[data-confirm]');
    if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
  });

  document.addEventListener('keydown', (event) => {
    const openDrawer = document.querySelector('[data-drawer].is-open');
    if (openDrawer && event.key === 'Escape') {
      event.preventDefault();
      closeDrawer(openDrawer, true);
      return;
    }
    if (openDrawer) trapDrawerFocus(event, openDrawer);
    if (event.key === 'Escape' && modalRoot() && modalRoot().children.length) closeModal();
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { boot(document); });
  } else {
    boot(document);
  }

  document.body.addEventListener('htmx:afterSwap', (event) => boot(event.detail && event.detail.target));
})();
