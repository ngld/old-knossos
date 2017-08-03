<script>
export default {
    props: ['caps', 'cmdline'],

    data: () => ({
        easy_flags: {},
        flags: {},
        selected_easy_flags: '',
        custom_flags: '',
        bool_flags: {},
        list_type: 'Graphics'
    }),

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
        }
    },

    watch: {
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
    }
};
</script>
<template>
    <div>
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
                <textarea readonly class="form-control" rows="3">{{ cmdline }}</textarea>
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