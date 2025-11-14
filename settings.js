// Pi Media Hub - Main Application and Settings
// ================================================

// === CONFIGURATION ===
let config = null;
let originalConfig = null;
let apps = [];

// === STATE ===
let isOnline = true;
let currentSelection = 0;
let inConfirm = false;
let inSettings = false;
let pendingApp = null;
let cursorTimeout = null;

// === ELEMENTS ===
const appContainer = document.getElementById('appContainer');
const overlaysContainer = document.getElementById('overlays');
const settingsBtn = document.getElementById('settingsBtn');
const exitBtn = document.getElementById('exitBtn');
const confirmDialog = document.getElementById('confirmDialog');
const dialogLogo = document.getElementById('dialogLogo');
const dialogDesc = document.getElementById('dialogDesc');
const confirmBtn = document.querySelector('#confirmDialog .confirm');
const cancelBtn = document.querySelector('#confirmDialog .cancel');
const whiteFlash = document.getElementById('whiteFlash');
const offlineScreen = document.getElementById('offlineScreen');
const loading = document.getElementById('loading');
const canvas = document.getElementById('orbCanvas');
const settingsScreen = document.getElementById('settingsScreen');
const settingsGrid = document.getElementById('settingsGrid');
const settingsCloseBtn = document.getElementById('settingsCloseBtn');
const saveBtn = document.getElementById('saveBtn');
const cancelSettingsBtn = document.getElementById('cancelBtn');
const saveStatus = document.getElementById('saveStatus');

// === TOAST NOTIFICATIONS ===
function showToast(message, isError = false) {
  const toast = document.createElement('div');
  toast.className = 'toast' + (isError ? ' error' : '');
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => toast.classList.add('show'), 100);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 400);
  }, 3000);
}

// === LOAD CONFIG ===
async function loadConfig() {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) {
      throw new Error('Failed to load config');
    }
    config = await response.json();
    originalConfig = JSON.parse(JSON.stringify(config));
    return config;
  } catch (error) {
    console.error('Failed to load config:', error);
    showToast('Failed to load configuration', true);
    // Fallback minimal config
    config = {
      apps: {
        youtube: { enabled: true, name: 'YouTube', icon: '', url: '', launch_method: 'browser' },
        spotify: { enabled: true, name: 'Spotify', icon: '', url: '', launch_method: 'browser' },
        jellyfin: { enabled: true, name: 'Jellyfin', icon: '', url: '', launch_method: 'auto' }
      },
      display: { performance_mode: 'balanced', hide_cursor_timeout: 3000, resolution_hint: '1080p' },
      startup: { check_network: true, autostart: false, boot_delay: 5 },
      exit: { action: 'cec_standby', show_confirmation: true, cec_fallback: 'close' },
      remote: { enable_cec: true }
    };
    originalConfig = JSON.parse(JSON.stringify(config));
    return config;
  }
}

// === SAVE CONFIG ===
async function saveConfig() {
  try {
    saveStatus.textContent = 'Saving...';
    const response = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });

    if (!response.ok) {
      throw new Error('Failed to save config');
    }

    originalConfig = JSON.parse(JSON.stringify(config));
    showToast('Settings saved successfully!');
    saveStatus.textContent = 'Settings saved';

    // Reload apps
    await reloadApps();
    closeSettings();
  } catch (error) {
    console.error('Failed to save config:', error);
    showToast('Failed to save settings', true);
    saveStatus.textContent = 'Save failed';
  }
}

// === RELOAD APPS ===
async function reloadApps() {
  appContainer.innerHTML = '';
  overlaysContainer.innerHTML = '';
  await loadConfig();
  initializeUI();
}

// === INITIALIZE UI ===
function initializeUI() {
  // Build app list from config
  apps = Object.entries(config.apps)
    .filter(([key, app]) => app.enabled)
    .map(([key, app]) => ({ key, ...app }));

  // Populate apps
  apps.forEach((app, index) => {
    const item = document.createElement('div');
    item.className = 'item';
    item.tabIndex = index + 1;
    item.dataset.app = app.key;
    item.innerHTML = `
      <img src="${app.icon}" alt="${app.name}">
      ${app.name}
    `;
    appContainer.appendChild(item);

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = `overlay ${app.key}`;
    overlay.innerHTML = `<img src="${app.icon}" alt="${app.name}">`;
    overlaysContainer.appendChild(overlay);
  });

  loading.classList.add('hidden');

  // Setup cursor hiding
  if (config.display.hide_cursor_timeout > 0) {
    document.body.classList.add('show-cursor');
    resetCursorTimeout();
  }

  // Initialize selection
  if (apps.length > 0) {
    updateSelection(0);
    focusItem(0);
  }
}

// === CURSOR MANAGEMENT ===
function resetCursorTimeout() {
  document.body.classList.add('show-cursor');
  if (cursorTimeout) clearTimeout(cursorTimeout);
  if (config.display.hide_cursor_timeout > 0) {
    cursorTimeout = setTimeout(() => {
      document.body.classList.remove('show-cursor');
    }, config.display.hide_cursor_timeout);
  }
}

document.addEventListener('mousemove', resetCursorTimeout);
document.addEventListener('keydown', resetCursorTimeout);

// === NETWORK CHECK ===
async function checkNetwork() {
  if (!config.startup.check_network) return true;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    await fetch('https://www.google.com/favicon.ico?' + Date.now(), {
      mode: 'no-cors',
      signal: controller.signal
    });

    clearTimeout(timeout);
    return true;
  } catch {
    return false;
  }
}

async function updateNetworkStatus() {
  const online = await checkNetwork();
  if (online !== isOnline) {
    isOnline = online;
    offlineScreen.classList.toggle('active', !isOnline);
  }
}

// === SELECTION MANAGEMENT ===
function updateSelection(index) {
  const items = document.querySelectorAll('.item');
  const overlays = document.querySelectorAll('.overlay');

  items.forEach(i => i.classList.remove('selected'));
  overlays.forEach(o => o.classList.remove('active'));
  exitBtn.classList.remove('selected');
  settingsBtn.classList.remove('selected');

  if (index < items.length) {
    items[index].classList.add('selected');
    const app = apps[index];
    const overlay = document.querySelector(`.overlay.${app.key}`);
    if (overlay) overlay.classList.add('active');
  } else if (index === items.length) {
    settingsBtn.classList.add('selected');
  } else {
    exitBtn.classList.add('selected');
  }
}

function focusItem(index) {
  const items = document.querySelectorAll('.item');
  if (index < items.length) {
    items[index].focus();
  } else if (index === items.length) {
    settingsBtn.focus();
  } else {
    exitBtn.focus();
  }
}

// === LAUNCH APP ===
function launchApp(appKey) {
  const app = apps.find(a => a.key === appKey);
  if (!app) return;

  whiteFlash.style.opacity = '1';

  setTimeout(() => {
    window.location.href = `/launch/app/${appKey}`;
  }, 300);
}

// === CONFIRM DIALOG ===
function showConfirm(appKey) {
  const app = apps.find(a => a.key === appKey);
  if (!app) return;

  inConfirm = true;
  pendingApp = appKey;
  dialogLogo.src = app.icon;
  dialogDesc.textContent = 'This will open in full screen.';
  confirmDialog.classList.add('active');
  confirmBtn.focus();
}

function hideConfirm() {
  inConfirm = false;
  pendingApp = null;
  confirmDialog.classList.remove('active');
}

function launchConfirmed() {
  hideConfirm();
  launchApp(pendingApp);
}

confirmBtn.onclick = launchConfirmed;
cancelBtn.onclick = hideConfirm;

// === EXIT HANDLING ===
function handleExit() {
  if (config.exit.show_confirmation) {
    if (confirm('Exit Pi Media Hub?')) {
      performExit();
    }
  } else {
    performExit();
  }
}

function performExit() {
  window.location.href = '/launch/exit';
}

exitBtn.onclick = handleExit;

// === SETTINGS UI ===
function openSettings() {
  inSettings = true;
  settingsScreen.classList.add('active');
  buildSettingsUI();
}

function closeSettings() {
  inSettings = false;
  settingsScreen.classList.remove('active');
  // Restore original config if not saved
  config = JSON.parse(JSON.stringify(originalConfig));
}

function buildSettingsUI() {
  settingsGrid.innerHTML = '';

  // Apps Section
  Object.entries(config.apps).forEach(([key, app]) => {
    const card = createSettingCard(
      app.name,
      'Enable or disable this app from the main menu',
      createToggle(app.enabled, (val) => {
        config.apps[key].enabled = val;
      })
    );
    settingsGrid.appendChild(card);

    // URL setting for each app
    if (key === 'jellyfin') {
      const urlCard = createSettingCard(
        'Jellyfin Server URL',
        'Enter your Jellyfin server address',
        createTextInput(app.url, 'http://192.168.1.100:8096', (val) => {
          config.apps[key].url = val;
        })
      );
      settingsGrid.appendChild(urlCard);
    }
  });

  // Performance Mode
  settingsGrid.appendChild(createSettingCard(
    'Performance Mode',
    'Adjust animations based on your Pi model',
    createSelectButtons(
      ['low', 'balanced', 'high'],
      ['Low (Pi 4)', 'Balanced', 'High (Pi 5)'],
      config.display.performance_mode,
      (val) => {
        config.display.performance_mode = val;
      }
    )
  ));

  // Resolution Hint
  settingsGrid.appendChild(createSettingCard(
    'Resolution',
    'Display resolution optimization',
    createSelectButtons(
      ['720p', '1080p', '4k'],
      ['720p', '1080p', '4K'],
      config.display.resolution_hint,
      (val) => {
        config.display.resolution_hint = val;
      }
    )
  ));

  // CEC Support
  settingsGrid.appendChild(createSettingCard(
    'HDMI-CEC Control',
    'Enable TV power control via HDMI',
    createToggle(config.remote.enable_cec, (val) => {
      config.remote.enable_cec = val;
    })
  ));

  // Exit Action
  settingsGrid.appendChild(createSettingCard(
    'Exit Behavior',
    'What happens when you press Exit',
    createSelectButtons(
      ['cec_standby', 'close', 'shutdown', 'reboot'],
      ['TV Standby', 'Close', 'Shutdown', 'Reboot'],
      config.exit.action,
      (val) => {
        config.exit.action = val;
      }
    )
  ));

  // Auto-start
  settingsGrid.appendChild(createSettingCard(
    'Auto-start on Boot',
    'Launch media hub automatically when Pi starts',
    createToggle(config.startup.autostart, (val) => {
      config.startup.autostart = val;
    })
  ));

  // Network Check
  settingsGrid.appendChild(createSettingCard(
    'Network Monitoring',
    'Check internet connection status',
    createToggle(config.startup.check_network, (val) => {
      config.startup.check_network = val;
    })
  ));

  // Cursor Auto-hide
  settingsGrid.appendChild(createSettingCard(
    'Cursor Auto-hide',
    'Hide cursor after inactivity (seconds)',
    createSelectButtons(
      [0, 1000, 3000, 5000],
      ['Never', '1s', '3s', '5s'],
      config.display.hide_cursor_timeout,
      (val) => {
        config.display.hide_cursor_timeout = val;
      }
    )
  ));
}

// === SETTINGS UI COMPONENTS ===
function createSettingCard(label, desc, control) {
  const card = document.createElement('div');
  card.className = 'setting-card';
  card.innerHTML = `
    <div class="setting-label">${label}</div>
    <div class="setting-desc">${desc}</div>
    <div class="setting-control"></div>
  `;
  card.querySelector('.setting-control').appendChild(control);
  return card;
}

function createToggle(initialValue, onChange) {
  const toggle = document.createElement('div');
  toggle.className = 'toggle' + (initialValue ? ' on' : '');
  toggle.tabIndex = 0;
  toggle.innerHTML = '<div class="toggle-knob"></div>';

  toggle.addEventListener('click', () => {
    const newValue = !toggle.classList.contains('on');
    toggle.classList.toggle('on', newValue);
    onChange(newValue);
  });

  toggle.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      toggle.click();
      e.preventDefault();
    }
  });

  return toggle;
}

function createSelectButtons(values, labels, initialValue, onChange) {
  const container = document.createElement('div');
  container.className = 'setting-control';

  values.forEach((value, index) => {
    const btn = document.createElement('button');
    btn.className = 'select-btn' + (value === initialValue ? ' active' : '');
    btn.textContent = labels[index];
    btn.tabIndex = 0;

    btn.addEventListener('click', () => {
      container.querySelectorAll('.select-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      onChange(value);
    });

    container.appendChild(btn);
  });

  return container;
}

function createTextInput(initialValue, placeholder, onChange) {
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'text-input';
  input.value = initialValue;
  input.placeholder = placeholder;

  input.addEventListener('input', () => {
    onChange(input.value);
  });

  return input;
}

// === SETTINGS BUTTON HANDLERS ===
settingsBtn.onclick = openSettings;
settingsCloseBtn.onclick = closeSettings;
saveBtn.onclick = saveConfig;
cancelSettingsBtn.onclick = closeSettings;

// === NAVIGATION ===
document.addEventListener('keydown', (e) => {
  if (!isOnline && !['~', 'Escape'].includes(e.key)) return;

  // Debug: Toggle offline mode with ~
  if (e.key === '~') {
    isOnline = !isOnline;
    offlineScreen.classList.toggle('active', !isOnline);
    e.preventDefault();
    return;
  }

  // Settings screen navigation
  if (inSettings) {
    if (e.key === 'Escape') {
      closeSettings();
      e.preventDefault();
    }
    return; // Let normal tab/enter work in settings
  }

  if (inConfirm) {
    if (e.key === 'Escape' || e.key === 'Backspace') {
      hideConfirm();
      e.preventDefault();
      return;
    }
    if (e.key === 'Enter') {
      if (document.activeElement === confirmBtn) {
        launchConfirmed();
      } else {
        hideConfirm();
      }
      e.preventDefault();
      return;
    }
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'Tab') {
      if (document.activeElement === confirmBtn) {
        cancelBtn.focus();
      } else {
        confirmBtn.focus();
      }
      e.preventDefault();
      return;
    }
    return;
  }

  const totalItems = apps.length;
  const isInSettings = currentSelection === totalItems;
  const isInExit = currentSelection === totalItems + 1;

  if (e.key === 'ArrowDown') {
    if (isInExit) {
      currentSelection = 0;
    } else {
      currentSelection = (currentSelection + 1) % (totalItems + 2);
    }
    updateSelection(currentSelection);
    focusItem(currentSelection);
    e.preventDefault();
  } else if (e.key === 'ArrowUp') {
    if (currentSelection === 0) {
      currentSelection = totalItems + 1; // Go to exit
    } else {
      currentSelection = (currentSelection - 1);
    }
    updateSelection(currentSelection);
    focusItem(currentSelection);
    e.preventDefault();
  } else if (e.key === 'ArrowRight') {
    if (!isInSettings && !isInExit) {
      currentSelection = totalItems; // Settings
      updateSelection(currentSelection);
      focusItem(currentSelection);
      e.preventDefault();
    }
  } else if (e.key === 'ArrowLeft') {
    if (isInSettings || isInExit) {
      currentSelection = Math.min(currentSelection - 1, totalItems - 1);
      updateSelection(currentSelection);
      focusItem(currentSelection);
      e.preventDefault();
    }
  } else if (e.key === 'Enter') {
    if (currentSelection < totalItems) {
      const app = apps[currentSelection];
      showConfirm(app.key);
    } else if (isInSettings) {
      openSettings();
    } else {
      handleExit();
    }
    e.preventDefault();
  }
});

// Mouse hover
document.addEventListener('mouseover', (e) => {
  if (inConfirm || inSettings) return;

  const item = e.target.closest('.item');
  if (item) {
    const items = Array.from(document.querySelectorAll('.item'));
    const index = items.indexOf(item);
    if (index >= 0) {
      currentSelection = index;
      updateSelection(currentSelection);
    }
  } else if (e.target.closest('#settingsBtn')) {
    currentSelection = apps.length;
    updateSelection(currentSelection);
  } else if (e.target.closest('#exitBtn')) {
    currentSelection = apps.length + 1;
    updateSelection(currentSelection);
  }
});

// === ORB ANIMATION ===
function initOrbs() {
  const ctx = canvas.getContext('2d', { alpha: true });
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const perfMode = config.display.performance_mode || 'balanced';

  // Adjust orb count based on performance mode
  const orbCounts = { low: 3, balanced: 5, high: 8 };
  const orbCount = orbCounts[perfMode] || 5;

  const orbs = [];
  const baseColors = [
    'rgba(255, 0, 0, 0.04)',
    'rgba(30, 215, 96, 0.04)',
    'rgba(138, 43, 226, 0.04)'
  ];

  class Orb {
    constructor() {
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;
      this.radius = 100 + Math.random() * 150;
      this.speed = 0.2 + Math.random() * 0.4;
      this.angle = Math.random() * Math.PI * 2;
      this.color = baseColors[Math.floor(Math.random() * baseColors.length)];
    }
    update() {
      this.angle += 0.003;
      this.x += Math.cos(this.angle) * this.speed;
      this.y += Math.sin(this.angle) * this.speed;

      if (this.x > canvas.width + this.radius) this.x = -this.radius;
      if (this.x < -this.radius) this.x = canvas.width + this.radius;
      if (this.y > canvas.height + this.radius) this.y = -this.radius;
      if (this.y < -this.radius) this.y = canvas.height + this.radius;
    }
    draw() {
      const gradient = ctx.createRadialGradient(this.x, this.y, 0, this.x, this.y, this.radius);
      gradient.addColorStop(0, this.color.replace('0.04', '0.06'));
      gradient.addColorStop(1, this.color.replace('0.04', '0.00'));
      ctx.fillStyle = gradient;
      ctx.fillRect(this.x - this.radius, this.y - this.radius, this.radius * 2, this.radius * 2);
    }
  }

  for (let i = 0; i < orbCount; i++) {
    orbs.push(new Orb());
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    orbs.forEach(orb => {
      orb.update();
      orb.draw();
    });
    requestAnimationFrame(animate);
  }

  // Don't animate if performance mode is 'low'
  if (perfMode !== 'low') {
    animate();
  }

  window.addEventListener('resize', () => {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  });
}

// === STARTUP ===
async function startup() {
  await loadConfig();
  initializeUI();
  initOrbs();

  if (config.startup.check_network) {
    await updateNetworkStatus();
    setInterval(updateNetworkStatus, 5000);
  }
}

startup();
