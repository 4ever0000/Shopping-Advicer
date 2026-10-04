(function () {
  if (document.getElementById("sa-floating-btn")) return;

  // 1. Üzən Kelebek Bulutsusu Düyməsi
  const floatBtn = document.createElement("div");
  floatBtn.id = "sa-floating-btn";

  const nebulaImg = document.createElement("img");
  nebulaImg.src = chrome.runtime.getURL("images/nebula.jpeg");
  nebulaImg.id = "sa-nebula-img";

  floatBtn.appendChild(nebulaImg);
  document.body.appendChild(floatBtn);

  // 2. Çat Pəncərəsinin Yaradılması (Header-ə Təmizlə və Sıfırla Düymələri Əlavə Olundu)
  const chatWindow = document.createElement("div");
  chatWindow.id = "sa-chat-window";
  chatWindow.innerHTML = `
    <div id="sa-chat-header">
      <div class="sa-header-title">🌌 Shopping Advisor</div>
      <div class="sa-header-actions">
        <button id="sa-clear-btn" title="Tarixçəni Təmizlə">🗑️</button>
        <button id="sa-close-btn" title="Bağla">&times;</button>
      </div>
    </div>
    <div id="sa-chat-box"></div>
    <div id="sa-input-area">
      <input type="text" id="sa-productInput" placeholder="Məhsul adı..." />
      <button id="sa-searchBtn">Tap</button>
    </div>
  `;
  document.body.appendChild(chatWindow);

  const chatBox = document.getElementById("sa-chat-box");
  const productInput = document.getElementById("sa-productInput");
  const searchBtn = document.getElementById("sa-searchBtn");
  const closeBtn = document.getElementById("sa-close-btn");
  const clearBtn = document.getElementById("sa-clear-btn");

  // Universal Təmizləyici Funksiya (Frontend tərəfi)
  function cleanProductTitle(text) {
    if (!text) return "";
    return text
      .replace(/^ᐈ\s*/, "")
      .replace(/\(.*?\)|\[.*?\]/g, "")
      .replace(/\b\d+\s*(ml|l|g|kg|gb|tb|cm|mm|m|oz|mah|w|hz)\b/gi, "")
      .replace(/\b(edt|edp|cologne|parfum|parfüm|eau de|essence|refill|tester)\b/gi, "")
      .replace(/\b(erkek|kadın|unisex|men|women|man|woman|set|paket|kit)\b/gi, "")
      .replace(/Книга|автор|Fiyatı|Satın al|Qiyməti/gi, "")
      .split("-")[0]
      .split(",")[0]
      .replace(/\s+/g, " ")
      .trim();
  }

  // İlk Başlanğıc Mesajını Yazan Funksiya
  function showWelcomeMessage() {
    chatBox.innerHTML = "";
    appendMessage("Salam! Axtarmaq istədiyiniz məhsulu yazın və ya aktiv səhifədən avtomatik aşkar edin.", "bot");
  }

  // LocalStorage-dan Tarixçəni Yüklə
  chrome.storage.local.get(["sa_chat_history"], (result) => {
    if (result.sa_chat_history && result.sa_chat_history.trim().length > 0) {
      chatBox.innerHTML = result.sa_chat_history;
      chatBox.scrollTop = chatBox.scrollHeight;
    } else {
      showWelcomeMessage();
    }
  });

  // Toggle Chat Window
  floatBtn.addEventListener("click", () => {
    chatWindow.style.display = chatWindow.style.display === "flex" ? "none" : "flex";
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
  let rawTitle = document.title || "";
  if (rawTitle) {
    let cleanedTitle = cleanProductTitle(rawTitle);
    if (cleanedTitle) {
      productInput.value = cleanedTitle;
    }
  }

  function appendMessage(text, sender = "bot") {
    const msgDiv = document.createElement("div");
    msgDiv.className = `sa-msg sa-${sender}-msg`;
    msgDiv.innerHTML = text;
    chatBox.appendChild(msgDiv);
    chatBox.scrollTop = chatBox.scrollHeight;

    chrome.storage.local.set({ sa_chat_history: chatBox.innerHTML });
  }

  async function performSearch() {
    let rawKeyword = productInput.value.trim();
    if (!rawKeyword) return;

    const keyword = cleanProductTitle(rawKeyword) || rawKeyword;
    appendMessage(keyword, "user");
    productInput.value = "";

    appendMessage("🔍 <i>Məhsul üzrə rəqib qiymətləri və rəylər axtarılır...</i>", "bot");

    try {
      const response = await fetch("http://localhost:8081/api/products/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          productName: keyword,
          current_url: window.location.href 
        }),
      });

      if (!response.ok) throw new Error("Status: " + response.status);

      const data = await response.json();

      if (data && data.competitorPrices && data.competitorPrices.length > 0) {
        appendMessage(`<b>"${keyword}"</b> üçün tapılan rəqib təklifləri:`, "bot");

        data.competitorPrices.forEach((item) => {
          let commentsHtml = "";
          if (item.comments && item.comments.length > 0) {
            const list = item.comments.slice(0, 3).map((c) => `<li>${c}</li>`).join("");
            commentsHtml = `
              <div class="sa-comments-box">
                <div class="sa-comments-title">💬 Məhsul Rəyləri:</div>
                <ul style="margin:0; padding-left:14px;">${list}</ul>
              </div>
            `;
          }

          const platform = item.platform_name || item.platformName || "Unknown";
          const imgUrl = item.image_url || item.imageUrl || "";
          const compUrl = item.competitor_url || item.competitorUrl || "#";
          const price = item.price;
          const currency = item.currency || "AZN";

          const imgHtml = imgUrl ? `<img src="${imgUrl}" alt="Product" />` : "";

          const cardHtml = `
            <div class="sa-card">
              ${imgHtml}
              <div class="sa-card-title">📦 ${platform}</div>
              <div class="sa-card-price">🏷️ ${price} ${currency}</div>
              <a href="${compUrl}" target="_blank" class="sa-card-link">Mağazaya Keçid ➔</a>
              ${commentsHtml}
            </div>
          `;
          appendMessage(cardHtml, "bot");
        });
      } else {
        appendMessage("Təəssüf ki, rəqib mağazalarda bu məhsul üzrə qiymət tapılmadı.", "bot");
      }
    } catch (err) {
      appendMessage("❌ Xəta: Serverlə əlaqə qurularkən problem baş verdi.", "bot");
      console.error(err);
    }
  }

  searchBtn.addEventListener("click", performSearch);

  productInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      performSearch();
    }
  });
})();