// Copyright (c) 2013 The Chromium Embedded Framework Authors. All rights
// reserved. Use of this source code is governed by a BSD-style license that
// can be found in the LICENSE file.

#ifndef CEF_TESTS_CEFSIMPLE_SIMPLE_APP_H_
#define CEF_TESTS_CEFSIMPLE_SIMPLE_APP_H_

#include "include/cef_app.h"
#include "renderer/knossos_js_interface.h"

// Implement application-level callbacks for the browser process.
class KnossosApp : public CefApp, public CefBrowserProcessHandler, public CefRenderProcessHandler {
 public:
  KnossosApp();

  // CefApp methods:
  virtual CefRefPtr<CefBrowserProcessHandler> GetBrowserProcessHandler()
      OVERRIDE {
    return this;
  }
  virtual CefRefPtr<CefRenderProcessHandler> GetRenderProcessHandler() OVERRIDE {
    return this;
  };

  // CefBrowserProcessHandler methods:
  virtual void OnContextInitialized() OVERRIDE;
  virtual void OnBeforeCommandLineProcessing(const CefString& process_type, CefRefPtr<CefCommandLine> command_line) OVERRIDE;

#ifndef OS_MAC
  // CefRenderProcessHandler methods:
  virtual void OnWebKitInitialized() OVERRIDE;
  virtual bool OnProcessMessageReceived(CefRefPtr<CefBrowser> browser, CefRefPtr<CefFrame> frame, CefProcessId source_process, CefRefPtr<CefProcessMessage> message) OVERRIDE;
#endif

  void InitializeSettings(CefSettings &settings, std::string appDataPath);
  std::string GetSettingsPath() { return _settings_path; };

 private:
  std::string _settings_path;

  // Include the default reference counting implementation.
  IMPLEMENT_REFCOUNTING(KnossosApp);
};

#endif  // CEF_TESTS_CEFSIMPLE_SIMPLE_APP_H_
