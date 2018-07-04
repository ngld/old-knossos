<script>
export default {
    props: [],
    
    data: () => ({
        engine_builds: [],
        fso_build: 'invalid',
        exe_file: null,
        exes: [],
        cmdline: '',
        loading_flags: false,
        easy_flags: {},
        custom_flags: '',
        flags: {},
        selected_easy_flags: '',
        flag_states: {},
        list_type: 'Graphics'
    }),

    created() {
        call(fs2mod.getEngineBuilds, (result) => {
            this.engine_builds = JSON.parse(result);
        });
    },

    watch: {
        fso_build(build) {
            this.fso_build = build;
            this.updateFsoBuild();
        },

        selected_easy_flags(idx) {
            let group = this.easy_flags[idx];
            if(!group) return;

            // TODO
            console.log(group);
        },

        custom_flags() {
            this.updateFlags();
        }
    },

    methods: {
        processCmdline(caps) {
            if(!caps) return;

            const flags = [];
            for(let list_type of Object.keys(caps.flags)) {
                for(let flag of caps.flags[list_type]) {
                    flags.push(flag.name);
                    if(this.flag_states[flag.name] === undefined) this.$set(this.flag_states, flag.name, 1);
                }
            }

            for(let name of Object.keys(this.flag_states)) {
                if(flags.indexOf(name) === -1) this.$delete(this.flag_states, name);
            }

            this.easy_flags = caps.easy_flags;
            this.flags = caps.flags;
            this.selected_easy_flags = '';
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
            for(let name of Object.keys(this.flag_states)) {
                if(this.flag_states[name] === 2) {
                    cmdline += name + ' ';
                }
            }

            this.cmdline = cmdline + this.custom_flags;
        },

        selectCustomBuild() {
            call(fs2mod.selectCustomBuild, (result) => {
                if(result !== '') {
                    this.fso_build = 'custom#' + result;
                }
            });
        },

        isValidBuild() {
            return this.fso_build !== 'invalid' && this.fso_build.indexOf('#') > -1;
        },

        updateFsoBuild() {
            if(this.fso_build !== 'invalid') {
                let sel_build = this.fso_build.split('#');

                this.loading_flags = true;
                this.exes = [];

                call_async(fs2mod.getFsoCaps, sel_build[0], sel_build[1], (caps) => {
                    this.loading_flags = false;
                    this.processCmdline(caps.flags);
                    this.exes = caps.exes;
                    if(!this.exe_file) this.exe_file = caps.exes[0];
                });
                call(fs2mod.getGlobalFlags, this.fso_build, (flags) => {
                    this.flag_states = JSON.parse(flags);
                    if(this.flag_states['#custom']) {
                        this.custom_flags = this.flag_states['#custom'];
                        delete this.flag_states['#custom'];
                    } else {
                        this.custom_flags = '';
                    }

                    if(this.flag_states['#exe']) {
                        this.exe_file = this.flag_states['#exe'];
                        delete this.flag_states['#exe'];
                    } else {
                        this.exe_file = this.exes && this.exes.length > 0 ? this.exes[0] : null;
                    }

                    this.updateFlags();
                });
            } else {
                this.fso_build = null;
            }
        },

        save() {
            fs2mod.saveGlobalFlags(this.fso_build, JSON.stringify({
                ...this.flag_states,
                '#custom': this.custom_flags,
                '#exe': this.exe_file
            }));
        },

        applyToAll() {
            fs2mod.applyGlobalFlagsToAll(JSON.stringify(this.flag_states), this.custom_flags);
        }
    }
}
</script>
<template>
    <div class="kn-global-flags">
        <div class="form-group">
            <label class="col-sm-4 control-label">FSO build:</label>
            <div class="col-sm-8">
                <select class="form-control" v-model:value="fso_build">
                    <option v-if="!isValidBuild()" :key="null" value="invalid">Please select a valid build</option>
                    <option v-for="mod in engine_builds" :key="mod.id + '-' + mod.version" :value="mod.id + '#' + mod.version">
                        {{ mod.title }} {{ mod.version }}
                    </option>
                </select>
            </div>
        </div>

        <div class="form-group">
            <label class="col-sm-4 control-label">Executable:</label>
            <div class="col-sm-8">
                <select class="form-control" v-model="exe_file">
                    <option v-for="filename in exes">{{ filename }}</option>
                </select>
            </div>
        </div>

        <!--
            Not yet implemented

        <div class="form-group">
            <label class="col-sm-4 control-label">Easy Setup:</label>
            <div class="col-sm-8">
                <select class="form-control" v-model="selected_easy_flags">
                    <option value="">Select a group</option>
                    <option v-for="(name, idx) in easy_flags" :value="idx">{{ name }}</option>
                </select>
            </div>
        </div>
        -->

        <div class="form-group">
            <label class="col-sm-4 control-label">Custom Flags:</label>
            <div class="col-sm-8">
                <input type="text" class="form-control" v-model="custom_flags">
            </div>
        </div>

        <div class="form-group">
            <label class="col-sm-4 control-label">Full Commandline:</label>
            <div class="col-sm-8">
                <textarea readonly class="form-control" rows="3">{{ loading_flags ? 'Loading...' : cmdline }}</textarea>
            </div>
        </div>

        <div class="form-group">
            <label class="col-sm-4 control-label">List Type:</label>
            <div class="col-sm-8">
                <select class="form-control" v-model="list_type">
                    <option v-for="(flags, name) in flags">{{ name }}</option>
                </select>
            </div>
        </div>

        <div class="form-group">
            <div class="col-sm-8 col-sm-offset-4">
                <div class="checklist">
                    <table style="width: 100%" cellspacing="2">
                        <tr>
                            <th>Off</th>
                            <th>Def.</th>
                            <th>On</th>
                            <th> </th>
                            <th width="2"> </th>
                        </tr>

                        <tr v-for="flag in flags[list_type]">
                            <td v-for="(label, i) in ['Off', 'Default', 'On']">
                                <input type="radio" @change="flag_states[flag.name] = i; updateFlags()" :checked="flag_states[flag.name] === i">
                            </td>

                            <td>{{ flag.desc === '' ? flag.name : flag.desc }}</td>
                            <td><a :href="flag.web_url" @click.prevent="showFlagDoc(flag.web_url)" v-if="flag.web_url" class="pull-right">?</a></td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>

        <div class="form-group">
            <div class="col-sm-8 col-sm-offset-4">
                <button class="mod-btn btn-green" @click="save">Save</button>
                <button class="mod-btn btn-green" @click="applyToAll">Apply to all</button>
            </div>
        </div>
    </div>
</template>