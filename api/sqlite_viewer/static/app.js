const state = {
  platform: "all",
  entityType: "content",
  authorQuery: "",
  timeFilter: "all",
  startDate: "",
  endDate: "",
  sortBy: "created_time",
  sortOrder: "desc",
  viewMode: "grid",
  page: 1,
  pageSize: 20,
  total: 0,
  totalPages: 0,
  options: null,
  lastPayload: null,
};

const platformSelect = document.getElementById("platform-select");
const entityTypeSelect = document.getElementById("entity-type-select");
const authorQueryInput = document.getElementById("author-query-input");
const timeFilterSelect = document.getElementById("time-filter-select");
const sortOrderSelect = document.getElementById("sort-order-select");
const timeFilterHint = document.getElementById("time-filter-hint");
const customDateRange = document.getElementById("custom-date-range");
const startDateInput = document.getElementById("start-date-input");
const endDateInput = document.getElementById("end-date-input");
const summaryBar = document.getElementById("summary-bar");
const recordList = document.getElementById("record-list");
const loadingState = document.getElementById("loading-state");
const errorState = document.getElementById("error-state");
const emptyState = document.getElementById("empty-state");
const resultMeta = document.getElementById("result-meta");
const paginationMeta = document.getElementById("pagination-meta");
const paginationControls = document.getElementById("pagination-controls");
const refreshButton = document.getElementById("refresh-button");
const resetButton = document.getElementById("reset-button");
const gridViewButton = document.getElementById("grid-view-button");
const listViewButton = document.getElementById("list-view-button");
const drawer = document.getElementById("detail-drawer");
const drawerBackdrop = document.getElementById("drawer-backdrop");
const drawerClose = document.getElementById("drawer-close");
const detailTitle = document.getElementById("detail-title");
const detailKicker = document.getElementById("detail-kicker");
const detailMeta = document.getElementById("detail-meta");
const detailJson = document.getElementById("detail-json");

const entityMetaLabel = { content: "发布时间", comment: "发布时间", creator: "最近更新" };
const timeFilterLabel = { all: "全部时间", today: "当日", week: "一周内", custom: "自定义时间段" };
const sortOrderLabel = {
  "created_time:desc": "创建时间倒序",
  "created_time:asc": "创建时间正序",
  "view_count:desc": "播放量倒序",
  "view_count:asc": "播放量正序",
};
const statLabel = {
  liked_count: "点赞",
  like_count: "点赞",
  comments_count: "评论",
  comment_count: "评论",
  video_comment: "评论",
  shared_count: "转发",
  share_count: "分享",
  video_share_count: "分享",
  collected_count: "收藏",
  video_play_count: "播放量",
  view_count: "播放量",
  read_count: "阅读量",
};

function icon(name) {
  const icons = {
    database: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7"/></svg>',
    layers: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m12 3 8 4.5-8 4.5-8-4.5L12 3Z"/><path d="m4 12 8 4.5 8-4.5"/><path d="m4 16.5 8 4.5 8-4.5"/></svg>',
    records: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/></svg>',
    calendar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></svg>',
    user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="8" r="3.2"/><path d="M5 21c.8-3.6 3.1-5.4 7-5.4s6.2 1.8 7 5.4"/></svg>',
    link: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 14 14 10M8.6 17.4l-1.2 1.2a3.5 3.5 0 1 1-5-5l3.2-3.2a3.5 3.5 0 0 1 5 0M15.4 6.6l1.2-1.2a3.5 3.5 0 1 1 5 5l-3.2 3.2a3.5 3.5 0 0 1-5 0"/></svg>',
  };
  return icons[name] || icons.records;
}

function getSortOrderDisplay() { return sortOrderLabel[`${state.sortBy}:${state.sortOrder}`] || sortOrderLabel["created_time:desc"]; }
function safeText(value, fallback = "-") { return value === null || value === undefined || value === "" ? fallback : String(value); }

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : String(value);
}

function setLoading(visible) { loadingState.classList.toggle("hidden", !visible); }
function setEmpty(visible) { emptyState.classList.toggle("hidden", !visible); }

function setError(message) {
  errorState.classList.toggle("hidden", !message);
  errorState.textContent = message || "";
}

function getTimeFilterDisplay() {
  if (state.timeFilter !== "custom") return timeFilterLabel[state.timeFilter] || timeFilterLabel.all;
  if (state.startDate && state.endDate) return `${state.startDate} 至 ${state.endDate}`;
  if (state.startDate) return `${state.startDate} 起`;
  if (state.endDate) return `截止 ${state.endDate}`;
  return "未设置";
}

function makeChip(text, accent = false) {
  const chip = document.createElement("span");
  chip.className = accent ? "chip chip--accent" : "chip";
  chip.textContent = text;
  return chip;
}

function createSummaryCard(iconName, label, value) {
  const card = document.createElement("article");
  card.className = "summary-card";
  card.innerHTML = `<span class="summary-card__icon" aria-hidden="true">${icon(iconName)}</span><div><p class="summary-card__label">${label}</p><strong class="summary-card__value">${value}</strong></div>`;
  return card;
}

function renderSummaryBar() {
  if (!state.options) return;
  const entityCount = state.options.entity_types.find((item) => item.value === state.entityType)?.count || 0;
  const platformCount = state.options.platforms.find((item) => item.value === state.platform)?.count || 0;
  summaryBar.replaceChildren(
    createSummaryCard("layers", "已接入平台", String(state.options.platforms.length - 1)),
    createSummaryCard("database", "当前实体类型总数", formatNumber(entityCount)),
    createSummaryCard("records", "当前平台总记录", formatNumber(platformCount)),
  );
}

function syncControls() {
  platformSelect.value = state.platform;
  entityTypeSelect.value = state.entityType;
  authorQueryInput.value = state.authorQuery;
  timeFilterSelect.value = state.timeFilter;
  sortOrderSelect.value = `${state.sortBy}:${state.sortOrder}`;
  startDateInput.value = state.startDate;
  endDateInput.value = state.endDate;
  customDateRange.classList.toggle("hidden", state.timeFilter !== "custom");
  timeFilterHint.textContent = state.entityType === "creator"
    ? "创作者列表按最近更新时间筛选。"
    : "按发布时间筛选当前列表。";
}

function renderViewToggle() {
  const gridSelected = state.viewMode === "grid";
  gridViewButton.classList.toggle("is-active", gridSelected);
  listViewButton.classList.toggle("is-active", !gridSelected);
  gridViewButton.setAttribute("aria-pressed", String(gridSelected));
  listViewButton.setAttribute("aria-pressed", String(!gridSelected));
}

function renderOptions(options) {
  state.options = options;
  platformSelect.replaceChildren();
  entityTypeSelect.replaceChildren();
  options.platforms.forEach((item) => {
    const option = new Option(`${item.label} (${item.count})`, item.value, false, item.value === state.platform);
    platformSelect.add(option);
  });
  options.entity_types.forEach((item) => {
    const option = new Option(`${item.label} (${item.count})`, item.value, false, item.value === state.entityType);
    entityTypeSelect.add(option);
  });
  syncControls();
  renderSummaryBar();
}

function createStats(stats) {
  const container = document.createElement("div");
  container.className = "stat-list";
  const entries = Object.entries(stats || {}).filter(([, value]) => value !== null && value !== undefined && value !== "");
  if (!entries.length) {
    container.append(makeChip("无统计字段"));
    return container;
  }
  entries.forEach(([key, value]) => {
    const stat = document.createElement("div");
    stat.className = "stat-pill";
    stat.innerHTML = `<strong>${formatNumber(value)}</strong><span>${statLabel[key] || key}</span>`;
    container.append(stat);
  });
  return container;
}

function createExternalLink(url) {
  const link = document.createElement("a");
  link.className = "record-link";
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.innerHTML = `${icon("link")}<span>打开原链接</span>`;
  link.addEventListener("click", (event) => event.stopPropagation());
  return link;
}

function bindDetailOpen(target, item) {
  const openDetail = async () => {
    try {
      const response = await fetch(`/api/sqlite-viewer/detail/${item.entity_type}/${item.platform}/${item.record_pk}`);
      if (!response.ok) throw new Error(`详情加载失败: ${response.status}`);
      openDrawer(await response.json());
    } catch (error) {
      setError(error.message);
    }
  };
  target.addEventListener("click", openDetail);
  target.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDetail();
    }
  });
}

function createRecordCard(item) {
  const card = document.createElement("article");
  card.className = "record-card";
  card.tabIndex = 0;
  card.setAttribute("role", "button");
  card.setAttribute("aria-label", `查看 ${safeText(item.title)} 的详情`);

  const body = document.createElement("div");
  body.className = "record-card__body";
  const heading = document.createElement("div");
  heading.className = "record-card__heading";
  const titleLine = document.createElement("div");
  titleLine.className = "record-card__title-line";
  const title = document.createElement("h2");
  title.className = "record-card__title";
  title.textContent = safeText(item.title);
  const tags = document.createElement("div");
  tags.className = "record-card__tags";
  tags.append(makeChip(item.platform, true), makeChip(item.entity_type));
  titleLine.append(title, tags);
  const summary = document.createElement("p");
  summary.className = "record-card__summary";
  summary.textContent = safeText(item.summary || item.raw_preview, "无摘要");
  heading.append(titleLine, summary);

  const footer = document.createElement("div");
  footer.className = "record-card__footer";
  const meta = document.createElement("div");
  meta.className = "record-card__meta";
  const author = document.createElement("span");
  author.className = "record-meta";
  author.innerHTML = `${icon("user")}<span>作者：${safeText(item.author_name)}</span>`;
  const table = document.createElement("span");
  table.className = "record-meta";
  table.innerHTML = `${icon("layers")}<span>表：${safeText(item.table_name)}</span>`;
  meta.append(author, table);
  if (item.external_url) meta.append(createExternalLink(item.external_url));
  footer.append(meta, createStats(item.stats));
  body.append(heading, footer);

  const side = document.createElement("div");
  side.className = "record-card__side";
  side.innerHTML = `<div class="record-card__time">${icon("calendar")}<div><span>${entityMetaLabel[item.entity_type] || "时间"}</span><strong>${safeText(item.publish_time_display)}</strong></div></div><div class="record-card__source">来源ID：${safeText(item.source_id)}</div>`;
  card.append(body, side);
  bindDetailOpen(card, item);
  return card;
}

function createListItem(item) {
  const row = document.createElement("article");
  row.className = "record-row";
  row.tabIndex = 0;
  row.setAttribute("role", "button");
  row.setAttribute("aria-label", `查看 ${safeText(item.title)} 的详情`);
  const main = document.createElement("div");
  main.className = "record-row__main";
  const title = document.createElement("h2");
  title.textContent = safeText(item.title);
  const detail = document.createElement("p");
  detail.textContent = `${safeText(item.author_name)} · ${safeText(item.table_name)} · ${safeText(item.summary || item.raw_preview, "无摘要")}`;
  main.append(title, detail);
  const labels = document.createElement("div");
  labels.className = "record-row__labels";
  labels.append(makeChip(item.platform, true), makeChip(item.entity_type));
  const time = document.createElement("time");
  time.textContent = safeText(item.publish_time_display);
  const stats = createStats(item.stats);
  stats.classList.add("record-row__stats");
  row.append(main, labels, stats, time);
  if (item.external_url) row.append(createExternalLink(item.external_url));
  bindDetailOpen(row, item);
  return row;
}

function openDrawer(detail) {
  const normalized = detail.normalized;
  detailKicker.textContent = `${detail.platform} / ${detail.entity_type} / ${detail.table_name}`;
  detailTitle.textContent = safeText(normalized.title);
  detailMeta.replaceChildren();
  const metaRows = [
    ["来源 ID", safeText(normalized.source_id)],
    ["作者", safeText(normalized.author_name)],
    [entityMetaLabel[detail.entity_type] || "时间", safeText(normalized.publish_time_display)],
    ["外部链接", normalized.external_url || "-"],
    ["摘要", safeText(normalized.summary)],
  ];
  metaRows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "detail-meta__row";
    const labelNode = document.createElement("div");
    labelNode.className = "detail-meta__label";
    labelNode.textContent = label;
    const valueNode = document.createElement("div");
    valueNode.className = "detail-meta__value";
    if (label === "外部链接" && value !== "-") {
      const link = document.createElement("a");
      link.className = "link";
      link.href = value;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = value;
      valueNode.append(link);
    } else valueNode.textContent = value;
    row.append(labelNode, valueNode);
    detailMeta.append(row);
  });
  detailJson.textContent = detail.raw_json;
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
  drawerClose.focus();
}

function closeDrawer() {
  drawer.classList.add("hidden");
  drawer.setAttribute("aria-hidden", "true");
}

function getPaginationItems(page, totalPages) {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, index) => index + 1);
  if (page <= 4) return [1, 2, 3, 4, 5, "ellipsis", totalPages];
  if (page >= totalPages - 3) return [1, "ellipsis", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  return [1, "ellipsis", page - 1, page, page + 1, "ellipsis", totalPages];
}

function createPageButton(label, page, disabled = false, active = false) {
  const button = document.createElement("button");
  button.className = `page-button${active ? " is-active" : ""}`;
  button.type = "button";
  button.textContent = label;
  button.disabled = disabled;
  button.setAttribute("aria-label", `前往第 ${page} 页`);
  if (active) button.setAttribute("aria-current", "page");
  if (!disabled) {
    button.addEventListener("click", () => {
      state.page = page;
      loadList();
    });
  }
  return button;
}

function renderPagination(payload) {
  paginationControls.replaceChildren();
  paginationMeta.textContent = payload.total ? `第 ${(payload.page - 1) * payload.page_size + 1}–${Math.min(payload.page * payload.page_size, payload.total)} 条，共 ${formatNumber(payload.total)} 条` : "暂无记录";
  if (!payload.total_pages) return;
  const previous = createPageButton("‹", payload.page - 1, payload.page <= 1);
  previous.setAttribute("aria-label", "上一页");
  paginationControls.append(previous);
  getPaginationItems(payload.page, payload.total_pages).forEach((item) => {
    if (item === "ellipsis") {
      const ellipsis = document.createElement("span");
      ellipsis.className = "pagination__ellipsis";
      ellipsis.textContent = "…";
      paginationControls.append(ellipsis);
    } else paginationControls.append(createPageButton(String(item), item, false, item === payload.page));
  });
  const next = createPageButton("›", payload.page + 1, payload.page >= payload.totalPages);
  next.setAttribute("aria-label", "下一页");
  paginationControls.append(next);
}

function renderList(payload) {
  state.lastPayload = payload;
  state.total = payload.total;
  state.totalPages = payload.total_pages;
  recordList.replaceChildren();
  recordList.classList.toggle("record-list--compact", state.viewMode === "list");
  const authorMeta = payload.author_query ? ` / 作者：${payload.author_query}` : "";
  resultMeta.textContent = `当前筛选：${payload.platform} / ${payload.entity_type}${authorMeta} / ${getTimeFilterDisplay()} / ${getSortOrderDisplay()}，共 ${formatNumber(payload.total)} 条`;
  renderPagination(payload);
  setEmpty(!payload.items.length);
  if (!payload.items.length) return;
  payload.items.forEach((item) => recordList.append(state.viewMode === "grid" ? createRecordCard(item) : createListItem(item)));
}

async function loadOptions() {
  const response = await fetch("/api/sqlite-viewer/options");
  if (!response.ok) throw new Error(`选项读取失败: ${response.status}`);
  renderOptions(await response.json());
}

async function loadList() {
  setLoading(true);
  setError("");
  setEmpty(false);
  if (state.timeFilter === "custom" && !state.startDate && !state.endDate) {
    setLoading(false);
    recordList.replaceChildren();
    paginationControls.replaceChildren();
    paginationMeta.textContent = "暂无分页";
    resultMeta.textContent = "自定义时间段至少需要开始日期或结束日期。";
    setError("自定义时间段至少需要选择开始日期或结束日期。");
    return;
  }
  const query = new URLSearchParams({ platform: state.platform, entity_type: state.entityType, time_filter: state.timeFilter, sort_by: state.sortBy, sort_order: state.sortOrder, page: String(state.page), page_size: String(state.pageSize) });
  if (state.authorQuery) query.set("author_query", state.authorQuery);
  if (state.timeFilter === "custom") {
    if (state.startDate) query.set("start_date", state.startDate);
    if (state.endDate) query.set("end_date", state.endDate);
  }
  try {
    const response = await fetch(`/api/sqlite-viewer/list?${query.toString()}`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      throw new Error(errorPayload?.detail || `列表读取失败: ${response.status}`);
    }
    renderList(await response.json());
  } catch (error) {
    recordList.replaceChildren();
    paginationControls.replaceChildren();
    setError(error.message);
  } finally {
    setLoading(false);
  }
}

function applyFilterChange(callback) {
  callback();
  state.page = 1;
  renderSummaryBar();
  loadList();
}

platformSelect.addEventListener("change", () => applyFilterChange(() => { state.platform = platformSelect.value; }));
entityTypeSelect.addEventListener("change", () => applyFilterChange(() => { state.entityType = entityTypeSelect.value; syncControls(); }));
authorQueryInput.addEventListener("change", () => applyFilterChange(() => { state.authorQuery = authorQueryInput.value.trim(); }));
authorQueryInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    applyFilterChange(() => { state.authorQuery = authorQueryInput.value.trim(); });
  }
});
timeFilterSelect.addEventListener("change", () => {
  state.timeFilter = timeFilterSelect.value;
  state.page = 1;
  syncControls();
  renderSummaryBar();
  if (state.timeFilter !== "custom" || state.startDate || state.endDate) loadList();
});
sortOrderSelect.addEventListener("change", () => applyFilterChange(() => {
  [state.sortBy, state.sortOrder] = sortOrderSelect.value.split(":");
}));
startDateInput.addEventListener("change", () => applyFilterChange(() => { state.startDate = startDateInput.value; }));
endDateInput.addEventListener("change", () => applyFilterChange(() => { state.endDate = endDateInput.value; }));
gridViewButton.addEventListener("click", () => {
  if (state.viewMode === "grid") return;
  state.viewMode = "grid";
  renderViewToggle();
  if (state.lastPayload) renderList(state.lastPayload);
});
listViewButton.addEventListener("click", () => {
  if (state.viewMode === "list") return;
  state.viewMode = "list";
  renderViewToggle();
  if (state.lastPayload) renderList(state.lastPayload);
});
resetButton.addEventListener("click", () => {
  Object.assign(state, { platform: "all", entityType: "content", authorQuery: "", timeFilter: "all", startDate: "", endDate: "", sortBy: "created_time", sortOrder: "desc", page: 1 });
  syncControls();
  renderSummaryBar();
  loadList();
});
refreshButton.addEventListener("click", async () => {
  try {
    await loadOptions();
    await loadList();
  } catch (error) {
    setLoading(false);
    setError(error.message);
  }
});
drawerBackdrop.addEventListener("click", closeDrawer);
drawerClose.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => { if (event.key === "Escape") closeDrawer(); });

(async function bootstrap() {
  try {
    renderViewToggle();
    await loadOptions();
    await loadList();
  } catch (error) {
    setLoading(false);
    setError(error.message);
  }
})();
