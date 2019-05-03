<script>
export default {
    props: ['mods'],

    components: {
        'kn-dev-staff': require('./kn-dev-staff.vue').default,
        'kn-save-btn': require('./kn-save-btn.vue').default
    },

    data: () => ({
        reloading: false,
        mod_map: {},

        page: 'fso',
        selected_mod: null,
        selected_pkg: null,
        sel_version: null,
        video_urls: '',

        fso_build: null,
        caps: null,
        tools: [],

        edit_dep: false,
        edit_dep_idx: -1,
        edit_dep_mod: null,
        edit_dep_version: null,
        edit_dep_allow_new: false,
        edit_dep_pkgs: null,
        edit_dep_pkg_sel: null,

        tab_scroll: -1,
        mod_box_tab: 'fso'
    }),

    created() {
        window.dp = this;

        this.mod_map = {};
        for(let mod of this.mods) {
            this.mod_map[mod.id] = mod;
        }

        fs2mod.applyDevDesc.connect(this.applyDevDesc);
    },

    beforeDestroy() {
        fs2mod.applyDevDesc.disconnect(this.applyDevDesc);
    },

    computed: {
        edit_dep_versions() {
            let mod = this.mod_map[this.edit_dep_mod];
            if(!mod) return [];

            let is_engine = mod.type === 'engine';
            let res = [];
            let found = {};

            for(let v of mod.versions) {
                if(is_engine) {
                    res.push([v.version, (this.edit_dep_allow_new ? '>=' : '') + v.version]);
                } else {
                    res.push(['~' + v.version, '~' + v.version]);
                }
            }

            return res;
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
                    if(mod.id === this.selected_mod.id) {
                        found = true;
                        let version = this.selected_mod.version;

                        this.selected_mod = Object.assign({}, mod);
                        if(version !== this.selected_mod.version) this.selectVersion(version);
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
        }
    },

    methods: {
        showRetailPrompt() {
            vm.showRetailPrompt(false);
        },

        openModFolder() {
            fs2mod.openExternal('file://' + this.selected_mod.folder);
        },

        openCreatePopup() {
            vm.popup_mode = 'create_mod';
            vm.popup_title = 'Create mod';
            vm.popup_mod_name = '';
            vm.popup_mod_id = '';
            vm.popup_mod_version = '1.0.0';
            vm.popup_mod_type = 'mod';
            vm.popup_mod_tcs = this.mods.filter((mod) => mod.type === 'tc');
            vm.popup_mod_parent = '';

            for(let tc of vm.popup_mod_tcs) {
                if(tc.id === 'FS2') {
                    vm.popup_mod_parent = 'FS2';
                    break;
                }
            }

            vm.popup_visible = true;
        },

        openNewVersionPopup() {
            vm.popup_mode = 'new_mod_version';
            vm.popup_title = 'Create a new mod version';
            vm.popup_mod_method = 'copy';
            vm.popup_mod_id = this.selected_mod.id;
            vm.popup_mod_name = this.selected_mod.title;
            vm.popup_mod_version = this.selected_mod.version;
            vm.popup_mod_new_version = this.selected_mod.version;
            vm.popup_visible = true;
            vm.popup_finished = (result) => {
                if(result) {
                    this.selectVersion(vm.popup_mod_new_version);
                }
            };
        },

        selectMod(mod) {
            // TODO: Warn about unsaved changes?
            this.selected_mod = Object.assign({}, mod);
            this.selected_pkg = null;
            this.sel_version = this.selected_mod.version;

            this.tab_scroll = -1;
            this.fso_build = null;
            this.caps = null;
            this.video_urls = mod.videos.join("\n");

            if(this.selected_mod.packages.length === 0) {
                this.mod_box_tab = 'modify';
            }

            this.tools = [];
            call(fs2mod.getModTools, this.selected_mod.id, this.selected_mod.version, (tools) => {
                this.tools = tools;
            });

            if(mod.type === 'mod' || mod.type === 'tc') {
                this.page = 'fso';

                call(fs2mod.getFsoBuild, mod.id, mod.version, (result) => {
                    this.fso_build = result;
                });
            } else {
                this.page = 'details';
            }
        },

        selectVersion(version) {
            let v_mod = null;
            for(let mod of this.selected_mod.versions) {
                if(mod.version === version) {
                    v_mod = mod;
                    break;
                }
            }

            if(!v_mod) return;
            // TODO: Refactor
            v_mod.versions = this.selected_mod.versions;
            v_mod.status = this.selected_mod.status;
            v_mod.progress = this.selected_mod.progress;
            v_mod.progress_info = this.selected_mod.progress_info;
            this.selected_mod = v_mod;

            if(this.selected_pkg) {
                let sel_pkg = null;
                for(let pkg of v_mod.packages) {
                    if(pkg.name === this.selected_pkg.name) {
                        sel_pkg = pkg;
                        break;
                    }
                }

                this.selected_pkg = sel_pkg;
            }

            this.edit_dep = false;
        },

        switchPage(page) {
            this.selected_pkg = null;
            this.page = page;
        },

        selectPkg(pkg) {
            // TODO: Warn about unsaved changes?
            this.selected_pkg = pkg;
            this.page = 'pkg';
        },

        saveDetails() {
            let mod = Object.assign({}, this.selected_mod);
            delete mod.packages;
            delete mod.cmdline;
            delete mod.versions;

            mod.video_urls = this.video_urls;
            return call_promise(fs2mod.saveModDetails, JSON.stringify(mod));
        },

        saveFsoSettings() {
            let mod = this.selected_mod;

            return call_promise(fs2mod.saveModFsoDetails, mod.id, mod.version, this.fso_build, mod.cmdline);
        },

        savePackage() {
            let pkg = Object.assign({}, this.selected_pkg);
            let mod = this.selected_mod;

            return call_promise(fs2mod.savePackage, mod.id, mod.version, pkg.name, JSON.stringify(pkg));
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

        changeImage(prop) {
            call(fs2mod.selectImage, this.selected_mod[prop] || (this.selected_mod.folder + '/dummy'), (new_path) => {
                if(new_path !== '') {
                    this.selected_mod[prop] = new_path;
                }
            });
        },

        saveModFlag() {
            return call_promise(fs2mod.saveModFlag, this.selected_mod.id, this.selected_mod.version, this.selected_mod.mod_flag);
        },

        addDep() {
            this.edit_dep_idx = -1;
            this.edit_dep_mod = null;
            this.edit_dep_version = null;
            this.edit_dep_allow_new = false;
            this.edit_dep_pkgs = [];
            this.edit_dep_pkg_sel = {};
            this.edit_dep = true;
        },

        editDep(idx, dep) {
            this.edit_dep_idx = idx;
            this.edit_dep_mod = dep.id;
            this.edit_dep_version = dep.version;
            this.edit_dep_allow_new = false;
            this.edit_dep_pkg_sel = {};
            this.edit_dep = true;

            if(dep.version && dep.version.substring(0, 2) === '>=') {
                this.edit_dep_version = dep.version.substring(2);
                this.edit_dep_allow_new = true;
            }

            this.updateDepModVersion();

            if(dep.packages) {
                for(let pkg of dep.packages) {
                    this.edit_dep_pkg_sel[pkg] = true;
                }
            }
        },

        updateDepMod() {
            let mod = this.mod_map[this.edit_dep_mod];

            this.edit_dep_version = null;
            this.edit_dep_allow_new = mod.type === 'engine';
            this.edit_dep_pkgs = [];
            this.edit_dep_pkg_sel = {};

            if(mod && mod.packages) {
                for(let pkg of mod.packages) {
                    this.edit_dep_pkgs.push(pkg);
                    this.edit_dep_pkg_sel[pkg.name] = pkg.status === 'recommended';
                }
            }
        },

        updateDepModVersion() {
            let mod = this.mod_map[this.edit_dep_mod];
            let v = null;

            for(let mv of mod.versions) {
                if(mv.version === this.edit_dep_version) {
                    v = mv;
                    break;
                }
            }

            if(!v) v = mod;

            this.edit_dep_pkgs = [];
            for(let pkg of v.packages) {
                this.edit_dep_pkgs.push(pkg);
            }
        },

        deleteDep() {
            if(this.edit_dep_idx !== -1) {
                this.selected_pkg.dependencies.splice(this.edit_dep_idx, 1);
            }

            this.edit_dep = false;
        },

        saveDep() {
            let version = this.edit_dep_version;
            if(version !== null && this.edit_dep_allow_new) {
                version = '>=' + version;
            }

            let dep = {
                id: this.edit_dep_mod,
                version: version,
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

        _swapHelper(list, idx, dir) {
            let other = idx + dir;

            if(other < 0) return list;
            if(other >= list.length) return list;

            // We have to create a new copy of the array and can't simply swap these in-place otherwise Vue.js gets confused
            // and can't detect the change.
            let new_list = list.slice(0, Math.min(other, idx));
            if(dir === -1) {
                new_list.push(list[idx]);
                new_list.push(list[other]);
            } else {
                new_list.push(list[other]);
                new_list.push(list[idx]);
            }

            return new_list.concat(list.slice(Math.max(other, idx) + 1));
        },

        swapFlagMod(idx, dir) {
            this.selected_mod.mod_flag = this._swapHelper(this.selected_mod.mod_flag, idx, dir);
        },

        swapDep(idx, dir) {
            this.selected_pkg.dependencies = this._swapHelper(this.selected_pkg.dependencies, idx, dir);
        },

        swapScreens(idx, dir) {
            this.selected_mod.screenshots = this._swapHelper(this.selected_mod.screenshots, idx, dir);
        },

        addScreen() {
            call(fs2mod.selectImage, this.selected_mod.folder + '/dummy', (new_path) => {
                if(new_path !== '') {
                    this.selected_mod.screenshots.push(new_path);
                }
            });
        },

        addExe() {
            call(fs2mod.addPkgExe, this.selected_mod.folder, (files) => {
                for(let path of files) {
                    this.selected_pkg.executables.push({
                        'file': path
                    });
                }
            });
        },

        autoAddExes() {
            let exes = this.selected_pkg.executables.map((item) => item.file);

            call(fs2mod.findPkgExes, this.selected_mod.folder + '/' + this.selected_pkg.folder, (files) => {
                for(let path of files) {
                    if(exes.indexOf(path) === -1) {
                        this.selected_pkg.executables.push({
                            'file': path
                        });
                    }
                }
            });
        },

        deleteExe(i) {
            this.selected_pkg.executables.splice(i, 1);
        },

        uploadMod() {
            vm.popup_progress_message = null;
            vm.popup_mode = 'upload_mod';
            vm.popup_title = 'Upload mod';
            vm.popup_mod_name = this.selected_mod.title;
            vm.popup_mod_version = this.selected_mod.version;
            vm.popup_content = false;

            vm.sureCallback = () => {
                vm.popup_mode = 'mod_progress';
                // We need the original mod here because the copy doesn't contain the progress info.
                vm.popup_mod_id = this.selected_mod.id;
                vm.popup_progress_cancel = () => {
                    fs2mod.cancelUpload();
                };

                fs2mod.startUpload(this.selected_mod.id, this.selected_mod.version, vm.popup_content);
            };
            vm.popup_visible = true;
        },

        reopenUploadPopup() {
            vm.popup_mode = 'mod_progress';
            vm.popup_title = 'Upload mod';
            vm.popup_progress_message = null;
            vm.popup_mod_id = this.selected_mod.id;
            vm.popup_progress_cancel = () => {
                fs2mod.cancelUpload();
            };
            vm.popup_visible = true;
        },

        deleteMod()  {
            vm.popup_mode = 'are_you_sure';
            vm.popup_title = 'Delete mod release';
            vm.popup_sure_question = `Are you sure that you want to delete ${this.selected_mod.title} ${this.selected_mod.version} from the Nebula?` +
                "\nThis will only delete this specific version.";

            vm.sureCallback = () => {
                fs2mod.nebDeleteMod(this.selected_mod.id, this.selected_mod.version);
                vm.popup_visible = false;
            };
            vm.popup_visible = true;
        },

        deleteModLocally()  {
            vm.popup_mode = 'are_you_sure';
            vm.popup_title = 'Delete mod release';
            vm.popup_sure_question = `Are you sure that you want to delete ${this.selected_mod.title} ${this.selected_mod.version} from your computer?` +
                "\nThis will only delete this specific version.";

            vm.sureCallback = () => {
                fs2mod.removeModFolder(this.selected_mod.id, this.selected_mod.version);
                vm.popup_visible = false;
            };
            vm.popup_visible = true;
        },

        launchMod() {
            let mod = this.selected_mod;

            // Make sure the FSO settings are save before launching the mod.
            call(fs2mod.saveModFsoDetails, mod.id, mod.version, this.fso_build, mod.cmdline, () => {
                fs2mod.runMod(this.selected_mod.id, this.selected_mod.version);
            });
        },

        launchTool(label) {
            fs2mod.runModTool(this.selected_mod.id, this.selected_mod.version, '', '', label);
        },

        tabScroll(diff) {
            let val = this.tab_scroll + diff;
            if(val < -1) {
                val = -1;
            } else if(val > this.selected_mod.packages.length - 2) {
                val = this.selected_mod.packages.length - 2;
            }

            this.tab_scroll = val;
        },

        openDescEditor() {
            fs2mod.showDescEditor(this.selected_mod.description);
        },

        applyDevDesc(desc) {
            if(this.selected_mod) {
                this.selected_mod.description = desc;
            }
        },

        launchButtonColor(tool) {
            if(tool.toLowerCase().indexOf('fred') > -1 || tool.toLowerCase().indexOf('qt') > -1) {
                return 'orange';
            } else if(tool.toLowerCase().indexOf('debug') > -1) {
                return 'yellow';
            } else {
                return 'grey';
            }
        }
    }
};
</script>
<template>
    <div>
        <div class="scroll-style mlist">
            <button class="mod-btn btn-link-blue" @click.prevent="openCreatePopup"><span class="btn-text">CREATE</span></button>
            <!-- <button class="btn btn-default btn-small dev-btn" @click.prevent="showRetailPrompt">INSTALL FS2</button> -->

            <a href="#" v-for="mod in mods" v-if="mod.dev_mode" :key="mod.id" :class="{ active: selected_mod && selected_mod.id === mod.id }" @click="selectMod(mod)">{{ mod.title }}</a>
        </div>
        <div class="content-pane">
            <div class="logo-box" v-if="selected_mod">
                <kn-dev-mod :mod="selected_mod" tab="develop"></kn-dev-mod>

                <div class="devmanagement">
                    <label @click="mod_box_tab = 'fso'" :class="{ active: mod_box_tab === 'fso' }">Launch FSO</label>
                    <label @click="mod_box_tab = 'modify'" :class="{ active: mod_box_tab === 'modify' }">Modify Mod</label>

                    <div class="buttonpane" v-if="mod_box_tab === 'fso'">
                        <button @click.prevent="launchMod" class="mod-btn btn-green"><p>Play</p></button>
                        <button
                            v-for="tool in tools"
                            @click.prevent="launchTool(tool)"
                            :class="'mod-btn btn-' + launchButtonColor(tool)"
                            :title="tool"
                        >
                            <p>{{ tool }}</p>
                        </button>
                        <br>
                    </div>

                    <div class="buttonpane" v-if="mod_box_tab === 'modify'">
                        <button @click.prevent="reopenUploadPopup" class="mod-btn btn-link-blue" v-if="(this.mod_map[(this.selected_mod || {}).id] || {}).progress">Uploading...</button>
                        <button @click.prevent="uploadMod" class="mod-btn btn-link-blue" v-else>Upload</button><br>
                        <button @click.prevent="deleteMod" class="mod-btn btn-link-red">Delete</button>
                        <button @click.prevent="deleteModLocally" class="mod-btn btn-link-red">Local Delete</button><br>
                        <button @click.prevent="openNewVersionPopup" class="mod-btn btn-link-grey">+ Version</button>
                        <button @click.prevent="addPackage" class="mod-btn btn-link-grey">+ Package</button>
                        <br>
                    </div>
                </div>

                Mod Versions:
                <select class="form-control mod-version" v-model="sel_version" @change="selectVersion(sel_version)">
                    <option v-for="m in selected_mod.versions">{{ m.version }}</option>
                </select>
                <br>

                Mod Path:
                <br>
                <span class="version-link"><a href="#" @click.prevent="openModFolder">{{ selected_mod.folder }}</a></span>
                <br>

                <a :href="'https://fsnebula.org/mod/' + encodeURIComponent(selected_mod.id)" class="open-ext">Download Link</a>
            </div>
            <div class="dev-instructions" v-else>
                <p>
                    This tab has advanced features that can help you get started
                    with modding for FreeSpace Open (FSO).
                </p>
                <p>
                    Here you can
                </p>
                <ul>
                    <li>create new mods</li>
                    <li>edit installed mods</li>
                    <li>apply experimental mod settings</li>
                    <li>customize a mod's command line options (flags)</li>
                    <li>make missions with the mission editors FRED (Windows only, full-featured) and qtFRED (all platforms, <a href="https://www.hard-light.net/forums/index.php?topic=94565.0" class="open-ext">under development</a>)</li>
                </ul>
                <p>
                    Check out these resources to help you get started:
                </p>
                <ul>
                    <li><a href="https://docs.google.com/document/d/1oHq1YRc1eXbCgW-NqqKo1-6N_myfZzoBdwZuP16XImA/edit?pli=1#heading=h.fk85esz24kjw" class="open-ext">Knossos Mod Creation Guide</a></li>
                    <li><a href="http://fredzone.hard-light.net/freddocs/" class="open-ext">FREDdocs</a> classic FRED tutorial</li>
                    <!-- TODO more -->
                </ul>
            </div>
            <div class="form-box" v-if="selected_mod">
                <div class="tabcorner"></div>
                <div class="dev-tabbox">
                    <div class="dev-tabbar">
                        <a href="#" @click.prevent="switchPage('details')" :class="{'active': page === 'details'}">Details</a>
                        <a href="#" @click.prevent="switchPage('fso')" :class="{'active': page === 'fso'}" v-if="selected_mod.type === 'mod' || selected_mod.type === 'tc'">FSO</a>
                        <a href="#" @click.prevent="switchPage('mod_flag')" :class="{'active': page === 'mod_flag'}" v-if="selected_mod.type === 'mod' || selected_mod.type === 'tc'">-mod Flag</a>
                        <a href="#" @click.prevent="switchPage('team')" :class="{'active': page === 'team'}">Members</a>
                    </div>

                    <div class="dev-tabbar">
                        <a href="#"
                            v-for="pkg, i in selected_mod.packages"
                            v-show="i > tab_scroll"
                            :class="{'active': (selected_pkg||{}).name === pkg.name }"
                            @click.prevent="selectPkg(pkg); edit_dep = false">
                            {{ pkg.name }}
                        </a>

                        <div class="dev-tabbar-arrows">
                            <a href="#" @click.prevent="tabScroll(-1)"><i class="fa fa-chevron-left"></i></a>
                            <a href="#" @click.prevent="tabScroll(1)"><i class="fa fa-chevron-right"></i></a>
                        </div>
                    </div>
                </div>

                <div class="form-content container-fluid scroll-style" ref="container">
                    <form class="form-horizontal" v-if="selected_mod">
                        <div v-if="selected_mod.packages.length === 0">
                            <h4>Dev Help</h4>

                            <p>
                                Your mod must have at least one package before you can start editing.
                            </p>

                            <p>
                                A <em>package</em> is a folder for mod data (missions, models, etc).
                                Smaller mods might need only one package that contains all of the mod's data.
                                Larger mods should split their data into multiple packages, such as
                            </p>
                            <ul>
                                <li>Core for textual data such as missions and tables</li>
                                <li>Models for new models and Maps for their textures</li>
                                <li>Packages for media such as Movies, Music, Sound Effects, and Voice Acting</li>
                                <li>Optional packages such as high-detail models/textures</li>
                            </ul>
                            <p>
                                When you release your mod, you should pack each package into an FSO-specific type of uncompressed file called a <em>VP file</em>.
                                VP file names end with ".vp". Knossos can automatically pack your packages into
                                VP files and compress them for you when you upload your mod to the <a href="https://fsnebula.org/" class="open-ext">Nebula</a> mod
                                repository.
                            </p>
                            <p>
                                To create a package, click the "+ Package" button on the left.<br>
                                To edit a package, click on the package name in the top tab list.
                            </p>
                            <p>
                                Some things to consider when deciding how to package your mod:
                            </p>
                            <ul>
                                <li>A VP file can be at most 2 GB.</li>
                                <li>Knossos's automatic VP packing packs each VP file into its own compressed archive file.<br>
                                Thus a player with an unreliable Internet connection who has to restart a download
                                will benefit from your mod having packages that aren't huge.</li>
                                <li>When you upload a new version of your mod, only modified packages are uploaded.<br>
                                Thus if a new version has just mission fixes and your missions are in
                                a separate package from models/textures, the new version will have a new missions
                                package only, meaning a smaller upload for you and smaller downloads for players.</li>
                            </ul>
                        </div>
                        <div v-else-if="!selected_pkg && page === 'details'">
                            <h4>Mod Details</h4>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Name</label>
                                <div class="col-xs-9">
                                    <input type="text" class="form-control" v-model="selected_mod.title">
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">ID</label>
                                <div class="col-xs-9">
                                    <p class="form-control-static">{{ selected_mod.id }}</p>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Version</label>
                                <div class="col-xs-9">
                                    <input type="text" class="form-control" :value="selected_mod.version" disabled>

                                    <p class="help-block">
                                        TODO: Version explanation. The versioning scheme is still pending. See the forum thread for details.
                                    </p>

                                    <p class="help-block">
                                        TODO: Allow version change through popup. (Important: Allow to choose whether to copy or rename the mod folder.)
                                    </p>
                                </div>
                            </div>

                            <div class="form-group" v-if="selected_mod.type === 'engine'">
                                <label class="col-xs-3 control-label">Stability</label>
                                <div class="col-xs-9">
                                    <select v-model="selected_mod.stability" class="form-control">
                                        <option value="stable">Stable</option>
                                        <option value="rc">RCs</option>
                                        <option value="nightly">Nightly</option>
                                    </select>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Type</label>
                                <div class="col-xs-9">
                                    <select class="form-control" v-model="selected_mod.type" disabled>
                                        <option value="mod">Mod</option>
                                        <option value="tc">Total Conversion</option>
                                        <option value="engine">FSO build</option>
                                        <!-- TODO uncomment once extension and tool types are supported
                                        <option value="tool">Tool</option>
                                        <option value="ext">Extension</option>
                                        -->
                                    </select>

                                    <span class="help-block" v-if="selected_mod.type === 'mod'">
                                        A campaign based on FreeSpace 2 (retail) or on a total conversion (TC).<br>
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'tc'">
                                        A standalone game that doesn't depend on other mods and doesn't use FS2 files.<br>
                                        Mods for TCs should use the "Mod" type.
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'engine'">
                                        A build of the FreeSpace Open (FSO) engine (fs2_open*.exe, fs2_open*.AppImage, fs2_open*.app, etc.)
                                    </span>
                                    <!-- TODO uncomment once tools and extensions are supported
                                    <span class="help-block" v-if="selected_mod.type === 'tool'">
                                        Software other than the FreeSpace Open (FSO) engine.<br>
                                        Examples include FRED (mission editor) and PCS2 (model converter).
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'ext'">
                                        A change that overrides, such as custom HUD tables
                                    </span>
                                    -->
                                </div>
                            </div>

                            <div class="form-group" :style="{visibility: (selected_mod.type === 'mod' || selected_mod.type === 'ext') ? 'visible' : 'hidden'}">
                                <label class="col-xs-3 control-label">Parent mod</label>
                                <div class="col-xs-9">
                                    <p class="form-control-static">{{ selected_mod.parent }}</p>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Description</label>
                                <div class="col-xs-9">
                                    <textarea class="form-control" v-model="selected_mod.description"></textarea>

                                    <button class="btn btn-small btn-default" @click.prevent="openDescEditor">Open Editor</button>

                                    <p class="help-block">
                                        Use <a href="https://en.wikipedia.org/wiki/BBCode" class="open-ext">BBCode</a> here. To preview your description, save, go to the Home tab,
                                        and go to this mod's Details page.
                                    </p>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Title Image</label>
                                <div class="col-xs-9">
                                    <img :src="'file://' + selected_mod.tile" v-if="selected_mod.tile"><br>

                                    <p class="help-block">
                                        This image should be 150&times;225 pixels large.
                                    </p>

                                    <button class="btn btn-small btn-default" @click.prevent="changeImage('tile')">Select Image</button>
                                    <button class="btn btn-small btn-default" @click.prevent="selected_mod.tile = null" v-if="selected_mod.tile">Remove Image</button>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Legacy Logo</label>
                                <div class="col-xs-9">
                                    <img :src="'file://' + selected_mod.logo" v-if="selected_mod.logo"><br>

                                    <p class="help-block">
                                        This image should be about 255&times;112 pixels large.<br />
                                        Use only for legacy logos and mod images from mods predating Knossos.
                                        If you create a new mod logo or image, use the above setting.
                                    </p>

                                    <button class="btn btn-small btn-default" @click.prevent="changeImage('logo')">Select Image</button>
                                    <button class="btn btn-small btn-default" @click.prevent="selected_mod.logo = null" v-if="selected_mod.logo">Remove Image</button>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Banner</label>
                                <div class="col-xs-9">
                                    <img :src="'file://' + selected_mod.banner" v-if="selected_mod.banner"><br>

                                    <p class="help-block">
                                        This image should be 1070x 300 pixels large.
                                    </p>

                                    <button class="btn btn-small btn-default" @click.prevent="changeImage('banner')">Select Image</button>
                                    <button class="btn btn-small btn-default" @click.prevent="selected_mod.banner = null" v-if="selected_mod.banner">Remove Image</button>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Release Thread</label>
                                <div class="col-xs-9">
                                    <input type="text" class="form-control" v-model="selected_mod.release_thread">
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Videos</label>
                                <div class="col-xs-9">
                                    <textarea class="form-control" v-model="video_urls"></textarea>

                                    <span class="help-block">You can put YouTube links here, one per line.</span>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Screenshots</label>
                                <div class="col-xs-9">
                                    <div v-for="img, i in selected_mod.screenshots">
                                        <img :src="'file://' + img">
                                        <button class="btn btn-small btn-default" @click.prevent="swapScreens(i, -1)"><i class="fa fa-chevron-up"></i></button>
                                        <button class="btn btn-small btn-default" @click.prevent="swapScreens(i, 1)"><i class="fa fa-chevron-down"></i></button>
                                        <button class="btn btn-small btn-default" @click.prevent="selected_mod.screenshots.splice(i, 1)"><i class="fa fa-times"></i></button>
                                    </div>

                                    <br>
                                    <button class="btn btn-default" @click.prevent="addScreen">Add Screenshot</button>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">First Release</label>
                                <div class="col-xs-9">
                                    <p class="form-control-static">{{ selected_mod.first_release }}</p>
                                    <!-- TODO: Date widget -->
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Last Update</label>
                                <div class="col-xs-9">
                                    <p class="form-control-static">{{ selected_mod.last_update }}</p>
                                </div>
                            </div>

                            <div class="col-xs-9 col-xs-offset-3">
                                <kn-save-btn :save-handler="saveDetails" />
                            </div>
                        </div>

                        <div v-else-if="!selected_pkg && page === 'fso'">
                            <h4>FSO Settings</h4>
                            <p>
                                These settings apply when you run FSO from the Develop tab and will apply to players.
                            </p>

                            <kn-fso-settings :mods="mods" :fso_build.sync="fso_build" :cmdline.sync="(selected_mod || {}).cmdline"></kn-fso-settings>

                            <div class="col-xs-9 col-xs-offset-3">
                                <kn-save-btn :save-handler="saveFsoSettings" />
                            </div>
                        </div>

                        <div v-else-if="!selected_pkg && page === 'mod_flag'">
                            <h4>-mod Flag</h4>

                            <p v-if="selected_mod.mod_flag.length < 1">
                                No dependencies available. Add your dependencies to the relevant packages and then
                                return here.
                            </p>

                            <div v-for="(dep, i) in selected_mod.mod_flag">
                                <a href="#" @click.prevent="swapFlagMod(i, -1)"><i class="fa fa-chevron-up"></i></a>
                                <a href="#" @click.prevent="swapFlagMod(i, 1)"><i class="fa fa-chevron-down"></i></a>

                                {{ mod_map[dep].title }}
                            </div>

                            <kn-save-btn :save-handler="saveModFlag" />
                        </div>

                        <div v-else-if="!selected_pkg && page === 'team'">
                            <h4>Staff List</h4>

                            <p>
                                <kn-dev-staff :mid="selected_mod.id"></kn-dev-staff>
                            </p>
                        </div>

                        <div v-if="selected_mod && selected_pkg">
                            <h4>Package</h4>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Name</label>
                                <div class="col-xs-9">
                                    {{ selected_pkg.name }}
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Folder</label>
                                <div class="col-xs-9">
                                    {{ selected_pkg.folder }}
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Description</label>
                                <div class="col-xs-9">
                                    <textarea class="form-control" v-model="selected_pkg.notes"></textarea>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Status</label>
                                <div class="col-xs-9">
                                    <select class="form-control" v-model="selected_pkg.status">
                                        <option value="required">Required</option>
                                        <option value="recommended">Recommended</option>
                                        <option value="optional">Optional</option>
                                    </select>
                                </div>
                            </div>

                            <div class="form-group" v-if="selected_mod.type !== 'engine' && selected_mod.type !== 'engine'">
                                <div class="col-xs-9 col-xs-offset-3">
                                    <div class="checkbox">
                                        <label>
                                            <input type="checkbox" v-model="selected_pkg.is_vp">
                                            Pack the contents as .VP
                                        </label>
                                    </div>
                                </div>
                            </div>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">Dependencies</label>
                                <div class="col-xs-9">
                                    <div v-for="(dep, i) in selected_pkg.dependencies">
                                        <a href="#" @click.prevent="swapDep(i, -1)"><i class="fa fa-chevron-up"></i></a>
                                        <a href="#" @click.prevent="swapDep(i, 1)"><i class="fa fa-chevron-down"></i></a>

                                        <a href="#" @click.prevent="editDep(i, dep)">{{ (mod_map[dep.id] || { title: 'NOT FOUND!' }).title }}</a>
                                        <span v-if="dep.packages && dep.packages.length > 0">({{ dep.packages.join(', ') }})</span>
                                    </div>

                                    <a href="#" @click.prevent="addDep()">Add a dependency</a>

                                    <div v-if="edit_dep">
                                        <br>
                                        <div class="form-group">
                                            <label class="col-xs-4 control-label">Mod</label>
                                            <div class="col-xs-8">
                                                <select class="form-control" v-model="edit_dep_mod" @change="updateDepMod">
                                                    <option v-for="mod in mods" :value="mod.id" :key="mod.id">{{ mod.title }}</option>
                                                </select>
                                            </div>
                                        </div>
                                        
                                        <div class="form-group">
                                            <label class="col-xs-4 control-label">Version</label>
                                            <div class="col-xs-8">
                                                <select class="form-control" disabled v-if="!mod_map[edit_dep_mod]"></select>
                                                <select class="form-control" v-model="edit_dep_version" @change="updateDepModVersion" v-else>
                                                    <option :value="null" :key="'newest'">newest</option>
                                                    <option v-for="v in edit_dep_versions" :value="v[0]" :key="v[0]">{{ v[1] }}</option>
                                                </select><br>

                                                <label v-if="mod_map[edit_dep_mod] && mod_map[edit_dep_mod].type === 'engine'">
                                                    <input type="checkbox" v-model="edit_dep_allow_new">
                                                    Allow newer versions
                                                </label>
                                            </div>
                                        </div>

                                        <div class="form-group">
                                            <label class="col-xs-4 control-label">Packages</label>
                                            <div class="col-xs-8">
                                                <span v-if="!edit_dep_pkgs" class="help-block">Please select a mod above.</span>

                                                <div v-if="edit_dep_pkgs">
                                                    <label class="checkbox" v-for="pkg in edit_dep_pkgs">
                                                        <input type="checkbox" :key="pkg.name" v-model="edit_dep_pkg_sel[pkg.name]" v-if="pkg.status !== 'required'">
                                                        <input type="checkbox" :key="pkg.name" disabled checked="true" v-if="pkg.status === 'required'">
                                                        {{ pkg.name }}
                                                    </label>
                                                </div>
                                            </div>
                                        </div>

                                        <button class="btn btn-small btn-success" @click.prevent="saveDep">Save</button>
                                        &nbsp;&nbsp;
                                        <button class="btn btn-small" @click.prevent="edit_dep = false">Cancel</button>

                                        <button class="btn btn-small pull-right" v-if="edit_dep_idx !== -1" @click.prevent="deleteDep">Delete</button>
                                    </div>
                                </div>
                            </div>

                            <div class="form-group" v-if="selected_mod.type === 'engine' || selected_mod.type === 'tool'">
                                <label class="col-xs-3 control-label">Conditions</label>
                                <div class="col-xs-9">
                                    <textarea class="form-control" rows="5" v-model="selected_pkg.environment"></textarea>

                                    <span class="help-block">
                                        This field determines on which CPUs and OS this
                                        {{ selected_mod.type === 'engine' ? 'build' : 'tool' }}
                                        is available. It can contain an expression like "x86_64 &amp;&amp; sse2 &amp;&amp; windows"
                                    </span>

                                    <p class="help-block">
                                        TODO: Add a list of available variables.
                                    </p>
                                </div>
                            </div>

                            <div class="form-group" v-if="selected_mod.type === 'engine' || selected_mod.type === 'tool'">
                                <label class="col-xs-3 control-label">Executables</label>
                                <div class="col-xs-9">
                                    <table class="table">
                                        <tr v-for="(exe, i) in selected_pkg.executables" :key="exe.file">
                                            <td>
                                                <input type="text" class="form-control" v-model="exe.file">
                                            </td>
                                            <td>
                                                <input type="text" class="form-control" v-model="exe.label" placeholder="name">
                                            </td>
                                            <td>
                                                <button class="btn btn-small btn-danger" @click.prevent="deleteExe(i)"><i class="fa fa-times"></i></button>
                                            </td>
                                        </tr>
                                    </table>
                                    <p class="help-block">
                                        Please use the name column to label debug builds and other tools like FRED.
                                        Executables without a name are expected to be FSO release builds.
                                    </p>

                                    <button type="button" class="btn btn-small" @click.prevent="addExe">Add</button>
                                    <button type="button" class="btn btn-small" @click.prevent="autoAddExes">Auto Add</button>
                                </div>
                            </div>

                            <div class="form-group">
                                <div class="col-xs-9 col-xs-offset-3">
                                    <kn-save-btn :save-handler="savePackage">
                                        <template slot-scope="{ click }">
                                            <button :class="'mod-btn btn-' + (edit_dep ? 'grey' : 'green')" @click.prevent="click" :disabled="edit_dep">
                                                <span class="btn-text">SAVE</span>
                                            </button>

                                            <button class="mod-btn btn-red" @click.prevent="deletePackage">
                                                <span class="btn-text">DELETE</span>
                                            </button>
                                        </template>
                                    </kn-save-btn>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
                <div class="devel-shadow-effect" :style="{ width: $refs.container ? $refs.container.clientWidth + 'px' : 'auto' }"></div>
            </div>
        </div>
    </div>
</template>