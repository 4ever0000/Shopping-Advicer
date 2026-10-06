(function () {
  if (document.getElementById("sa-floating-btn")) return;

  // HTML escape: skreyp olunmuş mətn, URL və istifadəçi girişi innerHTML-ə düşməzdən əvvəl
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Yalnız http/https linklərinə icazə verir (javascript:, data: və s. bloklanır)
  function safeUrl(url, fallback) {
    const fb = fallback === undefined ? "" : fallback;
    if (!url) return fb;
    const u = String(url).trim();
    return /^https?:\/\//i.test(u) ? u : fb;
  }

  // Səhifə başlığında sayt adı olan hissələr (məhsul adı deyil)
  const SITE_NAMES = [
    "birmarket", "umico", "alinino", "trendyol", "amazon", "ebay", "aliexpress",
    "kontakt", "kontakthome", "irshad", "irsad", "bakuelectronics", "temu",
  ];

  // "Məhsul ✅ qiymət | Birmarket" -> "Məhsul ✅ qiymət" (sayt adı hissəsini atır)
  function pickTitlePart(text) {
    const parts = String(text || "")
      .split(/\s*[|•·]\s*/)
      .map((p) => p.trim())
      .filter(Boolean);
    for (const p of parts) {
      const letters = p.toLowerCase().replace(/[^a-z0-9]/g, "");
      if (!SITE_NAMES.includes(letters)) return p;
    }
    return String(text || "");
  }

  //       Köhnə davranışı istəyirsənsə UNITS sətrinə "|gb|tb|mah|w|hz" əlavə et.
  const UNITS = "ml|l|g|kg|cm|mm|m|oz";
  const UNITS_RE = new RegExp("\\b\\d+\\s*(" + UNITS + ")\\b", "gi");

  function cleanProductTitle(text) {
    if (!text) return "";
    return pickTitlePart(text)
      .replace(/^ᐈ\s*/, "")
      .replace(/[\u2705\u2662\u2B50\u2714\u2764\uFE0F]/g, "") // ✅ ♢ ⭐ ✔ ❤ və emoji seçicisi
      .replace(/\(.*?\)|\[.*?\]/g, "")
      .replace(UNITS_RE, "")
      .replace(/\b(edt|edp|cologne|parfum|parfüm|eau de|essence|refill|tester)\b/gi, "")
      .replace(/Книга|автор|Fiyatı|Yorumları|Satın al|Qiym[əe]ti|Satış[ıi]|Satisi/gi, "")
      .replace(/\s+/g, " ")
      .replace(/\s+(və|ve|and)\s*$/i, "")
      .replace(/^[\s,\-–—]+|[\s,\-–—]+$/g, "")
      .trim();
  }

  // <PURE-END>

  // Əvvəlki sessiyalardan qalmış (escape olunmamış) tarixçəni təmizləyir
  function sanitizeHistory(html) {
    const tpl = document.createElement("template");
    tpl.innerHTML = html;
    tpl.content
      .querySelectorAll("script, iframe, object, embed, link, style, meta, base, form")
      .forEach((n) => n.remove());
    tpl.content.querySelectorAll("*").forEach((el) => {
      Array.from(el.attributes).forEach((attr) => {
        const name = attr.name.toLowerCase();
        const val = (attr.value || "").trim().toLowerCase();
        if (name.startsWith("on")) {
          el.removeAttribute(attr.name);
        } else if (
          (name === "href" || name === "src" || name === "xlink:href" || name === "action") &&
          !/^https?:\/\//.test(val) &&
          !val.startsWith("chrome-extension://") &&
          val !== "#"
        ) {
          el.removeAttribute(attr.name);
        }
      });
      if (el.tagName === "A") {
        el.setAttribute("rel", "noopener noreferrer");
      }
    });
    const holder = document.createElement("div");
    holder.appendChild(tpl.content.cloneNode(true));
    return holder.innerHTML;
  }

  // ===================================================================
  // 1. Üzən Kelebek Bulutsusu Düyməsi (Draggable)
  // ===================================================================
  const floatBtn = document.createElement("div");
  floatBtn.id = "sa-floating-btn";

  const nebulaImg = document.createElement("img");
  nebulaImg.src = chrome.runtime.getURL("images/nebula.jpeg");
  nebulaImg.id = "sa-nebula-img";

  floatBtn.appendChild(nebulaImg);
  document.body.appendChild(floatBtn);

  // Düymənin Sürüşdürülməsi (Drag) və Klik Məntiqi
  let isDraggingBtn = false;
  let startX = 0, startY = 0;
  let initialLeft = 0, initialTop = 0;
  let hasMoved = false;

  floatBtn.addEventListener("mousedown", (e) => {
    isDraggingBtn = true;
    hasMoved = false;
    startX = e.clientX;
    startY = e.clientY;

    const rect = floatBtn.getBoundingClientRect();
    initialLeft = rect.left;
    initialTop = rect.top;

    floatBtn.style.right = "auto";
    floatBtn.style.bottom = "auto";
    floatBtn.style.left = initialLeft + "px";
    floatBtn.style.top = initialTop + "px";
    
    e.preventDefault();
  });

  document.addEventListener("mousemove", (e) => {
    if (!isDraggingBtn) return;

    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      hasMoved = true;
    }

    floatBtn.style.left = (initialLeft + dx) + "px";
    floatBtn.style.top = (initialTop + dy) + "px";
  });

  document.addEventListener("mouseup", () => {
    isDraggingBtn = false;
  });

  floatBtn.addEventListener("click", (e) => {
    // Əgər düymə sürüşdürülübsə, çat pəncərəsinin açılmasının qarşısını alırıq
    if (hasMoved) {
      e.stopPropagation();
      return;
    }
    chatWindow.style.display = chatWindow.style.display === "flex" ? "none" : "flex";
  });

  // ===================================================================
  // 2. Çat Pəncərəsinin Yaradılması
  // ===================================================================
  const chatWindow = document.createElement("div");
  chatWindow.id = "sa-chat-window";
  chatWindow.innerHTML = `
    <div id="sa-chat-header">
      <div class="sa-header-tabs">
        <button id="sa-tab-search" class="sa-tab-btn active">🔍 Axtarış</button>
        <button id="sa-tab-saved" class="sa-tab-btn">🔖 Yadda Saxlanılanlar</button>
      </div>
      <div class="sa-header-actions">
        <button id="sa-clear-btn" title="Tarixçəni Təmizlə">🗑️</button>
        <button id="sa-close-btn" title="Bağla">&times;</button>
      </div>
    </div>

    <!-- 1. Axtarış Bölməsi (Əsas View) -->
    <div id="sa-search-view" class="sa-view-container">
      <div id="sa-chat-box"></div>
      
      <!-- Sürüşdürülən Məhsulun Ön Baxış / Qeydiyyat Sahəsi -->
      <div id="sa-drop-preview" style="display: none;">
        <div class="sa-preview-content">
          <img id="sa-preview-img" src="" alt="Dropped Product" />
          <div class="sa-preview-inputs">
            <input type="text" id="sa-preview-title" placeholder="Məhsul adı..." />
            <div class="sa-category-select-wrapper">
              <select id="sa-preview-category"></select>
              <input type="text" id="sa-preview-new-category" placeholder="Yeni kateqoriya yazın..." style="display: none;" />
            </div>
            <textarea id="sa-preview-note" placeholder="Niyə almaq istəyirsiniz? (Qeyd tutun...)"></textarea>
          </div>
        </div>
        <div class="sa-preview-actions">
          <button id="sa-drop-search-btn">🔍 Axtar</button>
          <button id="sa-drop-save-btn">💾 Yadda Saxla</button>
        </div>
      </div>

      <div id="sa-input-area">
        <input type="text" id="sa-productInput" placeholder="Məhsul adı..." />
        <button id="sa-searchBtn">Tap</button>
      </div>
    </div>

    <!-- 2. Yadda Saxlanılanlar Bölməsi (Baku Electronics Stilində Layout) -->
    <div id="sa-saved-view" class="sa-view-container" style="display: none;">
      <div id="sa-saved-layout">
        <!-- Sol Tərəf: Kateqoriyalar Sidebar -->
        <div id="sa-categories-sidebar">
          <div class="sa-sidebar-header">Kateqoriyalar</div>
          <ul id="sa-categories-list"></ul>
        </div>
        <!-- Sağ Tərəf: Məhsul Kartları Grid -->
        <div id="sa-saved-products-grid">
          <div class="sa-empty-state">Hələ ki, yadda saxlanılan məhsul yoxdur.</div>
        </div>
      </div>
    </div>
  `;
  document.body.appendChild(chatWindow);

  const chatBox = document.getElementById("sa-chat-box");
  const productInput = document.getElementById("sa-productInput");
  const searchBtn = document.getElementById("sa-searchBtn");
  const closeBtn = document.getElementById("sa-close-btn");
  const clearBtn = document.getElementById("sa-clear-btn");

  // --- Element Referansları ---
  const tabSearch = document.getElementById("sa-tab-search");
  const tabSaved = document.getElementById("sa-tab-saved");
  const searchView = document.getElementById("sa-search-view");
  const savedView = document.getElementById("sa-saved-view");

  const previewCategorySelect = document.getElementById("sa-preview-category");
  const previewNewCategoryInput = document.getElementById("sa-preview-new-category");
  const previewNoteInput = document.getElementById("sa-preview-note");
  const dropSaveBtn = document.getElementById("sa-drop-save-btn");

  const categoriesList = document.getElementById("sa-categories-list");
  const savedProductsGrid = document.getElementById("sa-saved-products-grid");

  let currentSelectedCategoryId = null;

  // Tab Keçid Məntiqi
  tabSearch.addEventListener("click", () => {
    tabSearch.classList.add("active");
    tabSaved.classList.remove("active");
    searchView.style.display = "flex";
    savedView.style.display = "none";
  });

  tabSaved.addEventListener("click", () => {
    tabSaved.classList.add("active");
    tabSearch.classList.remove("active");
    searchView.style.display = "none";
    savedView.style.display = "flex";
    loadCategoriesAndProducts();
  });

  // Kateqoriya Seçimi Dəyişdikdə ("+ Yeni Kateqoriya" seçilərsə)
  previewCategorySelect.addEventListener("change", () => {
    if (previewCategorySelect.value === "__NEW__") {
      previewNewCategoryInput.style.display = "block";
      previewNewCategoryInput.focus();
    } else {
      previewNewCategoryInput.style.display = "none";
    }
  });

  // Kateqoriyaları Dropdown-a Yükləmək Funksiyası
  async function loadCategoryOptions() {
    try {
      const res = await fetch("http://localhost:8081/api/saved-products/categories");
      const categories = await res.json();

      previewCategorySelect.innerHTML = `<option value="">-- Kateqoriya Seçin --</option>`;
      categories.forEach((cat) => {
        previewCategorySelect.innerHTML += `<option value="${esc(cat.name)}">${esc(cat.name)}</option>`;
      });
      previewCategorySelect.innerHTML += `<option value="__NEW__">➕ Yeni Kateqoriya Yarat...</option>`;
    } catch (err) {
      console.error("Kateqoriyaları yükləyərkən xəta:", err);
    }
  }

  // Baku Electronics Stilində: Kateqoriya və Məhsulları Yükləyən Funksiya
  async function loadCategoriesAndProducts() {
    try {
      const resCat = await fetch("http://localhost:8081/api/saved-products/categories");
      const categories = await resCat.json();

      categoriesList.innerHTML = `<li class="sa-cat-item ${!currentSelectedCategoryId ? "active" : ""}" data-id="ALL">Bütün Məhsullar</li>`;

      categories.forEach((cat) => {
        const isActive = currentSelectedCategoryId === cat.id ? "active" : "";
        categoriesList.innerHTML += `<li class="sa-cat-item ${isActive}" data-id="${cat.id}">${esc(cat.name)}</li>`;
      });

      // Sidebar klik hadisəsi
      document.querySelectorAll(".sa-cat-item").forEach((item) => {
        item.addEventListener("click", (e) => {
          document.querySelectorAll(".sa-cat-item").forEach((el) => el.classList.remove("active"));
          e.target.classList.add("active");

          const catId = e.target.getAttribute("data-id");
          currentSelectedCategoryId = catId === "ALL" ? null : catId;
          fetchAndDisplaySavedProducts();
        });
      });

      fetchAndDisplaySavedProducts();
    } catch (err) {
      console.error("Bazar məlumatları yüklənərkən xəta:", err);
    }
  }

  // Yadda Saxlanılan Məhsulları Sol Kateqoriyaya Uyğun Gətirmək
  async function fetchAndDisplaySavedProducts() {
    const url = currentSelectedCategoryId
      ? `http://localhost:8081/api/saved-products/category/${currentSelectedCategoryId}`
      : "http://localhost:8081/api/saved-products";

    try {
      const res = await fetch(url);
      const products = await res.json();

      if (!products || products.length === 0) {
        savedProductsGrid.innerHTML = `<div class="sa-empty-state">Bu kateqoriyada yadda saxlanılan məhsul tapılmadı.</div>`;
        return;
      }

      savedProductsGrid.innerHTML = products
        .map(
          (prod) => `
        <div class="sa-saved-card">
          <button class="sa-delete-saved-btn" data-id="${prod.id}" title="Məhsulu sil">&times;</button>
          <img src="${esc(safeUrl(prod.imageUrl, ""))}" alt="${esc(prod.customTitle)}" referrerpolicy="no-referrer"/>
          <div class="sa-saved-card-body">
            <div class="sa-saved-card-title">${esc(prod.customTitle)}</div>
            ${prod.price ? `<div class="sa-saved-card-price">🏷️ ${esc(prod.price)} AZN</div>` : ""}
            <span class="sa-saved-card-badge">${esc(prod.categoryName || "Ümumi")}</span>
            ${prod.note ? `<div class="sa-saved-card-note"><b>Niyə almaq istəyirəm:</b> ${esc(prod.note)}</div>` : ""}
            <a href="${esc(safeUrl(prod.sourceUrl, "#"))}" target="_blank" rel="noopener noreferrer" class="sa-card-link">Səhifəyə Keç ➔</a>
          </div>
        </div>
      `
        )
        .join("");

      // Silmə Düymələrinin Məntiqi
      document.querySelectorAll(".sa-delete-saved-btn").forEach((btn) => {
        btn.addEventListener("click", async (e) => {
          const id = e.target.getAttribute("data-id");
          if (confirm("Bu məhsulu yadda saxlanılanlardan silmək istəyirsiniz?")) {
            await fetch(`http://localhost:8081/api/saved-products/${id}`, { method: "DELETE" });
            fetchAndDisplaySavedProducts();
          }
        });
      });
    } catch (err) {
      console.error("Yadda saxlanılan məhsullar yüklənərkən xəta:", err);
    }
  }

  // Məhsulu Bazaya (Java Spring Boot-a) Saxlayan "Yadda Saxla" Klik Hadisəsi
  dropSaveBtn.addEventListener("click", async () => {
    const title = previewTitle.value.trim();
    if (!title) {
      alert("Xahiş olunur məhsul adını daxil edin!");
      return;
    }

    let finalCategory = previewCategorySelect.value;
    if (finalCategory === "__NEW__") {
      finalCategory = previewNewCategoryInput.value.trim();
    }

    const payload = {
      customTitle: title,
      imageUrl: previewImg.src,
      sourceUrl: window.location.href,
      note: previewNoteInput.value.trim(),
      categoryName: finalCategory || "Ümumi",
    };

    try {
      const res = await fetch("http://localhost:8081/api/saved-products", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        dropPreview.style.display = "none";
        previewNoteInput.value = "";
        previewNewCategoryInput.value = "";
        previewNewCategoryInput.style.display = "none";
        appendMessage(`✅ <b>"${esc(title)}"</b> uğurla Yadda Saxlanılanlara əlavə edildi!`, "bot");
      } else {
        alert("Xəta baş verdi, yenidən cəhd edin.");
      }
    } catch (err) {
      console.error("Saxlama zamanı xəta:", err);
      alert("Serverlə əlaqə qurularkən xəta yarandı.");
    }
  });

  let isSearching = false;

  function saveHistory() {
    try {
      chrome.storage.local.set({ sa_chat_history: chatBox.innerHTML });
    } catch (e) {
      console.error(e);
    }
  }

  // text: HTML kimi qəbul olunur. İstifadəçi/skreyp mətnini çağıran tərəf esc() ilə keçirməlidir.
  function appendMessage(text, sender = "bot") {
    const msgDiv = document.createElement("div");
    msgDiv.className = `sa-msg sa-${sender}-msg`;
    msgDiv.innerHTML = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    saveHistory();
    return msgDiv;
  }

  function removeMessage(el) {
    if (el && el.parentNode) {
      el.parentNode.removeChild(el);
      saveHistory();
    }
  }

  // İlk Başlanğıc Mesajını Yazan Funksiya
  function showWelcomeMessage() {
    chatBox.innerHTML = "";
    appendMessage(
      "Salam! Axtarmaq istədiyiniz məhsulu yazın və ya aktiv səhifədən avtomatik aşkar edin.",
      "bot"
    );
  }

  // Tarixçəni yüklə (köhnə tarixçə təmizlənərək)
  chrome.storage.local.get(["sa_chat_history"], (result) => {
    if (result.sa_chat_history && result.sa_chat_history.trim().length > 0) {
      chatBox.innerHTML = sanitizeHistory(result.sa_chat_history);
      chatBox.scrollTop = chatBox.scrollHeight;
    } else {
      showWelcomeMessage();
    }
  });

  

  closeBtn.addEventListener("click", () => {
    chatWindow.style.display = "none";
  });

  // Tarixçəni Təmizləmə Düyməsinin Məntiqi
  clearBtn.addEventListener("click", () => {
    if (confirm("Çat tarixçəsini təmizləmək istədiyinizdən əminsiniz?")) {
      chrome.storage.local.remove("sa_chat_history", () => {
        showWelcomeMessage();
      });
    }
  });

  // Səhifə Başlığından (Title) Axtarış Sözünün Avtomatik Təmizlənib Inputa Yazılması
  const rawTitle = document.title || "";
  if (rawTitle) {
    const cleanedTitle = cleanProductTitle(rawTitle);
    if (cleanedTitle) {
      productInput.value = cleanedTitle;
    }
  }

  function setBusy(busy) {
    isSearching = busy;
    searchBtn.disabled = busy;
    productInput.disabled = busy;
    searchBtn.textContent = busy ? "..." : "Tap";
  }

  function buildCard(item) {
    let commentsHtml = "";
    if (Array.isArray(item.comments) && item.comments.length > 0) {
      const list = item.comments
        .slice(0, 3)
        .map((c) => `<li>${esc(c)}</li>`)
        .join("");
      commentsHtml = `
      <div class="sa-comments-box">
        <div class="sa-comments-title">💬 Məhsul Rəyləri:</div>
        <ul style="margin:0; padding-left:14px;">${list}</ul>
      </div>
    `;
    }

    // Sahə adlarının həm CamelCase həm də snake_case oxunmasını təmin edirik:
    const platform = item.platformName || item.platform_name || "Unknown";
    const imgUrl = safeUrl(item.imageUrl || item.image_url, "");
    const compUrl = safeUrl(item.competitorUrl || item.competitor_url, "#");
    const price = item.price;
    const currency = item.currency || "AZN";

    const imgHtml = imgUrl
      ? `<img src="${esc(imgUrl)}" alt="Product" referrerpolicy="no-referrer" />`
      : "";

    return `
    <div class="sa-card">
      ${imgHtml}
      <div class="sa-card-title">📦 ${esc(platform)}</div>
      <div class="sa-card-price">🏷️ ${esc(price)} ${esc(currency)}</div>
      <a href="${esc(compUrl)}" target="_blank" rel="noopener noreferrer" class="sa-card-link">Mağazaya Keçid ➔</a>
      ${commentsHtml}
    </div>
  `;
  }

  async function performSearch() {
    if (isSearching) return;

    const rawKeyword = productInput.value.trim();
    if (!rawKeyword) return;

    const keyword = cleanProductTitle(rawKeyword) || rawKeyword;
    appendMessage(esc(keyword), "user");
    productInput.value = "";

    setBusy(true);
    const loadingMsg = appendMessage(
      "🔍 <i>Məhsul üzrə rəqib qiymətləri və rəylər axtarılır... (30 saniyəyə qədər çəkə bilər)</i>",
      "bot"
    );

    // Python (~30s) + Java ehtiyatı; sonsuz gözləməyin qarşısını alır
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);

    try {
      const response = await fetch("http://localhost:8081/api/products/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          productName: keyword,
          current_url: window.location.href,
        }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error("Status: " + response.status);

      const data = await response.json();
      removeMessage(loadingMsg);

      if (data && Array.isArray(data.competitorPrices) && data.competitorPrices.length > 0) {
        appendMessage(`<b>"${esc(keyword)}"</b> üçün tapılan rəqib təklifləri:`, "bot");
        data.competitorPrices.forEach((item) => {
          appendMessage(buildCard(item), "bot");
        });
      } else {
        appendMessage("Təəssüf ki, rəqib mağazalarda bu məhsul üzrə qiymət tapılmadı.", "bot");
      }
    } catch (err) {
      removeMessage(loadingMsg);
      if (err && err.name === "AbortError") {
        appendMessage("⏱️ Axtarış çox uzun çəkdi. Bir az sonra yenidən cəhd edin.", "bot");
      } else {
        appendMessage("❌ Xəta: Serverlə əlaqə qurularkən problem baş verdi.", "bot");
      }
      console.error(err);
    } finally {
      clearTimeout(timer);
      setBusy(false);
      productInput.focus();
    }
  }

  searchBtn.addEventListener("click", performSearch);

  productInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      performSearch();
    }
  });

  // ===================================================================
  // Drag & Drop Məntiqi (Sürüşdürüb Çat-a Atmaq)
  // ===================================================================
  const dropPreview = document.getElementById("sa-drop-preview");
  const previewImg = document.getElementById("sa-preview-img");
  const previewTitle = document.getElementById("sa-preview-title");
  const dropSearchBtn = document.getElementById("sa-drop-search-btn");

  // Tarayıcının resmi açmasını engellemek ve bırakmaya izin vermek için preventDefault şarttır
  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    chatWindow.classList.add("sa-drag-over");
  }

  chatWindow.addEventListener("dragenter", handleDragOver);
  chatWindow.addEventListener("dragover", handleDragOver);

  chatWindow.addEventListener("dragleave", (e) => {
    e.preventDefault();
    chatWindow.classList.remove("sa-drag-over");
  });

chatWindow.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    chatWindow.classList.remove("sa-drag-over");

    console.log("Dropped items:", e.dataTransfer.types);

    const htmlData = e.dataTransfer.getData("text/html");
    const textData = e.dataTransfer.getData("text/plain");
    const uriData = e.dataTransfer.getData("text/uri-list");

    let imgSrc = "";
    let imgAlt = "";

    if (htmlData) {
      const tempDiv = document.createElement("div");
      tempDiv.innerHTML = htmlData;
      const imgEl = tempDiv.querySelector("img");
      if (imgEl) {
        imgSrc = imgEl.src;
        imgAlt = imgEl.alt || imgEl.title || "";
      }
    }

    if (!imgSrc && uriData) {
      imgSrc = uriData;
    }

    if (!imgSrc && /^https?:\/\/.*?\.(png|jpg|jpeg|webp|gif)/i.test(textData)) {
      imgSrc = textData;
    }

    // Yalnız metin və ya link sürüşdürülübsə:
    if (!imgSrc && textData) {
      previewTitle.value = cleanProductTitle(textData);

      // Sürüşdürülən obyektin şəkli yoxdursa, səhifədən avtomatik çək:
      const fallbackImg = getPageProductImage();
      previewImg.src = fallbackImg || chrome.runtime.getURL("images/nebula.jpeg");

      loadCategoryOptions();
      dropPreview.style.display = "flex";
      chatBox.scrollTop = chatBox.scrollHeight;
      return;
    }

    // Şəkil sürüşdürülübsə:
    if (imgSrc) {
      previewImg.src = imgSrc;
      const cleanTitle = cleanProductTitle(imgAlt || document.title || "");
      previewTitle.value = cleanTitle;

      loadCategoryOptions();
      dropPreview.style.display = "flex";
      chatBox.scrollTop = chatBox.scrollHeight;
    } else {
      console.warn("Sürüşdürülən elementdən şəkil və ya mətn alınamadı.");
    }
  });

  // Ön baxış kartındakı "Axtar" düyməsinə kliklədikdə
  dropSearchBtn.addEventListener("click", () => {
    const titleToSearch = previewTitle.value.trim();
    if (titleToSearch) {
      // 1. Məhsulun adını əsas inputa yazırıq
      productInput.value = titleToSearch;
      
      // 2. Ön baxış kartını gizlədirik
      dropPreview.style.display = "none";
      
      // 3. Əsas axtarış funksiyasını çağıraraq API-yə (Java backend-ə) sorğunu atırıq
      performSearch();
    }
  });

  // Ön baxış kartındakı xanada Enter basıldıqda da axtarış getsin
  previewTitle.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      dropSearchBtn.click();
    }
  });

 
function getPageProductImage() {
  
  const ogImage = document.querySelector('meta[property="og:image"], meta[name="og:image"]');
  if (ogImage && ogImage.content) {
    return ogImage.content;
  }

 
  const jsonLdScripts = document.querySelectorAll('script[type="application/ld+json"]');
  for (const script of jsonLdScripts) {
    try {
      const data = JSON.parse(script.textContent);
      if (data.image) {
        return Array.isArray(data.image) ? data.image[0] : data.image;
      }
    } catch (e) {}
  }

  
  const images = Array.from(document.querySelectorAll("img"));
  const mainImg = images.find((img) => img.width > 200 && img.height > 200);
  if (mainImg && mainImg.src) {
    return mainImg.src;
  }

  return "";
}
})();