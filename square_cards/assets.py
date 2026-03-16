"""Static CSS and JS assets for the built-in web UI."""

APP_STYLES = """
:root {
  color-scheme: light;
  --bg: #f4efe6;
  --panel: rgba(255, 252, 246, 0.92);
  --panel-strong: #fffaf2;
  --ink: #1f2a23;
  --muted: #5f665f;
  --line: rgba(31, 42, 35, 0.12);
  --accent: #1f6b52;
  --accent-soft: rgba(31, 107, 82, 0.12);
  --highlight: #bb4d2c;
  --shadow: 0 22px 70px rgba(52, 35, 17, 0.12);
  --radius: 22px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Avenir Next", "Segoe UI", sans-serif;
  color: var(--ink);
  background:
    radial-gradient(circle at top left, rgba(255, 200, 130, 0.35), transparent 28%),
    radial-gradient(circle at bottom right, rgba(31, 107, 82, 0.16), transparent 24%),
    linear-gradient(135deg, #f8f2e7 0%, #efe5d7 55%, #e3dbc9 100%);
  min-height: 100vh;
}
body.viewer-page {
  min-height: 100dvh;
  height: 100dvh;
  overflow: hidden;
}
.shell {
  width: min(1240px, calc(100% - 32px));
  margin: 28px auto 40px;
}
.viewer-shell {
  width: min(1240px, calc(100% - 20px));
  min-height: 100dvh;
  height: 100dvh;
  margin: 0 auto;
  padding: 10px 0;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 10px;
  overflow: hidden;
}
.hero {
  display: grid;
  gap: 18px;
  grid-template-columns: 1.25fr 0.95fr;
  align-items: stretch;
  margin-bottom: 24px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  backdrop-filter: blur(10px);
}
.hero-copy {
  padding: 28px;
}
.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--highlight);
  font-size: 0.75rem;
  margin-bottom: 12px;
  font-weight: 700;
}
h1 {
  margin: 0 0 12px;
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 0.94;
  letter-spacing: -0.04em;
  max-width: 12ch;
}
.hero-copy p {
  margin: 0;
  color: var(--muted);
  font-size: 1.02rem;
  line-height: 1.55;
  max-width: 64ch;
}
.hero-side {
  padding: 24px;
  display: grid;
  gap: 16px;
  align-content: center;
  background:
    linear-gradient(160deg, rgba(31, 107, 82, 0.95), rgba(22, 70, 54, 0.95)),
    linear-gradient(160deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0));
  color: #f8f4ec;
}
.hero-side h2 {
  margin: 0;
  font-size: 1.2rem;
  letter-spacing: -0.02em;
}
.hero-side p {
  margin: 0;
  color: rgba(248, 244, 236, 0.86);
  line-height: 1.5;
}
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.stat-pill {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  padding: 10px 14px;
  display: inline-flex;
  gap: 8px;
  align-items: center;
}
.stat-pill span {
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.banner {
  margin-bottom: 18px;
  border-radius: 16px;
  padding: 14px 16px;
  font-weight: 600;
}
.banner.success {
  background: rgba(31, 107, 82, 0.12);
  color: #174736;
  border: 1px solid rgba(31, 107, 82, 0.18);
}
.banner.error {
  background: rgba(187, 77, 44, 0.12);
  color: #7b2d15;
  border: 1px solid rgba(187, 77, 44, 0.18);
}
.controls {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: 22px;
  margin-bottom: 24px;
}
.form-panel,
.filter-panel,
.viewer-toolbar,
.viewer-stage {
  padding: 22px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
  margin-bottom: 18px;
}
.panel-header h2 {
  margin: 0 0 4px;
  font-size: 1.3rem;
}
.panel-header p {
  margin: 0;
  color: var(--muted);
  line-height: 1.45;
}
form {
  margin: 0;
}
.grid {
  display: grid;
  gap: 14px;
}
.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
label {
  display: grid;
  gap: 8px;
  font-weight: 600;
  font-size: 0.95rem;
}
input,
select,
textarea,
button {
  font: inherit;
}
input,
select,
textarea {
  width: 100%;
  border: 1px solid rgba(31, 42, 35, 0.16);
  border-radius: 14px;
  padding: 12px 14px;
  background: var(--panel-strong);
  color: var(--ink);
}
textarea {
  min-height: 240px;
  resize: vertical;
  line-height: 1.45;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-top: 16px;
}
button,
.button-link,
.ghost-link {
  border: none;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition:
    transform 140ms ease,
    box-shadow 140ms ease,
    background 140ms ease;
}
button:hover,
.button-link:hover,
.ghost-link:hover {
  transform: translateY(-1px);
}
button,
.button-link {
  background: var(--accent);
  color: #f8f4ec;
  box-shadow: 0 14px 30px rgba(31, 107, 82, 0.22);
}
.ghost-link {
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--line);
}
.danger {
  background: rgba(187, 77, 44, 0.12);
  color: #7b2d15;
  box-shadow: none;
}
.filters {
  display: grid;
  gap: 12px;
}
.filters .actions {
  margin-top: 8px;
}
.catalog {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
}
.module-card {
  padding: 20px;
  display: grid;
  gap: 16px;
  position: relative;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.76), rgba(255, 248, 238, 0.92)),
    radial-gradient(circle at top right, rgba(31, 107, 82, 0.08), transparent 38%);
}
.module-card::after {
  content: "";
  position: absolute;
  inset: auto -30px -46px auto;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: rgba(255, 186, 119, 0.14);
  pointer-events: none;
}
.module-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: start;
}
.module-title {
  margin: 0;
  font-size: 1.15rem;
  line-height: 1.15;
  letter-spacing: -0.02em;
}
.badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  background: rgba(31, 107, 82, 0.08);
  color: var(--accent);
}
.badge.start {
  background: rgba(187, 77, 44, 0.1);
  color: #9a3f20;
}
.module-meta {
  color: var(--muted);
  font-size: 0.92rem;
  display: grid;
  gap: 5px;
}
.hash {
  font-family: "SFMono-Regular", ui-monospace, monospace;
  font-size: 0.83rem;
  word-break: break-all;
  background: rgba(31, 42, 35, 0.05);
  border-radius: 14px;
  padding: 10px 12px;
}
.call-list {
  margin: 0;
  padding-left: 22px;
  display: grid;
  gap: 8px;
  line-height: 1.45;
}
details {
  border-top: 1px solid var(--line);
  padding-top: 14px;
}
summary {
  cursor: pointer;
  font-weight: 700;
}
.module-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}
.module-actions form {
  display: inline;
}
.viewer-layout {
  display: grid;
  gap: 20px;
  max-width: 1180px;
  margin: 0 auto;
  height: 100%;
  min-height: 0;
}
.viewer-toolbar.slim {
  padding: 10px 14px;
}
.viewer-filter-form {
  display: grid;
  gap: 8px;
}
.viewer-filter-grid {
  display: grid;
  gap: 10px;
  grid-template-columns:
    minmax(0, 160px)
    minmax(0, 180px)
    minmax(0, 220px)
    minmax(220px, 1fr)
    auto;
  align-items: end;
}
.viewer-filter-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}
.viewer-filter-meta {
  color: var(--muted);
  font-size: 0.82rem;
  padding-left: 2px;
}
.viewer-body {
  display: grid;
  gap: 16px;
  grid-template-columns:
    minmax(110px, 130px)
    minmax(0, 1fr)
    minmax(110px, 130px);
  align-items: stretch;
  height: 100%;
  min-height: 0;
}
.viewer-card {
  padding: 28px;
  max-width: 780px;
  width: 100%;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}
.viewer-nav {
  display: flex;
  align-items: center;
  justify-content: center;
}
.viewer-nav .button-link,
.viewer-nav .ghost-link,
.nav-placeholder {
  width: 100%;
  min-height: 64px;
}
.nav-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid var(--line);
  color: rgba(31, 42, 35, 0.38);
  background: rgba(255, 255, 255, 0.35);
  font-weight: 700;
}
.viewer-empty {
  padding: 48px 28px;
  text-align: center;
  color: var(--muted);
}
.viewer-module-list {
  margin: 0;
  padding: 0;
  list-style: none;
  width: 100%;
  display: grid;
  gap: 10px;
  font-size: 2rem;
  line-height: 1.28;
  letter-spacing: -0.01em;
  overflow: hidden;
}
.viewer-call-row {
  padding: 10px 16px;
  border-radius: 16px;
  background: rgba(178, 91, 63, 0.28);
  border: 1px solid rgba(145, 63, 38, 0.28);
}
.viewer-call-row:nth-child(even) {
  background: rgba(54, 110, 142, 0.26);
  border-color: rgba(38, 82, 107, 0.28);
}
.empty-state {
  grid-column: 1 / -1;
  padding: 42px 28px;
  border: 1px dashed rgba(31, 42, 35, 0.2);
  border-radius: var(--radius);
  text-align: center;
  color: var(--muted);
  background: rgba(255, 250, 242, 0.7);
}
@media (max-width: 980px) {
  .hero,
  .controls {
    grid-template-columns: 1fr;
  }
  .viewer-filter-grid {
    grid-template-columns: 1fr 1fr;
  }
  .viewer-filter-actions {
    justify-content: flex-start;
    grid-column: 1 / -1;
  }
  .viewer-body {
    grid-template-columns: 94px minmax(0, 1fr) 94px;
  }
}
@media (max-width: 700px) {
  .shell {
    width: min(100% - 18px, 1240px);
  }
  .viewer-shell {
    width: min(100% - 12px, 1240px);
    padding: 6px 0;
    gap: 8px;
  }
  .grid.two,
  .grid.three,
  .viewer-filter-grid {
    grid-template-columns: 1fr;
  }
  .hero-copy,
  .hero-side,
  .form-panel,
  .filter-panel,
  .module-card,
  .viewer-toolbar,
  .viewer-stage,
  .viewer-card {
    padding: 14px;
  }
  .module-top {
    flex-direction: column;
  }
  .viewer-module-list {
    gap: 8px;
  }
  .viewer-call-row {
    padding: 8px 12px;
  }
  .viewer-nav .button-link,
  .viewer-nav .ghost-link,
  .nav-placeholder {
    min-height: 52px;
    min-width: 0;
    padding: 10px 8px;
    font-size: 0.9rem;
  }
}
"""

VIEWER_FIT_SCRIPT = """
(() => {
  const steps = [
    { size: 2.1, gap: 16, line: 1.28 },
    { size: 1.9, gap: 15, line: 1.26 },
    { size: 1.75, gap: 14, line: 1.24 },
    { size: 1.6, gap: 13, line: 1.22 },
    { size: 1.48, gap: 12, line: 1.2 },
    { size: 1.36, gap: 11, line: 1.18 },
    { size: 1.24, gap: 10, line: 1.16 },
    { size: 1.14, gap: 9, line: 1.14 },
    { size: 1.04, gap: 8, line: 1.12 },
    { size: 0.96, gap: 7, line: 1.1 }
  ];

  function fitViewerModule() {
    const card = document.querySelector(".viewer-card");
    const list = document.querySelector(".viewer-module-list");
    if (!card || !list) {
      return;
    }

    for (const step of steps) {
      list.style.fontSize = `${step.size}rem`;
      list.style.gap = `${step.gap}px`;
      list.style.lineHeight = String(step.line);
      if (list.scrollHeight <= card.clientHeight - 4) {
        return;
      }
    }
  }

  window.addEventListener("load", fitViewerModule);
  window.addEventListener("resize", fitViewerModule);
})();
"""
