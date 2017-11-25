<script>
const default_paths = {
    win32: 'C:\\Games\\FreespaceOpen',
    linux: '~/games/FreespaceOpen',
    macos: '~/Documents/Games/FreespaceOpen'
};

export default {
    data: () => ({
        step: 1,
        data_path: (default_paths[platform] || ''),

        retail_searching: false,
        retail_found: false,
        retail_path: '',

        installer_path: '',

        wl_popup_visible: false
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
    },

    methods: {
        selectDataFolder() {
            call(fs2mod.browseFolder, 'Please select a folder', this.data_path, (path) => {
                if(path) this.data_path = path;
            });
        },

        finishFirst() {
            call(fs2mod.setBasePath, this.data_path, (result) => {
                if(result) {
                    this.step++;
                }
            });
        },

        selectInstaller() {
            call(fs2mod.browseFiles, 'Please select your setup_freespace2_...exe', this.installer_path, '*.exe', (files) => {
                if(files.length > 0) {
                    this.installer_path = files[0];
                }
            });
        },

        selectRetailFolder() {
            call(fs2mod.browseFolder, 'Please select your FS2 folder', this.retail_path, (path) => {
                if(path) this.retail_path = path;
            });
        },

        processRetail() {
            alert('Not yet implemented!');
        },

        skipRetail() {
            this.wl_popup_visible = false;
            this.step++;
        },

        goToExplore() {
            vm.showTab('explore');
        },

        goToMVPS() {
            vm.page = 'details';
            vm.mod = mod_table.MVPS;
        }
    }
};
</script>
<template>
    <div class="container main-notice">
        <div v-if="step === 1">
            <h1>Welcome!</h1>
            
            <p>It looks like you started Knossos for the first time.</p>
            <p>You need to select a directoy where Knossos will store the game data (models, textures, etc.).</p>
            
            <p>We recommend...</p>
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
            <h1>Great!</h1>

            <form class="form-horizontal">
                <p>Just a few more steps...</p>
                <p>
                    If you want to play Freespace 2 Mods (Games that are built on and modify Retail Freespace 2 data), you'll need
                    to get Retail Freespace 2 installed. First, you'll need to own a copy. You can buy it here at
                    <a href="https://www.gog.com/game/freespace_2" class="open-ext">gog.com</a> for just a few dollars.
                </p>

                <p>Once you have purchased Freespace 2, just point us to the GOG Installer EXE.</p>
            
                <div class="input-group">
                    <input type="text" class="form-control" v-model="installer_path">
                    <span class="input-group-btn">
                        <button class="btn btn-default" @click.prevent="selectInstaller">Browse...</button>
                    </span>
                </div>
                <br>

                <p>OR...</p>

                <p>If you already own Freespace 2, just point us to the retail data files (usually C:\Games\Freespace2).</p>

                <div class="input-group">
                    <input type="text" class="form-control" v-model="retail_path">
                    <span class="input-group-btn">
                        <button class="btn btn-default" @click.prevent="selectRetailFolder">Browse...</button>
                    </span>
                </div>
                <br>

                <p>
                    <button class="btn btn-primary" @click.prevent="processRetail">Continue</button>
                    <button class="btn btn-default pull-right" @click.prevent="wl_popup_visible = true">Skip</button>
                </p>
            </form>
        </div>

        <div v-else-if="step === 3">
            <h1>Suit Up, Pilot!</h1>

            <p>
                Everything's setup and you can start playing Freespace Open games right away. Head on over to the
                <a href="#" @click.prevent="goToExplore">Explore</a> tab and pick a few to start with.
            </p>

            <p>
                If you are interested in playing Retail Freespace 2, we recommend you install the
                <a href="#" @click.prevent="goToMVPS">MediaVPs mod</a>. That mod will let you play Freespace 2 with all
                of the glittery graphical goodness that Hard-Light has created over the years!
            </p>

            <p><button class="btn btn-primary" @click.prevent="goToExplore">Finish</button></p>
        </div>

        <div v-else>
            <h1>Whoops</h1>

            <p>You somehow managed to end up in nirvana. If you see this page, please tell us how you managed that!</p>
        </div>

        <hr>
        <p>
            This launcher is still in development. Join us on
            <a href="https://discord.gg/qfReB8t" class="open-ext">#knossos</a>
            in HLP's Discord or visit our
            <a href="https://www.hard-light.net/forums/index.php?topic=94068.0" class="open-ext">release thread</a>
            and let us know what you think, what didn't work and what you would like to change.
        </p>
        <p>-- ngld</p>

        <div class="popup-bg" v-if="wl_popup_visible" @click.prevent="wl_popup_visible = false"></div>

        <div class="popup" v-if="wl_popup_visible">
            <div class="title clearfix">
                Are You Sure?

                <a href="" class="pull-right" @click.prevent="wl_popup_visible = false">
                    <i class="fa fa-times"></i>
                </a>
            </div>
            <div class="content gen-scroll-style">
                <p>
                    You can skip this step, but you won't be able to play most games that Knossos offers.
                    If you try to install a Freespace2 mod, you'll be asked to install Retail Freespace2 again.
                </p>

                <p>You can always install Retail Freespace2 from the settings!</p>

                <div class="popup-buttons">
                    <button class="btn btn-default" @click.prevent="skipRetail">Skip</button>
                    <button class="btn btn-default pull-right" @click.prevent="wl_popup_visible = false">Cancel</button>
                </div>
            </div>
        </div>
    </div>
</template>