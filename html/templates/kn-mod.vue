<script>
export default {
    props: ['mod', 'tab'],

    data: () => ({
        dropdown_active: false,
        open: false,
        tools: [],
        tools_built: false
    }),

    watch: {
        mod(new_mod) {
            this.mod = new_mod;
            this.tools_built = false;

            if(this.open) this.updateTools();
        }
    },

    methods: {
        showDetails() {
            vm.mod = this.mod;
            vm.page = 'details';
        },

        updateTools() {
            if(this.tools_built) return;
            this.tools_built = true;

            call(fs2mod.getModTools, this.mod.id, this.mod.version, (tools) => {
                this.tools = tools;
            });
        },

        launchTool(label) {
            fs2mod.runModTool(this.mod.id, this.mod.version, '', '', label);
        },

        uploadLog() {
            alert('Not yet implemented!');
        },

        uninstallMod() {
            fs2mod.uninstall(this.mod.id, this.mod.version, []);
        }
    }
};
</script>
<template>
    <div class="mod row">
        <div :class="{ 'mod-node': true, 'active': open }">
            <div class="mod-image">
                <img :src="mod.tile ? ((mod.tile.indexOf('://') === -1 ? 'file://' : '') + mod.tile) : 'images/modstock.jpg'" class="mod-stock">
                <div class="mod-logo-container">
                    <img class="mod-logo-legacy img-responsive" v-if="mod.logo" :src="(mod.logo.indexOf('://') === -1 ? 'file://' : '') + mod.logo">
                </div>
            </div>
            <div class="mod-installed" v-if="tab === 'explore' && mod.installed">
                <div class="mod-banner">
                    <span v-if="!mod.versions[0].installed">Older Version</span>
                    <span v-else>Installed!</span>
                </div>
            </div>
            <div class="mod-notifier" v-if="tab === 'home'">
                <img :src="'images/modnotify_' + (tab === 'home' ? mod.status : 'ready') + '.png'" class="notifier">
            </div>
            <div class="actions">
                <div class="btn-wrapper">
                    <kn-mod-buttons :tab="tab" :mod="mod"></kn-mod-buttons>

                    <button class="mod-btn btn-grey" v-if="tab !== 'develop'" v-on:click="showDetails">
                        <span class="btn-text">DETAILS</span>
                    </button>

                    <kn-dropdown v-if="tab === 'home'" @open="updateTools(); open = true" @close="open = false">
                        <button v-for="tool in tools" @click="launchTool(tool)">Run {{ tool }}</button>
                        <button @click="uploadLog">Upload Debug Log</button>
                        <button v-if="mod.id !== 'FS2' && mod.status !== 'updating' && !mod.dev_mode" @click="uninstallMod">Uninstall</button>
                    </kn-dropdown>
                </div>
            </div>
            <div class="mod-progress"><div class="bar" :style="'width: ' + mod.progress + '%'"></div></div>
            <div class="mod-title"><p>{{ mod.title }} {{ mod.version }}</p></div>
        </div>
    </div>
</template>