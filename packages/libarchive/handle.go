package libarchive

// #cgo CFLAGS: -I${SRCDIR}/../../build/libarchive
// #cgo LDFLAGS: -L${SRCDIR}/../../build/libarchive/libarchive -larchive
//
// #include <stdlib.h>
// #include <libarchive/archive.h>
// #include <libarchive/archive_entry.h>
import "C"
import "unsafe"

type Archive struct {
	Error    error
	handle   *C.struct_archive
	Filename string
	Entry    Header
}

type Header struct {
	Pathname string
}

func OpenArchive(filename string) (*Archive, error) {
	a := new(Archive)
	a.handle = C.archive_read_new()
	a.Filename = filename

	if a.handle == nil {
		return nil, ErrAlloc
	}

	C.archive_read_support_filter_bzip2(a.handle)
	C.archive_read_support_filter_gzip(a.handle)
	C.archive_read_support_filter_lz4(a.handle)
	C.archive_read_support_filter_lzma(a.handle)
	C.archive_read_support_filter_lzop(a.handle)
	C.archive_read_support_filter_xz(a.handle)
	C.archive_read_support_filter_zstd(a.handle)

	C.archive_read_support_format_7zip(a.handle)
	C.archive_read_support_format_tar(a.handle)
	C.archive_read_support_format_rar(a.handle)
	C.archive_read_support_format_zip(a.handle)

	cfilename := C.CString(a.Filename)
	code := C.archive_read_open_filename(a.handle, cfilename, 4096)
	C.free(unsafe.Pointer(cfilename))

	if code != C.ARCHIVE_OK {
		a.Close()
		return nil, ErrAlloc
	}

	return a, nil
}

func (a *Archive) Next() bool {
	var entry *C.struct_archive_entry
	code := C.archive_read_next_header(a.handle, &entry)
	if code != C.ARCHIVE_OK {
		a.Error = ErrAlloc
		return false
	}

	a.Entry.Pathname = C.GoString(C.archive_entry_pathname(entry))
	return true
}

func (a *Archive) Close() error {
	C.archive_read_free(a.handle)
	return nil
}
