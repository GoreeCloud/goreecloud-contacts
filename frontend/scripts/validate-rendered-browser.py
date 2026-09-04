#!/usr/bin/env python3
"""Rendered browser evidence for the GoreeCloud Contacts Development candidate.

Runs against the already-started hardened production-shaped Contacts container in CI.
Uses the runner's Chromium-class browser through ChromeDriver, validates the exact
checked-out revision at the five governed Contacts web form-factor widths, exercises
bounded accessibility/appearance behavior, and writes reviewable screenshots plus a
machine-readable evidence summary.

The validator never submits credentials or enables CardDAV writes. Passing this gate
is rendered Development browser evidence only; it is not human optical approval,
representative real-device acceptance, production approval, Release Candidate, or
Stable application acceptance.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / ".artifacts" / "contacts-rendered"
APP_BASE = os.environ.get("CONTACTS_RENDER_BASE_URL", "http://127.0.0.1:18080").rstrip("/")
DRIVER_HOST = "127.0.0.1"
DRIVER_PORT = 9532
DRIVER_BASE = f"http://{DRIVER_HOST}:{DRIVER_PORT}"
SOURCE_REVISION = os.environ.get("CONTACTS_SOURCE_REVISION", "unknown")
TAB_KEY = "\ue004"

SCENES = (
    ("mobile", 390, 844, True, "mobile"),
    ("narrow-tablet", 768, 1024, True, "tablet"),
    ("roomier-tablet", 1023, 1180, True, "tablet"),
    ("desktop", 1280, 900, False, "desktop"),
    ("wide-desktop", 1600, 1000, False, "wide"),
)


class RenderedAcceptanceError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise RenderedAcceptanceError(message)


def request(method: str, path: str, payload: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(
        f"{DRIVER_BASE}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RenderedAcceptanceError(f"WebDriver HTTP {error.code} for {path}: {detail}") from error
    except (URLError, TimeoutError) as error:
        raise RenderedAcceptanceError(f"WebDriver request failed for {path}: {error}") from error

    if not raw:
        return None
    decoded = json.loads(raw.decode("utf-8"))
    value = decoded.get("value")
    if isinstance(value, dict) and value.get("error"):
        raise RenderedAcceptanceError(
            f"WebDriver {value.get('error')}: {value.get('message', '')}"
        )
    return value


def chromedriver() -> str:
    for candidate in (
        shutil.which("chromedriver"),
        "/usr/bin/chromedriver",
        "/usr/local/share/chromedriver-linux64/chromedriver",
    ):
        if candidate and Path(candidate).is_file():
            return str(candidate)
    raise RenderedAcceptanceError("chromedriver is unavailable on the runner")


def wait_driver() -> None:
    deadline = time.monotonic() + 15
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            state = request("GET", "/status")
            if isinstance(state, dict) and state.get("ready"):
                return
        except Exception as error:  # noqa: BLE001 - preserve diagnostics from a short-lived local service
            last = error
        time.sleep(0.2)
    raise RenderedAcceptanceError(f"chromedriver did not become ready: {last}")


def create_session() -> str:
    value = request(
        "POST",
        "/session",
        {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "chrome",
                    "goog:chromeOptions": {
                        "args": [
                            "--headless=new",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-background-networking",
                            "--disable-component-update",
                            "--disable-default-apps",
                            "--disable-extensions",
                            "--disable-sync",
                            "--metrics-recording-only",
                            "--no-first-run",
                            "--window-size=1600,1000",
                        ]
                    },
                }
            }
        },
    )
    require(isinstance(value, dict), f"Unexpected Chrome session response: {value!r}")
    session_id = value.get("sessionId")
    require(isinstance(session_id, str) and bool(session_id), "Chrome did not return a session id")
    return session_id


def execute(session_id: str, script: str) -> Any:
    return request(
        "POST",
        f"/session/{session_id}/execute/sync",
        {"script": script, "args": []},
    )


def execute_async(session_id: str, script: str) -> Any:
    return request(
        "POST",
        f"/session/{session_id}/execute/async",
        {"script": script, "args": []},
    )


def cdp(session_id: str, command: str, params: dict[str, Any] | None = None) -> Any:
    return request(
        "POST",
        f"/session/{session_id}/goog/cdp/execute",
        {"cmd": command, "params": params or {}},
    )


def set_viewport(session_id: str, width: int, height: int, mobile: bool) -> None:
    cdp(
        session_id,
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": mobile,
            "screenWidth": width,
            "screenHeight": height,
        },
    )
    cdp(
        session_id,
        "Emulation.setTouchEmulationEnabled",
        {"enabled": mobile, "maxTouchPoints": 5 if mobile else 1},
    )
    cdp(session_id, "Emulation.setScrollbarsHidden", {"hidden": mobile})


def emulate_media(session_id: str, features: list[dict[str, str]]) -> None:
    cdp(
        session_id,
        "Emulation.setEmulatedMedia",
        {"media": "screen", "features": features},
    )


def navigate(session_id: str) -> None:
    request("POST", f"/session/{session_id}/url", {"url": f"{APP_BASE}/"})
    deadline = time.monotonic() + 20
    last_state: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        value = execute(
            session_id,
            """
            return {
              ready: document.readyState,
              title: document.title,
              body: document.body ? document.body.innerText : '',
              login: Boolean(document.querySelector('.login-card')),
            };
            """,
        )
        if isinstance(value, dict):
            last_state = value
            if (
                value.get("ready") == "complete"
                and value.get("title") == "GoreeCloud Contacts"
                and "Backend online" in str(value.get("body", ""))
                and value.get("login") is True
            ):
                return
        time.sleep(0.15)
    raise RenderedAcceptanceError(f"Contacts did not settle into the expected read-only sign-in surface: {last_state}")


def settle_render(session_id: str) -> None:
    state = execute_async(
        session_id,
        """
        const done = arguments[arguments.length - 1];
        const complete = () => {
          window.scrollTo(0, 0);
          void document.documentElement.getBoundingClientRect();
          requestAnimationFrame(() => requestAnimationFrame(() => requestAnimationFrame(() => {
            done({
              ready: document.readyState,
              fonts: document.fonts ? document.fonts.status : 'unsupported'
            });
          })));
        };
        if (document.fonts && document.fonts.ready) {
          document.fonts.ready.then(complete, complete);
        } else {
          complete();
        }
        """,
    )
    require(
        isinstance(state, dict) and state.get("ready") == "complete",
        f"render did not settle on a complete document: {state}",
    )
    require(
        state.get("fonts") in {"loaded", "unsupported"},
        f"render fonts did not settle: {state}",
    )


def capture_png(session_id: str, name: str) -> tuple[Path, str]:
    settle_render(session_id)
    encoded = request("GET", f"/session/{session_id}/screenshot")
    require(isinstance(encoded, str) and bool(encoded), f"Chrome did not return screenshot bytes for {name}")
    image = base64.b64decode(encoded)
    require(len(image) > 10_000, f"Screenshot appears empty or invalid for {name}")
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    path = ARTIFACTS / f"contacts-{name}.png"
    path.write_bytes(image)
    return path, hashlib.sha256(image).hexdigest()


def read_state(session_id: str) -> dict[str, Any]:
    value = execute(
        session_id,
        """
        const q = (s) => document.querySelector(s);
        const root = document.documentElement;
        const rootStyle = getComputedStyle(root);
        const workspace = q('.workspace');
        const sidebar = q('.sidebar');
        const content = q('#contacts');
        const tableHeading = q('.table-heading');
        const create = q('.create-button');
        const topbar = q('.topbar');
        const login = q('.login-card');
        const skip = q('.skip-link');
        const rect = (el) => {
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};
        };
        const visibleControls = [...document.querySelectorAll('button,input,select')]
          .map((el) => ({el, r: el.getBoundingClientRect(), style: getComputedStyle(el)}))
          .filter((x) => x.r.width > 0 && x.r.height > 0 && x.style.display !== 'none' && x.style.visibility !== 'hidden')
          .map((x) => ({
            tag:x.el.tagName,
            text:(x.el.textContent || x.el.getAttribute('aria-label') || x.el.getAttribute('name') || '').trim(),
            height:x.r.height,
            width:x.r.width,
            disabled:Boolean(x.el.disabled),
          }));
        const topStyle = topbar ? getComputedStyle(topbar) : null;
        const loginStyle = login ? getComputedStyle(login) : null;
        const skipStyle = skip ? getComputedStyle(skip) : null;
        return {
          ready:document.readyState,
          title:document.title,
          h1:q('h1')?.textContent?.trim() || '',
          width:innerWidth,
          height:innerHeight,
          scrollWidth:document.documentElement.scrollWidth,
          scrollHeight:document.documentElement.scrollHeight,
          appearance:root.getAttribute('data-glz-appearance'),
          canvasRole:rootStyle.getPropertyValue('--glz1-canvas').trim().toLowerCase(),
          baseRole:rootStyle.getPropertyValue('--glz1-base').trim().toLowerCase(),
          targetFloor:rootStyle.getPropertyValue('--glz11-target-min').trim(),
          workspaceDisplay:workspace ? getComputedStyle(workspace).display : null,
          workspaceColumns:workspace ? getComputedStyle(workspace).gridTemplateColumns : null,
          sidebarDisplay:sidebar ? getComputedStyle(sidebar).display : null,
          sidebarPosition:sidebar ? getComputedStyle(sidebar).position : null,
          tableHeadingDisplay:tableHeading ? getComputedStyle(tableHeading).display : null,
          createDisplay:create ? getComputedStyle(create).display : null,
          workspaceRect:rect(workspace),
          sidebarRect:rect(sidebar),
          contentRect:rect(content),
          controls:visibleControls,
          topbarBackgroundImage:topStyle?.backgroundImage || null,
          topbarBoxShadow:topStyle?.boxShadow || null,
          loginBackdropFilter:loginStyle?.backdropFilter || null,
          loginBackgroundColor:loginStyle?.backgroundColor || null,
          skipTransitionDuration:skipStyle?.transitionDuration || null,
          hasNavigation:Boolean(q('nav[aria-label="Contact navigation"]')),
          hasSearch:Boolean(q('input[aria-label="Search contacts"]')),
          hasLogin:Boolean(login),
          hasContentTarget:Boolean(content),
          backendOnline:(document.body?.innerText || '').includes('Backend online'),
        };
        """,
    )
    require(isinstance(value, dict), f"Could not read rendered Contacts state: {value!r}")
    return value


def first_grid_column_px(value: Any) -> float:
    text = str(value or "").strip()
    first = text.split()[0] if text else ""
    require(first.endswith("px"), f"Expected a pixel-resolved first grid column, got {text!r}")
    return float(first[:-2])


def validate_common(state: dict[str, Any], scene: str, width: int) -> None:
    require(state.get("ready") == "complete", f"{scene}: document is not complete")
    require(state.get("title") == "GoreeCloud Contacts", f"{scene}: product title is wrong")
    require(state.get("h1") == "Contacts", f"{scene}: primary product heading is wrong")
    require(abs(int(state.get("width", 0)) - width) <= 1, f"{scene}: viewport width mismatch: {state}")
    require(int(state.get("scrollWidth", width + 2)) <= width + 1, f"{scene}: horizontal overflow: {state}")
    require(state.get("canvasRole") == "#f5f7fa", f"{scene}: deterministic light canvas did not resolve")
    require(bool(state.get("baseRole")), f"{scene}: V1 base role is missing")
    require(state.get("targetFloor") == "48px", f"{scene}: V1.1 48px target floor is not active")
    require(state.get("hasNavigation") is True, f"{scene}: contact navigation landmark is missing")
    require(state.get("hasSearch") is True, f"{scene}: named search field is missing")
    require(state.get("hasLogin") is True, f"{scene}: expected sign-in surface is missing")
    require(state.get("hasContentTarget") is True, f"{scene}: skip-navigation content target is missing")
    require(state.get("backendOnline") is True, f"{scene}: production-shaped backend did not become online")
    controls = state.get("controls") or []
    require(bool(controls), f"{scene}: no visible controls were rendered")
    undersized = [control for control in controls if float(control.get("height", 0)) < 47.5]
    require(not undersized, f"{scene}: visible control below the 48px V1.1 floor: {undersized}")
    require(
        state.get("loginBackdropFilter") in {"none", ""},
        f"{scene}: durable login/decision surface must not use backdrop blur: {state.get('loginBackdropFilter')}",
    )


def validate_layout(state: dict[str, Any], scene: str, family: str) -> None:
    sidebar = state.get("sidebarRect") or {}
    content = state.get("contentRect") or {}

    if family == "mobile":
        require(state.get("workspaceDisplay") == "block", f"{scene}: mobile workspace must be single-task block layout")
        require(state.get("sidebarDisplay") == "grid", f"{scene}: mobile navigation must use its compact grid composition")
        require(state.get("sidebarPosition") == "relative", f"{scene}: mobile sidebar must not remain sticky")
        require(state.get("tableHeadingDisplay") == "none", f"{scene}: mobile table heading must collapse into card semantics")
        require(state.get("createDisplay") == "none", f"{scene}: disabled fixed create action must remain hidden before authentication")
        require(float(content.get("top", 0)) >= float(sidebar.get("bottom", 0)) - 2, f"{scene}: mobile content must follow compact navigation")
        return

    require(state.get("workspaceDisplay") == "grid", f"{scene}: non-mobile workspace must use a pane-aware grid")
    require(float(content.get("left", 0)) >= float(sidebar.get("right", 0)) - 2, f"{scene}: content must remain beside the navigation pane")

    if family == "tablet":
        require(abs(first_grid_column_px(state.get("workspaceColumns")) - 204.0) <= 1.0, f"{scene}: tablet navigation rail must resolve to 204px")
        require(state.get("sidebarDisplay") == "flex", f"{scene}: tablet navigation must use the touch-first pane composition")
        require(state.get("sidebarPosition") == "sticky", f"{scene}: tablet navigation pane must remain sticky")
        require(state.get("tableHeadingDisplay") == "none", f"{scene}: tablet contacts must use card presentation")
    elif family == "desktop":
        require(abs(first_grid_column_px(state.get("workspaceColumns")) - 252.0) <= 1.0, f"{scene}: desktop navigation pane must resolve to 252px")
        require(state.get("tableHeadingDisplay") != "none", f"{scene}: desktop productivity table heading must remain visible")
    elif family == "wide":
        require(abs(first_grid_column_px(state.get("workspaceColumns")) - 288.0) <= 1.0, f"{scene}: wide-desktop navigation pane must resolve to 288px")
        require(state.get("tableHeadingDisplay") != "none", f"{scene}: wide-desktop productivity table heading must remain visible")
    else:
        raise RenderedAcceptanceError(f"Unknown form-factor family: {family}")


def send_tab(session_id: str) -> None:
    request(
        "POST",
        f"/session/{session_id}/actions",
        {
            "actions": [
                {
                    "type": "key",
                    "id": "keyboard",
                    "actions": [
                        {"type": "keyDown", "value": TAB_KEY},
                        {"type": "keyUp", "value": TAB_KEY},
                    ],
                }
            ]
        },
    )


def validate_keyboard_focus(session_id: str, scene: str) -> None:
    execute(session_id, "document.activeElement && document.activeElement.blur(); return true;")
    send_tab(session_id)
    state = execute(
        session_id,
        """
        const active=document.activeElement;
        const style=active?getComputedStyle(active):null;
        return {
          tag:active?.tagName || null,
          className:active?.className || null,
          href:active?.getAttribute('href') || null,
          outlineStyle:style?.outlineStyle || null,
          outlineWidth:style?.outlineWidth || null,
          transform:style?.transform || null,
        };
        """,
    )
    require(isinstance(state, dict), f"{scene}: could not read keyboard focus state")
    require(state.get("tag") == "A" and "skip-link" in str(state.get("className", "")), f"{scene}: first Tab must reach the skip link: {state}")
    require(state.get("href") == "#contacts", f"{scene}: skip link must target #contacts")
    require(state.get("outlineStyle") != "none", f"{scene}: keyboard focus must have a visible outline")
    width = float(str(state.get("outlineWidth") or "0").replace("px", ""))
    require(width >= 1.0, f"{scene}: keyboard focus outline is not visible: {state}")
    require(state.get("transform") == "none", f"{scene}: focused skip link must be visibly translated into view: {state}")


def validate_appearance_precedence(session_id: str) -> None:
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "dark"}])
    execute(session_id, "document.documentElement.removeAttribute('data-glz-appearance'); return true;")
    state = read_state(session_id)
    require(state.get("canvasRole") == "#0b0d11", f"system dark fallback did not resolve the Dark canvas: {state}")

    expected = {
        "light": "#f5f7fa",
        "dark": "#0b0d11",
        "deep-dark": "#05070a",
    }
    for appearance, canvas in expected.items():
        execute(session_id, f"document.documentElement.setAttribute('data-glz-appearance', {json.dumps(appearance)}); return true;")
        state = read_state(session_id)
        require(state.get("appearance") == appearance, f"explicit {appearance} attribute was not retained")
        require(state.get("canvasRole") == canvas, f"explicit {appearance} must override system dark fallback: {state}")

    execute(session_id, "document.documentElement.removeAttribute('data-glz-appearance'); return true;")
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])


def validate_touch_assistance(session_id: str) -> None:
    execute(session_id, "document.documentElement.setAttribute('data-glz-touch-assistance','true'); return true;")
    state = read_state(session_id)
    require(state.get("targetFloor") == "56px", "Touch Assistance did not resolve the 56px target floor")
    controls = state.get("controls") or []
    undersized = [control for control in controls if float(control.get("height", 0)) < 55.5]
    require(not undersized, f"Touch Assistance control below 56px: {undersized}")
    execute(session_id, "document.documentElement.removeAttribute('data-glz-touch-assistance'); return true;")


def validate_reduced_motion(session_id: str) -> None:
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}, {"name": "prefers-reduced-motion", "value": "reduce"}])
    result = execute(
        session_id,
        """
        const skip=getComputedStyle(document.querySelector('.skip-link'));
        const login=getComputedStyle(document.querySelector('.login-card'));
        return {
          media:matchMedia('(prefers-reduced-motion: reduce)').matches,
          skipTransition:skip.transitionDuration,
          loginTransition:login.transitionDuration,
        };
        """,
    )
    require(isinstance(result, dict) and result.get("media") is True, f"Reduced Motion emulation is not active: {result}")
    require(result.get("skipTransition") == "0s", f"Reduced Motion must remove skip-link transition: {result}")
    require(result.get("loginTransition") == "0s", f"Reduced Motion must remove login-card transition: {result}")
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])


def validate_increased_contrast(session_id: str) -> None:
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}, {"name": "prefers-contrast", "value": "more"}])
    result = execute(
        session_id,
        """
        const top=getComputedStyle(document.querySelector('.topbar'));
        return {
          media:matchMedia('(prefers-contrast: more)').matches,
          shadow:top.boxShadow,
        };
        """,
    )
    require(isinstance(result, dict) and result.get("media") is True, f"Increased Contrast emulation is not active: {result}")
    require(result.get("shadow") == "none", f"Increased Contrast must remove decorative topbar shadow: {result}")
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])


def validate_forced_colors(session_id: str) -> None:
    emulate_media(session_id, [{"name": "forced-colors", "value": "active"}])
    result = execute(
        session_id,
        """
        const top=getComputedStyle(document.querySelector('.topbar'));
        return {
          media:matchMedia('(forced-colors: active)').matches,
          backgroundImage:top.backgroundImage,
          shadow:top.boxShadow,
        };
        """,
    )
    require(isinstance(result, dict) and result.get("media") is True, f"Forced Colors emulation is not active: {result}")
    require(result.get("backgroundImage") == "none", f"Forced Colors must remove custom topbar background image: {result}")
    require(result.get("shadow") == "none", f"Forced Colors must remove custom topbar shadow: {result}")
    emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])


def validate_large_text_and_rtl(session_id: str, width: int, label: str) -> None:
    execute(session_id, "document.documentElement.style.fontSize='200%'; document.documentElement.dir='rtl'; return true;")
    state = execute(
        session_id,
        """
        const root=getComputedStyle(document.documentElement);
        return {
          rootFont:parseFloat(root.fontSize),
          dir:document.documentElement.dir,
          width:innerWidth,
          scrollWidth:document.documentElement.scrollWidth,
          searchRect:document.querySelector('.search')?.getBoundingClientRect() || null,
          loginRect:document.querySelector('.login-card')?.getBoundingClientRect() || null,
        };
        """,
    )
    require(isinstance(state, dict), f"{label}: could not read 200%/RTL state")
    require(float(state.get("rootFont", 0)) >= 31.5, f"{label}: 200% root text scaling is not active: {state}")
    require(state.get("dir") == "rtl", f"{label}: RTL direction is not active")
    require(int(state.get("scrollWidth", width + 2)) <= width + 1, f"{label}: 200% text + RTL creates root horizontal overflow: {state}")
    execute(session_id, "document.documentElement.style.fontSize=''; document.documentElement.dir=''; return true;")


def main() -> int:
    driver_process: subprocess.Popen[str] | None = None
    session_id: str | None = None
    evidence: dict[str, Any] = {
        "source_revision": SOURCE_REVISION,
        "base_url": APP_BASE,
        "status": "unverified",
        "scenes": [],
        "coverage": [
            "five Contacts form-factor widths",
            "48px interaction floor",
            "56px Touch Assistance floor",
            "keyboard skip-link focus",
            "system Light/Dark and explicit Light/Dark/Deep Dark precedence",
            "Reduced Motion",
            "Increased Contrast",
            "Forced Colors",
            "200% text plus RTL overflow boundary on mobile and desktop",
            "solid durable login surface",
        ],
        "boundary": "Rendered Development browser evidence only; human optical, reduced-transparency, representative real-device/browser, platform-system, release, and production acceptance remain separate.",
    }

    try:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        driver_process = subprocess.Popen(
            [chromedriver(), f"--port={DRIVER_PORT}", f"--allowed-ips={DRIVER_HOST}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        wait_driver()
        session_id = create_session()

        for scene, width, height, mobile, family in SCENES:
            set_viewport(session_id, width, height, mobile)
            emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])
            navigate(session_id)
            execute(session_id, "document.documentElement.removeAttribute('data-glz-appearance'); return true;")
            state = read_state(session_id)
            validate_common(state, scene, width)
            validate_layout(state, scene, family)
            path, digest = capture_png(session_id, scene)
            evidence["scenes"].append(
                {
                    "name": scene,
                    "width": width,
                    "height": height,
                    "family": family,
                    "screenshot": str(path.relative_to(ROOT)),
                    "sha256": digest,
                }
            )

            if scene in {"mobile", "desktop"}:
                validate_keyboard_focus(session_id, scene)
                validate_large_text_and_rtl(session_id, width, scene)

        set_viewport(session_id, 1280, 900, False)
        emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "light"}])
        navigate(session_id)
        validate_appearance_precedence(session_id)
        validate_touch_assistance(session_id)
        validate_reduced_motion(session_id)
        validate_increased_contrast(session_id)
        validate_forced_colors(session_id)

        execute(session_id, "document.documentElement.setAttribute('data-glz-appearance','deep-dark'); return true;")
        emulate_media(session_id, [{"name": "prefers-color-scheme", "value": "dark"}])
        path, digest = capture_png(session_id, "desktop-deep-dark")
        evidence["scenes"].append(
            {
                "name": "desktop-deep-dark",
                "width": 1280,
                "height": 900,
                "family": "desktop",
                "screenshot": str(path.relative_to(ROOT)),
                "sha256": digest,
            }
        )

        emulate_media(session_id, [{"name": "forced-colors", "value": "active"}])
        path, digest = capture_png(session_id, "desktop-forced-colors")
        evidence["scenes"].append(
            {
                "name": "desktop-forced-colors",
                "width": 1280,
                "height": 900,
                "family": "desktop",
                "screenshot": str(path.relative_to(ROOT)),
                "sha256": digest,
            }
        )

        evidence["status"] = "pass"
        (ARTIFACTS / "contacts-rendered-evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("GoreeCloud Contacts rendered browser Development acceptance: PASS")
        print(f"Evidence: {len(evidence['scenes'])} reviewable screenshots plus contacts-rendered-evidence.json")
        print("Coverage: form-factor composition, appearance precedence, target floors, keyboard focus, accessibility media modes, 200% text, and RTL overflow boundary.")
        print("Boundary: rendered Development browser evidence only; corrected-Stable re-pin, human optical, reduced-transparency, representative real-device/browser, platform-system, release, and production acceptance remain separate.")
        return 0
    except Exception as error:  # noqa: BLE001 - final fail-closed diagnostic boundary
        evidence["status"] = "fail"
        evidence["error"] = str(error)
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        (ARTIFACTS / "contacts-rendered-evidence.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"GoreeCloud Contacts rendered browser acceptance FAILED: {error}")
        return 1
    finally:
        if session_id:
            try:
                request("DELETE", f"/session/{session_id}")
            except Exception:
                pass
        if driver_process and driver_process.poll() is None:
            driver_process.terminate()
            try:
                driver_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                driver_process.kill()


if __name__ == "__main__":
    sys.exit(main())
