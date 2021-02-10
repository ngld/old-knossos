// Copyright (c) 2013 The Chromium Embedded Framework Authors. All rights
// reserved. Use of this source code is governed by a BSD-style license that
// can be found in the LICENSE file.

#include "knossos_app.h"

#include <string>

#include "include/cef_browser.h"
#include "include/cef_command_line.h"
#include "include/cef_path_util.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_window.h"
#include "include/wrapper/cef_helpers.h"
#include "include/wrapper/cef_closure_task.h"
#include "browser/knossos_handler.h"
#include "libbrain.h"

namespace {

// When using the Views framework this object provides the delegate
// implementation for the CefWindow that hosts the Views-based browser.
class KnossosWindowDelegate : public CefWindowDelegate {
 public:
  explicit KnossosWindowDelegate(CefRefPtr<CefBrowserView> browser_view)
      : browser_view_(browser_view) {}

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

  CefSize GetPreferredSize(CefRefPtr<CefView> view) OVERRIDE {
    return CefSize(1000, 700);
  }

 private:
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
    // Create a new top-level Window for the popup. It will show itself after
    // creation.
    CefWindow::CreateTopLevelWindow(
        new KnossosWindowDelegate(popup_browser_view));

    // We created the Window.
    return true;
  }

 private:
  IMPLEMENT_REFCOUNTING(KnossosBrowserViewDelegate);
  DISALLOW_COPY_AND_ASSIGN(KnossosBrowserViewDelegate);
};

void KnossosLogger(uint8_t level, char* message, int length) {
  std::string msg((const char*)message, length);
  switch (level) {
    case KNOSSOS_LOG_INFO:
      LOG(INFO) << msg;
      break;
case KNOSSOS_LOG_WARNING:
  LOG(WARNING) << msg;
  break;
case KNOSSOS_LOG_ERROR:
  LOG(ERROR) << msg;
  break;
case KNOSSOS_LOG_FATAL:
  LOG(FATAL) << msg;
  break;
default:
  LOG(FATAL) << "Invalid log level passed to KnossosLogger: " << level;
  }
}

static void PrepareBrain() {
  CefString resource_path;
  if (!CefGetPath(PK_DIR_RESOURCES, resource_path)) {
    LOG(FATAL) << "Resource directory not found";
  }

  std::string path_conv = resource_path;
  if (!KnossosInit((char*)path_conv.c_str(), path_conv.size(), &KnossosLogger)) {
    LOG(FATAL) << "Failed to initialize brain";
  }
}

}  // namespace

KnossosApp::KnossosApp() {}

void KnossosApp::OnBeforeCommandLineProcessing(const CefString& process_type, CefRefPtr<CefCommandLine> command_line) {
  if (process_type.empty()) {
    // Don't create a "GPUCache" directory when cache-path is unspecified.
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

  const bool enable_chrome_runtime = false;
      //command_line->HasSwitch("enable-chrome-runtime");

#if defined(OS_WIN) || defined(OS_LINUX)
  // Create the browser using the Views framework if "--use-views" is specified
  // via the command-line. Otherwise, create the browser using the native
  // platform framework. The Views framework is currently only supported on
  // Windows and Linux.
  const bool use_views = command_line->HasSwitch("use-views");
#else
  const bool use_views = false;
#endif

  // KnossosHandler implements browser-level callbacks.
  CefRefPtr<KnossosHandler> handler(new KnossosHandler(use_views));

  // Specify CEF browser settings here.
  CefBrowserSettings browser_settings;

  std::string url;

  // Check if a "--url=" value was provided via the command-line. If so, use
  // that instead of the default URL.
  url = command_line->GetSwitchValue("url");
  if (url.empty())
    url = "https://nu.fsnebula.org";

  if (use_views && !enable_chrome_runtime) {
    // Create the BrowserView.
    CefRefPtr<CefBrowserView> browser_view = CefBrowserView::CreateBrowserView(
        handler, url, browser_settings, nullptr, nullptr,
        new KnossosBrowserViewDelegate());

    // Create the Window. It will show itself after creation.
    CefWindow::CreateTopLevelWindow(new KnossosWindowDelegate(browser_view));
  } else {
    // Information used when creating the native window.
    CefRect screen_size = handler->GetScreenSize();

    CefWindowInfo window_info;
    window_info.width = 1200;
    window_info.height = 800;

    window_info.x = (screen_size.width - window_info.width) / 2;
    window_info.y = (screen_size.height - window_info.height) / 2 - 200;

#if defined(OS_WIN)
    // On Windows we need to specify certain flags that will be passed to
    // CreateWindowEx().
    window_info.SetAsPopup(NULL, "knossos");
#endif

    // Create the first browser window.
    CefBrowserHost::CreateBrowser(window_info, handler, url, browser_settings,
                                  nullptr, nullptr);
  }

  CefPostTask(TID_IO, base::Bind(PrepareBrain));
}

