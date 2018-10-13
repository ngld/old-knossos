<script>
export default {
    data: () => ({}),

    methods: {
        fixBuildSelection() {
            fs2mod.fixBuildSelection();
        },

        fixImages() {
            fs2mod.fixImages(false);
        },

        fixDevImages() {
            fs2mod.fixImages(true);
        },

        rewriteModJson() {
            fs2mod.rewriteModJson();
        }
    }
}
</script>
<template>
    <ul>
        <li>
            <p><a href="#" @click.prevent="fixBuildSelection">Enforce build requirements for mods</a></p>
            <p>
                Use this if you get an FSO error complaining about
                "Missing required token: [#END]. Found [$Target Version:] instead."
                or something similar. It makes sure that your selected FSO builds (in FSO settings) are correct for each
                mod.
            </p>
        </li>
        <li>
            <p><a href="#" @click.prevent="fixImages">Fix broken/missing mod images</a></p>
            <p>
                Use this if one or more mods have broken pictures in Knossos (this doesn't affect the actual game;
                in that case, go to the Home tab, hover over the dropdown button and click "Verify file integrity").
            </p>
            <p><strong>NOTE:</strong> This skips mods on your Dev tab since that might overwrite your local changes.</p>
        </li>
        <li>
            <p><a href="#" @click.prevent="fixDevImages">Fix broken/missing mod images for dev mods</a></p>
            <p>
                This only checks mods on your Dev tab. Beware that any local changes to logo, tile, banner images and
                screenshots will be lost.
            </p>
        </li>
        <li>
            <p><a href="#" @click.prevent="rewriteModJson">Discard local changes to mod.json files</a></p>
            <p>
                This can fix weird issues caused by invalid values in your local mod.json file (which contains the mod
                metadata for each installed mod).
            </p>
        </li>
    </ul>
</template>