<script>
import Popper from 'vue-popperjs';
import 'vue-popperjs/dist/css/vue-popper.css';
import KnTroubleshooting from './kn-troubleshooting.vue';

let next_tab = null;
let first_load = true;

export default {
    components: {
        'kn-troubleshooting': KnTroubleshooting,
        popper: Popper
    },

    data: () => ({
        w: window,

        tabs: {
            home: 'Home',
            explore: 'Explore',
            develop: 'Develop',
            trouble: 'Troubleshooting'
        },

        search_text: '',
        status_message: '',
        tab: 'explore',
        page: 'modlist',
        show_filter: false,
        mods: [],
        mod_table: {},

        // details page
        detail_mod: null,

        popup_visible: false,
        popup_title: 'Popup',
        popup_mode: '',
        popup_content: null,

        popup_progress_message: null,
        popup_progress: {},
        popup_progress_cancel: null,

        popup_mod_name: '',
        popup_mod_id: '',
        popup_mod_version: '1.0.0',
        popup_mod_type: 'mod',
        popup_mod_parent: 'FS2',
        popup_mod_tcs: [],

        popup_mod_new_version: '',
        popup_mod_method: 'copy',

        popup_mod_message: '',

        popup_mod_exes: [],
        popup_mod_flag: [],
        popup_mod_sel_exe: null,
        popup_mod_is_tool: false,
        popup_mod_flag_map: {},

        popup_pkg_name: '',
        popup_pkg_folder: '',

        popup_ini_path: '',

        popup_sure_question: '',
        sureCallback: null,

        popup_finished: null,

        // retail prompt
        retail_searching: true,
        retail_found: false,
        detected_retail_path: '',
        retail_folder_path: '',
        gog_installer_path: '',
        retail_data_path: '', // TODO remove once no longer needed
        mod_install_attempted: false,
        retail_install_option: 'auto-detect-installation',

        retail_data_path: '',
        sort_types: ['alphabetical', 'last_played', 'last_released', 'last_updated'],
        sort_type: 'alphabetical'
    }),

    watch: {
        search_text(phrase) {
            fs2mod.triggerSearch(phrase);
        }
    },

    methods: {
        openLink(url) {
            fs2mod.openExternal(url);
        },

        openScreenshotFolder() {
            fs2mod.openScreenshotFolder();
        },

        showHelp() {
            fs2mod.showTempHelpPopup();
        },

        updateList() {
            fs2mod.fetchModlist();
        },

        showSettings() {
            this.tab = null;
            this.page = 'settings';
        },

        showTab(tab) {
            // TODO: This is ugly.
            if(tab === 'trouble') {
                this.tab = tab;
                this.page = tab;
                return;
            }
            next_tab = tab;

            if(window.qt) {
                fs2mod.showTab(tab);
            } else {
                setTimeout(() => { fs2mod.showTab(tab); }, 100);
            }
        },

        updateModlist(mods) {
            this.mods = mods;

            if(next_tab) {
                this.tab = next_tab;
                this.page = next_tab === 'develop' ? 'develop' : 'modlist';
                next_tab = null;
            } else if(first_load) {
                first_load = false;

                if(this.page !== 'welcome') {
                    next_tab = mods.length === 0 ? 'explore' : 'home';
                    fs2mod.showTab(next_tab);
                }
            } else if(this.page === 'details' && !mod_table[this.detail_mod]) {
                // The currently visible mod has been uninstalled thus making displaying this page impossible.
                // Switch to the tab instead
                this.exitDetails();
            }
        },

        exitDetails() {
            this.page = 'modlist';
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

            call(fs2mod.createMod, this.popup_ini_path, this.popup_mod_name, this.popup_mod_id, this.popup_mod_version,
                this.popup_mod_type, this.popup_mod_parent,
                (result) => {
                    if(result) {
                        this.popup_visible = false;
                    }
                }
            );
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

            if(this.popup_pkg_folder.indexOf(' ') > -1) {
                alert("Your folder name must not contain a space!");
                return;
            }

            call(fs2mod.addPackage, this.popup_mod_id, this.popup_mod_version, this.popup_pkg_name, this.popup_pkg_folder, (result) => {
                if(result > -1) {
                    dp.selected_pkg = dp.selected_mod.packages[result];
                    this.popup_visible = false;
                }
            });
        },

        createNewModVersion() {
            call(fs2mod.createModVersion, this.popup_mod_id, this.popup_mod_version, this.popup_mod_new_version, this.popup_mod_method, (result) => {
                if(result) {
                    this.popup_visible = false;
                }

                if(this.popup_finished) {
                    this.popup_finished(result);
                }
            });
        },

        sendModReport() {
            call(fs2mod.nebReportMod, this.popup_mod_id, this.popup_mod_version, this.popup_mod_message, (result) => {
                if(result) {
                    this.popup_visible = false;
                }
            });
        },

        showModErrors() {
            this.popup_content = this.mod;
            this.popup_title = 'Mod errors';
            this.popup_mode = 'mod_errors';
            this.popup_visible = true;
        },

        showModProgress() {
            this.popup_progress_message = null;
            this.popup_mod_id = this.mod.id;
            this.popup_title = 'Installation Details';
            this.popup_mode = 'mod_progress';
            this.popup_progress_cancel = null;
            this.popup_visible = true;
        },

        showRetailPrompt(mod_install_attempted) {
            this.popup_mode = 'retail_prompt';
            this.popup_title = mod_install_attempted ? 'FreeSpace 2 data missing' : "Install FreeSpace 2";
            this.popup_visible = true;

            this.retail_data_path = '';
            this.detected_retail_path = '';
            this.retail_folder_path = '';
            this.gog_installer_path = '';
            this.retail_install_option = 'auto-detect-installation';
            this.mod_install_attempted = mod_install_attempted;
            this.retailAutoDetect();
        },

        retailAutoDetect() {
            this.retail_searching = true;
            this.retail_found = false;

            call(fs2mod.searchRetailData, (path) => {
                this.retail_searching = false;

                if(path !== '') {
                    this.retail_found = true;
                    this.detected_retail_path = path;
                }
            });
        },

        selectRetailFolder() {
            call(fs2mod.browseFiles, 'Select your FreeSpace 2 folder\'s Root_fs2.vp', '', '*.vp', (vp_files) => {
                if(vp_files.length > 0) {
                    let root_vp_path = vp_files[0];
                    call(fs2mod.verifyRootVPFolder, root_vp_path, (result) => {
                        if(result) {
                            this.retail_folder_path = result;
                        }
                    });
                }
            });
        },

        selectRetailFile() {
            call(fs2mod.browseFiles, 'Select your setup_freespace2_...exe', this.gog_installer_path, '*.exe', (files) => {
                if (files.length > 0) {
                    this.gog_installer_path = files[0];
                }
            });
        },

        selectRetailLocation() {
            if(this.retail_install_option === 'select-installation-folder') {
                this.selectRetailFolder();
            } else {
                this.selectRetailFile();
            }
        },

        selectModIni() {
            // FIXME shouldn't retail_data_path be popup_ini_path?
            call(fs2mod.browseFiles, 'Please select the desired mod.ini', this.retail_data_path, 'mod.ini', (files) => {
                if(files.length > 0) {
                    this.popup_ini_path = files[0];
                    call(fs2mod.parseIniMod, this.popup_ini_path, (mod) => {
                        let ini_mod = JSON.parse(mod);

                        this.popup_mod_id = ini_mod.id;
                        this.popup_mod_name = ini_mod.title;
                    });
                }
            });
        },

        finishRetailPrompt() {
            let path = '';
            if(this.retail_install_option === 'select-installation-folder') {
                path = this.retail_folder_path;
            } else if(this.retail_install_option === 'select-installer-file') {
                path = this.gog_installer_path;
            } else {
                path = this.detected_retail_path;
            }
            call(fs2mod.copyRetailData, path, (result) => {
                if (result) {
                    this.popup_mod_id = 'FS2';
                    this.popup_title = 'FreeSpace 2';
                    this.popup_mode = 'mod_progress';
                    this.popup_progress_cancel = null;

                    connectOnce(fs2mod.retailInstalled, () => {
                        this.popup_visible = false;
                    });
                }
            });
        },

        launchModAdvanced() {
            let mod_flag = [];
            for(let part of this.popup_mod_flag) {
                if(this.popup_mod_flag_map[part[0]]) mod_flag.push(part[0]);
            }

            fs2mod.runModAdvanced(this.popup_mod_id, this.popup_mod_version, this.popup_mod_sel_exe, this.popup_mod_is_tool, mod_flag);
            this.popup_visible = false;
        },

        popupProposeFolder() {
            if(this.popup_pkg_folder === '') {
                this.popup_pkg_folder = this.popup_pkg_name.toLowerCase().replace(/ /g, '_');
            }
        },

        closePopup() {
            // There's no way to reopen the popup during the welcome assistant so just don't close it at that point.
            if(this.page !== 'welcome') {
                this.popup_visible = false;
            }
        },

        sortButtonClass(sort_button_type) {
            return [
                'filter-content-btn',
                this.sort_type === sort_button_type ? 'selected' : ''
            ];
        },

        setSortType(sort_type) {
            call(fs2mod.setSortType, sort_type, (type) => {
                if (type) this.sort_type = type;
            });
        },

        getSortTypeDisplayName(sort_type) {
            // adapted from https://flaviocopes.com/how-to-uppercase-first-letter-javascript/
            return sort_type.split('_').map(type => type.charAt(0).toUpperCase() + type.slice(1)).join(' ');
        }
    }
};
</script>
<template>
    <div class="root-container">
        <div class="main-menus">
            <div class="pull-right top-right-btns">
                <a href="#" class="top-btn" @click="showHelp"><span class="help-image"></span></a>
                <a href="#" class="top-btn" @click="updateList"><span class="update-image"></span></a>
                <a href="#" :class="{ 'top-btn': true, active: page === 'settings' }" @click="showSettings"><span class="settings-image"></span></a>
            </div>
            <div id="top-bar">
                <div class="mod-search">
                    <input v-model="search_text" type="text" placeholder="Search">
                </div>
                <div class="text-marquee">
                    <!-- <span>Announcements go here!</span> -->
                    {{ status_message }}
                </div>
            </div>
        </div>
    <!-------------------------------------------------------------------------------- Start the Tab Menus ---------->
        <div id="tab-bar" v-if="page !== 'details'">
            <a href="#" class="main-btn" v-for="(label, name) in tabs" :class="(tab === name ? 'active ' : '') + 'tab-' + name" @click.prevent="showTab(name)">
                <span :class="'icon ' + name + '-image'"></span>
                {{ label }}
            </a>
        </div>
        <div id="tab-bar-misc" class="keep-left" v-if="page === 'modlist'">
            <a href="#" @click.prevent="openScreenshotFolder" class="tab-misc-btn"><span class="screenshots-image"></span></a>
        </div>
        <div id="tab-bar-misc" class="keep-right" v-if="page !== 'modlist'">
            <a href="#" @click.prevent="openScreenshotFolder" class="tab-misc-btn"><span class="screenshots-image"></span></a>
        </div>
    <!-------------------------------------------------------------------------------- Start the Filter Button ---------->
        <popper v-if="page === 'modlist'"
                trigger="click"
                @show="show_filter = true"
                @hide="show_filter = false"
                class="filter-container"
                :options="{ placement: 'bottom-end', modifiers: { keepTogether: { enabeld: false }, arrow: { enabled: false }, offset: { offset: '0px, 7px' }}}">
            <div class="filter-content">
                <template v-for="sort_type in sort_types">
                    <div class="filter-lines">
                        <button :class="sortButtonClass(sort_type)" @click="setSortType(sort_type)">{{ getSortTypeDisplayName(sort_type) }}</button>
                    </div>
                </template>
            </div>

            <button :class="['filterbtn', show_filter ? 'filter-active' : '']" slot="reference"></button>
        </popper>

        <div class="welcome-overlay" v-if="page === 'welcome'"></div>

    <!-------------------------------------------------------------------------------- Start the Details Menu ---------->
        <div id="details-tab-bar" v-show="page === 'details'">
            <a href="#" class="main-btn" @click="exitDetails"><i class="fa fa-chevron-left"></i> Back</a>
            <span class="main-btn active"><i class="fa fa-exclamation-circle"></i> Details</span>
        </div>

    <!-------------------------------------------------------------------------------- Build the Main View container ---------->
        <keep-alive>
            <kn-scroll-container v-if="page === 'modlist'" key="modlist" :dummy="mods">
                <div class="container-fluid mod-container">
                    <div v-if="tab === 'home'">
                        <kn-mod-home v-for="mod in mods" :key="mod.id" :mod="mod" :tab="tab"></kn-mod-home>
                    </div>
                    <div v-else>
                        <kn-mod-explore v-for="mod in mods" :key="mod.id" :mod="mod" :tab="tab"></kn-mod-explore>
                    </div>
                    <div v-if="mods.length === 0" class="main-notice">No mods found.</div>
                </div>
            </kn-scroll-container>
        </keep-alive>

        <kn-scroll-container v-if="page === 'welcome'" key="welcome" :dummy="mods">
            <kn-welcome-page></kn-welcome-page>
        </kn-scroll-container>

        <kn-scroll-container v-if="page === 'details'" key="details" :dummy="detail_mod">
            <div class="info-page" id="details-page" slot-scope="{ update }">
                <kn-details-page :modbundle="mod_table[detail_mod]" :updater="update"></kn-details-page>
            </div>
        </kn-scroll-container>

        <kn-scroll-container v-if="page === 'settings'" key="settings" :dummy="mods">
            <div class="info-page settings-page container-fluid">
                <kn-settings-page :mods="mods"></kn-settings-page>
            </div>
        </kn-scroll-container>

        <keep-alive>
            <kn-scroll-container v-if="page === 'develop'" key="develop" :dummy="mods">
                <div class="info-page devel-page" v-if="page === 'develop'">
                    <kn-devel-page :mods="mods"></kn-devel-page>
                </div>
            </kn-scroll-container>
        </keep-alive>

        <kn-scroll-container v-if="page === 'trouble'" key="trouble">
            <div class="info-page trouble-page container-fluid">
                <kn-troubleshooting></kn-troubleshooting>
            </div>
        </kn-scroll-container>

        <div class="popup-bg" v-if="popup_visible" @click="closePopup"></div>

        <div class="popup" v-if="popup_visible">
            <div class="title clearfix">
                {{ popup_title }}

                <a href="" class="pull-right" @click.prevent="closePopup">
                    <i class="fa fa-times"></i>
                </a>
            </div>
            <div :class="{ content: true, 'gen-scroll-style': true, iframe: popup_mode === 'frame' }">
                <div v-if="popup_mode === 'html'" v-html="popup_content"></div>
                <iframe v-if="popup_mode === 'frame'" :src="popup_content"></iframe>

                <div v-if="popup_mode === 'mod_errors'">
                    <div v-for="pkg in popup_content.packages" v-if="pkg.check_notes && pkg.check_notes.length > 0">
                        <strong>{{ pkg.name }}</strong><br>
                        <ul>
                            <li v-for="msg in pkg.check_notes">{{ msg }}</li>
                        </ul>
                    </div>
                </div>

                <div v-if="popup_mode === 'mod_progress'">
                    <p v-if="popup_progress_message">{{ popup_progress_message }}</p>

                    <p v-if="!popup_progress[popup_mod_id]">
                        Preparing...
                    </p>

                    <button v-if="popup_progress_cancel" class="mod-btn btn-link-red" @click="popup_progress_cancel">
                        Cancel
                    </button>

                    <div v-for="row in (popup_progress[popup_mod_id] || [])" :key="row[0]" class="row">
                        <div class="col-xs-4 mod-prog-label">{{ row[0] }}</div>
                        <div class="col-xs-5">
                            <div :class="'mod-prog-bar' + (row[1] === 1 ? ' complete' : '')">
                                <div class="inner" :style="'width: ' + (row[1] * 100) + '%'"></div>
                            </div>
                        </div>
                        <div class="col-xs-3 mod-prog-status">{{ row[2] }}</div>
                    </div>
                </div>

                <div v-if="popup_mode === 'retail_prompt'">
                    <p>
                        <span v-if="mod_install_attempted">You need the FreeSpace 2 data files to play this mod.<br></span>
                        Choose how you want to install FreeSpace 2. You can buy it from
                        <a href="https://www.gog.com/game/freespace_2" class="open-ext">GOG</a>
                        or <a href="https://store.steampowered.com/app/273620/Freespace_2/" class="open-ext">Steam</a>.
                    </p>
                    <form class="form-horizontal col-xs-12">
                        <div class="form-group">
                            <label class="checkbox">
                                <input type="radio" value="auto-detect-installation" v-model="retail_install_option" @change="retailAutoDetect">
                                Auto-detect installation
                            </label>
                            <label class="checkbox">
                                <input type="radio" value="select-installation-folder" v-model="retail_install_option">
                                Select installation folder
                            </label>
                            <label class="checkbox">
                                <input type="radio" value="select-installer-file" v-model="retail_install_option">
                                Select GOG installer file
                            </label>
                        </div>
                    </form>

                    <p v-if="retail_install_option === 'select-installation-folder'">
                        Browse to the folder that has the FreeSpace 2 data files and find the file <strong>Root_fs2.vp</strong> or <strong>root_fs2.vp</strong>.<br>
                        Knossos will copy the files into the Knossos library.
                    </p>
                    <p v-else-if="retail_install_option === 'select-installer-file'">
                        Select the GOG FreeSpace 2 installer (example: setup_freespace2_2.0.0.8.exe).<br>
                        Knossos will extract the data files from the installer into the Knossos library.
                    </p>
                    <p v-else>
                        <span v-if="retail_searching"><strong>Searching files...</strong></span>
                        <span v-else-if="retail_found"><strong>FreeSpace 2 folder found</strong> at<br>
                        {{  detected_retail_path  }}</span>
                        <span v-else>
                            <strong>FreeSpace 2 folder auto-detection failed.</strong><br>
                            Choose another install option or install FreeSpace 2 and
                            <a href="#" @click.prevent="retailAutoDetect">try again</a>.
                        </span>
                    </p>
                    <p>
                        <div class="input-group" :style="{ visibility: (retail_install_option !== 'auto-detect-installation') ? 'visible' : 'hidden' }">
                            <input v-if="retail_install_option === 'select-installation-folder'" type="text" class="form-control" v-model="retail_folder_path">
                            <input v-else type="text" class="form-control" v-model="gog_installer_path">
                            <span class="input-group-btn">
                                <button class="btn btn-default" @click.prevent="selectRetailLocation">Browse...</button>
                            </span>
                        </div>
                    </p>
                    <p>
                        <button class="btn btn-primary" @click="finishRetailPrompt">Continue</button>
                        <button class="btn btn-default pull-right" @click.prevent="popup_visible = false">Cancel</button>
                    </p>
                </div>

                <div v-if="popup_mode === 'create_mod'">
                    <form class="form-horizontal">
                        <div class="form-group">
                            <label class="col-xs-3 control-label">Name</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_mod_name">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">ID</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_mod_id" pattern="^[a-zA-Z0-9_]+$">

                                <span class="help-block">Only characters (a-z, A-Z), numbers (0-9) and underscores are allowed.</span>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Mod.ini path</label>
                            <div class="col-xs-9">
                                <div class="input-group">
                                    <input type="text" class="form-control" v-model="popup_ini_path">
                                    <span class="input-group-btn">
                                        <button class="btn btn-default" @click.prevent="selectModIni">Select mod.ini</button>
                                    </span>
                                </div>

                                <p class="help-block">Only use this if you want to convert a legacy mod! Will update Name and ID fields above.</p>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Version</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_mod_version" pattern="^([0-9]+\.){0-2}[0-9]+(\-.*)?$">

                                <span class="help-block">
                                    TODO: Version explanation. The versioning scheme is still pending. See the forum thread for details.
                                </span>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Type</label>
                            <div class="col-xs-9">
                                <select class="form-control" v-model="popup_mod_type">
                                    <option value="mod">Mod</option>
                                    <option value="tc" v-if="popup_mode === 'create_mod'">Total Conversion</option>
                                    <option value="engine" v-if="popup_mode === 'create_mod'">FSO build</option>
                                    <!-- TODO uncomment once Tool and Extension are supported
                                    <option value="tool" v-if="popup_mode === 'create_mod'">Tool</option>
                                    <option value="ext">Extension</option>
                                    -->
                                </select>

                                <span class="help-block" v-if="popup_mod_type === 'mod'">
                                    A campaign based on FreeSpace 2 (retail) or on a total conversion (TC).<br>
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'tc'">
                                    A standalone game that doesn't depend on other mods and doesn't use FS2 files.<br>
                                    Mods for TCs should use the "Mod" type.
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'engine'">
                                    A build of the FreeSpace Open (FSO) engine (fs2_open*.exe, fs2_open*.AppImage, fs2_open*.app, etc.)
                                </span>
                                <!-- TODO uncomment once tools and extensions are supported
                                <span class="help-block" v-if="popup_mod_type === 'tool'">
                                    Software other than the FreeSpace Open (FSO) engine.<br>
                                    Examples include FRED (mission editor) and PCS2 (model converter).
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'ext'">
                                    A change that overrides, such as custom HUD tables
                                </span>
                                -->
                            </div>
                        </div>

                        <div class="form-group" v-if="popup_mod_type === 'mod' || popup_mod_type === 'ext'">
                            <label class="col-xs-3 control-label">Parent mod</label>
                            <div class="col-xs-9">
                                <select class="form-control" v-model="popup_mod_parent">
                                    <option v-for="mod in popup_mod_tcs" :value="mod.id" :key="mod.id">{{ mod.title }}</option>
                                </select>

                                <span class="help-block">
                                    The game your mod is based on, either FreeSpace 2 ("Retail FS2") or a total conversion (TC).
                                </span>
                            </div>
                        </div>

                        <button class="mod-btn btn-green" @click.prevent="createMod">CREATE</button>
                        <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">CANCEL</button>
                    </form>
                </div>

                <div v-if="popup_mode === 'add_pkg'">
                    <form class="form-horizontal">
                        <div class="form-group">
                            <label class="col-xs-3 control-label">Name</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_pkg_name" @blur="popupProposeFolder">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Folder</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_pkg_folder">
                            </div>
                        </div>

                        <button class="mod-btn btn-green" @click.prevent="addPackage">ADD</button>
                        <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">CANCEL</button>
                    </form>
                </div>

                <div v-if="popup_mode === 'new_mod_version'">
                    <form class="form-horizontal">
                        <div class="form-group">
                            <label class="col-xs-3 control-label">Mod</label>
                            <div class="col-xs-9">
                                <p class="form-control-static">{{ popup_mod_name }}</p>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Old Version</label>
                            <div class="col-xs-9">
                                <p class="form-control-static">{{ popup_mod_version }}</p>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">New Version</label>
                            <div class="col-xs-9">
                                <input type="text" class="form-control" v-model="popup_mod_new_version">
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Method</label>
                            <div class="col-xs-9">
                                <label class="checkbox">
                                    <input type="radio" name="v_popup_mod_method" value="copy" v-model="popup_mod_method">
                                    Copy the old folder
                                </label>

                                <label class="checkbox">
                                    <input type="radio" name="v_popup_mod_method" value="rename" v-model="popup_mod_method">
                                    Rename the old folder
                                </label>

                                <label class="checkbox">
                                    <input type="radio" name="v_popup_mod_method" value="empty" v-model="popup_mod_method">
                                    Create a new folder
                                </label>
                            </div>
                        </div>

                        <button class="mod-btn btn-green" @click.prevent="createNewModVersion">CREATE</button>
                        <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">CANCEL</button>
                    </form>
                </div>

                <div v-if="popup_mode === 'report_mod'">
                    <form class="form-horizontal">
                        <div class="form-group">
                            <label class="col-xs-3 control-label">Mod</label>
                            <div class="col-xs-9">
                                <p class="form-control-static">{{ popup_mod_name }}</p>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Version</label>
                            <div class="col-xs-9">
                                <p class="form-control-static">{{ popup_mod_version }}</p>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="col-xs-3 control-label">Message</label>
                            <div class="col-xs-9">
                                <textarea class="form-control" v-model="popup_mod_message" placeholder="Please provide a reason for your report.">
                                </textarea>
                            </div>
                        </div>

                        <button class="mod-btn btn-green" @click.prevent="sendModReport">SEND</button>
                        <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">CANCEL</button>
                    </form>
                </div>

                <div v-if="popup_mode == 'launch_mod'">
                    <form class="form">
                        <div class="form-group">
                            <label class="control-label" for="mod_exes">FSO build / Tool</label>
                            <select name="mod_exes" class="form-control" v-model="popup_mod_sel_exe">
                                <option v-for="x in popup_mod_exes" :key="x[0]" :value="x[0]">{{ x[1] }}</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label class="control-label">Activated packages</label>
                            <div class="checklist">
                                <label class="checkbox" v-for="p in popup_mod_flag">
                                    <input type="checkbox" v-model="popup_mod_flag_map[p[0]]">
                                    {{ p[1] }}
                                </label>
                            </div>
                        </div>

                        <div class="form-group">
                            <button class="mod-btn btn-green" @click.prevent="launchModAdvanced">LAUNCH</button>
                            <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">CANCEL</button>
                        </div>
                    </form>
                </div>

                <div v-if="popup_mode == 'are_you_sure'">
                    <p>
                        {{ popup_sure_question }}
                    </p>

                    <button class="mod-btn btn-green" @click.prevent="sureCallback">YES</button>
                    <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">NO</button>
                </div>

                <div v-if="popup_mode == 'upload_mod'">
                    <p>
                        Upload {{popup_mod_name}} {{popup_mod_version}} to Nebula?
                    </p>

                    <p>
                        <label>
                            <input type="checkbox" v-model="popup_content">
                            Mark this release as private
                        </label>
                    </p>

                    <button class="mod-btn btn-green" @click.prevent="sureCallback">YES</button>
                    <button class="mod-btn btn-red pull-right" @click.prevent="popup_visible = false">NO</button>
                </div>

                <div v-if="popup_mode == 'fso_settings'">
                    <kn-fso-user-settings :mods="mods" :mod="popup_content"></kn-fso-user-settings>
                </div>

                <div v-if="popup_mode === 'debug_log'">
                    <p>
                        You debug log was successfully uploaded and can now be accessed through the following link:
                    </p>
                    <p>
                        <a :href="popup_content" class="open-ext">{{ popup_content }}</a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>