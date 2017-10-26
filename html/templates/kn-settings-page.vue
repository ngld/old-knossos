<script>
/**
 * Current state:
 *  - Global flags are missing (see thread and chief's idea regarding this)
 *  - Network isn't implemented (read / write)
 *  - Joystick isn't finished (read / write) and the buttons aren't working
 */

export default {
    props: [],

    data: () => ({
        knossos: {},
        fso: {},
        old_settings: {},
        ff_enabled: false,

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

            this.neb_user = this.knossos.neb_user;
            this.ff_enabled = settings.fso.joystick_ff_strength == 100;
        });
        fs2mod.getSettings();
    },

    methods: {
        changeBasePath() {
            call(fs2mod.browseFolder, 'Please select a folder', this.knossos.base_path || '', (path) => {
                if(path) this.knossos.base_path = path;
            });
        },

        save() {
            this.fso.joystick_ff_strength = this.ff_enabled ? 100 : 0;

            for(let set of ['base_path', 'max_downloads', 'use_raven', 'engine_stability']) {
                if(this.knossos[set] != this.old_settings.knossos[set]) {
                    fs2mod.saveSetting(set, JSON.stringify(this.knossos[set]));
                }
            }

            let fso = Object.assign({}, this.fso);
            for(let key of Object.keys(this.old_settings.fso)) {
                if(fso[key] === undefined) fso[key] = this.old_settings.fso[key];
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
        },

        testVoice() {
            fs2mod.testVoice(parseInt(this.fso.speech_voice), parseInt(this.fso.speech_vol), 'Test');
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
                        <input type="number" style="width: 50px" v-model.number="knossos.max_downloads">
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

            <kn-drawer label="Joystick">
                <div class="settings-exp drawer-exp">Setup and calibrate your joystick</div>
                <div class="form-group">
                    <label class="col-sm-4 control-label">Joystick:</label>
                    <div class="col-sm-8">
                        <select v-model="fso.joystick_id">
                            <option>No Joystick</option>
                            <option v-for="(joy, id) in fso.joysticks" :value="id" :key="id">{{ joy }}</option>
                        </select>
                    </div>
                </div>

                <!--
                <div class="form-group">
                    <div class="col-sm-8 col-sm-offset-5">
                        <button disabled>Detect</button>
                        <button disabled>Calibrate</button>
                    </div>
                </div>
                -->

                <div class="form-group">
                    <div class="col-sm-4 col-sm-offset-4">
                        Force Feedback:
                        <!-- TODO: This should be a slider -->
                        <input type="checkbox" v-model="ff_enabled">
                    </div>
                    <div class="col-sm-4">
                        Directional Hit:
                        <input type="checkbox" v-model="fso.joystick_enable_hit">
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
        </div>
    </div>
</template>