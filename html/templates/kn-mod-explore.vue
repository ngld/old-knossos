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
        ...require('../js/mod_button_methods.js').default,

        showDetails() {
            vm.detail_mod = this.mod.id;
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
        <div :class="{ 'mod-node': true, 'active': open, 'retail-dependency-missing': mod.retail_dependency_missing }">
            <div class="mod-image">
                <img :src="mod.tile ? ((mod.tile.indexOf('://') === -1 ? 'file://' : '') + mod.tile) : 'images/modstock.jpg'" class="mod-stock">
                <div class="mod-logo-container" v-if="!mod.tile">
                    <img class="mod-logo-legacy img-responsive" v-if="mod.logo" :src="(mod.logo.indexOf('://') === -1 ? 'file://' : '') + mod.logo">
                </div>
            </div>
            <div class="mod-status" v-if="mod.installed || mod.retail_dependency_missing">
                <div class="mod-banner mod-banner-blue" v-if="mod.status === 'update'">
                    <span>Update Avail!</span>
                </div>
                <div class="mod-banner mod-banner-blue" v-else-if="mod.status === 'updating'">
                    <span>Installing...</span>
                </div>
                <div class="mod-banner mod-banner-grey" v-else-if="mod.retail_dependency_missing">
                    <span>Requires FS2</span>
                </div>
                <div class="mod-banner mod-banner-green" v-else>
                    <span>Installed!</span>
                </div>
            </div>
            <div class="actions">
                <div class="btn-wrapper">
                    <button class="mod-btn btn-blue" v-if="mod.status === 'update'" @click="update">
                        <span class="btn-text">UPDATE</span>
                    </button>

                    <button class="mod-btn btn-red" v-if="mod.status === 'error'" @click="showErrors">
                        <span class="btn-text">ERROR</span>
                    </button>

                    <button class="mod-btn btn-blue" v-if="mod.status !== 'update' && mod.status !== 'updating'" @click="install">
                        <span class="btn-text">{{ mod.installed ? 'MODIFY' : 'INSTALL' }}</span>
                    </button>

                    <button class="mod-btn btn-blue" v-if="mod.status === 'updating'" @click="showProgress">
                        <span class="small-btn-text">
                            INSTALLING...<br>
                            {{ Math.round(mod.progress) }}%
                        </span>
                    </button>

                    <button class="mod-btn btn-orange" v-if="mod.status === 'updating'" @click="cancel">
                        <span class="btn-text">CANCEL</span>
                    </button>

                    <button class="mod-btn btn-grey" v-if="tab !== 'develop'" v-on:click="showDetails">
                        <span class="btn-text">DETAILS</span>
                    </button>
                </div>
            </div>
            <div class="mod-progress"><div class="bar" :style="'width: ' + mod.progress + '%'"></div></div>
            <div class="mod-title"><p>{{ mod.title }}</p></div>
        </div>
    </div>
</template>