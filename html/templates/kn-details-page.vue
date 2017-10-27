<script>
import 'blueimp-gallery/css/blueimp-gallery.min.css';
import Gallery from 'blueimp-gallery/js/blueimp-gallery.min.js';
import '../js/gallery_yt';

import bbparser from '../js/bbparser';

export default {
    props: ['mod'],

    data: () => ({
        version: null,
        lightbox: null,
        tools: [],
        tools_built: false,
        open: false
    }),

    created() {
        this.version = this.mod.version;
    },

    computed: {
        cur_mod() {
            for(let mod of this.mod.versions) {
                if(mod.version === this.version) {
                    return Object.assign(mod, {
                        status: this.mod.status,
                        progress: this.mod.progress,
                        progress_info: this.mod.progress_info
                    });
                }
            }

            return null;
        },

        rendered_desc() {
            return bbparser(this.cur_mod.description);
        }
    },

    watch: {
        cur_mod(new_mod) {
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
            this.lightbox = Gallery(this.cur_mod.screenshots);
        },

        showVideos(videos) {
            let ytids = [];
            for(let link of this.cur_mod.videos) {
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

        updateTools(cur_mod) {
            if(this.tools_built) return;
            this.tools_built = true;

            if(!cur_mod) cur_mod = this.cur_mod;

            call(fs2mod.getModTools, cur_mod.id, cur_mod.version, (tools) => {
                this.tools = tools;
            });
        },

        launchTool(label) {
            fs2mod.runModTool(this.cur_mod.id, this.cur_mod.version, '', '', label);
        },

        uploadLog() {
            alert('Not yet implemented!');
        },

        uninstallMod() {
            fs2mod.uninstall(this.mod.id, this.mod.version, []);
        }
    }
}
</script>
<template>
    <div class="details-container">
        <div class="img-frame">
            <img v-if="cur_mod.banner" :src="cur_mod.banner.indexOf('://') === -1 ? 'file://' + cur_mod.banner : cur_mod.banner" class="mod-banner">
            <div class="title-frame">
                <h1>{{ cur_mod.title }}</h1>
                Version
                <select v-model="version" class="form-control">
                    <option v-for="m in mod.versions" :value="m.version">{{ m.version }}</option>
                </select>
            </div>
        </div>

        <div class="row details-btns">
            <div class="col-sm-6">
                <button
                    class="mod-btn btn-green"
                    v-if="cur_mod.installed && (cur_mod.status === 'ready' || cur_mod.status === 'update') && (cur_mod.type === 'mod' || cur_mod.type === 'tc')"
                    @click="play">
                    <span class="btn-text">PLAY</span>
                </button>

                <button class="mod-btn btn-yellow" v-if="cur_mod.installed && cur_mod.status === 'update'" @click="update">
                    <span class="btn-text">UPDATE</span>
                </button>

                <button class="mod-btn btn-red" v-if="cur_mod.status === 'error'" @click="showErrors">
                    <span class="btn-text">ERROR</span>
                </button>

                <button class="mod-btn btn-blue" v-if="cur_mod.status !== 'updating' && !cur_mod.installed" @click="install">
                    <span class="btn-text">INSTALL</span>
                </button>

                <button class="mod-btn btn-blue" v-if="cur_mod.status === 'updating'" @click="showProgress">
                    <span class="small-btn-text">
                        INSTALLING...<br>
                        {{ Math.round(cur_mod.progress) }}%
                    </span>
                </button>

                <button class="mod-btn btn-orange" v-if="cur_mod.status === 'updating'" @click="cancel">
                    <span class="btn-text">CANCEL</span>
                </button>

                <button class="mod-btn btn-blue" v-if="cur_mod.installed" @click="reportMod">
                    <span class="btn-text">REPORT</span>
                </button>

                <kn-dropdown btn_style="options" @open="updateTools(); open = true" @close="open = false">
                    <button v-for="tool in tools" @click="launchTool(tool)">Run {{ tool }}</button>
                    <button @click="uploadLog">Upload Debug Log</button>
                    <button v-if="mod.status !== 'updating' && mod.installed" @click="install">Modify</button>
                    <button v-if="mod.id !== 'FS2' && mod.status !== 'updating' && !mod.dev_mode" @click="uninstallMod">Uninstall</button>
                </kn-dropdown>
            </div>

            <div class="col-sm-6 short-frame">
                <div class="date-frame pull-right">
                    <div v-if="cur_mod.first_release">Release: {{ cur_mod.first_release }}</div>
                    <div v-if="cur_mod.last_update"><em>Last Updated: {{ cur_mod.last_update }}</em></div>
                </div>

                <button class="link-btn btn-link-blue pull-right" v-if="cur_mod.screenshots.length > 0" @click="showScreens(cur_mod.screenshots)"><span class="btn-text">IMAGES</span></button>
                <button class="link-btn btn-link-blue pull-right" v-if="cur_mod.videos.length > 0" @click="showVideos(cur_mod.videos)"><span class="btn-text">VIDEOS</span></button>
                <button class="link-btn btn-link-red pull-right" v-if="cur_mod.release_thread" @click="openLink(cur_mod.release_thread)"><span class="btn-text">FORUM</span></button>
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