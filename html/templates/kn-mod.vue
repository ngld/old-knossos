<script>
export default {
    props: ['mod', 'tab'],

    data: () => ({
        dropdown_active: false,
        force_active: false
    }),

    methods: {
        showDetails() {
            vm.mod = this.mod;
            vm.page = 'details';
        }
    }
};
</script>
<template>
    <div class="mod row">
        <div :class="{ 'mod-node': true, 'active': force_active }">
            <div class="mod-image">
                <img :src="mod.tile_path ? ('file://' + mod.tile_path) : 'images/modstock.jpg'" class="mod-stock">
                <div class="mod-logo-container">
                    <img class="mod-logo-legacy img-responsive" v-if="mod.logo_path" :src="'file://' + mod.logo_path">
                </div>
            </div>
            <div class="mod-notifier" v-if="tab === 'home'">
                <img :src="'images/modnotify_' + mod.status + '.png'" class="notifier">
            </div>
            <div class="actions">
                <div class="btn-wrapper">
                    <kn-mod-buttons :tab="tab" :mod="mod"></kn-mod-buttons>

                    <button class="mod-btn btn-grey" v-if="tab !== 'develop'" v-on:click="showDetails">
                        <span class="btn-text">DETAILS</span>
                    </button>

                    <kn-dropdown v-if="tab === 'home'" @change="val => force_active = val">
                        <button>Run Fast Debug</button>
                        <button>Run Debug</button>
                        <button>Upload Debug Log</button>
                    </kn-dropdown>
                </div>
            </div>
            <div class="mod-progress"><div class="bar" :style="'width: ' + mod.progress + '%'"></div></div>
            <div class="mod-title">{{ mod.title }}</div>
        </div>
    </div>
</template>