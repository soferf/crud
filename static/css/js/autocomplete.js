/**
 * Autocomplete para trabajadores en el formulario de recibos.
 * Busca en los trabajadores activos de la BD por nombre O alias/apodo.
 * Acepta tanto una lista estática (trabajadores[]) como búsqueda live a /api/trabajadores.
 */
function initTrabajadorAutocomplete(trabajadores, options) {
  const { searchInput, suggestionsList, fields, onSelect } = options;
  if (!searchInput || !suggestionsList) return;

  let debounceTimer = null;

  function formatValor(v) {
    if (!v) return '';
    return new Intl.NumberFormat('es-CO').format(v);
  }

  function renderSuggestions(matches) {
    suggestionsList.innerHTML = '';
    if (!matches || matches.length === 0) {
      const li = document.createElement('li');
      li.className = 'suggestion-item suggestion-item--empty';
      li.textContent = 'Sin coincidencias. Verifica el nombre o apodo.';
      suggestionsList.appendChild(li);
      suggestionsList.style.display = 'block';
      return;
    }
    matches.forEach(t => {
      const li = document.createElement('li');
      li.className = 'suggestion-item';
      const aliasList = Array.isArray(t.alias) ? t.alias : [];
      const aliasText = aliasList.length > 0
        ? ` <span class="alias-tag">(${aliasList.join(', ')})</span>`
        : '';
      li.innerHTML = `<strong>${t.nombre}</strong>${aliasText}<span class="suggestion-nit">NIT: ${t.nit || '—'}</span>`;
      li.addEventListener('mousedown', (e) => {
        e.preventDefault(); // prevent blur before click
        fillFields(t);
      });
      suggestionsList.appendChild(li);
    });
    suggestionsList.style.display = 'block';
  }

  function showSuggestions(query) {
    const q = query.toLowerCase().trim();
    suggestionsList.innerHTML = '';

    if (!q) {
      suggestionsList.style.display = 'none';
      return;
    }

    // First try local list (pre-loaded on page)
    if (trabajadores && trabajadores.length > 0) {
      const matches = trabajadores.filter(t => {
        if (t.nombre && t.nombre.toLowerCase().includes(q)) return true;
        const aliasList = Array.isArray(t.alias) ? t.alias : [];
        if (aliasList.some(a => a.toLowerCase().includes(q))) return true;
        return false;
      });
      renderSuggestions(matches);
    }

    // Also refresh from API live (catches newly registered workers)
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      fetch(`/api/trabajadores?q=${encodeURIComponent(q)}`)
        .then(r => r.json())
        .then(data => {
          // Only update if still same query
          if (searchInput.value.toLowerCase().trim() === q) renderSuggestions(data);
        })
        .catch(err => console.warn('Autocomplete API error:', err));
    }, 200);
  }

  function fillFields(t) {
    if (fields.proveedor)  fields.proveedor.value  = t.nombre || '';
    if (fields.nit)        fields.nit.value        = t.nit || '';
    if (fields.direccion)  fields.direccion.value  = t.direccion || '';
    if (fields.telefono)   fields.telefono.value   = t.telefono || '';
    if (fields.ciudad)     fields.ciudad.value     = t.ciudad || '';
    if (fields.concepto && t.concepto_habitual)
      fields.concepto.value = t.concepto_habitual;
    if (fields.valor_operacion && t.valor_habitual) {
      const v = formatValor(t.valor_habitual);
      fields.valor_operacion.value = v;
      if (fields.neto_a_pagar) fields.neto_a_pagar.value = v;
    }
    searchInput.value = t.nombre;
    suggestionsList.style.display = 'none';
    // Callback for any post-fill logic (e.g. recalcSubtotal)
    if (typeof onSelect === 'function') onSelect(t);
  }

  searchInput.addEventListener('input', function() {
    showSuggestions(this.value);
  });

  searchInput.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      suggestionsList.style.display = 'none';
    }
    // Arrow key navigation
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const items = suggestionsList.querySelectorAll('.suggestion-item');
      if (!items.length) return;
      e.preventDefault();
      const active = suggestionsList.querySelector('.suggestion-item.is-active');
      let idx = active ? Array.from(items).indexOf(active) : -1;
      if (active) active.classList.remove('is-active');
      if (e.key === 'ArrowDown') idx = (idx + 1) % items.length;
      else idx = (idx - 1 + items.length) % items.length;
      items[idx].classList.add('is-active');
      items[idx].scrollIntoView({ block: 'nearest' });
    }
    if (e.key === 'Enter') {
      const active = suggestionsList.querySelector('.suggestion-item.is-active');
      if (active) { e.preventDefault(); active.dispatchEvent(new MouseEvent('mousedown')); }
    }
  });

  document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !suggestionsList.contains(e.target)) {
      suggestionsList.style.display = 'none';
    }
  });
}
