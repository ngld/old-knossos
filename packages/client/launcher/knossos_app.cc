// Copyright (c) 2013 The Chromium Embedded Framework Authors. All rights
// reserved. Use of this source code is governed by a BSD-style license that
// can be found in the LICENSE file.

#include "knossos_app.h"

#include <cstdio>
#include <string>

#include "include/cef_browser.h"
#include "include/cef_command_line.h"
#include "include/cef_file_util.h"
#include "include/cef_path_util.h"
#include "include/cef_process_message.h"
#include "include/cef_values.h"
#include "include/internal/cef_types.h"
#include "include/internal/cef_types_wrappers.h"
#include "include/internal/cef_win.h"
#include "include/views/cef_box_layout.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_window.h"
#include "include/wrapper/cef_helpers.h"
#include "include/wrapper/cef_closure_task.h"

#include "browser/knossos_handler.h"
#include "browser/knossos_bridge.h"
#include "browser/knossos_dev_tools.h"
#include "renderer/knossos_js_interface.h"

namespace {

// When using the Views framework this object provides the delegate
// implementation for the CefWindow that hosts the Views-based browser.
class KnossosWindowDelegate : public CefWindowDelegate {
 public:
  explicit KnossosWindowDelegate(CefRefPtr<CefBrowserView> browser_view, bool main_browser)
      : main_browser_(main_browser), browser_view_(browser_view) {}

  void OnWindowCreated(CefRefPtr<CefWindow> window) OVERRIDE {
    // Add the browser view and show the window.
    window->AddChildView(browser_view_);
    window->Show();

    // Give keyboard focus to the browser view.
    browser_view_->RequestFocus();
  }

  void OnWindowDestroyed(CefRefPtr<CefWindow> window) OVERRIDE {
    browser_view_ = nullptr;
  }

  bool CanClose(CefRefPtr<CefWindow> window) OVERRIDE {
    // Allow the window to close if the browser says it's OK.
    CefRefPtr<CefBrowser> browser = browser_view_->GetBrowser();
    if (browser)
      return browser->GetHost()->TryCloseBrowser();
    return true;
  }

  bool IsFrameless(CefRefPtr<CefWindow> window) OVERRIDE {
    return true;
  }

  CefRect GetInitialBounds(CefRefPtr<CefWindow> window) OVERRIDE {
    CefRect screen_size = KnossosHandler::GetInstance()->GetScreenSize();
    CefRect window_size(0, 0, 1200, 800);

    window_size.x = (screen_size.width - window_size.width) / 2;
    window_size.y = (screen_size.height - window_size.height) / 2;

    return window_size;
  }

 private:
  bool main_browser_;
  CefRefPtr<CefBrowserView> browser_view_;

  IMPLEMENT_REFCOUNTING(KnossosWindowDelegate);
  DISALLOW_COPY_AND_ASSIGN(KnossosWindowDelegate);
};

class KnossosBrowserViewDelegate : public CefBrowserViewDelegate {
 public:
  KnossosBrowserViewDelegate() {}

  bool OnPopupBrowserViewCreated(CefRefPtr<CefBrowserView> browser_view,
                                 CefRefPtr<CefBrowserView> popup_browser_view,
                                 bool is_devtools) OVERRIDE {
    if (is_devtools) {
      CefWindow::CreateTopLevelWindow(
        new KnossosDevToolsWindowDelegate(popup_browser_view));
    } else {
      // Create a new top-level Window for the popup. It will show itself after
      // creation.
      CefWindow::CreateTopLevelWindow(
          new KnossosWindowDelegate(popup_browser_view, false));
    }

    // We created the Window.
    return true;
  }

 private:
  IMPLEMENT_REFCOUNTING(KnossosBrowserViewDelegate);
  DISALLOW_COPY_AND_ASSIGN(KnossosBrowserViewDelegate);
};

}  // namespace

KnossosApp::KnossosApp() {}

void KnossosApp::OnBeforeCommandLineProcessing(const CefString& process_type, CefRefPtr<CefCommandLine> command_line) {
  if (process_type.empty()) {
    // Don't create a "GPUCache" directory
    command_line->AppendSwitch("disable-gpu-shader-disk-cache");

#if defined(OS_MAC)
    // Disable the toolchain prompt on macOS.
    command_line->AppendSwitch("use-mock-keychain");
#endif
  }
}

void KnossosApp::OnContextInitialized() {
  CEF_REQUIRE_UI_THREAD();

  CefRefPtr<CefCommandLine> command_line =
      CefCommandLine::GetGlobalCommandLine();

  const bool enable_chrome_runtime = command_line->HasSwitch("enable-chrome-runtime");

#if defined(OS_WIN) || defined(OS_LINUX)
  // The Views framework is currently only supported on Windows and Linux.
  const bool use_views = true;
#else
  const bool use_views = false;
#endif

  // KnossosHandler implements browser-level callbacks.
  CefRefPtr<KnossosHandler> handler(new KnossosHandler(use_views, _settings_path));

  // Specify CEF browser settings here.
  CefBrowserSettings browser_settings;

  std::string url;

  // Check if a "--url=" value was provided via the command-line. If so, use
  // that instead of the default URL.
  url = command_line->GetSwitchValue("url");
  if (url.empty())
    url = "https://files.client.fsnebula.org/index.html";

  if (use_views && !enable_chrome_runtime) {
    // Create the BrowserView.
    CefRefPtr<CefBrowserView> browser_view = CefBrowserView::CreateBrowserView(
        handler, url, browser_settings, nullptr, nullptr,
        new KnossosBrowserViewDelegate());

    // Create the Window. It will show itself after creation.
    CefWindow::CreateTopLevelWindow(new KnossosWindowDelegate(browser_view, true));
  } else {
    // Information used when creating the native window.
    CefWindowInfo window_info;

#if defined(OS_WIN)
    // On Windows we need to specify certain flags that will be passed to
    // CreateWindowEx().
    window_info.SetAsPopup(NULL, "knossos");
#else
    CefRect screen_size = handler->GetScreenSize();

    window_info.width = 1200;
    window_info.height = 800;

    window_info.x = (screen_size.width - window_info.width) / 2;
    window_info.y = (screen_size.height - window_info.height) / 2 - 200;
#endif

    // Create the first browser window.
    CefBrowserHost::CreateBrowser(window_info, handler, url, browser_settings,
                                  nullptr, nullptr);
  }

  // Load libknossos on the thread dedicated to Knossos tasks
  handler->PostKnossosTask(base::Bind(PrepareLibKnossos, _settings_path));
}

void KnossosApp::InitializeSettings(CefSettings &settings, std::string appDataPath) {
  CefString path;
  if (!CefGetPath(PK_DIR_EXE, path)) {
    LOG(ERROR) << "Could not find application directory!";
  }

  std::string tmp = path;
#if defined(OS_LINUX) || defined(OS_APPLE)
  std::string sep("/");
#else
  std::string sep("\\");
#endif
  tmp += sep + "portable_settings";

  std::string config_path;
  LOG(INFO) << "Portable path: " << tmp;

  if (CefDirectoryExists(CefString(tmp))) {
    config_path = tmp;
  } else {
    if (!appDataPath.empty()) {
      config_path = appDataPath + "/Knossos";
    } else {
      LOG(ERROR) << "Could not find appdata directory!";
    }
  }

  if (config_path.empty()) {
    KnossosHandler::ShowError("Could not find a viable configuration folder.\n"
                              "Please check the log for details.");
    LOG(FATAL) << "Could not determine a valid config folder.";
  }

  LOG(INFO) << "Config path: " << config_path;

  CefString cache_path(&settings.cache_path);
  cache_path = config_path + sep + "cache";
  _settings_path = config_path;

  settings.background_color = CefColorSetARGB(0xff, 0x1c, 0x1c, 0x1c);
}

#ifndef OS_APPLE

// Keep in sync with knossos_helper_app.cc
bool KnossosApp::OnProcessMessageReceived(CefRefPtr<CefBrowser> browser,
                                                CefRefPtr<CefFrame> frame,
                                                CefProcessId source_process,
                                                CefRefPtr<CefProcessMessage> message
) {
  return KnossosJsInterface::ProcessMessage(browser, frame, source_process, message);
}

// Keep in sync with knossos_helper_app.cc
void KnossosApp::OnWebKitInitialized()
{
  KnossosJsInterface::Init();
}

#endif
