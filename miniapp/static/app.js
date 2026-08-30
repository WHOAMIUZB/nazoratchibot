// ============================================================
// SETUP
// ============================================================
const tg = window.Telegram ? window.Telegram.WebApp : null;
const API = "/api";
let INIT_DATA = "";
let ME = null;
const cache = { genres: null };

function applyTheme() {
  if (!tg || !tg.themeParams) return;
  const root = document.documentElement.style;
  const p = tg.themeParams;
  if (p.bg_color) root.setProperty("--tg-theme-bg-color", p.bg_color);
  if (p.secondary_bg_color) root.setProperty("--tg-theme-secondary-bg-color", p.secondary_bg_color);
  if (p.text_color) root.setProperty("--tg-theme-text-color", p.text_color);
  if (p.hint_color) root.setProperty("--tg-theme-hint-color", p.hint_color);
  if (p.link_color) root.setProperty("--tg-theme-link-color", p.link_color);
  if (p.button_color) root.setProperty("--tg-theme-button-color", p.button_color);
  if (p.button_text_color) root.setProperty("--tg-theme-button-text-color", p.button_text_color);
  if (p.section_bg_color) root.setProperty("--tg-theme-section-bg-color", p.section_bg_color);
}

function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  applyTheme();
  tg.onEvent("themeChanged", applyTheme);
  INIT_DATA = tg.initData || "";
}

// ============================================================
// API HELPERS
// ============================================================
async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    method: opts.method || "GET",
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": INIT_DATA,
    },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch (e) {}
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

function toast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2200);
}

// ============================================================
// SHEET (bottom modal)
// ============================================================
function openSheet(html) {
  document.getElementById("sheet").innerHTML = html;
  document.getElementById("sheet").classList.add("open");
  document.getElementById("sheetOverlay").classList.add("open");
}
function closeSheet() {
  document.getElementById("sheet").classList.remove("open");
  document.getElementById("sheetOverlay").classList.remove("open");
}

// ============================================================
// ROUTER
// ============================================================
const TOP_TABS = ["home", "genres", "favorites", "library", "profile"];

function navigate(tab) {
  location.hash = "#" + tab;
}
function goTo(hash) {
  location.hash = hash;
}
function goBack() {
  history.back();
}

window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", () => {
  initTelegram();
  if (!INIT_DATA) {
    document.getElementById("app").innerHTML = `
      <div class="empty-state">
        <div class="icon">📱</div>
        <div>Bu ilova faqat Telegram ilovasi ichida ishlaydi.<br>Iltimos, botdagi "Mini App" tugmasi orqali oching.</div>
      </div>`;
    return;
  }
  route();
});

async function route() {
  const hash = location.hash.replace("#", "") || "home";
  const [page, ...parts] = hash.split("/");

  document.querySelectorAll("#bottomNav button").forEach(b => {
    b.classList.toggle("active", b.dataset.tab === page);
  });

  const isRoot = TOP_TABS.includes(page);
  document.getElementById("backBtn").style.display = isRoot ? "none" : "block";
  if (tg && tg.BackButton) {
    if (isRoot) { tg.BackButton.hide(); } else { tg.BackButton.show(); }
    tg.BackButton.offClick(goBack);
    tg.BackButton.onClick(goBack);
  }

  const app = document.getElementById("app");
  app.innerHTML = `<div class="skeleton" style="height:200px"></div>`;

  try {
    switch (page) {
      case "home": setTitle("📚 Kitoblar"); await renderHome(); break;
      case "genres": setTitle("📁 Janrlar"); await renderGenres(); break;
      case "genre": setTitle("📁 Janr"); await renderGenreBooks(parts[0]); break;
      case "search": setTitle("🔎 Qidiruv"); await renderSearch(decodeURIComponent(parts[0] || "")); break;
      case "book": setTitle("📖"); await renderBookDetail(parts[0]); break;
      case "read": setTitle("📄"); await renderReader(parts[0], parseInt(parts[1] || "0")); break;
      case "favorites": setTitle("⭐ Sevimlilar"); await renderFavorites(); break;
      case "library": setTitle("📖 Kutubxonam"); await renderLibrary(parts[0] || "reading"); break;
      case "history": setTitle("🕘 Tarix"); await renderHistory(); break;
      case "profile": setTitle("👤 Profil"); await renderProfile(); break;
      case "quiz": setTitle("🎮 Viktorina"); await renderQuiz(); break;
      case "top": setTitle("🔥 TOP-10"); await renderTopFull(); break;
      default: setTitle("📚 Kitoblar"); await renderHome();
    }
  } catch (e) {
    app.innerHTML = `<div class="empty-state"><div class="icon">⚠️</div><div>Xatolik: ${escapeHtml(e.message)}</div></div>`;
  }
}

function setTitle(t) {
  document.getElementById("headerTitle").textContent = t;
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s == null ? "" : String(s);
  return d.innerHTML;
}

// ============================================================
// BOOK CARD BUILDER
// ============================================================
function bookCard(b) {
  const cover = b.has_cover
    ? `<img class="book-cover" src="${API}/books/${b.book_id}/cover?t=${encodeURIComponent(INIT_DATA)}" loading="lazy" onerror="this.outerHTML='<div class=book-cover>📖</div>'">`
    : `<div class="book-cover">📖</div>`;
  const rating = b.rating ? `⭐ ${b.rating}` : "—";
  return `
    <div class="book-card" onclick="goTo('#book/${b.book_id}')">
      ${cover}
      <div class="info">
        <div class="title">${escapeHtml(b.title)}</div>
        <div class="author">${escapeHtml(b.author || "—")}</div>
        <div class="meta">${rating} · ⬇️ ${b.downloads}</div>
      </div>
    </div>`;
}

function bookGrid(books) {
  if (!books.length) return `<div class="empty-state"><div class="icon">📭</div><div>Hech narsa topilmadi</div></div>`;
  return `<div class="book-grid">${books.map(bookCard).join("")}</div>`;
}

// ============================================================
// HOME
// ============================================================
async function renderHome() {
  const app = document.getElementById("app");
  const [me, top] = await Promise.all([api("/me"), api("/top")]);
  ME = me;

  app.innerHTML = `
    <div class="searchbar">
      <input id="searchInput" type="text" placeholder="Kitob nomi yoki muallif..." onkeydown="if(event.key==='Enter') doSearch()">
      <button onclick="doSearch()">🔎</button>
    </div>

    <div class="quick-grid">
      <div class="quick-item" onclick="navigate('genres')"><span>📁</span><small>Janrlar</small></div>
      <div class="quick-item" onclick="goTo('#top')"><span>🔥</span><small>TOP-10</small></div>
      <div class="quick-item" onclick="goTo('#quiz')"><span>🎮</span><small>Viktorina</small></div>
      <div class="quick-item" onclick="goTo('#history')"><span>🕘</span><small>Tarix</small></div>
      <div class="quick-item" onclick="openPromoSheet()"><span>🎁</span><small>Promo-kod</small></div>
      <div class="quick-item" onclick="openClub()"><span>💬</span><small>Klub</small></div>
    </div>

    <div class="section-title">🔥 TOP-10 kitoblar <small onclick="goTo('#top')">Barchasi ›</small></div>
    <div class="hscroll">${top.map(bookCard).join("") || `<div class="empty-state">Hozircha yo'q</div>`}</div>
  `;
}

async function renderTopFull() {
  const top = await api("/top");
  document.getElementById("app").innerHTML = `
    <div class="section-title">🔥 TOP-10 kitoblar</div>
    ${bookGrid(top)}
  `;
}

function doSearch() {
  const q = document.getElementById("searchInput").value.trim();
  if (q) goTo("#search/" + encodeURIComponent(q));
}

// ============================================================
// GENRES
// ============================================================
async function renderGenres() {
  if (!cache.genres) cache.genres = await api("/genres");
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="section-title">📁 Janrlarni tanlang</div>
    <div class="chip-grid">${cache.genres.map(g => `<div class="chip" onclick="goTo('#genre/${g.genre_id}')">${escapeHtml(g.name_uz)}</div>`).join("")}</div>
  `;
}

async function renderGenreBooks(genreId) {
  const sub = await api(`/genres?parent_id=${genreId}`);
  const app = document.getElementById("app");
  const subState = await api(`/genres/${genreId}/subscribed`);
  const bellBtn = `
    <button class="btn secondary full" style="margin-bottom:14px" onclick="toggleGenreSub(${genreId}, this)" data-sub="${subState.subscribed}">
      ${subState.subscribed ? "🔕 Yangi kitoblardan xabardor bo‘lishni to‘xtatish" : "🔔 Bu janrga yangi kitob qo‘shilsa, xabar bering"}
    </button>`;
  if (sub.length) {
    app.innerHTML = `
      ${bellBtn}
      <div class="section-title">📁 Subjanrlar</div>
      <div class="chip-grid">${sub.map(g => `<div class="chip" onclick="goTo('#genre/${g.genre_id}')">${escapeHtml(g.name_uz)}</div>`).join("")}</div>
    `;
    return;
  }
  const books = await api(`/genres/${genreId}/books`);
  app.innerHTML = `${bellBtn}<div class="section-title">📚 Kitoblar</div>${bookGrid(books)}`;
}

async function toggleGenreSub(genreId, btn) {
  const res = await api(`/genres/${genreId}/subscribe`, { method: "POST" });
  btn.textContent = res.subscribed ? "🔕 Yangi kitoblardan xabardor bo‘lishni to‘xtatish" : "🔔 Bu janrga yangi kitob qo‘shilsa, xabar bering";
  toast(res.subscribed ? "🔔 Obuna bo‘ldingiz" : "🔕 Obuna bekor qilindi");
}

// ============================================================
// SEARCH
// ============================================================
async function renderSearch(q) {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="searchbar">
      <input id="searchInput2" type="text" value="${escapeHtml(q)}" onkeydown="if(event.key==='Enter') doSearch2()">
      <button onclick="doSearch2()">🔎</button>
    </div>
    <div id="searchResults"><div class="skeleton" style="height:200px"></div></div>
  `;
  const results = await api(`/search?q=${encodeURIComponent(q)}`);
  document.getElementById("searchResults").innerHTML = bookGrid(results);
}
function doSearch2() {
  const q = document.getElementById("searchInput2").value.trim();
  if (q) goTo("#search/" + encodeURIComponent(q));
}

// ============================================================
// BOOK DETAIL
// ============================================================
async function renderBookDetail(bookId) {
  const b = await api(`/books/${bookId}`);
  setTitle(b.title.length > 20 ? b.title.slice(0, 20) + "…" : b.title);
  const app = document.getElementById("app");

  const cover = b.has_cover
    ? `<img class="detail-cover" src="${API}/books/${bookId}/cover" onerror="this.outerHTML='<div class=detail-cover>📖</div>'">`
    : `<div class="detail-cover">📖</div>`;

  const favLabel = b.is_favorite ? "❌ Sevimlilardan olish" : "⭐ Sevimlilarga";
  const readBtn = b.has_text
    ? `<button class="btn" onclick="goTo('#read/${bookId}/${b.progress_page || 0}')">📱 Onlayn o‘qish</button>`
    : "";
  const downloadBtn = b.is_premium
    ? `<button class="btn secondary" disabled>🔒 Premium</button>`
    : `<button class="btn secondary" onclick="downloadBook(${bookId}, '${escapeHtml(b.title).replace(/'/g, "")}')">⬇️ Yuklab olish</button>`;

  app.innerHTML = `
    ${cover}
    <div class="detail-title">${escapeHtml(b.title)}</div>
    <div class="detail-author">${escapeHtml(b.author || "Noma'lum muallif")}</div>
    <div class="detail-meta">
      <span>⭐ ${b.rating || "—"} (${b.rating_count})</span>
      <span>⬇️ ${b.downloads}</span>
      ${b.year ? `<span>📅 ${b.year}</span>` : ""}
    </div>
    <div class="detail-desc">${escapeHtml(b.description || "Tavsif mavjud emas.")}</div>

    <div class="btn-row">
      ${readBtn}
      ${downloadBtn}
    </div>
    <div class="btn-row">
      <button class="btn secondary" onclick="toggleFavorite(${bookId})" id="favBtn">${favLabel}</button>
      <button class="btn secondary" onclick="openShelfSheet(${bookId})">📚 Javonga</button>
    </div>
    <div class="btn-row">
      <button class="btn secondary full" onclick="openRateSheet(${bookId}, ${b.already_reviewed})">🌟 Baholash</button>
    </div>

    <div id="similarBlock"></div>
    <div class="section-title">🌟 Sharhlar</div>
    <div id="reviewsBlock"><div class="skeleton" style="height:80px"></div></div>
  `;

  api(`/books/${bookId}/similar`).then(sim => {
    if (sim.length) {
      document.getElementById("similarBlock").innerHTML = `
        <div class="section-title">🔁 O‘xshash kitoblar</div>
        <div class="hscroll">${sim.map(bookCard).join("")}</div>
      `;
    }
  });

  api(`/books/${bookId}/reviews`).then(reviews => {
    document.getElementById("reviewsBlock").innerHTML = reviews.length
      ? reviews.map(r => `
          <div class="review-item">
            <div class="review-user">${escapeHtml(r.user)} <span class="review-stars">${"⭐".repeat(r.rating)}</span></div>
            ${r.text ? `<div class="review-text">${escapeHtml(r.text)}</div>` : ""}
          </div>`).join("")
      : `<div class="empty-state"><div class="icon">💭</div><div>Hali sharhlar yo‘q</div></div>`;
  });
}

async function toggleFavorite(bookId) {
  const res = await api(`/books/${bookId}/favorite`, { method: "POST" });
  document.getElementById("favBtn").textContent = res.is_favorite ? "❌ Sevimlilardan olish" : "⭐ Sevimlilarga";
  toast(res.is_favorite ? "Sevimlilarga qo‘shildi ⭐" : "Sevimlilardan olindi");
}

async function downloadBook(bookId, title) {
  toast("Yuklab olinmoqda...");
  try {
    const res = await fetch(`${API}/books/${bookId}/download`, {
      headers: { "X-Telegram-Init-Data": INIT_DATA },
    });
    if (!res.ok) throw new Error("Yuklab bo'lmadi");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = title || "kitob";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("✅ Yuklab olindi");
  } catch (e) {
    toast("❌ Xatolik: " + e.message);
  }
}

function openShelfSheet(bookId) {
  openSheet(`
    <h3>📚 Qaysi javonga qo‘shamiz?</h3>
    <button class="btn full" style="margin-bottom:8px" onclick="setShelf(${bookId},'reading')">📗 O‘qilmoqda</button>
    <button class="btn full secondary" style="margin-bottom:8px" onclick="setShelf(${bookId},'read')">✅ O‘qib bo‘lingan</button>
    <button class="btn full secondary" onclick="setShelf(${bookId},'planned')">🕓 Rejadagi</button>
  `);
}
async function setShelf(bookId, status) {
  await api(`/books/${bookId}/shelf`, { method: "POST", body: { status } });
  closeSheet();
  toast("✅ Javon yangilandi");
}

function openRateSheet(bookId, alreadyReviewed) {
  if (alreadyReviewed) {
    toast("Siz bu kitobni allaqachon baholagansiz");
    return;
  }
  openSheet(`
    <h3>🌟 Kitobni baholang</h3>
    <div class="star-picker" id="starPicker">
      ${[1,2,3,4,5].map(i => `<span data-v="${i}" onclick="pickStar(${i})">⭐</span>`).join("")}
    </div>
    <textarea id="reviewText" placeholder="Izoh (ixtiyoriy)..."></textarea>
    <button class="btn full" onclick="submitReview(${bookId})">Yuborish</button>
  `);
  window._selectedStars = 0;
}
function pickStar(n) {
  window._selectedStars = n;
  document.querySelectorAll("#starPicker span").forEach(el => {
    el.classList.toggle("on", parseInt(el.dataset.v) <= n);
  });
}
async function submitReview(bookId) {
  if (!window._selectedStars) { toast("Baho tanlang"); return; }
  const text = document.getElementById("reviewText").value.trim();
  try {
    const res = await api(`/books/${bookId}/review`, { method: "POST", body: { rating: window._selectedStars, text: text || null } });
    closeSheet();
    toast(`✅ Rahmat! +${res.xp} XP`);
    route();
  } catch (e) {
    toast("❌ " + e.message);
  }
}

// ============================================================
// READER
// ============================================================
async function renderReader(bookId, page) {
  const data = await api(`/books/${bookId}/text?page=${page}`);
  setTitle(data.title.length > 18 ? data.title.slice(0, 18) + "…" : data.title);
  document.getElementById("app").innerHTML = `
    <div class="reader-text">${escapeHtml(data.text)}</div>
    <div class="reader-nav">
      <button class="btn secondary" ${data.page <= 0 ? "disabled" : ""} onclick="goTo('#read/${bookId}/${data.page - 1}')">⬅️ Oldingi</button>
      <span class="reader-page-indicator">${data.page + 1} / ${data.total_pages}</span>
      <button class="btn secondary" ${data.page >= data.total_pages - 1 ? "disabled" : ""} onclick="goTo('#read/${bookId}/${data.page + 1}')">Keyingi ➡️</button>
    </div>
  `;
}

// ============================================================
// FAVORITES / LIBRARY / HISTORY
// ============================================================
async function renderFavorites() {
  const favs = await api("/favorites");
  document.getElementById("app").innerHTML = bookGrid(favs);
}

async function renderLibrary(tab) {
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="tab-bar">
      <button class="${tab === "reading" ? "active" : ""}" onclick="goTo('#library/reading')">📗 O‘qilmoqda</button>
      <button class="${tab === "read" ? "active" : ""}" onclick="goTo('#library/read')">✅ O‘qilgan</button>
      <button class="${tab === "planned" ? "active" : ""}" onclick="goTo('#library/planned')">🕓 Reja</button>
    </div>
    <div id="libraryBooks"><div class="skeleton" style="height:200px"></div></div>
  `;
  const books = await api(`/shelf?status=${tab}`);
  document.getElementById("libraryBooks").innerHTML = bookGrid(books);
}

async function renderHistory() {
  const hist = await api("/history");
  const app = document.getElementById("app");
  if (!hist.length) {
    app.innerHTML = `<div class="empty-state"><div class="icon">🕘</div><div>Tarix bo‘sh</div></div>`;
    return;
  }
  const actionLabels = { view: "👁 Ko‘rdi", download: "⬇️ Yukladi", read: "📖 O‘qidi" };
  app.innerHTML = hist.map(h => {
    const label = h.action.startsWith("search:")
      ? `🔎 Qidirdi: "${escapeHtml(h.action.slice(7))}"`
      : (actionLabels[h.action] || h.action);
    return `
      <div class="list-item" ${h.book_id ? `onclick="goTo('#book/${h.book_id}')"` : ""}>
        <div>
          <div>${label}</div>
          ${h.title ? `<div class="sub">${escapeHtml(h.title)}</div>` : ""}
        </div>
        <div class="sub">${(h.ts || "").slice(5, 16).replace("T", " ")}</div>
      </div>`;
  }).join("");
}

// ============================================================
// PROFILE
// ============================================================
async function renderProfile() {
  const me = await api("/me");
  ME = me;
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="profile-card">
      <div class="profile-avatar">👤</div>
      <div class="profile-name">${escapeHtml(me.first_name || "Foydalanuvchi")}</div>
      <div class="profile-xp">💎 ${me.xp} XP</div>
      <div class="stat-row">
        <div><div class="num">${me.favorites_count}</div><div class="label">Sevimli</div></div>
        <div><div class="num">${me.read_count}</div><div class="label">O‘qilgan</div></div>
      </div>
    </div>

    <div class="section-title">🌐 Til</div>
    <div class="lang-row">
      <button class="${me.language === "uz" ? "active" : ""}" onclick="setLang('uz')">🇺🇿 O‘zbek</button>
      <button class="${me.language === "ru" ? "active" : ""}" onclick="setLang('ru')">🇷🇺 Рус</button>
      <button class="${me.language === "en" ? "active" : ""}" onclick="setLang('en')">🇬🇧 Eng</button>
    </div>

    <div class="section-title">⚙️ Sozlamalar</div>
    <div class="toggle-row">
      <span>🔔 Kunlik o‘qish eslatmasi</span>
      <label class="switch">
        <input type="checkbox" id="reminderToggle" ${me.reminder_enabled ? "checked" : ""} onchange="toggleReminder(this.checked)">
        <span class="slider"></span>
      </label>
    </div>
    <div class="toggle-row">
      <span>🕐 Eslatma vaqti (UTC)</span>
      <select id="reminderHour" onchange="changeReminderHour(this.value)" style="padding:8px; border-radius:8px; background:var(--card); color:var(--text); border:1px solid var(--border)">
        ${Array.from({length: 24}, (_, h) => `<option value="${h}" ${h === me.reminder_hour ? "selected" : ""}>${String(h).padStart(2,"0")}:00</option>`).join("")}
      </select>
    </div>

    <div class="section-title">👥 Do‘stlarni taklif qiling</div>
    <div class="list-item" style="flex-direction:column; align-items:stretch; gap:8px">
      <div class="sub">Har bir taklif qilingan do‘stingiz uchun XP olasiz</div>
      <div class="btn-row" style="margin:0">
        <button class="btn secondary" onclick="copyReferral('${me.referral_link}')">📋 Nusxalash</button>
        <button class="btn" onclick="shareReferral('${me.referral_link}')">📤 Ulashish</button>
      </div>
    </div>

    <div class="section-title">🔗 Boshqa</div>
    <div class="btn-row">
      <button class="btn secondary" onclick="goTo('#history')">🕘 Tarix</button>
      <button class="btn secondary" onclick="openPromoSheet()">🎁 Promo-kod</button>
    </div>
    <div class="btn-row">
      <button class="btn secondary" onclick="openClub()">💬 Kitobxonlar klubi</button>
      <button class="btn secondary" onclick="openFeedbackSheet()">✍️ Fikr bildirish</button>
    </div>
  `;
}

async function changeReminderHour(hour) {
  const enabled = document.getElementById("reminderToggle").checked;
  await api("/reminder", { method: "POST", body: { enabled, hour: parseInt(hour) } });
  toast("✅ Eslatma vaqti yangilandi");
}

function copyReferral(link) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(link).then(() => toast("📋 Havola nusxalandi"));
  } else {
    toast(link);
  }
}

function shareReferral(link) {
  const text = "Kitoblar botiga qo‘shiling! 📚";
  if (tg && tg.switchInlineQuery) {
    // ichki ulashish imkoni bo'lmasa, oddiy Telegram share havolasidan foydalanamiz
  }
  const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(link)}&text=${encodeURIComponent(text)}`;
  if (tg && tg.openTelegramLink) {
    tg.openTelegramLink(shareUrl);
  } else {
    window.open(shareUrl, "_blank");
  }
}

async function setLang(lang) {
  await api("/language", { method: "POST", body: { lang } });
  toast("✅ Til o‘zgartirildi");
  renderProfile();
}

async function toggleReminder(enabled) {
  await api("/reminder", { method: "POST", body: { enabled } });
  toast(enabled ? "🔔 Eslatma yoqildi" : "🔕 Eslatma o‘chirildi");
}

function openClub() {
  api("/me").then(me => {
    if (tg && tg.openTelegramLink && me.club_link.includes("t.me")) {
      tg.openTelegramLink(me.club_link);
    } else if (tg && tg.openLink) {
      tg.openLink(me.club_link);
    } else {
      window.open(me.club_link, "_blank");
    }
  });
}

function openPromoSheet() {
  openSheet(`
    <h3>🎁 Promo-kod</h3>
    <input type="text" id="promoInput" placeholder="Kodni kiriting...">
    <button class="btn full" onclick="submitPromo()">Faollashtirish</button>
  `);
}
async function submitPromo() {
  const code = document.getElementById("promoInput").value.trim();
  if (!code) return;
  const res = await api("/promo/redeem", { method: "POST", body: { code } });
  closeSheet();
  const messages = {
    ok: `✅ Muvaffaqiyatli! +${res.xp} XP`,
    not_found: "❌ Bunday kod topilmadi",
    exhausted: "❌ Kod muddati tugagan",
    already_used: "❌ Siz bu kodni allaqachon ishlatgansiz",
  };
  toast(messages[res.status] || "Xatolik");
  if (res.status === "ok") renderProfile();
}

function openFeedbackSheet() {
  openSheet(`
    <h3>✍️ Fikr-mulohaza</h3>
    <textarea id="feedbackText" placeholder="Taklif, shikoyat yoki muammoingizni yozing..."></textarea>
    <button class="btn full" onclick="submitFeedback()">Yuborish</button>
  `);
}
async function submitFeedback() {
  const text = document.getElementById("feedbackText").value.trim();
  if (!text) return;
  await api("/feedback", { method: "POST", body: { text } });
  closeSheet();
  toast("🙏 Rahmat! Xabaringiz yuborildi");
}

// ============================================================
// QUIZ
// ============================================================
async function renderQuiz() {
  const app = document.getElementById("app");
  const q = await api("/quiz/random");
  if (!q) {
    app.innerHTML = `<div class="empty-state"><div class="icon">🎮</div><div>Hozircha savollar yo‘q</div></div>`;
    return;
  }
  app.innerHTML = `
    <div class="quiz-question">${escapeHtml(q.question)}</div>
    <div class="quiz-options" id="quizOptions">
      ${Object.entries(q.options).map(([k, v]) => `
        <button class="quiz-option" data-key="${k}" onclick="answerQuiz(${q.id}, '${k}')">${escapeHtml(v)}</button>
      `).join("")}
    </div>
  `;
}

async function answerQuiz(questionId, chosen) {
  document.querySelectorAll(".quiz-option").forEach(b => b.onclick = null);
  const res = await api(`/quiz/${questionId}/answer`, { method: "POST", body: { chosen } });
  document.querySelectorAll(".quiz-option").forEach(b => {
    if (b.dataset.key === res.correct_option) b.classList.add("correct");
    else if (b.dataset.key === chosen) b.classList.add("wrong");
  });
  toast(res.correct ? `✅ To‘g‘ri! +${res.xp} XP` : `❌ Noto‘g‘ri`);
  setTimeout(() => {
    const app = document.getElementById("app");
    app.insertAdjacentHTML("beforeend", `<button class="btn full" style="margin-top:16px" onclick="renderQuiz()">Keyingi savol ➡️</button>`);
  }, 400);
}
