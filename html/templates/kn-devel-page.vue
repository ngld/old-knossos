<script>
export default {
    props: ['mods'],

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
        edit_dep_pkgs: null,
        edit_dep_pkg_sel: null,

        tab_scroll: -1
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

    watch: {
        mods(new_list) {
            this.reloading = true;
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

            this.reloading = false;
        },

        selected_mod(sel_mod) {
            if(this.reloading) return;
            this.selected_pkg = null;

            if(sel_mod) {
                this.tab_scroll = -1;
                this.fso_build = null;
                this.video_urls = sel_mod.videos.join("\n");

                this.tools = [];
                call(fs2mod.getModTools, this.selected_mod.id, this.selected_mod.version, (tools) => {
                    this.tools = tools;
                });

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
            if(this.reloading) return;
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

            this.edit_dep_version = null;
            this.edit_dep_pkgs = [];
            this.edit_dep_pkg_sel = {};

            if(mod && mod.packages) {
                for(let pkg of mod.packages) {
                    this.edit_dep_pkgs.push(pkg);
                    this.edit_dep_pkg_sel[pkg.name] = pkg.status === 'recommended';
                }
            }
        }
    },

    computed: {
        engine_builds() {
            let builds = [];
            for(let mod of this.mods) {
                if(mod.type === 'engine') {
                    builds = builds.concat(mod.versions);
                }
            }

            return builds;
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
        },

        selectMod(mod) {
            // TODO: Warn about unsaved changes?
            this.selected_mod = Object.assign({}, mod);
            this.sel_version = this.selected_mod.version;
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
            fs2mod.saveModDetails(JSON.stringify(mod));
        },

        saveFsoSettings() {
            let mod = this.selected_mod;

            fs2mod.saveModFsoDetails(mod.id, mod.version, this.fso_build, mod.cmdline);
        },

        selectCustomBuild() {
            call(fs2mod.selectCustomBuild, (result) => {
                this.selected_mod.custom_build = result;
                this.fso_build = 'custom#' + result;
            });
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

        changeImage(prop) {
            call(fs2mod.selectImage, this.selected_mod[prop] || (this.selected_mod.folder + '/dummy'), (new_path) => {
                if(new_path !== '') {
                    this.selected_mod[prop] = new_path;
                }
            });
        },

        isValidBuild() {
            return this.fso_build && this.fso_build.indexOf('#') > -1;
        },

        saveModFlag() {
            fs2mod.saveModFlag(this.selected_mod.id, this.selected_mod.version, this.selected_mod.mod_flag);
        },

        addDep() {
            this.edit_dep_idx = -1;
            this.edit_dep_mod = null;
            this.edit_dep_version = null;
            this.edit_dep_pkgs = [];
            this.edit_dep_pkg_sel = {};
            this.edit_dep = true;
        },

        editDep(idx, dep) {
            this.edit_dep_idx = idx;
            this.edit_dep_mod = dep.id;
            this.edit_dep_version = dep.version;
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
                version: this.edit_dep_version,
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
                        'file': path,
                        'debug': false
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
                            'file': path,
                            'debug': false
                        });
                    }
                }
            });
        },

        deleteExe(i) {
            this.selected_pkg.executables.splice(i, 1);
        },

        uploadMod()  {
            vm.popup_progress_message = null;
            vm.popup_mode = 'are_you_sure';
            vm.popup_title = 'Upload mod';
            vm.popup_sure_question = `Are you sure that you want to upload ${this.selected_mod.title} ${this.selected_mod.version}?`;
            vm.sureCallback = () => {
                vm.popup_mode = 'mod_progress';
                // We need the original mod here because the copy doesn't contain the progress info.
                vm.popup_content = this.mod_map[this.selected_mod.id];

                fs2mod.startUpload(this.selected_mod.id, this.selected_mod.version);
            };
            vm.popup_visible = true;
        },

        deleteMod()  {
            vm.popup_mode = 'are_you_sure';
            vm.popup_title = 'Delete mod release';
            vm.popup_sure_question = `Are you sure that you want to delete ${this.selected_mod.title} ${this.selected_mod.version}?` +
                "\nThis will only delete this specific version.";

            vm.sureCallback = () => {
                fs2mod.nebDeleteMod(this.selected_mod.id, this.selected_mod.version);
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
        }
    }
};
</script>
<template>
    <div>
        <div class="scroll-style mlist">
            <button class="mod-btn btn-link-blue" @click.prevent="openCreatePopup"><span class="btn-text">CREATE</span></button>
            <!-- <button class="btn btn-default btn-small dev-btn" @click.prevent="showRetailPrompt">INSTALL RETAIL</button> -->

            <a href="#" v-for="mod in mods" v-if="mod.dev_mode" :key="mod.id" :class="{ active: selected_mod && selected_mod.id === mod.id }" @click="selectMod(mod)">{{ mod.title }}</a>
        </div>
        <div class="content-pane">
            <div class="logo-box" v-if="selected_mod">
                <kn-dev-mod :mod="selected_mod" tab="develop"></kn-dev-mod>

                <p>
                    <button @click.prevent="launchMod" class="mod-btn btn-green"><p>Play</p></button>
                    <button v-for="tool in tools" @click.prevent="launchTool(tool)" :class="'mod-btn btn-' + (tool.toLowerCase().indexOf('fred') > -1 ? 'orange' : tool.toLowerCase().indexOf('debug') > -1 ? 'yellow' : 'grey')"><p>{{ tool }}</p></button>

                    <br><br>
                    <button @click.prevent="uploadMod" class="mod-btn btn-link-blue">Upload</button>
                    <button @click.prevent="deleteMod" class="mod-btn btn-link-red">Delete</button><br>
                    <button @click.prevent="openNewVersionPopup" class="mod-btn btn-link-grey">+ Version</button>
                    <button @click.prevent="addPackage" class="mod-btn btn-link-grey">+ Package</button>
                </p>

                Mod Versions:
                <select class="form-control mod-version" v-model="sel_version" @change="selectVersion(sel_version)">
                    <option v-for="m in selected_mod.versions">{{ m.version }}</option>
                </select>
                <br>

                Mod Path:
                <br>
                <span class="version-link"><a href="#" @click.prevent="openModFolder">{{ selected_mod.folder }}</a></span>
            </div>
            <div class="dev-instructions" v-else>
                This is the Development tab. Here you can create new mods or edit currently installed mods. This is also where you can apply experimental mod settings, work with the Freespace Mission Editor, and alter the mod flags and commandline options. <br><br>Consider this an advanced section of Knossos but also a great place to get started if you wish to learn the ins and outs of modding with Freespace 2 Open.
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
                            @click.prevent="selectPkg(pkg)">
                            {{ pkg.name }}
                        </a>

                        <div class="dev-tabbar-arrows">
                            <a href="#" @click.prevent="tabScroll(-1)"><i class="fa fa-chevron-left"></i></a>
                            <a href="#" @click.prevent="tabScroll(1)"><i class="fa fa-chevron-right"></i></a>
                        </div>
                    </div>
                </div>

                <div class="form-content container-fluid scroll-style">
                    <form class="form-horizontal" v-if="selected_mod">
                        <div v-if="!selected_pkg && page === 'details'">
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
                                        <option value="tool">Tool</option>
                                        <option value="ext">Extension</option>
                                    </select>

                                    <span class="help-block" v-if="selected_mod.type === 'mod'">
                                        This type is the default and covers most cases. Normally you'll want to use this type.
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'tc'">
                                        Use this type if your mod doesn't depend on other mods or retail files.<br>
                                        (Mods for TCs should still use the "Mod" type.)
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'engine'">
                                        This should only be used for builds FSO builds (fs2_open*.exe, fs2_open*.AppImage, etc.).
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'tool'">
                                        This is used for all executables which aren't FSO like FRED or PCS2.
                                    </span>

                                    <span class="help-block" v-if="selected_mod.type === 'ext'">
                                        This mod type is meant for overrides like custom HUD tables.
                                    </span>
                                </div>
                            </div>

                            <div class="form-group" v-if="selected_mod.type === 'mod' || selected_mod.type === 'ext'">
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
                                        Please use BBCode here. To preview your description, save, go to your home tab
                                        and go to this mod's detail page.
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
                                        This image should be about 255&times;112 pixels large. Please only use this for legacy logos and mod images from mods predating the Knossos installer.
                                        If you create a new mod logo or image, please use the above setting.
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

                            <div class="form-group">
                                <div class="col-xs-9 col-xs-offset-3">
                                    <button class="mod-btn btn-green" @click.prevent="saveDetails"><span class="btn-text">SAVE</span></button>
                                </div>
                            </div>
                        </div>

                        <div v-if="!selected_pkg && page === 'fso'">
                            <h4>FSO Settings</h4>

                            <div class="form-group">
                                <label class="col-xs-3 control-label">FSO build</label>
                                <div class="col-xs-9">
                                    <div class="input-group">
                                        <select class="form-control" v-model="fso_build">
                                            <option v-if="!isValidBuild()" :key="'invalid'" value="invalid">Please select a valid build</option>
                                            <option v-for="mod in engine_builds" :key="mod.id + '-' + mod.version" :value="mod.id + '#' + mod.version">
                                                {{ mod.title }} {{ mod.version }}
                                            </option>
                                            <option v-if="selected_mod.custom_build" :value="'custom#' + selected_mod.custom_build">{{ selected_mod.custom_build.replace(/\\/g, '/').split('/').pop() }}</option>
                                        </select>
                                        <span class="input-group-btn">
                                            <button class="btn btn-default" @click.prevent="selectCustomBuild">Browse...</button>
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <kn-flag-editor :caps="caps" :cmdline.sync="selected_mod.cmdline"></kn-flag-editor>

                            <div class="form-group">
                                <div class="col-xs-9 col-xs-offset-3">
                                    <button class="mod-btn btn-green" @click.prevent="saveFsoSettings"><span class="btn-text">SAVE</span></button>
                                </div>
                            </div>
                        </div>

                        <div v-if="!selected_pkg && page === 'mod_flag'">
                            <h4>-mod Flag</h4>

                            <p v-if="selected_mod.mod_flag.length < 1">
                                No dependencies available. Please add your dependencies to the relevant packages and then
                                return here.
                            </p>

                            <div v-for="(dep, i) in selected_mod.mod_flag">
                                <a href="#" @click.prevent="swapFlagMod(i, -1)"><i class="fa fa-chevron-up"></i></a>
                                <a href="#" @click.prevent="swapFlagMod(i, 1)"><i class="fa fa-chevron-down"></i></a>

                                {{ mod_map[dep].title }}
                            </div>

                            <button class="mod-btn btn-green" @click.prevent="saveModFlag"><span class="btn-text">SAVE</span></button>
                        </div>

                        <div v-if="!selected_pkg && page === 'team'">
                            <h4>Staff List</h4>

                            <p>
                                This page hasn't been implemented, yet.
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
                                                <select class="form-control" v-model="edit_dep_mod">
                                                    <option v-for="mod in mods" :value="mod.id" :key="mod.id">{{ mod.title }}</option>
                                                </select>
                                            </div>
                                        </div>
                                        
                                        <div class="form-group">
                                            <label class="col-xs-4 control-label">Version</label>
                                            <div class="col-xs-8">
                                                <select class="form-control" disabled v-if="!mod_map[edit_dep_mod]"></select>
                                                <select class="form-control" v-model="edit_dep_version" v-else>
                                                    <option :value="null" :key="'newest'">newest</option>
                                                    <option v-for="v in mod_map[edit_dep_mod].versions" :value="v.version" :key="v.version">{{ v.version }}</option>
                                                </select>
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

                                        <button class="btn btn-small" @click.prevent="saveDep">Save</button>

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
                                    <button class="mod-btn btn-green" @click.prevent="savePackage"><span class="btn-text">SAVE</span></button>

                                    <button class="mod-btn btn-red" @click.prevent="deletePackage">DELETE</button>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
</template>