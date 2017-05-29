function init() {
    let task_mod_map = {};

    Vue.component('kn-mod', {
        template: '#kn-mod',
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

            showDetails() {
                vm.mod = this.mod;
                vm.page = 'details';
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
    });

    Vue.component('kn-drawer', {
        template: '#kn-drawer',
        props: ['label'],

        data: () => ({
            open: false
        })
    });

    let vm = new Vue({
        el: '#loading',
        template: '#kn-page',
        data: {
            tabs: {
                home: 'Home',
                explore: 'Explore',
                develop: 'Development'
            },

            search_text: '',
            tab: 'home',
            page: 'modlist',
            show_filter: false,
            mods: [],

            // welcome page
            data_path: '?',

            // details page
            mod: null,

            popup_visible: false,
            popup_title: 'Popup',
            popup_mode: '',
            popup_content: null
        },

        watch: {
            search_text(phrase) {
                fs2mod.triggerSearch(phrase);
            }
        },

        methods: {
            openLink(url) {
                fs2mod.openExternal(url);
            },

            showHelp() {
                alert('Not yet implemented!');
            },

            updateList() {
                fs2mod.fetchModlist();
            },

            showSettings() {
                this.page = 'settings';
            },

            showTab(tab) {
                fs2mod.showTab(tab);
            },

            exitDetails() {
                this.page = 'modlist';
            },

            selectFolder() {
                if(window.qt) {
                    fs2mod.browseFolder('Please select a folder', this.data_path, (path) => {
                        if(path) this.data_path = path;
                    });
                } else {
                    let path = fs2mod.browseFolder('Please select a folder', this.data_path);
                    if(path) this.data_path = path;
                }
            },

            finishWelcome() {
                fs2mod.setBasePath(this.data_path);
            },

            installMod() {
                fs2mod.install(this.mod.id, '', []);
            },

            uninstallMod() {
                fs2mod.uninstall(this.mod.id, '', []);
            },

            cancelMod() {
                fs2mod.abortTask(task_mod_map[this.mod.id]);
            },

            playMod() {
                fs2mod.runMod(this.mod.id, '');
            },

            updateMod() {
                fs2mod.updateMod(this.mod.id, '');
            },

            showModErrors() {
                vm.popup_content = this.mod;
                vm.popup_title = 'Mod errors';
                vm.popup_mode = 'mod_errors';
                vm.popup_visible = true;
            },

            showModProgress() {
                vm.popup_content = this.mod;
                vm.popup_title = 'Installation Details';
                vm.popup_mode = 'mod_progress';
                vm.popup_visible = true;
            }
        }
    });
    window.vm = vm;
    let mod_table = null;

    fs2mod.showWelcome.connect(() => vm.page = 'welcome');
    fs2mod.showDetailsPage.connect((mod) => {
        vm.mod = mod;
        vm.page = 'details';
    });
    fs2mod.updateModlist.connect((mods, type) => {
        window.mt = mod_table = {};
        console.log(mods);
        for(let mod of mods) {
            mod_table[mod.id] = mod;
        }

        vm.mods = mods;
        vm.page = 'modlist';
        vm.tab = type;
    });

    let tasks = {};
    fs2mod.taskStarted.connect((tid, title, mods) => {
        tasks[tid] = { title, mods };

        for(let mid of mods) {
            if(mod_table[mid]) {
                mod_table[mid].status = 'updating';
                task_mod_map[mid] = tid;
            }
        }
    });

    fs2mod.taskProgress.connect((tid, progress, details) => {
        details = JSON.parse(details);
        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = progress;
                mod_table[mid].progress_info = details;
            }
        }
    });

    fs2mod.taskFinished.connect((tid) => {
        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = 0;
                mod_table[mid].status = 'ready';
            }

            if(task_mod_map[mid]) delete task_mod_map[mid];
        }

        delete tasks[tid];
    });

    if(window.qt) {
        fs2mod.finishInit(get_translation_source(), (t) => vm.trans = t);
    } else {
        vm.trans = fs2mod.finishInit(get_translation_source());
    }
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else {
    window.addEventListener('load', init);
}
