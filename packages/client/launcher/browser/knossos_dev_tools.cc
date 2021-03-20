#include "knossos_dev_tools.h"

#include "include/cef_base.h"
#include "include/base/cef_macros.h"
#include "include/cef_browser.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_panel.h"
#include "include/views/cef_window.h"
#include "include/views/cef_window_delegate.h"

#include "browser/knossos_handler.h"

void KnossosDevToolsWindowDelegate::OnWindowCreated(CefRefPtr<CefWindow> window) {
  window->AddChildView(browser_view_);
  window->Show();
}

void KnossosDevToolsWindowDelegate::OnWindowDestroyed(CefRefPtr<CefWindow> window) {
  browser_view_ = nullptr;
}

CefRect KnossosDevToolsWindowDelegate::GetInitialBounds(CefRefPtr<CefWindow> window) {
  CefRect screen_size = KnossosHandler::GetInstance()->GetScreenSize();
  CefRect window_size;

  window_size.width = screen_size.width - 200;
  window_size.height = 400;

  window_size.x = (screen_size.width - window_size.width) / 2;
  window_size.y = screen_size.height / 2 + 500;

  return window_size;
}

void KnossosShowDevTools(CefRefPtr<CefBrowser> browser) {
  CefWindowInfo window_info;
  CefBrowserSettings settings;
  CefPoint point;
  CefRefPtr<CefClient> client = browser->GetHost()->GetClient();

#ifdef OS_MAC
  CefRect screen_size = KnossosHandler::GetInstance()->GetScreenSize();
  window_info.width = screen_size.width - 200;
  window_info.height = 400;

  window_info.x = (screen_size.width - window_info.width) / 2;
  window_info.y = screen_size.height / 2 + 500;

  CefString(&window_info.window_name).FromASCII("dev_tools");
#endif

  browser->GetHost()->ShowDevTools(window_info, client, settings, point);
}
