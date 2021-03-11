#include "browser/knossos_handler.h"
#include "include/base/cef_callback_forward.h"

#import <Cocoa/Cocoa.h>

#include "include/base/cef_callback.h"
#include "include/cef_browser.h"
#include "include/wrapper/cef_helpers.h"

void KnossosHandler::PlatformTitleChange(CefRefPtr<CefBrowser> browser,
                                         const CefString &title) {
  NSView *view =
      CAST_CEF_WINDOW_HANDLE_TO_NSVIEW(browser->GetHost()->GetWindowHandle());
  NSWindow *window = [view window];
  std::string titleStr(title);
  NSString *str = [NSString stringWithUTF8String:titleStr.c_str()];
  [window setTitle:str];
}

CefRect KnossosHandler::GetScreenSize() {
  CGSize rect = [NSScreen mainScreen].frame.size;
  return CefRect(0, 0, rect.width, rect.height);
}

void KnossosHandler::ShowError(std::string message) {
  NSString *text = [[NSString alloc] initWithUTF8String:message.c_str()];

  NSAlert *alert = [[NSAlert alloc] init];
  [alert addButtonWithTitle:@"OK"];
  [alert setMessageText:text];
  [alert setAlertStyle:NSAlertStyleCritical];
  [alert runModal];
}

static void RunSavePanel(NSSavePanel *panel, CefRefPtr<CefBrowser> browser,
                         std::string title, std::string message,
                         std::string default_filename, std::string folder,
                         base::Callback<void(bool, std::string)> callback) {
  panel.title = [NSString stringWithUTF8String:title.c_str()];
  panel.message = [NSString stringWithUTF8String:message.c_str()];
  panel.nameFieldStringValue =
      [NSString stringWithUTF8String:default_filename.c_str()];
  panel.directoryURL =
      [NSURL fileURLWithPath:[NSString stringWithUTF8String:folder.c_str()]
                 isDirectory:YES];

  NSView *view =
      CAST_CEF_WINDOW_HANDLE_TO_NSVIEW(browser->GetHost()->GetWindowHandle());
  NSWindow *window = [view window];

  [panel beginSheetModalForWindow:window
                completionHandler:^(NSModalResponse result) {
                  bool success = result == NSFileHandlingPanelOKButton;
                  std::string path;

                  if (panel.URL != nil) {
                    path = panel.URL.path.UTF8String;
                  }
                  callback.Run(success, path);
                }];
}

void KnossosHandler::SaveFileDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string default_filename, std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  NSSavePanel *panel = [NSSavePanel savePanel];
  panel.prompt = @"Save";
  RunSavePanel(panel, browser, title, message, default_filename, folder,
               callback);
}

void KnossosHandler::OpenFileDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string default_filename, std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  NSOpenPanel *panel = [NSOpenPanel openPanel];
  panel.canChooseFiles = YES;
  panel.canChooseDirectories = NO;
  panel.allowsMultipleSelection = NO;
  panel.prompt = @"Open";
  RunSavePanel(panel, browser, title, message, default_filename, folder,
               callback);
}

void KnossosHandler::OpenFolderDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  NSOpenPanel *panel = [NSOpenPanel openPanel];
  panel.canChooseFiles = NO;
  panel.canChooseDirectories = YES;
  panel.allowsMultipleSelection = NO;
  panel.prompt = @"Open Folder";
  RunSavePanel(panel, browser, title, message, "", folder, callback);
}
