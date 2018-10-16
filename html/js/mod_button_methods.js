export default {
    play() {
        fs2mod.runMod(this.mod.id, this.mod.version);
    },

    update() {
        fs2mod.updateMod(this.mod.id, '');
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
        vm.popup_progress_message = null;
        vm.popup_mod_id = this.mod.id;
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
    },

    showFsoSettings() {
        vm.popup_visible = true;
        vm.popup_title = 'FSO Settings';
        vm.popup_mode = 'fso_settings';
        vm.popup_content = this.mod;
    }
};
