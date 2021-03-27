package ui

import (
	_ "embed"

	"github.com/inkyblackness/imgui-go/v4"
)

var (
	//go:embed Inter-Regular.otf
	interFontData []byte
	InterFont     imgui.Font

	//go:embed PTMono-Regular.ttf
	ptMonoFontData []byte
	PtMonoFont     imgui.Font
)

func loadFont(io imgui.IO) {
	fonts := io.Fonts()
	InterFont = fonts.AddFontFromMemoryTTF(interFontData, 18.0)
	PtMonoFont = fonts.AddFontFromMemoryTTF(ptMonoFontData, 17.0)
}
