#include "knossos_helper_app.h"

#include "renderer/knossos_js_interface.h"

#ifdef OS_MAC

// Keep in sync with knossos_app.cc
void KnossosHelperApp::OnWebKitInitialized()
{
  KnossosJsInterface::Init();
}

#endif
