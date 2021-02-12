#include "knossos_handler.h"

#include <windows.h>
#include <string>

#include "include/cef_browser.h"

void KnossosHandler::PlatformTitleChange(CefRefPtr<CefBrowser> browser,
                                        const CefString& title) {
  CefWindowHandle hwnd = browser->GetHost()->GetWindowHandle();
  if (hwnd)
    SetWindowText(hwnd, std::wstring(title).c_str());
}

CefRect KnossosHandler::GetScreenSize() {
  int width = GetSystemMetrics(SM_CXSCREEN);
  int height = GetSystemMetrics(SM_CYSCREEN);
  CefRect screen_size(0, 0, width, height);
  return screen_size;
}
