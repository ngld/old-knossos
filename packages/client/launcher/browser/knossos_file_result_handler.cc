#include "browser/knossos_file_result_handler.h"

#include "include/cef_process_message.h"
#include "include/cef_values.h"

KnossosFileResultHandler::KnossosFileResultHandler(
    CefRefPtr<CefFrame> request_frame, int promise_id, bool multi)
    : request_frame_(request_frame), promise_id_(promise_id), multi_(multi) {}

void KnossosFileResultHandler::OnFileDialogDismissed(
    int selected_accept_filter, const std::vector<CefString> &file_paths) {
  if (multi_) {
    auto msg = CefProcessMessage::Create("knResolvePromiseWithStringArray");
    auto args = msg->GetArgumentList();

    auto list = CefListValue::Create();
    for (size_t i = 0; i < file_paths.size(); i++) {
      list->SetString(i, file_paths[i]);
    }

    args->SetInt(0, promise_id_);
    args->SetList(1, list);

    request_frame_->SendProcessMessage(PID_RENDERER, msg);
  } else {
    auto msg = CefProcessMessage::Create("knResolvePromiseWithString");
    auto args = msg->GetArgumentList();

    args->SetInt(0, promise_id_);
    if (file_paths.size() < 1) {
      args->SetString(1, "");
    } else {
      args->SetString(1, file_paths[0]);
    }

    request_frame_->SendProcessMessage(PID_RENDERER, msg);
  }
}
