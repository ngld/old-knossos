<script>
export default {
    props: [],

    data: () => ({
        knossos: {},
        fso: {},
        old_settings: {},
        default_fs2_bin: null,
        default_fred_bin: null,
        caps: null,

        neb_user: '',
        neb_password: '',
        neb_email: ''
    }),

    beforeMount() {
        connectOnce(fs2mod.settingsArrived, (settings) => {
            settings = JSON.parse(settings);

            this.knossos = Object.assign({}, settings.knossos);
            this.fso = Object.assign({}, settings.fso);
            this.old_settings = settings;
            this.default_fs2_bin = settings.knossos.fs2_bin;
            this.default_fred_bin = settings.knossos.fred_bin;

            this.neb_user = this.knossos.neb_user;
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
        },

        login() {
            fs2mod.nebLogin(this.neb_user, this.neb_password);
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
};
</script>
<template>
    <div class="row form-horizontal settings-container">
        <div class="col-sm-6">
            <h2>
                Settings
                <small><button class="mod-btn btn-green pull-right" @click="save">Save</button></small>
            </h2>
            <div class="settings-exp">Click the arrows to reveal each group's options. Click SAVE when done.</div>

            <kn-drawer label="Knossos">
                <div class="settings-exp drawer-exp">Basic Knossos settings for downloads, errors, and data</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Data Path:</label>
                    <div class="col-sm-8">
                        <small>{{ knossos.base_path }}</small>
                        <button @click.prevent="changeBasePath">Browse</button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Max Downloads:</label>
                    <div class="col-sm-8">
                        <input type="number" style="width: 50px" v-model="knossos.max_downloads">
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Send Error Reports:</label>
                    <div class="col-sm-8">
                        <input type="checkbox" v-model="knossos.use_raven">
                    </div>
                </div>
            </kn-drawer>

            <!--We're not using this anymore!
            <kn-drawer label="Exec">
                <div class="settings-exp drawer-exp">Manage the default executable Knossos will choose</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">FSO Exec:</label>
                    <div class="col-sm-8">
                        <select v-model="default_fs2_bin">
                            <option v-for="(bin, title) in fso.fs2_bins" :value="bin">{{ title }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">FRED Exec:</label>
                    <div class="col-sm-8">
                        <select v-model="default_fred_bin">
                            <option v-for="(bin, title) in fso.fred_bins" :value="bin">{{ title }}</option>
                        </select>
                    </div>
                </div>
            </kn-drawer>
            -->

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
            </kn-drawer>
        </div>
        <div class="col-sm-6">
            <kn-drawer label="Nebula">
                <div class="settings-exp drawer-exp">Login and manage your Nebula credentials</div>
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
                    <div class="col-sm-offset-4 col-sm-4 neb-btns">
                        <button class="mod-btn btn-link-blue" @click="login">Login</button>
                        <button class="mod-btn btn-link-blue" @click="register">Register</button>
                        <button class="mod-btn btn-link-red" @click="resetPassword">Reset Pass</button>
                    </div>
                </div>
            </kn-drawer> 

            <kn-drawer label="Speech" v-if="fso.has_voice">
                <div class="settings-exp drawer-exp">Manage settings related to Text-To-Speech</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Voice:</label>
                    <div class="col-sm-8">
                        <select disabled></select>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Volume:</label>
                    <div class="col-sm-8">
                        <input type="range" min="0" max="100" style="width: calc(100% - 80px); display: inline-block;" disabled>
                        <button disabled>Test</button>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Use Speech In:</label>
                    <div class="col-sm-4">
                        Tech Room:
                        <input type="checkbox" disabled>
                    </div>
                    <div class="col-sm-4">
                        In-Game:
                        <input type="checkbox" disabled>
                    </div>
                </div>
                <div class="form-group">
                    <div class="col-sm-4 col-sm-offset-4">
                        Briefings:
                        <input type="checkbox" disabled>
                    </div>
                    <div class="col-sm-4">
                        Multiplayer:
                        <input type="checkbox" disabled>
                    </div>
                </div>
            </kn-drawer>

            <kn-drawer label="Joystick">
                <div class="settings-exp drawer-exp">Setup and calibrate your joystick</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Joystick:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.joystick_id">
                            <option>No Joystick</option>
                            <option v-for="(joy, i) in fso.joysticks" :value="i">{{ joy }}</option>
                        </select>
                    </div>
                </div>

                <div class="form-group">
                    <div class="col-sm-8 col-sm-offset-5">
                        <button disabled>Detect</button>
                        <button disabled>Calibrate</button>
                    </div>
                </div>

                <div class="form-group">
                    <div class="col-sm-4 col-sm-offset-4">
                        Force Feedback:
                        <input type="checkbox" disabled>
                    </div>
                    <div class="col-sm-4">
                        Directional Hit:
                        <input type="checkbox" disabled>
                    </div>
                </div>
            </kn-drawer>

            

            <kn-drawer label="Network">
                <div class="settings-exp drawer-exp">Manage your network settings for multiplayer</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Connection Type:</label>
                    <div class="col-sm-3">
                        <select>
                            <option>None</option>
                            <option>Dialup</option>
                            <option>Broadband/LAN</option>
                        </select>
                    </div>
                    <label class="col-sm-2 control-label">Force Local Port:</label>
                    <div class="col-sm-2">
                        <input type="number" disabled>
                    </div>
                </div>

                <div class="form-group">
                    <label class="col-sm-4 control-label">Connection Speed:</label>
                    <div class="col-sm-3">
                        <select disabled>
                            <option>None</option>
                            <option>28k modem</option>
                            <option>56k modem</option>
                            <option>ISDN</option>
                            <option>DSL</option>
                            <option>Cable/LAN</option>
                        </select>
                    </div>
                    <label class="col-sm-3 control-label">Force IP Address:</label>
                    <div class="col-sm-2">
                        <input type="text" disabled>
                    </div>
                </div>
            </kn-drawer>
            

            <!--
            <kn-drawer label="Flag Defaults">
                <div class="settings-exp drawer-exp">Create the default flag set that Knossos will use if a mod or TC does not provide one</div>
                <kn-flag-editor :caps="caps" :cmdline="''" ref="flagEditor"></kn-flag-editor>
            </kn-drawer>
            -->
        </div>
    </div>
</template>