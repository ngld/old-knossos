#include "browser/knossos_handler.h"

#include <cstddef>
#include <sstream>
#include <string>

#include "browser/knossos_archive.h"
#include "include/base/cef_bind.h"
#include "include/cef_app.h"
#include "include/cef_parser.h"
#include "include/cef_path_util.h"
#include "include/views/cef_browser_view.h"
#include "include/views/cef_window.h"
#include "include/cef_menu_model.h"
#include "include/wrapper/cef_closure_task.h"
#include "include/wrapper/cef_helpers.h"

#include "browser/knossos_resource_handler.h"
#include "browser/knossos_archive_handler.h"

namespace {

KnossosHandler* g_instance = nullptr;

const int kDevToolsMenuItem = MENU_ID_USER_FIRST;

// Returns a data: URI with the specified contents.
std::string GetDataURI(const std::string& data, const std::string& mime_type) {
  return "data:" + mime_type + ";base64," +
         CefURIEncode(CefBase64Encode(data.data(), data.size()), false)
             .ToString();
}

}  // namespace

KnossosHandler::KnossosHandler(bool use_views, std::string settings_path)
    : use_views_(use_views), is_closing_(false), _settings_path(settings_path) {
  DCHECK(!g_instance);

  g_instance = this;

  CefString path;
  if (!CefGetPath(PK_DIR_RESOURCES, path)) {
    LOG(ERROR) << "Could not determine resource directory!";
  } else {
    std::string archive_path(path);
    archive_path += "/ui.kar";

    _resources = new KnossosArchive();
    int err = _resources->Open(archive_path);
    if (err != 0) {
      std::ostringstream msg;
      msg << "Failed to open resource archive " << archive_path << " (" << err << ").";
      LOG(ERROR) << msg.str();
      ShowError(msg.str());

      _resources = nullptr;
    }
  }
}

KnossosHandler::~KnossosHandler() {
  g_instance = nullptr;
}

// static
KnossosHandler* KnossosHandler::GetInstance() {
  return g_instance;
}

void KnossosHandler::OnTitleChange(CefRefPtr<CefBrowser> browser,
                                  const CefString& title) {
  CEF_REQUIRE_UI_THREAD();

  if (use_views_) {
    // Set the title of the window using the Views framework.
    CefRefPtr<CefBrowserView> browser_view =
        CefBrowserView::GetForBrowser(browser);
    if (browser_view) {
      CefRefPtr<CefWindow> window = browser_view->GetWindow();
      if (window)
        window->SetTitle(title);
    }
  } else {
    // Set the title of the window using platform APIs.
    PlatformTitleChange(browser, title);
  }
}

void KnossosHandler::OnAfterCreated(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();

  // Add to the list of existing browsers.
  browser_list_.push_back(browser);
}

bool KnossosHandler::DoClose(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();

  // Closing the main window requires special handling. See the DoClose()
  // documentation in the CEF header for a detailed destription of this
  // process.
  if (browser_list_.size() == 1) {
    // Set a flag to indicate that the window close should be allowed.
    is_closing_ = true;
  }

  // Allow the close. For windowed browsers this will result in the OS close
  // event being sent.
  return false;
}

void KnossosHandler::OnBeforeClose(CefRefPtr<CefBrowser> browser) {
  CEF_REQUIRE_UI_THREAD();

  // Remove from the list of existing browsers.
  BrowserList::iterator bit = browser_list_.begin();
  for (; bit != browser_list_.end(); ++bit) {
    if ((*bit)->IsSame(browser)) {
      browser_list_.erase(bit);
      break;
    }
  }

  if (browser_list_.empty()) {
    // All browser windows have closed. Quit the application message loop.
    CefQuitMessageLoop();
  }
}

void KnossosHandler::OnLoadError(CefRefPtr<CefBrowser> browser,
                                CefRefPtr<CefFrame> frame,
                                ErrorCode errorCode,
                                const CefString& errorText,
                                const CefString& failedUrl) {
  CEF_REQUIRE_UI_THREAD();

  // Don't display an error for downloaded files.
  if (errorCode == ERR_ABORTED)
    return;

  // Display a load error message using a data: URI.
  std::stringstream ss;
  ss << "<html><style>body { background: white; font-family: Helvetica, Arial, "
        "\"Lucida Grande\", sans-serif; }</style><body>"
        "<h2>Failed to load URL "
     << std::string(failedUrl) << " with error " << std::string(errorText)
     << " (" << errorCode << ").</h2></body></html>";

  frame->LoadURL(GetDataURI(ss.str(), "text/html"));
}

void KnossosHandler::CloseAllBrowsers(bool force_close) {
  if (!CefCurrentlyOn(TID_UI)) {
    // Execute on the UI thread.
    CefPostTask(TID_UI, base::Bind(&KnossosHandler::CloseAllBrowsers, this,
                                   force_close));
    return;
  }

  if (browser_list_.empty())
    return;

  BrowserList::const_iterator it = browser_list_.begin();
  for (; it != browser_list_.end(); ++it)
    (*it)->GetHost()->CloseBrowser(force_close);
}

bool KnossosHandler::OnProcessMessageReceived(CefRefPtr<CefBrowser> browser,
                                        CefRefPtr<CefFrame> frame,
                                        CefProcessId source_process,
                                        CefRefPtr<CefProcessMessage> message) {
  const std::string& message_name = message->GetName();
  if (message_name == "knDevToolsRequest") {
    ShowDevTools(browser);
    return true;
  }

  return false;
}

void KnossosHandler::OnBeforeContextMenu(CefRefPtr<CefBrowser> browser,
                                         CefRefPtr<CefFrame> frame,
                                         CefRefPtr<CefContextMenuParams> params,
                                         CefRefPtr<CefMenuModel> model) {
  model->AddSeparator();
  model->AddItem(kDevToolsMenuItem, "Show DevTools");
}

bool KnossosHandler::OnContextMenuCommand(CefRefPtr<CefBrowser> browser,
                                          CefRefPtr<CefFrame> frame,
                                          CefRefPtr<CefContextMenuParams> params,
                                          int command_id,
                                          CefContextMenuHandler::EventFlags event_flags) {
  if (command_id == kDevToolsMenuItem) {
    ShowDevTools(browser);
    return true;
  }

  return false;
}

bool KnossosHandler::OnBeforeBrowse(CefRefPtr<CefBrowser> browser,
                                    CefRefPtr<CefFrame> frame,
                                    CefRefPtr<CefRequest> request,
                                    bool user_gesture,
                                    bool is_redirect) {
  LOG(INFO) << "Browsing to " << request->GetURL();

  return false;
}

CefRefPtr<CefResourceRequestHandler> KnossosHandler::GetResourceRequestHandler(
  CefRefPtr<CefBrowser> browser,
  CefRefPtr<CefFrame> frame,
  CefRefPtr<CefRequest> request,
  bool is_navigation,
  bool is_download,
  const CefString& request_initiator,
  bool& disable_default_handling
) {
  if (is_download) {
    disable_default_handling = true;
    LOG(WARNING) << "Aborted download " << request->GetURL() << " from " << request_initiator;
  } else {
    std::string url = request->GetURL();
    if (url.substr(0, 11) != "devtools://")
      LOG(INFO) << "Request " << request->GetURL() << " from " << request_initiator << " (" << request->GetReferrerURL() << ")";

    if (!request_initiator.empty()) {
      if (url.substr(0, 34) == "https://files.client.fsnebula.org/") {
        return new KnossosArchiveHandler(_resources, 34);
      }

      if (url.substr(0, 32) == "https://api.client.fsnebula.org/") {
        return new KnossosResourceHandler();
      }
    }
  }

  return nullptr;
}

void KnossosHandler::ShowDevTools(CefRefPtr<CefBrowser> browser) {
  CefWindowInfo window_info;
  CefBrowserSettings settings;
  CefPoint point;
  CefRefPtr<CefClient> client = browser->GetHost()->GetClient();

#ifdef OS_WIN
  window_info.SetAsPopup(browser->GetHost()->GetWindowHandle(), "dev_tools");
#else
  CefRect screen_size = GetScreenSize();
  window_info.width = screen_size.width - 200;
  window_info.height = 400;

  window_info.x = (screen_size.width - window_info.width) / 2;
  window_info.y = screen_size.height / 2 + 500;

  CefString(&window_info.window_name).FromASCII("dev_tools");
#endif

  browser->GetHost()->ShowDevTools(window_info, client, settings, point);
}
