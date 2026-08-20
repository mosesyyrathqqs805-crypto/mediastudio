const state = {
  activeTab: 'youtube',
  theme: 'dark',
  downloadFolder: '',
  cutterFolder: '',
  subtitlesFolder: '',
  selectedVideoFile: '',
  selectedAudioFile: '',
  segmentDuration: 30,
  lastYtOutputFolder: '',
  lastCutOutputFolder: '',
  lastSubOutputFolder: '',
  isDownloading: false,
  isCutting: false,
  isTranscribing: false,
  isBurning: false,

  banner: {
    path: '',
    previewUrl: '',
    posX: 50,
    posY: 82,
    widthPct: 45,
    opacity: 100
  },

  subtitles: {
    videoPath: '',
    rawSegments: [],
    segments: [],
    style: {
      font_name: 'Montserrat',
      font_size: 56,
      font_bold: true,
      text_color: '#ffffff',
      active_color: '#ffd700',
      outline_color: '#000000',
      outline_width: 4,
      position_y: 75,
      animation: 'pop',
      active_word_enabled: true
    }
  }
};

document.addEventListener('DOMContentLoaded', async () => {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  setTheme(savedTheme);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeVideoModal();
      closeCloudflareModal();
    }
  });

  const ytInput = document.getElementById('ytUrlInput');
  if (ytInput) {
    ytInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        checkVideoInfo();
      }
    });
  }

  window.addEventListener('pywebviewready', async () => {
    try {
      const defaultDir = await window.pywebview.api.get_default_download_dir();
      state.downloadFolder = defaultDir;
      state.cutterFolder = defaultDir;
      state.subtitlesFolder = defaultDir;
      document.getElementById('ytFolderDisplay').innerText = defaultDir;
      document.getElementById('cutFolderDisplay').innerText = defaultDir;
      document.getElementById('subFolderDisplay').innerText = defaultDir;

      checkCloudflareStatus();
    } catch (err) {
      console.error('Ошибка инициализации pywebview:', err);
    }
  });
});

function toggleTheme() {
  const newTheme = state.theme === 'dark' ? 'light' : 'dark';
  setTheme(newTheme);
}

function setTheme(theme) {
  state.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);

  const iconSun = document.getElementById('themeIconSun');
  const iconMoon = document.getElementById('themeIconMoon');
  if (theme === 'light') {
    iconSun.style.display = 'block';
    iconMoon.style.display = 'none';
  } else {
    iconSun.style.display = 'none';
    iconMoon.style.display = 'block';
  }
}

function switchTab(tabId) {
  state.activeTab = tabId;
  
  document.getElementById('tab-yt-btn').classList.toggle('active', tabId === 'youtube');
  document.getElementById('tab-cut-btn').classList.toggle('active', tabId === 'cutter');
  document.getElementById('tab-sub-btn').classList.toggle('active', tabId === 'subtitles');

  document.getElementById('tab-youtube').classList.toggle('active', tabId === 'youtube');
  document.getElementById('tab-cutter').classList.toggle('active', tabId === 'cutter');
  document.getElementById('tab-subtitles').classList.toggle('active', tabId === 'subtitles');

  const ytB = document.getElementById('ytSuccessBanner');
  if (ytB && ytB.style.display !== 'none') clearYouTubeWorkspace();

  const cutB = document.getElementById('cutSuccessBanner');
  if (cutB && cutB.style.display !== 'none') clearCutterWorkspace();

  const subB = document.getElementById('subSuccessBanner');
  if (subB && subB.style.display !== 'none') {
    clearSubtitlesWorkspace();
    subB.style.display = 'none';
  }
}

function hideAllSuccessBanners() {
  const b1 = document.getElementById('ytSuccessBanner');
  if (b1 && b1.style.display !== 'none') clearYouTubeWorkspace();

  const b2 = document.getElementById('cutSuccessBanner');
  if (b2 && b2.style.display !== 'none') clearCutterWorkspace();

  const b3 = document.getElementById('subSuccessBanner');
  if (b3 && b3.style.display !== 'none') {
    clearSubtitlesWorkspace();
    b3.style.display = 'none';
  }
}

function clearYouTubeWorkspace() {
  const b1 = document.getElementById('ytSuccessBanner');
  if (b1) b1.style.display = 'none';
  const inp = document.getElementById('ytUrlInput');
  if (inp) inp.value = '';
  const prog = document.getElementById('ytProgressCard');
  if (prog) prog.style.display = 'none';
  resetDownloadUI();
}

async function chooseFolder(target) {
  try {
    const selected = await window.pywebview.api.select_folder();
    if (selected) {
      if (target === 'youtube') {
        state.downloadFolder = selected;
        document.getElementById('ytFolderDisplay').innerText = selected;
      } else if (target === 'cutter') {
        state.cutterFolder = selected;
        document.getElementById('cutFolderDisplay').innerText = selected;
      } else if (target === 'subtitles') {
        state.subtitlesFolder = selected;
        document.getElementById('subFolderDisplay').innerText = selected;
      }
      hideAllSuccessBanners();
    }
  } catch (err) {
    alert('Ошибка выбора папки: ' + err);
  }
}

async function checkCloudflareStatus() {
  try {
    const cfg = await window.pywebview.api.get_cloudflare_settings();
    const badge = document.getElementById('cfStatusBadgeText');
    if (cfg.has_token) {
      badge.innerText = 'Cloudflare: Подключен';
    } else {
      badge.innerText = 'Cloudflare: Не настроен';
    }
  } catch (err) {
    console.error('Ошибка проверки Cloudflare:', err);
  }
}

async function openCloudflareModal() {
  try {
    const cfg = await window.pywebview.api.get_cloudflare_settings();
    document.getElementById('cfAccountIdInput').value = cfg.account_id || '';
    document.getElementById('cfApiTokenInput').value = cfg.api_token || '';
    
    const tokenInput = document.getElementById('cfApiTokenInput');
    tokenInput.type = 'password';
    document.getElementById('eyeIconOpen').style.display = 'none';
    document.getElementById('eyeIconClosed').style.display = 'block';

    document.getElementById('cfTestResultBox').style.display = 'none';
    document.getElementById('cloudflareModal').classList.add('active');
  } catch (err) {
    alert('Ошибка: ' + err);
  }
}

function closeCloudflareModal() {
  document.getElementById('cloudflareModal').classList.remove('active');
}

function toggleTokenVisibility() {
  const tokenInput = document.getElementById('cfApiTokenInput');
  const iconOpen = document.getElementById('eyeIconOpen');
  const iconClosed = document.getElementById('eyeIconClosed');

  if (tokenInput.type === 'password') {
    tokenInput.type = 'text';
    iconOpen.style.display = 'block';
    iconClosed.style.display = 'none';
  } else {
    tokenInput.type = 'password';
    iconOpen.style.display = 'none';
    iconClosed.style.display = 'block';
  }
}

async function testCloudflareConnection() {
  const accountId = document.getElementById('cfAccountIdInput').value.trim();
  const token = document.getElementById('cfApiTokenInput').value.trim();
  const resBox = document.getElementById('cfTestResultBox');
  const btn = document.getElementById('cfTestBtn');

  btn.disabled = true;
  btn.innerText = 'Проверка...';
  resBox.style.display = 'none';

  try {
    const res = await window.pywebview.api.test_cloudflare_connection(accountId, token);
    resBox.style.display = 'block';
    if (res.success) {
      resBox.style.background = 'rgba(16, 185, 129, 0.15)';
      resBox.style.color = 'var(--success)';
      resBox.innerText = res.message || 'Подключение успешно!';
    } else {
      resBox.style.background = 'rgba(239, 68, 68, 0.15)';
      resBox.style.color = 'var(--danger)';
      resBox.innerText = res.error || 'Ошибка проверки';
    }
  } catch (err) {
    resBox.style.display = 'block';
    resBox.style.background = 'rgba(239, 68, 68, 0.15)';
    resBox.style.color = 'var(--danger)';
    resBox.innerText = 'Ошибка: ' + err;
  } finally {
    btn.disabled = false;
    btn.innerText = 'Проверить подключение';
  }
}

async function saveCloudflareSettings() {
  const accountId = document.getElementById('cfAccountIdInput').value.trim();
  const token = document.getElementById('cfApiTokenInput').value.trim();

  if (!accountId || !token) {
    alert('Пожалуйста, заполните Account ID и API Token');
    return;
  }

  try {
    await window.pywebview.api.save_cloudflare_settings(accountId, token);
    closeCloudflareModal();
    checkCloudflareStatus();
    alert('Настройки Cloudflare успешно сохранены!');
  } catch (err) {
    alert('Ошибка сохранения: ' + err);
  }
}

function onSaveModeChange() {
  const mode = document.querySelector('input[name=saveMode]:checked').value;
  document.getElementById('saveModeFolderCard').classList.toggle('selected', mode === 'folder_split');
  document.getElementById('saveModeSingleCard').classList.toggle('selected', mode === 'single_file');
}

async function checkVideoInfo() {
  const url = document.getElementById('ytUrlInput').value.trim();
  if (!url) {
    alert('Пожалуйста, введите ссылку на видео YouTube');
    return;
  }

  const checkBtn = document.getElementById('checkVideoBtn');
  const origBtnHtml = checkBtn.innerHTML;
  checkBtn.disabled = true;
  checkBtn.innerHTML = '<span class=spinner></span><span>Проверка...</span>';

  try {
    const res = await window.pywebview.api.check_youtube_video(url);
    if (!res.success) {
      alert('Ошибка при проверке видео: ' + (res.error || 'Не удалось получить данные'));
      return;
    }

    document.getElementById('modalVideoTitle').innerText = res.title;
    document.getElementById('modalAuthor').innerText = res.uploader;
    document.getElementById('modalDurationBadge').innerText = res.duration_formatted;
    document.getElementById('modalViews').innerText = res.view_count + ' просмотров';
    document.getElementById('modalThumbImg').src = res.thumbnail || '';

    const modalSelect = document.getElementById('modalQualitySelect');
    const mainSelect = document.getElementById('ytQualitySelect');
    modalSelect.innerHTML = '';
    mainSelect.innerHTML = '';

    res.qualities.forEach(q => {
      const opt1 = document.createElement('option');
      opt1.value = q.id;
      opt1.innerText = q.label;
      modalSelect.appendChild(opt1);

      const opt2 = document.createElement('option');
      opt2.value = q.id;
      opt2.innerText = q.label;
      mainSelect.appendChild(opt2);
    });

    openVideoModal();
  } catch (err) {
    alert('Произошла ошибка: ' + err);
  } finally {
    checkBtn.disabled = false;
    checkBtn.innerHTML = origBtnHtml;
  }
}

function openVideoModal() {
  document.getElementById('videoInfoModal').classList.add('active');
}

function closeVideoModal() {
  document.getElementById('videoInfoModal').classList.remove('active');
}

function onBackdropClick(e) {
  if (e.target.id === 'videoInfoModal') closeVideoModal();
  if (e.target.id === 'cloudflareModal') closeCloudflareModal();
}

function applyModalAndDownload() {
  const selectedQuality = document.getElementById('modalQualitySelect').value;
  document.getElementById('ytQualitySelect').value = selectedQuality;
  closeVideoModal();
  startDownload();
}

async function startDownload() {
  const url = document.getElementById('ytUrlInput').value.trim();
  if (!url) {
    alert('Введите ссылку на видео YouTube');
    return;
  }

  const quality = document.getElementById('ytQualitySelect').value;
  const saveMode = document.querySelector('input[name=saveMode]:checked').value;
  const outputDir = state.downloadFolder;

  state.isDownloading = true;
  document.getElementById('downloadBtn').disabled = true;
  document.getElementById('stopDownloadBtn').disabled = false;
  document.getElementById('ytSuccessBanner').style.display = 'none';

  const progCard = document.getElementById('ytProgressCard');
  progCard.style.display = 'block';
  document.getElementById('ytProgressPercent').innerText = '0%';
  document.getElementById('ytProgressBarFill').style.width = '0%';
  document.getElementById('ytProgressStatusText').innerText = 'Инициализация...';

  try {
    await window.pywebview.api.start_youtube_download(url, quality, saveMode, outputDir);
  } catch (err) {
    alert('Ошибка запуска: ' + err);
    resetDownloadUI();
  }
}

async function stopDownload() {
  if (!state.isDownloading) return;
  document.getElementById('stopDownloadBtn').disabled = true;
  document.getElementById('ytProgressStatusText').innerText = 'Остановка...';
  try {
    await window.pywebview.api.cancel_youtube_download();
  } catch (err) {}
}

window.onYouTubeProgress = function(data) {
  if (data.percent !== undefined) {
    document.getElementById('ytProgressPercent').innerText = data.percent + '%';
    document.getElementById('ytProgressBarFill').style.width = data.percent + '%';
  }
  if (data.speed) document.getElementById('ytProgressSpeed').innerText = 'Скорость: ' + data.speed;
  if (data.downloaded && data.total) document.getElementById('ytProgressDownloaded').innerText = data.downloaded + ' / ' + data.total;
  if (data.eta) document.getElementById('ytProgressEta').innerText = 'Осталось: ' + data.eta;
  if (data.stage) document.getElementById('ytProgressStatusText').innerText = data.stage;
};

window.onYouTubeCompleted = function(res) {
  state.isDownloading = false;
  resetDownloadUI();

  if (res.cancelled) {
    document.getElementById('ytProgressCard').style.display = 'none';
    alert('Скачивание остановлено.');
    return;
  }

  if (res.success) {
    state.lastYtOutputFolder = res.target_folder;
    document.getElementById('ytProgressCard').style.display = 'none';
    const banner = document.getElementById('ytSuccessBanner');
    document.getElementById('ytSuccessMsg').innerText = res.message || 'Загрузка успешно завершена!';
    banner.style.display = 'flex';
  } else {
    alert('Ошибка скачивания: ' + (res.error || res.message));
  }
};

function resetDownloadUI() {
  state.isDownloading = false;
  document.getElementById('downloadBtn').disabled = false;
  document.getElementById('stopDownloadBtn').disabled = true;
}

function openLastFolder() {
  if (state.lastYtOutputFolder) window.pywebview.api.open_folder(state.lastYtOutputFolder);
  else if (state.downloadFolder) window.pywebview.api.open_folder(state.downloadFolder);
  clearYouTubeWorkspace();
}

function onCutModeChange() {
  const mode = document.querySelector('input[name=cutMode]:checked').value;
  document.getElementById('cutModeAutoCard').classList.toggle('selected', mode === 'auto');
  document.getElementById('cutModeManualCard').classList.toggle('selected', mode === 'manual');
  document.getElementById('cutAutoSettingsBox').style.display = mode === 'auto' ? 'block' : 'none';
  document.getElementById('cutManualSettingsBox').style.display = mode === 'manual' ? 'block' : 'none';
}

function selectSegmentDuration(seconds) {
  state.segmentDuration = seconds;
  document.querySelectorAll('.segment-chip').forEach(chip => {
    chip.classList.toggle('active', chip.innerText.includes(seconds.toString()));
  });
}

async function chooseVideoFile() {
  try {
    const file = await window.pywebview.api.select_video_file();
    if (!file) return;

    state.selectedVideoFile = file;
    document.getElementById('cutVideoTitle').innerText = file.split('/').pop();
    document.getElementById('cutVideoSub').innerText = file;
    const b = document.getElementById('cutSuccessBanner');
    if (b) b.style.display = 'none';

    const info = await window.pywebview.api.get_media_info(file);
    if (info.success) {
      document.getElementById('cutVideoMetaBox').style.display = 'flex';
      document.getElementById('cutMetaDur').innerText = info.duration_formatted;
      document.getElementById('cutMetaRes').innerText = info.resolution;
      document.getElementById('cutMetaSize').innerText = info.size_mb;
      document.getElementById('cutMetaAudio').innerText = info.has_audio ? 'Присутствует' : 'Отсутствует';
    }
  } catch (err) {
    alert('Ошибка: ' + err);
  }
}

async function chooseAudioFile() {
  try {
    const file = await window.pywebview.api.select_audio_file();
    if (!file) return;
    state.selectedAudioFile = file;
    document.getElementById('cutAudioDisplay').innerText = file.split('/').pop();
    document.getElementById('cutClearAudioBtn').style.display = 'inline-flex';
  } catch (err) {
    alert('Ошибка: ' + err);
  }
}

function clearAudioFile() {
  state.selectedAudioFile = '';
  document.getElementById('cutAudioDisplay').innerText = 'Аудиодорожка не выбрана (используется встроенный звук)';
  document.getElementById('cutClearAudioBtn').style.display = 'none';
}

async function chooseBannerFile() {
  try {
    const file = await window.pywebview.api.select_banner_file();
    if (!file) return;
    state.banner.path = file;
    const streamUrl = await window.pywebview.api.get_video_url(file);
    state.banner.previewUrl = streamUrl;

    document.getElementById('cutBannerChip').style.display = 'inline-flex';
    document.getElementById('cutBannerName').innerText = file.split('/').pop();
    document.getElementById('cutBannerControlsBox').style.display = 'block';

    const img = document.getElementById('bannerPreviewImg');
    img.src = streamUrl || file;

    updateBannerVisuals();
    initBannerDrag();
  } catch (err) {
    alert('Ошибка при выборе баннера: ' + err);
  }
}

function clearBannerFile() {
  state.banner.path = '';
  state.banner.previewUrl = '';
  document.getElementById('cutBannerChip').style.display = 'none';
  document.getElementById('cutBannerControlsBox').style.display = 'none';
  const img = document.getElementById('bannerPreviewImg');
  if (img) img.src = '';
}

function updateBannerVisuals() {
  const posX = parseInt(document.getElementById('cutBannerPosX').value, 10);
  const posY = parseInt(document.getElementById('cutBannerPosY').value, 10);
  const widthPct = parseInt(document.getElementById('cutBannerWidth').value, 10);
  const opacity = parseInt(document.getElementById('cutBannerOpacity').value, 10);

  state.banner.posX = posX;
  state.banner.posY = posY;
  state.banner.widthPct = widthPct;
  state.banner.opacity = opacity;

  document.getElementById('cutBannerPosXVal').innerText = posX;
  document.getElementById('cutBannerPosYVal').innerText = posY;
  document.getElementById('cutBannerWidthVal').innerText = widthPct;
  document.getElementById('cutBannerOpacityVal').innerText = opacity;

  const overlay = document.getElementById('bannerOverlayItem');
  if (overlay) {
    overlay.style.left = posX + '%';
    overlay.style.top = posY + '%';
    overlay.style.width = widthPct + '%';
    overlay.style.opacity = (opacity / 100).toString();
  }
}

function applyBannerPreset(preset) {
  if (preset === 'top') {
    document.getElementById('cutBannerPosX').value = 50;
    document.getElementById('cutBannerPosY').value = 10;
  } else if (preset === 'bottom') {
    document.getElementById('cutBannerPosX').value = 50;
    document.getElementById('cutBannerPosY').value = 82;
  } else if (preset === 'top_right') {
    document.getElementById('cutBannerPosX').value = 85;
    document.getElementById('cutBannerPosY').value = 8;
  } else if (preset === 'center') {
    document.getElementById('cutBannerPosX').value = 50;
    document.getElementById('cutBannerPosY').value = 50;
  }
  updateBannerVisuals();
}

let isDraggingBanner = false;
let isResizingBanner = false;
let activeResizeHandle = null;
let resizeStartX = 0;
let resizeStartWidth = 45;

function initBannerDrag() {
  const container = document.getElementById('bannerPreviewContainer');
  const overlay = document.getElementById('bannerOverlayItem');
  if (!container || !overlay || container.dataset.dragInit) return;
  container.dataset.dragInit = 'true';

  const handles = overlay.querySelectorAll('.banner-resize-handle');
  handles.forEach(handle => {
    handle.addEventListener('mousedown', (e) => {
      e.stopPropagation();
      e.preventDefault();
      isResizingBanner = true;
      activeResizeHandle = handle.dataset.handle || 'se';
      resizeStartX = e.clientX;
      resizeStartWidth = parseInt(document.getElementById('cutBannerWidth').value, 10) || 45;
    });
  });

  function onPointerMove(e) {
    if (isResizingBanner) {
      const containerRect = container.getBoundingClientRect();
      const deltaPx = e.clientX - resizeStartX;
      const factor = (activeResizeHandle === 'ne' || activeResizeHandle === 'se') ? 1 : -1;
      const deltaPct = Math.round(((deltaPx * factor * 2) / containerRect.width) * 100);
      let newWidth = resizeStartWidth + deltaPct;
      newWidth = Math.max(10, Math.min(100, newWidth));
      document.getElementById('cutBannerWidth').value = newWidth;
      updateBannerVisuals();
      return;
    }

    if (isDraggingBanner) {
      const rect = container.getBoundingClientRect();
      const clientX = e.clientX || (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      const clientY = e.clientY || (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

      let xPct = Math.round(((clientX - rect.left) / rect.width) * 100);
      let yPct = Math.round(((clientY - rect.top) / rect.height) * 100);

      xPct = Math.max(0, Math.min(100, xPct));
      yPct = Math.max(0, Math.min(100, yPct));

      document.getElementById('cutBannerPosX').value = xPct;
      document.getElementById('cutBannerPosY').value = yPct;
      updateBannerVisuals();
    }
  }

  function onPointerUp() {
    if (isDraggingBanner) {
      isDraggingBanner = false;
      overlay.style.cursor = 'grab';
    }
    if (isResizingBanner) {
      isResizingBanner = false;
      activeResizeHandle = null;
    }
  }

  overlay.addEventListener('mousedown', (e) => {
    if (e.target.classList.contains('banner-resize-handle')) return;
    isDraggingBanner = true;
    overlay.style.cursor = 'grabbing';
    e.preventDefault();
  });

  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);
}

async function startCutting() {
  if (!state.selectedVideoFile) {
    alert('Пожалуйста, выберите исходное видео');
    return;
  }

  const mode = document.querySelector('input[name=cutMode]:checked').value;
  const formatMode = document.getElementById('cutFormatSelect').value;
  const outputDir = state.cutterFolder;
  const manualText = document.getElementById('cutManualTextarea').value;

  state.isCutting = true;
  document.getElementById('startCutBtn').disabled = true;
  document.getElementById('stopCutBtn').disabled = false;
  document.getElementById('cutSuccessBanner').style.display = 'none';

  const progCard = document.getElementById('cutProgressCard');
  progCard.style.display = 'block';
  document.getElementById('cutProgressPercent').innerText = '0%';
  document.getElementById('cutProgressBarFill').style.width = '0%';
  document.getElementById('cutProgressStatusText').innerText = 'Подготовка...';

  const bannerInfo = state.banner.path ? {
    path: state.banner.path,
    pos_x: state.banner.posX,
    pos_y: state.banner.posY,
    width_pct: state.banner.widthPct,
    opacity: state.banner.opacity
  } : null;

  try {
    await window.pywebview.api.start_cutting_video(
      state.selectedVideoFile,
      state.selectedAudioFile || null,
      mode,
      state.segmentDuration,
      manualText,
      formatMode,
      outputDir,
      bannerInfo
    );
  } catch (err) {
    alert('Ошибка: ' + err);
    resetCutterUI();
  }
}

async function stopCutting() {
  if (!state.isCutting) return;
  document.getElementById('stopCutBtn').disabled = true;
  document.getElementById('cutProgressStatusText').innerText = 'Остановка...';
  try {
    await window.pywebview.api.cancel_cutting_video();
  } catch (err) {}
}

window.onCutterProgress = function(data) {
  if (data.percent !== undefined) {
    document.getElementById('cutProgressPercent').innerText = data.percent + '%';
    document.getElementById('cutProgressBarFill').style.width = data.percent + '%';
  }
  if (data.current_clip && data.total_clips) {
    document.getElementById('cutProgressCurrentClip').innerText = 'Видео ' + data.current_clip + ' из ' + data.total_clips;
  }
  if (data.message) document.getElementById('cutProgressStatusText').innerText = data.message;
};

window.onCutterCompleted = function(res) {
  state.isCutting = false;
  resetCutterUI();

  if (res.cancelled) {
    document.getElementById('cutProgressCard').style.display = 'none';
    alert('Нарезка остановлена.');
    return;
  }

  if (res.success) {
    state.lastCutOutputFolder = res.target_folder;
    document.getElementById('cutProgressCard').style.display = 'none';
    const banner = document.getElementById('cutSuccessBanner');
    document.getElementById('cutSuccessMsg').innerText = res.message || 'Нарезка завершена!';
    banner.style.display = 'flex';
  } else {
    alert('Ошибка: ' + (res.error || res.message));
  }
};

function resetCutterUI() {
  state.isCutting = false;
  document.getElementById('startCutBtn').disabled = false;
  document.getElementById('stopCutBtn').disabled = true;
}

function clearCutterWorkspace() {
  state.isCutting = false;
  state.selectedVideoFile = '';
  state.selectedAudioFile = '';
  document.getElementById('cutVideoTitle').innerText = 'Нажмите для выбора видеофайла';
  document.getElementById('cutVideoSub').innerText = 'Поддерживаются форматы MP4, MKV, MOV, WEBM';
  document.getElementById('cutVideoMetaBox').style.display = 'none';
  document.getElementById('cutAudioDisplay').innerText = 'Аудиодорожка не выбрана (используется встроенный звук)';
  document.getElementById('cutClearAudioBtn').style.display = 'none';
  document.getElementById('cutManualTextarea').value = '';
  document.getElementById('cutProgressCard').style.display = 'none';
  document.getElementById('cutProgressBarFill').style.width = '0%';
  document.getElementById('cutProgressPercent').innerText = '0%';
  document.getElementById('cutSuccessBanner').style.display = 'none';
  clearBannerFile();
  resetCutterUI();
}

function openLastCutFolder() {
  if (state.lastCutOutputFolder) window.pywebview.api.open_folder(state.lastCutOutputFolder);
  else if (state.cutterFolder) window.pywebview.api.open_folder(state.cutterFolder);
  clearCutterWorkspace();
}

async function chooseSubtitleVideoFile() {
  try {
    const file = await window.pywebview.api.select_video_file();
    if (!file) return;

    state.subtitles.videoPath = file;
    document.getElementById('subVideoTitle').innerText = file.split('/').pop();
    document.getElementById('subVideoSub').innerText = file;
    const b = document.getElementById('subSuccessBanner');
    if (b) b.style.display = 'none';

    const info = await window.pywebview.api.get_media_info(file);
    if (info.success) {
      document.getElementById('subVideoMetaBox').style.display = 'flex';
      document.getElementById('subMetaDur').innerText = info.duration_formatted;
      document.getElementById('subMetaRes').innerText = info.resolution;
      document.getElementById('subMetaAudio').innerText = info.has_audio ? 'Присутствует' : 'Отсутствует (Распознавание невозможно)';
    }

    const player = document.getElementById('subPreviewVideo');
    const streamUrl = await window.pywebview.api.get_video_url(file);
    player.src = streamUrl;
    player.load();
    setupVideoSubtitleSync();
    renderSamplePreview();
  } catch (err) {
    alert('Ошибка выбора видео: ' + err);
  }
}

async function startTranscription() {
  if (!state.subtitles.videoPath) {
    alert('Пожалуйста, сначала выберите видеофайл для создания субтитров');
    return;
  }

  const lang = document.getElementById('subLanguageSelect').value;
  const wordsPerSub = parseInt(document.getElementById('subWordsPerBlockSelect').value, 10);

  state.isTranscribing = true;
  document.getElementById('startTranscribeBtn').disabled = true;
  document.getElementById('subTranscribeProgressCard').style.display = 'block';
  document.getElementById('subTranscribePercent').innerText = '0%';
  document.getElementById('subTranscribeBarFill').style.width = '0%';
  document.getElementById('subTranscribeStatusText').innerText = 'Инициализация распознавания...';

  try {
    await window.pywebview.api.start_transcription(state.subtitles.videoPath, lang, wordsPerSub);
  } catch (err) {
    alert('Ошибка запуска транскрипции: ' + err);
    state.isTranscribing = false;
    document.getElementById('startTranscribeBtn').disabled = false;
    document.getElementById('subTranscribeProgressCard').style.display = 'none';
  }
}

window.onTranscriptionProgress = function(data) {
  if (data.percent !== undefined) {
    document.getElementById('subTranscribePercent').innerText = data.percent + '%';
    document.getElementById('subTranscribeBarFill').style.width = data.percent + '%';
  }
  if (data.message) {
    document.getElementById('subTranscribeStatusText').innerText = data.message;
  }
};

window.onTranscriptionCompleted = function(res) {
  state.isTranscribing = false;
  document.getElementById('startTranscribeBtn').disabled = false;
  document.getElementById('subTranscribeProgressCard').style.display = 'none';

  if (!res.success) {
    alert('Ошибка распознавания: ' + (res.error || 'Не удалось получить текст'));
    return;
  }

  const data = res.data || {};
  state.subtitles.fullText = data.text || '';
  state.subtitles.rawSegments = data.segments || [];
  state.subtitles.segments = data.chunked_segments || data.segments || [];

  document.getElementById('subEditorCard').style.display = 'block';
  document.getElementById('subStylesCard').style.display = 'block';
  document.getElementById('subExportCard').style.display = 'block';
  document.getElementById('subAiCard').style.display = 'block';

  renderSubtitleSegmentsList();
  updateSubStyle();
};

async function onWordsPerBlockChange() {
  if (!state.subtitles.rawSegments.length) return;
  const wordsPerSub = parseInt(document.getElementById('subWordsPerBlockSelect').value, 10);
  try {
    const chunked = await window.pywebview.api.rechunk_transcription(state.subtitles.rawSegments, wordsPerSub);
    state.subtitles.segments = chunked;
    renderSubtitleSegmentsList();
  } catch (err) {
    console.error('Ошибка переразбиения:', err);
  }
}

function renderSubtitleSegmentsList() {
  const container = document.getElementById('subSegmentsList');
  container.innerHTML = '';

  if (!state.subtitles.segments || state.subtitles.segments.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); padding:30px 16px; text-align:center; font-size:0.9rem; border:1px dashed var(--border-color); border-radius:12px;">Речь в аудиодорожке не обнаружена.<br>Нажмите «➕ Добавить фразу» вверху для ручного ввода.</div>';
    return;
  }

  state.subtitles.segments.forEach((seg, idx) => {
    const row = document.createElement('div');
    row.className = 'sub-segment-item';
    row.id = 'sub-seg-row-' + idx;

    row.innerHTML = 
      '<button class="sub-seg-play-btn" onclick="jumpToSegment(' + seg.start + ')" title="Воспроизвести с этого места">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>' +
      '</button>' +
      '<input type="text" class="sub-seg-time-input" value="' + seg.start + '" onchange="updateSegmentTime(' + idx + ', &quot;start&quot;, this.value)" title="Начало (сек)">' +
      '<span style="color:var(--text-muted); font-size:0.8rem;">-</span>' +
      '<input type="text" class="sub-seg-time-input" value="' + seg.end + '" onchange="updateSegmentTime(' + idx + ', &quot;end&quot;, this.value)" title="Конец (сек)">' +
      '<input type="text" class="sub-seg-text-input" value="' + (seg.text || '').replace(/"/g, '&quot;') + '" onchange="updateSegmentText(' + idx + ', this.value)">' +
      '<button class="sub-seg-del-btn" onclick="deleteSubtitleSegment(' + idx + ')" title="Удалить фразу">' +
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>' +
      '</button>';
    container.appendChild(row);
  });
}

function updateSegmentText(idx, newText) {
  if (state.subtitles.segments[idx]) {
    state.subtitles.segments[idx].text = newText;
  }
}

function updateSegmentTime(idx, field, val) {
  const num = parseFloat(val);
  if (!isNaN(num) && state.subtitles.segments[idx]) {
    state.subtitles.segments[idx][field] = num;
  }
}

function deleteSubtitleSegment(idx) {
  state.subtitles.segments.splice(idx, 1);
  renderSubtitleSegmentsList();
}

function addNewSubtitleSegment() {
  const lastSeg = state.subtitles.segments[state.subtitles.segments.length - 1];
  const newStart = lastSeg ? lastSeg.end + 0.2 : 0.0;
  const newEnd = newStart + 2.0;

  state.subtitles.segments.push({
    start: Math.round(newStart * 100) / 100,
    end: Math.round(newEnd * 100) / 100,
    text: 'Новая фраза',
    words: []
  });
  renderSubtitleSegmentsList();
}

function jumpToSegment(startSec) {
  const player = document.getElementById('subPreviewVideo');
  player.currentTime = startSec;
  player.play();
}

function setupVideoSubtitleSync() {
  const player = document.getElementById('subPreviewVideo');
  const overlay = document.getElementById('liveSubOverlay');

  player.ontimeupdate = () => {
    const curTime = player.currentTime;
    const activeSegIdx = state.subtitles.segments.findIndex(s => curTime >= s.start && curTime <= s.end);

    document.querySelectorAll('.sub-segment-item').forEach((item, i) => {
      item.classList.toggle('active', i === activeSegIdx);
    });

    if (activeSegIdx !== -1) {
      const seg = state.subtitles.segments[activeSegIdx];
      const words = seg.words || [];

      if (state.subtitles.style.active_word_enabled && words.length > 0) {
        overlay.innerHTML = words.map(w => {
          const isWordActive = curTime >= w.start && curTime <= w.end;
          const activeStyle = isWordActive ? `style="color:${state.subtitles.style.active_color}; transform:scale(1.15); display:inline-block;"` : '';
          return `<span class="live-sub-word ${isWordActive ? 'active' : ''}" ${activeStyle}>${w.word}</span>`;
        }).join(' ');
      } else {
        overlay.innerText = seg.text;
      }
      overlay.style.display = 'block';
    } else {
      if (player.paused && state.subtitles.segments.length === 0) {
        renderSamplePreview();
      } else {
        overlay.innerText = '';
        overlay.style.display = 'none';
      }
    }
  };

  player.onplay = () => {
    overlay.style.display = 'none';
  };
}

function renderSamplePreview() {
  const overlay = document.getElementById('liveSubOverlay');
  if (!overlay) return;
  const s = state.subtitles.style;
  if (s.active_word_enabled) {
    overlay.innerHTML = `<span class="live-sub-word">Создавай</span> <span class="live-sub-word active" style="color:${s.active_color}; transform:scale(1.15); display:inline-block;">трендовые</span> <span class="live-sub-word">Shorts</span>`;
  } else {
    overlay.innerText = 'Создавай трендовые Shorts';
  }
  overlay.style.display = 'block';
}

function applyPreset(presetName) {
  document.querySelectorAll('.preset-chip').forEach(c => c.classList.remove('active'));

  if (presetName === 'tiktok') {
    state.subtitles.style = {
      font_name: 'Montserrat',
      font_size: 56,
      font_bold: true,
      text_color: '#ffffff',
      active_color: '#ffd700',
      outline_color: '#000000',
      outline_width: 4,
      position_y: 75,
      animation: 'pop',
      active_word_enabled: true
    };
  } else if (presetName === 'mrbeast') {
    state.subtitles.style = {
      font_name: 'Impact',
      font_size: 64,
      font_bold: true,
      text_color: '#ffff00',
      active_color: '#00ffcc',
      outline_color: '#000000',
      outline_width: 6,
      position_y: 70,
      animation: 'pop',
      active_word_enabled: true
    };
  } else if (presetName === 'karaoke') {
    state.subtitles.style = {
      font_name: 'Rubik',
      font_size: 52,
      font_bold: true,
      text_color: '#ffffff',
      active_color: '#ec4899',
      outline_color: '#3b0764',
      outline_width: 4,
      position_y: 80,
      animation: 'bounce',
      active_word_enabled: true
    };
  } else if (presetName === 'minimal') {
    state.subtitles.style = {
      font_name: 'Inter',
      font_size: 46,
      font_bold: false,
      text_color: '#ffffff',
      active_color: '#6366f1',
      outline_color: '#0f172a',
      outline_width: 3,
      position_y: 82,
      animation: 'fade',
      active_word_enabled: false
    };
  }

  document.getElementById('subStyleFont').value = state.subtitles.style.font_name;
  document.getElementById('subStyleSize').value = state.subtitles.style.font_size;
  document.getElementById('subStyleSizeVal').innerText = state.subtitles.style.font_size;
  document.getElementById('subStyleTextColor').value = state.subtitles.style.text_color;
  document.getElementById('subStyleTextColorHex').innerText = state.subtitles.style.text_color.toUpperCase();
  document.getElementById('subStyleActiveColor').value = state.subtitles.style.active_color;
  document.getElementById('subStyleActiveColorHex').innerText = state.subtitles.style.active_color.toUpperCase();
  document.getElementById('subStyleOutlineColor').value = state.subtitles.style.outline_color;
  document.getElementById('subStyleOutlineWidth').value = state.subtitles.style.outline_width;
  document.getElementById('subStylePosY').value = state.subtitles.style.position_y;
  document.getElementById('subStylePosYVal').innerText = state.subtitles.style.position_y;
  document.getElementById('subStyleAnimation').value = state.subtitles.style.animation;
  document.getElementById('subStyleBold').checked = state.subtitles.style.font_bold;
  document.getElementById('subStyleActiveWord').checked = state.subtitles.style.active_word_enabled;

  updateSubStyle();
}

function updateSubStyle() {
  const font = document.getElementById('subStyleFont').value;
  const size = parseInt(document.getElementById('subStyleSize').value, 10);
  const textColor = document.getElementById('subStyleTextColor').value;
  const activeColor = document.getElementById('subStyleActiveColor').value;
  const outlineColor = document.getElementById('subStyleOutlineColor').value;
  const outlineWidth = parseInt(document.getElementById('subStyleOutlineWidth').value, 10);
  const posY = parseInt(document.getElementById('subStylePosY').value, 10);
  const animation = document.getElementById('subStyleAnimation').value;
  const bold = document.getElementById('subStyleBold').checked;
  const activeWord = document.getElementById('subStyleActiveWord').checked;

  document.getElementById('subStyleSizeVal').innerText = size;
  document.getElementById('subStylePosYVal').innerText = posY;
  document.getElementById('subStyleTextColorHex').innerText = textColor.toUpperCase();
  document.getElementById('subStyleActiveColorHex').innerText = activeColor.toUpperCase();

  state.subtitles.style = {
    font_name: font,
    font_size: size,
    font_bold: bold,
    text_color: textColor,
    active_color: activeColor,
    outline_color: outlineColor,
    outline_width: outlineWidth,
    position_y: posY,
    animation: animation,
    active_word_enabled: activeWord
  };

  const overlay = document.getElementById('liveSubOverlay');
  if (overlay) {
    overlay.style.fontFamily = "'" + font + "', sans-serif";
    overlay.style.color = textColor;
    overlay.style.fontSize = Math.round(size * 0.45) + 'px';
    overlay.style.fontWeight = bold ? '800' : '500';
    overlay.style.bottom = (100 - posY) + '%';
    overlay.style.textShadow = '0 0 ' + (outlineWidth * 2) + 'px ' + outlineColor + ', 0 2px 4px rgba(0,0,0,0.9)';

    const player = document.getElementById('subPreviewVideo');
    if (player && (player.paused || !player.currentTime)) {
      renderSamplePreview();
    }
  }
}

async function startSubtitleBurn() {
  if (!state.subtitles.videoPath || !state.subtitles.segments.length) {
    alert('Нет видео или распознанных субтитров для рендера');
    return;
  }

  const outputDir = state.subtitlesFolder;
  const qualityMode = document.getElementById('subQualityModeSelect').value;

  state.isBurning = true;
  document.getElementById('startBurnBtn').disabled = true;
  document.getElementById('stopBurnBtn').disabled = false;
  document.getElementById('subSuccessBanner').style.display = 'none';

  const progCard = document.getElementById('subBurnProgressCard');
  progCard.style.display = 'block';
  document.getElementById('subBurnPercent').innerText = '0%';
  document.getElementById('subBurnBarFill').style.width = '0%';
  document.getElementById('subBurnStatusText').innerText = 'Подготовка к рендеру...';

  try {
    await window.pywebview.api.start_subtitle_burn(
      state.subtitles.videoPath,
      state.subtitles.segments,
      state.subtitles.style,
      outputDir,
      qualityMode
    );
  } catch (err) {
    alert('Ошибка запуска: ' + err);
    resetBurnUI();
  }
}

async function stopSubtitleBurn() {
  if (!state.isBurning) return;
  document.getElementById('stopBurnBtn').disabled = true;
  document.getElementById('subBurnStatusText').innerText = 'Остановка...';
  try {
    await window.pywebview.api.cancel_subtitle_burn();
  } catch (err) {}
}

window.onBurnProgress = function(data) {
  if (data.percent !== undefined) {
    document.getElementById('subBurnPercent').innerText = data.percent + '%';
    document.getElementById('subBurnBarFill').style.width = data.percent + '%';
  }
  if (data.message) {
    document.getElementById('subBurnStatusText').innerText = data.message;
  }
};

window.onBurnCompleted = function(res) {
  state.isBurning = false;
  resetBurnUI();

  if (res.cancelled) {
    document.getElementById('subBurnProgressCard').style.display = 'none';
    alert('Рендеринг остановлен.');
    return;
  }

  if (res.success) {
    state.lastSubOutputFolder = state.subtitlesFolder;
    document.getElementById('subBurnProgressCard').style.display = 'none';
    const banner = document.getElementById('subSuccessBanner');
    document.getElementById('subSuccessMsg').innerText = res.message || 'Субтитры успешно вшиты в видео!';
    banner.style.display = 'flex';
    
    clearSubtitlesWorkspace();
  } else {
    alert('Ошибка рендера: ' + (res.error || res.message));
  }
};

function clearSubtitlesWorkspace() {
  state.subtitles.videoPath = null;
  state.subtitles.segments = [];
  state.subtitles.rawSegments = [];
  state.subtitles.fullText = '';
  
  document.getElementById('subVideoTitle').innerText = 'Нажмите для выбора видео для субтитров';
  document.getElementById('subVideoSub').innerText = 'Поддерживаются форматы MP4, MOV, WEBM, MKV';
  document.getElementById('subVideoMetaBox').style.display = 'none';
  
  const player = document.getElementById('subPreviewVideo');
  if (player) {
    player.pause();
    player.removeAttribute('src');
    player.load();
  }
  const overlay = document.getElementById('liveSubOverlay');
  if (overlay) {
    overlay.innerText = '';
    overlay.style.display = 'none';
  }
  
  const list = document.getElementById('subSegmentsList');
  if (list) list.innerHTML = '';
  
  document.getElementById('subEditorCard').style.display = 'none';
  document.getElementById('subStylesCard').style.display = 'none';
  document.getElementById('subExportCard').style.display = 'none';
  document.getElementById('subAiCard').style.display = 'none';
  document.getElementById('aiHashtagsBox').style.display = 'none';
  document.getElementById('aiDescBox').style.display = 'none';
}

function resetBurnUI() {
  state.isBurning = false;
  document.getElementById('startBurnBtn').disabled = false;
  document.getElementById('stopBurnBtn').disabled = true;
}

function openLastSubFolder() {
  if (state.lastSubOutputFolder) {
    window.pywebview.api.open_folder(state.lastSubOutputFolder);
  } else if (state.subtitlesFolder) {
    window.pywebview.api.open_folder(state.subtitlesFolder);
  }
  clearSubtitlesWorkspace();
  const b = document.getElementById('subSuccessBanner');
  if (b) b.style.display = 'none';
}

async function exportSubtitlesFile(formatType) {
  if (!state.subtitles.segments.length) {
    alert('Сначала выполните распознавание субтитров');
    return;
  }
  const baseName = (state.subtitles.videoPath.split('/').pop() || 'subtitles').replace(/\.[^/.]+$/, '');
  const defaultFileName = baseName + '.' + formatType.toLowerCase();

  try {
    const chosenPath = await window.pywebview.api.select_save_subtitle_file(defaultFileName, formatType);
    if (!chosenPath) {
      return;
    }

    const res = await window.pywebview.api.export_subtitles(
      state.subtitles.segments,
      formatType,
      chosenPath,
      state.subtitles.style
    );

    if (res.success) {
      state.lastSubOutputFolder = res.file_path;
      const banner = document.getElementById('subSuccessBanner');
      document.getElementById('subSuccessMsg').innerText = 'Файл .' + formatType.toUpperCase() + ' сохранен: ' + res.file_path;
      banner.style.display = 'flex';
      alert('Файл .' + formatType.toUpperCase() + ' успешно сохранен:\n' + res.file_path);
    } else {
      alert('Ошибка экспорта: ' + res.error);
    }
  } catch (err) {
    alert('Ошибка: ' + err);
  }
}

async function generateAiHashtags() {
  const text = state.subtitles.fullText || state.subtitles.segments.map(s => s.text).join(' ');
  if (!text.trim()) {
    alert('Сначала распознайте субтитры');
    return;
  }

  const btn = document.getElementById('genHashtagsBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:14px; height:14px; margin-right:6px; display:inline-block;"></span> Генерация...';

  try {
    const res = await window.pywebview.api.generate_ai_hashtags(text);
    if (res.success && res.hashtags) {
      document.getElementById('aiHashtagsBox').style.display = 'block';
      document.getElementById('aiHashtagsText').innerText = res.hashtags;
    } else {
      alert('Ошибка генерации хэштегов: ' + (res.error || 'Неизвестная ошибка'));
    }
  } catch (err) {
    alert('Ошибка запроса: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg> <span>✨ Сгенерировать хэштеги</span>';
  }
}

async function generateAiDescription() {
  const text = state.subtitles.fullText || state.subtitles.segments.map(s => s.text).join(' ');
  if (!text.trim()) {
    alert('Сначала распознайте субтитры');
    return;
  }

  const btn = document.getElementById('genDescBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:14px; height:14px; margin-right:6px; display:inline-block;"></span> Генерация...';

  try {
    const res = await window.pywebview.api.generate_ai_description(text);
    if (res.success && res.description) {
      document.getElementById('aiDescBox').style.display = 'block';
      document.getElementById('aiDescText').innerText = res.description;
    } else {
      alert('Ошибка генерации описания: ' + (res.error || 'Неизвестная ошибка'));
    }
  } catch (err) {
    alert('Ошибка запроса: ' + err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg> <span>📝 Сгенерировать заголовок и описание</span>';
  }
}

function copyAiHashtags() {
  const tags = document.getElementById('aiHashtagsText').innerText;
  if (!tags) return;
  navigator.clipboard.writeText(tags).then(() => {
    alert('Хэштеги скопированы в буфер обмена!');
  }).catch(() => {
    prompt('Скопируйте хэштеги вручную:', tags);
  });
}

function copyAiDescription() {
  const desc = document.getElementById('aiDescText').innerText;
  if (!desc) return;
  navigator.clipboard.writeText(desc).then(() => {
    alert('Описание и заголовки скопированы в буфер обмена!');
  }).catch(() => {
    prompt('Скопируйте текст вручную:', desc);
  });
}

function copyViralPack(packType) {
  const packs = {
    viral: '#shorts #fyp #рек #рекомендации #хочуврек #тренды #viral #топ #тикток #рилс',
    tech: '#игры #playstation #sony #пк #технологии #хакер #гаджеты #shorts #новости #девайсы',
    facts: '#факты #истории #интересно #познавательно #лайфхак #шок #shorts #секреты',
    humor: '#юмор #мемы #приколы #смешно #жиза #позитив #shorts #ржака #топ'
  };

  const text = packs[packType] || packs.viral;
  navigator.clipboard.writeText(text).then(() => {
    alert('Набор хэштегов скопирован в буфер обмена:\n\n' + text);
  }).catch(() => {
    prompt('Скопируйте хэштеги вручную:', text);
  });
}
