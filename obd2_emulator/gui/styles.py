"""App CSS for NiceGUI (OBD2 chrome)."""

APP_CSS = """
*, *::before, *::after { box-sizing: border-box; }
body, .nicegui-content {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
  background-color: #E8ECF0 !important;
  color: #1F2A37;
  font-size: 13px;
  line-height: 1.5;
}
.q-page, .nicegui-content { padding: 0 !important; }
.font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }

.obd2-root { min-height: 100vh; display: flex; flex-direction: column; background: #E8ECF0; }
.topbar {
  min-height: 48px; height: auto; background: #FFFFFF; border-bottom: 1px solid #CBD5E1;
  padding: 8px 16px; display: flex; flex-wrap: wrap; align-items: center;
  justify-content: space-between; gap: 8px 12px; flex-shrink: 0;
}
.brand-section { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1 1 auto; }
.brand-icon {
  width: 28px; height: 28px; background: #0B6BCB; color: white; border-radius: 3px;
  display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 12px;
  flex-shrink: 0;
}
.brand-title {
  font-weight: 800; font-size: 13px; letter-spacing: 0.04em; text-transform: uppercase;
  color: #1F2A37; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.badge-subtle {
  font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 3px;
  background: #E7F0FD; color: #0B6BCB; border: 1px solid #B6D4FE;
}
.status-pill {
  display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 3px;
  font-size: 11px; font-weight: 700; letter-spacing: 0.03em;
}
.status-pill.stopped { background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }
.status-pill.running { background: #EAF8F0; color: #1F9D55; border: 1px solid #A3E2BD; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.status-pill.stopped .status-dot { background: #94A3B8; }
.status-pill.running .status-dot { background: #1F9D55; }

.obd2-main {
  flex: 1; max-width: 1100px; width: 100%; margin: 0 auto; padding: 14px;
  display: flex; flex-direction: column; gap: 12px;
}
.card {
  background: #FFFFFF; border: 1px solid #C5CCD6; border-radius: 3px;
  padding: 12px 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.field-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em;
  color: #5B6775; margin-bottom: 2px; display: block;
}
.action-btn {
  height: 30px; padding: 0 12px; font-size: 12px; font-weight: 700; border-radius: 3px;
  border: 1px solid transparent; cursor: pointer;
}
.btn-start { background: #1F9D55; color: #FFFFFF; border-color: #1A8246; }
.btn-stop { background: #FFFFFF; color: #D32F2F; border-color: #C5CCD6; }
.btn-restart { background: #FFFFFF; color: #1F2A37; border-color: #C5CCD6; }
.btn-quit { background: #B91C1C; color: #FFFFFF; border-color: #991B1B; }
.footer {
  background: #FFFFFF; border-top: 1px solid #CBD5E1; padding: 6px 16px;
  display: flex; justify-content: space-between; font-size: 11px; color: #5B6775;
  flex-shrink: 0;
}
.live-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
"""
