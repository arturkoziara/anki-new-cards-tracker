"""New Cards Tracker — daily card creation chart on the deck browser."""

from __future__ import annotations

from aqt import gui_hooks, mw
from aqt.deckbrowser import DeckBrowser
from aqt.webview import WebContent

from . import bridge, options, renderer, review_edit

_hooks_registered = False


def _on_deck_browser_will_render_content(
    deck_browser: DeckBrowser, content
) -> None:
    config = options.get_config()
    if not config.get("show_on_deck_browser", True):
        return
    content.stats += renderer.render_chart_html(config)


def _on_webview_will_set_content(
    web_content: WebContent, context
) -> None:
    if not isinstance(context, DeckBrowser):
        return
    config = options.get_config()
    if not config.get("show_on_deck_browser", True):
        return

    addon_package = mw.addonManager.addonFromModule(__name__)
    web_content.css.append(f"/_addons/{addon_package}/web/chart.css")
    web_content.js.append(f"/_addons/{addon_package}/web/chart.js")


def _register_hooks() -> None:
    global _hooks_registered
    if _hooks_registered:
        return
    mw.addonManager.setWebExports(__name__, r"web/.*(css|js)")
    gui_hooks.deck_browser_will_render_content.append(
        _on_deck_browser_will_render_content
    )
    gui_hooks.webview_will_set_content.append(_on_webview_will_set_content)
    gui_hooks.webview_did_receive_js_message.append(bridge.on_js_message)
    gui_hooks.card_will_show.append(review_edit.on_card_will_show)
    _hooks_registered = True


def _on_main_window_did_init() -> None:
    _register_hooks()
    options.setup_menu()


# Register content hooks as early as possible; menu needs the main window.
_register_hooks()
gui_hooks.main_window_did_init.append(_on_main_window_did_init)
