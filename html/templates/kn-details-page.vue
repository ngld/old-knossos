<script>
import 'blueimp-gallery/css/blueimp-gallery.min.css';
import Gallery from 'blueimp-gallery/js/blueimp-gallery.min.js';
import '../js/gallery_yt';

import Popper from 'vue-popperjs';
import 'vue-popperjs/dist/css/vue-popper.css';

import bbparser from '../js/bbparser';
import moment from 'moment';

export default {
    props: ['modbundle', 'updater'],

    components: {
        popper: Popper
    },

    data: () => ({
        version: null,
        lightbox: null,
        tools: [],
        tools_built: false,
        open: false
    }),

    created() {
        this.version = this.modbundle.version;
    },

    mounted() {
        this.updater();
    },

    computed: {
        mod() {
            for(let mod of this.modbundle.versions) {
                if(mod.version === this.version) {
                    return Object.assign({}, mod, {
                        last_played: this.modbundle.last_played,
                        status: this.modbundle.status,
                        progress: this.modbundle.progress,
                        progress_info: this.modbundle.progress_info
                    });
                }
            }

            return null;
        },

        rendered_desc() {
            return bbparser(this.mod.description);
        }
    },

    watch: {
        mod(new_mod) {
            this.tools_built = false;
            if(this.open) this.updateTools(new_mod);
        }
    },

    methods: {
        ...require('../js/mod_button_methods.js').default,

        openLink(url) {
            fs2mod.openExternal(url);
        },

        showScreens(screens) {
            this.lightbox = Gallery(this.mod.screenshots);
        },

        showVideos(videos) {
            let ytids = [];
            for(let link of this.mod.videos) {
                let id = /[\?&]v=([^&]+)/.exec(link);

                if(id) {
                    ytids.push({
                        type: 'text/html',
                        youtube: id[1],
                        poster: 'https://img.youtube.com/vi/' + id[1] + '/maxresdefault.jpg',
                        href: 'https://www.youtube.com/watch?v=' + id[1]
                    });
                }
            }

            this.lightbox = Gallery(ytids, {
                youTubeClickToPlay: false,
                youTubePlayerVars: {
                    fs: 0,
                    vq: 'hd720'
                },
                toggleControlsOnSlideClick: false,
                onslideend: (idx, el) => {
                    // Make sure the videos start automatically.
                    let link = el.querySelector('.video-content a');
                    if(link) link.click();
                }
            });
        },

        updateTools(mod) {
            if(this.tools_built || !this.mod.installed) return;
            this.tools_built = true;

            if(!mod) mod = this.mod;

            call(fs2mod.getModTools, mod.id, mod.version, (tools) => {
                this.tools = tools;
            });
        },

        launchTool(label) {
            fs2mod.runModTool(this.mod.id, this.mod.version, '', '', label);
        },

        uploadLog() {
            call(fs2mod.uploadFsoDebugLog, (result) => {
                if(result !== '') {
                    vm.popup_visible = true;
                    vm.popup_title = 'Uploaded Debug Log';
                    vm.popup_mode = 'debug_log';
                    vm.popup_content = result;
                }
            });
        },

        uninstallMod() {
            fs2mod.uninstall(this.mod.id, this.mod.version, []);
        },

        verifyIntegrity() {
            fs2mod.verifyModIntegrity(this.mod.id, this.mod.version);
        },

        formatTime(time_str) {
            return moment(time_str).fromNow();
        }
    }
};
</script>
<template>
    <div class="details-container">
        <div class="img-frame">
            <img v-if="mod.banner" :src="mod.banner.indexOf('://') === -1 ? 'file://' + mod.banner : mod.banner" class="mod-banner">
            <div class="title-frame">
                <h1>{{ mod.title }}</h1>
                Version
                <select v-model="version" class="form-control">
                    <option v-for="m in modbundle.versions" :value="m.version">{{ m.version }}</option>
                </select>
            </div>
        </div>

        <div class="row details-btns">
            <div class="col-sm-6">
                <button
                    class="mod-btn btn-green"
                    v-if="mod.installed && (mod.status === 'ready' || mod.status === 'update') && (mod.type === 'mod' || mod.type === 'tc')"
                    @click="play">
                    <span class="btn-text">PLAY</span>
                </button>

                <button class="mod-btn btn-blue" v-if="mod.installed && mod.status === 'update'" @click="update">
                    <span class="btn-text">UPDATE</span>
                </button>

                <button class="mod-btn btn-red" v-if="mod.status === 'error'" @click="showErrors">
                    <span class="btn-text">ERROR</span>
                </button>

                <button class="mod-btn btn-blue" v-if="mod.status !== 'updating' && !mod.installed" @click="install">
                    <span class="btn-text">INSTALL</span>
                </button>

                <button class="mod-btn btn-blue" v-if="mod.status === 'updating'" @click="showProgress">
                    <span class="small-btn-text">
                        INSTALLING...<br>
                        {{ Math.round(mod.progress) }}%
                    </span>
                </button>

                <button class="mod-btn btn-orange" v-if="mod.status === 'updating'" @click="cancel">
                    <span class="btn-text">CANCEL</span>
                </button>

                <button class="mod-btn btn-yellow" v-if="mod.installed" @click="reportMod">
                    <span class="btn-text">REPORT</span>
                </button>

                <popper v-if="mod.status !== 'updating' && mod.installed" trigger="click" @show="updateTools(); open = true" @hide="open = false" class="dropdown dropdown-mod-btn">
                    <div class="dropdown-content">
                        <button v-for="tool in tools" @click="launchTool(tool)">Run {{ tool }}</button>
                        <button @click="uploadLog">Upload Debug Log</button>
                        <button v-if="mod.id !== 'FS2' && mod.status !== 'updating' && !mod.dev_mode" @click="install">Modify</button>
                        <button v-if="mod.status !== 'updating' && (mod.type === 'mod' || mod.type == 'tc')" @click="showFsoSettings">FSO Settings</button>
                        <button v-if="mod.id !== 'FS2' && mod.status !== 'updating' && !mod.dev_mode" @click="uninstallMod">Uninstall</button>
                        <button v-if="mod.id !== 'FS2' && !mod.dev_mode" @click="verifyIntegrity">Verify file integrity</button>
                    </div>

                    <button class="mod-btn btn-grey" slot="reference">Options</button>
                </popper>
            </div>

            <div class="col-sm-6 short-frame">
                <div class="date-frame pull-right">
                    <div v-if="mod.first_release">Release: {{ mod.first_release }}</div>
                    <div v-if="mod.last_update"><em>Last Updated: {{ mod.last_update }}</em></div>
                    <div v-if="mod.last_played"><em>Last Played: {{  formatTime(mod.last_played) }}</em></div>
                </div>

                <button class="link-btn btn-link-blue pull-right" v-if="mod.screenshots.length > 0" @click="showScreens(mod.screenshots)"><span class="btn-text">IMAGES</span></button>
                <button class="link-btn btn-link-blue pull-right" v-if="mod.videos.length > 0" @click="showVideos(mod.videos)"><span class="btn-text">VIDEOS</span></button>
                <button class="link-btn btn-link-red pull-right" v-if="mod.release_thread" @click="openLink(mod.release_thread)"><span class="btn-text">FORUM</span></button>
            </div>
        </div>

        <div class="mod-desc">
            <p v-html="rendered_desc"></p>
        </div>

        <div id="blueimp-gallery" class="blueimp-gallery blueimp-gallery-controls">
            <div class="slides"></div>
            <h3 class="title"></h3>
            <a class="prev">‹</a>
            <a class="next">›</a>
            <a class="close">×</a>
            <a class="play-pause"></a>
            <ol class="indicator"></ol>
        </div>
    </div>
</template>