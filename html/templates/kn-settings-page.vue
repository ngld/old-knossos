<script>
/**
 * Current state:
 *  - Global flags are missing (see thread and chief's idea regarding this)
 *  - Network isn't implemented (read / write)
 *  - Joystick isn't finished (read / write) and the buttons aren't working
 */

export default {
    props: ['mods'],

    data: () => ({
        loading: false,

        retail_installed: true,
        knossos: {},
        fso: {},
        old_settings: {},
        joylist: [],
        joylist_loading: false,

        neb_logged_in: false,
        neb_user: '',
        neb_password: '',
        neb_email: ''
    }),

    beforeMount() {
        this.loading = true;

        call_async(fs2mod.getSettings, (settings) => {
            this.retail_installed = settings.has_retail;

            this.knossos = Object.assign({}, settings.knossos);
            this.fso = Object.assign({}, settings.fso);
            this.old_settings = settings;

            this.neb_user = this.knossos.neb_user;
            this.neb_logged_in = this.neb_user !== '';

            this.loading = false;
        });

        this.joylist_loading = true;
        call_async(fs2mod.getJoysticks, (joysticks) => {
            this.joylist = joysticks;
            this.joylist_loading = false;
        });
    },

    methods: {
        changeBasePath() {
            call(fs2mod.browseFolder, 'Select a folder for the Knossos library', this.knossos.base_path || '', (path) => {
                if(path) this.knossos.base_path = path;
            });
        },

        save() {
            // SDL device index could always change, so don't depend on it. We do
            // use it as a fallback however and need to keep track of it to an extent.
            // So try to find guid in currently connected joysticks and set the device
            // index to match.
            for (let j = 0; j < this.fso.joysticks.length; ++j) {
                if (this.fso.joysticks[j].guid) {
                    const joy = this.joylist.find(item => item[0] === this.fso.joysticks[j].guid);

                    // update index if found, otherwise we just keep the existing value
                    if (!joy) continue;

                    const [guid, id, name] = joy;

                    // skip if item is a previously configured entry
                    if (!Number.isInteger(id) || id == -1) continue;

                    this.fso.joysticks[j].id = id;

                    // also save this to knossos config so that we can still see what
                    // joystick is configured even when not currently connected
                    this.knossos.joysticks[`joy${j}`].name = name;
                    this.knossos.joysticks[`joy${j}`].guid = guid;
                } else {
                    // 'No Joystick'
                    this.fso.joysticks[j].id = '';

                    this.knossos.joysticks[`joy${j}`].name = '';
                    this.knossos.joysticks[`joy${j}`].guid = '';
                }
            }

            if(this.knossos.base_path !== this.old_settings.knossos.base_path) {
                fs2mod.setBasePath(this.knossos.base_path);
            }

            for(let set of [
                'max_downloads', 'use_raven', 'engine_stability', 'download_bandwidth', 'update_notify',
                'custom_bar', 'show_fs2_mods_without_retail', 'debug_log',  'show_fso_builds', 'fetch_interval'
            ]) {
                if(this.knossos[set] != this.old_settings.knossos[set]) {
                    fs2mod.saveSetting(set, JSON.stringify(this.knossos[set]));
                }
            }

            // always save this (easier than checking for changes)
            fs2mod.saveSetting('joysticks', JSON.stringify(this.knossos['joysticks']))

            let fso = Object.assign({}, this.fso);
            for(let key of Object.keys(this.old_settings.fso)) {
                if(fso[key] === undefined) fso[key] = this.old_settings.fso[key];
            }

            fs2mod.saveFsoSettings(JSON.stringify(fso));
            this.old_settings.knossos = Object.assign({}, this.knossos);
        },

        login() {
            call(fs2mod.nebLogin, this.neb_user, this.neb_password, (result) => {
                if(result) {
                    this.neb_logged_in = true;
                }
            });
        },

        logout() {
            call(fs2mod.nebLogout, (result) => {
                if(result) {
                    this.neb_user = '';
                    this.neb_logged_in = false;
                }
            });
        },

        register() {
            if(this.neb_user == '' || this.neb_password == '' || this.neb_email == '') {
                alert('You have to enter your desired username, password and email address!');
            } else {
                fs2mod.nebRegister(this.neb_user, this.neb_password, this.neb_email);
            }
        },

        resetPassword() {
            fs2mod.nebResetPassword(this.neb_user);
        },

        testVoice() {
            fs2mod.testVoice(parseInt(this.fso.speech_voice), parseInt(this.fso.speech_vol), 'Test');
        },

        showRetailPrompt() {
            vm.showRetailPrompt(false);
        },

        openKnossosLog() {
            fs2mod.openKnossosLog();
        },

        uploadKnossosLog() {
            call(fs2mod.uploadKnossosLog, (result) => {
                if(result !== '') {
                    vm.popup_visible = true;
                    vm.popup_title = 'Uploaded Knossos Log';
                    vm.popup_mode = 'debug_log';
                    vm.popup_content = result;
                }
            });
        },

        isJoySelected(exclude_id, guid) {
            let selected = false;

            for (let j = 0; j < this.fso.joysticks.length; ++j) {
                if (j == exclude_id) continue;

                if (guid == this.fso.joysticks[j].guid) {
                    selected = true;
                    break;
                }
            }

            return selected
        }
    }
};
</script>
<template>
    <div class="row form-horizontal settings-container">
        <div class="col-sm-6">
            <h2>
                Settings
                <button class="mod-btn btn-blue pull-right" @click="showRetailPrompt" v-if="!retail_installed">Install FS2</button>
                <button class="mod-btn btn-green pull-right" @click="save" v-if="!loading">Save</button>
                <button class="mod-btn btn-grey pull-right" disabled v-if="loading">Loading...</button>
            </h2>
            <div class="settings-exp">Click the arrows to reveal each group's options. Click SAVE when done.</div>

            <kn-drawer label="Knossos">
                <div class="settings-exp drawer-exp">Settings for basic Knossos options, errors, and data</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Library Path:</label>
                    <div class="col-sm-8">
                        <small>{{ knossos.base_path }}</small>
                        <button class="mod-btn btn-link-grey pull-right" @click.prevent="changeBasePath">Browse</button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Update Notifications:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.update_notify">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Update Interval:</label>
                    <div class="col-sm-8">
                        <select v-model="knossos.fetch_interval">
                            <option value="hourly">Hourly</option>
                            <option value="daily">Daily</option>
                            <option value="manual">Manual</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Send Error Reports:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.use_raven">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Preferred Engine Stability:</label>
                    <div class="col-sm-8">
                        <select v-model="knossos.engine_stability">
                            <option value="stable">Stable</option>
                            <option value="rc">RCs</option>
                            <option value="nightly">Nightlies</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Custom Title Bar:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.custom_bar">
                    </div>
                </div>

                <div class="form-group" v-if="!retail_installed">
                    <label class="col-sm-4 control-label">Show FreeSpace 2 Mods:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.show_fs2_mods_without_retail">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Extended Knossos Log:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.debug_log">

                        <button class="mod-btn btn-link-grey" @click="openKnossosLog">Open</button>
                        <button class="mod-btn btn-link-grey" @click="uploadKnossosLog">Upload</button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Show Engine Builds In Mod List:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.show_fso_builds">
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Downloads">
                <div class="settings-exp drawer-exp">Configuration of how Knossos handles downloads</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Max Downloads:</label>
                    <div class="col-sm-8">
                        <input type="number" style="width: 50px" v-model.number="knossos.max_downloads">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Download bandwidth limit:</label>
                    <div class="col-sm-8">
                        <select v-model="knossos.download_bandwidth">
                            <option :value="-1 ">No limit</option>
                            <option :value="128 * 1024">128 KB/s</option>
                            <option :value="512 * 1024">512 KB/s</option>
                            <option :value="1 * 1024 * 1024">1 MB/s</option>
                            <option :value="2 * 1024 * 1024">2 MB/s</option>
                            <option :value="3 * 1024 * 1024">3 MB/s</option>
                            <option :value="5 * 1024 * 1024">5 MB/s</option>
                            <option :value="10 * 1024 * 1024">10 MB/s</option>
                            <option :value="20 * 1024 * 1024">20 MB/s</option>
                            <option :value="50 * 1024 * 1024">50 MB/s</option>
                        </select>
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Video">
                <div class="settings-exp drawer-exp">Set your default video settings and resolution</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Resolution:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.active_mode">
                            <option v-for="res in fso.modes">{{ res }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Bit Depth:</label>
                    <div class="col-sm-2">
                        <select v-model="fso.depth">
                            <option value="16">16-bit</option>
                            <option value="32">32-bit</option>
                        </select>
                    </div>
                    <label class="col-sm-3 control-label">Texture Filter:</label>
                    <div class="col-sm-2">
                        <select v-model="fso.texfilter">
                            <option value="0">Bilinear</option>
                            <option value="1">Trilinear</option>
                        </select>
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Audio">
                <div class="settings-exp drawer-exp">Set your default playback and capture devices</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Playback Device:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.active_audio_dev">
                            <option v-for="dev in fso.audio_devs">{{ dev }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Capture Device:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.active_cap_dev">
                            <option v-for="dev in fso.cap_devs">{{ dev }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Enable EFX:</label>
                    <div class="col-sm-1"><input type="checkbox" v-model="fso.enable_efx"></div>

                    <label class="col-sm-3 control-label">Sample Rate:</label>
                    <div class="col-sm-4">
                        <input type="number" v-model="fso.sample_rate">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Language:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.language">
                            <option>English</option>
                            <option>German</option>
                            <option>French</option>
                            <option>Polish</option>
                        </select>
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Network">
                <div class="settings-exp drawer-exp">Manage your network settings for multiplayer</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Connection Type:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.net_type">
                            <option value="0">None</option>
                            <option value="1">Dialup</option>
                            <option value="2">Broadband/LAN</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Force Local Port:</label>
                    <div class="col-sm-8">
                        <input type="number" min="0" max="65535" maxlength="5" v-model="fso.net_port">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Connection Speed:</label>
                    <div class="col-sm-4">
                        <select v-model="fso.net_speed">
                            <option value="0">None</option>
                            <option value="1">28k modem</option>
                            <option value="2">56k modem</option>
                            <option value="3">ISDN</option>
                            <option value="4">DSL</option>
                            <option value="5">Cable/Fiber/LAN</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Force IP Address:</label>
                    <div class="col-sm-8">
                        <input type="text" v-model="fso.net_ip">
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Speech" v-if="fso.has_voice">
                <div class="settings-exp drawer-exp">Manage settings related to Text-To-Speech</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Voice:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.speech_voice">
                            <option v-for="voice, id in fso.voice_list" :value="id" :key="id">{{ voice }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Volume:</label>
                    <div class="col-sm-8">
                        <input type="range" min="0" max="100" style="width: calc(100% - 80px); display: inline-block;" v-model="fso.speech_vol">
                        <button @click.prevent="testVoice">Test</button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Use Speech In:</label>
                    <div class="col-sm-4">
                        Tech Room:
                        <input type="checkbox" v-model="fso.speech_techroom">
                    </div>
                    <div class="col-sm-4">
                        In-Game:
                        <input type="checkbox" v-model="fso.speech_ingame">
                    </div>
                </div>
                <div class="form-group">
                    <div class="col-sm-4 col-sm-offset-4">
                        Briefings:
                        <input type="checkbox" v-model="fso.speech_briefings">
                    </div>
                    <div class="col-sm-4">
                        Multiplayer:
                        <input type="checkbox" v-model="fso.speech_multi">
                    </div>
                </div>
            </kn-drawer>
        </div>
        <div class="col-sm-6">
            <kn-drawer label="Joystick">
                <div class="settings-exp drawer-exp">Setup and calibrate your joystick</div>
                <template v-for="(joystick, idx) in fso.joysticks">
                    <div class="form-group">
                        <label class="col-sm-4 control-label">Joy-{{ idx }}:</label>
                        <div class="col-sm-8">
                            <div v-if="joylist_loading">Loading...</div>
                            <select v-else v-model="fso.joysticks[idx].guid">
                                <option value="">None / Autodetect</option>
                                <option v-for="joy in joylist" :value="joy[0]" :key="joy[0]" v-bind:disabled="isJoySelected(idx, joy[0])">{{ joy[2] }}</option>
                            </select>
                        </div>
                    </div>
                    <!--
                        haptic/force feedback is currently only supported on the first joystick
                        so let's only show the options for it on the first entry
                    -->
                    <template v-if="(idx == 0)">
                        <div class="form-group">
                            <div class="col-sm-4 col-sm-offset-4">
                                Force Feedback:
                                <input type="checkbox" v-model="fso.joystick_ff">
                            </div>
                            <div class="col-sm-4">
                                Directional Hit:
                                <input type="checkbox" v-model="fso.joystick_enable_hit">
                            </div>
                            <div class="col-sm-8 col-sm-offset-4">
                                Strength:
                                <input type="range" min="0" max="100" style="display: inline-block; width: 70%; vertical-align: middle;" v-model="fso.joystick_ff_strength">
                            </div>
                        </div>
                    </template>
                </template>
            </kn-drawer>

            <kn-drawer label="Nebula">
                <div class="settings-exp drawer-exp">Login and manage your Nebula credentials</div>

                <template v-if="!neb_logged_in">
                    <div class="form-group">
                        <label class="col-sm-4 control-label">Username:</label>
                        <div class="col-sm-8">
                            <input type="text" class="neb-input" v-model="neb_user">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="col-sm-4 control-label">Password:</label>
                        <div class="col-sm-8">
                            <input type="password" class="neb-input" v-model="neb_password">
                        </div>
                    </div>

                    <div class="form-group">
                        <label class="col-sm-4 control-label">E-Mail:</label>
                        <div class="col-sm-8">
                            <input type="email" class="neb-input" v-model="neb_email" placeholder="only required for registration">
                        </div>
                    </div>

                    <div class="form-group">
                        <div class="col-sm-offset-4 col-sm-8 neb-btns">
                            <button class="mod-btn btn-link-blue" @click="login">Login</button>
                            <button class="mod-btn btn-link-blue" @click="register">Register</button>
                            <button class="mod-btn btn-link-red" @click="resetPassword">Reset Pass</button>
                        </div>
                    </div>
                </template>
                <template v-else>
                    <div class="form-group">
                        <div class="col-sm-offset-4 col-sm-8">
                            <p>
                                Logged in as <strong>{{ neb_user }}</strong>
                            </p>

                            <button class="mod-btn btn-link-red" @click="logout">Logout</button>
                        </div>
                    </div>
                </template>
            </kn-drawer>

            <kn-drawer label="Global Flags">
                <div class="settings-exp drawer-exp">Set the FSO settings defaults for all mods</div>
                <p>
                    Here you can set the defaults for all mods. <em>On</em> means that this flag will be on for all mods using the selected engine version.
                    <em>Default</em> tells Knossos to use the setting the modder chose and <em>Off</em> tells it to always turn that flag off.
                </p>
                <p>
                    You can always override these settings for each mod by going to your Home tab, hovering over a mod tile, clicking on the little arrow and
                    clicking on "FSO Settings".
                </p>

                <div class="form-group">
                    <kn-global-flags :mods="mods"></kn-global-flags>
                </div>
            </kn-drawer>
        </div>
    </div>
</template>