<script>
export default {
    props: ['mod', 'tab'],

    methods: {
        play() {
            fs2mod.runMod(this.mod.id, '');
        },

        update() {
            fs2mod.updateMod(this.mod.id, '');
        },

        install() {
            fs2mod.install(this.mod.id, '', []);
        },

        uninstall() {
            fs2mod.uninstall(this.mod.id, '', []);
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
        }
    }
};
</script>
<template>
    <div>
        <button class="mod-btn btn-green" v-if="mod.installed && (mod.status === 'ready' || mod.status === 'update') && (mod.type === 'mod' || mod.type == 'tc')" v-on:click="play">
            <span class="btn-text">PLAY</span>
        </button>

        <button class="mod-btn btn-yellow" v-if="mod.installed && mod.status === 'update'" v-on:click="update">
            <span class="btn-text">UPDATE</span>
        </button>

        <button class="mod-btn btn-red" v-if="mod.status === 'error'" v-on:click="showErrors">
            <span class="btn-text">ERROR</span>
        </button>

        <button class="mod-btn btn-orange" v-if="mod.installed && mod.status !== 'updating'" v-on:click="uninstall">
            <span class="btn-text">UNINSTALL</span>
        </button>

        <button class="mod-btn btn-blue" v-if="!mod.installed" v-on:click="install">
            <span class="btn-text">INSTALL</span>
        </button>

        <button class="mod-btn btn-blue" v-if="mod.status === 'updating'" v-on:click="showProgress">
            <span class="small-btn-text">
                INSTALLING...<br>
                {{ Math.round(mod.progress) }}%
            </span>
        </button>

        <button class="mod-btn btn-orange" v-if="mod.status === 'updating'" v-on:click="cancel">
            <span class="btn-text">CANCEL</span>
        </button>
    </div>
</template>