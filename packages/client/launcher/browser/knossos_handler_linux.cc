#include "browser/knossos_handler.h"

#if defined(CEF_X11)
#include <X11/Xatom.h>
#include <X11/Xlib.h>

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#include <gtk/gtk.h>
#pragma GCC diagnostic pop
#endif

#include <string>

#include "include/base/cef_logging.h"
#include "include/cef_browser.h"
#include "include/wrapper/cef_helpers.h"

void KnossosHandler::PlatformTitleChange(CefRefPtr<CefBrowser> browser,
                                         const CefString& title) {
  std::string titleStr(title);

#if defined(CEF_X11)
  // Retrieve the X11 display shared with Chromium.
  ::Display* display = cef_get_xdisplay();
  DCHECK(display);

  // Retrieve the X11 window handle for the browser.
  ::Window window = browser->GetHost()->GetWindowHandle();
  if (window == kNullWindowHandle)
    return;

  // Retrieve the atoms required by the below XChangeProperty call.
  const char* kAtoms[] = {"_NET_WM_NAME", "UTF8_STRING"};
  Atom atoms[2];
  int result =
      XInternAtoms(display, const_cast<char**>(kAtoms), 2, false, atoms);
  if (!result)
    NOTREACHED();

  // Set the window title.
  XChangeProperty(display, window, atoms[0], atoms[1], 8, PropModeReplace,
                  reinterpret_cast<const unsigned char*>(titleStr.c_str()),
                  titleStr.size());

  // TODO(erg): This is technically wrong. So XStoreName and friends expect
  // this in Host Portable Character Encoding instead of UTF-8, which I believe
  // is Compound Text. This shouldn't matter 90% of the time since this is the
  // fallback to the UTF8 property above.
  XStoreName(display, browser->GetHost()->GetWindowHandle(), titleStr.c_str());
#endif  // defined(CEF_X11)
}

CefRect KnossosHandler::GetScreenSize() {
  CEF_REQUIRE_UI_THREAD();
  CefRect screen_size;

#if defined(CEF_X11)
  XWindowAttributes attrs;
  XGetWindowAttributes(cef_get_xdisplay(), XDefaultRootWindow(cef_get_xdisplay()), &attrs);

  screen_size.width = attrs.width;
  screen_size.height = attrs.height;
#endif

  return screen_size;
}

void KnossosHandler::ShowError(std::string msg) {
  gtk_init(0, 0);

  auto dialog = gtk_message_dialog_new(NULL, GTK_DIALOG_MODAL,
      GTK_MESSAGE_ERROR, GTK_BUTTONS_CLOSE, "%s", msg.c_str());
  gtk_dialog_run(GTK_DIALOG(dialog));
  gtk_widget_destroy(dialog);
}

void KnossosHandler::SaveFileDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string default_filename, std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  // TODO
}

void KnossosHandler::OpenFileDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string default_filename, std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  // TODO
}

void KnossosHandler::OpenFolderDialog(
    CefRefPtr<CefBrowser> browser, std::string title, std::string message,
    std::string folder,
    const base::Callback<void(bool, std::string)> callback) {
  // TODO
}
