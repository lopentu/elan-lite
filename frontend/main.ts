import "./style.css";
type Tier = { id: string; name: string; channel: string; color: string };
type Annotation = {
  id: string;
  tier_id: string;
  start: number;
  end: number;
  value: string;
  lexicon_id: string | null;
  provenance: Record<string, unknown>;
};
type Lexeme = { id: string; gloss: string; description: string };
type Frame = { timeMs: number; points: Record<string, [number, number]> };
type Pose = {
  coordinateSystem: string;
  model: { name: string; version: string };
  topology: { version: string; names: string[]; edges: [string, string][] };
  frames: Frame[];
  transforms: { offsetMs: number; mirrored: boolean };
};
type Suggestion = {
  id: string;
  tier_id: string;
  start: number;
  end: number;
  value: string;
  status: string;
  provenance: Record<string, unknown>;
};
type Project = {
  id: string;
  name: string;
  duration: number;
  tiers: Tier[];
  annotations: Annotation[];
  lexicon: Lexeme[];
  suggestions: Suggestion[];
  pose: Pose;
  mediaDescriptors: Record<string, string>[];
};
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `<header><a class="brand" href="/">ELAN<span>lite</span></a><div class="header-title">臺灣手語與手勢研究 <small>TSL & gesture research workspace</small></div><span class="local">● 本機 / Local only</span></header>
<main><div class="projectbar"><div><div class="eyebrow">ANNOTATION WORKSPACE · 標記工作台</div><h1 id="project-name">載入中 / Loading</h1></div><select id="projects" aria-label="Project / 專案"></select><button id="create-project">新專案 / New project</button><button id="backup">備份 / Backup JSON</button><button id="export">匯出 EAF</button><label class="button">匯入 EAF<input id="eaf-input" type="file" accept=".eaf,.xml" hidden></label></div>
<p class="export-note">EAF: independent aligned tiers only · JSON backup retains lexicon links, pose, loci and AI provenance / JSON 備份保留完整研究資料</p><div id="notice" role="status">合成示例，非臺灣手語詞彙。影片不會上傳。 / Synthetic fixture; no participant video uploads.</div>
<div class="workspace"><section class="viewer card"><div class="section-title">01 <strong>影片與姿態 / Video & pose</strong><label><input id="overlay" type="checkbox" checked>2D overlay</label></div><div class="stage"><video id="video" src="/synthetic.mp4" preload="auto" playsinline></video><svg id="pose" viewBox="0 0 960 540" aria-label="Synchronized pose overlay"></svg><span class="stage-label" id="media-label">SYNTHETIC · NO SIGNER</span></div><div class="transport"><button id="play">▶ 播放 / Play</button><button id="back">−100 ms</button><button id="forward">+100 ms</button><output id="clock">00:00.000</output><label>速度<select id="speed"><option>.5</option><option selected>1</option><option>1.5</option></select></label></div><input id="seek" type="range" min="0" max="8000" step="10" value="0" aria-label="Seek time"><div class="media-tools"><label class="button">選擇本機影片 / Local video<input id="media-input" type="file" accept="video/*" hidden></label><label class="button">匯入 Pose JSON<input id="pose-input" type="file" accept=".json" hidden></label></div><div class="two"><label>影片起始偏移 / Media origin (ms)<input id="media-origin" type="number" value="0" step="1"></label><div class="muted">annotation time = media time − origin<br>請核對匯入媒體 / Verify media mapping</div></div><p class="muted" id="pose-meta"></p><p class="muted">2D image coordinates · 無校正 3D / No calibrated 3D · handedness ≠ signing dominance</p></section>
<aside class="editor card"><div class="section-title">02 <strong>區間編輯 / Interval editor</strong></div><form id="annotation-form"><label>層級 / Tier<select id="tier" required></select></label><div class="two"><label>起點 / Start (ms)<input id="start" type="number" min="0" step="1" required value="0"></label><label>終點 / End (ms)<input id="end" type="number" min="1" step="1" required value="500"></label></div><div class="two"><button type="button" id="mark-start">以目前時間設起點</button><button type="button" id="mark-end">以目前時間設終點</button></div><label>標記 / Annotation<input id="value" maxlength="2000" placeholder="輸入 gloss、動作或觀察" required></label><label>詞彙連結 / Stable lexicon ID<select id="lexeme"><option value="">未連結 / None</option></select></label><div class="two"><button class="primary" type="submit">儲存 / Save</button><button type="button" id="new">新增 / New</button></div><button type="button" id="delete" class="danger" disabled>刪除選取標記 / Delete selected</button><p id="selected-id" class="muted">點擊 timeline interval 編輯</p></form><details><summary>空間位置 / Spatial loci</summary><p class="muted">研究者自訂 2D 位置；與目前標記連結，並隨該區間顯示。</p><div class="two"><label>X (0–1)<input id="locus-x" type="number" min="0" max="1" step=".01" value=".7"></label><label>Y (0–1)<input id="locus-y" type="number" min="0" max="1" step=".01" value=".4"></label></div><button id="locus">儲存位置 / Save locus</button></details></aside></div>
<section class="timeline card"><div class="section-title">03 <strong>同步層級 / Synchronized tiers</strong><span>點選區間編輯 · 點擊軌道定位 / Click intervals to edit</span></div><div id="tracks"></div></section>
<div class="bottom"><section class="card"><div class="section-title">04 <strong>詞彙 / Lexicon</strong><span>IDs survive renaming</span></div><div id="lexicon-list"></div><form id="lexicon-form"><input id="lex-id" type="hidden"><label>Gloss<input id="gloss" required placeholder="詞彙名稱 / Gloss"></label><label>說明 / Description<input id="description" placeholder="變體、來源、研究備註"></label><div class="two"><button type="submit">儲存詞彙 / Save</button><button id="new-lex" type="button">新增 / New</button></div></form></section>
<section class="card"><div class="section-title">05 <strong>時間重疊查詢 / Overlap query</strong></div><form id="query-form"><div class="two"><label>Start ms<input id="q-start" type="number" value="1500" required></label><label>End ms<input id="q-end" type="number" value="2900" required></label></div><label>Channel<select id="q-channel"><option value="">全部 / All channels</option></select></label><button type="submit">查詢 / Query</button></form><div id="query-results"></div><p class="muted">[start, end) · 接觸端點不算重疊 / Touching endpoints do not overlap</p></section>
<section class="card"><div class="section-title">06 <strong>AI 提案審查 / Suggestion review</strong></div><p class="muted">Motion-boundary v1 · 動作 heuristic，非已訓練手語辨識器。研究者需逐項審查。</p><button id="propose" class="primary">產生動作區間提案 / Propose boundaries</button><div id="suggestions"></div></section></div><footer>ELAN-lite v0.1 · Local research MVP · EAF independent aligned subset · Single researcher · <a href="https://archive.mpi.nl/tla/elan/documentation" target="_blank" rel="noreferrer">ELAN docs ↗</a></footer></main>`;
let project: Project;
let selected: Annotation | null = null;
let mediaUrl: string | null = null;
let synthetic = true;
const el = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const input = (id: string) => el<HTMLInputElement>(id);
const select = (id: string) => el<HTMLSelectElement>(id);
const video = el<HTMLVideoElement>("video");
const ns = "http://www.w3.org/2000/svg";
function notice(message: string, error = false) {
  el("notice").textContent = message;
  el("notice").classList.toggle("error", error);
}
async function api(path: string, data?: unknown) {
  const r = await fetch(
    "/api" + path,
    data
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        }
      : undefined,
  );
  const d = await r.json();
  if (!r.ok) throw new Error(d.error || r.statusText);
  return d;
}
function handle(fn: () => Promise<void>) {
  return () => fn().catch((e) => notice(e.message, true));
}
function option(parent: HTMLSelectElement, value: string, label: string) {
  const o = document.createElement("option");
  o.value = value;
  o.textContent = label;
  parent.append(o);
}
function time(): number {
  return Math.max(
    0,
    Math.round(video.currentTime * 1000) -
      Number(input("media-origin").value || 0),
  );
}
function clock(ms: number) {
  return `${String(Math.floor(ms / 60000)).padStart(2, "0")}:${((ms / 1000) % 60).toFixed(3).padStart(6, "0")}`;
}
function seek(ms: number) {
  video.currentTime = Math.max(
    0,
    Math.min(
      (ms + Number(input("media-origin").value || 0)) / 1000,
      Number.isFinite(video.duration)
        ? video.duration
        : project.duration / 1000,
    ),
  );
  sync();
}
function sync() {
  if (!project) return;
  const ms = time();
  el("clock").textContent = clock(ms);
  input("seek").value = String(ms);
  document
    .querySelectorAll<HTMLElement>(".playhead")
    .forEach((p) => (p.style.left = `${(ms / project.duration) * 100}%`));
  document
    .querySelectorAll<HTMLElement>(".interval")
    .forEach((a) =>
      a.classList.toggle(
        "active",
        Number(a.dataset.start) <= ms && ms < Number(a.dataset.end),
      ),
    );
  drawPose(ms);
}
function svgElement(tag: string, attrs: Record<string, string>) {
  const n = document.createElementNS(ns, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}
function drawPose(ms: number) {
  const svg = el<SVGElement & HTMLElement>("pose");
  svg.replaceChildren();
  if (!input("overlay").checked) return;
  const pose = project.pose;
  const offset = pose.transforms?.offsetMs || 0;
  const t = ms - offset;
  let f: Frame | undefined = pose.frames.reduce<Frame | undefined>(
    (best, c) =>
      !best || Math.abs(c.timeMs - t) < Math.abs(best.timeMs - t) ? c : best,
    undefined,
  );
  if (
    f &&
    Math.abs(f.timeMs - t) <= 150 &&
    (synthetic || pose.model.name !== "synthetic-stick-figure")
  ) {
    svg.dataset.frame = String(f.timeMs);
    const point = (p: [number, number]) => [
      (pose.transforms?.mirrored ? 1 - p[0] : p[0]) * 960,
      p[1] * 540,
    ];
    for (const [a, b] of pose.topology.edges) {
      if (!f.points[a] || !f.points[b]) continue;
      const [x1, y1] = point(f.points[a]);
      const [x2, y2] = point(f.points[b]);
      svg.append(
        svgElement("line", {
          x1: String(x1),
          y1: String(y1),
          x2: String(x2),
          y2: String(y2),
          stroke: "#3dd6bd",
          "stroke-width": "4",
        }),
      );
    }
    for (const [name, p] of Object.entries(f.points)) {
      const [cx, cy] = point(p);
      const n = svgElement("circle", {
        cx: String(cx),
        cy: String(cy),
        r: name === "head" ? "22" : "7",
        fill: name === "head" ? "#1e474e" : "#d7fff6",
        stroke: "#3dd6bd",
        "stroke-width": "2",
      });
      svg.append(n);
    }
  } else svg.dataset.frame = "missing";
  for (const a of project.annotations) {
    const locus = a.provenance.locus as { x: number; y: number } | undefined;
    if (locus && a.start <= ms && ms < a.end) {
      svg.append(
        svgElement("circle", {
          cx: String(locus.x * 960),
          cy: String(locus.y * 540),
          r: "25",
          fill: "none",
          stroke: "#ffcd78",
          "stroke-width": "3",
        }),
      );
      const text = svgElement("text", {
        x: String(locus.x * 960 + 30),
        y: String(locus.y * 540),
        fill: "#ffcd78",
      });
      text.textContent = "Locus";
      svg.append(text);
    }
  }
}
function reset() {
  selected = null;
  input("start").value = String(Math.min(time(), project.duration - 1));
  input("end").value = String(Math.min(project.duration, time() + 500));
  input("value").value = "";
  select("lexeme").value = "";
  el<HTMLButtonElement>("delete").disabled = true;
  el("selected-id").textContent = "新增標記 / New annotation";
}
function edit(a: Annotation) {
  selected = a;
  select("tier").value = a.tier_id;
  input("start").value = String(a.start);
  input("end").value = String(a.end);
  input("value").value = a.value;
  select("lexeme").value = a.lexicon_id || "";
  el<HTMLButtonElement>("delete").disabled = false;
  el("selected-id").textContent = a.id;
  seek(a.start);
}
async function refresh(pid = project?.id) {
  project = await api("/project/" + pid);
  render();
}
function render() {
  el("project-name").textContent = project.name;
  input("seek").max = String(project.duration);
  const tierValue = select("tier").value;
  select("tier").replaceChildren();
  select("q-channel").replaceChildren();
  option(select("q-channel"), "", "全部 / All channels");
  for (const t of project.tiers) {
    option(select("tier"), t.id, t.name);
    option(select("q-channel"), t.channel, t.name);
  }
  if (tierValue) select("tier").value = tierValue;
  const lexValue = select("lexeme").value;
  select("lexeme").replaceChildren();
  option(select("lexeme"), "", "未連結 / None");
  el("lexicon-list").replaceChildren();
  for (const l of project.lexicon) {
    option(select("lexeme"), l.id, l.gloss);
    const b = document.createElement("button");
    b.className = "lex-item";
    b.textContent = l.gloss + " · " + l.description;
    b.onclick = () => {
      input("lex-id").value = l.id;
      input("gloss").value = l.gloss;
      input("description").value = l.description;
    };
    el("lexicon-list").append(b);
  }
  select("lexeme").value = lexValue;
  el("tracks").replaceChildren();
  const ruler = document.createElement("div");
  ruler.className = "ruler";
  for (const text of [
    "0 s",
    `${(project.duration / 2000).toFixed(1)} s`,
    `${(project.duration / 1000).toFixed(1)} s`,
  ]) {
    const tick = document.createElement("span");
    tick.textContent = text;
    ruler.append(tick);
  }
  el("tracks").append(ruler);
  for (const t of project.tiers) {
    const row = document.createElement("div");
    row.className = "tier-row";
    const label = document.createElement("div");
    label.className = "tier-label";
    label.textContent = t.name;
    label.style.borderLeftColor = t.color;
    const track = document.createElement("div");
    track.className = "track";
    track.onclick = (e) => {
      if (e.target === track) {
        const r = track.getBoundingClientRect();
        seek(((e.clientX - r.left) / r.width) * project.duration);
        select("tier").value = t.id;
      }
    };
    for (const a of project.annotations.filter((a) => a.tier_id === t.id)) {
      const b = document.createElement("button");
      b.className = "interval";
      b.style.left = `${(a.start / project.duration) * 100}%`;
      b.style.width = `${((a.end - a.start) / project.duration) * 100}%`;
      b.style.background = t.color;
      b.textContent =
        (a.lexicon_id
          ? project.lexicon.find((l) => l.id === a.lexicon_id)?.gloss
          : a.value) || a.value;
      b.title = `${a.value} · ${a.start}–${a.end} ms`;
      b.dataset.start = String(a.start);
      b.dataset.end = String(a.end);
      b.onclick = () => edit(a);
      track.append(b);
    }
    const head = document.createElement("div");
    head.className = "playhead";
    track.append(head);
    row.append(label, track);
    el("tracks").append(row);
  }
  el("suggestions").replaceChildren();
  for (const s of project.suggestions) {
    const card = document.createElement("div");
    card.className = "suggestion";
    const title = document.createElement("p");
    title.textContent = `${s.start}–${s.end} ms · ${s.status}`;
    card.append(title);
    const detail = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "來源 / Provenance";
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(s.provenance, null, 2);
    detail.append(summary, pre);
    card.append(detail);
    for (const [decision, label] of s.status === "pending"
      ? [
          ["accepted", "接受 / Accept"],
          ["rejected", "拒絕 / Reject"],
        ]
      : [["undo", "復原 / Undo"]]) {
      const b = document.createElement("button");
      b.textContent = label;
      b.onclick = handle(async () => {
        await api("/review", { project_id: project.id, id: s.id, decision });
        await refresh();
        notice("審查已儲存 / Review saved");
      });
      card.append(b);
    }
    el("suggestions").append(card);
  }
  el("pose-meta").textContent =
    `${project.pose.model.name} v${project.pose.model.version} · ${project.pose.topology.version} · ${project.pose.frames.length} frames`;
  sync();
}
el("annotation-form").onsubmit = (e) => {
  e.preventDefault();
  handle(async () => {
    const a = {
      project_id: project.id,
      id: selected?.id,
      tier_id: select("tier").value,
      start: Number(input("start").value),
      end: Number(input("end").value),
      value: input("value").value,
      lexicon_id: select("lexeme").value,
      provenance: selected?.provenance || { source: "manual" },
    };
    const result = await api("/annotation", a);
    await refresh();
    selected = project.annotations.find((x) => x.id === result.result) || null;
    notice("標記已儲存至 SQLite / Annotation saved to SQLite");
  })();
};
el("new").onclick = reset;
el("mark-start").onclick = () => (input("start").value = String(time()));
el("mark-end").onclick = () => (input("end").value = String(time()));
el("delete").onclick = handle(async () => {
  if (!selected) return;
  await api("/delete", { project_id: project.id, id: selected.id });
  await refresh();
  reset();
  notice("標記已刪除 / Deleted");
});
el("locus").onclick = handle(async () => {
  if (!selected) throw new Error("先選取標記 / Select an annotation first");
  const x = Number(input("locus-x").value),
    y = Number(input("locus-y").value);
  if (
    !Number.isFinite(x) ||
    !Number.isFinite(y) ||
    x < 0 ||
    x > 1 ||
    y < 0 ||
    y > 1
  )
    throw new Error("Locus coordinates must be 0–1");
  await api("/annotation", {
    ...selected,
    project_id: project.id,
    provenance: {
      ...selected.provenance,
      locus: { x, y, coordinateSystem: "normalized-image-2d" },
    },
  });
  await refresh();
  selected = project.annotations.find((a) => a.id === selected?.id) || null;
  notice("空間位置已儲存 / Locus saved");
});
el("lexicon-form").onsubmit = (e) => {
  e.preventDefault();
  handle(async () => {
    await api("/lexicon", {
      id: input("lex-id").value || undefined,
      gloss: input("gloss").value,
      description: input("description").value,
    });
    await refresh();
    notice("詞彙已儲存；連結 ID 不變 / Lexicon saved; linked IDs preserved");
  })();
};
el("new-lex").onclick = () => {
  for (const id of ["lex-id", "gloss", "description"]) input(id).value = "";
};
el("query-form").onsubmit = (e) => {
  e.preventDefault();
  handle(async () => {
    const d = await api("/overlap", {
      project_id: project.id,
      start: Number(input("q-start").value),
      end: Number(input("q-end").value),
      channels: select("q-channel").value ? [select("q-channel").value] : [],
    });
    el("query-results").replaceChildren();
    for (const a of d.result) {
      const b = document.createElement("button");
      b.className = "query-item";
      b.textContent = `${a.tier_name}: ${a.value} [${a.start}, ${a.end})`;
      b.onclick = () => edit(project.annotations.find((x) => x.id === a.id)!);
      el("query-results").append(b);
    }
    if (!d.result.length)
      el("query-results").textContent = "沒有重疊 / No overlaps";
  })();
};
el("propose").onclick = handle(async () => {
  await api("/propose", { project_id: project.id });
  await refresh();
  notice("動作候選已產生；尚未加入標記 / Motion candidates ready for review");
});
el("play").onclick = () =>
  video.paused
    ? video.play().catch((e) => notice(e.message, true))
    : video.pause();
video.onplay = () => (el("play").textContent = "Ⅱ 暫停 / Pause");
video.onpause = () => (el("play").textContent = "▶ 播放 / Play");
video.ontimeupdate = sync;
video.onseeked = sync;
el("back").onclick = () => seek(time() - 100);
el("forward").onclick = () => seek(time() + 100);
input("seek").oninput = () => seek(Number(input("seek").value));
select("speed").onchange = () =>
  (video.playbackRate = Number(select("speed").value));
input("overlay").onchange = sync;
function download(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
el("export").onclick = handle(async () => {
  const r = await fetch(`/api/project/${project.id}/eaf`);
  if (!r.ok) throw new Error("Export failed");
  download("elan-lite.eaf", await r.text(), "application/xml");
  notice(
    "EAF 不含詞彙連結、pose、AI、loci；請另存完整 JSON backup / EAF excludes app extensions; save a JSON backup too",
  );
});
el("backup").onclick = handle(async () =>
  download(
    "elan-lite-backup.json",
    JSON.stringify(await api(`/project/${project.id}/backup`), null, 2),
    "application/json",
  ),
);
input("eaf-input").onchange = handle(async () => {
  const file = input("eaf-input").files?.[0];
  if (!file) return;
  const d = await api("/import-eaf", { xml: await file.text() });
  await loadProjects(d.result);
  reset();
  notice(
    "EAF 已匯入。請選擇對應本機影片；保留 media offsets 為 metadata / Imported; select matching local media. Media origins retained; verify origin control before annotation.",
  );
});
input("pose-input").onchange = handle(async () => {
  const f = input("pose-input").files?.[0];
  if (!f) return;
  await api("/pose", {
    project_id: project.id,
    pose: JSON.parse(await f.text()),
  });
  await refresh();
  notice(
    "Pose 已儲存；確認 timestamps、offset 與方向 / Pose saved; verify timestamps, offset and orientation",
  );
});
input("media-input").onchange = () => {
  const f = input("media-input").files?.[0];
  if (!f) return;
  if (mediaUrl) URL.revokeObjectURL(mediaUrl);
  mediaUrl = URL.createObjectURL(f);
  video.src = mediaUrl;
  synthetic = false;
  el("media-label").textContent = "LOCAL FILE · NOT UPLOADED";
  notice(
    "本機影片只在瀏覽器；重新開啟需再次選取。Demo pose 不會疊到 participant media / Local file only; reselect after reload. Demo pose hidden.",
  );
};
video.onloadedmetadata = () => {
  if (project && Math.abs(video.duration * 1000 - project.duration) > 500)
    notice(
      "影片長度與專案時間軸不同；MVP 不會自動延長專案 / Media duration differs from project; interval range remains project duration",
      true,
    );
  sync();
};
async function loadProjects(pid?: string) {
  const projects = await api("/projects");
  select("projects").replaceChildren();
  for (const p of projects) option(select("projects"), p.id, p.name);
  select("projects").value = pid || projects[0].id;
  await refresh(select("projects").value);
  resetMedia();
}
select("projects").onchange = handle(async () => {
  await refresh(select("projects").value);
  resetMedia();
  reset();
});
void loadProjects().catch((e) => notice(e.message, true));
function tick() {
  if (!video.paused) sync();
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

el("create-project").onclick = handle(async () => {
  const name = prompt("專案名称 / Project name");
  if (!name) return;
  const value = prompt(
    "影片時間長度（毫秒）/ Duration in milliseconds",
    "8000",
  );
  if (value === null) return;
  const d = await api("/create-project", { name, duration: Number(value) });
  await loadProjects(d.result);
  reset();
  notice("已建立專案，請選擇本機影片 / Project created; select local video");
});

function resetMedia() {
  video.pause();
  input("media-origin").value = project.mediaDescriptors[0]?.TIME_ORIGIN || "0";
  if (mediaUrl) {
    URL.revokeObjectURL(mediaUrl);
    mediaUrl = null;
  }
  synthetic = project.pose.model.name === "synthetic-stick-figure";
  if (synthetic) {
    video.src = "/synthetic.mp4";
    el("media-label").textContent = "SYNTHETIC · NO SIGNER";
  } else {
    video.removeAttribute("src");
    video.load();
    el("media-label").textContent = "SELECT LOCAL MEDIA · 請選取本機影片";
  }
  sync();
}
document.addEventListener("keydown", (e) => {
  if (
    !project ||
    e.target instanceof HTMLInputElement ||
    e.target instanceof HTMLSelectElement ||
    e.target instanceof HTMLTextAreaElement
  )
    return;
  if (e.code === "Space") {
    e.preventDefault();
    el("play").click();
  }
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    seek(time() - 100);
  }
  if (e.key === "ArrowRight") {
    e.preventDefault();
    seek(time() + 100);
  }
  if (e.key.toLowerCase() === "i") input("start").value = String(time());
  if (e.key.toLowerCase() === "o") input("end").value = String(time());
});

input("media-origin").oninput = sync;
