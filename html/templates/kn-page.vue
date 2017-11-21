<script>
export default {
    data: () => ({
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

        popup_progress_message: null,

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
        popup_mod_flag_map: {},

        popup_pkg_name: '',
        popup_pkg_folder: '',

        popup_ini_path: '',

        popup_sure_question: '',
        sureCallback: null,

        // retail prompt
        retail_searching: true,
        retail_found: false,
        retail_data_path: ''
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
            call(fs2mod.getPreferencesPath, (path) => {
                fs2mod.openExternal('file://' + path + 'screenshots');
            });
        },

        showHelp() {
            alert('Not yet implemented! Sorry.');
        },

        updateList() {
            fs2mod.fetchModlist();
        },

        showSettings() {
            this.tab = null;
            this.page = 'settings';
        },

        showTab(tab) {
            if(this.page === 'settings') {
                this.tab = tab;
                this.page = tab === 'develop' ? 'develop' : 'modlist';
            }

            if(window.qt) {
                fs2mod.showTab(tab);
            } else {
                setTimeout(() => { fs2mod.showTab(tab); }, 100);
            }
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
            this.popup_content = this.mod;
            this.popup_title = 'Installation Details';
            this.popup_mode = 'mod_progress';
            this.popup_visible = true;
        },

        showRetailPrompt() {
            this.popup_mode = 'retail_prompt';
            this.popup_title = 'Retail data missing';
            this.popup_visible = true;

            this.retail_data_path = '';
            this.retailAutoDetect();
        },

        retailAutoDetect() {
            this.retail_searching = true;
            this.retail_found = false;

            call(fs2mod.searchRetailData, (path) => {
                this.retail_searching = false;

                if(path !== '') {
                    this.retail_found = true;
                    this.retail_data_path = path;
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

        selectModIni() {
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
            call(fs2mod.copyRetailData, this.retail_data_path, (result) => {
                if(result) this.popup_visible = false;
            });
        },

        launchModAdvanced() {
            let mod_flag = [];
            for(let part of this.popup_mod_flag) {
                if(this.popup_mod_flag_map[part[0]]) mod_flag.push(part[0]);
            }

            fs2mod.runModAdvanced(this.popup_mod_id, this.popup_mod_version, this.popup_mod_sel_exe, mod_flag);
            this.popup_visible = false;
        },

        popupProposeFolder() {
            if(this.popup_pkg_folder === '') {
                this.popup_pkg_folder = this.popup_pkg_name.toLowerCase().replace(/ /g, '_');
            }
        }
    }
};
</script>
<template>
    <div>
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
                <div class="text-marquee"><span>Announcements go here!</span></div>
            </div>
        </div>
    <!-------------------------------------------------------------------------------- Start the Tab Menus ---------->
        <div id="tab-bar" v-if="page !== 'details'">
            <a href="#" class="main-btn" v-for="(label, name) in tabs" :class="{ active: tab === name }" @click.prevent="showTab(name)">
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
        <div class="filter-container" v-if="page === 'modlist'">
            <button class="filterbtn" @click="show_filter = true"></button>
            <div class="filter-content" v-show="show_filter" @click="show_filter = false">
                <div class="filter-lines">
                    <button class="filter-content-btn last-played-btn">Last Played</button>
                </div>
                <div class="filter-lines">
                    <button class="filter-content-btn alphabetical-btn">Alphabetical</button>
                </div>
                <div class="filter-lines">
                    <button class="filter-content-btn last-updated-log-btn">Last Updated</button>
                </div>
                <div class="filter-lines">
                    <button class="filter-content-btn last-released-btn">Last Released</button>
                </div>
            </div>
        </div>

    <!-------------------------------------------------------------------------------- Start the Details Menu ---------->
        <div id="details-tab-bar" v-if="page === 'details'">
            <a href="#" class="main-btn" @click="exitDetails"><i class="fa fa-chevron-left"></i> Back</a>
            <span class="main-btn active"><i class="fa fa-exclamation-circle"></i> Details</span>
        </div>

    <!-------------------------------------------------------------------------------- Build the Main View container ---------->
        <div class="main-container scroll-style">
            <div id="main-background"></div>
            <div class="container-fluid mod-container" v-if="page === 'modlist'">
                <div v-if="tab === 'home'">
                    <kn-mod-home v-for="mod in mods" :key="mod.id" :mod="mod" :tab="tab"></kn-mod-home>
                </div>
                <div v-else>
                    <kn-mod-explore v-for="mod in mods" :key="mod.id" :mod="mod" :tab="tab"></kn-mod-explore>
                </div>
                <div v-if="mods.length === 0" class="main-notice">No mods found.</div>
            </div>
            <div id="main-shadow-effect"></div>

    <!-------------------------------------------------------------------------------- Start the Welcome page ---------->
            <div data-tr class="info-page" v-if="page === 'welcome'">
                <div class="container main-notice">
                    <h1>Welcome!</h1>
                    
                    <p>It looks like you started Knossos for the first time.</p>
                    <p>You need to select a directoy where Knossos will store the game data (models, textures, etc.).</p>
                    
                    <form class="form-horizontal">
                        <div class="form-group">
                            <div class="col-xs-8">
                                <input type="text" class="form-control" v-model="data_path">
                            </div>
                            <div class="col-xs-4">
                                <button class="btn btn-default" @click.prevent="selectFolder">Browse...</button>
                            </div>
                        </div>
                    </form>
                    
                    <p><button class="btn btn-primary" @click="finishWelcome">Continue</button></p>

                    <hr>
                    <p>
                        This launcher is still in development. Please visit
                        <a href="#" @click="openLink('http://www.hard-light.net/forums/index.php?topic=93144.0')">this HLP thread</a>
                        and let me know what you think, what didn't work and what you would like to change.
                    </p>
                    <p>-- ngld</p>
                </div>
            </div>

    <!-------------------------------------------------------------------------------- Start the Details page ---------->
            <div class="info-page" id="details-page" v-if="page === 'details'">
                <kn-details-page :modbundle="mod"></kn-details-page>
            </div>

            <div class="info-page settings-page container-fluid" v-if="page === 'settings'">
                <kn-settings-page></kn-settings-page>
            </div>

            <div class="info-page devel-page" v-if="page === 'develop'">
                <kn-devel-page :mods="mods"></kn-devel-page>
            </div>
        </div>

        <div class="popup-bg" v-if="popup_visible" @click="popup_visible = false"></div>

        <div class="popup" v-if="popup_visible">
            <div class="title clearfix">
                {{ popup_title }}

                <a href="" class="pull-right" @click.prevent="popup_visible = false">
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

                    <p v-if="popup_content.progress_info.length === 0">
                        Preparing...
                    </p>

                    <div v-for="row in popup_content.progress_info" class="row">
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
                        You're trying to install an FS2 mod which requires retail files which you don't have.<br>
                        Please select the folder of your FS2 installation or the FS2 installer from GOG (setup_freespace2_....exe).
                    </p>
                    <p>
                        <strong v-if="retail_searching">Searching files...</strong>
                        <strong v-else-if="retail_found">Folder found!</strong>
                        <strong v-else>
                            Nothing found, please select the appropriate folder or install FS2 and
                            <a href="#" @click.prevent="retailAutoDetect">try again</a>.
                        </strong>
                    </p>
                    <form class="form-horizontal">
                        <div class="form-group">
                            <div class="col-xs-8">
                                <input type="text" class="form-control" v-model="retail_data_path" :disabled="retail_searching">
                            </div>
                            <div class="col-xs-4">
                                <button class="btn btn-default" @click.prevent="selectRetailFolder">Browse...</button>
                                <button class="btn btn-default" @click.prevent="selectRetailFile">Select .exe</button>
                            </div>
                        </div>
                    </form>
                    
                    <p><button class="btn btn-primary" @click="finishRetailPrompt">Continue</button></p>
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
                                    <option value="tool" v-if="popup_mode === 'create_mod'">Tool</option>
                                    <option value="ext">Extension</option>
                                </select>

                                <span class="help-block" v-if="popup_mod_type === 'mod'">
                                    This type is the default and covers most cases. Normally you'll want to use this type.
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'tc'">
                                    Use this type if your mod doesn't depend on other mods or retail files.<br>
                                    (Mods for TCs should still use the "Mod" type.)
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'engine'">
                                    This should only be used for builds FSO builds (fs2_open*.exe, fs2_open*.AppImage, etc.).
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'tool'">
                                    This is used for all executables which aren't FSO like FRED or PCS2.
                                </span>

                                <span class="help-block" v-if="popup_mod_type === 'ext'">
                                    This mod type is meant for overrides like custom HUD tables.
                                </span>
                            </div>
                        </div>

                        <div class="form-group" v-if="popup_mod_type === 'mod' || popup_mod_type === 'ext'">
                            <label class="col-xs-3 control-label">Parent mod</label>
                            <div class="col-xs-9">
                                <select class="form-control" v-model="popup_mod_parent">
                                    <option v-for="mod in popup_mod_tcs" :value="mod.id" :key="mod.id">{{ mod.title }}</option>
                                </select>

                                <span class="help-block">
                                    Please select your parent TC here. If this doesn't apply to a TC, select FS2.
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
                                    Create a new, empty folder
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
            </div>
        </div>
    </div>
</template>