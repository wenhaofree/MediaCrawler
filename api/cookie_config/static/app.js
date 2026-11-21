const state = {
  items: [],
  busyPlatform: null,
};

const authPanel = document.getElementById("auth-panel");
const authDesc = document.getElementById("auth-desc");
const authError = document.getElementById("auth-error");
const loginForm = document.getElementById("login-form");
const adminPasswordInput = document.getElementById("admin-password");
const mainPanel = document.getElementById("main-panel");
const logoutButton = document.getElementById("logout-button");
const refreshAllButton = document.getElementById("refresh-all-button");
const globalError = document.getElementById("global-error");
const platformGrid = document.getElementById("platform-grid");

function showError(el, message) {
  if (!message) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  el.textContent = message;
  el.classList.remove("hidden");
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = new Error(payload.detail || payload.message || "请求失败");
    err.status = response.status;
    throw err;
  }
  return payload;
}

function statusBadge(status) {
  if (status === "valid") return { cls: "badge--valid", text: "有效" };
  if (status === "expired") return { cls: "badge--expired", text: "失效/异常" };
  return { cls: "badge--unknown", text: "未探测" };
}

function sourceLabel(source) {
  if (source === "database") return "数据库 (热生效)";
  if (source === "secret_file" || source === "runtime_file") return "Secret 文件";
  if (source && source.startsWith("env:")) return `环境变量 (${source.slice(4)})`;
  return "未配置";
}

function escapeHtml(text) {
  return String(text || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderGrid() {
  platformGrid.innerHTML = "";
  for (const item of state.items) {
    const badge = statusBadge(item.status);
    const card = document.createElement("article");
    card.className = "platform-card";
    card.dataset.platform = item.platform;

    card.innerHTML = `
      <div class="card-head">
        <div>
          <div class="card-key">${escapeHtml(item.config_key)}</div>
          <h3>${escapeHtml(item.label)}</h3>
        </div>
        <span class="badge ${badge.cls}">${badge.text}</span>
      </div>

      <div class="meta-grid">
        <div><span class="meta-label">生效来源</span><span class="meta-val">${escapeHtml(sourceLabel(item.source))}</span></div>
        <div><span class="meta-label">长度</span><span class="meta-val">${item.length} 字符</span></div>
        <div><span class="meta-label">脱敏掩码</span><code class="mask-code">${escapeHtml(item.masked_cookie || "（空）")}</code></div>
        <div><span class="meta-label">最近校验</span><span class="meta-val">${escapeHtml(item.last_checked_at || "—")}</span></div>
        <div><span class="meta-label">DB 更新时间</span><span class="meta-val">${escapeHtml(item.updated_at || "未写入 DB")}</span></div>
      </div>

      ${item.last_error ? `<div class="card-msg">${escapeHtml(item.last_error)}</div>` : ""}
      <div class="card-hint">${escapeHtml(item.hint)}</div>

      <form class="cookie-form">
        <textarea class="cookie-input" rows="4" placeholder="粘贴新的完整 Cookie 字符串（保存后自动覆盖生效，不会回显明文）"></textarea>
        <div class="card-actions">
          <button class="button button--primary" type="submit">保存并校验</button>
          <button class="button button--ghost js-save-only" type="button">仅保存</button>
          <button class="button button--ghost js-probe" type="button">探测有效性</button>
          ${item.has_db_override ? '<button class="button button--danger js-clear" type="button">清空 DB 覆盖</button>' : ""}
        </div>
        <div class="card-feedback hidden"></div>
      </form>
    `;

    const form = card.querySelector(".cookie-form");
    const textarea = card.querySelector(".cookie-input");
    const feedback = card.querySelector(".card-feedback");
    const saveOnlyBtn = card.querySelector(".js-save-only");
    const probeBtn = card.querySelector(".js-probe");
    const clearBtn = card.querySelector(".js-clear");

    const setCardFeedback = (msg, isError = false) => {
      if (!msg) {
        feedback.textContent = "";
        feedback.classList.add("hidden");
        return;
      }
      feedback.textContent = msg;
      feedback.className = `card-feedback ${isError ? "card-feedback--err" : "card-feedback--ok"}`;
    };

    const setButtonsDisabled = (disabled) => {
      card.querySelectorAll("button").forEach((b) => {
        b.disabled = disabled;
      });
    };

    const saveCookie = async (probe) => {
      const val = textarea.value.trim();
      if (!val) {
        setCardFeedback("请先粘贴 Cookie 内容", true);
        return;
      }
      setButtonsDisabled(true);
      setCardFeedback(probe ? "正在保存并探测有效性..." : "正在保存...");
      try {
        const res = await requestJson(`/api/cookie-config/${item.platform}`, {
          method: "PUT",
          body: JSON.stringify({ cookie: val, probe }),
        });
        textarea.value = "";
        const idx = state.items.findIndex((x) => x.platform === item.platform);
        if (idx >= 0 && res.item) state.items[idx] = res.item;
        renderGrid();
      } catch (err) {
        setButtonsDisabled(false);
        setCardFeedback(err.message, true);
        if (err.status === 401) await initAuth();
      }
    };

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      saveCookie(true);
    });

    saveOnlyBtn.addEventListener("click", () => saveCookie(false));

    probeBtn.addEventListener("click", async () => {
      setButtonsDisabled(true);
      setCardFeedback("正在探测有效性...");
      try {
        const res = await requestJson(`/api/cookie-config/${item.platform}/check`, {
          method: "POST",
        });
        const idx = state.items.findIndex((x) => x.platform === item.platform);
        if (idx >= 0 && res.item) state.items[idx] = res.item;
        renderGrid();
      } catch (err) {
        setButtonsDisabled(false);
        setCardFeedback(err.message, true);
        if (err.status === 401) await initAuth();
      }
    });

    if (clearBtn) {
      clearBtn.addEventListener("click", async () => {
        if (!window.confirm(`确认清空 ${item.label} 在数据库中的 Cookie 覆盖并回退环境变量吗？`)) return;
        setButtonsDisabled(true);
        try {
          const res = await requestJson(`/api/cookie-config/${item.platform}`, {
            method: "DELETE",
          });
          const idx = state.items.findIndex((x) => x.platform === item.platform);
          if (idx >= 0 && res.item) state.items[idx] = res.item;
          renderGrid();
        } catch (err) {
          setButtonsDisabled(false);
          setCardFeedback(err.message, true);
        }
      });
    }

    platformGrid.appendChild(card);
  }
}

async function loadConfigs() {
  showError(globalError, "");
  try {
    const data = await requestJson("/api/cookie-config");
    state.items = data.items || [];
    renderGrid();
  } catch (err) {
    if (err.status === 401 || err.status === 503) {
      await initAuth();
      return;
    }
    showError(globalError, err.message);
  }
}

async function initAuth() {
  showError(authError, "");
  try {
    const status = await requestJson("/api/cookie-config/auth/status");
    if (!status.password_configured) {
      authPanel.classList.remove("hidden");
      mainPanel.classList.add("hidden");
      logoutButton.classList.add("hidden");
      authDesc.textContent = "服务端尚未配置 COOKIE_ADMIN_PASSWORD，请在 .env 中配置后重启/重建容器。";
      loginForm.classList.add("hidden");
      return;
    }
    loginForm.classList.remove("hidden");
    if (status.authenticated) {
      authPanel.classList.add("hidden");
      mainPanel.classList.remove("hidden");
      logoutButton.classList.remove("hidden");
      await loadConfigs();
    } else {
      authPanel.classList.remove("hidden");
      mainPanel.classList.add("hidden");
      logoutButton.classList.add("hidden");
    }
  } catch (err) {
    showError(authError, err.message);
  }
}

loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  showError(authError, "");
  try {
    await requestJson("/api/cookie-config/auth/login", {
      method: "POST",
      body: JSON.stringify({ password: adminPasswordInput.value }),
    });
    adminPasswordInput.value = "";
    await initAuth();
  } catch (err) {
    showError(authError, err.message);
  }
});

logoutButton.addEventListener("click", async () => {
  await requestJson("/api/cookie-config/auth/logout", { method: "POST" }).catch(() => {});
  await initAuth();
});

refreshAllButton.addEventListener("click", loadConfigs);

initAuth();
