<script>
import Popper from 'vue-popperjs';
import 'vue-popperjs/dist/css/vue-popper.css';

export default {
    props: ['mod', 'tab'],

    components: {
        popper: Popper
    },

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

        openLog() {
            fs2mod.openFsoDebugLog();
        },

        uploadLog() {
            call(fs2mod.uploadFsoDebugLog, (result) => {
                if(result !== '') {
                    vm.popup_visible = true;
                    vm.popup_title = 'Uploaded Debug Log';
                    vm.popup_mode = 'debug_log';
                    vm.popup_content = result;
                }
            });
        },

        uninstallMod() {
            fs2mod.uninstall(this.mod.id, this.mod.version, []);
        },

        verifyIntegrity() {
            fs2mod.verifyModIntegrity(this.mod.id, this.mod.version);
        }
    }
};
</script>
<template>
    <div class="mod row">
        <div :class="{ 'mod-node': true, 'active': open }">
            <div class="mod-image">
                <img :src="mod.tile ? ((mod.tile.indexOf('://') === -1 ? 'file://' : '') + mod.tile) : 'images/modstock.jpg'" class="mod-stock">
                <div class="mod-logo-container" v-if="!mod.tile">
                    <img class="mod-logo-legacy img-responsive" v-if="mod.logo" :src="(mod.logo.indexOf('://') === -1 ? 'file://' : '') + mod.logo">
                </div>
            </div>
            <div class="mod-notifier">
                <img :src="'images/modnotify_' + mod.status + '.png'" class="notifier">
            </div>
            <div class="mod-banner" v-if="mod.installed">
                <div class="mod-banner mod-banner-blue" v-if="mod.status === 'update'">
                    <span>Update Avail!</span>
                </div>
                <div class="mod-banner mod-banner-blue" v-else-if="mod.status === 'updating'">
                    <span>Installing...</span>
                </div>
                <div class="mod-banner mod-banner-red" v-else-if="mod.status === 'error'">
                    <span>Error!</span>
                </div>
                <!--<div class="mod-banner mod-banner-green" v-else>
                    <span>Installed!</span>
                </div>-->
            </div>
            <div class="actions">
                <div class="btn-wrapper">
                    <button class="mod-btn btn-green" v-if="(mod.status === 'ready' || mod.status === 'update') && (mod.type === 'mod' || mod.type == 'tc')" @click="play">
                        <span class="btn-text">PLAY</span>
                    </button>

                    <button class="mod-btn btn-blue" v-if="mod.status === 'update'" @click="update">
                        <span class="btn-text">UPDATE</span>
                    </button>

                    <button class="mod-btn btn-red" v-if="mod.status === 'error'" @click="showErrors">
                        <span class="btn-text">ERROR</span>
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

                    <popper
                        v-if="mod.status !== 'updating'"
                        trigger="click"
                        @show="updateTools(); open = true"
                        @hide="open = false"
                        class="dropdown"
                        :options="{ modifiers: { keepTogether: { enabled: false }, arrow: { enabled: false } } }"
                    >
                        <div class="dropdown-content">
                            <button v-for="tool in tools" v-if="(mod.status === 'ready' || mod.status === 'update') && (mod.type === 'mod' || mod.type == 'tc')" @click="launchTool(tool)">Run {{ tool }}</button>
                            <button @click="openLog">Open Debug Log</button>
                            <button @click="uploadLog">Upload Debug Log</button>
                            <button v-if="mod.id !== 'FS2' && !mod.dev_mode" @click="install">Modify</button>
                            <button v-if="mod.type === 'mod' || mod.type == 'tc'" @click="showFsoSettings">FSO Settings</button>
                            <button v-if="mod.id !== 'FS2' && !mod.dev_mode" @click="uninstallMod">Uninstall</button>
                            <button v-if="mod.id !== 'FS2' && !mod.dev_mode" @click="verifyIntegrity">Verify file integrity</button>
                        </div>

                        <button class="dropbtn" slot="reference"></button>
                    </popper>
                </div>
            </div>
            <div class="mod-progress"><div class="bar" :style="'width: ' + mod.progress + '%'"></div></div>
            <div class="mod-title"><p>{{ mod.title }}</p></div>
        </div>
    </div>
</template>