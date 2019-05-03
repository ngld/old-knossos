<script>
export default {
    props: ['mod', 'mods'],

    data: () => ({
        user_build: null,
        mod_cmdline: null
    }),

    created() {
        this.updateMeta();
    },

    watch: {
        mod() {
            this.updateMeta();
        }
    },

    methods: {
        updateMeta() {
            let mod = this.mod;
            if(!mod.user_cmdline) {
                //mod.user_cmdline = mod.cmdline;
                call(fs2mod.getModCmdline, mod.id, mod.version, (result) => {
                    mod.user_cmdline = this.mod_cmdline = result;
                });
            }

            call(fs2mod.getUserBuild, mod.id, mod.version, (result) => {
                this.user_build = result;
            });
        },

        save() {
            // Sadly we can't use null here since the cmdline parameter for saveUserFsoDetails is a QString.
            if(this.mod.user_cmdline === this.mod_cmdline) this.mod.user_cmdline = '#DEFAULT#';

            let build = this.user_build;
            if(build === null) build = '';

            fs2mod.saveUserFsoDetails(this.mod.id, this.mod.version, build, this.mod.user_cmdline);
        },

        reset() {
            call(fs2mod.getModCmdline, this.mod.id, this.mod.version, (result) => {
                this.mod.user_cmdline = this.mod_cmdline = result;
            });
            this.user_build = null;
        }
    }
}
</script>
<template>
    <div>
        <p v-if="mod.dev_mode">
            These settings apply only to your Home tab. To make changes that will apply to players, use the Develop tab.
        </p>
        <kn-fso-settings :mods="mods" :fso_build.sync="user_build" :cmdline.sync="mod.user_cmdline"></kn-fso-settings>

        <div class="form-group">
            <div class="col-xs-9 col-xs-offset-3">
                <button class="mod-btn btn-green" @click.prevent="save"><span class="btn-text">SAVE</span></button>
                <button class="mod-btn btn-red" @click.prevent="reset"><span class="btn-text">RESET</span></button>
            </div>
        </div>
    </div>
</template>