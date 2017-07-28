/**
 * The fs2mod object is defined through python. The methods are implemented in knossos/web.py.
 */

function init() {
    let task_mod_map = {};

    function call(ref) {
        let args = Array.prototype.slice.apply(arguments, [1]);
        
        if(window.qt) {
            ref.apply(null, args);
        } else {
            let cb = args.pop();
            cb(ref.apply(null, args));
        }
    }

    function connectOnce(sig, cb) {
        let wrapper = function () {
            sig.disconnect(wrapper);
            return cb.apply(this, arguments);
        };
        sig.connect(wrapper);
    }

    // Make sure we never reach load_left <= 0 until load_cb is declared.
    let load_left = 1;
    function registerComp(name, options) {
        load_left++;
        call(fs2mod.loadTemplate, name, (res) => {
            options.template = res;
            Vue.component(name, options);

            load_left--;
            if(load_left <= 0) load_cb();
        });
    }

    registerComp('kn-mod', {
        props: ['mod', 'tab'],

        methods: {
            showDetails() {
                vm.mod = this.mod;
                vm.page = 'details';
            }
        }
    });

    registerComp('kn-mod-buttons', {
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
    });

    registerComp('kn-drawer', {
        props: ['label'],

        data: () => ({
            open: false
        })
    });

    registerComp('kn-settings-page', {
        props: [],

        data: () => ({
            knossos: {},
            fso: {},
            old_settings: {},
            default_fs2_bin: null,
            default_fred_bin: null,
            caps: null
        }),

        beforeMount() {
            connectOnce(fs2mod.settingsArrived, (settings) => {
                settings = JSON.parse(settings);

                this.knossos = Object.assign({}, settings.knossos);
                this.fso = Object.assign({}, settings.fso);
                this.old_settings = settings;
                this.default_fs2_bin = settings.knossos.fs2_bin;
                this.default_fred_bin = settings.knossos.fred_bin;
            });
            fs2mod.getSettings();
            call(fs2mod.getDefaultFsoCaps, (caps) => {
                this.caps = JSON.parse(caps);
            });
        },

        methods: {
            changeBasePath() {
                call(fs2mod.browseFolder, 'Please select a folder', this.knossos.base_path || '', (path) => {
                    if(path) this.knossos.base_path = path;
                });
            },

            save() {
                for(let set of ['base_path', 'max_downloads', 'use_raven']) {
                    if(this.knossos[set] != this.old_settings.knossos[set]) {
                        fs2mod.saveSetting(set, JSON.stringify(this.knossos[set]));
                    }
                }

                let fso = Object.assign({}, this.fso);
                for(let key of Object.keys(this.old_settings.fso)) {
                    if(!fso[key]) fso[key] = this.old_settings.fso[key];
                }

                fs2mod.saveFsoSettings(JSON.stringify(fso));
            }
        },

        watch: {
            default_fs2_bin(new_bin) {
                if(this.default_fs2_bin === null) return;

                call(fs2mod.saveSetting, 'fs2_bin', JSON.stringify(new_bin), () => {
                    call(fs2mod.getDefaultFsoCaps, (caps) => {
                        this.caps = JSON.parse(caps);
                    });
                });
            },

            default_fred_bin(new_bin) {
                if(this.default_fred_bin === null) return;

                fs2mod.saveSetting('fred_bin', JSON.stringify(new_bin));
            }
        }
    });

    registerComp('kn-flag-editor', {
        props: ['caps', 'cmdline'],

        data: () => ({
            easy_flags: {},
            flags: {},
            selected_easy_flags: '',
            custom_flags: '',
            bool_flags: {},
            list_type: 'Graphics'
        }),

        methods: {
            processCmdline() {
                if(!this.caps) return;

                this.bool_flags = {};
                const custom = [];
                const flags = [];

                for(let list_type of Object.keys(this.caps.flags)) {
                    for(let flag of this.caps.flags[list_type]) {
                        flags.push(flag.name);
                    }
                }

                for(let part of this.cmdline.split(' ')) {
                    if(part === '') continue;

                    if(flags.indexOf(part) > -1) {
                        this.bool_flags[part] = true;
                    } else {
                        custom.push(part);
                    }
                }

                this.easy_flags = this.caps.easy_flags;
                this.flags = this.caps.flags;
                this.selected_easy_flags = '';
                this.custom_flags = custom.join(' ');
                this.list_type = 'Audio';
            },

            showFlagDoc(url) {
                vm.popup_visible = true;
                vm.popup_mode = 'frame';
                vm.popup_title = 'Flag Documentation';
                vm.popup_content = url;
            },

            updateFlags() {
                let cmdline = '';
                for(let name of Object.keys(this.bool_flags)) {
                    if(this.bool_flags[name]) {
                        cmdline += name + ' ';
                    }
                }

                cmdline += this.custom_flags;
                this.$emit('update:cmdline', cmdline);
            }
        },

        watch: {
            caps() {
                this.processCmdline();
            },

            custom_flags() {
                this.updateFlags();
            },

            selected_easy_flags(idx) {
                let group = this.easy_flags[idx];
                if(!group) return;

                // TODO
                console.log(group);
            }
        }
    });

    registerComp('kn-devel-page', {
        props: ['mods'],

        data: () => ({
            mod_map: {},

            page: 'fso',
            selected_mod: null,
            selected_pkg: null,
            video_urls: '',

            fso_build: null,
            caps: null,

            edit_dep: false,
            edit_dep_idx: -1,
            edit_dep_mod: null,
            edit_dep_pkgs: null,
            edit_dep_pkg_sel: null
        }),

        created() {
            window.dp = this;

            this.mod_map = {};
            for(let mod of this.mods) {
                this.mod_map[mod.id] = mod;
            }
        },

        watch: {
            mods(new_list) {
                this.mod_map = {};
                for(let mod of new_list) {
                    this.mod_map[mod.id] = mod;
                }

                // Update the references when the list is updated.

                if(this.selected_mod) {
                    // TODO: Warn about unsaved changes?
                    let found = false;

                    for(let mod of new_list) {
                        if(mod.id === this.selected_mod.id && mod.version === this.selected_mod.version) {
                            this.selected_mod = Object.assign({}, mod);
                            found = true;
                            break;
                        }
                    }

                    if(!found) {
                        this.selected_mod = null;
                        this.selected_pkg = null;
                    }

                    if(this.selected_pkg) {
                        for(let pkg of this.selected_mod.packages) {
                            if(pkg.name === this.selected_pkg.name) {
                                this.selected_pkg = pkg;
                                break;
                            }
                        }
                    }
                }
            },

            page(sel_page) {
                this.selected_pkg = null;
            },

            selected_mod(sel_mod) {
                this.selected_pkg = null;

                if(sel_mod) {
                    this.fso_build = null;

                    if(sel_mod.type === 'mod' || sel_mod.type === 'tc') {
                        this.page = 'fso';

                        call(fs2mod.getFsoBuild, sel_mod.id, sel_mod.version, (result) => {
                            this.fso_build = result;
                        });
                    } else {
                        this.page = 'details';
                    }
                }
            },

            selected_pkg(sel_pkg) {
                this.edit_dep = false;
            },

            fso_build(sel_build) {
                if(sel_build) {
                    sel_build = sel_build.split('#');
                    call(fs2mod.getFsoCaps, sel_build[0], sel_build[1], (caps) => {
                        this.caps = JSON.parse(caps);
                    });
                } else {
                    this.caps = null;
                }
            },

            edit_dep_mod(sel_mod) {
                let mod = this.mod_map[sel_mod];

                this.edit_dep_pkgs = [];
                this.edit_dep_pkg_sel = {};

                if(mod && mod.packages) {
                    for(let pkg of mod.packages) {
                        this.edit_dep_pkgs.push(pkg);
                        this.edit_dep_pkg_sel[pkg.name] = pkg.status !== 'optional';
                    }
                }
            }
        },

        methods: {
            showRetailPrompt() {
                vm.showRetailPrompt();
            },

            openModFolder() {
                fs2mod.openExternal('file://' + this.selected_mod.folder);
            },

            openCreatePopup() {
                vm.popup_mode = 'create_mod';
                vm.popup_title = 'Create mod';
                vm.popup_mod_name = '';
                vm.popup_mod_id = '';
                vm.popup_mod_version = '1.0';
                vm.popup_mod_type = 'mod';
                vm.popup_mod_tcs = this.mods.filter((mod) => mod.type === 'tc');
                vm.popup_mod_parent = vm.popup_mod_tcs.indexOf('FS2') > -1 ? 'FS2' : '';
                vm.popup_visible = true;
            },

            selectMod(mod) {
                // TODO: Warn about unsaved changes?
                this.selected_mod = Object.assign({}, mod);
            },

            selectPkg(pkg) {
                // TODO: Warn about unsaved changes?
                this.selected_pkg = pkg;
            },

            saveDetails() {
                let mod = Object.assign({}, this.selected_mod);
                delete mod.packages;
                delete mod.cmdline;

                fs2mod.saveModDetails(JSON.stringify(mod));
            },

            saveFsoSettings() {
                let mod = this.selected_mod;

                fs2mod.saveModFsoDetails(mod.id, mod.version, this.fso_build, mod.cmdline);
            },

            savePackage() {
                let pkg = Object.assign({}, this.selected_pkg);
                let mod = this.selected_mod;

                fs2mod.savePackage(mod.id, mod.version, pkg.name, JSON.stringify(pkg));
            },

            addPackage() {
                vm.popup_mode = 'add_pkg';
                vm.popup_title = 'Add Package';
                vm.popup_mod_id = this.selected_mod.id;
                vm.popup_mod_version = this.selected_mod.version;
                vm.popup_pkg_name = '';
                vm.popup_pkg_folder = '';
                vm.popup_visible = true;
            },

            deletePackage() {
                vm.popup_mode = 'are_you_sure';
                vm.popup_title = 'Confirmation';
                vm.popup_sure_question = 'Are you sure you want to delete ' + this.selected_pkg.name + '?';
                vm.sureCallback = () => {
                    let pidx = this.selected_mod.packages.indexOf(this.selected_pkg);
                    call(fs2mod.deletePackage, this.selected_mod.id, this.selected_mod.version, pidx, (result) => {
                        if(result) {
                            vm.popup_visible = false;
                            this.selected_pkg = null;
                        }
                    });
                };
                vm.popup_visible = true;
            },

            changeLogo() {
                call(fs2mod.selectImage, this.selected_mod.logo_path || '', (new_path) => {
                    this.selected_mod.logo_path = new_path;
                });
            },

            changeTile() {
                call(fs2mod.selectImage, this.selected_mod.tile_path || '', (new_path) => {
                    this.selected_mod.tile_path = new_path;
                });
            },

            addDep() {
                this.edit_dep_idx = -1;
                this.edit_dep_mod = null;
                this.edit_dep_pkgs = [];
                this.edit_dep_pkg_sel = {};
                this.edit_dep = true;
            },

            editDep(idx, dep) {
                this.edit_dep_idx = idx;
                this.edit_dep_mod = dep.id;
                this.edit_dep_pkg_sel = {};
                this.edit_dep = true;

                if(dep.packages) {
                    for(let pkg of dep.packages) {
                        this.edit_dep_pkg_sel[pkg] = true;
                    }
                }
            },

            deleteDep() {
                if(this.edit_dep_idx !== -1) {
                    this.selected_pkg.dependencies.splice(this.edit_dep_idx, 1);
                }

                this.edit_dep = false;
            },

            saveDep() {
                let dep = {
                    id: this.edit_dep_mod,
                    packages: []
                };

                for(let pkg of this.edit_dep_pkgs) {
                    if(this.edit_dep_pkg_sel[pkg.name]) {
                        dep.packages.push(pkg.name);
                    }
                }

                if(this.edit_dep_idx === -1) {
                    this.selected_pkg.dependencies.push(dep);
                } else {
                    this.selected_pkg.dependencies[this.edit_dep_idx] = dep;
                }

                this.edit_dep = false;
            },

            swapDep(idx, dir) {
                let other = idx + dir;
                let deps = this.selected_pkg.dependencies;

                if(other < 0) return;
                if(other >= deps.length) return;

                // We have to create a new copy of the array and can't simply swap these in-place otherwise Vue.js gets confused
                // and can't detect the change.
                let new_deps = deps.slice(0, Math.min(other, idx));
                if(dir === -1) {
                    new_deps.push(deps[idx]);
                    new_deps.push(deps[other]);
                } else {
                    new_deps.push(deps[other]);
                    new_deps.push(deps[idx]);
                }
                
                this.selected_pkg.dependencies = new_deps.concat(deps.slice(Math.max(other, idx) + 1));
            },

            addExe() {
                call(fs2mod.addPkgExe, this.selected_mod.folder, (files) => {
                    for(let path of files) {
                        this.selected_pkg.executables.push({
                            'file': path,
                            'debug': false
                        });
                    }
                });
            },

            autoAddExes() {
                let exes = this.selected_pkg.executables.map((item) => item.file);

                call(fs2mod.findPkgExes, this.selected_mod.folder, (files) => {
                    for(let path of files) {
                        if(exes.indexOf(path) === -1) {
                            this.selected_pkg.executables.push({
                                'file': path,
                                'debug': false
                            });
                        }
                    }
                });
            },

            deleteExe(i) {
                this.selected_pkg.executables.splice(i, 1);
            }
        }
    });

    let vm;
    function load_cb() {
        call(fs2mod.loadTemplate, 'kn-page', (tpl) => {
            window.vm = vm = new Vue({
                el: '#loading',
                template: tpl,

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
                    popup_content: null,

                    popup_mod_name: '',
                    popup_mod_id: '',
                    popup_mod_version: '1.0',
                    popup_mod_type: 'mod',
                    popup_mod_parent: 'FS2',
                    popup_mod_tcs: [],

                    popup_pkg_name: '',
                    popup_pkg_folder: '',

                    popup_sure_question: '',
                    sureCallback: null,

                    // retail prompt
                    retail_searching: true,
                    retail_found: false,
                    retail_data_path: ''
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
                        alert('Not yet implemented! Sorry.');
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
                        call(fs2mod.browseFolder, 'Please select a folder', this.data_path, (path) => {
                            if(path) this.data_path = path;
                        });
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

                    createMod() {
                        if(this.popup_mod_id === '') {
                            alert('You need to enter a mod ID!');
                            return;
                        }


                        if(this.popup_mod_name === '') {
                            alert('You need to enter a mod name!');
                            return;
                        }

                        call(fs2mod.createMod, this.popup_mod_name, this.popup_mod_id, this.popup_mod_version, this.popup_mod_type, this.popup_mod_parent, (result) => {
                            if(result) {
                                this.popup_visible = false;
                            }
                        });
                    },

                    addPackage() {
                        if(this.popup_pkg_name === '') {
                            alert('You need to enter a package name!');
                            return;
                        }

                        if(this.popup_pkg_folder === '') {
                            alert('You need to enter a folder name!');
                            return;
                        }

                        call(fs2mod.addPackage, this.popup_mod_id, this.popup_mod_version, this.popup_pkg_name, this.popup_pkg_folder, (result) => {
                            if(result > -1) {
                                dp.selected_pkg = dp.selected_mod.packages[result];
                                this.popup_visible = false;
                            }
                        });
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
                    },

                    showRetailPrompt() {
                        vm.popup_mode = 'retail_prompt';
                        vm.popup_title = 'Retail data missing';
                        vm.popup_visible = true;

                        vm.retail_data_path = '';
                        vm.retailAutoDetect();
                    },

                    retailAutoDetect() {
                        vm.retail_searching = true;
                        vm.retail_found = false;

                        call(fs2mod.searchRetailData, (path) => {
                            vm.retail_searching = false;

                            if(path !== '') {
                                vm.retail_found = true;
                                vm.retail_data_path = path;
                            }
                        });
                    },

                    selectRetailFolder() {
                        call(fs2mod.browseFolder, 'Please select your FS2 folder', this.retail_data_path, (path) => {
                            if(path) this.retail_data_path = path;
                        });
                    },

                    selectRetailFile() {
                        call(fs2mod.browseFiles, 'Please select your setup_freespace2_...exe', this.retail_data_path, '*.exe', (files) => {
                            if(files.length > 0) {
                                this.retail_data_path = files[0];
                            }
                        });
                    },

                    finishRetailPrompt() {
                        call(fs2mod.copyRetailData, this.retail_data_path, (result) => {
                            if(result) vm.popup_visible = false;
                        });
                    }
                }
            });

            call(fs2mod.finishInit, get_translation_source(), (t) => vm.trans = t);
        });
    }
    let mod_table = null;

    // Now that load_cb() is declared, we can subtract one from load_left thus making load_left <= 0 possible.
    load_left--;
    if(load_left == 0) {
        // All pending load requests are finished which means we can call load_cb() immediately.
        load_cb();
    }

    fs2mod.showWelcome.connect(() => vm.page = 'welcome');
    fs2mod.showDetailsPage.connect((mod) => {
        vm.mod = mod;
        vm.page = 'details';
    });
    fs2mod.showRetailPrompt.connect(() => {
        vm.showRetailPrompt();
    });
    fs2mod.updateModlist.connect((mods, type) => {
        window.mt = mod_table = {};
        mods = JSON.parse(mods);
        for(let mod of mods) {
            mod_table[mod.id] = mod;
        }

        vm.mods = mods;
        vm.page = type === 'develop' ? 'develop' : 'modlist';
        vm.tab = type;
    });

    let tasks = null;
    call(fs2mod.getRunningTasks, (tasks) => {
        tasks = JSON.parse(tasks);
    });

    fs2mod.taskStarted.connect((tid, title, mods) => {
        if(!tasks) return;

        tasks[tid] = { title, mods };

        for(let mid of mods) {
            if(mod_table[mid]) {
                mod_table[mid].status = 'updating';
                task_mod_map[mid] = tid;
            }
        }
    });

    fs2mod.taskProgress.connect((tid, progress, details) => {
        if(!tasks) return;

        details = JSON.parse(details);
        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = progress;
                mod_table[mid].progress_info = details;
            }
        }
    });

    fs2mod.taskFinished.connect((tid) => {
        if(!tasks) return;

        for(let mid of tasks[tid].mods) {
            if(mod_table[mid]) {
                mod_table[mid].progress = 0;
                mod_table[mid].status = 'ready';
            }

            if(task_mod_map[mid]) delete task_mod_map[mid];
        }

        delete tasks[tid];
    });
}

if(window.qt) {
    new QWebChannel(qt.webChannelTransport, function (channel) {
        window.fs2mod = channel.objects.fs2mod;
        init();
    });
} else {
    window.addEventListener('load', init);
}
