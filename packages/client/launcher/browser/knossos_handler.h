#ifndef KNOSSOS_LAUNCHER_KNOSSOS_HANDLER
#define KNOSSOS_LAUNCHER_KNOSSOS_HANDLER

#include <list>

#include "browser/knossos_archive.h"
#include "include/base/cef_callback.h"
#include "include/cef_client.h"
#include "include/cef_drag_handler.h"
#include "include/cef_thread.h"
#include "include/internal/cef_ptr.h"

class KnossosHandler : public CefClient,
                       public CefDisplayHandler,
                       public CefLifeSpanHandler,
                       public CefLoadHandler,
                       public CefContextMenuHandler,
                       public CefRequestHandler,
                       public CefDragHandler {
public:
  explicit KnossosHandler(bool use_views, std::string settings_path);
  ~KnossosHandler();

  // Provide access to the single global instance of this object.
  static KnossosHandler *GetInstance();

  // CefClient methods:
  virtual CefRefPtr<CefDisplayHandler> GetDisplayHandler() OVERRIDE {
    return this;
  }
  virtual CefRefPtr<CefLifeSpanHandler> GetLifeSpanHandler() OVERRIDE {
    return this;
  }
  virtual CefRefPtr<CefLoadHandler> GetLoadHandler() OVERRIDE { return this; }
  virtual CefRefPtr<CefContextMenuHandler> GetContextMenuHandler() OVERRIDE {
    return this;
  }
  virtual CefRefPtr<CefRequestHandler> GetRequestHandler() OVERRIDE {
    return this;
  }
  virtual CefRefPtr<CefDragHandler> GetDragHandler() OVERRIDE { return this; }

  virtual bool
  OnProcessMessageReceived(CefRefPtr<CefBrowser> browser,
                           CefRefPtr<CefFrame> frame,
                           CefProcessId source_process,
                           CefRefPtr<CefProcessMessage> message) OVERRIDE;

  // CefDisplayHandler methods:
  virtual void OnTitleChange(CefRefPtr<CefBrowser> browser,
                             const CefString &title) OVERRIDE;

  // CefLifeSpanHandler methods:
  /*virtual bool OnBeforePopup( CefRefPtr< CefBrowser > browser, CefRefPtr<
   * CefFrame > frame, const CefString& target_url, const CefString&
   * target_frame_name, CefLifeSpanHandler::WindowOpenDisposition
   * target_disposition, bool user_gesture, const CefPopupFeatures&
   * popupFeatures, CefWindowInfo& windowInfo, CefRefPtr< CefClient >& client,
   * CefBrowserSettings& settings, CefRefPtr< CefDictionaryValue >& extra_info,
   * bool* no_javascript_access ) OVERRIDE;*/
  virtual void OnAfterCreated(CefRefPtr<CefBrowser> browser) OVERRIDE;
  virtual bool DoClose(CefRefPtr<CefBrowser> browser) OVERRIDE;
  virtual void OnBeforeClose(CefRefPtr<CefBrowser> browser) OVERRIDE;

  // CefLoadHandler methods:
  virtual void OnLoadError(CefRefPtr<CefBrowser> browser,
                           CefRefPtr<CefFrame> frame, ErrorCode errorCode,
                           const CefString &errorText,
                           const CefString &failedUrl) OVERRIDE;

  // CefContextMenuHandler methods:
  virtual void OnBeforeContextMenu(CefRefPtr<CefBrowser> browser,
                                   CefRefPtr<CefFrame> frame,
                                   CefRefPtr<CefContextMenuParams> params,
                                   CefRefPtr<CefMenuModel> model) OVERRIDE;
  virtual bool
  OnContextMenuCommand(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
                       CefRefPtr<CefContextMenuParams> params, int command_id,
                       CefContextMenuHandler::EventFlags event_flags) OVERRIDE;

  // CefRequestHandler methods:
  virtual bool OnBeforeBrowse(CefRefPtr<CefBrowser> browser,
                              CefRefPtr<CefFrame> frame,
                              CefRefPtr<CefRequest> request, bool user_gesture,
                              bool is_redirect) OVERRIDE;
  virtual CefRefPtr<CefResourceRequestHandler> GetResourceRequestHandler(
      CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
      CefRefPtr<CefRequest> request, bool is_navigation, bool is_download,
      const CefString &request_initiator,
      bool &disable_default_handling) OVERRIDE;

  // CefDragHandler methods:
  void OnDraggableRegionsChanged(
      CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame,
      const std::vector<CefDraggableRegion> &regions) OVERRIDE;

  // Request that all existing browser windows close.
  void CloseAllBrowsers(bool force_close);
  void BroadcastMessage(CefRefPtr<CefProcessMessage> message);

  bool IsClosing() const { return is_closing_; }

  CefRect GetScreenSize();
  std::string GetSettingsPath() { return _settings_path; };
  CefRefPtr<CefBrowser> GetMainBrowser() { return browser_list_.front(); };

  bool PostKnossosTask(CefRefPtr<CefTask> task);
  bool PostKnossosTask(const base::Closure &closure);

  static void ShowError(std::string message);

private:
  friend class KnossosApp;

  // Platform-specific implementation.
  void PlatformTitleChange(CefRefPtr<CefBrowser> browser,
                           const CefString &title);
  void SaveFileDialog(CefRefPtr<CefBrowser> browser, std::string title,
                      std::string message, std::string default_filename,
                      std::string folder,
                      const base::Callback<void(bool, std::string)> callback);
  void OpenFileDialog(CefRefPtr<CefBrowser> browser, std::string title,
                      std::string message, std::string default_filename,
                      std::string folder,
                      const base::Callback<void(bool, std::string)> callback);
  void OpenFolderDialog(CefRefPtr<CefBrowser> browser, std::string title,
                        std::string message, std::string folder,
                        const base::Callback<void(bool, std::string)> callback);

  // True if the application is using the Views framework.
  const bool use_views_;

  // List of existing browser windows. Only accessed on the CEF UI thread.
  typedef std::list<CefRefPtr<CefBrowser>> BrowserList;
  BrowserList browser_list_;

  bool is_closing_;
  CefRefPtr<KnossosArchive> _resources;

  std::string _settings_path;
  CefRefPtr<CefThread> knossos_thread_;

  // Include the default reference counting implementation.
  IMPLEMENT_REFCOUNTING(KnossosHandler);
};

#endif /* KNOSSOS_LAUNCHER_KNOSSOS_HANDLER */
