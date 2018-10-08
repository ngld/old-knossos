<script>
export default {
    data: () => ({}),

    methods: {
        fixBuildSelection() {
            fs2mod.fixBuildSelection();
        },

        fixImages() {
            fs2mod.fixImages();
        }
    }
}
</script>
<template>
    <ul>
        <li><a href="#" @click.prevent="fixBuildSelection">Enforce build requirements for mods</a></li>
        <li><a href="#" @click.prevent="fixImages">Fix broken logos and tile pictures</a></li>
    </ul>
</template>