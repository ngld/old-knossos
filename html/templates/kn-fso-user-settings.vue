<script>
export default {
    props: ['mod', 'mods'],

    data: () => ({
        last_user_build: null,
        user_build: null
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
            if(!mod.user_cmdline) mod.user_cmdline = mod.cmdline;

            call(fs2mod.getUserBuild, mod.id, mod.version, (result) => {
                this.last_user_build = this.user_build = result;
            });
        },

        save() {
            this.last_user_build = this.user_build;
            fs2mod.saveUserFsoDetails(this.mod.id, this.mod.version, this.user_build, this.mod.user_cmdline);
        },

        reset() {
            this.mod.user_cmdline = this.mod.cmdline;
            this.user_build = this.last_user_build;
        }
    }
}
</script>
<template>
    <div>
        <kn-fso-settings :mods="mods" :fso_build.sync="user_build" :cmdline.sync="mod.user_cmdline"></kn-fso-settings>

        <div class="form-group">
            <div class="col-xs-9 col-xs-offset-3">
                <button class="mod-btn btn-green" @click.prevent="save"><span class="btn-text">SAVE</span></button>
                <button class="mod-btn btn-red" @click.prevent="reset"><span class="btn-text">RESET</span></button>
            </div>
        </div>
    </div>
</template>