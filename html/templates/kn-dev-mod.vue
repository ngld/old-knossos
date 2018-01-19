<script>
export default {
    props: ['mod']
};
</script>
<template>
    <div class="mod row">
        <div class="dev-mod-node">
            <div class="mod-image">
                <img :src="mod.tile ? ('file://' + mod.tile) : 'images/modstock.jpg'" class="mod-stock">
                <div class="mod-logo-container" v-if="!mod.tile">
                    <img class="mod-logo-legacy img-responsive" v-if="mod.logo" :src="'file://' + mod.logo">
                </div>
            </div>
            <div class="mod-progress"><div class="bar" :style="'width: ' + mod.progress + '%'"></div></div>
            <div class="mod-title"><p>{{ mod.title }}</p></div>
        </div>
    </div>
</template>