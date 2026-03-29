const state = {
  tasks: [],
  selectedTaskId: null,
};

const taskForm = document.getElementById("task-form");
const formTitle = document.getElementById("form-title");
const taskIdInput = document.getElementById("task-id");
const taskNameInput = document.getElementById("task-name");
const taskPlatformInput = document.getElementById("task-platform");
const taskRunTimeInput = document.getElementById("task-run-time");
const taskMaxPagesInput = document.getElementById("task-max-pages");
const taskSaveOptionInput = document.getElementById("task-save-option");
const taskEnableCommentsInput = document.getElementById("task-enable-comments");
const taskEnableSubCommentsInput = document.getElementById("task-enable-sub-comments");
const taskStatusInput = document.getElementById("task-status");
const taskCreatorsInput = document.getElementById("task-creators");
const formError = document.getElementById("form-error");
const taskList = document.getElementById("task-list");
const emptyState = document.getElementById("empty-state");
const refreshButton = document.getElementById("refresh-button");
const resetFormButton = document.getElementById("reset-form-button");
const cdpStatus = document.getElementById("cdp-status");
const busyStatus = document.getElementById("busy-status");
const runHistory = document.getElementById("run-history");
const historyTitle = document.getElementById("history-title");

function setFormError(message) {
  if (!message) {
    formError.classList.add("hidden");
    formError.textContent = "";
    return;
  }
  formError.classList.remove("hidden");
  formError.textContent = message;
}

function safeText(value, fallback = "-") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return String(value);
}

function resetForm() {
  taskIdInput.value = "";
  taskNameInput.value = "";
  taskPlatformInput.value = "xhs";
  taskRunTimeInput.value = "09:00";
  taskMaxPagesInput.value = "3";
  taskSaveOptionInput.value = "sqlite";
  taskEnableCommentsInput.checked = false;
  taskEnableSubCommentsInput.checked = false;
  taskStatusInput.checked = true;
  taskCreatorsInput.value = "";
  formTitle.textContent = "新建平台任务";
  setFormError("");
}

function taskPayloadFromForm() {
  return {
    name: taskNameInput.value.trim(),
    platform: taskPlatformInput.value,
    run_time: taskRunTimeInput.value,
    max_pages: Number(taskMaxPagesInput.value || 0),
    enable_comments: taskEnableCommentsInput.checked,
    enable_sub_comments: taskEnableSubCommentsInput.checked,
    save_option: taskSaveOptionInput.value,
    status: taskStatusInput.checked ? "active" : "paused",
    creators: taskCreatorsInput.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

function populateForm(task) {
  taskIdInput.value = String(task.id);
  taskNameInput.value = task.name;
  taskPlatformInput.value = task.platform;
  taskRunTimeInput.value = task.run_time;
  taskMaxPagesInput.value = String(task.max_pages);
  taskSaveOptionInput.value = task.save_option;
  taskEnableCommentsInput.checked = Boolean(task.enable_comments);
  taskEnableSubCommentsInput.checked = Boolean(task.enable_sub_comments);
  taskStatusInput.checked = task.status === "active";
  taskCreatorsInput.value = (task.creators || [])
    .map((item) => item.raw_input)
    .join("\n");
  formTitle.textContent = `编辑任务 #${task.id}`;
  setFormError("");
}

function makeChip(text, extraClass = "") {
  const span = document.createElement("span");
  span.className = `chip ${extraClass}`.trim();
  span.textContent = text;
  return span;
}

function renderBusyStatus(busy) {
  busyStatus.classList.toggle("hidden", !busy);
  busyStatus.textContent = busy ? "调度队列正在执行或等待执行任务，手动启动普通爬虫会被拒绝。" : "";
}

function renderTaskList(tasks) {
  taskList.innerHTML = "";
  emptyState.classList.toggle("hidden", tasks.length > 0);

  tasks.forEach((task) => {
    const card = document.createElement("article");
    card.className = `task-card ${task.status}`;

    const head = document.createElement("div");
    head.className = "task-card__head";

    const titleWrap = document.createElement("div");
    const title = document.createElement("div");
    title.className = "task-card__title";
    title.textContent = task.name;
    const subtitle = document.createElement("div");
    subtitle.className = "task-card__subtitle";
    subtitle.textContent = `${task.platform} / 每日 ${task.run_time} / 每作者 ${task.max_pages} 页`;
    titleWrap.append(title, subtitle);

    const badges = document.createElement("div");
    badges.className = "task-card__meta";
    badges.append(
      makeChip(task.status === "active" ? "启用" : "暂停"),
      makeChip(`${task.creator_count} 位作者`, "muted"),
      makeChip(`保存到 ${task.save_option}`, "muted"),
    );

    head.append(titleWrap, badges);

    const creators = document.createElement("div");
    creators.className = "creator-list";
    (task.creators || []).forEach((creator) => {
      const row = document.createElement("div");
      row.className = "creator-row";
      const rowTitle = document.createElement("div");
      rowTitle.className = "creator-row__title";
      rowTitle.textContent = creator.display_name || creator.normalized_creator_id;
      const rowSub = document.createElement("div");
      rowSub.className = "creator-row__sub";
      rowSub.textContent = creator.raw_input;
      row.append(rowTitle, rowSub);
      creators.append(row);
    });

    const meta = document.createElement("div");
    meta.className = "task-card__meta";
    meta.append(
      makeChip(`下次执行 ${safeText(task.next_run_at, "未计算")}`, "muted"),
      makeChip(`最近执行 ${safeText(task.last_run_at, "暂无")}`, "muted"),
    );
    if (task.latest_run && task.latest_run.status) {
      meta.append(makeChip(`最近状态 ${task.latest_run.status}`));
    }
    if (task.last_error) {
      const error = document.createElement("div");
      error.className = "state state--error";
      error.textContent = task.last_error;
      meta.append(error);
    }

    const actions = document.createElement("div");
    actions.className = "task-card__actions";

    const editButton = document.createElement("button");
    editButton.className = "button";
    editButton.type = "button";
    editButton.textContent = "编辑";
    editButton.addEventListener("click", () => populateForm(task));

    const toggleButton = document.createElement("button");
    toggleButton.className = "button";
    toggleButton.type = "button";
    toggleButton.textContent = task.status === "active" ? "暂停" : "启用";
    toggleButton.addEventListener("click", () => toggleTask(task));

    const runButton = document.createElement("button");
    runButton.className = "button";
    runButton.type = "button";
    runButton.textContent = "立即执行";
    runButton.addEventListener("click", () => runTask(task.id));

    const deleteButton = document.createElement("button");
    deleteButton.className = "button button--warning";
    deleteButton.type = "button";
    deleteButton.textContent = "删除";
    deleteButton.addEventListener("click", () => deleteTask(task.id));

    const historyButton = document.createElement("button");
    historyButton.className = "button button--ghost";
    historyButton.type = "button";
    historyButton.textContent = "运行记录";
    historyButton.addEventListener("click", () => selectTask(task.id));

    actions.append(editButton, toggleButton, runButton, historyButton, deleteButton);
    card.append(head, creators, meta, actions);
    taskList.append(card);
  });
}

function renderRuns(task, runs) {
  historyTitle.textContent = task ? `${task.name} 的运行历史` : "运行历史";
  if (!runs.length) {
    runHistory.className = "run-history empty";
    runHistory.textContent = task ? "该任务还没有运行记录。" : "点击任务卡片查看运行记录。";
    return;
  }

  runHistory.className = "run-history";
  runHistory.innerHTML = "";
  runs.forEach((run) => {
    const card = document.createElement("article");
    card.className = "run-card";

    const head = document.createElement("div");
    head.className = "run-card__head";
    const title = document.createElement("div");
    title.innerHTML = `<strong>${run.status}</strong><div class="mono">${safeText(run.started_at)}</div>`;
    const sub = document.createElement("div");
    sub.className = "mono";
    sub.textContent = run.trigger_type;
    head.append(title, sub);

    const itemList = document.createElement("div");
    itemList.className = "run-item-list";
    (run.items || []).forEach((item) => {
      const node = document.createElement("div");
      node.className = "run-item";
      const titleNode = document.createElement("div");
      titleNode.className = "run-item__title";
      titleNode.textContent = `${item.normalized_creator_id} / ${item.status}`;
      const meta = document.createElement("div");
      meta.className = "run-item__meta mono";
      meta.textContent = `新增 ${item.items_fetched} 条 / 页数 ${item.pages_fetched} / ${safeText(item.finished_at)}`;
      node.append(titleNode, meta);
      if (item.error_message) {
        const error = document.createElement("div");
        error.className = "state state--error";
        error.textContent = item.error_message;
        node.append(error);
      }
      itemList.append(node);
    });

    card.append(head, itemList);
    if (run.error_message) {
      const error = document.createElement("div");
      error.className = "state state--error";
      error.textContent = run.error_message;
      card.append(error);
    }
    runHistory.append(card);
  });
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload;
}

async function refreshCdpStatus() {
  try {
    const payload = await requestJson("/api/scheduled-tasks/cdp-status");
    cdpStatus.className = `cdp-status ${payload.status}`;
    if (payload.status === "ok") {
      cdpStatus.textContent = `9222 浏览器可用：${payload.browser || payload.endpoint}`;
    } else {
      cdpStatus.textContent = `9222 浏览器不可用：${payload.error || "未连接"}`;
    }
  } catch (error) {
    cdpStatus.className = "cdp-status error";
    cdpStatus.textContent = `9222 状态检查失败：${error.message}`;
  }
}

async function refreshTasks() {
  const payload = await requestJson("/api/scheduled-tasks");
  state.tasks = payload.tasks || [];
  renderBusyStatus(Boolean(payload.busy));
  renderTaskList(state.tasks);

  if (state.selectedTaskId) {
    const selected = state.tasks.find((task) => task.id === state.selectedTaskId);
    if (selected) {
      await loadRuns(selected.id);
    } else {
      state.selectedTaskId = null;
      renderRuns(null, []);
    }
  }
}

async function loadRuns(taskId) {
  state.selectedTaskId = taskId;
  const task = state.tasks.find((item) => item.id === taskId) || null;
  const payload = await requestJson(`/api/scheduled-tasks/${taskId}/runs`);
  renderRuns(task, payload.runs || []);
}

async function selectTask(taskId) {
  try {
    await loadRuns(taskId);
  } catch (error) {
    renderRuns(null, []);
    window.alert(error.message);
  }
}

async function saveTask(event) {
  event.preventDefault();
  setFormError("");
  const payload = taskPayloadFromForm();
  const taskId = taskIdInput.value;
  const url = taskId ? `/api/scheduled-tasks/${taskId}` : "/api/scheduled-tasks";
  const method = taskId ? "PATCH" : "POST";

  try {
    await requestJson(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    resetForm();
    await refreshTasks();
  } catch (error) {
    setFormError(error.message);
  }
}

async function toggleTask(task) {
  const payload = {
    name: task.name,
    platform: task.platform,
    run_time: task.run_time,
    max_pages: task.max_pages,
    enable_comments: Boolean(task.enable_comments),
    enable_sub_comments: Boolean(task.enable_sub_comments),
    save_option: task.save_option,
    status: task.status === "active" ? "paused" : "active",
    creators: (task.creators || []).map((item) => item.raw_input),
  };

  try {
    await requestJson(`/api/scheduled-tasks/${task.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await refreshTasks();
  } catch (error) {
    window.alert(error.message);
  }
}

async function runTask(taskId) {
  try {
    await requestJson(`/api/scheduled-tasks/${taskId}/run`, { method: "POST" });
    await refreshTasks();
    await loadRuns(taskId);
  } catch (error) {
    window.alert(error.message);
  }
}

async function deleteTask(taskId) {
  if (!window.confirm("确认删除这个平台任务吗？")) {
    return;
  }
  try {
    await requestJson(`/api/scheduled-tasks/${taskId}`, { method: "DELETE" });
    if (state.selectedTaskId === taskId) {
      state.selectedTaskId = null;
      renderRuns(null, []);
    }
    await refreshTasks();
  } catch (error) {
    window.alert(error.message);
  }
}

taskForm.addEventListener("submit", saveTask);
refreshButton.addEventListener("click", async () => {
  await refreshCdpStatus();
  await refreshTasks();
});
resetFormButton.addEventListener("click", resetForm);

async function init() {
  resetForm();
  await refreshCdpStatus();
  await refreshTasks();
}

init().catch((error) => {
  cdpStatus.className = "cdp-status error";
  cdpStatus.textContent = error.message;
});
