<script>
export default {
    props: ['mod', 'tab'],

    methods: {
        play() {
            fs2mod.runMod(this.mod.id, this.mod.version);
        },

        update() {
            fs2mod.updateMod(this.mod.id, this.mod.version);
        },

        install() {
            fs2mod.install(this.mod.id, this.mod.version, []);
        },

        uninstall() {
            fs2mod.uninstall(this.mod.id, this.mod.version, []);
        },

        cancel() {
            fs2mod.abortTask(task_mod_map[this.mod.id]);
        },

        showErrors() {
            vm.popup_content = this.mod;
            vm.popup_title = 'Mod errors';
            vm.popup_mode = 'mod_errors';
            vm.popup_visible = true;
        },

        showProgress() {
            vm.popup_content = this.mod;
            vm.popup_title = 'Installation Details';
            vm.popup_mode = 'mod_progress';
            vm.popup_visible = true;
        },

        reportMod() {
            vm.popup_mode = 'report_mod';
            vm.popup_mod_id = this.mod.id;
            vm.popup_mod_name = this.mod.title;
            vm.popup_mod_version = this.mod.version;
            vm.popup_mod_message = '';
            vm.popup_visible = true;
        }
    }
};
</script>
<template>
    <div>
        <button class="mod-btn btn-green" v-if="mod.installed && (mod.status === 'ready' || mod.status === 'update') && (mod.type === 'mod' || mod.type == 'tc')" @click="play">
            <span class="btn-text">PLAY</span>
        </button>

        <button class="mod-btn btn-yellow" v-if="mod.installed && mod.status === 'update'" @click="update">
            <span class="btn-text">UPDATE</span>
        </button>

        <button class="mod-btn btn-red" v-if="mod.status === 'error'" @click="showErrors">
            <span class="btn-text">ERROR</span>
        </button>

        <button class="mod-btn btn-orange" v-if="tab === 'details' && mod.installed && mod.status !== 'updating' && mod.id !== 'FS2' && !mod.dev_mode" @click="uninstall">
            <span class="btn-text">UNINSTALL</span>
        </button>

        <button class="mod-btn btn-blue" v-if="mod.status !== 'updating'" @click="install">
            <span class="btn-text">{{ mod.installed ? 'MODFIY' : 'INSTALL' }}</span>
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

        <button class="mod-btn btn-blue" v-if="mod.installed && tab == 'details'" @click="reportMod">
            <span class="btn-text">REPORT</span>
        </button>
    </div>
</template>