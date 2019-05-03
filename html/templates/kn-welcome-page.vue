<script>
export default {
    data: () => ({
        step: 1,
        data_path: '',

        retail_searching: false,
        retail_found: false,
        retail_path: '',
        retail_installed: false,

        installer_path: '',

        wl_popup_visible: false,

        neb_user: '',
        neb_password: '',
        neb_email: ''
    }),

    created() {
        this.retail_searching = true;
        this.retail_found = false;

        call(fs2mod.searchRetailData, (path) => {
            this.retail_searching = false;

            if(path !== '') {
                this.retail_found = true;
                this.retail_path = path;
            }
        });

        call(fs2mod.getDefaultBasePath, (result) => {
            this.data_path = result;
        });
    },

    methods: {
        selectDataFolder() {
            call(fs2mod.browseFolder, 'Select a folder for the Knossos library', this.data_path, (path) => {
                if(path) this.data_path = path;
            });
        },

        finishFirst() {
            call(fs2mod.setBasePath, this.data_path, (result) => {
                if(result) {
                    call(fs2mod.checkIfRetailInstalled, (result) => {
                        if(result) {
                            this.retail_installed = true;
                        }
                    });
                    this.step++;
                }
            });
        },

        selectInstaller() {
            call(fs2mod.browseFiles, 'Select your setup_freespace2_...exe', this.installer_path, '*.exe', (files) => {
                if(files.length > 0) {
                    this.installer_path = files[0];
                }
            });
        },

        selectRetailFolder() {
            call(fs2mod.browseFiles, 'Select your FreeSpace 2 folder\'s Root_fs2.vp', '', '*.vp', (vp_files) => {
                if(vp_files.length > 0) {
                    let root_vp_path = vp_files[0];

                    call(fs2mod.verifyRootVPFolder, root_vp_path, (result) => {
                        if(result) {
                            this.retail_path = result;
                        }
                    });
                }
            });
        },

        processRetail(has_retail_folder) {
            let path = has_retail_folder ? this.retail_path : this.installer_path;
            call(fs2mod.copyRetailData, path, (result) => {
                if(result) {
                    vm.popup_visible = true;
                    vm.popup_title = 'Installing FreeSpace 2';
                    vm.popup_mode = 'mod_progress';
                    vm.popup_mod_id = 'FS2';
                    vm.popup_progress_cancel = null;

                    connectOnce(fs2mod.retailInstalled, () => {
                        vm.popup_visible = false;
                        this.retail_installed = true;
                        this.step++;
                    });
                }
            });
        },

        skipRetail() {
            this.wl_popup_visible = false;
            this.step++;
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

        goToExplore() {
            vm.showTab('explore');
        },

        goToMVPS() {
            // Make sure the user ends up on the explore tab if they press Back on the details page.
            vm.tab = 'explore';
            fs2mod.showMod('MVPS');
        }
    }
};
</script>
<template>
    <div class="container main-notice" id="welcome-page">
        <div v-if="step === 1">
            <h1>Welcome!</h1>

            <p>Select a folder for the Knossos library, where Knossos will store the game data (models, textures, etc.).</p>

            <form class="form-horizontal">
                <div class="input-group">
                    <input type="text" class="form-control" v-model="data_path">
                    <span class="input-group-btn">
                        <button class="btn btn-default" @click.prevent="selectDataFolder">Browse...</button>
                    </span>
                </div>
                <br>
            </form>

            <p>
                <button v-if="retail_searching" class="btn btn-primary" disabled>Please wait...</button>
                <button v-else class="btn btn-primary" @click.prevent="finishFirst">Continue</button>
            </p>
        </div>

        <div v-else-if="step === 2">
            <form class="form-horizontal">
                <div v-if="retail_installed">
                    <h1>FreeSpace 2 already installed</h1>
                    <p>The Knossos library already has FreeSpace 2 installed.</p>
                    <p>You will be able to play the original (retail) FreeSpace 2 and FreeSpace 2 mods (fan-made campaigns).</p>
                    <p>
                        <button class="btn btn-primary" @click.prevent="step++">Continue</button>
                    </p>
                </div>
                <div v-else-if="retail_found">
                    <h1>FreeSpace 2 installation found</h1>
                    <p>We found a FreeSpace 2 installation in the location below. Is this correct?</p>
                    <p>If you click "Yes", Knossos will copy the FreeSpace 2 files into the Knossos library.</p>

                    <p><strong>{{ retail_path }}</strong></p>

                    <p>
                        <button class="btn btn-primary" @click.prevent="processRetail(true)">Yes</button>
                        <button class="btn btn-default pull-right" @click.prevent="retail_found = false; retail_path = ''">No</button>
                    </p>
                </div>
                <div v-else>
                    <h1>Install FreeSpace 2 (optional)</h1>
                    <p>
                        If you want to play FreeSpace 2 mods (fan-made campaigns), you'll need a copy of FreeSpace 2.
                        You can buy it for cheap from
                        <a href="https://www.gog.com/game/freespace_2" class="open-ext">GOG</a>
                        or <a href="https://store.steampowered.com/app/273620/Freespace_2/" class="open-ext">Steam</a>.
                    </p>
                    <p>
                        Click "Skip" if you want to play only "total conversion" games, which don't use FreeSpace 2.
                    </p>

                    <h2>Use an existing FreeSpace 2 installation</h2>
                    <p>
                        Browse to the folder that has the FreeSpace 2 data files and find the file <strong>Root_fs2.vp</strong> or <strong>root_fs2.vp</strong>.<br>
                        Knossos will copy the files into the Knossos library.
                    </p>

                    <div class="input-group">
                        <input type="text" class="form-control" v-model="retail_path">
                        <span class="input-group-btn">
                            <button class="btn btn-default" @click.prevent="selectRetailFolder">Browse...</button>
                            <button class="btn btn-primary" @click.prevent="processRetail(true)">Continue</button>
                        </span>
                    </div>

                    <h2>Use the GOG FreeSpace 2 installer</h2>

                    <p>
                        Download the GOG FreeSpace 2 installer (example: setup_freespace2_2.0.0.8.exe) and select it.<br>
                        Knossos will extract the data files from the installer into the Knossos library.
                    </p>
                    <p>
                        If you select FreeSpace 2 in your game library, download the installer beneath the
                        "Download offline backup game installers" heading. Do <strong>not</strong> click the big blue
                        "Download and install now" button. That's the GOG Galaxy installer which we can't use.
                    </p>
                    <div class="input-group">
                        <input type="text" class="form-control" v-model="installer_path">
                        <span class="input-group-btn">
                            <button class="btn btn-default" @click.prevent="selectInstaller">Browse...</button>
                            <button class="btn btn-primary" @click.prevent="processRetail(false)">Continue</button>
                        </span>
                    </div>
                    <br>

                    <p>
                        <button class="btn btn-default" @click.prevent="wl_popup_visible = true">Skip</button>
                    </p>
                </div>
            </form>
        </div>

        <div v-else-if="step === 3">
            <h1>Suit up, pilot!</h1>

            <p>
                Now you can play <span v-if="retail_installed">FreeSpace 2 mods and</span>
                non-FreeSpace "total conversion" games for FreeSpace Open! You can find games on the <a href="#" @click.prevent="goToExplore">Explore</a> tab.
            </p>

            <p v-if="retail_installed">
                If you want to play the original (retail) FreeSpace 2, we <strong>highly</strong> recommend you use the
                <a href="#" @click.prevent="goToMVPS">MediaVPs mod</a>, which greatly improves the graphics.
            </p>

            <p><button class="btn btn-primary" @click.prevent="goToExplore">Finish</button></p>

            <hr>

            <div class="welcome-login">
                <div class="login-instructions">
                    <p>Are you a mod developer?</p>
                    <p>Log into the <a href="https://fsnebula.org/" class="open-ext">Nebula</a> mod repository!</p>
                    <p>You can also log in from the settings.</p>
                </div>
                <div class="login-form">
                    <div class="form-group">
                        <label class="col-sm-4 welcome-label">Username:</label>
                        <div class="col-sm-8">
                            <input type="text" class="neb-input" v-model="neb_user">
                        </div>
                    </div>

                    <br>

                    <div class="form-group">
                        <label class="col-sm-4 welcome-label">Password:</label>
                        <div class="col-sm-8">
                            <input type="password" class="neb-input" v-model="neb_password">
                        </div>
                    </div>

                    <br>

                    <div class="form-group">
                        <label class="col-sm-4 welcome-label">E-Mail:</label>
                        <div class="col-sm-8">
                            <input type="email" class="neb-input" v-model="neb_email" placeholder="only required for registration">
                        </div>
                    </div>

                    <br>

                    <div class="form-group">
                        <div class="col-sm-offset-2 col-sm-8 neb-btns">
                            <button class="mod-btn btn-link-blue" @click="login">Login</button>
                            <button class="mod-btn btn-link-blue" @click="register">Register</button>
                            <button class="mod-btn btn-link-red" @click="resetPassword">Reset Pass</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-else>
            <h1>Whoops!</h1>

            <p>If you see this page, please tell us how you managed to get here!</p>
        </div>

        <hr>
        <div id="welcome-footer">
            <h2>Need help or have feedback?</h2>
            <p>
                Join the <a href="https://discord.gg/qfReB8t" class="open-ext">#knossos</a> channel on Discord or post
                on the <a href="https://www.hard-light.net/forums/index.php?topic=94068.0" class="open-ext">Knossos release thread</a> and tell us
            </p>
            <ul>
                <li>What do you like about Knossos?</li>
                <li>What problems did you run into?</li>
                <li>What changes do you want to see?</li>
            </ul>
            <p>-- ngld</p>
        </div>
        <div class="popup-bg" v-if="wl_popup_visible" @click.prevent="wl_popup_visible = false"></div>

        <div class="popup" v-if="wl_popup_visible">
            <div class="title clearfix">
                Skip FreeSpace 2 installation?

                <a href="" class="pull-right" @click.prevent="wl_popup_visible = false">
                    <i class="fa fa-times"></i>
                </a>
            </div>
            <div class="content gen-scroll-style">
                <p>
                    Without FreeSpace 2, you won't be able to play most games that Knossos offers.
                    However, you <strong>can</strong> still play "total conversion" (TC) games, which don't use the FreeSpace 2 data files.
                </p>
                <p>You can install FreeSpace 2 at any time from the settings.</p>

                <div class="popup-buttons">
                    <button class="btn btn-default" @click.prevent="skipRetail">Skip</button>
                    <button class="btn btn-default pull-right" @click.prevent="wl_popup_visible = false">Cancel</button>
                </div>
            </div>
        </div>
    </div>
</template>