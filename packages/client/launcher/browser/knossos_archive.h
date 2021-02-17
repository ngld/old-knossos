#ifndef KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE
#define KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE

#include <fstream>
#include <string>
#include <map>
#include "include/base/cef_lock.h"
#include "include/cef_base.h"

typedef struct {
  int32_t offset;
  int32_t size;
  int32_t dec_size;
} KnossosArchiveItem;

class KnossosArchive: public CefBaseRefCounted {
  public:
  KnossosArchive();
  int Open(std::string filename);
  void ReadEntry(std::string name, int32_t &size, void **data);
  void Close();

  private:
  std::ifstream _hdl;
  std::map<std::string, KnossosArchiveItem> _items;
  base::Lock _lock;

  IMPLEMENT_REFCOUNTING(KnossosArchive);
};

#endif /* KNOSSOS_LAUNCHER_BROWSER_KNOSSOS_ARCHIVE */
