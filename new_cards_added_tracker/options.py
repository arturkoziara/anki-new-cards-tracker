"""Config helpers and Tools menu options dialog."""

from __future__ import annotations

from typing import Any, Dict

from aqt import mw
from aqt.qt import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QSpinBox, QVBoxLayout


ADDON_MODULE = __name__.rsplit(".", 1)[0]

DEFAULTS: Dict[str, Any] = {
    "daily_target": 10,
    "default_view": "week",
    "show_on_deck_browser": True,
}


def get_config() -> Dict[str, Any]:
    cfg = mw.addonManager.getConfig(ADDON_MODULE) or {}
    merged = dict(DEFAULTS)
    merged.update(cfg)
    # Normalize
    try:
        merged["daily_target"] = max(1, int(merged.get("daily_target", 10)))
    except (TypeError, ValueError):
        merged["daily_target"] = 10
    view = merged.get("default_view", "week")
    merged["default_view"] = "month" if view == "month" else "week"
    merged["show_on_deck_browser"] = bool(merged.get("show_on_deck_browser", True))
    return merged


def write_config(cfg: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON_MODULE, cfg)


# In-session UI state (not persisted): pagination offset while browsing periods
_session_view: str | None = None
_session_page: int = 0


def get_view_state() -> tuple[str, int]:
    cfg = get_config()
    view = _session_view if _session_view is not None else cfg["default_view"]
    return view, _session_page


def set_view(view: str) -> None:
    global _session_view, _session_page
    _session_view = "month" if view == "month" else "week"
    _session_page = 0


def shift_page(delta: int) -> None:
    global _session_page
    _session_page = min(0, _session_page + delta)


def set_page(page: int) -> None:
    global _session_page
    _session_page = min(0, int(page))


def reset_session_state() -> None:
    global _session_view, _session_page
    _session_view = None
    _session_page = 0


class OptionsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent or mw)
        self.setWindowTitle("New Cards Tracker Options")
        self._cfg = get_config()

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.target_spin = QSpinBox()
        self.target_spin.setRange(1, 9999)
        self.target_spin.setValue(int(self._cfg["daily_target"]))
        form.addRow("Daily target:", self.target_spin)

        self.view_combo = QComboBox()
        self.view_combo.addItem("Week", "week")
        self.view_combo.addItem("Month", "month")
        idx = 1 if self._cfg["default_view"] == "month" else 0
        self.view_combo.setCurrentIndex(idx)
        form.addRow("Default view:", self.view_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self._cfg["daily_target"] = self.target_spin.value()
        self._cfg["default_view"] = self.view_combo.currentData()
        write_config(self._cfg)
        reset_session_state()
        if mw.deckBrowser:
            mw.deckBrowser.refresh()
        super().accept()


def open_options() -> None:
    dlg = OptionsDialog(mw)
    dlg.exec()


def setup_menu() -> None:
    if getattr(mw, "_ncat_menu_attached", False):
        return
    action = mw.form.menuTools.addAction("New Cards Tracker Options...")
    action.triggered.connect(open_options)
    mw._ncat_menu_attached = True
