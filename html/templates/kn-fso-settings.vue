<script>
export default {
    props: ['fso_build', 'mods', 'cmdline'],

    data: () => ({
        custom_build: null,
        caps: null,
        loading_flags: false,
        easy_flags: {},
        flags: {},
        selected_easy_flags: '',
        custom_flags: '',
        bool_flags: {},
        list_type: 'Graphics'
    }),

    created() {
        this.processCmdline();
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

    watch: {
        fso_build(build) {
            this.fso_build = build;
            this.updateFsoBuild();
        },

        caps() {
            this.processCmdline();
        },

        custom_flags() {
            this.updateFlags();
        },

        selected_easy_flags(idx) {
            let group = this.easy_flags[idx];
            if(!group) return;

            // TODO
            console.log(group);
        }
    },

    methods: {
        processCmdline() {
            if(!this.caps) return;

            this.bool_flags = {};
            const custom = [];
            const flags = [];

            for(let list_type of Object.keys(this.caps.flags)) {
                for(let flag of this.caps.flags[list_type]) {
                    flags.push(flag.name);
                }
            }

            for(let part of this.cmdline.split(' ')) {
                if(part === '') continue;

                if(flags.indexOf(part) > -1) {
                    this.bool_flags[part] = true;
                } else {
                    custom.push(part);
                }
            }

            this.easy_flags = this.caps.easy_flags;
            this.flags = this.caps.flags;
            this.selected_easy_flags = '';
            this.custom_flags = custom.join(' ');
            this.list_type = 'Audio';
        },

        showFlagDoc(url) {
            vm.popup_visible = true;
            vm.popup_mode = 'frame';
            vm.popup_title = 'Flag Documentation';
            vm.popup_content = url;
        },

        updateFlags() {
            let cmdline = '';
            for(let name of Object.keys(this.bool_flags)) {
                if(this.bool_flags[name]) {
                    cmdline += name + ' ';
                }
            }

            cmdline += this.custom_flags;
            this.$emit('update:cmdline', cmdline);
        },

        selectCustomBuild() {
            call(fs2mod.selectCustomBuild, (result) => {
                if(result !== '') {
                    this.$emit('update:fso_build', 'custom#' + result);
                }
            });
        },

        isValidBuild() {
            return this.fso_build && this.fso_build.indexOf('#') > -1;
        },

        updateFsoBuild() {
            if(this.fso_build) {
                let sel_build = this.fso_build.split('#');

                if(sel_build[0] === 'custom') {
                    this.custom_build = sel_build[1];
                }

                this.loading_flags = true;
                call_async(fs2mod.getFsoCaps, sel_build[0], sel_build[1], (caps) => {
                    this.loading_flags = false;
                    this.caps = caps.flags;
                });
            } else {
                if (this.fso_build !== null) this.$emit('update:fso_build', null);
                this.custom_build = null;
                this.caps = null;
            }
        }
    }
}
</script>
<template>
    <div>
        <div class="form-group">
            <label class="col-xs-3 control-label">FSO build</label>
            <div class="col-xs-9">
                <div class="input-group">
                    <select class="form-control" :value="fso_build" @input="$emit('update:fso_build', $event.target.value)">
                        <option v-if="!isValidBuild()" :key="'invalid'" value="invalid">Select a valid build</option>
                        <option :value="null">{{ custom_build || 'Mod default' }}</option>
                        <option v-for="mod in engine_builds" :key="mod.id + '-' + mod.version" :value="mod.id + '#' + mod.version">
                            {{ mod.title }} {{ mod.version }}
                        </option>
                        <option v-if="custom_build" :value="'custom#' + custom_build">{{ custom_build.replace(/\\/g, '/').split('/').pop() }}</option>
                    </select>
                    <span class="input-group-btn">
                        <button class="btn btn-default" @click.prevent="selectCustomBuild">Browse...</button>
                    </span>
                </div>
            </div>
        </div>

        <!--
            Not yet implemented

        <div class="form-group">
            <label class="col-sm-4 control-label">Easy setup</label>
            <div class="col-sm-8">
                <select class="form-control" v-model="selected_easy_flags">
                    <option value="">Select a group</option>
                    <option v-for="(name, idx) in easy_flags" :value="idx">{{ name }}</option>
                </select>
            </div>
        </div>
        -->

        <div class="form-group">
            <label class="col-sm-4 control-label">Custom flags</label>
            <div class="col-sm-8">
                <input type="text" class="form-control" v-model="custom_flags">
            </div>
        </div>

        <div class="form-group">
            <label class="col-sm-4 control-label">Full command line</label>
            <div class="col-sm-8">
                <textarea readonly class="form-control" rows="3">{{ loading_flags ? 'Loading...' : cmdline }}</textarea>
            </div>
        </div>

        <div class="form-group">
           <label class="col-sm-4 control-label">Flag list type</label>
            <div class="col-sm-8">
                <select class="form-control" v-model="list_type">
                    <option v-for="(flags, name) in flags">{{ name }}</option>
                </select>
            </div>
        </div>

        <div class="form-group">
            <div class="col-sm-8 col-sm-offset-4">
                <div class="checklist">
                    <label class="checkbox" v-for="flag in flags[list_type]">
                        <input type="checkbox" v-model="bool_flags[flag.name]" @change="updateFlags">
                        {{ flag.desc === '' ? flag.name : flag.desc }}
                        <a :href="flag.web_url" @click.prevent="showFlagDoc(flag.web_url)" v-if="flag.web_url" class="pull-right">?</a>
                    </label>
                </div>
            </div>
        </div>
    </div>
</template>