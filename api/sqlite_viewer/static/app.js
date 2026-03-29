const state = {
  platform: "all",
  entityType: "content",
  authorQuery: "",
  timeFilter: "all",
  startDate: "",
  endDate: "",
  page: 1,
  pageSize: 20,
  total: 0,
  totalPages: 0,
  options: null,
};

const platformSelect = document.getElementById("platform-select");
const entityTypeSelect = document.getElementById("entity-type-select");
const authorQueryInput = document.getElementById("author-query-input");
const timeFilterSelect = document.getElementById("time-filter-select");
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
const prevButton = document.getElementById("prev-button");
const nextButton = document.getElementById("next-button");
const refreshButton = document.getElementById("refresh-button");
const drawer = document.getElementById("detail-drawer");
const drawerBackdrop = document.getElementById("drawer-backdrop");
const drawerClose = document.getElementById("drawer-close");
const detailTitle = document.getElementById("detail-title");
const detailKicker = document.getElementById("detail-kicker");
const detailMeta = document.getElementById("detail-meta");
const detailJson = document.getElementById("detail-json");

const entityMetaLabel = {
  content: "发布时间",
  comment: "发布时间",
  creator: "最近更新",
};

const timeFilterLabel = {
  all: "全部时间",
  today: "当日",
  week: "一周内",
  custom: "自定义时间段",
};

function setLoading(visible) {
  loadingState.classList.toggle("hidden", !visible);
}

function setError(message) {
  if (!message) {
    errorState.classList.add("hidden");
    errorState.textContent = "";
    return;
  }
  errorState.classList.remove("hidden");
  errorState.textContent = message;
}

function setEmpty(visible) {
  emptyState.classList.toggle("hidden", !visible);
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("zh-CN") : String(value);
}

function makeChip(text, accent = false) {
  const span = document.createElement("span");
  span.className = accent ? "chip chip--accent" : "chip";
  span.textContent = text;
  return span;
}

function createSummaryCard(label, value) {
  const card = document.createElement("div");
  card.className = "summary-card";

  const labelNode = document.createElement("div");
  labelNode.className = "summary-card__label";
  labelNode.textContent = label;

  const valueNode = document.createElement("div");
  valueNode.className = "summary-card__value";
  valueNode.textContent = value;

  card.append(labelNode, valueNode);
  return card;
}

function getTimeFilterDisplay() {
  if (state.timeFilter !== "custom") {
    return timeFilterLabel[state.timeFilter] || "全部时间";
  }

  if (state.startDate && state.endDate) {
    return `${state.startDate} 至 ${state.endDate}`;
  }
  if (state.startDate) {
    return `${state.startDate} 起`;
  }
  if (state.endDate) {
    return `截止 ${state.endDate}`;
  }
  return "未设置";
}

function getAuthorFilterDisplay() {
  return state.authorQuery ? state.authorQuery : "全部作者";
}

function syncTimeFilterControls() {
  authorQueryInput.value = state.authorQuery;
  timeFilterSelect.value = state.timeFilter;
  startDateInput.value = state.startDate;
  endDateInput.value = state.endDate;
  customDateRange.classList.toggle("hidden", state.timeFilter !== "custom");
  timeFilterHint.textContent = state.entityType === "creator"
    ? "创作者列表按最近更新时间筛选，其余类型按发布时间筛选。"
    : "按发布时间筛选当前列表。";
}

function renderSummaryBar() {
  if (!state.options) {
    return;
  }

  summaryBar.innerHTML = "";
  summaryBar.append(
    createSummaryCard("已接入平台", String(state.options.platforms.length - 1)),
    createSummaryCard(
      "当前实体类型总数",
      formatNumber(state.options.entity_types.find((item) => item.value === state.entityType)?.count || 0),
    ),
    createSummaryCard(
      "当前平台总记录",
      formatNumber(state.options.platforms.find((item) => item.value === state.platform)?.count || 0),
    ),
    createSummaryCard("作者筛选", getAuthorFilterDisplay()),
    createSummaryCard("时间筛选", getTimeFilterDisplay()),
  );
}

function renderOptions(options) {
  state.options = options;

  platformSelect.innerHTML = "";
  entityTypeSelect.innerHTML = "";
  syncTimeFilterControls();

  options.platforms.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.label} (${item.count})`;
    if (item.value === state.platform) {
      option.selected = true;
    }
    platformSelect.append(option);
  });

  options.entity_types.forEach((item) => {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = `${item.label} (${item.count})`;
    if (item.value === state.entityType) {
      option.selected = true;
    }
    entityTypeSelect.append(option);
  });
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
    const pill = document.createElement("span");
    pill.className = "stat-pill";
    pill.textContent = `${key}: ${formatNumber(value)}`;
    container.append(pill);
  });

  return container;
}

function openDrawer(detail) {
  const normalized = detail.normalized;
  detailKicker.textContent = `${detail.platform} / ${detail.entity_type} / ${detail.table_name}`;
  detailTitle.textContent = safeText(normalized.title);
  detailMeta.innerHTML = "";

  const metaRows = [
    ["来源 ID", safeText(normalized.source_id)],
    ["作者", safeText(normalized.author_name)],
    [entityMetaLabel[detail.entity_type] || "时间", safeText(normalized.publish_time_display)],
    ["外部链接", normalized.external_url ? normalized.external_url : "-"],
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
    } else {
      valueNode.textContent = value;
    }

    row.append(labelNode, valueNode);
    detailMeta.append(row);
  });

  detailJson.textContent = detail.raw_json;
  drawer.classList.remove("hidden");
  drawer.setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  drawer.classList.add("hidden");
  drawer.setAttribute("aria-hidden", "true");
}

function createRecordCard(item) {
  const card = document.createElement("article");
  card.className = "record-card";
  card.tabIndex = 0;

  const head = document.createElement("div");
  head.className = "record-card__head";

  const titleWrap = document.createElement("div");
  const title = document.createElement("h3");
  title.className = "record-card__title";
  title.textContent = safeText(item.title);

  const subtitle = document.createElement("p");
  subtitle.className = "record-card__subtitle";
  subtitle.textContent = safeText(item.summary || item.raw_preview, "无摘要");
  titleWrap.append(title, subtitle);

  const meta = document.createElement("div");
  meta.className = "record-card__meta";
  meta.append(
    makeChip(item.platform, true),
    makeChip(item.entity_type),
    makeChip(`${entityMetaLabel[item.entity_type] || "时间"}: ${safeText(item.publish_time_display)}`),
    makeChip(`来源ID: ${safeText(item.source_id)}`),
  );

  head.append(titleWrap, meta);
  card.append(head);

  const authorMeta = document.createElement("div");
  authorMeta.className = "record-card__meta";
  authorMeta.append(
    makeChip(`作者: ${safeText(item.author_name)}`),
    makeChip(`表: ${safeText(item.table_name)}`),
  );
  if (item.external_url) {
    const externalChip = document.createElement("a");
    externalChip.className = "chip link";
    externalChip.href = item.external_url;
    externalChip.target = "_blank";
    externalChip.rel = "noopener noreferrer";
    externalChip.textContent = "打开原链接";
    externalChip.addEventListener("click", (event) => {
      event.stopPropagation();
    });
    authorMeta.append(externalChip);
  }
  card.append(authorMeta);

  card.append(createStats(item.stats));

  const openDetail = async () => {
    try {
      const response = await fetch(`/api/sqlite-viewer/detail/${item.entity_type}/${item.platform}/${item.record_pk}`);
      if (!response.ok) {
        throw new Error(`详情加载失败: ${response.status}`);
      }
      openDrawer(await response.json());
    } catch (error) {
      setError(error.message);
    }
  };

  card.addEventListener("click", openDetail);
  card.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      openDetail();
    }
  });

  return card;
}

function renderList(payload) {
  state.total = payload.total;
  state.totalPages = payload.total_pages;
  recordList.innerHTML = "";

  const authorMeta = payload.author_query ? ` / 作者: ${payload.author_query}` : "";
  resultMeta.textContent = `当前筛选：${payload.platform} / ${payload.entity_type}${authorMeta} / ${getTimeFilterDisplay()}，共 ${formatNumber(payload.total)} 条`;
  paginationMeta.textContent = payload.total
    ? `第 ${payload.page} / ${payload.total_pages} 页`
    : "暂无分页";

  prevButton.disabled = payload.page <= 1;
  nextButton.disabled = payload.page >= payload.total_pages || payload.total_pages === 0;

  if (!payload.items.length) {
    setEmpty(true);
    return;
  }

  setEmpty(false);
  payload.items.forEach((item) => {
    recordList.append(createRecordCard(item));
  });
}

async function loadOptions() {
  const response = await fetch("/api/sqlite-viewer/options");
  if (!response.ok) {
    throw new Error(`选项读取失败: ${response.status}`);
  }
  const options = await response.json();
  renderOptions(options);
}

async function loadList() {
  setLoading(true);
  setError("");
  setEmpty(false);

  if (state.timeFilter === "custom" && !state.startDate && !state.endDate) {
    setLoading(false);
    recordList.innerHTML = "";
    resultMeta.textContent = "自定义时间段至少需要开始日期或结束日期。";
    paginationMeta.textContent = "暂无分页";
    setError("自定义时间段至少需要选择开始日期或结束日期。");
    return;
  }

  const query = new URLSearchParams({
    platform: state.platform,
    entity_type: state.entityType,
    time_filter: state.timeFilter,
    page: String(state.page),
    page_size: String(state.pageSize),
  });
  if (state.authorQuery) {
    query.set("author_query", state.authorQuery);
  }
  if (state.timeFilter === "custom") {
    if (state.startDate) {
      query.set("start_date", state.startDate);
    }
    if (state.endDate) {
      query.set("end_date", state.endDate);
    }
  }

  try {
    const response = await fetch(`/api/sqlite-viewer/list?${query.toString()}`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => null);
      throw new Error(errorPayload?.detail || `列表读取失败: ${response.status}`);
    }
    renderList(await response.json());
  } catch (error) {
    recordList.innerHTML = "";
    setError(error.message);
  } finally {
    setLoading(false);
  }
}

platformSelect.addEventListener("change", () => {
  state.platform = platformSelect.value;
  state.page = 1;
  if (state.options) {
    renderSummaryBar();
  }
  loadList();
});

entityTypeSelect.addEventListener("change", () => {
  state.entityType = entityTypeSelect.value;
  state.page = 1;
  if (state.options) {
    syncTimeFilterControls();
    renderSummaryBar();
  }
  loadList();
});

authorQueryInput.addEventListener("change", () => {
  state.authorQuery = authorQueryInput.value.trim();
  state.page = 1;
  renderSummaryBar();
  loadList();
});

authorQueryInput.addEventListener("keydown", (event) => {
  if (event.key !== "Enter") {
    return;
  }
  event.preventDefault();
  state.authorQuery = authorQueryInput.value.trim();
  state.page = 1;
  renderSummaryBar();
  loadList();
});

timeFilterSelect.addEventListener("change", () => {
  state.timeFilter = timeFilterSelect.value;
  state.page = 1;
  syncTimeFilterControls();
  renderSummaryBar();
  if (state.timeFilter === "custom" && !state.startDate && !state.endDate) {
    setError("");
    return;
  }
  loadList();
});

startDateInput.addEventListener("change", () => {
  state.startDate = startDateInput.value;
  state.page = 1;
  renderSummaryBar();
  loadList();
});

endDateInput.addEventListener("change", () => {
  state.endDate = endDateInput.value;
  state.page = 1;
  renderSummaryBar();
  loadList();
});

refreshButton.addEventListener("click", async () => {
  await loadOptions();
  await loadList();
});

prevButton.addEventListener("click", () => {
  if (state.page <= 1) {
    return;
  }
  state.page -= 1;
  loadList();
});

nextButton.addEventListener("click", () => {
  if (state.page >= state.totalPages) {
    return;
  }
  state.page += 1;
  loadList();
});

drawerBackdrop.addEventListener("click", closeDrawer);
drawerClose.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDrawer();
  }
});

(async function bootstrap() {
  try {
    await loadOptions();
    await loadList();
  } catch (error) {
    setLoading(false);
    setError(error.message);
  }
})();
