#include "browser/knossos_handler.h"

#import <Cocoa/Cocoa.h>

#include "include/cef_browser.h"
#include "include/wrapper/cef_helpers.h"

void KnossosHandler::PlatformTitleChange(CefRefPtr<CefBrowser> browser,
                                        const CefString& title) {
  NSView* view =
      CAST_CEF_WINDOW_HANDLE_TO_NSVIEW(browser->GetHost()->GetWindowHandle());
  NSWindow* window = [view window];
  std::string titleStr(title);
  NSString* str = [NSString stringWithUTF8String:titleStr.c_str()];
  [window setTitle:str];
}

CefRect KnossosHandler::GetScreenSize() {
  CGSize rect = [NSScreen mainScreen].frame.size;
  return CefRect(0, 0, rect.width, rect.height);
}
