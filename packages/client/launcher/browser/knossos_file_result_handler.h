#ifndef KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_FILE_RESULT_HANDLER
#define KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_FILE_RESULT_HANDLER

#include "include/cef_base.h"
#include "include/cef_browser.h"

class KnossosFileResultHandler : public CefRunFileDialogCallback {
public:
  KnossosFileResultHandler(CefRefPtr<CefFrame> request_frame, int promise_id, bool multi);

  virtual void
  OnFileDialogDismissed(int selected_accept_filter,
                        const std::vector<CefString> &file_paths) OVERRIDE;

private:
  CefRefPtr<CefFrame> request_frame_;
  int promise_id_;
  bool multi_;

  IMPLEMENT_REFCOUNTING(KnossosFileResultHandler);
};

#endif /* KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_FILE_RESULT_HANDLER */
